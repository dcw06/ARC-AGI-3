# Token usage on ARC-AGI-3: GPT-6 Astra and Claude Opus 5.5

Written 2026-11-15. No model was called for this. The public numbers come from the usage record attached
to every step of ARC Prize's public replay recordings (75 recordings, one per game and run). Ours come
from the usage the Claude CLI returned for each call of the 6 November run.

**There is no official ARC-AGI-3 run of Opus 5.5.** So the two models were never run on the same harness.
Opus 5.5 is measured on our harness; Astra on ARC Prize's two official ones. Claude Opus 5 on the official
standard harness is included because it is the only Anthropic model on the same harness as Astra.

## Same budget: the first 100 actions of each of the 25 games

Our run stopped at 100 actions per game, so the public runs are cut at the same point.

| Run | Levels completed | Input tokens | of which cached | Output tokens |
|---|---|---|---|---|
| GPT-6 Astra, official standard harness, high | 76 | 327.5 million | 58.1 million | 0.55 million |
| GPT-6 Astra, provider adapter harness, high | 99 | 305.0 million | 155.7 million | 0.23 million |
| Claude Opus 5, official standard harness, high | 58 | 329.1 million | none recorded | 9.59 million |
| Claude Opus 5.5, our harness, high | 67 | 31.9 million | none | 4.90 million |

- **Input: ours is about a tenth.** The official harnesses resend a growing conversation: the first call
  of a game is about 12,500 tokens in every run, and by action 100 it is 137,000 to 153,000. Our harness
  sends a fresh prompt of about 12,700 tokens every time.
- **Output: Astra writes far less.** Per action, Astra produced 94 to 224 output tokens, Opus 5.5 about
  1,980 and Opus 5 about 3,860. On the same standard harness, Opus 5 produced about 17 times Astra's output.
- **Levels for the tokens:** at this budget Opus 5.5 on our harness completed 67 levels, between Opus 5
  (58) and Astra (76) on the standard harness and below Astra on the adapter (99).

## Whole runs

| Run | Games won | Levels | Actions | Model calls | Input per call, median | Output per call, median (mean) | Input, total | cached | Output, total | of which reasoning or thinking |
|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6 Astra, standard, high | 11 | 132 | 14,141 | 14,034 | 161,403 | 226 (371) | 2,016 million | 352 million | 5.20 million | 4.24 million |
| GPT-6 Astra, adapter, high | 25 | 183 | 7,085 | 7,078 | 125,567 | 17 (118) | 901 million | 447 million | 0.83 million | 0.77 million |
| Claude Opus 5, standard, high | 6 | 95 | 10,557 | 10,500 | 153,385 | 1,407 (3,928) | 1,475 million | none recorded | 41.25 million | not separated |
| Claude Opus 5.5, ours, high (100-action cap) | 1 | 67 | 2,475 | 2,467 | 12,692 | 1,313 (1,984) | 31.9 million | none | 4.90 million | 3.25 million |

Per completed level, whole run:

| Run | Input per level | not cached | Output per level |
|---|---|---|---|
| GPT-6 Astra, standard | 15.3 million | 12.6 million | 39,400 |
| GPT-6 Astra, adapter | 4.9 million | 2.5 million | 4,500 |
| Claude Opus 5, standard | 15.5 million | 15.5 million | 434,000 |
| Claude Opus 5.5, ours | 0.48 million | 0.48 million | 73,100 |

The last row is not comparable with the others: our run was cut at 100 actions and so only reached early
levels, which are short. Use the same-budget table for that comparison.

One more Opus 5.5 data point, on Tycho, bp35 only: 427 actions, 8 levels, 674 model calls, 18.4 million
input tokens plus 38.6 million read from cache and 1.6 million written to it, and 0.55 million output.

## What this does and does not show

- **Harness and model are mixed together** for Opus 5.5 against Astra. The clean model comparison in this
  data is Astra against Opus 5 on the standard harness: about the same input per call, about a tenth of
  the output.
- **Each row is one run.**
- **Tokens, not money.** The recordings carry zero in their cost fields, and I have not looked up prices.
  Cached input is usually billed at a fraction of the normal rate, so the cached column matters for cost.
- "None recorded" for Opus 5's cache means the record shows zero cached tokens. It does not show whether
  caching was in use and unreported.
- Output includes reasoning tokens (OpenAI) or thinking tokens (Anthropic).
- A few steps in the public recordings carry no usage record (107, 7 and 57 in the three runs); they are
  left out of the token totals and counted in the actions.

## Files

- `comparison.json`: every number above, and per-game totals.
- `research/token_usage_v1/fetch_usage.py`: reads the usage records from the public recordings.
- `research/token_usage_v1/compare.py`: builds the tables.
