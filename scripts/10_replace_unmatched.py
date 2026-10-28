"""Step 10: replace sampled trials that cannot be used.

Rule (docs/analysis_plan.md, "Matched controls"): a sampled retracted trial
that cannot be used is replaced by the next trial in the same stratum's random
order from step 08 that respects the journal cap and can be used. A trial
cannot be used if no control can be found for it (for example because it has
no MeSH major topics) or if its PubMed abstract is a retraction notice. The
replacement is matched to a control with the step-09 rules.

How the random order is recovered: step 08 is replayed with the same seed,
recording every permutation it draws. The replay must reproduce the saved
samples exactly, otherwise the script stops.

Updates data/processed/sample_{main,pilot}.csv and controls_{main,pilot}.csv
in place (the replaced row is swapped for the new one, with its PMID kept in
the column replaces_pmid) and writes results/10_replacement_log.txt. The
original files remain in the git history.

Usage:
    python scripts/10_replace_unmatched.py
"""

import importlib.util
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
LOG_PATH = ROOT / "results" / "10_replacement_log.txt"


def load_script(filename):
    # Script names start with a digit, so they cannot be imported normally.
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s07 = load_script("07_fetch_pubmed.py")
s08 = load_script("08_draw_sample.py")
s09 = load_script("09_match_controls.py")
# Paper-level flags from step 07, added to the sample files.
FLAG_COLUMNS = ["abstract_is_retraction_notice", "pubmed_title_marked"]


class RecordingRng:
    """Wraps a generator and records each permutation, so the step-08 random
    order of every stratum can be read back. Step 08 only calls permutation()."""

    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.orders = []

    def permutation(self, n):
        order = self.rng.permutation(n)
        self.orders.append(order)
        return order


def replay_step08():
    """Rebuild the step-08 frame and samples; return them with the recorded
    order of each (sample, stratum) pool."""
    trials = pd.read_csv(PROCESSED / "retracted_trials.csv", dtype=str, keep_default_na=False)
    frame = trials[trials["has_abstract"] == "True"].copy()
    frame["stratum"] = pd.to_datetime(frame["retraction_date"]).dt.year.map(s08.stratum_of)
    frame["journal_key"] = frame["journal"].str.strip().str.lower()
    frame = frame.sort_values("pmid", key=lambda s: s.astype(int)).reset_index(drop=True)

    rec = RecordingRng(s08.SEED)
    main = s08.draw(frame, s08.MAIN_QUOTA, rec, "main")
    rest = frame[~frame["pmid"].isin(set(main["pmid"]))]
    pilot = s08.draw(rest, s08.PILOT_QUOTA, rec, "pilot")

    orders = {}
    for i, (label, pool_frame) in enumerate([("main", frame), ("pilot", rest)]):
        for j, stratum in enumerate(s08.STRATA):
            pool = pool_frame[pool_frame["stratum"] == stratum]
            orders[(label, stratum)] = pool.iloc[rec.orders[i * len(s08.STRATA) + j]]
    return {"main": main, "pilot": pilot}, orders


def main():
    samples = {n: pd.read_csv(PROCESSED / f"sample_{n}.csv", dtype=str, keep_default_na=False)
               for n in ("main", "pilot")}
    controls = {n: pd.read_csv(PROCESSED / f"controls_{n}.csv", dtype=str, keep_default_na=False)
                for n in ("main", "pilot")}
    trials = pd.read_csv(PROCESSED / "retracted_trials.csv", dtype=str, keep_default_na=False)
    flags = trials.set_index("pmid")[FLAG_COLUMNS]
    for n in samples:
        samples[n] = samples[n].drop(columns=FLAG_COLUMNS, errors="ignore").join(flags, on="pmid")

    # Trials to replace, in draw order, with the reason.
    to_replace = {}
    for n in ("main", "pilot"):
        unmatched = set(controls[n].loc[controls[n]["match_level"] == "NONE", "pmid"])
        notice = set(samples[n].loc[samples[n]["abstract_is_retraction_notice"] == "True", "pmid"])
        to_replace[n] = [(p, "abstract is a retraction notice" if p in notice else "no control found")
                         for p in samples[n]["pmid"] if p in unmatched | notice]
    if not any(to_replace.values()):
        sys.exit("Every sampled trial can be used; nothing to replace.")

    replayed, orders = replay_step08()
    for n in ("main", "pilot"):
        # Earlier replacements change the saved files, so compare only rows
        # that were not added by this step.
        original = samples[n]
        if "replaces_pmid" in original:
            original = original[original["replaces_pmid"] == ""]
        if not set(original["pmid"]) <= set(replayed[n]["pmid"]):
            sys.exit(f"Replaying step 08 does not reproduce sample_{n}.csv; stopping.")

    rw_path, rw_pmids, rw_dois = s09.load_rw_ids()
    in_any_sample = set(samples["main"]["pmid"]) | set(samples["pilot"]["pmid"])
    used = set(controls["main"]["control_pmid"]) | set(controls["pilot"]["control_pmid"])
    used.discard("")
    # A fresh generator with the study seed for the control searches of
    # replacements; logged below.
    rng = np.random.default_rng(s09.SEED)
    rejections = Counter()
    log = [f"Seed: {s09.SEED} (numpy {np.__version__}, default_rng)",
           f"Retraction Watch snapshot: {rw_path.name}",
           f"Run at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}"]

    for n in ("main", "pilot"):
        for old_pmid, why in to_replace[n]:
            sample, ctrl = samples[n], controls[n]
            old = sample[sample["pmid"] == old_pmid].iloc[0]
            stratum = old["stratum"]
            # Journal counts without the trial being replaced.
            trial_journals = Counter(sample.loc[sample["pmid"] != old_pmid, "journal"]
                                     .str.strip().str.lower())
            keep = (ctrl["pmid"] != old_pmid) & (ctrl["control_journal"] != "")
            control_journals = Counter(ctrl.loc[keep, "control_journal"])

            order = orders[(n, stratum)].reset_index(drop=True)
            start = order.index[order["pmid"] == old_pmid][0] + 1
            log += ["", f"{n}: replacing {old_pmid}, {why} (stratum {stratum}, position "
                        f"{start} in the stratum's random order)"]
            new_trial, result = None, None
            for pos in range(start, len(order)):
                cand = order.iloc[pos]
                if cand["pmid"] in in_any_sample:
                    continue
                if s07.is_retraction_notice(cand["pm_abstract"]):
                    log.append(f"  position {pos + 1}: {cand['pmid']} skipped (abstract is a retraction notice)")
                    continue
                if trial_journals[cand["journal_key"]] >= s08.JOURNAL_CAP:
                    log.append(f"  position {pos + 1}: {cand['pmid']} skipped (journal cap)")
                    continue
                cand = cand.copy()
                cand["stratum"] = stratum
                article = s09.trial_records({cand["pmid"]}).get(cand["pmid"])
                tree = s09.load_mesh_tree({ui for ui, _ in s09.major_topics(article)}) if article is not None else {}
                tree = s09.load_mesh_tree({p for ui in list(tree) for p in tree[ui]["parents"]}) if tree else tree
                ctx_base = {"rw_pmids": rw_pmids, "rw_dois": rw_dois, "used": used,
                            "journals": control_journals, "rejections": rejections}
                result = s09.match_trial(cand, article, tree, rng, ctx_base)
                if result["match_level"] == "NONE":
                    log.append(f"  position {pos + 1}: {cand['pmid']} skipped ({result['note']})")
                    continue
                new_trial = cand
                log.append(f"  position {pos + 1}: {cand['pmid']} taken; control "
                           f"{result['control_pmid']} (level {result['match_level']}, "
                           f"topic {result['matched_topic']})")
                break
            if new_trial is None:
                sys.exit(f"No replacement found for {old_pmid} in stratum {stratum}.")

            # Swap the rows, keeping the old draw order and sample label.
            new_row = {c: new_trial.get(c, "") for c in sample.columns if c != "replaces_pmid"}
            new_row.update({"sample": n, "draw_order": old["draw_order"], "stratum": stratum,
                            "replaces_pmid": old_pmid})
            new_row.update({c: str(new_trial[c]) for c in FLAG_COLUMNS})
            if "replaces_pmid" not in sample:
                sample = sample.assign(replaces_pmid="")
            samples[n] = pd.concat([sample[sample["pmid"] != old_pmid], pd.DataFrame([new_row])],
                                   ignore_index=True) \
                .sort_values("draw_order", key=lambda s: s.astype(int), ignore_index=True)
            # Put the new control row where the old one was (same draw order).
            result["replaces_pmid"] = old_pmid
            if "replaces_pmid" not in ctrl:
                ctrl = ctrl.assign(replaces_pmid="")
            i = ctrl.index[ctrl["pmid"] == old_pmid][0]
            controls[n] = pd.concat([ctrl.iloc[:i], pd.DataFrame([result]), ctrl.iloc[i + 1:]],
                                    ignore_index=True)
            in_any_sample.add(new_trial["pmid"])

    for n in ("main", "pilot"):
        samples[n].to_csv(PROCESSED / f"sample_{n}.csv", index=False)
        controls[n].to_csv(PROCESSED / f"controls_{n}.csv", index=False)
    LOG_PATH.write_text("\n".join(log) + "\n")
    print("\n".join(log))
    print(f"\nUpdated samples and controls; log in {LOG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
