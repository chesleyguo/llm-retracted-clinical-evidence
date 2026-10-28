# Candidate models (research notes, not a decision)

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
