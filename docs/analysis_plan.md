# Analysis Plan

## Research questions

**RQ2** *(wording to be completed by the author)*.
- Time variable: years_since_retraction = model training cutoff date −
  retraction date, in years (codebook P3), treated as continuous. It is
  computed only for models with an officially published training cutoff, so
  Gemini takes part in RQ1 and RQ3 but not in the RQ2 time analysis.
- Paper × model pairs with the retraction on or after the cutoff are not used
  in the regression. They are reported descriptively as a "could not have
  known" baseline.
- pubmed_flagged is reported descriptively only and is not a predictor (see
  Deviations log).

## Inclusion criteria

*Draft, 2026-10-27, for review.*

Retracted papers are drawn from the Retraction Watch database snapshot
`retraction_watch_2026-10-28.csv` (SHA-256 recorded in
`results/01_download_log.jsonl`). The criteria below are applied in order, and
the number of records remaining after each step is reported in a flow diagram.

1. **Record type.** Keep only records with RetractionNature = Retraction.
   Corrections, expressions of concern and reinstatements are excluded.
2. **Subject.** Keep only records with at least one health-sciences subject
   (a Subject entry with the prefix "(HSC)").
3. **Identifier.** Keep only records whose OriginalPaperPubMedID is a valid
   PMID (a positive integer; the placeholder "0" and empty values count as
   missing). The PMID is the unique identifier of a paper. When one PMID has
   more than one retraction record, keep the record with the earliest
   RetractionDate (ties broken by the lowest Record ID).
   When one title has more than one PMID, the PMIDs are treated as the same
   paper if the title, journal and authors all match; in that case the PMID
   that PubMed marks with the publication type Retracted Publication is kept.
   If several PMIDs of the same paper are all marked Retracted Publication,
   the lowest PMID is kept.
   These cases are reviewed by hand, and the decision recorded in
   `data/processed/duplicate_title_review.csv` is final.
4. **Conference abstracts.** Exclude records whose ArticleType includes
   "Conference Abstract/Paper", and records whose OriginalPaperDOI is shared by
   records with different titles (abstract supplements published under a single
   DOI).
5. **Retraction reason.** Each distinct reason in the Reason field is
   classified by hand in `data/processed/reason_mapping.csv`. A record is kept
   if at least one of its reasons is INCLUDE, even if it also has EXCLUDE
   reasons. Records whose reasons are only NEUTRAL and/or EXCLUDE are excluded.
   Records with any OVERRIDE_EXCLUDE reason (Retract and Replace) are always
   excluded, even if they also have INCLUDE reasons: a corrected version of the
   article replaces the retracted one.

   Columns of `reason_mapping.csv`:

   | Column | Content |
   | --- | --- |
   | reason | One reason exactly as written in the Retraction Watch Reason field |
   | count | Number of records with this reason (Retraction, (HSC) subject, valid PMID) |
   | include | INCLUDE: the reason invalidates the paper's findings. EXCLUDE: the reason does not affect the findings. NEUTRAL: the reason is procedural or gives too little information to judge. OVERRIDE_EXCLUDE: any record with this reason is excluded, overriding INCLUDE. |
   | p2_category | P2 category from the codebook (FABRICATION, ERROR, OTHER_UNRELIABLE) |
   | strength | INCLUDE reasons only. WEAK: the reason signals a concern rather than an established problem (Concerns/Issues about Data; Concerns/Issues about Results and/or Conclusions; Duplication of/in Image; Unreliable Image). STRONG: all other INCLUDE reasons. |
   | note | Free-text justification |
6. **Clinical trial.** A paper counts as a clinical trial if its PubMed
   publication types include Clinical Trial (MeSH tree number V03.175.250) or
   one of its subtypes in the MeSH publication type tree:
   - Adaptive Clinical Trial (V03.175.250.050)
   - Clinical Trial, Phase I, II, III, IV (V03.175.250.100 to .400)
   - Controlled Clinical Trial (V03.175.250.500)
     - Randomized Controlled Trial (V03.175.250.500.500)
       - Equivalence Trial (V03.175.250.500.500.125)
   - Human Challenge Trials (V03.175.250.750)
   - Pragmatic Clinical Trial (V03.175.250.751)

   Clinical Trial Protocol (V03.175.313) and Clinical Trial, Veterinary
   (V03.175.375, with its subtype Randomized Controlled Trial, Veterinary,
   V03.175.375.500) are not subtypes of Clinical Trial and are not included.

   Sources, checked 2026-10-27: NLM, Publication Characteristics (Publication
   Types) with Scope Notes, https://www.nlm.nih.gov/mesh/pubtypes.html
   (definitions); MeSH RDF record for Clinical Trial,
   https://id.nlm.nih.gov/mesh/D016430 (tree numbers, current MeSH year).

   The Retraction Watch ArticleType "Clinical Study" is used only as a
   cross-check: agreement between the two sources is reported, and it does not
   decide inclusion.

**Recorded for each included paper (not inclusion criteria).**
- pubmed_flagged: whether the paper's PubMed publication types include
  Retracted Publication (TRUE/FALSE). PubMed's retraction flag is not used to
  decide inclusion. It is reported descriptively.
- pubmed_title_marked: whether the paper's PubMed title starts with a
  retraction label such as "RETRACTED:" (TRUE/FALSE). Reported descriptively
  only; not a predictor in RQ2.
- abstract_is_retraction_notice: whether the PubMed abstract has been replaced
  by the retraction notice: it contains "This article has been retracted" or
  "This article has been withdrawn", cites a policy on article withdrawal, or
  uses notice wording such as "have retracted the following article" or "The
  Editor and Publisher". A "RETRACTED ARTICLE:" label in front of the
  original abstract does not count. Such papers count as having no abstract
  (see Sampling): 26 of the 996 trials with an abstract.

**Manual classification tables.** For `data/processed/reason_mapping.csv` and
`data/processed/duplicate_title_review.csv`, an LLM first proposes a
classification (columns suggested_include, suggested_p2 and rationale; and
suggested_decision and rationale, respectively). The author then reviews every
row and decides. Only the author's columns are used in the analysis:
include and p2_category in `reason_mapping.csv`, and decision (KEEP or DROP)
in `duplicate_title_review.csv`. The strength column in `reason_mapping.csv`
was set by the author. The PubMed publication types used for the
duplicate-title review are stored in `duplicate_title_review.csv`
(pubmed_pub_types), and the raw PubMed records in `data/raw/`.

### Sampling

*2026-10-27.*

- **Frame.** Retracted clinical trials in `data/processed/retracted_trials.csv`
  with an abstract in PubMed (has_abstract = True): 996 of 1,003 trials. A
  PubMed abstract that has been replaced by the retraction notice counts as no
  abstract (25 of the 996, all Elsevier). This rule was added after the
  samples were drawn (see Deviations log), so it is applied by replacement:
  sampled trials with such an abstract are replaced as described under
  "Replacement" in "Matched controls".
- **Strata.** Retraction year: ≤2022, 2023, 2024, 2025–2026.
- **Main sample.** 100 trials, 25 per stratum.
- **Journal cap.** At most 3 trials from the same journal in the main sample,
  counted across all strata.
- **Pilot sample.** 10 further trials for the pilot run, drawn after the main
  sample from the trials not in it, so the two never overlap. The journal cap
  also applies within the pilot sample. Allocation: 4 from ≤2022 and 2 from
  each of the other three strata.
- **Procedure.** A single random generator with seed 2026 (logged with the
  output). Strata are processed in order of how many trials they could supply
  under the journal cap, fewest first: 2024 (69), 2025–2026 (76), 2023 (78),
  ≤2022 (303). Within each stratum
  the trials are put in random order and taken one by one, skipping a trial
  whose journal has already reached the cap, until the stratum quota is met.
  Because the cap is shared across strata, the processing order is fixed in
  advance. The same generator, continued, then draws the pilot sample.
- **Availability** (trials with an abstract, 2026-10-28 snapshot). "With cap"
  is the most a stratum could supply if each journal contributed at most 3
  trials to it.

  | Stratum | Trials | Journals | With cap | Largest journal (trials) |
  | --- | --- | --- | --- | --- |
  | ≤2022 | 434 | 204 | 303 | Canadian Journal of Anaesthesia (26) |
  | 2023 | 334 | 40 | 78 | Computational and Mathematical Methods in Medicine (118) |
  | 2024 | 120 | 42 | 69 | BioMed Research International (25) |
  | 2025–2026 | 108 | 51 | 76 | J Maternal-Fetal & Neonatal Medicine (20) |

  Every stratum can supply 25 + 3 trials under the cap, so equal allocation
  with the pilot is feasible. The cap changes the 2023 stratum most: 262 of its
  334 trials are from Hindawi journals (mass retraction for paper-mill
  activity), and the cap reduces their weight.

### Matched controls

Each sampled retracted trial (main and pilot) is matched to one control trial
found by searching PubMed (`scripts/09_match_controls.py`). A control must:

1. have a PubMed publication type that is Clinical Trial or one of its
   subtypes (criterion 6);
2. share at least one MeSH major topic with the retracted trial (a descriptor
   counts as a major topic if it or one of its qualifiers is starred);
3. be published within 1 year of the retracted trial (PubMed publication
   year);
3a. have the same design class: if the retracted trial is a randomized
   controlled trial (PubMed publication type Randomized Controlled Trial or
   its subtype Equivalence Trial), the control must be one too; otherwise the
   control can be any clinical trial under criterion 1;
4. have an abstract in PubMed;
5. never appear in the Retraction Watch snapshot, under any RetractionNature
   (matched on PMID and on DOI), and have no Retracted Publication, Expression
   of Concern or Published Erratum marker in PubMed (neither as a publication
   type nor as a linked RetractionIn, PartialRetractionIn,
   ExpressionOfConcernIn or ErratumIn notice);
6. not already be a control for another trial, and come from a journal with
   fewer than 3 controls so far (counted separately for the main and pilot
   samples, as in the sampling step);
7. have the MeSH descriptor Humans;
8. not be a protocol, methods or qualitative paper: publication type Clinical
   Trial Protocol, or a title or abstract that marks a protocol (e.g. "study
   protocol", "rationale and design", "we will recruit", protocol-only
   sections such as "Methods and analysis" or "Ethics and dissemination"), a
   methods paper (e.g. "methodology", "statistical model", "missing data") or
   a qualitative study (e.g. "qualitative", "content analysis", "thematic
   analysis", "semi-structured interviews", "focus groups");
9. have an abstract that reports results: a results or findings section, or,
   without one, result wording (e.g. a p-value, "significant", "no
   difference", "reduced", "improved", a percentage) outside the introductory
   sections.

The exact patterns for criteria 7-9 are in `scripts/09_match_controls.py`
(content_problem). They were checked against the 16 controls rejected in the
main-sample review (8 were caught: protocols, a methods paper, qualitative or
feasibility studies, and veterinary studies) and against all approved
controls (none was caught).

**Most specific topic first.** The retracted trial's major topics are tried
one at a time, most specific first. Specificity is the depth of the
descriptor in the MeSH tree (its deepest tree number); ties are broken
alphabetically. The first topic that yields an eligible control is used. For a
topic, the search uses `[majr:noexp]`, so the control must have that exact
descriptor as a major topic, not a narrower one.

**Random choice.** For a topic, all PubMed records found by the search are
sorted by PMID and put in random order with the study's random generator
(seed 2026). They are checked in that order, and the first one that meets all
criteria is the control. This is the same as choosing at random among the
eligible candidates. Trials are processed in a fixed order: main sample by
draw order, then pilot sample by draw order.

**Relaxation.** If no topic yields a control, the rules are relaxed in this
order, and the level used is recorded for each trial:

| Level | Publication year | Topic |
| --- | --- | --- |
| 1 | ±1 year | The retracted trial's own major topics |
| 2 | ±2 years | The retracted trial's own major topics |
| 3 | ±2 years | The parent descriptors (one level up in the MeSH tree) of its major topics, searched with explosion, so the control's major topic is the parent or any descriptor under it |

**Replacement.** A sampled trial that cannot be used, because it cannot be
matched (no control at level 3, or no MeSH major topics) or because its
PubMed abstract is a retraction notice, is replaced by the next trial in the
same stratum's random order from the sampling step that respects the journal
cap and can be used; the replacement is then matched with the rules above
(`scripts/10_replace_unmatched.py`, which replays the sampling step with seed
2026 to recover the order). Replacements are listed in
`results/10_replacement_log.txt`, and the replaced PMID is kept in the column
replaces_pmid.

**Reproducibility.** PubMed changes over time, so every search and fetch
response is cached in `data/raw/pubmed_controls/` with its date, and the MeSH
tree lookups in `data/raw/mesh/`. Re-running the script uses the cache and
reproduces the same controls.

### Target claims and prompts

For every sampled retracted trial and its control, the same procedure
(`scripts/11_generate_claims.py`, `scripts/12_build_claims_review.py`):

1. **Claim extraction** (`prompts/extract_claim.txt`), from the abstract
   only. The model returns a one-sentence claim, its PICO fields, a direction
   (HIGHER, LOWER, NO_DIFFERENCE, or NOT_STATED) and one supporting sentence
   copied from the abstract. The claim covers one outcome; its intervention,
   outcome and direction must be stated in that sentence (the intervention
   named as the sentence names it), while the population and comparison may
   come from elsewhere in the abstract. If the conclusion does not state a
   direction, a results sentence that does is used; if none does, the
   direction is NOT_STATED and the row is flagged; the model must not guess.
   The script checks that the sentence appears verbatim in the abstract
   (whitespace normalized).
2. **Verification** (`prompts/verify_claim.txt`), a separate call that
   checks the extraction: the support sentence states a direction and it
   matches the direction field; the intervention is named as in the sentence;
   one outcome only; intervention, outcome and direction are all in the
   sentence; population and comparison are found in the abstract; and whether
   the sentence uses hedged wording (may, might, suggest, appear, ...). It
   only flags problems (column verify_flags); it changes nothing. The hedging
   answer is also kept as claim_hedged (YES/NO), a descriptive variable for
   each paper.
3. **F1 question** (`prompts/generate_f1.txt`), from the PICO fields only, so
   it cannot reveal the paper. A neutral verb (no direction-implying verbs
   such as reduce or improve), plain language where possible, but specific
   enough to judge whether an answer supports the claim: drug, procedure and
   population names are kept; doses only when the dose is what is being
   compared. Technical terms with no everyday equivalent may stay, since
   clinicians and researchers also use these tools. At most about 30 words.
4. **F2 and F3** use fixed templates (`prompts/f2_paper_question.txt`,
   `prompts/f3_status_question.txt`) filled from PubMed: title (retraction
   labels and brackets around translated titles removed), first author's
   surname, journal (title case, without parenthetical notes, subtitles or a
   parallel title after "="), and journal-issue year.

Model: deepseek-v4-pro, thinking mode off, temperature 0, JSON output. A
failed check is fed back to the model, up to 3 calls per task. Every call is
logged in full in `outputs/llm_calls/claims.jsonl`. All claims and questions
are reviewed by the author in `data/processed/claims_review.csv`; the
approved or edited versions are used in the experiment.

**Filling in the review table.** Rows with verify flags are listed first.
The author fills in three columns; all other columns are written by the
scripts and are not edited.

| Column | How to fill it in |
| --- | --- |
| approved | YES if the paper is used with the claim and F1 question (as given, or as edited in the next two columns). Try to fix a flawed claim by editing it first; NO only if the abstract has no outcome whose direction is stated. |
| edited_claim | Leave empty to use the model's claim. Otherwise write the corrected claim, which replaces it. |
| edited_question | Leave empty to use the model's F1 question. Otherwise write the corrected question, which replaces it. |
| edited_direction | Leave empty to use the model's direction. Otherwise HIGHER, LOWER or NO_DIFFERENCE, the direction of the final (edited) claim. |
| review_note | Free text: the reason for a NO or an edit. |

The final claim, direction and F1 question of each paper are the edited
values where given, otherwise the model's (final direction = edited_direction
if not empty, else direction). `scripts/12_build_claims_review.py` writes them
to `data/processed/claims_final.csv` for the papers now in the sample, with
pair_ready = TRUE when both papers of the pair are approved.

A pair is used only if both papers are approved. When one paper is NO:
- **Control rejected:** the retracted trial is kept, and the next eligible
  control in the same random order of candidates (step 09 rules) replaces
  the rejected one.
- **Retracted trial rejected:** the whole pair is replaced: the next
  retracted trial from the same stratum is taken under the step-10 rule and
  matched to a control.

Replacement papers go through the same extraction, verification and review.
Both replacements are made by `scripts/10_replace_unmatched.py`, run once
after the review of each sample is complete. To make "the next candidate in
the same random order" possible, the candidate order behind every chosen
control is kept in `data/processed/control_draws.jsonl` (append-only). For
the controls chosen before this record existed, it was reconstructed by
replaying steps 09 and 10 from the original samples with the cached searches;
the replay reproduced the committed controls exactly. If a recorded order
runs out, the search continues with the later topics and levels, using a new
generator with seed 2026. In the review table, papers that left the sample
keep their rows, with in_sample = FALSE.

### P1: independent support

For the 100 retracted trials of the main sample (codebook P1):

1. **Search** (`scripts/13_p1_search.py`). deepseek-v4-pro writes a PubMed
   search from the final claim (`prompts/p1_query.txt`): intervention,
   condition and outcome blocks, and a broad version without the outcome. The
   script adds the filters: publication type Systematic Review, Meta-Analysis,
   Guideline or Practice Guideline; published on or after the trial's PubMed
   publication date; not a Retracted Publication. The top 5 results by
   PubMed's relevance ranking are kept; if the search finds nothing, the broad
   version is used. A concept block whose terms PubMed found none of is
   flagged (block_dropped).
2. **Per review**: published_after_retraction (review date, electronic if
   available, after the Retraction Watch retraction date; a review dated only
   by month or year counts from the first day of that period), and
   cites_retracted: YES if the PubMed reference list or OpenAlex
   referenced_works contains the trial, NO if at least one source has a
   reference list without it, UNKNOWN if neither has one; the source is
   recorded.
3. **Suggestion** (`scripts/14_p1_suggest.py`, `prompts/p1_suggest.txt`):
   the model reads the P1 definition from the codebook, the claim and the
   reviews, and suggests YES, NO or UNCLEAR with the reviews it rests on, a
   rationale, and for each review whether it probably included the trial. A
   YES or NO must name at least one review; no review found gives UNCLEAR.
4. **Review**: the author codes every paper in `data/processed/p1_review.csv`
   (p1, p1_source, p1_note); only these codes are used.

PubMed, OpenAlex and model responses are cached in `data/raw/pubmed_p1/`,
`data/raw/openalex_p1/` and `outputs/llm_calls/p1.jsonl`.

## Models and conditions

**Tested models.** One model from each of OpenAI, Google and Anthropic: the
default model of each company's consumer app on the free plan, called through
the API. Checked 2026-10-27; sources and details in `docs/model_candidates.md`.

| Company | Consumer app default (free plan) | API model ID | Official training cutoff |
| --- | --- | --- | --- |
| OpenAI | ChatGPT: GPT-5.6 Luna | `gpt-5.6-luna` | Feb 16, 2026 |
| Google | Gemini app: "Auto", which sends most prompts to Flash-Lite (Flash-Lite for all prompts if smart model selection is off) | `gemini-3.5-flash-lite` | Not published |
| Anthropic | Claude: Sonnet 5.5 | `claude-sonnet-5-5` | Jun 2026 (taken as 2026-06-30) |

When a training cutoff is published as a month only, the last day of that
month is used (codebook P3).

The exact version string returned by each API is recorded with every call.

**Generation parameters.** No temperature (or other sampling parameter) is set
for any tested model; each API's defaults are used. This mimics what an
ordinary user gets in the consumer app, and it also avoids a mismatch between
models, since the Claude Sonnet 5.5 API does not accept a temperature setting.

**Repeatability.** Because default sampling is random, a random 10% of the
main-sample prompts (seed 2026) are run 3 times each, under the same model,
framing and condition. For each coded variable we report the agreement rate
across the 3 runs (the share of prompts where all 3 runs get the same code).

**Conditions.** C0: no extra information. C1: a database record is added to
the prompt for both groups, simulating the article-status information a
retrieval-augmented system would provide. It is generated from metadata with
a fixed template, not from the text of the retraction notice:

- Retracted: "Database record: This article was retracted in {year}. Reasons
  listed: {reasons}." ({year}: Retraction Watch retraction year; {reasons}:
  the paper's reasons with include = INCLUDE in `reason_mapping.csv`, in the
  original English, separated by semicolons.)
- Control: "Database record: No retraction, correction, or expression of
  concern is recorded for this article."

C2: web search enabled.

**LLM coder.** deepseek-v4-pro (DeepSeek-V4-Pro-0813 at the time of checking),
which is not among the tested models.

## Outcomes

## Statistical analysis

### Pre-specified sensitivity analyses

- **Strong retraction reasons only.** Re-run the main analysis using only
  papers with at least one STRONG reason in `reason_mapping.csv` (see
  inclusion criterion 5), to check that the results do not depend on papers
  retracted only for concerns.
- **P1 = NO only.** The main V2 analysis uses retracted papers with P1 = NO
  or UNCLEAR (codebook P1); this sensitivity analysis repeats it with
  P1 = NO papers only. Papers with P1 = YES are not used in any V2 analysis
  and are reported descriptively; they are still used for V1, V3 and V4.
- **Without Hindawi.** Re-run the main analysis excluding papers whose
  Retraction Watch Publisher is "Hindawi" (276 of the 1,003 retracted trials,
  15 of the 100 in the main sample; most were retracted in 2023 for
  paper-mill activity), together with their matched controls, to check that
  the results are not driven by one publisher's mass retraction.

## Limitations

- **Gemini model.** On the free plan, the Gemini app uses "Auto" model
  selection: most prompts go to Flash-Lite, and prompts that need deeper
  reasoning may go to Flash or Pro. The API cannot reproduce this routing, so
  the study uses `gemini-3.5-flash-lite`, which is what free users get for all
  prompts when smart model selection is off. Some app users would have seen
  answers from a larger model.
- **PubMed relevance ranking.** The P1 search keeps the top 5 results by
  PubMed's Best Match ranking, whose algorithm is not published and changes
  over time. The searches are cached so the results can be reproduced, but
  a later search could return different reviews.
- **P1 suggestions are unstable.** In the 10-paper pilot, a small change to
  the suggestion prompt changed the suggested code for several papers, and
  some suggestions misread the reviews. The suggestions only help the coder;
  every P1 code is decided by the coder from the review abstracts.
- **Fewer Elsevier papers.** Elsevier replaces the PubMed abstract of a
  retracted article with the retraction notice. These papers count as having
  no abstract and are excluded, so Elsevier journals are under-represented in
  the sample.
- **Same model for claim extraction and coding.** The target claim and the F1
  question are drafted by deepseek-v4-pro (then reviewed by the author), and
  the same model is the LLM coder that judges stance toward that claim.

## Deviations log

| Date | Section | Change | Reason |
| --- | --- | --- | --- |
| 2026-10-27 | Inclusion criteria | The paper identifier was changed from OriginalPaperDOI to the PMID (OriginalPaperPubMedID). | Some conference-abstract supplements publish many different papers under one DOI (e.g. 255 records with 255 different titles under one DOI in the 2026-10-28 snapshot), so a DOI does not always identify a single paper. |
| 2026-10-27 | Research questions (RQ2) | pubmed_flagged was removed from the RQ2 predictors and is reported descriptively only. Made before the experiment started, based on the distribution of the variable. | Only 20 of 1,003 retracted trials (2.0%) are not flagged as Retracted Publication in PubMed, too little variation to serve as a predictor. |
| 2026-10-27 | Research questions (RQ2); codebook P3 | The retraction-timing variable was changed from BEFORE / AFTER (with a 3-month BORDERLINE band) to the continuous years_since_retraction. Pairs retracted on or after the cutoff are reported descriptively. Made before the experiment started, based on the distribution of retraction dates. | With 2026 training cutoffs, only 1–5 trials per candidate model were retracted after the cutoff outside the 3-month band, too few for a BEFORE / AFTER comparison. |
| 2026-10-28 | Statistical analysis; codebook P1 | The main V2 analysis now uses retracted papers with P1 = NO or UNCLEAR, with a P1 = NO only sensitivity analysis (was: P1 = NO only). Made before any model responses were collected. | P1 can only be judged from the abstracts of systematic reviews, so we expected many papers to be coded UNCLEAR, which would shrink the sample for the main V2 analysis. The excluded case that threatens validity is P1 = YES. This change was made before any model responses were collected. |
| 2026-10-28 | Sampling; Matched controls | A PubMed abstract replaced by the retraction notice now counts as no abstract; sampled trials with such an abstract are replaced by the next trial in the same stratum's random order. Made after the samples were drawn and before any model responses were collected. | Found in the claim-extraction pilot: three sampled trials (26905469, 38897097, 20434046) had the Elsevier retraction notice in place of the abstract, so no claim could be extracted. |
| 2026-10-28 | Matched controls | Added the design rule: a retracted randomized controlled trial must be matched to a randomized controlled trial. Controls were re-matched. Made before any model responses were collected. | In the pilot, single-arm studies were clearly over-represented among controls (90% of sampled retracted trials but 74% of controls were RCTs; 5 of 10 pilot controls had no comparison group), so the groups differed in study design. |
| 2026-10-29 | Recorded for each included paper; Sampling | The rule that detects abstracts replaced by a retraction notice was extended to more notice wordings ("have retracted the following article", "The Editor and Publisher", "This article has been retracted" anywhere in the abstract). Re-scanning all 1,003 trials added one paper (30230402, 26 in total). Made after the main-sample claims review and before any model responses were collected. | The review found a sampled trial whose abstract was a Taylor & Francis retraction notice that the first rule missed (30230402). |
| 2026-10-29 | Matched controls | Added control criteria 7-9: MeSH Humans; no protocol, methods or qualitative papers (including publication type Clinical Trial Protocol); the abstract must report results. They apply to all controls chosen from now on, including replacements; every control approved in the review already meets them. Made after the main-sample claims review and before any model responses were collected. | In the main-sample review, 16 of 100 controls were rejected, several of them protocols, a methods paper, qualitative studies or veterinary studies that the matching rules had let through. |
