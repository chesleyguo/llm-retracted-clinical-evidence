# Analysis Plan

## Research questions

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

   Columns of `reason_mapping.csv`:

   | Column | Content |
   | --- | --- |
   | reason | One reason exactly as written in the Retraction Watch Reason field |
   | count | Number of records with this reason (Retraction, (HSC) subject, valid PMID) |
   | include | INCLUDE: the reason invalidates the paper's findings. EXCLUDE: the reason does not affect the findings. NEUTRAL: the reason is procedural or gives too little information to judge. |
   | p2_category | P2 category from the codebook (FABRICATION, ERROR, OTHER_UNRELIABLE) |
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

**Manual classification tables.** For `data/processed/reason_mapping.csv` and
`data/processed/duplicate_title_review.csv`, an LLM first proposes a
classification (columns suggested_include, suggested_p2 and rationale; and
suggested_decision and rationale, respectively). The author then reviews every
row and decides. Only the author's columns are used in the analysis:
include and p2_category in `reason_mapping.csv`, and decision (KEEP or DROP)
in `duplicate_title_review.csv`. The PubMed publication types used for the
duplicate-title review are stored in `duplicate_title_review.csv`
(pubmed_pub_types), and the raw PubMed records in `data/raw/`.

## Models and conditions

## Outcomes

## Statistical analysis

## Deviations log

| Date | Section | Change | Reason |
| --- | --- | --- | --- |
| 2026-10-27 | Inclusion criteria | The paper identifier was changed from OriginalPaperDOI to the PMID (OriginalPaperPubMedID). | Some conference-abstract supplements publish many different papers under one DOI (e.g. 255 records with 255 different titles under one DOI in the 2026-10-28 snapshot), so a DOI does not always identify a single paper. |
