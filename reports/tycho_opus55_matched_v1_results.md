# Tycho vs. claude_arc_v1 on lf52 and bp35 (Opus 5.5, 100 actions per game)

Run date: 2026-11-09 (UTC). Artifacts are in [`tycho_opus55_matched_v1/`](tycho_opus55_matched_v1/).

## Question

Does a harness with tools, memory and an optional executable world model help Claude Opus 5.5 solve more of
the games where our harness did worst? We ran [Tycho](https://github.com/NIMI-research/Tycho) (Lehmann et
al., arXiv 2607.28287) on two of our weakest games. The model, reasoning effort and action budget were the
same as in our baseline run.

## Setup

| | Baseline (`research/claude_arc_v1`) | Tycho |
|---|---|---|
| Model | `claude-opus-5-5`, effort high | `claude-opus-5-5`, effort high |
| Budget | 100 scored actions per game, RESETs included | same, via a local `TYCHO_MAX_GAME_ACTIONS=100` patch |
| Turn structure | one stateless call per action | multi-turn conversation per level; up to 40 tool steps before each action |
| Observation | hex text grid, last 8 transitions, at most 8 model-written hypotheses | rendered image plus text grid; recent images and grids kept |
| Tools | none | sandboxed Python with an evidence library over the full history (`wmlib`); notes files; optional world-model builder |
| Memory across levels | hypotheses carried over | notes, plus a level-summary call at each level-up |
| Policy | stage `hypotheses` | `orchestrator`, the paper's selected policy |
| Run | competition run `opus55-competition-20261106T054112Z` | local engine (`normal` mode), then exact trace replay through the ARC API in competition mode |

The game versions were identical: `lf52-271a04aa` and `bp35-0a0ad940`.

## Results (official ARC scorecards)

| Game | Harness | Levels | Score | Actions per level | Resets | Replay |
|---|---|---|---|---|---|---|
| lf52 | baseline | 1 / 10 | 1.82 | 8, then 92 without clearing level 2 | 0 | [replay](https://arcprize.org/replay/45a376b9-4f81-4b86-a203-56989ed42b18) |
| lf52 | **Tycho** | **2 / 10** | **5.45** | 8, 53, then 39 without clearing level 3 | 2 | [replay](https://arcprize.org/replay/6dae6784-7e76-4f57-bbdb-cc2e7448e1d1) |
| bp35 | baseline | 1 / 9 | 2.22 | 17, then 83 without clearing level 2 | 3 | [replay](https://arcprize.org/replay/32ee9606-b8b2-4670-8d98-2bb1796d785b) |
| bp35 | **Tycho** | **3 / 9** | **13.33** | 15, 49, 34, then 2 on level 4 | 1 | [replay](https://arcprize.org/replay/0e0b3223-4d8d-4891-8a16-dffcf3e4e156) |

- **Scorecards.** Baseline: [`09cc9d25`](https://arcprize.org/scorecards/09cc9d25-ec26-4f26-98f8-9cbd60ec69d7), all 25 games. Tycho replay: [`ac6e3999`](https://arcprize.org/scorecards/ac6e3999-e5e4-4488-b981-9d6d80eff73f).
- **The Tycho card's total of 0.75 is not a 25-game result.** Competition mode opens all 25 games, and the 23 games we did not play count as 0. Compare the per-game scores above.
- **Level scores.** Tycho scored 115, the cap, on every level it cleared, except bp35 level 2, which scored 96.0 (49 actions against a human baseline of 48).
- **Clean finishes.** Both Tycho games stopped on `game_action_limit` at exactly 100 actions. The cost cap never triggered.
- **Local run matches the server.** The trace replay reproduced the local results exactly, and frame validation was on.

## Compute and cost

| Game | LLM calls (actor / level summary / animation summary) | Fresh input tokens | Cache-read tokens | Output tokens | Cost |
|---|---|---|---|---|---|
| lf52 | 117 / 5 / 6 | 3.49 M | 10.65 M | 55.9 k | $20.54 |
| bp35 | 135 / 6 / 15 | 1.65 M | 4.82 M | 47.6 k | $9.28 |

Costs are at Opus 5.5 list prices ($4 / $20 / $0.20 / $5 per million tokens for input / output / cache read /
cache write) and were paid from promotional API credits. Wall-clock time was 13.6 min for lf52 and 11.7 min
for bp35, running in parallel. The baseline makes one call per action, so it used about 100 calls per game.
Tycho's actor calls also include Python tool steps. **Tycho therefore spent more inference per action. This
confound is not controlled.**

## What Tycho used

- **The world-model builder was never used.** It was invoked 0 times in both games. Under a 100-action
  budget the actor never asked for it, so the paper's headline component played no part here. The gains
  come from Tycho's other features, listed in the next point.
- **Features in use:** multi-turn context, image input, Python queries over the full evidence history,
  animation summaries, and notes and level summaries kept across levels.
- **Agent notes.** The agent's notes and level insights are in `tycho_opus55_matched_v1/tycho_run/notes/`.
  The full per-step records, including prompts, Python tool calls and reasoning summaries, are in
  `tycho_run/game_<id>.json.gz`.

## Local changes to Tycho

These are applied on top of commit `f68912a`; the full diff is in `tycho_patch/tycho_f68912a_local.diff`.
1. **`TYCHO_MAX_GAME_ACTIONS`:** a whole-game cap on scored actions, with RESETs counted. Upstream only
   caps each level at 5× the human baseline. Stop reason: `game_action_limit`.
2. **Opus 5.5 pricing** of $4 / $20 / $0.20 / $5. Upstream priced `claude-opus-5-5` at Opus 5 rates, which
   made the cost cap and reported costs about 1.3–1.6× too high.
3. **Preserved-thinking compatibility.** Opus 5.5 can reject replayed thinking blocks after the history has
   been edited. On organizations that enforce this check, Tycho retries the request once with
   `prefix_mismatch_behavior: drop_block` and strips the stale reasoning. **This never triggered.** A probe
   (`scripts/binding_probe.py`) showed our organization is not enforced, so Tycho ran with upstream behaviour.
4. **Placeholders for empty or whitespace-only text and tool output.** The API rejects such blocks, and
   upstream would have crashed. This differs from upstream only on that path.
5. **`ANTHROPIC_THINKING_DISPLAY=summarized`** for observability. It does not change billing or behaviour.

All 164 upstream tests and 12 new tests pass. Two review passes found no blocking problems with these patches.

## Caveats

- **One stochastic run** per harness on two games. Treat this as an existence result, not an effect size.
- **Unequal inference per action**, as noted under Compute and cost.
- **Possible training-data familiarity.** All 25 public games may be familiar to the model; the Tycho paper
  makes the same caveat.
- **Exposure classes.** Our holdout ledger classes lf52 as a development game and bp35 as reduced-exposure.
- **Not a test of the world model.** The world-model builder never ran under this budget, so this does not
  test the paper's main claim.

## Reproduce

1. Clone Tycho at `f68912a` and apply `tycho_patch/tycho_f68912a_local.diff`.
2. Build the sandbox with `make sandbox-image`. Docker via Colima works; workspaces must live under `$HOME`
   so the VM can mount them.
3. Run `scripts/run_tycho.sh smoke`, then `run <name>`, then `replay <name>`. The script hardcodes the paths
   used on the original machine.

It reads `ANTHROPIC_API_KEY` from `~/.config/tycho/anthropic.env` and `ARC_API_KEY` from the repo `.env`, and
launches Tycho with a clean environment. `scripts/compare_tycho.py <run-dir>` prints the comparison table.

## Pending

A per-game causal analysis is in progress. It covers how Tycho cleared the levels where the baseline stalled,
the baseline's hypotheses during its stall, and a token-level compute comparison. It will be added to this
report when finished.
