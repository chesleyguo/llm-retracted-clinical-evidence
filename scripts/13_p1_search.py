"""Step 13: find reviews and guidelines for P1 (independent support).

For each retracted trial in the main sample (codebook P1; analysis plan,
"P1: independent support"):
1. deepseek-v4-pro writes a PubMed search (prompts/p1_query.txt) from the
   final claim in data/processed/claims_final.csv: a three-block query
   (intervention, condition, outcome) and a broad two-block query.
2. The script adds fixed filters: publication type Systematic Review,
   Meta-Analysis, Guideline or Practice Guideline; published on or after the
   trial's PubMed publication date; not a Retracted Publication. It takes the
   top 5 by PubMed's relevance ranking (Best Match). If the query finds
   nothing, the broad query is used.
3. For each review: whether it was published after the trial's retraction,
   and whether it cites the trial (PubMed reference list or OpenAlex
   referenced_works; YES if either shows it, NO if a list exists without it,
   UNKNOWN if neither source has a reference list).

PubMed, OpenAlex and model responses are cached (data/raw/pubmed_p1/,
data/raw/openalex_p1/, outputs/llm_calls/p1.jsonl), so re-runs are
reproducible and resumable. Writes data/processed/p1_candidates.csv (one row
per trial and review).

Usage:
    python scripts/13_p1_search.py --limit 10    # first 10 trials by draw order
    python scripts/13_p1_search.py               # all main-sample trials
"""

import argparse
import importlib.util
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
SEARCH_CACHE = ROOT / "data" / "raw" / "pubmed_p1" / "esearch"
FETCH_CACHE = ROOT / "data" / "raw" / "pubmed_p1" / "efetch"
OPENALEX_CACHE = ROOT / "data" / "raw" / "openalex_p1"
LLM_LOG = ROOT / "outputs" / "llm_calls" / "p1.jsonl"
OUT_PATH = PROCESSED / "p1_candidates.csv"

TOP_N = 5
REVIEW_TYPES = ["Systematic Review", "Meta-Analysis", "Guideline", "Practice Guideline"]
# A review of reviews can depend on the retracted trial without citing it.
UMBRELLA = re.compile(r"\bumbrella\b|overview of (systematic )?reviews|review of (systematic )?reviews"
                      r"|meta-analys[ie]s of meta-analys[ie]s", re.IGNORECASE)
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def load_script(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s09 = load_script("09_match_controls.py")
s11 = load_script("11_generate_claims.py")


# -------------------------------------------------------------------- dates

def parse_pubmed_date(text):
    """'2015 May 3', '2004 Jan-Feb', '2016' -> earliest date in that period.
    Taking the first day of the period means a review dated only by month or
    year counts as published after the retraction only if the whole period
    is after it."""
    parts = text.replace("-", " ").split()
    year = int(parts[0])
    month = MONTHS.get(parts[1][:3].lower(), 1) if len(parts) > 1 else 1
    day = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
    return date(year, month, day)


def review_date(article):
    """Electronic publication date if PubMed has one, else the issue date."""
    art = article.find("MedlineCitation/Article")
    e = art.find("ArticleDate")
    if e is not None and e.findtext("Year"):
        return date(int(e.findtext("Year")), int(e.findtext("Month") or 1), int(e.findtext("Day") or 1))
    pd_ = art.find("Journal/JournalIssue/PubDate")
    text = pd_.findtext("MedlineDate") or " ".join(
        x for x in (pd_.findtext("Year"), pd_.findtext("Month"), pd_.findtext("Day")) if x)
    return parse_pubmed_date(text)


# ------------------------------------------------------------------- search

def check_query(parsed, paper):
    for k in ("query", "broad_query"):
        q = str(parsed.get(k, "")).strip()
        if not q:
            return f"'{k}' is missing or empty."
        if re.search(r"\[pt\]|\[dp\]|systematic review|meta-analys", q, re.IGNORECASE):
            return f"'{k}' must not contain publication types, dates or review words."
        if q.count("(") != q.count(")"):
            return f"'{k}' has unbalanced parentheses."
    return None


def esearch_top(query):
    """Top results by PubMed relevance, cached by query text."""
    path = SEARCH_CACHE / f"{s09.cache_name(query)}.json"
    if not path.exists():
        r = s09.post(s09.EUTILS + "esearch.fcgi", {**s09.BASE_PARAMS, "db": "pubmed", "term": query,
                                                    "sort": "relevance", "retmax": TOP_N,
                                                    "retmode": "json"})
        result = r.json()["esearchresult"]
        if "ERROR" in result:
            sys.exit(f"esearch error for {query!r}: {result}")
        warnings = (result.get("errorlist", {}).get("phrasesnotfound", [])
                    + result.get("warninglist", {}).get("quotedphrasesnotfound", []))
        s09.write_new(path, json.dumps({
            "query": query, "sort": "relevance",
            "searched_at_utc": pd.Timestamp.now("UTC").isoformat(timespec="seconds"),
            "count": int(result["count"]), "pmids": result["idlist"],
            "phrases_not_found": warnings}, indent=1).encode())
    return json.loads(path.read_text())


def top_level_blocks(query):
    """Split 'A AND B AND C' at top-level ANDs (outside parentheses)."""
    blocks, depth, start = [], 0, 0
    for i, ch in enumerate(query):
        depth += ch == "("
        depth -= ch == ")"
        if depth == 0 and query[i:i + 5] == " AND ":
            blocks.append(query[start:i])
            start = i + 5
    blocks.append(query[start:])
    # A query wrapped in one pair of parentheses has a single top-level block.
    if len(blocks) == 1 and query.startswith("(") and query.endswith(")"):
        return top_level_blocks(query[1:-1])
    return blocks


def dropped_block(topic_query, not_found):
    """YES if PubMed found none of the terms of some concept block, which
    would silently drop that block and widen the search."""
    missing = {m.lower() for m in not_found}
    for block in top_level_blocks(topic_query):
        terms = re.findall(r'"[^"]+"\[\w+\]|[\w*-]+\[\w+\]', block)
        if terms and all(t.lower() in missing for t in terms):
            return "YES"
    return "NO"


def full_query(topic_query, since):
    types = " OR ".join(f'"{t}"[pt]' for t in REVIEW_TYPES)
    return (f"({topic_query}) AND ({types}) AND {since:%Y/%m/%d}:3000/12/31[dp] "
            f'NOT "Retracted Publication"[pt]')


def efetch_cached(pmids):
    key = ",".join(pmids)
    path = FETCH_CACHE / f"{s09.cache_name(key)}.xml"
    if not path.exists():
        r = s09.post(s09.EUTILS + "efetch.fcgi", {**s09.BASE_PARAMS, "db": "pubmed",
                                                   "retmode": "xml", "id": key})
        ET.fromstring(r.content)
        s09.write_new(path, r.content)
    return {a.findtext("MedlineCitation/PMID"): a for a in ET.parse(path).getroot().iter("PubmedArticle")}


def openalex_work(pmid):
    """OpenAlex record for a PMID (id and referenced works), cached; None if
    OpenAlex has no record."""
    path = OPENALEX_CACHE / f"{pmid}.json"
    if not path.exists():
        r = requests.get(f"https://api.openalex.org/works/pmid:{pmid}", timeout=60,
                         params={"select": "id,doi,publication_date,referenced_works,referenced_works_count",
                                 "mailto": os.environ.get("CONTACT_EMAIL", "")})
        time.sleep(0.2)
        if r.status_code == 404:
            body = {"not_found": True}
        else:
            r.raise_for_status()
            body = r.json()
        body["retrieved_at_utc"] = pd.Timestamp.now("UTC").isoformat(timespec="seconds")
        s09.write_new(path, json.dumps(body, indent=1).encode())
    body = json.loads(path.read_text())
    return None if body.get("not_found") else body


def cites_retracted(article, review_pmid, trial_pmid, trial_openalex_id):
    """YES / NO / UNKNOWN and the sources behind it."""
    found, informative = [], []
    refs = article.findall("PubmedData/ReferenceList/Reference")
    if refs:
        informative.append("pubmed")
        ids = {i.text for r in refs for i in r.findall("ArticleIdList/ArticleId")
               if i.get("IdType") == "pubmed"}
        if trial_pmid in ids:
            found.append("pubmed")
    work = openalex_work(review_pmid)
    if work and work.get("referenced_works"):
        informative.append("openalex")
        if trial_openalex_id and trial_openalex_id in work["referenced_works"]:
            found.append("openalex")
    if found:
        return "YES", "+".join(found)
    if informative:
        return "NO", "+".join(informative)
    return "UNKNOWN", "none"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only the first N trials by draw order")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    key = os.environ["DEEPSEEK_API_KEY"]

    final = pd.read_csv(PROCESSED / "claims_final.csv", dtype=str, keep_default_na=False)
    final = final[(final["sample"] == "main") & (final["group"] == "retracted")].set_index("pmid")
    sample = pd.read_csv(PROCESSED / "sample_main.csv", dtype=str, keep_default_na=False)
    sample = sample.sort_values("draw_order", key=lambda s: s.astype(int))
    sample = sample[sample["pmid"].isin(final.index)]
    if args.limit:
        sample = sample.head(args.limit)

    prompt = s11.load_prompt("p1_query.txt")
    done = s11.already_done(LLM_LOG)
    LLM_LOG.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for _, t in sample.iterrows():
        pmid = t["pmid"]
        claim = final.loc[pmid, "claim"]
        values = {"claim": claim}
        paper = {"pmid": pmid, "group": "retracted", "sample": "main", "pair_pmid": pmid}
        parsed = done.get(s11.done_key(pmid, "p1_query", prompt, values))
        if parsed is None:
            parsed = s11.run_task("p1_query", prompt, values, paper, check_query, key, LLM_LOG)
        if parsed is None:
            print(f"  {pmid}: query generation FAILED")
            continue

        since = parse_pubmed_date(t["pm_pub_date"])
        retracted_on = date.fromisoformat(t["retraction_date"])
        level, search = "query", esearch_top(full_query(parsed["query"], since))
        if search["count"] == 0:
            level, search = "broad_query", esearch_top(full_query(parsed["broad_query"], since))
        block_dropped = dropped_block(parsed[level], search["phrases_not_found"])

        trial_work = openalex_work(pmid)
        trial_oa = trial_work["id"] if trial_work else None
        base = {"retracted_pmid": pmid, "claim": claim, "trial_published": since.isoformat(),
                "retraction_date": retracted_on.isoformat(), "query_level": level,
                "query": search["query"], "n_results": search["count"],
                "phrases_not_found": "; ".join(search["phrases_not_found"]),
                "block_dropped": block_dropped,
                "searched_at_utc": search["searched_at_utc"]}
        if not search["pmids"]:
            rows.append({**base, "rank": ""})
            print(f"  {pmid}: no reviews found")
            continue
        articles = efetch_cached(search["pmids"])
        for rank, rp in enumerate(search["pmids"], 1):
            a = articles[rp]
            art = a.find("MedlineCitation/Article")
            cites, source = cites_retracted(a, rp, pmid, trial_oa)
            rdate = review_date(a)
            rows.append({**base, "rank": rank, "review_pmid": rp,
                         "review_title": "".join(art.find("ArticleTitle").itertext()).strip(),
                         "review_date": rdate.isoformat(),
                         "review_pub_types": "; ".join(x.text for x in art.findall("PublicationTypeList/PublicationType")),
                         "published_after_retraction": "YES" if rdate > retracted_on else "NO",
                         "cites_retracted": cites, "cites_source": source,
                         "umbrella_review": "YES" if UMBRELLA.search(
                             "".join(art.find("ArticleTitle").itertext()) + " " + "".join(
                                 "".join(p.itertext()) for p in art.findall("Abstract/AbstractText"))) else "NO",
                         "review_abstract": "\n".join(
                             (f"{p.get('Label')}: " if p.get("Label") else "") + "".join(p.itertext()).strip()
                             for p in art.findall("Abstract/AbstractText"))})
        print(f"  {pmid}: {level}, {search['count']} results, top {len(search['pmids'])} kept")

    out = pd.DataFrame(rows)
    # Keep rows of trials not processed in this run (e.g. an earlier --limit run).
    if OUT_PATH.exists():
        old = pd.read_csv(OUT_PATH, dtype=str, keep_default_na=False)
        out = pd.concat([old[~old["retracted_pmid"].isin(set(out["retracted_pmid"]))], out.astype(str)])
    out.to_csv(OUT_PATH, index=False)
    print(f"Saved {OUT_PATH.relative_to(ROOT)} ({out['retracted_pmid'].nunique()} trials)")


if __name__ == "__main__":
    main()
