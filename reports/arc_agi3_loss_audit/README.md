# Where ARC-AGI-3 agents lose actions: a 25-game audit

Date: 2026-11-09. Cost: $0 in model calls. Everything here comes from public data:
325 public ARC sessions, Tycho's six published 25-game scorecards, 100 public replay recordings,
our own run logs, and the bp35 simulator that was validated against the game.

The audit was run to check a strategy that had been drafted from bp35 alone. It did not support
two of that draft's main ideas. Read the "What changed" section before building anything.

## Headline numbers

**1. On the public 25 games the official score is already at its ceiling.**
Tycho with Opus 5 (Tycho's published run) wins 25 of 25 games at RHAE 100, using 6,641 actions
and 17 resets. Human baseline for the same levels is 17,135 actions. Improvement can only show up
as fewer actions.

**2. What the published 25-game data says about design choices** (same harness, levels both arms
completed, games as the resampling unit, 20,000 bootstrap resamples):

| Comparison | Action ratio | 95% interval | Reading |
|---|---|---|---|
| Opus 5 vs Opus 4.8, same mode | 0.64 | 0.53 to 0.78 | The model is the largest effect |
| No world model vs orchestrator (Opus 4.8) | 1.23 | 1.12 to 1.38 | Having a world-model builder helps |
| Model written by the actor vs orchestrator | 1.12 | 0.96 to 1.35 | Not resolved |
| Harness-forced model ("trigger") vs orchestrator | 0.99 | 0.82 to 1.18 | No detectable gain, about twice the model calls |

Trigger mode also completed 4 fewer levels than orchestrator (worse in 5 games, better in 1).

**3. Where Tycho + Opus 5 spends its 6,641 actions** (replays of all 25 games, split into attempts;
my per-level counts match the official scorecard on all 100 audited sessions):

| Part | Actions | Share | Spread |
|---|---|---|---|
| Equal to the best count any public run achieved on that level | 5,858 | 88.2% | |
| Extra actions inside successful attempts | 475 | 7.2% | 19 games; largest re86 51, dc22 50, sp80 48 |
| Failed attempts, including the reset | 308 | 4.6% | 8 games; bp35 96, s5i5 58, ls20 56 |

- Failed attempts: 6 deaths cost 95 actions in 3 games; 11 restarts chosen by the agent cost 213
  actions in 7 games. 17 games have no failed attempt at all.
- First levels run at 1.24 times the best-known count, later levels at 1.07.
- No-effect actions: 58 (0.9%). Undo was used 16 times; 6 games offer it.
- "Best known" is the minimum over 19 runs, so it flatters the comparison, and it is not the true
  optimum. On bp35 the best-known sum is 371 and 324 is achievable (below).

**4. bp35 is the outlier game.** It has 4 of the 6 deaths and 31% of all failed-attempt actions.
Two independent Tycho runs fail at the same places:

| Level | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| Opus 5 (published): actions | 17 | 47 | 35 | 31 | 32 | 70 | 53 | 59 | 123 | 467 |
| Opus 5 (published): failed | 0 | 7 | 0 | 0 | 0 | 20 | 10 | 0 | 59 | 96 |
| Opus 5.5 (ours): actions | 15 | 49 | 34 | 23 | 35 | 68 | 54 | 57 | 139 | 474 |
| Opus 5.5 (ours): failed | 0 | 7 | 0 | 0 | 0 | 17 | 10 | 15 | 71 | 120 |
| Best verified clean attempt | 15 | 40 | 34 | 19 | 30 | 41 | 43 | 38 | 64 | 324 |

Levels 1 to 6 are proven optimal. Level 7 in 43 and level 9 in 64 come from the published Opus 5
replay and were replayed to a win in the unmodified game logic. Level 8 in 38 is from our manual play on the local player.

**5. Tycho's built-in planner cannot search bp35.** Given a perfect model (the validated
simulator), one click per block and a compact state key, `plan_bfs` at its default budget of
20,000 nodes solves 0 of 9 levels. At 1,000,000 nodes it solves levels 4, 5 and 6 optimally and
fails on 1, 2, 3 and 8.
In both of our Tycho runs (574 actions) the acting agent never called `verify`, `plan_bfs`, `plan_astar`
or `validate_plan`; on bp35 it wrote its own restricted searches instead, starting at level 7 after dying there.

**6. What one live run can and cannot show.**
- A full 25-game run costs about $3,000 at list price (Tycho's estimate for its Opus 5 run).
- One paired 25-game comparison resolves action-count changes of about 15 to 18% (the interval
  widths above). The whole measured gap to best-known is 12%.
- Across the six Astra-adapter configurations, a game's total varies by a median of 7%
  (up to 32%). These differ in effort setting, so treat this as a rough noise scale.

## What changed

| Draft idea (from bp35) | Audit result |
|---|---|
| Deaths from hazards not yet seen are the main loss | True on bp35 only. Across 25 games deaths are 1.4% of actions, in 3 games |
| Enforce a validated world model before acting | Not supported. Forced model-building shows no gain over optional |
| Build stitcher, segmenter, replay gate, planner | Tycho already ships segment, verify, planners and plan validation |
| A 25-game check costs about $370 | That was at a 100-action cap. Full length is about $3,000 |

What survived: plans inside successful attempts are longer than needed (at least 7% across 19
games, 10% on bp35), and on bp35 the planner tool is too weak to help.

## Planner capacity on bp35

Setup: Tycho's own `plan_bfs`, the validated bp35 simulator as a perfect model, one click per
on-screen block, and a compact state key that drops the step counter where it has no effect.

| Budget (expanded nodes) | Levels solved | Detail |
|---|---|---|
| 20,000 (Tycho default) | 0 of 9 | Every level hits the budget in 1 to 6 seconds |
| 1,000,000 | 3 of the 7 run | Levels 4, 5, 6 found at the proven optimum (19, 30, 41). Levels 1, 2, 3, 8 not found |

- Levels 9 and 7 were not run to completion at 1,000,000: the process reached about 10 GB of swap
  on a 16 GB machine and was stopped. The planner stores a full action list per node.
- Level 4 needs 20,333 expansions, just over the default.
- The state key matters as much as the budget: with the step counter left in the key, level 6
  fails at 1,000,000 nodes; without it, it is solved in 150,729.
- Levels 1 and 3 are solvable by plain search once blocks below the player are dropped from the
  state (430,362 and 85,013 states in `.cache/bp35_play/solver/`). Level 2 needed the
  click-ordering reduction. Both reductions were derived by hand from bp35's rules.
  A general method that finds such reductions is not something this audit provides.

## Opus 5 baseline (standard ARC harness)

From the public Opus 5 run in ARC's own harness (high effort, all 25 games) and its replays.
The score formula used for the 100-action cut reproduces all 350 official game scores we hold.

| Run | Levels (of 183) | Games won | Actions | Score |
|---|---|---|---|---|
| Opus 5, standard harness, full length | 95 | 6 | 10,557 | 40.67 |
| Opus 5, standard harness, first 100 actions per game | 58 | 1 | 2,484 | 19.98 |
| Opus 5.5, our thin harness, 100 actions per game | 67 | 1 | 2,475 | 23.16 |
| Opus 5 in Tycho, full length | 183 | 25 | 6,641 | 100.00 |

Per game: `data/opus5_baseline.json`. The 100-action row is a truncation of a full-length run.

## Cost: Tycho vs the PRO-LONG-based Strands run (Opus 5, 25 games)

| | Tycho | PRO-LONG (Strands fork) |
|---|---|---|
| Cost | $2,986 (published, list price) | $831 (sum of each replay's recorded total) |
| Score | 100.00 | 99.95 |
| Game actions | 6,641 | 8,841 |
| Cost per action | $0.45 | $0.094 |
| Model decisions | 15,103 calls | 937 agent turns |
| Effort | extra high | high |

Strands was cheaper in all 25 games (2.0x to 12x). The two figures use different accounting
and different effort settings, and each is a single run. Per game: `data/cost_tycho_vs_strands.json`.
The Strands scorecard (99.949, 183 of 183 levels) is in `data/strands_scorecard.json`; the
score recomputed from its per-level actions matches exactly.

## Reproduce

Scripts are in `scripts/`; compact outputs in `data/`. Compact replay steps (no raw recordings)
are in `.cache/arc_loss_audit/rec/`.

1. `headroom.py <out.json> <tycho>/artifacts/scorecards <sessions_by_game.json>`: best-known
   per level and each agent's gap. The session index is in `reports/arc_agi3_full_solve_benchmark/`.
2. `paired_modes.py data/headroom.json`: the paired mode comparison.
3. `fetch_recordings.py <index.json> <out dir> <labels>`: streams public replays and keeps
   action, state, level and a frame hash per step.
4. `audit_recordings.py <dir with headroom.json and rec/>`, `failed_split.py <same dir>`:
   attempt decomposition, checked against official per-level counts.
5. `audit_baseline.py`, `report_baseline.py`: the same decomposition for our 100-action baseline run.
6. `bp35_clean_from_recordings.py`, `tycho_planner_capacity.py`: need the bp35 solver in
   `.cache/bp35_play/solver/` (kept local; it is derived from the game's source).
7. `opus5_baseline.py <audit dir> <public sessions dir>`: the Opus 5 baseline table.
8. `strands_costs.py data/strands_scorecard.json <out.json>`: recorded cost totals per Strands replay.

## Limits

- Tycho's published runs are one run per mode. Intervals come from variation across games.
- The published Opus 5 run and our Opus 5.5 run are different model versions.
- Route excess outside bp35 is measured against best-known counts, not true optima.
- The planner test covers bp35 only. Whether planner capacity limits other games is untested.
