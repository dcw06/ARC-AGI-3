# Tycho vs. claude_arc_v1 on lf52 and bp35 (Opus 5.5, 100 actions per game)

Run date: 2026-11-09 (UTC). Artifacts are in [`tycho_opus55_matched_v1/`](tycho_opus55_matched_v1/).

**Summary.**
- **Matched 100-action runs, same model and effort:** Tycho cleared 2 of 10 levels on lf52 (baseline 1)
  and 3 of 9 on bp35 (baseline 1).
- **bp35 continued under ARC's official 5×-per-level rule:** Tycho solved all 9 levels in 474 actions for
  $107.66, scoring 100 ([replay](https://arcprize.org/replay/b642c1f4-99b6-491f-8e84-813ca4634314)).
  GPT-6 Astra needed 488 actions with ARC Prize's Provider Adapter harness at high effort.

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

## bp35 continued to the official per-level limit

We continued the same bp35 trajectory from Tycho's exact checkpoint at action 100. The recorded actions were
replayed on the engine, then the actor and workspace were restored. A zero-cost dry run reproduced the
100-action record exactly, so the matched result above is an exact prefix of this run.

Only budget values changed, and each change is recorded in `run_spec_override.json`:
1. **Actions 100–427.** The whole-game cap was removed (`TYCHO_MAX_GAME_ACTIONS` 100 → 0), so ARC's
   official cutoff of 5× the human baseline per level applied. Total spend was capped at $100. The run
   stopped at that cap with 8 of 9 levels cleared.
2. **Actions 427–474.** The spend cap was raised to $115 (`TYCHO_MAX_INFERENCE_COST_PER_GAME` 100 → 115).
   Tycho won the game at action 474.

| Run | Levels | Score | Actions | Cumulative cost | Official replay |
|---|---|---|---|---|---|
| Matched (100-action cap) | 3 / 9 | 13.33 | 100 | $9.28 | [replay](https://arcprize.org/replay/0e0b3223-4d8d-4891-8a16-dffcf3e4e156) |
| Continued, $100 cap | 8 / 9 | 80.0 | 427 | $100.10 | [replay](https://arcprize.org/replay/a8d9ab0a-653c-4e47-8f29-d932551cdd4d) |
| **Continued, $115 cap** | **9 / 9** | **100.0** | **474** | **$107.66** | [replay](https://arcprize.org/replay/b642c1f4-99b6-491f-8e84-813ca4634314) |

**Actions per level compared with the references.** The GPT-6 Astra column is its high-effort run with
ARC Prize's Provider Adapter harness, which preserves reasoning state between requests.

| Level | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| Human baseline | 21 | 48 | 44 | 38 | 33 | 87 | 86 | 131 | 163 | 651 |
| **Tycho + Opus 5.5** | 15 | 49 | 34 | 23 | 35 | 68 | 54 | 57 | 139 | **474** |
| GPT-6 Astra, Provider Adapter, high | 15 | 40 | 34 | 23 | 31 | 103 | 57 | 71 | 114 | 488 |

**Other full solves of bp35, for reference:**
- **GPT-6 Astra, Provider Adapter harness:** 430–516 actions across its six effort settings.
- **Tycho paper, Claude Opus 5, xhigh effort:** 467 actions at $302.96 (Opus 5 list prices).
- **Claude Opus 5 on ARC Prize's Standard harness (high), the configuration behind its verified 30% score:**
  it cleared 0 of 9 levels, stopping at the level-1 cutoff of 105 actions
  ([replay](https://arcprize.org/replay/ea232c70-c129-495d-b3e7-da1759333aeb)).
- **Our `claude_arc_v1` harness:** 1 level in 100 actions.

**Notes on the continuation:**
- **Level scores.** Every level scored the cap of 115 except level 2 (96.0) and level 5 (88.9).
- **Resets and efficiency.** There were 6 resets in total. The run used 73% of the human action count.
- **The builder ran once, during level 6.** The world-model builder was invoked a single time, at action
  173: 41 builder calls costing $15.46. Level 6 was then solved in 68 actions, against Astra's 103.
- **Cost breakdown for actions 100–427.** $90.82 in total: actor $73.94 (591 calls), builder $15.46,
  animation and level summaries $1.43. Actions 427–474 cost a further $7.56.
- **Spend per action rose through the game.** It was $0.09 per action over the first 100 actions and about
  $0.28 per action from 100 to 427, because the context grew and the builder pass ran.
- **The agent's final notes and model.** Its notes, per-level insights and the `world_model.py` written
  by the builder are in `bp35_continuation/final_notes/`.

## Reference: GPT-6 Astra on these two games

ARC Prize published Astra's Public Demo runs. Per-run session data is in
`astra_reference/astra_lf52_bp35_sessions_summary.json`, taken from `arcprize.org/api/sessions/<guid>` and
linked from [arcprize.org/results/openai-gpt-6-astra](https://arcprize.org/results/openai-gpt-6-astra).
- **Provider Adapter harness.** Astra solved every level at every effort setting: lf52 in 716–809 actions
  (770 at high) and bp35 in 430–516 actions (488 at high).
- **Standard harness, where the model keeps only notes of its choosing.** Astra cleared 2–3 of lf52's 10
  levels and 1 of bp35's 9 levels.

## What Tycho used

- **The world-model builder was not used within the first 100 actions.** It was invoked 0 times in both
  games under the 100-action budget, so the gains up to that point came from Tycho's other features,
  listed in the next point. It ran once later, in the bp35 continuation (see above).
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
- **Not a test of the world model.** The builder never ran within 100 actions. It ran once in the bp35
  continuation, a single instance, so this does not test the paper's main claim.
- **Not a leaderboard result.** bp35 and lf52 are public games, and ARC Prize's verified testing does not
  allow code execution, which Tycho relies on.

## Reproduce

1. Clone Tycho at `f68912a` and apply `tycho_patch/tycho_f68912a_local.diff`.
2. Build the sandbox with `make sandbox-image`. Docker via Colima works; workspaces must live under `$HOME`
   so the VM can mount them.
3. Run `scripts/run_tycho.sh smoke`, then `run <name>`, then `replay <name>`. The script hardcodes the paths
   used on the original machine.

It reads `ANTHROPIC_API_KEY` from `~/.config/tycho/anthropic.env` and `ARC_API_KEY` from the repo `.env`, and
launches Tycho with a clean environment. `scripts/compare_tycho.py <run-dir>` prints the comparison table.

**Budget-only continuation.**
1. Copy the game's `resume/`, `ws/` and `status/` directories into a new run directory.
2. Write a new run spec: `EXTRA_ENV="TYCHO_MAX_GAME_ACTIONS=0 TYCHO_MAX_INFERENCE_COST_PER_GAME=<usd>"
   scripts/run_tycho.sh extend-spec <source-run> <new-run> '<games-json>'`. This uses
   `scripts/build_extend_spec.py` and Tycho's own `build_run_spec`, and it refuses if any non-budget
   setting differs.
3. Continue with `GAMES=<id> EXTRA_ENV=... scripts/run_tycho.sh continue <new-run>`.

## Why Tycho cleared more levels

This section is a per-game trace analysis that has been checked by an adversarial verifier. Claims are
limited to those that held up; the raw output is in
[`tycho_opus55_matched_v1/analysis.json`](tycho_opus55_matched_v1/analysis.json). Neither game was won by
better discovery: the baseline proposed the right mechanics in both. The differences were in escaping a
dead end and in keeping facts across the attempt.

### lf52: escaping a dead end the game never reports as failure

lf52 is peg solitaire played across boards linked by wires, with a movable carrier that ferries a peg
between boards from level 2 onwards.

- **Identical level 1.** Both harnesses solved level 1 with the same 8 clicks.
- **Same dead end.** Both opened level 2 the same way and reached the same frame at action 15, apart
  from the row-0 counter. The pegs had turned grey and a purple key had appeared. The game stays
  `NOT_FINISHED` in that state; there is no GAME_OVER.
- **Tycho's escape (action 16).** An animation-summary call described the key appearing. The actor then
  clicked the key as an experiment ("the orange square might be a lock"), and that restored the level.
  It confirmed with Python queries over the archived animations, used RESET at step 21, and wrote the rule
  to its notes. It found the carrier with ACTION4 at steps 25–26 and solved the level by action 61.
- **The baseline stayed frozen.** It was stuck from t15 to t100: every frame has 0 live pegs.
  - **No way out.** Its controller only resets after GAME_OVER, and its schema and system prompt forbid
    RESET ("Never reset (action 0)"). The key click was its only exit, and it never clicked the key.
  - **Right idea, filed wrong.** At t16 it named the object "a key or tool that actions 1-4 can move".
    It guessed the carrier mechanic early (t9, t20).
  - **Lost the board reading.** After the 8-transition window lost the early boards, it began reading
    empty holes as pegs (from t32). On the frozen board every click did nothing, so it marked jump ideas
    "contradicted".
  - **Repetition.** It spent the remaining actions shuttling the carrier end to end about three times,
    plus 21 clicks that did nothing.

### bp35: memory, not discovery

bp35 is a falling-piece maze: you clear green tiles and float the piece up while avoiding purple spikes,
and ACTION7 is undo.

- **The baseline knew the rules.** By t25 it had the movement, green-removal, float-up and spike rules,
  and at t25 it proposed the route Tycho later used. In its third attempt it reached the decisive state
  in fewer actions than Tycho (24 against 26).
- **It lost rules as they aged out of its window.** The spike rule (supported by t23) was downgraded at
  t33 and dropped by t36. It came back as "hazards or goals, role unknown" just before death 2 (t48),
  which was a rise into the same column Tycho had rejected at its step 42. "ACTION7 is undo" was dropped
  at t29 and later retested only right after no-ops, so the tests could show nothing.
- **Death 3 was unrecoverable.** It came from a board-misreading over-click at t74; undo was the only
  safe exit, and the baseline had forgotten undo.
- **Each death cost a replay.** Each death cost a RESET plus re-running the setup: about 48 actions in
  total. Only 21 actions were left for an attempt that needed 42.
- **Tycho kept its conversation across the RESET.** The spike rule derived at step 22 was cited again
  at steps 32, 42, 44 and 48. At the level-3 boundary the conversation was cleared, and Tycho re-read its
  notes ("HAZARD ... avoid purple columns", "ACTION7 = UNDO"). It solved level 3 in 34 actions with no
  deaths.
- **The margin was thin.** Tycho also died once at level 2 from the same board as the baseline, and it
  spent 2 actions on a click-and-undo.

### Which Tycho features mattered (verified ratings)

| Feature | lf52 | bp35 |
|---|---|---|
| Conversation kept through each level (vs. stateless calls with an 8-transition window) | helpful | decisive |
| Notes and level summaries carried across levels | helpful (level 3) | helpful (level 3) |
| Python queries over the full evidence history | helpful (confirmed the key reset) | helpful (located the piece at the decisive board) |
| Animation summaries | plausible trigger for the key click | unclear (generic scroll captions) |
| Structured GAME_OVER evidence (diff, death frames, archived animation) | — (no GAME_OVER) | helpful |
| Ability to RESET | unclear (the key click was the actual escape) | not needed |
| Image input | unclear | unclear |
| World-model builder, `world_model.py`, `plan.py` (first 100 actions) | not used | not used |

### Compute

Tycho did **not** think more per action. It produced fewer output tokens than the baseline, but it
re-read far more context.

| Game | Harness | Calls | Fresh input | Cache read | Output (thinking) | Cost |
|---|---|---|---|---|---|---|
| lf52 | baseline | 100 | 1.69 M | 0 | 152.8 k (94.8 k) | $9.82 notional |
| lf52 | Tycho | 128 | 3.49 M | 10.65 M | 55.9 k | $20.54 |
| bp35 | baseline | 97 | 1.45 M | 0 | 201.1 k (134.8 k) | $9.81 notional |
| bp35 | Tycho | 156 | 1.65 M | 4.82 M | 47.6 k | $9.28 |

Baseline "notional" cost is the Claude Code CLI's `costUSD` estimate. The run itself was billed to the
subscription.

### Implications for `claude_arc_v1`

1. **Escape dead ends that never signal GAME_OVER.** Allow the agent to RESET, or detect long runs of
   frames with no progress. The current "Never reset" rule plus GAME_OVER-only resets left lf52 frozen
   for 85 actions.
2. **Keep established rules beyond the 8-transition window.** Use a running conversation within the
   level (see the GPT-6 Astra Standard vs. Provider Adapter gap), or a durable "confirmed rules" note
   that the model cannot silently drop.
3. **Give GAME_OVER structured evidence.** Provide the pre-death vs. death diff and frames, so the model
   can extract the fatal rule before the evidence ages out.
