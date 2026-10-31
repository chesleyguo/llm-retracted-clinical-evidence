"""Step 19: how much the LLM codes of the pilot changed from codebook v0.13
to v1.0 (script 16 re-run on the same 300 responses).

Reports, per variable, the number of responses whose code changed and the
code distribution under each version. Only aggregate counts are printed; the
item-level table is saved for later review.

The 30 round 1 items supplied the v1.0 examples, so changes on those items
are not a clean test of v1.0; they are counted separately.

Writes:
- results/19_codebook_v0.13_vs_v1.0.json: counts per variable;
- data/processed/coding_pilot_changes.csv: one row per changed code.

Usage:
    python scripts/19_compare_codebook_versions.py
"""

import json
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OLD_PATH = PROCESSED / "coding_pilot_v0.13.csv"
NEW_PATH = PROCESSED / "coding_pilot.csv"
ROUND1_KEY = PROCESSED / "human_coding_pilot_key.csv"
VARS = ["V1_retraction_flag", "V2_stance", "V3_cited", "V3_source",
        "V4_status_answer", "V5_fabrication", "V6_accuracy"]


def main():
    old = pd.read_csv(OLD_PATH, dtype=str, keep_default_na=False)
    new = pd.read_csv(NEW_PATH, dtype=str, keep_default_na=False)
    assert new["codebook_version"].eq("v1.0").all(), "coding_pilot.csv is not the v1.0 run"
    both = old.merge(new, on="response_id", suffixes=("_old", "_new"))
    both = both[(both["status_old"] == "ok") & (both["status_new"] == "ok")]
    round1 = set(pd.read_csv(ROUND1_KEY, dtype=str)["response_id"])
    both["round1_item"] = both["response_id"].isin(round1)
    print(f"Responses coded ok under both versions: {len(both)} "
          f"({int(both['round1_item'].sum())} of them round 1 items)")

    out, changes = {"n": len(both)}, []
    print(f"\n{'variable':<20}{'changed':>8}{'outside round 1':>17}")
    for var in VARS:
        diff = both[both[f"{var}_old"] != both[f"{var}_new"]]
        out[var] = {"changed": len(diff),
                    "changed_outside_round1": int((~diff["round1_item"]).sum()),
                    "v0.13": dict(Counter(both[f"{var}_old"])),
                    "v1.0": dict(Counter(both[f"{var}_new"])),
                    "transitions": dict(Counter(f"{a} -> {b}" for a, b in
                                                zip(diff[f"{var}_old"], diff[f"{var}_new"])))}
        print(f"{var:<20}{len(diff):>8}{out[var]['changed_outside_round1']:>17}")
        for _, r in diff.iterrows():
            changes.append({"response_id": r["response_id"], "variable": var,
                            "v0.13": r[f"{var}_old"], "v1.0": r[f"{var}_new"],
                            "round1_item": r["round1_item"]})
    any_change = both[[any(r[f"{v}_old"] != r[f"{v}_new"] for v in VARS) for _, r in both.iterrows()]]
    out["responses_with_any_change"] = len(any_change)
    out["quote_not_found_responses"] = {"v0.13": int((both["quote_not_found_old"] != "").sum()),
                                        "v1.0": int((both["quote_not_found_new"] != "").sum())}
    print(f"\nResponses with any change: {len(any_change)}")
    print(f"Responses with quote_not_found: v0.13 {out['quote_not_found_responses']['v0.13']}, "
          f"v1.0 {out['quote_not_found_responses']['v1.0']}")

    (ROOT / "results" / "19_codebook_v0.13_vs_v1.0.json").write_text(
        json.dumps(out, indent=1) + "\n")
    pd.DataFrame(changes).to_csv(PROCESSED / "coding_pilot_changes.csv", index=False)
    print("Wrote results/19_codebook_v0.13_vs_v1.0.json and data/processed/coding_pilot_changes.csv")


if __name__ == "__main__":
    main()
