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
| OpenAlex | Citation counts | TODO | TODO |

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
