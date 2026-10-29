# Project status (handover)

Last updated: 2026-10-30. Read this first in a new session, together with
`CLAUDE.md`, `docs/codebook.md` (now v0.13) and `docs/analysis_plan.md`.

## 1. Where the project is

All steps below are done and committed (latest commit at the time of writing:
`67895f8`).

| Step | Script | Key outputs |
| --- | --- | --- |
| Retraction Watch download, description, reason mapping | `01`–`03` | `data/raw/` (not committed), `data/processed/reason_mapping.csv`, `results/0[1-3]_*` |
| Duplicate titles, publication types | `04`, `05` | `data/processed/duplicate_title_review.csv` |
| Inclusion filter, PubMed metadata | `06`, `07` | `retractions_eligible.csv`, `pubmed_metadata.csv` (both not committed, regenerate per README), `retracted_trials.csv`, `results/filter_flow.csv` |
| Stratified sampling (pilot 10, main 100 retracted trials) | `08` | `sample_pilot.csv`, `sample_main.csv` |
| Matched controls (criteria 1–10) | `09` | `controls_*.csv`, `control_draws.jsonl` |
| Replacement of rejected / unmatched papers | `10` | `results/10_replacement_log.txt` |
| Target claims, F1/F2/F3 prompts, author review | `11`, `12` | `claims_review.csv` (author-reviewed), `claims_final.csv`: 110 pairs ready (pilot 10, main 100) |
| P1 search, LLM suggestions, author codes | `13`, `14` | `p1_candidates.csv`, `p1_review.csv`; main sample P1: YES 6, NO 5, UNCLEAR 89 (copied into `claims_final.csv`) |
| Pilot experiment (20 papers × 3 models × 5 cells = 300 calls, all ok) | `15` | `outputs/responses/pilot.jsonl` (352 records incl. smoke test and errors) |
| LLM coding of the 300 pilot responses, V6 second pass | `16` | `outputs/llm_calls/coding_pilot.jsonl`, `data/processed/coding_pilot.csv`, `results/coding_pilot_summary.json` |
| Human coding sheets | `17` | `human_coding_pilot.xlsx` (30) + `human_coding_pilot_key.csv`; `practice_coding.xlsx` (6, practice only) + `practice_key.csv` |

Analysis numbers fixed so far: V2 main analysis uses 94 retracted trials
(P1 = NO or UNCLEAR); the P1 = NO analysis (n = 5) is descriptive only.

Pilot LLM coding (for reference; do not show per-item codes, see section 5):
300 coded, 0 failed; 65 EXPLICIT, all in the retracted group (V6: 49
ACCURATE, 11 NO_DETAIL, 5 INACCURATE); quote_not_found in 33 responses after
the ellipsis rule; 6 V3 quotes taken from the prompt (`v3_quote_from_prompt`).
Cost ¥1.99, cache-hit share 77%.

## 2. Waiting on

The author is hand-coding `data/processed/human_coding_pilot.xlsx` (30
responses), after a practice round on `practice_coding.xlsx`. The second coder
is not yet chosen (codebook, Open questions).

## 3. Next, once the human coding is done

1. **Check the author's sheet.** Every code cell filled with an allowed value;
   V4 = NA exactly for non-F3 items; V3_source = NA exactly when NOT_CITED;
   evidence quotes present in the response. Report problems, do not fix them.
2. **Agreement, LLM vs. author** (new script, e.g. `18_agreement.py`; join on
   `human_coding_pilot_key.csv` → `coding_pilot.csv`): per variable, Cohen's
   kappa and percent agreement; for V1, the LLM's sensitivity and precision
   with the author's codes as reference (positive = EXPLICIT; report also
   with EXPLICIT or INTEGRITY_CONCERN as positive). With 30 items, report
   kappa with a note on its instability for rare codes. Save to `results/`.
3. **List every disagreement** (item, variable, both codes, both evidence
   quotes), with the 6 `v3_quote_from_prompt` items and all quote_not_found
   items marked. The author decides on codebook changes; per codebook
   section 6, if any variable has more than 5 disagreements, code 20 new
   responses after the revision.
4. **Practice sheet**: only if the author asks, compare with `practice_key.csv`.

## 4. Decided but not yet done

**Codebook v1.0 revision** (after the pilot human coding, logged in the
revision log):
- Quote rule, option 2: one continuous exact passage per evidence field, no
  added comments, several passages listed separately (replaces the current
  ellipsis rule in the checks).
- V3: the 6 items whose V3 quote comes from the prompt need review (4 are
  F1). The V3 rule only says that F2/F3 prompts name the paper; the F1-C1
  prompt names it too and should be added.
- Changes from the disagreements in step 3 above; then freeze and save as v1.0 (codebook section 6, step 2).

**Main experiment after the freeze**, in this order:
1. `python scripts/15_run_experiment.py main`: 200 papers × 15 calls = 3,000.
   Run it in stages (e.g. the first 20 pairs, then the rest), checking spend
   after each stage.
2. Repeat runs: 10% of main-sample prompts (seed 2026), 3 runs each
   (about 600 extra calls). **Not yet implemented** in script 15 (it already
   records `run_index`).
3. `python scripts/16_code_responses.py main`, off-peak, plus V6.
4. Intra-coder agreement: 100 random responses (seed 2026) coded a second
   time in a separate run. **Not yet implemented.**
5. Validation sample of about 200 responses (≥ 5 per model × framing ×
   condition cell, all LLM-coded EXPLICIT / INTEGRITY_CONCERN included),
   author codes all, second coder 50; agreement statistics and decision rule
   in codebook section 6. Then the final hand check of all V1 = EXPLICIT /
   INTEGRITY_CONCERN responses.
6. Analysis per `docs/analysis_plan.md` (frozen once the main run starts).

**Budget: total spend cap $95, cumulative over the whole project.**
- Spent so far: about $8, of which about $5.8 on tested models (pilot and
  smoke test, estimated from token counts) and ¥14.5 (about $2) on DeepSeek
  (claims ¥3.6, P1 ¥8.9, pilot coding ¥2.0).
- Projected: main run about $43.5 (Gemini Search grounding is probably free,
  which would save about $3.4), repeats about $8.7, DeepSeek coding of the
  main sample about $4 at pilot rates. Total about $64, leaving about $30.
- Before each large run, estimate its cost from the pilot rates and stop if
  the cumulative total would pass $95. A spend check / stop in script 15 is
  **not yet implemented**; add it before the main run.

**Cost settings already in place** (keep them):
- Design of 5 cells per paper (C1/C2 with F1 only); no Anthropic refusal
  fallback; 4 concurrent requests per provider.
- DeepSeek: calls only outside peak hours (weekdays 9:00–12:00 and
  14:00–18:00 Beijing time, half price otherwise); fixed prompt prefix first
  for the automatic prefix cache; thinking off for coding.
- Every script is resumable, so a crashed or stopped run never pays twice.
  Script 16 has a hard 5-minute limit per DeepSeek call (a call once hung
  for 12 minutes).

## 5. Conventions

- **Who runs what.** Claude runs every script, including API calls, and
  reports the results; the author does not run code. The author fills only
  the review / coding columns: `claims_review.csv` (approved, edited_*,
  review_note), `p1_review.csv` (p1, p1_source, p1_note) and the coding
  sheets. Before writing new code, Claude explains the plan and waits for OK.
- **Blinding.** Until the author has finished `human_coding_pilot.xlsx`, the
  author does not open, and Claude does not show or quote item-level content
  from: `human_coding_pilot_key.csv`, `data/processed/coding_pilot.csv`,
  `results/coding_pilot_summary.json`, `outputs/llm_calls/coding_pilot.jsonl`.
  Aggregate counts over all 300 responses may be reported. The same applies
  to `practice_key.csv` until the practice round is done.
- **Practice sheet** (`practice_coding.xlsx`) is not used in any analysis.
- Every codebook change gets a version bump and a revision-log row; every
  change to the analysis plan gets a Deviations-log row. The analysis plan
  is frozen once the main experiment starts.
- Commit after each completed step; never overwrite logs in `outputs/`.
