"""Step 07: fetch PubMed records and apply criterion 6 (clinical trial).

1. Fetches every PMID in data/processed/retractions_eligible.csv with
   E-utilities efetch (XML, 200 PMIDs per request). Each response is cached as
   data/raw/pubmed/efetch_<timestamp>.xml, and the PMIDs requested are logged in
   data/raw/pubmed/fetch_log.jsonl. Cached files are never overwritten; on a
   re-run, PMIDs already requested are skipped (resumable).
2. Parses the cached XML into data/processed/pubmed_metadata.csv.
3. Keeps papers whose publication types include Clinical Trial or one of its
   subtypes (analysis_plan, criterion 6) and writes
   data/processed/retracted_trials.csv.
4. Adds the step-6 rows to results/filter_flow.csv and writes a descriptive
   summary to results/07_trials_summary.txt.

Usage:
    python scripts/07_fetch_pubmed.py
"""

import json
import os
import time
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
CACHE_DIR = ROOT / "data" / "raw" / "pubmed"
FETCH_LOG = CACHE_DIR / "fetch_log.jsonl"
FLOW_PATH = ROOT / "results" / "filter_flow.csv"
SUMMARY_PATH = ROOT / "results" / "07_trials_summary.txt"

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
BATCH_SIZE = 200
MAX_TRIES = 4

# Clinical Trial (V03.175.250) and its subtypes, as listed in
# docs/analysis_plan.md, criterion 6. Clinical Trial Protocol and the
# veterinary trial types are not in this subtree.
TRIAL_TYPES = {
    "Clinical Trial",
    "Adaptive Clinical Trial",
    "Clinical Trial, Phase I",
    "Clinical Trial, Phase II",
    "Clinical Trial, Phase III",
    "Clinical Trial, Phase IV",
    "Controlled Clinical Trial",
    "Randomized Controlled Trial",
    "Equivalence Trial",
    "Human Challenge Trials",
    "Pragmatic Clinical Trial",
}


# ---------------------------------------------------------------- fetching

def already_requested():
    if not FETCH_LOG.exists():
        return set()
    done = set()
    with open(FETCH_LOG) as f:
        for line in f:
            done.update(json.loads(line)["pmids"])
    return done


def fetch_batch(pmids, params, pause):
    # POST is used because 200 PMIDs make a long URL. Retry with a growing
    # wait on rate-limit (429) or server errors.
    for attempt in range(1, MAX_TRIES + 1):
        r = requests.post(EFETCH_URL, data={**params, "id": ",".join(pmids)}, timeout=120)
        if r.status_code == 200:
            ET.fromstring(r.content)  # fail here, not later, if the XML is broken
            return r.content
        if attempt == MAX_TRIES or r.status_code not in (429, 500, 502, 503, 504):
            r.raise_for_status()
        time.sleep(pause * 5 * attempt)


def fetch_all(pmids):
    load_dotenv(ROOT / ".env")
    params = {"db": "pubmed", "retmode": "xml",
              "tool": "llm-retracted-clinical-evidence",
              "email": os.getenv("CONTACT_EMAIL", "")}
    api_key = os.getenv("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    # NCBI allows 3 requests/second without an API key and 10 with one; stay
    # below both.
    pause = 0.15 if api_key else 0.4

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    todo = [p for p in pmids if p not in already_requested()]
    batches = [todo[i:i + BATCH_SIZE] for i in range(0, len(todo), BATCH_SIZE)]
    print(f"PMIDs: {len(pmids)}; already requested: {len(pmids) - len(todo)}; "
          f"batches to fetch: {len(batches)}")

    for i, batch in enumerate(batches, 1):
        content = fetch_batch(batch, params, pause)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = CACHE_DIR / f"efetch_{stamp}.xml"
        # Write to .part and rename, then log: an interrupted run never leaves
        # a logged batch without its file.
        part = path.with_suffix(".xml.part")
        part.write_bytes(content)
        part.rename(path)
        with open(FETCH_LOG, "a") as f:
            f.write(json.dumps({"file": path.name, "fetched_at_utc": stamp,
                                "n": len(batch), "pmids": batch}) + "\n")
        print(f"  batch {i}/{len(batches)}: {len(batch)} PMIDs -> {path.name}")
        time.sleep(pause)


# ----------------------------------------------------------------- parsing

def text_of(elem):
    # Titles and abstracts can contain markup such as <i> or <sup>.
    return "".join(elem.itertext()).strip() if elem is not None else ""


def parse_date(article):
    pub_date = article.find("MedlineCitation/Article/Journal/JournalIssue/PubDate")
    if pub_date is None:
        return ""
    medline_date = pub_date.findtext("MedlineDate")
    if medline_date:  # free text such as "2004 Jan-Feb"
        return medline_date
    parts = [pub_date.findtext(k) for k in ("Year", "Month", "Day")]
    return " ".join(p for p in parts if p)


def parse_article(article):
    citation = article.find("MedlineCitation")
    art = citation.find("Article")

    abstract_parts = []
    for part in art.findall("Abstract/AbstractText"):
        label = part.get("Label")
        text = text_of(part)
        abstract_parts.append(f"{label}: {text}" if label else text)

    authors = []
    for a in art.findall("AuthorList/Author"):
        if a.findtext("CollectiveName"):
            authors.append(a.findtext("CollectiveName"))
        else:
            authors.append(" ".join(x for x in (a.findtext("LastName"), a.findtext("Initials")) if x))

    mesh = []
    for heading in citation.findall("MeshHeadingList/MeshHeading"):
        descriptor = heading.find("DescriptorName")
        # A heading is a major topic if the descriptor or any of its
        # qualifiers is marked MajorTopicYN="Y". Major topics end with "*".
        major = descriptor.get("MajorTopicYN") == "Y" or any(
            q.get("MajorTopicYN") == "Y" for q in heading.findall("QualifierName"))
        mesh.append(descriptor.text + ("*" if major else ""))

    pub_types = [pt.text for pt in art.findall("PublicationTypeList/PublicationType")]
    return {
        "pmid": citation.findtext("PMID"),
        "pm_title": text_of(art.find("ArticleTitle")),
        "pm_abstract": "\n".join(abstract_parts),
        "pm_journal": art.findtext("Journal/Title", ""),
        "pm_pub_date": parse_date(article),
        "pm_authors": "; ".join(authors),
        "pm_pub_types": "; ".join(pub_types),
        "pm_mesh": "; ".join(mesh),
        "has_abstract": bool(abstract_parts),
        "pubmed_flagged": "Retracted Publication" in pub_types,
        "is_trial": bool(TRIAL_TYPES & set(pub_types)),
    }


def parse_cache():
    rows = {}
    for path in sorted(CACHE_DIR.glob("efetch_*.xml")):
        for article in ET.parse(path).getroot().iter("PubmedArticle"):
            row = parse_article(article)
            rows[row["pmid"]] = row  # a later fetch of the same PMID wins
    return pd.DataFrame(rows.values())


# ----------------------------------------------------------------- summary

def summarize(trials, eligible, meta):
    lines = []
    out = lines.append
    out(f"Clinical trials (criterion 6): {len(trials)}")

    # Cross-check with Retraction Watch ArticleType "Clinical Study", among the
    # eligible papers that have a PubMed record.
    both = eligible.merge(meta[["pmid", "is_trial"]], on="pmid")
    rw = both["rw_clinical_study"]
    pm = both["is_trial"]
    out(f"\nCross-check among {len(both)} eligible papers with a PubMed record:")
    out(f"  PubMed trial and RW Clinical Study: {(pm & rw).sum()}")
    out(f"  PubMed trial only:                  {(pm & ~rw).sum()}")
    out(f"  RW Clinical Study only:             {(~pm & rw).sum()}")
    out(f"  Neither:                            {(~pm & ~rw).sum()}")

    out(f"\npubmed_flagged = False among trials: {(~trials['pubmed_flagged']).sum()} "
        f"of {len(trials)}")
    out(f"Trials with an abstract: {trials['has_abstract'].sum()} "
        f"({trials['has_abstract'].mean():.1%})")

    out("\nTrials by retraction year:")
    years = pd.to_datetime(trials["retraction_date"]).dt.year
    for year, n in sorted(Counter(years).items()):
        out(f"  {year}  {n:>5}")

    for col in ["p2_category", "strength"]:
        out(f"\n{col}:")
        for value, n in trials[col].value_counts().items():
            out(f"  {n:>5}  {n / len(trials):6.1%}  {value}")

    out("\nTrial publication types (a paper can have several):")
    types = Counter(t for ts in trials["pm_pub_types"] for t in ts.split("; ") if t in TRIAL_TYPES)
    for t, n in types.most_common():
        out(f"  {n:>5}  {t}")

    text = "\n".join(lines) + "\n"
    SUMMARY_PATH.write_text(text)
    print(text)
    print(f"Saved summary to {SUMMARY_PATH.relative_to(ROOT)}")


def main():
    eligible = pd.read_csv(PROCESSED / "retractions_eligible.csv", dtype=str,
                           keep_default_na=False)
    eligible["rw_clinical_study"] = eligible["rw_clinical_study"] == "True"
    pmids = eligible["pmid"].tolist()

    fetch_all(pmids)

    meta = parse_cache()
    meta = meta[meta["pmid"].isin(set(pmids))]
    missing = sorted(set(pmids) - set(meta["pmid"]), key=int)
    print(f"Parsed {len(meta)} PubMed records; not returned by PubMed: {len(missing)}")
    meta.sort_values("pmid", key=lambda s: s.astype(int)).to_csv(
        PROCESSED / "pubmed_metadata.csv", index=False)

    trials = eligible.merge(meta, on="pmid")
    trials = trials[trials["is_trial"]].drop(columns="is_trial")
    trials.to_csv(PROCESSED / "retracted_trials.csv", index=False)
    print(f"Saved {len(trials)} trials to data/processed/retracted_trials.csv")

    # Replace any step-6 rows from an earlier run, so re-running is safe.
    flow = pd.read_csv(FLOW_PATH, dtype=str)
    flow = flow[~flow["step"].str.startswith("6")]
    flow = pd.concat([flow, pd.DataFrame([
        {"step": "6a", "description": "PubMed record retrieved", "n_remaining": len(meta)},
        {"step": "6b", "description": "PubMed publication type is Clinical Trial or a subtype",
         "n_remaining": len(trials)},
    ])])
    flow.to_csv(FLOW_PATH, index=False)

    summarize(trials, eligible, meta)


if __name__ == "__main__":
    main()
