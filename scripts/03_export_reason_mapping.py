"""Step 03: export the list of retraction reasons for manual mapping.

Takes retraction records (RetractionNature = Retraction) with an (HSC) subject
and a valid OriginalPaperPubMedID, counts every reason that appears, and writes
data/processed/reason_mapping.csv with columns:
    reason, count, include, p2_category, note
The last three are left empty to be filled in by hand.

The file is filled in by hand afterwards, so this script never overwrites it.
Record counts after each filter are printed and saved to
results/03_reason_mapping_flow.txt.

Usage:
    python scripts/03_export_reason_mapping.py [path/to/snapshot.csv]
"""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "processed" / "reason_mapping.csv"
FLOW_PATH = ROOT / "results" / "03_reason_mapping_flow.txt"

# Same rule as step 02: a PMID is valid only if it is a positive integer, so
# the placeholder "0" and empty strings count as missing.
PMID_PATTERN = re.compile(r"^[1-9]\d*$")


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
    df = df[df["OriginalPaperPubMedID"].str.strip().str.match(PMID_PATTERN)]
    flow.append(f"Valid OriginalPaperPubMedID: {len(df)}")

    # Reasons look like "A;B;". Count each reason once per record.
    reasons = (df["Reason"].str.split(";").explode().str.strip()
               .loc[lambda s: s != ""])
    reasons = reasons.groupby(level=0).unique().explode()
    counts = reasons.value_counts()
    flow.append(f"Distinct reasons: {len(counts)}")
    flow.append(f"Records with no reason: {len(df) - reasons.index.nunique()}")

    # Sort by count, then alphabetically so ties have a stable order.
    table = (counts.rename_axis("reason").reset_index(name="count")
             .sort_values(["count", "reason"], ascending=[False, True]))
    for col in ["include", "p2_category", "note"]:
        table[col] = ""

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_PATH, index=False)
    FLOW_PATH.write_text("\n".join(flow) + "\n")

    print("\n".join(flow))
    print(f"Saved {len(table)} reasons to {OUT_PATH.relative_to(ROOT)}")
    print(f"Saved counts to {FLOW_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
