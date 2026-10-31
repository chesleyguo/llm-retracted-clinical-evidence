"""Step 16: code the model responses with the LLM coder (codebook section 5).

The prompt template, codebook sections 2 and 3, and the output format are read
from docs/codebook.md, never copied here. Each response is coded in its own
call by deepseek-v4-pro (thinking off, temperature 0, JSON output). The coder
sees the paper, the claim, the framing, the prompt, the response and the
auto-attached citations; it does not see the group, the tested model or the
condition.

Every request starts with the same fixed text (instructions, codebook, output
format), so DeepSeek's automatic prefix cache can reuse it; the first call
runs alone to fill the cache before the others run in parallel. Calls are made
only outside DeepSeek's peak hours (half price) unless --allow-peak is given.

Checks: an answer that is not valid JSON, uses a value outside the allowed
list, or is internally inconsistent is sent back with the problem (at most 3
attempts). An evidence quote that does not appear in the response is not
retried; the variable is listed in quote_not_found for human review. A quote
may hold several exact passages separated by " | " (codebook rule 9).

Auto-attached citations shown to the coder are only the entries the response
cites (OpenAI inline citations, Gemini grounding sources); search results the
response does not cite are left out (codebook v1.0, V3). The raw log keeps all.

V6 second pass: for each response coded V1 = EXPLICIT on a retracted paper,
a separate call (prompts/code_v6.txt) with the Retraction Watch record. A
control paper coded V1 = EXPLICIT gets V6 = FALSE_FLAG without a call.

Calls are appended to outputs/llm_calls/coding_{sample}.jsonl; a response
already coded with the current prompt is skipped on a re-run. Writes
data/processed/coding_{sample}.csv and results/coding_{sample}_summary.json.

Usage:
    python scripts/16_code_responses.py pilot --limit 3    # smoke test
    python scripts/16_code_responses.py pilot
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
CODEBOOK = ROOT / "docs" / "codebook.md"
V6_PROMPT = ROOT / "prompts" / "code_v6.txt"

PARAMS = {"temperature": 0, "thinking": {"type": "disabled"},
          "response_format": {"type": "json_object"}, "max_tokens": 2000}
MAX_ATTEMPTS = 3
WORKERS = 4
CACHE_WAIT_S = 10
# requests' read timeout restarts whenever a byte arrives, and DeepSeek sends
# keep-alive lines while a request waits, so a call can hang for good (it
# happened in the first full run). Each call gets a hard limit instead.
CALL_LIMIT_S = 300
FRAMING_LABELS = {"F1": "F1 clinical question", "F2": "F2 paper question",
                  "F3": "F3 status question"}
V6_CODES = {"ACCURATE", "INACCURATE", "NO_DETAIL"}
# Auto-attached entries that the response cites. "search source" entries are
# pages the search returned, which the response may not have used.
CITED_KINDS = {"inline citation", "grounding source"}

# DeepSeek peak hours: weekdays 9:00-12:00 and 14:00-18:00 Beijing time; all
# other hours are billed at half price. Chinese public holidays are also
# off-peak, but they are treated as peak here (the script just waits longer).
BEIJING = timezone(timedelta(hours=8))
# CNY per 1M tokens for deepseek-v4-pro: (cache hit, cache miss, output).
PRICES = {"peak": (0.30, 9.0, 27.0), "off_peak": (0.15, 4.5, 13.5)}


def load_script(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s11 = load_script("11_generate_claims.py")
s12 = load_script("12_build_claims_review.py")
s15 = load_script("15_run_experiment.py")
log_lock = threading.Lock()


# ------------------------------------------------------------ codebook parts

def codebook_parts():
    """Template, sections 2-3, output format and the V6 section, from the codebook."""
    text = CODEBOOK.read_text()
    sections = re.search(r"(## 2\. .*?)\n## 4\. ", text, re.S).group(1).strip()
    sec5 = re.search(r"## 5\. .*?\n## 6\. ", text, re.S).group(0)
    template = re.search(r"Prompt template.*?\n```\n(.*?)\n```", sec5, re.S).group(1)
    output_format = re.search(r"```json\n(.*?)\n```", sec5, re.S).group(1)
    v6 = re.search(r"(### V6\. .*?)\n## 4\. ", text, re.S).group(1).strip()
    return template, sections, output_format, v6


def codebook_version():
    return re.search(r"^(?:Draft )?(v[\d.]+) ·", CODEBOOK.read_text(), re.M).group(1)


def allowed_values(output_format):
    """Allowed codes per variable, from the "A | B | C" strings of the format."""
    fmt = json.loads(output_format)
    return {k: set(v.split(" | ")) for k, v in fmt.items() if " | " in v}


# ------------------------------------------------------------------ inputs

def authors(pmids):
    """'Surname Initials' of every author, from the cached PubMed XML."""
    out = {}
    for d in s12.XML_DIRS:
        for path in sorted(d.glob("*.xml")):
            for a in ET.parse(path).getroot().iter("PubmedArticle"):
                pmid = a.findtext("MedlineCitation/PMID")
                if pmid not in pmids or pmid in out:
                    continue
                names = []
                for au in a.findall("MedlineCitation/Article/AuthorList/Author"):
                    name = au.findtext("CollectiveName") or " ".join(
                        x for x in (au.findtext("LastName"), au.findtext("Initials")) if x)
                    if name:
                        names.append(name)
                out[pmid] = ", ".join(names)
    return out


def load_papers():
    """Paper fields shown to the coder, plus the Retraction Watch record for V6."""
    final = pd.read_csv(PROCESSED / "claims_final.csv", dtype=str, keep_default_na=False)
    review = pd.read_csv(PROCESSED / "claims_review.csv", dtype=str, keep_default_na=False)
    abstracts = dict(zip(review.loc[review["in_sample"] == "TRUE", "pmid"],
                         review.loc[review["in_sample"] == "TRUE", "abstract"]))
    pmids = set(final["pmid"])
    meta, names = s12.metadata(pmids), authors(pmids)
    rw = pd.concat([pd.read_csv(PROCESSED / f"sample_{s}.csv", dtype=str, keep_default_na=False)
                    for s in ("pilot", "main")]).drop_duplicates("pmid").set_index("pmid")
    papers = {}
    for _, r in final.iterrows():
        m = meta[r["pmid"]]
        p = {"title": s12.clean_title(m["raw_title"])[0], "authors": names.get(r["pmid"], ""),
             "year": m["year"], "journal": s12.clean_journal(m["raw_journal"]),
             "abstract": abstracts[r["pmid"]], "claim": r["claim"]}
        if r["group"] == "retracted":
            reasons = [x.strip().lstrip("+") for x in rw.loc[r["pmid"], "reason"].split(";")]
            p["retraction_date"] = rw.loc[r["pmid"], "retraction_date"]
            p["reasons"] = "; ".join(x for x in reasons if x)
        papers[r["pmid"]] = p
    return papers


def load_responses(sample):
    """Successful calls in the design cells, one per call key."""
    path = ROOT / "outputs" / "responses" / f"{sample}.jsonl"
    records = [json.loads(line) for line in open(path)]
    counts = {"records in log": len(records)}
    ok = [r for r in records if r["status"] == "ok"]
    counts["successful calls"] = len(ok)
    design = [r for r in ok if (r["framing"], r["condition"]) in s15.DESIGN]
    counts["in design cells"] = len(design)
    latest = {}
    for r in design:   # a re-run appends; keep the latest successful call per key
        latest[(r["pmid"], r["model_requested"], r["framing"], r["condition"], r["run_index"])] = r
    out = sorted(latest.values(), key=lambda r: r["order_index"])
    counts["one per call key"] = len(out)
    for k, v in counts.items():
        print(f"  {k}: {v}")
    return out, counts


def format_citations(r):
    cited = [c for c in r["auto_citations"] or [] if c["kind"] in CITED_KINDS]
    if r["condition"] != "C2" or not cited:
        return "None"
    return "\n".join(f"[{i}] {c['kind']}: {c['title'] or '(no title)'} | {c['url']}"
                     for i, c in enumerate(cited, 1))


# ------------------------------------------------------------------ checks

def norm(text):
    # Whitespace, markdown emphasis and curly quotes are normalized before the
    # quote check; the coder often drops ** or changes quote marks when quoting.
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = re.sub(r"[*`]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def make_check(allowed, framing, has_citations):
    def check(parsed):
        for var, codes in allowed.items():
            if parsed.get(var) not in codes:
                return f"{var} must be one of: {' | '.join(sorted(codes))}."
        for var in [k for k in parsed if k.endswith("_evidence")] + ["note"]:
            if not isinstance(parsed.get(var, ""), str):
                return f"{var} must be a string."
        if framing == "F3" and parsed["V4_status_answer"] == "NA":
            return "The framing is F3, so V4_status_answer cannot be NA."
        if framing != "F3" and parsed["V4_status_answer"] != "NA":
            return f"The framing is {framing}, not F3, so V4_status_answer must be NA."
        if (parsed["V3_cited"] == "NOT_CITED") != (parsed["V3_source"] == "NA"):
            return "V3_source must be NA if and only if V3_cited is NOT_CITED."
        if parsed["V3_source"] == "AUTO_CITATION" and not has_citations:
            return "There are no auto-attached citations, so V3_source cannot be AUTO_CITATION."
        return None
    return check


def check_v6(parsed):
    if parsed.get("V6_accuracy") not in V6_CODES:
        return f"V6_accuracy must be one of: {' | '.join(sorted(V6_CODES))}."
    if not isinstance(parsed.get("V6_evidence", ""), str):
        return "V6_evidence must be a string."
    return None


def quote_found(quote, text):
    """A quote is found if every passage between " | " separators appears in
    the text (codebook rule 9). Passages joined by an ellipsis are not split,
    so they are found only if the text itself has the ellipsis there."""
    parts = [norm(x).strip(" .,;:") for x in quote.split(" | ")]
    return all(x in norm(text) for x in parts if x)


def quotes_not_found(parsed, response, citations):
    """Evidence variables whose quote does not appear in the response
    (for V3, in the response or the auto-attached citations)."""
    missing = []
    for var, quote in parsed.items():
        if not var.endswith("_evidence") or not str(quote).strip():
            continue
        where = response + ("\n" + citations if var == "V3_evidence" else "")
        if not quote_found(quote, where):
            missing.append(var.replace("_evidence", ""))
    return missing


# ----------------------------------------------------------------- calling

def is_peak(now=None):
    t = (now or datetime.now(timezone.utc)).astimezone(BEIJING)
    return t.weekday() < 5 and (9 <= t.hour < 12 or 14 <= t.hour < 18)


def wait_off_peak(allow_peak):
    while not allow_peak and is_peak():
        print("  peak hours (Beijing time); waiting 5 minutes")
        time.sleep(300)


def post_with_limit(messages, key):
    """s11.post with a hard time limit. A call over the limit is abandoned
    (left in a daemon thread, so it cannot keep the script from exiting) and
    sent again, at most 3 times."""
    for attempt in range(1, 4):
        box = {}

        def target():
            try:
                box["raw"] = s11.post(messages, key, PARAMS)
            except Exception as e:
                box["error"] = e
        t = threading.Thread(target=target, daemon=True)
        t.start()
        t.join(CALL_LIMIT_S)
        if "raw" in box:
            return box["raw"]
        if "error" in box:
            raise box["error"]
        print(f"    call over {CALL_LIMIT_S} s; sending again ({attempt}/3)", flush=True)
    raise RuntimeError("API call timed out 3 times")


def already_done(log_path):
    done = {}
    if log_path.exists():
        for line in open(log_path):
            r = json.loads(line)
            if r["status"] == "ok":
                done[(r["response_id"], r["task"], r["prompt_sha256"])] = r["parsed"]
    return done


def code_one(task, prompt_text, prompt_sha, values, r, check, key, log_path, allow_peak):
    """One coding call with up to 3 attempts; every attempt is logged."""
    messages = [{"role": "user", "content": s11.fill(prompt_text, values)}]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        wait_off_peak(allow_peak)
        peak = is_peak()
        raw = post_with_limit(messages, key)
        content = raw["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
            problem = check(parsed)
        except json.JSONDecodeError:
            parsed, problem = None, "The answer was not valid JSON."
        status = "ok" if problem is None else ("failed" if attempt == MAX_ATTEMPTS else "retry")
        record = {
            "call_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "task": task, "response_id": r["call_id"], "sample": r["sample"],
            "pmid": r["pmid"], "pair_pmid": r["pair_pmid"], "group": r["group"],
            "tested_model": r["model_requested"], "framing": r["framing"],
            "condition": r["condition"], "attempt": attempt, "peak_hours": peak,
            "prompt_sha256": prompt_sha, "model_requested": s11.MODEL,
            "model_returned": raw.get("model"), "system_fingerprint": raw.get("system_fingerprint"),
            "parameters": PARAMS, "input_values": values, "messages": messages,
            "response": raw, "usage": raw.get("usage"),
            "parsed": parsed, "status": status, "problem": problem,
        }
        with log_lock, open(log_path, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        if problem is None:
            return parsed
        messages = messages + [{"role": "assistant", "content": content},
                               {"role": "user", "content": problem + " Return the corrected JSON object."}]
    return None


def run_jobs(jobs):
    """Run the first job alone (fills the prefix cache), the rest in parallel."""
    results = {}
    if not jobs:
        return results
    first, rest = jobs[0], jobs[1:]
    results[first[0]] = first[1]()
    # DeepSeek builds the cache a few seconds after a request; in the smoke
    # test, calls made 1-2 s after the first had no cache hits.
    time.sleep(CACHE_WAIT_S)
    with ThreadPoolExecutor(WORKERS) as ex:
        futures = {rid: ex.submit(fn) for rid, fn in rest}
        for i, (rid, fut) in enumerate(futures.items(), 2):
            try:
                results[rid] = fut.result()
            except Exception as e:   # left uncoded; a re-run tries it again
                print(f"  {rid}: {type(e).__name__}: {e}", flush=True)
                results[rid] = None
            if i % 25 == 0:
                print(f"  {i}/{len(jobs)} done", flush=True)
    return results


# ----------------------------------------------------------------- summary

def cost_summary(log_path):
    calls = [json.loads(line) for line in open(log_path)]
    tokens = Counter()
    cost = 0.0
    for c in calls:
        u = c["usage"] or {}
        hit, miss = u.get("prompt_cache_hit_tokens", 0), u.get("prompt_cache_miss_tokens", 0)
        out = u.get("completion_tokens", 0)
        tokens.update({"cache_hit": hit, "cache_miss": miss, "output": out})
        price = PRICES["peak" if c["peak_hours"] else "off_peak"]
        cost += (hit * price[0] + miss * price[1] + out * price[2]) / 1e6
    total_in = tokens["cache_hit"] + tokens["cache_miss"]
    return {"api_calls": len(calls), "peak_hour_calls": sum(c["peak_hours"] for c in calls),
            "input_tokens": total_in, "cache_hit_tokens": tokens["cache_hit"],
            "cache_hit_share": round(tokens["cache_hit"] / total_in, 3) if total_in else None,
            "output_tokens": tokens["output"], "cost_cny": round(cost, 2),
            "model_returned": sorted({c["model_returned"] for c in calls if c["model_returned"]})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample", choices=["pilot", "main"])
    ap.add_argument("--limit", type=int, help="only the first N responses (smoke test)")
    ap.add_argument("--allow-peak", action="store_true", help="also call during peak hours")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    key = os.environ["DEEPSEEK_API_KEY"]
    log_path = ROOT / "outputs" / "llm_calls" / f"coding_{args.sample}.jsonl"

    template, sections, output_format, v6_section = codebook_parts()
    version = codebook_version()
    print(f"Codebook {version}")
    allowed = allowed_values(output_format)
    # The fixed prefix is filled once; only the response fields vary per call.
    prompt_text = s11.fill(template, {"codebook_sections_2_and_3": sections,
                                      "output_format": output_format})
    prompt_sha = hashlib.sha256(prompt_text.encode()).hexdigest()
    v6_text = s11.fill(V6_PROMPT.read_text(), {"v6_section": v6_section})
    v6_sha = hashlib.sha256(v6_text.encode()).hexdigest()

    papers = load_papers()
    responses, counts = load_responses(args.sample)
    if args.limit:
        responses = responses[:args.limit]
        print(f"  smoke test: first {len(responses)}")
    done = already_done(log_path)

    # ---- main pass
    jobs, codes = [], {}
    for r in responses:
        p = papers[r["pmid"]]
        citations = format_citations(r)
        values = {"title": p["title"], "authors": p["authors"], "year": p["year"],
                  "journal": p["journal"], "abstract": p["abstract"], "claim": p["claim"],
                  "framing": FRAMING_LABELS[r["framing"]], "prompt": r["prompt"],
                  "response": r["response_text"], "auto_citations": citations}
        cached = done.get((r["call_id"], "code", prompt_sha))
        if cached is not None:
            codes[r["call_id"]] = cached
            continue
        check = make_check(allowed, r["framing"], citations != "None")
        jobs.append((r["call_id"], lambda r=r, v=values, c=check: code_one(
            "code", prompt_text, prompt_sha, v, r, c, key, log_path, args.allow_peak)))
    print(f"Main pass: {len(codes)} already coded, {len(jobs)} to code")
    codes.update(run_jobs(jobs))

    # ---- V6 second pass
    jobs, v6 = [], {}
    for r in responses:
        c = codes.get(r["call_id"])
        if not c or c["V1_retraction_flag"] != "EXPLICIT":
            continue
        if r["group"] == "control":
            v6[r["call_id"]] = {"V6_accuracy": "FALSE_FLAG", "V6_evidence": "", "note": ""}
            continue
        p = papers[r["pmid"]]
        values = {"retraction_date": p["retraction_date"], "reasons": p["reasons"],
                  "prompt": r["prompt"], "response": r["response_text"]}
        cached = done.get((r["call_id"], "code_v6", v6_sha))
        if cached is not None:
            v6[r["call_id"]] = cached
            continue
        jobs.append((r["call_id"], lambda r=r, v=values: code_one(
            "code_v6", v6_text, v6_sha, v, r, check_v6, key, log_path, args.allow_peak)))
    print(f"V6 pass: {len(v6)} done or assigned, {len(jobs)} to code")
    v6.update(run_jobs(jobs))

    # ---- table
    rows = []
    for r in responses:
        c = codes.get(r["call_id"])
        row = {"response_id": r["call_id"], "sample": r["sample"], "pair_pmid": r["pair_pmid"],
               "pmid": r["pmid"], "group": r["group"], "tested_model": r["model_requested"],
               "framing": r["framing"], "condition": r["condition"],
               "codebook_version": version, "status": "ok" if c else "failed"}
        if c:
            row.update({k: c.get(k, "") for k in json.loads(output_format) if k != "response_id"})
            missing = quotes_not_found(c, r["response_text"], format_citations(r))
            row["quote_not_found"] = "; ".join(missing)
            # A V3 quote taken from the prompt, not the response, may mean V3 was
            # miscoded (codebook: the paper named in the prompt does not count).
            row["v3_quote_from_prompt"] = "TRUE" if "V3" in missing and \
                quote_found(c["V3_evidence"], r["prompt"]) else "FALSE"
            d = v6.get(r["call_id"])
            row["V6_accuracy"] = d["V6_accuracy"] if d else ("FAILED" if c["V1_retraction_flag"] == "EXPLICIT" else "")
            row["V6_evidence"] = d.get("V6_evidence", "") if d else ""
            if d and d["V6_accuracy"] != "FALSE_FLAG" and d.get("V6_evidence") and \
                    not quote_found(d["V6_evidence"], r["response_text"]):
                row["quote_not_found"] = "; ".join(x for x in (row["quote_not_found"], "V6") if x)
        rows.append(row)
    table = pd.DataFrame(rows)
    out_path = PROCESSED / f"coding_{args.sample}.csv"
    table.to_csv(out_path, index=False)

    ok = table[table["status"] == "ok"]
    summary = {"counts": {**counts, "coded": len(ok), "failed": int((table["status"] == "failed").sum())},
               "distributions": {v: ok.loc[ok[v] != "", v].value_counts().to_dict() for v in
                                 list(allowed) + ["V6_accuracy"] if v in ok},
               "quote_not_found": {"responses": int((ok["quote_not_found"] != "").sum()),
                                   "by_variable": Counter(x for q in ok["quote_not_found"]
                                                          for x in q.split("; ") if x),
                                   "v3_quote_from_prompt": int((ok["v3_quote_from_prompt"] == "TRUE").sum())},
               "calls": cost_summary(log_path)}
    if not args.limit:
        (ROOT / "results" / f"coding_{args.sample}_summary.json").write_text(
            json.dumps(summary, indent=1, default=int) + "\n")
    print(json.dumps(summary, indent=1, default=int))
    print(f"Wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
