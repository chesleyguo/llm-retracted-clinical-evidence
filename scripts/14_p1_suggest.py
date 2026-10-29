"""Step 14: LLM-suggested P1 codes for review by the author.

For each trial in data/processed/p1_candidates.csv (step 13), deepseek-v4-pro
reads the P1 definition (taken from docs/codebook.md, not copied here), the
final claim and the retrieved reviews, and suggests YES / NO / UNCLEAR with
the reviews it rests on, a one-sentence rationale and, for each review,
whether it probably included the retracted trial. A trial with no review
found gets UNCLEAR without a model call.

Adds one row per new trial to data/processed/p1_review.csv. Rows already in
the table are never changed, so the author's p1 / p1_source / p1_note entries
are kept. Calls are logged in outputs/llm_calls/p1.jsonl.

Usage:
    python scripts/14_p1_suggest.py
"""

import importlib.util
import os
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
CODEBOOK = ROOT / "docs" / "codebook.md"
LLM_LOG = ROOT / "outputs" / "llm_calls" / "p1.jsonl"
CANDIDATES = PROCESSED / "p1_candidates.csv"
REVIEW_PATH = PROCESSED / "p1_review.csv"

CODES = {"YES", "NO", "UNCLEAR"}
# Thinking mode on for this judgment (it needs careful reading); thinking mode
# takes no temperature. Each paper is judged twice in separate calls, and the
# two answers are compared (p1_disagree).
P1_PARAMS = {"thinking": {"type": "enabled"}, "response_format": {"type": "json_object"},
             "max_tokens": 16000}
RUNS = ["p1_suggest_run1", "p1_suggest_run2"]
AUTHOR_COLUMNS = ["p1", "p1_source", "p1_note"]


def load_script(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s11 = load_script("11_generate_claims.py")


def p1_definition():
    """The P1 question and code table from the codebook, up to 'Procedure:'."""
    text = CODEBOOK.read_text()
    m = re.search(r"### P1\..*?\n(.*?)\nProcedure:", text, re.S)
    if not m:
        sys.exit("Could not find the P1 definition in docs/codebook.md")
    return m.group(1).strip()


def format_reviews(g):
    blocks = []
    for _, r in g.iterrows():
        blocks.append(
            f"[{r['rank']}] PMID {r['review_pmid']} | published {r['review_date']} | "
            f"{r['review_pub_types']}\n"
            f"published_after_retraction: {r['published_after_retraction']} | "
            f"cites_retracted: {r['cites_retracted']} (source: {r['cites_source']}) | "
            f"umbrella_review: {r['umbrella_review']}\n"
            f"Title: {r['review_title']}\nAbstract: {r['review_abstract']}")
    return "\n\n".join(blocks)


def make_check(review_pmids, umbrella_pmids):
    def check(parsed, paper):
        if parsed.get("suggested_p1") not in CODES:
            return f"suggested_p1 must be one of {sorted(CODES)}."
        basis = [str(x) for x in parsed.get("basis_pmids", [])]
        if not set(basis) <= review_pmids:
            return f"basis_pmids must be PMIDs from the list: {sorted(review_pmids)}."
        if parsed["suggested_p1"] in ("YES", "NO") and not basis:
            return ("A YES or NO needs at least one PMID in basis_pmids; if no review "
                    "addresses the claim, the answer is UNCLEAR.")
        if parsed["suggested_p1"] in ("YES", "NO") and set(basis) & umbrella_pmids:
            return ("Umbrella reviews can support UNCLEAR at most; remove them from "
                    "basis_pmids or answer UNCLEAR.")
        notes = parsed.get("inclusion_notes", [])
        noted = {str(n.get("pmid")) for n in notes}
        if noted != review_pmids:
            return f"Give exactly one inclusion note for each review: {sorted(review_pmids)}."
        if any(n.get("likely_includes_retracted") not in CODES for n in notes):
            return "likely_includes_retracted must be YES, NO or UNCLEAR."
        if not str(parsed.get("rationale", "")).strip():
            return "rationale is missing."
        return None
    return check


def main():
    load_dotenv(ROOT / ".env")
    key = os.environ["DEEPSEEK_API_KEY"]
    cand = pd.read_csv(CANDIDATES, dtype=str, keep_default_na=False)
    existing = (pd.read_csv(REVIEW_PATH, dtype=str, keep_default_na=False)
                if REVIEW_PATH.exists() else None)
    seen = set(existing["pmid"]) if existing is not None else set()

    sample = pd.read_csv(PROCESSED / "sample_main.csv", dtype=str, keep_default_na=False).set_index("pmid")
    prompt = s11.load_prompt("p1_suggest.txt")
    definition = p1_definition()
    done = s11.already_done(LLM_LOG)

    rows = []
    for pmid, g in cand.groupby("retracted_pmid", sort=False):
        if pmid in seen:
            continue
        g = g[g["rank"] != ""]
        first = cand[cand["retracted_pmid"] == pmid].iloc[0]
        base = {"pmid": pmid, "claim": first["claim"], "trial_published": first["trial_published"],
                "retraction_date": first["retraction_date"], "query_level": first["query_level"],
                "query": first["query"], "n_results": first["n_results"],
                "block_dropped": first["block_dropped"],
                "reviews": "\n".join(
                    f"{r['review_pmid']} | {r['review_date'][:4]} | after_retraction={r['published_after_retraction']} | "
                    f"cites={r['cites_retracted']} ({r['cites_source']}) | {r['review_title']}"
                    for _, r in g.iterrows())}
        if g.empty:
            rows.append({**base, "suggested_p1": "UNCLEAR", "suggested_p1_run2": "UNCLEAR",
                         "p1_disagree": "FALSE", "basis_pmids": "", "basis_pmids_run2": "",
                         "rationale": "No systematic review, meta-analysis or guideline was found.",
                         "rationale_run2": "", "inclusion_notes": ""})
            print(f"  {pmid}: no reviews -> UNCLEAR")
            continue

        values = {"p1_definition": definition, "title": sample.loc[pmid, "pm_title"],
                  "published": first["trial_published"], "retracted": first["retraction_date"],
                  "claim": first["claim"], "reviews": format_reviews(g)}
        paper = {"pmid": pmid, "group": "retracted", "sample": "main", "pair_pmid": pmid}
        check = make_check(set(g["review_pmid"]), set(g.loc[g["umbrella_review"] == "YES", "review_pmid"]))
        answers = []
        for task in RUNS:
            parsed = done.get(s11.done_key(pmid, task, prompt, values))
            if parsed is not None and check(parsed, paper) is not None:
                parsed = None   # logged earlier but fails the current checks: ask again
            if parsed is None:
                parsed = s11.run_task(task, prompt, values, paper, check, key, LLM_LOG, P1_PARAMS)
            answers.append(parsed)
        if any(a is None for a in answers):
            print(f"  {pmid}: suggestion FAILED")
            continue
        a1, a2 = answers
        rows.append({**base, "suggested_p1": a1["suggested_p1"],
                     "suggested_p1_run2": a2["suggested_p1"],
                     "p1_disagree": "TRUE" if a1["suggested_p1"] != a2["suggested_p1"] else "FALSE",
                     "basis_pmids": "; ".join(str(x) for x in a1["basis_pmids"]),
                     "basis_pmids_run2": "; ".join(str(x) for x in a2["basis_pmids"]),
                     "rationale": a1["rationale"], "rationale_run2": a2["rationale"],
                     "inclusion_notes": "\n".join(
                         f"{n['pmid']}: {n['likely_includes_retracted']} - {n['note']}"
                         for n in a1["inclusion_notes"])})
        print(f"  {pmid}: {a1['suggested_p1']} / {a2['suggested_p1']}")

    new = pd.DataFrame(rows)
    for col in AUTHOR_COLUMNS:
        new[col] = ""
    table = new if existing is None else pd.concat([existing, new], ignore_index=True)
    # Disagreements first; reordering keeps the author's entries.
    table = table.sort_values("p1_disagree", ascending=False, kind="stable")
    table.to_csv(REVIEW_PATH, index=False)
    print(f"Added {len(new)} rows to {REVIEW_PATH.relative_to(ROOT)} (now {len(table)})")


if __name__ == "__main__":
    main()
