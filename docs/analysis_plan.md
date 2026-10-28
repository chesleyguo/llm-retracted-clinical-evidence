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
  with an abstract in PubMed (has_abstract = True): 996 of 1,003 trials.
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
4. have an abstract in PubMed;
5. never appear in the Retraction Watch snapshot, under any RetractionNature
   (matched on PMID and on DOI), and have no Retracted Publication, Expression
   of Concern or Published Erratum marker in PubMed (neither as a publication
   type nor as a linked RetractionIn, PartialRetractionIn,
   ExpressionOfConcernIn or ErratumIn notice);
6. not already be a control for another trial, and come from a journal with
   fewer than 3 controls so far (counted separately for the main and pilot
   samples, as in the sampling step).

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

**Replacement.** A sampled trial that cannot be matched (no control at
level 3, or no MeSH major topics) is replaced by the next trial in the same
stratum's random order from the sampling step that respects the journal cap
and can be matched; the replacement is then matched with the rules above
(`scripts/10_replace_unmatched.py`, which replays the sampling step with seed
2026 to recover the order). Replacements are listed in
`results/10_replacement_log.txt`, and the replaced PMID is kept in the column
replaces_pmid. One pilot trial was replaced: PMID 38416549 (no MeSH major
topics) by PMID 31593299.

**Reproducibility.** PubMed changes over time, so every search and fetch
response is cached in `data/raw/pubmed_controls/` with its date, and the MeSH
tree lookups in `data/raw/mesh/`. Re-running the script uses the cache and
reproduces the same controls.

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
  P1 = NO papers only.
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

## Deviations log

| Date | Section | Change | Reason |
| --- | --- | --- | --- |
| 2026-10-27 | Inclusion criteria | The paper identifier was changed from OriginalPaperDOI to the PMID (OriginalPaperPubMedID). | Some conference-abstract supplements publish many different papers under one DOI (e.g. 255 records with 255 different titles under one DOI in the 2026-10-28 snapshot), so a DOI does not always identify a single paper. |
| 2026-10-27 | Research questions (RQ2) | pubmed_flagged was removed from the RQ2 predictors and is reported descriptively only. Made before the experiment started, based on the distribution of the variable. | Only 20 of 1,003 retracted trials (2.0%) are not flagged as Retracted Publication in PubMed, too little variation to serve as a predictor. |
| 2026-10-27 | Research questions (RQ2); codebook P3 | The retraction-timing variable was changed from BEFORE / AFTER (with a 3-month BORDERLINE band) to the continuous years_since_retraction. Pairs retracted on or after the cutoff are reported descriptively. Made before the experiment started, based on the distribution of retraction dates. | With 2026 training cutoffs, only 1–5 trials per candidate model were retracted after the cutoff outside the 3-month band, too few for a BEFORE / AFTER comparison. |
| 2026-10-28 | Statistical analysis; codebook P1 | The main V2 analysis now uses retracted papers with P1 = NO or UNCLEAR, with a P1 = NO only sensitivity analysis (was: P1 = NO only). Made before any model responses were collected. | *(reason to be added by the author)* |
