"""Step 02: describe the Retraction Watch snapshot. No filtering.

Reads the newest data/raw/retraction_watch_*.csv (or a path given as an
argument) and writes a plain-text summary to
results/02_retraction_watch_summary.txt. The summary is used to write the
inclusion criteria in docs/analysis_plan.md.

Sections:
  A. How missing values are actually written, per column
  B. Coverage of DOI / PMID fields, using the real missing values
  C. Record type (RetractionNature)
  D. Subjects (is there a health-sciences group?)
  E. Article types (can clinical trials be identified?)
  F. Retraction reasons (input for P2)
  G. Dates (input for P3)
  H. Original papers with more than one record (by OriginalPaperDOI)

Usage:
    python scripts/02_describe_retraction_watch.py [path/to/snapshot.csv]
"""

import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "results" / "02_retraction_watch_summary.txt"

# Values that might stand for "missing". Section A counts each one per column
# so we can see which ones the database really uses before trusting them.
CANDIDATE_MISSING = ["", "0", "unavailable", "na", "n/a", "none", "null", "nan", "-"]

ID_COLUMNS = ["OriginalPaperDOI", "OriginalPaperPubMedID",
              "RetractionDOI", "RetractionPubMedID"]
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$")
PMID_PATTERN = re.compile(r"^[1-9]\d*$")
DATE_FORMAT = "%m/%d/%Y %H:%M"  # e.g. "7/18/2026 0:00"

lines = []


def out(text=""):
    print(text)
    lines.append(str(text))


def header(title):
    out()
    out("=" * 72)
    out(title)
    out("=" * 72)


def split_multi(series):
    """Multi-valued fields look like 'A;B;' -> ['A', 'B']."""
    return series.str.split(";").explode().str.strip().loc[lambda s: s != ""]


def show_counts(counter, n_total, top=None):
    for value, n in counter.most_common(top):
        out(f"  {n:>7}  {n / n_total:6.1%}  {value}")


def is_valid(col, s):
    # Coverage counts only values that look like a real identifier, so
    # placeholders such as "0" or "Unavailable" count as missing.
    pattern = DOI_PATTERN if "DOI" in col else PMID_PATTERN
    return s.str.strip().str.match(pattern)


def coverage_table(df, label):
    out(f"\n{label} (n = {len(df)})")
    for col in ID_COLUMNS:
        n_ok = is_valid(col, df[col]).sum()
        out(f"  {col:<24} {n_ok:>7}  {n_ok / max(len(df), 1):6.1%}")


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        snapshots = sorted((ROOT / "data" / "raw").glob("retraction_watch_*.csv"))
        if not snapshots:
            sys.exit("No snapshot found. Run scripts/01_download_retraction_watch.py first.")
        path = snapshots[-1]

    # Read everything as text and turn off pandas' own missing-value guessing,
    # so we see exactly what is written in the file.
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="latin-1")
        encoding = "latin-1 (utf-8 failed)"

    out(f"File: {path.name}")
    out(f"Encoding: {encoding}")
    out(f"Records: {len(df)}")

    # Each line ends with a comma, which creates an empty unnamed column.
    unnamed = [c for c in df.columns if c.startswith("Unnamed")]
    if unnamed:
        non_empty = (df[unnamed] != "").sum().sum()
        out(f"Dropped trailing empty column(s) {unnamed}; non-empty cells in them: {non_empty}")
        df = df.drop(columns=unnamed)
    out(f"Columns ({len(df.columns)}): {', '.join(df.columns)}")
    out(f"Unique Record ID: {df['Record ID'].nunique()} of {len(df)}")

    header("A. How missing values are written (count per column)")
    out(f"  {'column':<24}" + "".join(f"{repr(v):>14}" for v in CANDIDATE_MISSING))
    for col in df.columns:
        v = df[col].str.strip().str.lower()
        counts = [(v == m).sum() for m in CANDIDATE_MISSING]
        out(f"  {col:<24}" + "".join(f"{c:>14}" for c in counts))
    for col in ID_COLUMNS:
        s = df[col].str.strip()
        bad = s[(s != "") & ~is_valid(col, s)]
        out(f"\n  {col}: {len(bad)} non-empty values that are not a valid ID. Most common:")
        show_counts(Counter(bad), len(df), top=10)

    header("B. Coverage of identifiers (valid values only)")
    is_retraction = df["RetractionNature"].str.strip() == "Retraction"
    is_hsc = df["Subject"].str.contains(r"\(HSC\)", regex=True)
    coverage_table(df, "All records")
    coverage_table(df[is_retraction], "RetractionNature = Retraction")
    coverage_table(df[is_retraction & is_hsc], "Retraction and any (HSC) subject")

    header("C. RetractionNature")
    show_counts(Counter(df["RetractionNature"].str.strip()), len(df))

    header("D. Subjects")
    subjects = split_multi(df["Subject"])
    # Count each prefix once per record: a record often lists several
    # subjects under the same prefix.
    prefixes = subjects.str.extract(r"^(\([A-Z/]+\))")[0].dropna()
    prefixes = prefixes.groupby(level=0).unique().explode()
    out("Records per subject prefix group (a record can have several):")
    show_counts(Counter(prefixes), len(df))
    out(f"\nRecords with any (HSC) subject: {is_hsc.sum()}")
    out("Top 30 (HSC) subjects:")
    show_counts(Counter(subjects[subjects.str.startswith("(HSC)")]), len(df), top=30)

    header("E. ArticleType")
    types = split_multi(df["ArticleType"])
    show_counts(Counter(types), len(df), top=30)
    clinical = types[types.str.contains("clinical|trial", case=False)]
    out("\nTypes mentioning 'clinical' or 'trial':")
    show_counts(Counter(clinical), len(df))

    header("F. Reason (among RetractionNature = Retraction)")
    reasons = split_multi(df.loc[is_retraction, "Reason"])
    n_ret = is_retraction.sum()
    out(f"Distinct reasons: {reasons.nunique()}")
    out("Top 40 (a record can have several):")
    show_counts(Counter(reasons), n_ret, top=40)
    out("\nNumber of reasons per record:")
    per_record = reasons.groupby(level=0).size().reindex(
        df.index[is_retraction], fill_value=0)
    show_counts(Counter(per_record), n_ret)

    header("G. Dates")
    for col in ["RetractionDate", "OriginalPaperDate"]:
        parsed = pd.to_datetime(df[col], format=DATE_FORMAT, errors="coerce")
        bad = df.loc[parsed.isna(), col]
        out(f"\n{col}: {parsed.notna().sum()} parsed, {len(bad)} not parsed")
        if len(bad):
            show_counts(Counter(bad), len(df), top=5)
        df[col + "_parsed"] = parsed
    out("\nRetractions per year (RetractionNature = Retraction):")
    years = df.loc[is_retraction, "RetractionDate_parsed"].dt.year.dropna().astype(int)
    for year, n in sorted(Counter(years).items()):
        out(f"  {year}  {n:>6}")
    gap = (df["RetractionDate_parsed"] - df["OriginalPaperDate_parsed"]).dt.days / 365.25
    gap = gap[is_retraction].dropna()
    out(f"\nYears from publication to retraction: median {gap.median():.1f}, "
        f"IQR {gap.quantile(.25):.1f}-{gap.quantile(.75):.1f}, "
        f"negative (retracted before published?): {(gap < 0).sum()}")

    header("H. Original papers with more than one record")
    # Normalize DOIs (case, whitespace) before grouping: DOIs are case-insensitive.
    doi = df["OriginalPaperDOI"].str.strip().str.lower()
    has_doi = is_valid("OriginalPaperDOI", doi)
    grouped = df[has_doi].assign(doi=doi[has_doi]).groupby("doi")
    sizes = grouped.size()
    out(f"Records with a valid OriginalPaperDOI: {has_doi.sum()}")
    out(f"Distinct original DOIs: {len(sizes)}")
    out(f"DOIs with more than one record: {(sizes > 1).sum()} "
        f"(covering {sizes[sizes > 1].sum()} records)")
    out("\nRecords per DOI:")
    show_counts(Counter(sizes), len(sizes))

    # Some DOIs are shared by many different papers (e.g. one DOI for a whole
    # conference-abstract supplement). Records with different titles under one
    # DOI are different papers, not repeated notices about the same paper.
    n_titles = grouped["Title"].agg(lambda s: s.str.strip().str.lower().nunique())
    shared = n_titles[n_titles > 1]
    out(f"\nDOIs whose records have different titles (shared DOI, different papers): "
        f"{len(shared)} (covering {sizes[shared.index].sum()} records)")
    for d in sizes[shared.index].sort_values(ascending=False).head(10).index:
        out(f"  {sizes[d]:>5} records, {n_titles[d]:>4} titles  {d}  "
            f"[{df.loc[doi == d, 'Journal'].iloc[0]}]")

    def combo(s):
        # e.g. "Expression of concern + Retraction x2"
        counts = Counter(s.str.strip())
        return " + ".join(f"{k} x{n}" if n > 1 else k for k, n in sorted(counts.items()))

    same_paper = (sizes > 1) & (n_titles == 1)
    combos = grouped["RetractionNature"].agg(combo)[same_paper]
    out(f"\nCombinations of RetractionNature among multi-record DOIs with one title "
        f"(n = {same_paper.sum()}):")
    show_counts(Counter(combos), len(combos))

    header("I. PMID as paper identifier (retractions with a valid OriginalPaperPubMedID)")
    pmid = df["OriginalPaperPubMedID"].str.strip()
    title = df["Title"].str.strip().str.lower()
    has_pmid = is_retraction & is_valid("OriginalPaperPubMedID", pmid)
    for label, mask in [("All subjects", has_pmid), ("Any (HSC) subject", has_pmid & is_hsc)]:
        sub = pd.DataFrame({"pmid": pmid[mask], "title": title[mask]})
        per_pmid = sub.groupby("pmid").size()
        pmids_per_title = sub.groupby("title")["pmid"].nunique()
        out(f"\n{label}: {len(sub)} records, {len(per_pmid)} distinct PMIDs")
        out(f"  PMIDs with more than one record: {(per_pmid > 1).sum()} "
            f"(covering {per_pmid[per_pmid > 1].sum()} records)")
        out(f"  Titles with more than one PMID: {(pmids_per_title > 1).sum()} "
            f"(covering {pmids_per_title[pmids_per_title > 1].sum()} PMIDs)")
        for t in pmids_per_title[pmids_per_title > 1].sort_values(ascending=False).head(5).index:
            out(f"    {pmids_per_title[t]} PMIDs  {t[:80]}")

    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text("\n".join(lines) + "\n")
    print(f"\nSaved to {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
