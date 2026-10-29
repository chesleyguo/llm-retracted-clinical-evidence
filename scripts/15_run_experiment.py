"""Step 15: run the experiment calls to the tested models.

For every approved pair in data/processed/claims_final.csv (pair_ready =
TRUE) of the chosen sample, each paper is asked about in 3 framings x 3
conditions, by each of the 3 tested models (analysis plan, "Models and
conditions"):

  F1 clinical question   F2 paper question   F3 status question
  C0 prompt only
  C1 database record before the question (prompts/c1_*.txt); for F1 the
     record is introduced by a sentence naming the article
  C2 web search enabled (OpenAI web_search, Anthropic web_search_20260209,
     Google Search grounding)

No system prompt and no sampling parameters are set: each API's defaults
are used (Anthropic requires max_tokens, set to 16000). Anthropic's refusal
fallback is not used; a refusal is recorded as returned (stop_reason).

Every call is appended to outputs/responses/<sample>.jsonl, never
overwritten: ids, framing, condition, model requested and returned, timestamp,
full prompt, parameters, full raw response(s), response text, auto-attached
citations (C2), usage, latency, status. A call that already succeeded is
skipped, so the script can be re-run or resumed; failed calls are retried on
the next run.

Calls are made in a random order (seed 2026, logged as order_index), with at
most 4 concurrent requests per provider.

Usage:
    python scripts/15_run_experiment.py pilot --pairs 2    # smoke test
    python scripts/15_run_experiment.py pilot
"""

import argparse
import importlib.util
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
PROMPTS = ROOT / "prompts"
OUT_DIR = ROOT / "outputs" / "responses"

SEED = 2026
MODELS = {"openai": "gpt-5.6-luna", "anthropic": "claude-sonnet-5-5",
          "google": "gemini-3.5-flash-lite"}
ANTHROPIC_MAX_TOKENS = 16000
FRAMINGS = ["F1", "F2", "F3"]
CONDITIONS = ["C0", "C1", "C2"]
WORKERS_PER_PROVIDER = 4
MAX_ATTEMPTS = 4
WRITE_LOCK = threading.Lock()


def load_script(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s12 = load_script("12_build_claims_review.py")


# ------------------------------------------------------------------ prompts

def template(name):
    return (PROMPTS / name).read_text().strip()


def fill(text, values):
    for k, v in values.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def load_papers(sample, n_pairs):
    """Approved pairs of the sample, in draw order, with what the prompts need."""
    final = pd.read_csv(PROCESSED / "claims_final.csv", dtype=str, keep_default_na=False)
    final = final[(final["sample"] == sample) & (final["pair_ready"] == "TRUE")]
    trials = pd.read_csv(PROCESSED / f"sample_{sample}.csv", dtype=str,
                         keep_default_na=False).set_index("pmid")
    order = trials.loc[final["pair_pmid"].unique(), "draw_order"].astype(int).sort_values()
    pairs = list(order.index[:n_pairs] if n_pairs else order.index)
    final = final[final["pair_pmid"].isin(pairs)]
    meta = s12.metadata(set(final["pmid"]))

    papers = []
    for pair in pairs:
        for _, row in final[final["pair_pmid"] == pair].sort_values("group", ascending=False).iterrows():
            m = meta[row["pmid"]]
            title, _ = s12.clean_title(m["raw_title"])
            article = {"title": title, "first_author": m["first_author"],
                       "journal": s12.clean_journal(m["raw_journal"]), "year": m["year"]}
            if row["group"] == "retracted":
                t = trials.loc[row["pmid"]]
                record = fill(template("c1_retracted.txt"),
                              {"year": t["retraction_date"][:4], "reasons": t["include_reasons"]})
            else:
                record = template("c1_control.txt")
            papers.append({"sample": sample, "pair_pmid": pair, "pmid": row["pmid"],
                           "group": row["group"], "f1": row["f1_question"],
                           "f2": row["f2_prompt"], "f3": row["f3_prompt"],
                           "c1_record": record,
                           "c1_f1_article": fill(template("c1_f1_article.txt"), article)})
    return papers


def build_prompt(paper, framing, condition):
    question = paper[framing.lower()]
    if condition != "C1":
        return question
    if framing == "F1":   # the F1 question does not name the article
        return f"{paper['c1_f1_article']} {paper['c1_record']}\n\n{question}"
    return f"{paper['c1_record']}\n\n{question}"


# ---------------------------------------------------------------- providers

def call_openai(prompt, web):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
    params = {"model": MODELS["openai"]}
    if web:
        params["tools"] = [{"type": "web_search"}]
        params["include"] = ["web_search_call.action.sources"]
    r = client.responses.create(input=prompt, **params)
    raw = r.model_dump(mode="json")
    citations = []
    for item in r.output:
        if item.type == "message":
            for part in item.content:
                for a in getattr(part, "annotations", None) or []:
                    if a.type == "url_citation":
                        citations.append({"title": a.title, "url": a.url, "kind": "inline citation"})
        elif item.type == "web_search_call":
            for src in (getattr(item.action, "sources", None) or []):
                citations.append({"title": getattr(src, "title", None), "url": src.url,
                                  "kind": "search source"})
    return {"parameters": params, "raw": [raw], "text": r.output_text,
            "model_returned": r.model, "stop_reason": r.status,
            "usage": raw.get("usage"), "auto_citations": citations}


def call_anthropic(prompt, web):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0)
    params = {"model": MODELS["anthropic"], "max_tokens": ANTHROPIC_MAX_TOKENS}
    if web:
        params["tools"] = [{"type": "web_search_20260209", "name": "web_search"}]
    messages = [{"role": "user", "content": prompt}]
    raws, responses = [], []
    for _ in range(6):   # a server-tool loop can pause; resume up to 5 times
        r = client.messages.create(messages=messages, **params)
        raws.append(r.model_dump(mode="json"))
        responses.append(r)
        if r.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": r.content}]
    text, citations = [], []
    for r in responses:
        for b in r.content:
            if b.type == "text":
                text.append(b.text)
                for c in b.citations or []:
                    citations.append({"title": getattr(c, "title", None), "url": getattr(c, "url", None),
                                      "kind": "inline citation"})
            elif b.type == "web_search_tool_result" and isinstance(b.content, list):
                for res in b.content:
                    citations.append({"title": res.title, "url": res.url, "kind": "search source"})
    last = responses[-1]
    return {"parameters": params, "raw": raws, "text": "".join(text),
            "model_returned": last.model, "stop_reason": last.stop_reason,
            "usage": [x.get("usage") for x in raws], "auto_citations": citations}


def call_google(prompt, web):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    params = {"model": MODELS["google"]}
    config = None
    if web:
        config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        params["config"] = {"tools": [{"google_search": {}}]}
    r = client.models.generate_content(model=MODELS["google"], contents=prompt, config=config)
    raw = r.model_dump(mode="json", exclude_none=True)
    citations = []
    cand = r.candidates[0] if r.candidates else None
    gm = getattr(cand, "grounding_metadata", None) if cand else None
    for ch in (gm.grounding_chunks or []) if gm else []:
        if ch.web:
            citations.append({"title": ch.web.title, "url": ch.web.uri, "kind": "grounding source"})
    finish = str(cand.finish_reason) if cand and cand.finish_reason else None
    return {"parameters": params, "raw": [raw], "text": r.text or "",
            "model_returned": r.model_version, "stop_reason": finish,
            "usage": raw.get("usage_metadata"), "auto_citations": citations}


CALLERS = {"openai": call_openai, "anthropic": call_anthropic, "google": call_google}


# ------------------------------------------------------------------ running

def done_keys(path):
    keys = set()
    if path.exists():
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if r["status"] == "ok":
                    keys.add((r["pmid"], r["framing"], r["condition"], r["provider"], r["run_index"]))
    return keys


def run_one(task, out_path):
    paper, framing, condition, provider, run_index, order_index = task
    prompt = build_prompt(paper, framing, condition)
    started = time.time()
    result, error = None, None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = CALLERS[provider](prompt, web=(condition == "C2"))
            break
        except Exception as e:   # network errors, rate limits, server errors
            error = f"{type(e).__name__}: {str(e)[:500]}"
            if attempt < MAX_ATTEMPTS:
                time.sleep(15 * attempt)
    record = {
        "call_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sample": paper["sample"], "pair_pmid": paper["pair_pmid"], "pmid": paper["pmid"],
        "group": paper["group"], "framing": framing, "condition": condition,
        "provider": provider, "model_requested": MODELS[provider], "run_index": run_index,
        "order_index": order_index, "seed": SEED, "prompt": prompt,
        "status": "ok" if result else "error", "error": None if result else error,
        "attempts": attempt, "latency_s": round(time.time() - started, 1),
    }
    if result:
        record.update({"model_returned": result["model_returned"],
                       "parameters": result["parameters"], "stop_reason": result["stop_reason"],
                       "response_text": result["text"], "auto_citations": result["auto_citations"],
                       "usage": result["usage"], "response_raw": result["raw"]})
    with WRITE_LOCK, open(out_path, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  {order_index:>4} {provider:9} {paper['group']:9} {paper['pmid']} {framing} {condition}: "
          f"{record['status']}" + (f" ({result['stop_reason']})" if result else f" {error[:80]}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample", choices=["pilot", "main"])
    ap.add_argument("--pairs", type=int, help="only the first N approved pairs (smoke test)")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{args.sample}.jsonl"

    papers = load_papers(args.sample, None)
    tasks = [(p, f, c, prov, 1) for p in papers for f in FRAMINGS for c in CONDITIONS for prov in MODELS]
    # Random call order (seed 2026), so no condition or model is run in one
    # block of time. The order is computed on all calls of the sample, so a
    # smoke test (--pairs) and the full run share it; calls already done are
    # skipped.
    order = np.random.default_rng(SEED).permutation(len(tasks))
    tasks = [(*tasks[i], rank) for rank, i in enumerate(order, 1)]
    if args.pairs:
        keep = {p["pair_pmid"] for p in load_papers(args.sample, args.pairs)}
        tasks = [t for t in tasks if t[0]["pair_pmid"] in keep]
        papers = [p for p in papers if p["pair_pmid"] in keep]
    done = done_keys(out_path)
    todo = [t for t in tasks if (t[0]["pmid"], t[1], t[2], t[3], t[4]) not in done]
    print(f"Papers: {len(papers)}; calls: {len(tasks)}; already done: {len(tasks) - len(todo)}; "
          f"to run: {len(todo)}")

    pools = {prov: ThreadPoolExecutor(WORKERS_PER_PROVIDER) for prov in MODELS}
    futures = [pools[t[3]].submit(run_one, t, out_path) for t in todo]
    for fut in futures:
        fut.result()
    for pool in pools.values():
        pool.shutdown()
    left = len(tasks) - len(done_keys(out_path) & {(t[0]["pmid"], t[1], t[2], t[3], t[4]) for t in tasks})
    print(f"Finished. Calls without a successful record: {left}")


if __name__ == "__main__":
    main()
