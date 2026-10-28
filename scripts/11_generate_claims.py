"""Step 11: extract the target claim and draft the F1 question with an LLM.

For every retracted trial and its control in the chosen sample(s):
1. extract_claim (prompts/extract_claim.txt): the abstract's main finding as
   a one-sentence claim, PICO fields, direction, and the abstract sentence that
   supports it. The script checks that the sentence really is in the abstract.
2. verify_claim (prompts/verify_claim.txt): a separate call that checks the
   extraction against its support sentence and abstract (direction stated
   and matching, same intervention name, one outcome, nothing added to the
   intervention / outcome / direction, population and comparison found in
   the abstract, hedged wording). It only flags problems; the flags go to
   the review table.
3. generate_f1 (prompts/generate_f1.txt): a neutral question built only from
   the PICO fields, so it cannot leak details of the paper.

Both groups go through exactly the same prompts; the prompt never says which
group a paper is in.

Model: deepseek-v4-pro with thinking mode off, temperature 0 and JSON output
(tested 2026-10-28). If an answer fails a check, the model is told what was
wrong and asked again, up to MAX_ATTEMPTS calls per task.

Every call is appended to outputs/llm_calls/claims.jsonl (never overwritten)
with the full messages, full raw response, parameters, returned model name and
system fingerprint. A task already done with the current prompt file is
skipped, so the script can be re-run or resumed.

Usage:
    python scripts/11_generate_claims.py pilot     # or: main, all
"""

import hashlib
import importlib.util
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
PROMPTS = ROOT / "prompts"
LOG_PATH = ROOT / "outputs" / "llm_calls" / "claims.jsonl"

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-pro"
PARAMS = {"temperature": 0, "thinking": {"type": "disabled"},
          "response_format": {"type": "json_object"}, "max_tokens": 1000}
MAX_ATTEMPTS = 3
DIRECTIONS = {"HIGHER", "LOWER", "NO_DIFFERENCE", "NOT_STATED"}
EXTRACT_KEYS = ["claim", "population", "intervention", "comparison", "outcome",
                "direction", "support_sentence"]


def load_script(filename):
    # Script names start with a digit, so they cannot be imported normally.
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s07 = load_script("07_fetch_pubmed.py")


# ------------------------------------------------------------------ inputs

def load_papers(which):
    """One row per paper: retracted trials and their controls."""
    rows = []
    for sample in (["pilot", "main"] if which == "all" else [which]):
        trials = pd.read_csv(PROCESSED / f"sample_{sample}.csv", dtype=str, keep_default_na=False)
        controls = pd.read_csv(PROCESSED / f"controls_{sample}.csv", dtype=str, keep_default_na=False)
        controls = controls.set_index("pmid")
        for _, t in trials.sort_values("draw_order", key=lambda s: s.astype(int)).iterrows():
            c = controls.loc[t["pmid"]]
            rows.append({"sample": sample, "group": "retracted", "pmid": t["pmid"],
                         "pair_pmid": t["pmid"], "abstract": t["pm_abstract"]})
            rows.append({"sample": sample, "group": "control", "pmid": c["control_pmid"],
                         "pair_pmid": t["pmid"], "abstract": c["control_abstract"]})
    return rows


def load_prompt(name):
    """A prompt file has a [system] and a [user] section."""
    path = PROMPTS / name
    text = path.read_text()
    system, user = text.split("[user]", 1)
    return {"file": name, "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "system": system.replace("[system]", "").strip(), "user": user.strip()}


def fill(template, values):
    # Plain replacement, not str.format: the prompts contain literal braces.
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


# ------------------------------------------------------------------ checks

def squash(text):
    # Only whitespace is normalized before the verbatim check.
    return re.sub(r"\s+", " ", text).strip()


def check_extract(parsed, paper):
    missing = [k for k in EXTRACT_KEYS if not str(parsed.get(k, "")).strip()]
    if missing:
        return f"These keys are missing or empty: {missing}."
    if parsed["direction"] not in DIRECTIONS:
        return f"direction must be one of {sorted(DIRECTIONS)}."
    if squash(parsed["support_sentence"]) not in squash(paper["abstract"]):
        return ("The support_sentence does not appear verbatim in the abstract. Copy one "
                "sentence from the abstract exactly, character for character, without a "
                "section label.")
    return None


# Each verify check and the answer that marks a problem.
VERIFY_CHECKS = {"direction_stated": "NO", "direction_matches": "NO",
                 "intervention_matches": "NO", "single_outcome": "NO",
                 "core_within_sentence": "NO", "population_comparison_supported": "NO",
                 "hedged_language": "YES"}


def check_verify(parsed, paper):
    bad = [k for k in VERIFY_CHECKS if parsed.get(k) not in ("YES", "NO")]
    if bad:
        return f"These keys must be YES or NO: {bad}."
    if not isinstance(parsed.get("problems", []), list):
        return "'problems' must be a list of strings."
    return None


def verify_values(extracted, paper):
    """Inputs of the verify call: the extraction plus the abstract."""
    fields = ["support_sentence", "claim", "population", "intervention",
              "comparison", "outcome", "direction"]
    return {**{f: extracted[f] for f in fields}, "abstract": paper["abstract"]}


def check_f1(parsed, paper):
    q = str(parsed.get("question", "")).strip()
    if not q:
        return "The key 'question' is missing or empty."
    if not q.endswith("?"):
        return "The question must end with a question mark."
    return None


# ----------------------------------------------------------------- calling

def done_key(pmid, task, prompt, values):
    # A task counts as done only for the same prompt file and the same inputs,
    # so a new extraction (e.g. after a prompt change) also redoes F1.
    return (pmid, task, prompt["sha256"], json.dumps(values, sort_keys=True))


def already_done():
    """Parsed answers of tasks that finished successfully, by done_key."""
    done = {}
    if LOG_PATH.exists():
        with open(LOG_PATH) as f:
            for line in f:
                r = json.loads(line)
                if r["status"] == "ok":
                    done[(r["pmid"], r["task"], r["prompt_sha256"],
                          json.dumps(r["input_values"], sort_keys=True))] = r["parsed"]
    return done


def post(messages, key):
    body = {"model": MODEL, "messages": messages, **PARAMS}
    r = requests.post(API_URL, json=body, timeout=180,
                      headers={"Authorization": f"Bearer {key}"})
    r.raise_for_status()
    return r.json()


def run_task(task, prompt, values, paper, check, key):
    """Call the model, check the answer, and retry with feedback if needed.
    Every attempt is logged. Returns the parsed answer or None."""
    messages = [{"role": "system", "content": prompt["system"]},
                {"role": "user", "content": fill(prompt["user"], values)}]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = post(messages, key)
        content = raw["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
            problem = check(parsed, paper)
        except json.JSONDecodeError:
            parsed, problem = None, "The answer was not valid JSON."
        status = "ok" if problem is None else ("failed" if attempt == MAX_ATTEMPTS else "retry")
        record = {
            "call_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pmid": paper["pmid"], "group": paper["group"], "sample": paper["sample"],
            "pair_pmid": paper["pair_pmid"], "task": task, "attempt": attempt,
            "prompt_file": prompt["file"], "prompt_sha256": prompt["sha256"],
            "model_requested": MODEL, "model_returned": raw.get("model"),
            "system_fingerprint": raw.get("system_fingerprint"),
            "parameters": PARAMS, "input_values": values,
            "messages": messages, "response": raw,
            "parsed": parsed, "status": status, "problem": problem,
        }
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        if problem is None:
            return parsed
        # Tell the model what was wrong and ask again in the same conversation.
        messages = messages + [{"role": "assistant", "content": content},
                               {"role": "user", "content": problem + " Return the corrected JSON object."}]
    return None


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which not in ("pilot", "main", "all"):
        sys.exit("Usage: python scripts/11_generate_claims.py pilot|main|all")
    load_dotenv(ROOT / ".env")
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        sys.exit("DEEPSEEK_API_KEY is not set in .env")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    extract_prompt = load_prompt("extract_claim.txt")
    f1_prompt = load_prompt("generate_f1.txt")
    verify_prompt = load_prompt("verify_claim.txt")
    done = already_done()
    papers = load_papers(which)
    print(f"Papers: {len(papers)}")

    counts = {"skipped": 0, "ok": 0, "failed": 0}
    for paper in papers:
        # Samples are cleaned of these in step 10; this is a safety check.
        if s07.is_retraction_notice(paper["abstract"]):
            print(f"  {paper['group']:9} {paper['pmid']}: abstract is a retraction notice, skipped")
            counts["failed"] += 1
            continue
        values = {"abstract": paper["abstract"]}
        k = done_key(paper["pmid"], "extract_claim", extract_prompt, values)
        if k in done:
            extracted = done[k]
            counts["skipped"] += 1
        else:
            extracted = run_task("extract_claim", extract_prompt, values,
                                 paper, check_extract, key)
            counts["ok" if extracted else "failed"] += 1
        if extracted is None:
            print(f"  {paper['group']:9} {paper['pmid']}: extraction FAILED")
            continue

        status = []
        values = verify_values(extracted, paper)
        if done_key(paper["pmid"], "verify_claim", verify_prompt, values) in done:
            counts["skipped"] += 1
        else:
            verified = run_task("verify_claim", verify_prompt, values, paper, check_verify, key)
            counts["ok" if verified else "failed"] += 1
            status.append("verify " + ("ok" if verified else "FAILED"))

        pico = {f: extracted[f] for f in ("population", "intervention", "comparison", "outcome")}
        if done_key(paper["pmid"], "generate_f1", f1_prompt, pico) in done:
            counts["skipped"] += 1
        else:
            question = run_task("generate_f1", f1_prompt, pico, paper, check_f1, key)
            counts["ok" if question else "failed"] += 1
            status.append("F1 " + ("ok" if question else "FAILED"))
        print(f"  {paper['group']:9} {paper['pmid']}: {', '.join(status) or 'already done'}")

    print(f"Tasks: {counts['ok']} done now, {counts['skipped']} already done, "
          f"{counts['failed']} failed. Log: {LOG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
