"""Step 08: draw the main and pilot samples of retracted trials.

Follows docs/analysis_plan.md, "Sampling":
- frame: data/processed/retracted_trials.csv with has_abstract = True
- strata by retraction year: <=2022, 2023, 2024, 2025-2026
- main sample 25 per stratum; pilot 4 from <=2022 and 2 from each other stratum
- at most 3 trials per journal in the main sample (across strata), and at most
  3 per journal within the pilot sample
- one random generator, seed 2026; strata processed in a fixed order

Writes data/processed/sample_main.csv, data/processed/sample_pilot.csv and a
log with the seed and counts to results/08_sampling_log.txt. The samples are
fixed once drawn, so the script refuses to overwrite them.

Usage:
    python scripts/08_draw_sample.py
"""

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
MAIN_PATH = PROCESSED / "sample_main.csv"
PILOT_PATH = PROCESSED / "sample_pilot.csv"
LOG_PATH = ROOT / "results" / "08_sampling_log.txt"

SEED = 2026
JOURNAL_CAP = 3
# Processing order is fixed in the analysis plan: fewest trials available
# under the journal cap first, so the cap shared across strata is used up by
# the strata that can least afford it last.
STRATA = ["2024", "2025-2026", "2023", "<=2022"]
MAIN_QUOTA = {"2024": 25, "2025-2026": 25, "2023": 25, "<=2022": 25}
PILOT_QUOTA = {"2024": 2, "2025-2026": 2, "2023": 2, "<=2022": 4}

lines = []


def out(text=""):
    print(text)
    lines.append(str(text))


def stratum_of(year):
    if year <= 2022:
        return "<=2022"
    if year >= 2025:
        return "2025-2026"
    return str(year)


def draw(frame, quotas, rng, label):
    """Take trials in random order within each stratum, skipping journals at
    the cap. The cap is counted across all strata of this sample."""
    per_journal = Counter()
    chosen = []
    for stratum in STRATA:
        pool = frame[frame["stratum"] == stratum]
        order = rng.permutation(len(pool))
        taken = 0
        for i in order:
            row = pool.iloc[i]
            if taken == quotas[stratum]:
                break
            if per_journal[row["journal_key"]] >= JOURNAL_CAP:
                continue
            per_journal[row["journal_key"]] += 1
            chosen.append({**row.to_dict(), "sample": label, "draw_order": len(chosen) + 1})
            taken += 1
        if taken < quotas[stratum]:
            sys.exit(f"{label}: stratum {stratum} supplied only {taken} of {quotas[stratum]}.")
    return pd.DataFrame(chosen)


def describe(sample, label):
    out(f"\n{label}: {len(sample)} trials")
    for stratum in STRATA:
        out(f"  {stratum:<10} {(sample['stratum'] == stratum).sum():>3}")
    jc = sample["journal"].value_counts()
    out(f"  distinct journals: {len(jc)}")
    out("  trials per journal: " + ", ".join(
        f"{n} journal(s) with {k}" for k, n in sorted(Counter(jc).items(), reverse=True)))
    out("  journals with more than 1 trial:")
    for journal, n in jc[jc > 1].items():
        out(f"    {n}  {journal}")
    for col in ["p2_category", "strength"]:
        out(f"  {col}: " + ", ".join(f"{k} {v}" for k, v in sample[col].value_counts().items()))


def main():
    for path in (MAIN_PATH, PILOT_PATH):
        if path.exists():
            sys.exit(f"{path.relative_to(ROOT)} already exists; samples are fixed once drawn.")

    trials = pd.read_csv(PROCESSED / "retracted_trials.csv", dtype=str, keep_default_na=False)
    out(f"Seed: {SEED} (numpy {np.__version__}, default_rng)")
    out(f"Retracted trials: {len(trials)}")
    frame = trials[trials["has_abstract"] == "True"].copy()
    out(f"With an abstract (sampling frame): {len(frame)}")

    frame["stratum"] = pd.to_datetime(frame["retraction_date"]).dt.year.map(stratum_of)
    # Journal names are compared after trimming and lowercasing.
    frame["journal_key"] = frame["journal"].str.strip().str.lower()
    # Sort before shuffling so the result depends only on the seed, not on
    # the row order of the input file.
    frame = frame.sort_values("pmid", key=lambda s: s.astype(int)).reset_index(drop=True)

    out("\nAvailable per stratum (trials / with journal cap):")
    for stratum in STRATA:
        pool = frame[frame["stratum"] == stratum]
        capped = pool["journal_key"].value_counts().clip(upper=JOURNAL_CAP).sum()
        out(f"  {stratum:<10} {len(pool):>4} / {capped:>4}")

    rng = np.random.default_rng(SEED)
    main_sample = draw(frame, MAIN_QUOTA, rng, "main")
    # The pilot continues the same generator and draws only from trials not
    # in the main sample, so the two samples never overlap.
    rest = frame[~frame["pmid"].isin(set(main_sample["pmid"]))]
    pilot_sample = draw(rest, PILOT_QUOTA, rng, "pilot")
    assert not set(main_sample["pmid"]) & set(pilot_sample["pmid"])

    describe(main_sample, "Main sample")
    describe(pilot_sample, "Pilot sample")

    cols = ["sample", "draw_order", "stratum"] + [c for c in trials.columns]
    main_sample[cols].to_csv(MAIN_PATH, index=False)
    pilot_sample[cols].to_csv(PILOT_PATH, index=False)
    LOG_PATH.write_text("\n".join(lines) + "\n")
    print(f"\nSaved {MAIN_PATH.relative_to(ROOT)}, {PILOT_PATH.relative_to(ROOT)}, "
          f"{LOG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
