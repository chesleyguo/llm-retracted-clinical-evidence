# Candidate models

## Selected for the study (decided 2026-10-27)

Tested models are the default model of each company's consumer app on the
free plan, called through the API. LLM coder: `deepseek-v4-pro`.

| Company | Free-plan default in the consumer app | API model ID | Official training cutoff | Web search via API | Price per 1M tokens (in / out) |
| --- | --- | --- | --- | --- | --- |
| OpenAI | ChatGPT: GPT-5.6 Luna (Free and Go plans) | `gpt-5.6-luna` | Feb 16, 2026 | Yes | $0.20 / $1.20 |
| Google | Gemini app: "Auto" model selection; "most prompts will go to Flash-Lite"; with smart model selection off, all responses use Flash-Lite | `gemini-3.5-flash-lite` | Not published | Yes (Search grounding) | see Gemini pricing page |
| Anthropic | Claude: Sonnet 5.5 (Opus 5.5 is not on the free plan) | `claude-sonnet-5-5` | Jun 2026 (training data and reliable knowledge) | Yes | $2 / $10 |

How each default was established, and how strong the evidence is:
- **ChatGPT.** OpenAI help center article "GPT-6 and other models in ChatGPT"
  (https://help.openai.com/en/articles/20001354-gpt-6-and-other-models-in-chatgpt)
  states that the Free and Go default is GPT-5.6 Luna. The page blocks
  automated fetching (HTTP 403), so this was read from search-engine excerpts
  of the page, not the page itself. API ID and cutoff from the official model
  page: https://developers.openai.com/api/docs/models/gpt-5.6-luna
- **Gemini.** Since Oct 9, 2026, free users can only choose "Auto"; Google
  says most prompts go to Flash-Lite and harder prompts may go to Flash or Pro
  (9to5Google, https://9to5google.com/2026/10/09/gemini-auto-free-users/,
  quoting Google; Google support page
  https://support.google.com/gemini/answer/17004136 not checked directly).
  The router itself is not available through the API, so `gemini-3.5-flash-lite`
  is the closest API equivalent. Official model page:
  https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite
  The last default announced in Google's own release notes
  (https://gemini.google/release-notes/) is Gemini 3 Flash (Dec 17, 2025).
- **Claude.** Secondary sources only: Sonnet 5.5 is available to and the
  default for free users, Opus 5.5 is for paid plans (Notebookcheck,
  https://www.notebookcheck.net/Claude-Sonnet-5-5-is-available-on-the-free-plan-unlike-Opus-5-5.1411941.0.html;
  PCWorld, https://www.pcworld.com/article/3246614/claude-sonnet-5-5-is-here-this-prompt-stops-it-from-wasting-your-usage.html).
  No official Anthropic statement of the free-plan default was found. Model
  facts from https://platform.claude.com/docs/en/models/sonnet-5-5/overview
  (the API rejects `temperature`, `top_p` and `top_k` with a 400 error).

Trials in `retracted_trials.csv` retracted on or after each cutoff (these are
reported descriptively, not used in the RQ2 regression):

| Model | Cutoff used | On or after cutoff | Median years from retraction to cutoff (others) |
| --- | --- | --- | --- |
| gpt-5.6-luna | 2026-02-16 | 37 | 2.66 |
| claude-sonnet-5-5 | Jun 2026 as 2026-06-01 | 15 | 2.93 |
| claude-sonnet-5-5 | Jun 2026 as 2026-06-30 | 8 | 3.01 |

## All candidates checked (research notes)

Checked 2026-10-27 from official documentation unless stated. Prices are list
prices per 1M tokens (input / output) for standard, non-batch calls and change
often; re-check before running the experiment.

| Provider | Model (API ID) | Official training / knowledge cutoff | Web search via API | Price per 1M tokens (in / out) |
| --- | --- | --- | --- | --- |
| OpenAI | GPT-6 Astra (`gpt-6-astra`), flagship | Apr 30, 2026 | Yes (Web search tool) | $10 / $50 |
| OpenAI | GPT-6.1 Sol (`gpt-6.1-sol`) | Apr 30, 2026 | Yes | $2 / $10 |
| OpenAI | GPT-6.1 Terra (`gpt-6.1-terra`) | Jun 1, 2026 | Yes | $1 / $5 |
| OpenAI | GPT-6 Luna (`gpt-6-luna`) | May 18, 2026 | Yes | $0.10 / $0.50 |
| Google | Gemini 4 Argon (`gemini-4-argon`), flagship | **Not stated** in official docs | Yes (Search grounding; 5,000 free requests/month, then $14 per 1,000) | $2 / $10 until Nov 30, 2026; $4 / $20 from Dec 1, 2026 |
| Google | Gemini 3.8 Flash (`gemini-3.8-flash`) | **Not stated** in official docs | Yes (Search grounding, same terms) | $0.75 / $3.75 until Dec 31, 2026; $1.50 / $7.50 from Jan 1, 2027 |
| Anthropic | Claude Fable 5.1 (`claude-fable-5-1`) | Jun 2026 (training data and reliable knowledge) | Yes (web search tool) | $10 / $50 |
| Anthropic | Claude Opus 5.5 (`claude-opus-5-5`), recommended default | Jun 2026 | Yes | $4 / $20 |
| Anthropic | Claude Sonnet 5.5 (`claude-sonnet-5-5`) | Jun 2026 | Yes | $2 / $10 |
| Anthropic | Claude Haiku 5.5 (`claude-haiku-5-5`) | Jun 2026 | Yes | from $0.10 / $0.50 |
| DeepSeek (open weights) | DeepSeek-V4-Pro-0813 (`deepseek-v4-pro`) | **Not stated** in official docs | Yes (separate Search / Fetch API) | ¥9 / ¥27 peak; ¥4.5 / ¥13.5 off-peak (CNY) |
| DeepSeek (open weights) | DeepSeek-V4.1-Flash-1017 (`deepseek-flash`) | **Not stated** in official docs | Yes (separate Search / Fetch API) | ¥2 / ¥8 peak; ¥1 / ¥4 off-peak (CNY) |
| Alibaba Qwen | Qwen3.8-Max (`qwen3.8-max`, snapshot `qwen3.8-max-0902`) | **Not stated** in official docs | Yes, in Singapore and Beijing regions only | $2 / $6 (Singapore) |

Notes:
- Anthropic gives the cutoff as a month only. Counts below treat "Jun 2026"
  both as Jun 1 and as Jun 30.
- Qwen3.8-Max appears to be API-only; the open-weight Qwen models are smaller
  (not checked here). Llama was not researched: no current Llama release was
  found in the official sources checked.
- DeepSeek's pricing page says prices may change.

## Trials retracted after each cutoff

Counted in `data/processed/retracted_trials.csv` (1,003 trials; latest
retraction 2026-10-06). "Borderline" = retracted within 3 months (91 days) of
the cutoff, dropped from the P3 analysis under codebook P3.

| Cutoff used | Model(s) | Retracted after cutoff | Within ±3 months | After and not borderline |
| --- | --- | --- | --- | --- |
| 2026-04-30 | gpt-6-astra, gpt-6.1-sol | 21 | 37 | 5 |
| 2026-05-18 | gpt-6-luna | 16 | 34 | 3 |
| 2026-06-01 | gpt-6.1-terra; Claude if "Jun 2026" = Jun 1 | 15 | 34 | 1 |
| 2026-06-30 | Claude if "Jun 2026" = Jun 30 | 5 | 28 | 1 |
| unknown | Gemini, DeepSeek, Qwen | — | — | — |

All trials retracted after a cutoff have an abstract.

## Sources

- OpenAI models: https://developers.openai.com/api/docs/models
- Google Gemini models: https://ai.google.dev/gemini-api/docs/models,
  https://ai.google.dev/gemini-api/docs/models/gemini-4-argon,
  https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash,
  pricing: https://ai.google.dev/gemini-api/docs/pricing
- Anthropic models overview: https://platform.claude.com/docs/en/models/overview
- DeepSeek pricing: https://api-docs.deepseek.com/zh-cn/quick_start/pricing/
- Qwen3.8-Max: https://www.alibabacloud.com/help/en/model-studio/qwen3-8-max
