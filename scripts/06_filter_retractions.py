"""Step 06: apply inclusion criteria 1-5 (docs/analysis_plan.md).

Reads the newest Retraction Watch snapshot plus the two hand-reviewed tables
    data/processed/reason_mapping.csv       (include, p2_category, strength)
    data/processed/duplicate_title_review.csv (decision)
and writes
    data/processed/retractions_eligible.csv  one row per PMID
    results/filter_flow.csv                  records remaining after each step

Criterion 6 (clinical trial) needs PubMed data and is applied in step 07,
which adds its rows to the same flow table.

Usage:
    python scripts/06_filter_retractions.py [path/to/snapshot.csv]
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUT_PATH = PROCESSED / "retractions_eligible.csv"
FLOW_PATH = ROOT / "results" / "filter_flow.csv"

PMID_PATTERN = r"^[1-9]\d*$"
DOI_PATTERN = r"^10\.\d{4,9}/\S+$"
DATE_FORMAT = "%m/%d/%Y %H:%M"
# Codebook P2: "If a record lists several reasons, apply the first matching
# category in the order above."
P2_ORDER = ["FABRICATION", "ERROR", "OTHER_UNRELIABLE"]


def split_reasons(text):
    """'A;B;' -> ['A', 'B'] (unique, sorted)."""
    return sorted({r.strip() for r in text.split(";") if r.strip()})


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        snapshots = sorted((ROOT / "data" / "raw").glob("retraction_watch_*.csv"))
        if not snapshots:
            sys.exit("No snapshot found. Run scripts/01_download_retraction_watch.py first.")
        path = snapshots[-1]

    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    mapping = pd.read_csv(PROCESSED / "reason_mapping.csv", dtype=str, keep_default_na=False)
    review = pd.read_csv(PROCESSED / "duplicate_title_review.csv", dtype=str, keep_default_na=False)

    # A reason without a decision would silently be treated as not INCLUDE,
    # so stop if the mapping is incomplete.
    if (mapping["include"] == "").any():
        sys.exit("reason_mapping.csv has rows with an empty include column.")
    is_inc = mapping["include"] == "INCLUDE"
    if ((mapping.loc[is_inc, "p2_category"] == "") | (mapping.loc[is_inc, "strength"] == "")).any():
        sys.exit("reason_mapping.csv has INCLUDE rows without p2_category or strength.")
    include = dict(zip(mapping["reason"], mapping["include"]))
    p2 = dict(zip(mapping["reason"], mapping["p2_category"]))
    strength = dict(zip(mapping["reason"], mapping["strength"]))

    # Criterion 4b looks for DOIs shared by records with different titles.
    # This is computed on the whole snapshot, before any filtering, so that a
    # DOI counts as shared even if the other records are filtered out earlier.
    doi = df["OriginalPaperDOI"].str.strip().str.lower()
    title_key = df["Title"].str.strip().str.lower()
    has_doi = doi.str.match(DOI_PATTERN)
    titles_per_doi = title_key[has_doi].groupby(doi[has_doi]).nunique()
    shared_dois = set(titles_per_doi[titles_per_doi > 1].index)

    flow = []

    def step(name, description, frame):
        flow.append({"step": name, "description": description, "n_remaining": len(frame)})
        print(f"{len(frame):>7}  {name}  {description}")
        return frame

    df = step("0", "All records in snapshot", df)
    df = step("1", "RetractionNature = Retraction",
              df[df["RetractionNature"].str.strip() == "Retraction"])
    df = step("2", "At least one (HSC) subject",
              df[df["Subject"].str.contains(r"\(HSC\)", regex=True)])

    df = df.assign(pmid=df["OriginalPaperPubMedID"].str.strip())
    df = step("3a", "Valid OriginalPaperPubMedID", df[df["pmid"].str.match(PMID_PATTERN)])
    dropped = set(review.loc[review["decision"] == "DROP", "record_id"])
    df = step("3b", "Duplicate-title review: DROP records removed",
              df[~df["Record ID"].isin(dropped)])
    # One record per PMID: earliest RetractionDate, ties -> lowest Record ID.
    df = df.assign(
        retraction_date=pd.to_datetime(df["RetractionDate"], format=DATE_FORMAT),
        record_id_num=df["Record ID"].astype(int),
        n_rw_records=df.groupby("pmid")["pmid"].transform("size"),
    )
    df = df.sort_values(["pmid", "retraction_date", "record_id_num"])
    df = step("3c", "One record per PMID (earliest RetractionDate, then lowest Record ID)",
              df.drop_duplicates("pmid", keep="first"))

    df = step("4a", "ArticleType is not Conference Abstract/Paper",
              df[~df["ArticleType"].str.contains("Conference Abstract/Paper", regex=False)])
    df = step("4b", "OriginalPaperDOI not shared by records with different titles",
              df[~df["OriginalPaperDOI"].str.strip().str.lower().isin(shared_dois)])

    reasons = df["Reason"].apply(split_reasons)
    unknown = sorted({r for rs in reasons for r in rs} - set(include))
    if unknown:
        sys.exit(f"Reasons missing from reason_mapping.csv: {unknown}")
    inc_reasons = reasons.apply(lambda rs: [r for r in rs if include[r] == "INCLUDE"])
    override = reasons.apply(lambda rs: any(include[r] == "OVERRIDE_EXCLUDE" for r in rs))
    keep = (inc_reasons.str.len() > 0) & ~override
    df = step("5", "At least one INCLUDE reason and no OVERRIDE_EXCLUDE reason", df[keep])
    inc_reasons = inc_reasons[keep]

    out = pd.DataFrame({
        "pmid": df["pmid"],
        "record_id": df["Record ID"],
        "n_rw_records": df["n_rw_records"],
        "title": df["Title"].str.strip(),
        "authors": df["Author"].str.strip(),
        "journal": df["Journal"].str.strip(),
        "publisher": df["Publisher"].str.strip(),
        "country": df["Country"].str.strip(),
        "subject": df["Subject"].str.strip(),
        "article_type": df["ArticleType"].str.strip(),
        "rw_clinical_study": df["ArticleType"].str.contains("Clinical Study", regex=False),
        "original_paper_date": pd.to_datetime(df["OriginalPaperDate"], format=DATE_FORMAT).dt.date,
        "original_paper_doi": df["OriginalPaperDOI"].str.strip(),
        "retraction_date": df["retraction_date"].dt.date,
        "retraction_doi": df["RetractionDOI"].str.strip(),
        "retraction_pmid": df["RetractionPubMedID"].str.strip(),
        "reason": df["Reason"].str.strip(),
        "include_reasons": inc_reasons.str.join("; "),
        # First category in codebook order among the INCLUDE reasons.
        "p2_category": inc_reasons.apply(
            lambda rs: next(c for c in P2_ORDER if c in {p2[r] for r in rs})),
        # STRONG if any INCLUDE reason is STRONG, otherwise WEAK.
        "strength": inc_reasons.apply(
            lambda rs: "STRONG" if any(strength[r] == "STRONG" for r in rs) else "WEAK"),
    }).sort_values("pmid", key=lambda s: s.astype(int))

    out.to_csv(OUT_PATH, index=False)
    FLOW_PATH.parent.mkdir(exist_ok=True)
    pd.DataFrame(flow).to_csv(FLOW_PATH, index=False)
    print(f"Saved {len(out)} papers to {OUT_PATH.relative_to(ROOT)}")
    print(f"Saved flow table to {FLOW_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
