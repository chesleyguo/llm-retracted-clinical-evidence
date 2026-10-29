# Project: LLMs and retracted clinical evidence

## What this project is
A research project (PhD application writing sample) testing whether current LLMs
propagate claims from retracted clinical studies.
- RQ1: When users ask clinical questions, do LLMs present claims from retracted
  clinical trials as true? Compared against matched non-retracted control papers.
- RQ2: Which factors predict whether a model recognizes a retraction (retraction
  before/after training cutoff, retraction reason, citation count)?
- RQ3: Does adding retraction metadata to the prompt, or enabling web search,
  correct the errors?

## Key documents
- docs/codebook.md: coding scheme for model responses. Follow it exactly.
  Sections 2-3 are inserted verbatim into the LLM-coder prompt; read them from
  this file, never hard-code a copy.
- docs/analysis_plan.md: pre-registered analysis plan (do not change after the
  full experiment starts).

## Rules
- Raw data in data/raw/ is never modified. Processed data goes in data/processed/.
- Model outputs are append-only (one JSONL record per call). Never overwrite.
- Every API call record includes: paper id, group, framing, condition, model name,
  model version string returned by the API, timestamp, full prompt, full response,
  parameters.
- In web-search mode, the citations and source information returned by the API
  are saved in full in the record.
- API keys live in .env and are never committed.
- Use a fixed random seed (2026) for all sampling, and log it.
- Every filtering step prints and saves how many records remain (for a flow diagram).
- Scripts must be resumable: skip calls that already succeeded.
- Prefer small, readable scripts in scripts/ numbered by pipeline step
  (01_..., 02_...). Explain any statistics choice in comments.
- I am learning: before writing code, briefly explain the plan and wait for my OK.
- Claude runs all scripts itself (including API calls) and reports the results.
- At the start of a session, read docs/STATUS.md; update it at the end of a
  block of work.
- Blinding: while I am hand-coding a sheet, never show or quote item-level LLM
  codes or the sheet's key file (group, model, condition) for its items.
  Aggregate counts are fine.
- Budget: total API spend is capped at $95 for the whole project. Estimate the
  cost before any large run, and report the actual spend after it.
- DeepSeek calls run outside peak hours, with the fixed part of the prompt first
  (prefix cache).
- Every codebook change gets a version bump and a revision-log row; every change
  to the analysis plan gets a row in its Deviations log.
- New dependencies are pinned in requirements.txt.
- Commit after each completed step.