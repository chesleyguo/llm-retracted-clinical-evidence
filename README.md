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
| Retraction Watch database (distributed by Crossref) | Retracted papers, retraction dates and reasons | TODO | TODO |
| PubMed (NCBI E-utilities) | Titles, authors, abstracts, publication types; control paper search | TODO | TODO |
| OpenAlex | Citation counts | TODO | TODO |

Copy `.env.example` to `.env` and fill in the keys before running any script.
