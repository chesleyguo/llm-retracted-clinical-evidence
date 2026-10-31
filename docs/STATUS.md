# Project status (handover)

Last updated: 2026-11-01. Read this first in a new session, together with
`CLAUDE.md`, `docs/codebook.md` (now v1.0) and `docs/analysis_plan.md`.

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
| Author's pilot coding (30, done 2026-10-31): sheet check, agreement with the LLM coder, disagreement list | `18` | `results/18_sheet_check.csv`, `results/18_agreement.json`, `results/18_disagreements.md` |
| Codebook v1.0 (2026-10-31); LLM re-coding of the 300 pilot responses with v1.0 | `16`, `19` | `coding_pilot.csv` (v1.0, column codebook_version), `coding_pilot_v0.13.csv` (old codes), `coding_pilot_changes.csv`, `results/19_codebook_v0.13_vs_v1.0.json` |
| Second pilot coding sheet (20 new responses, 4 per framing × condition cell, seed 2026) | `17 round2` | `human_coding_round2.xlsx` + `human_coding_round2_key.csv` |

Analysis numbers fixed so far: V2 main analysis uses 94 retracted trials
(P1 = NO or UNCLEAR); the P1 = NO analysis (n = 5) is descriptive only.

Pilot LLM coding with v1.0 (for reference; do not show per-item codes, see
section 5): 300 coded, 0 failed; V1 EXPLICIT 65, INTEGRITY_CONCERN 5 (as in
v0.13); V3 CITED 102 (was 184); V5 YES 21 (was 28); V6 48 ACCURATE, 12
NO_DETAIL, 5 INACCURATE; quote_not_found in 27 responses (was 33); 1
v3_quote_from_prompt (was 6). 115 responses changed at least one code
(V2 25, V3 86, V3_source 88, V5 9, V1 2, V6 2). Re-coding cost ¥1.94
(v0.13 run ¥1.99), all off-peak, cache-hit share 82.5% over the whole log.
The v1.0 examples come from round 1 items, so v1.0 vs. the author on those
30 is not a clean test; round 2 is.

Web-search citations (checked 2026-10-31): Anthropic returned `citations:
null` on all 228 text blocks of the 20 Claude F1-C2 pilot responses; the raw
responses are complete (the SDK keeps citations, also of unknown types) and
every search ran through dynamic filtering (`web_search_20260209` default).
Not a recording bug; script 15 parses citations correctly, so a main-run
Claude response with citations would be captured. No re-run needed.
Recorded as a limitation (analysis plan, C2; codebook section 1). The coder
now sees only cited entries (OpenAI inline citations, Gemini grounding
sources; Gemini titles are domain names only).

## 2. Waiting on

The author is hand-coding `data/processed/human_coding_round2.xlsx` (20
responses, codebook v1.0). This is the last pilot round: afterwards the
codebook is frozen whatever the agreement (v1.0 if unchanged, otherwise
v1.1). The second coder is not yet chosen; without one, the author re-codes
20 validation responses one week later (codebook section 6).

## 3. Next, once round 2 is coded

1. Check the round 2 sheet and compute agreement with the v1.0 LLM codes:
   give `scripts/18_agreement.py` a round argument (sheet, key and output
   names; the LLM codes are in `coding_pilot.csv`). Same checks and
   statistics as round 1; list disagreements without group, model or
   condition.
2. The author decides on a last revision (v1.1) or none; then freeze
   (codebook section 6, step 2), re-code the pilot only if v1.1 changes the
   prompt, and update this file.

Round 1 results (author vs. v0.13 LLM codes, 30 items): kappa V1 0.79, V2
0.69, V3 0.61, V3_source 0.52, V4 1.00 (F3 only), V5 0.63; V1 sensitivity
1.0 (5/5), precision 0.71 (5/7). Details in `results/18_*`.

## 4. Decided but not yet done

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
5. Validation sample of about 100 responses (seed 2026), stratified by
   model × design cell, at least 40 LLM-coded EXPLICIT / INTEGRITY_CONCERN;
   author codes all; weighted kappa / agreement, V1 precision with a 95%
   Wilson interval. No separate check of every positive. Second coder 50,
   or without one the author re-codes 20 a week later (codebook section 6).
   **Not yet implemented.**
6. Analysis per `docs/analysis_plan.md` (frozen once the main run starts).

**Budget: total spend cap $95, cumulative over the whole project.**
- Spent so far: about $8.3, of which about $5.8 on tested models (pilot and
  smoke test, estimated from token counts) and ¥16.4 (about $2.3) on
  DeepSeek (claims ¥3.6, P1 ¥8.9, pilot coding v0.13 ¥2.0, v1.0 ¥1.9).
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
- **Blinding.** Until the author has finished `human_coding_round2.xlsx`,
  the author does not open, and Claude does not show or quote item-level
  content from: `human_coding_round2_key.csv`, `coding_pilot.csv`,
  `coding_pilot_v0.13.csv`, `coding_pilot_changes.csv` (all in
  `data/processed/`), `outputs/llm_calls/coding_pilot.jsonl`. Aggregate
  counts over all 300 responses may be reported (`results/coding_pilot_summary.json`,
  `results/19_*`). Round 1 (`human_coding_pilot.xlsx`) is done and unblinded.
- **Practice sheet** (`practice_coding.xlsx`) is not used in any analysis.
- Every codebook change gets a version bump and a revision-log row; every
  change to the analysis plan gets a Deviations-log row. The analysis plan
  is frozen once the main experiment starts.
- Commit after each completed step; never overwrite logs in `outputs/`.
