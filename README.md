# LLMs and retracted clinical evidence

Tests whether current large language models present claims from retracted
clinical studies as true, compared with matched non-retracted control papers.
See `docs/codebook.md` for the coding scheme and `docs/analysis_plan.md` for the
analysis plan.

## Raw data: sources and download

Raw files go in `data/raw/` and are not committed. Record the download date of
each file here when you retrieve it.

| Source | Used for | How to get it | Downloaded |
| --- | --- | --- | --- |
| Retraction Watch database (distributed by Crossref) | Retracted papers, retraction dates and reasons | `python scripts/01_download_retraction_watch.py` (CSV from `https://api.labs.crossref.org/data/retractionwatch?<CONTACT_EMAIL>`; provenance logged in `results/01_download_log.jsonl`) | TODO |
| PubMed (NCBI E-utilities) | Titles, authors, abstracts, publication types; control paper search | `python scripts/07_fetch_pubmed.py` (efetch, XML, 200 PMIDs per request; cached in `data/raw/pubmed/`, PMIDs requested logged in `data/raw/pubmed/fetch_log.jsonl`) | 2026-10-28 |
| PubMed, control search | Candidate control trials | `python scripts/09_match_controls.py` (esearch + efetch; responses cached in `data/raw/pubmed_controls/` with search dates) | 2026-10-28 |
| NLM MeSH RDF (SPARQL, https://id.nlm.nih.gov/mesh/sparql) | MeSH tree numbers and parent descriptors for matching | `python scripts/09_match_controls.py` (cached in `data/raw/mesh/descriptor_tree.json`) | 2026-10-28 |
| OpenAlex | Citation counts | TODO | TODO |

Exception: `data/raw/pubmed_controls/` (PubMed esearch/efetch responses used
to choose control trials, with search dates) and `data/raw/mesh/` (MeSH tree
lookups) are committed. PubMed changes over time, so these caches are what
make `scripts/09_match_controls.py` and `scripts/10_replace_unmatched.py`
reproduce the same controls. The Retraction Watch CSV and the step-07 PubMed
cache (`data/raw/pubmed/`) are not committed.

## Reviewing the claims table

`data/processed/claims_review.csv` lists, for every sampled paper, the claim
and F1 question drafted by the model (`scripts/11_generate_claims.py`,
`scripts/12_build_claims_review.py`). Rows with verify flags come first. Fill
in only these columns:

- `approved`: `YES` or `NO`.
- `edited_claim`: leave empty to use the model's claim; otherwise the corrected claim.
- `edited_question`: leave empty to use the model's F1 question; otherwise the corrected question.

Re-running step 12 only adds papers that are not yet in the table, so these
entries are never overwritten. See `docs/analysis_plan.md`, "Target claims and
prompts".

## Setup

Requires Python 3.14.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the values
```

Run scripts from the repository root, e.g.
`python scripts/01_download_retraction_watch.py`.

## Regenerating processed data

`data/processed/retractions_eligible.csv` and `data/processed/pubmed_metadata.csv`
are not committed because of their size. Recreate them with:

```bash
python scripts/06_filter_retractions.py   # -> retractions_eligible.csv
python scripts/07_fetch_pubmed.py         # -> pubmed_metadata.csv, retracted_trials.csv
```

Script 07 reuses the PubMed XML cached in `data/raw/pubmed/` and only queries
PubMed for PMIDs not requested before.
