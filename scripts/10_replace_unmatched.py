"""Step 10: replace sampled papers that cannot be used.

Rules (docs/analysis_plan.md, "Matched controls" and "Target claims and
prompts"):

- Pair replacement. A sampled retracted trial that cannot be used is replaced,
  together with its control, by the next trial in the same stratum's random
  order from step 08 that respects the journal cap and can be used; the new
  trial is matched to a control with the step-09 rules. A trial cannot be used
  if no control can be found for it, if its PubMed abstract is a retraction
  notice, or if it was rejected in the claims review (approved = NO).
- Control replacement. A control rejected in the claims review is replaced by
  the next eligible candidate in the same recorded random order that chose it
  (data/processed/control_draws.jsonl), continuing with the later topics and
  levels if that order runs out. If no control is left, the pair is replaced.

How the random orders are recovered: step 08 is replayed with the same seed,
recording every permutation it draws (the replay must reproduce the saved
samples, otherwise the script stops); control orders are read from the
draws record.

Updates data/processed/sample_{main,pilot}.csv and controls_{main,pilot}.csv
in place: a replaced trial's PMID is kept in replaces_pmid, replaced controls
in replaced_control_pmids. Each run appends a section to
results/10_replacement_log.txt. Earlier versions of the files remain in the
git history. Each run uses a new generator with seed 2026 for any new
candidate orders it needs; every order used is recorded.

Usage:
    python scripts/10_replace_unmatched.py
"""

import importlib.util
import json
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
REVIEW_PATH = PROCESSED / "claims_review.csv"
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


def review_rejections():
    """PMIDs marked approved = NO in the claims review, by group."""
    if not REVIEW_PATH.exists():
        return set(), set(), set()
    t = pd.read_csv(REVIEW_PATH, dtype=str, keep_default_na=False)
    no = t[t["approved"] == "NO"]
    return (set(no.loc[no["group"] == "retracted", "pmid"]),
            set(no.loc[no["group"] == "control", "pmid"]),
            set(t.loc[t["group"] == "control", "pmid"]))


def trial_inputs(pmid):
    """Cached PubMed record and MeSH tree entries for a retracted trial."""
    article = s09.trial_records({pmid}).get(pmid)
    tree = {}
    if article is not None:
        tree = s09.load_mesh_tree({ui for ui, _ in s09.major_topics(article)})
        tree = s09.load_mesh_tree({p for ui in list(tree) for p in tree[ui]["parents"]})
    return article, tree


def swap_row(frame, key, new_row):
    """Replace the row whose pmid is `key` by new_row, at the same position."""
    i = frame.index[frame["pmid"] == key][0]
    return pd.concat([frame.iloc[:i], pd.DataFrame([new_row]), frame.iloc[i + 1:]],
                     ignore_index=True)


def main():
    samples = {n: pd.read_csv(PROCESSED / f"sample_{n}.csv", dtype=str, keep_default_na=False)
               for n in ("main", "pilot")}
    controls = {n: pd.read_csv(PROCESSED / f"controls_{n}.csv", dtype=str, keep_default_na=False)
                for n in ("main", "pilot")}
    trials = pd.read_csv(PROCESSED / "retracted_trials.csv", dtype=str, keep_default_na=False)
    flags = trials.set_index("pmid")[FLAG_COLUMNS]
    for n in samples:
        samples[n] = samples[n].drop(columns=FLAG_COLUMNS, errors="ignore").join(flags, on="pmid")
        for frame in (samples[n], controls[n]):
            if "replaces_pmid" not in frame:
                frame["replaces_pmid"] = ""
        if "replaced_control_pmids" not in controls[n]:
            controls[n]["replaced_control_pmids"] = ""

    rejected_trials, rejected_controls, reviewed_controls = review_rejections()

    # What to do for each pair, in draw order.
    actions = {}
    for n in ("main", "pilot"):
        ctrl = controls[n].set_index("pmid")
        actions[n] = []
        for _, row in samples[n].sort_values("draw_order", key=lambda s: s.astype(int)).iterrows():
            p = row["pmid"]
            if row["abstract_is_retraction_notice"] == "True":
                actions[n].append(("pair", p, "abstract is a retraction notice"))
            elif ctrl.loc[p, "match_level"] == "NONE":
                actions[n].append(("pair", p, "no control found"))
            elif p in rejected_trials:
                actions[n].append(("pair", p, "retracted trial rejected in claims review"))
            elif ctrl.loc[p, "control_pmid"] in rejected_controls:
                actions[n].append(("control", p, "control rejected in claims review"))
    if not any(actions.values()):
        sys.exit("Every sampled paper can be used; nothing to replace.")

    replayed, orders = replay_step08()
    for n in ("main", "pilot"):
        # Rows added by earlier replacements are not in the step-08 draw.
        original = samples[n][samples[n]["replaces_pmid"] == ""]
        if not set(original["pmid"]) <= set(replayed[n]["pmid"]):
            sys.exit(f"Replaying step 08 does not reproduce sample_{n}.csv; stopping.")

    rw_path, rw_pmids, rw_dois = s09.load_rw_ids()
    in_any_sample = set(samples["main"]["pmid"]) | set(samples["pilot"]["pmid"])
    # Every control ever chosen or reviewed stays used, including rejected ones.
    used = set(controls["main"]["control_pmid"]) | set(controls["pilot"]["control_pmid"])
    used |= reviewed_controls
    if s09.DRAWS_PATH.exists():
        used |= {json.loads(l)["control_pmid"] for l in open(s09.DRAWS_PATH)}
    used.discard("")
    rng = np.random.default_rng(s09.SEED)
    rejections = Counter()
    log = ["", "=" * 72,
           f"Run at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
           f"Seed for new candidate orders: {s09.SEED} (numpy {np.__version__}, default_rng)",
           f"Retraction Watch snapshot: {rw_path.name}"]

    def ctx_for(n, without_pmid):
        keep = (controls[n]["pmid"] != without_pmid) & (controls[n]["control_journal"] != "")
        return {"rw_pmids": rw_pmids, "rw_dois": rw_dois, "used": used,
                "journals": Counter(controls[n].loc[keep, "control_journal"]),
                "rejections": rejections}

    def replace_pair(n, old_pmid, why):
        sample = samples[n]
        old = sample[sample["pmid"] == old_pmid].iloc[0]
        stratum = old["stratum"]
        trial_journals = Counter(sample.loc[sample["pmid"] != old_pmid, "journal"]
                                 .str.strip().str.lower())
        order = orders[(n, stratum)].reset_index(drop=True)
        start = order.index[order["pmid"] == old_pmid][0] + 1
        log.extend(["", f"{n}: replacing pair of {old_pmid}, {why} (stratum {stratum}, "
                        f"position {start} in the stratum's random order)"])
        for pos in range(start, len(order)):
            cand = order.iloc[pos].copy()
            if cand["pmid"] in in_any_sample:
                continue
            if s07.is_retraction_notice(cand["pm_abstract"]):
                log.append(f"  position {pos + 1}: {cand['pmid']} skipped (abstract is a retraction notice)")
                continue
            if trial_journals[cand["journal_key"]] >= s08.JOURNAL_CAP:
                log.append(f"  position {pos + 1}: {cand['pmid']} skipped (journal cap)")
                continue
            cand["stratum"] = stratum
            article, tree = trial_inputs(cand["pmid"])
            result = s09.match_trial(cand, article, tree, rng, ctx_for(n, old_pmid))
            if result["match_level"] == "NONE":
                log.append(f"  position {pos + 1}: {cand['pmid']} skipped ({result['note']})")
                continue
            s09.append_draw(result, n, "step 10: pair replacement")
            log.append(f"  position {pos + 1}: {cand['pmid']} taken; control "
                       f"{result['control_pmid']} (level {result['match_level']}, "
                       f"topic {result['matched_topic']})")
            new_row = {c: cand.get(c, "") for c in sample.columns}
            new_row.update({"sample": n, "draw_order": old["draw_order"], "stratum": stratum,
                            "replaces_pmid": old_pmid})
            new_row.update({c: str(cand[c]) for c in FLAG_COLUMNS})
            samples[n] = swap_row(sample, old_pmid, new_row)
            result.update({"replaces_pmid": old_pmid, "replaced_control_pmids": ""})
            controls[n] = swap_row(controls[n], old_pmid, result)
            in_any_sample.add(cand["pmid"])
            return
        sys.exit(f"No replacement found for {old_pmid} in stratum {stratum}.")

    def replace_control(n, trial_pmid, why):
        row = controls[n][controls[n]["pmid"] == trial_pmid].iloc[0]
        old_control = row["control_pmid"]
        draw = s09.latest_draw(trial_pmid, old_control)
        if draw is None:
            sys.exit(f"No recorded candidate order for control {old_control} of {trial_pmid}.")
        log.extend(["", f"{n}: replacing control {old_control} of {trial_pmid}, {why} "
                        f"(recorded order: level {draw['level']}, topic {draw['topic']}, "
                        f"chosen at position {draw['chosen_index'] + 1} of {len(draw['order'])})"])
        trial = samples[n][samples[n]["pmid"] == trial_pmid].iloc[0]
        article, tree = trial_inputs(trial_pmid)
        result = s09.match_trial(trial, article, tree, rng, ctx_for(n, trial_pmid), resume=draw)
        if result["match_level"] == "NONE":
            log.append("  no eligible control left; the pair is replaced")
            replace_pair(n, trial_pmid, "no control left after a rejected control")
            return
        s09.append_draw(result, n, "step 10: control replacement")
        log.append(f"  new control {result['control_pmid']} (level {result['match_level']}, "
                   f"topic {result['matched_topic']}, position {result['n_checked']})")
        previous = [x for x in row["replaced_control_pmids"].split(";") if x]
        result.update({"replaces_pmid": row["replaces_pmid"],
                       "replaced_control_pmids": ";".join(previous + [old_control])})
        controls[n] = swap_row(controls[n], trial_pmid, result)

    for n in ("main", "pilot"):
        for kind, pmid, why in actions[n]:
            if kind == "pair":
                replace_pair(n, pmid, why)
            else:
                replace_control(n, pmid, why)

    for n in ("main", "pilot"):
        samples[n].to_csv(PROCESSED / f"sample_{n}.csv", index=False)
        controls[n].to_csv(PROCESSED / f"controls_{n}.csv", index=False)
    with open(LOG_PATH, "a") as f:
        f.write("\n".join(log) + "\n")
    print("\n".join(log))
    print(f"\nUpdated samples and controls; log appended to {LOG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
