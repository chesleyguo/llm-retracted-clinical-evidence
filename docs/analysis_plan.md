# Analysis Plan

## Research questions

**RQ2** *(wording to be completed by the author)*. pubmed_flagged is reported
descriptively only and is not a predictor (see Deviations log).

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

### Sampling (draft, not yet run)

*Draft, 2026-10-27. Strata will be revised once the tested models are chosen.*

- **Frame.** Retracted clinical trials in `data/processed/retracted_trials.csv`
  with an abstract in PubMed (has_abstract = True): 996 of 1,003 trials.
- **Strata.** Retraction year: ≤2022, 2023, 2024, 2025–2026.
- **Main sample.** 100 trials. [To decide: equal allocation, 25 per stratum,
  or another allocation.]
- **Journal cap.** At most 3 trials from the same journal in the main sample,
  counted across all strata.
- **Pilot sample.** 10 further trials for the pilot run, drawn after the main
  sample from the trials not in it, so the two never overlap. The journal cap
  also applies within the pilot sample. [To decide: allocation across strata,
  e.g. 3/3/2/2.]
- **Procedure.** A single random generator with seed 2026 (logged with the
  output). Strata are processed in the order listed above. Within each stratum
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
- Matched control papers are sampled in a later step and are not covered here.

## Models and conditions

## Outcomes

## Statistical analysis

### Pre-specified sensitivity analyses

- **Strong retraction reasons only.** Re-run the main analysis using only
  papers with at least one STRONG reason in `reason_mapping.csv` (see
  inclusion criterion 5), to check that the results do not depend on papers
  retracted only for concerns.

## Deviations log

| Date | Section | Change | Reason |
| --- | --- | --- | --- |
| 2026-10-27 | Inclusion criteria | The paper identifier was changed from OriginalPaperDOI to the PMID (OriginalPaperPubMedID). | Some conference-abstract supplements publish many different papers under one DOI (e.g. 255 records with 255 different titles under one DOI in the 2026-10-28 snapshot), so a DOI does not always identify a single paper. |
| 2026-10-27 | Research questions (RQ2) | pubmed_flagged was removed from the RQ2 predictors and is reported descriptively only. Made before the experiment started, based on the distribution of the variable. | Only 20 of 1,003 retracted trials (2.0%) are not flagged as Retracted Publication in PubMed, too little variation to serve as a predictor. |
