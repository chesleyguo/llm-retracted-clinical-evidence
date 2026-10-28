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
4. **Conference abstracts.** Exclude records whose ArticleType includes
   "Conference Abstract/Paper", and records whose OriginalPaperDOI is shared by
   records with different titles (abstract supplements published under a single
   DOI).
5. **Retraction reason.** Each reason in the Reason field is marked include
   or exclude in `data/processed/reason_mapping.csv`, which also assigns the P2
   category. [To decide: a record is kept if *any* / *all* of its reasons are
   marked include.]
6. **Clinical trial.** A paper counts as a clinical trial if its PubMed
   publication types include Clinical Trial or one of its subtypes (Clinical
   Trial, Phase I–IV; Controlled Clinical Trial; Randomized Controlled Trial;
   Pragmatic Clinical Trial; Adaptive Clinical Trial; Equivalence Trial).
   Clinical Trial Protocol and Clinical Trial, Veterinary are not included.
   [To verify against the MeSH publication type tree before use.] The Retraction
   Watch ArticleType "Clinical Study" is used only as a cross-check: agreement
   between the two sources is reported, and it does not decide inclusion.

## Models and conditions

## Outcomes

## Statistical analysis

## Deviations log

| Date | Section | Change | Reason |
| --- | --- | --- | --- |
| 2026-10-27 | Inclusion criteria | The paper identifier was changed from OriginalPaperDOI to the PMID (OriginalPaperPubMedID). | Some conference-abstract supplements publish many different papers under one DOI (e.g. 255 records with 255 different titles under one DOI in the 2026-10-28 snapshot), so a DOI does not always identify a single paper. |
