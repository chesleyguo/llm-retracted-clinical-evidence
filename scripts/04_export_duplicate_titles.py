"""Step 04: export titles that have more than one PMID, for manual review.

Takes retraction records (RetractionNature = Retraction) with an (HSC) subject
and a valid OriginalPaperPubMedID, finds titles (compared after trimming and
lowercasing) that appear under more than one PMID, and writes one row per
record to data/processed/duplicate_title_review.csv with columns:
    title, pmid, journal, first_author, year, record_id, decision, note
The last two are left empty to be filled in by hand.

The file is filled in by hand afterwards, so this script never overwrites it.
Record counts after each filter are printed and saved to
results/04_duplicate_title_flow.txt.

Usage:
    python scripts/04_export_duplicate_titles.py [path/to/snapshot.csv]
"""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "processed" / "duplicate_title_review.csv"
FLOW_PATH = ROOT / "results" / "04_duplicate_title_flow.txt"

# Same rule as steps 02-03: "0" and empty strings are not valid PMIDs.
PMID_PATTERN = re.compile(r"^[1-9]\d*$")
DATE_FORMAT = "%m/%d/%Y %H:%M"


def main():
    if OUT_PATH.exists():
        sys.exit(f"{OUT_PATH.relative_to(ROOT)} already exists; not overwriting "
                 "(it may contain manual edits). Move it away to regenerate.")

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        snapshots = sorted((ROOT / "data" / "raw").glob("retraction_watch_*.csv"))
        if not snapshots:
            sys.exit("No snapshot found. Run scripts/01_download_retraction_watch.py first.")
        path = snapshots[-1]

    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")

    flow = [f"File: {path.name}", f"All records: {len(df)}"]
    df = df[df["RetractionNature"].str.strip() == "Retraction"]
    flow.append(f"RetractionNature = Retraction: {len(df)}")
    df = df[df["Subject"].str.contains(r"\(HSC\)", regex=True)]
    flow.append(f"Any (HSC) subject: {len(df)}")
    df = df.assign(pmid=df["OriginalPaperPubMedID"].str.strip())
    df = df[df["pmid"].str.match(PMID_PATTERN)]
    flow.append(f"Valid OriginalPaperPubMedID: {len(df)}")

    df = df.assign(title_key=df["Title"].str.strip().str.lower())
    pmids_per_title = df.groupby("title_key")["pmid"].nunique()
    dup_keys = pmids_per_title[pmids_per_title > 1].index
    df = df[df["title_key"].isin(dup_keys)]
    flow.append(f"Titles with more than one PMID: {len(dup_keys)} "
                f"({df['pmid'].nunique()} PMIDs, {len(df)} records)")

    table = pd.DataFrame({
        "title": df["Title"].str.strip(),
        "pmid": df["pmid"],
        "journal": df["Journal"].str.strip(),
        # Authors look like "A;B;C"; the first one is the first author.
        "first_author": df["Author"].str.split(";").str[0].str.strip(),
        "year": pd.to_datetime(df["OriginalPaperDate"], format=DATE_FORMAT,
                               errors="coerce").dt.year.astype("Int64"),
        "record_id": df["Record ID"],
        "decision": "",
        "note": "",
        "_key": df["title_key"],
    })
    # Keep rows of the same title together.
    table = table.sort_values(["_key", "pmid", "record_id"]).drop(columns="_key")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_PATH, index=False)
    FLOW_PATH.write_text("\n".join(flow) + "\n")

    print("\n".join(flow))
    print(f"Saved {len(table)} rows to {OUT_PATH.relative_to(ROOT)}")
    print(f"Saved counts to {FLOW_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
