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
| PubMed (NCBI E-utilities) | Titles, authors, abstracts, publication types; control paper search | TODO | TODO |
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
