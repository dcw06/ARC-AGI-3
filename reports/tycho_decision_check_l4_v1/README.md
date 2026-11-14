# Decision check on bp35 level 4 (Tycho + Opus 5.5): no detectable effect

Run 2026-11-09 and 2026-11-10. Eight local level-4 replicates ($14.90), two levels 5-6 replicates
($83.27) and a restart-decision test on level 6 ($26.75), at list price, played on the local engine.

**Result.** Level 4 took 19 or 23 actions in every replicate, with or without the decision check.
The proven optimum is 19. The two arms cannot be told apart.

| Arm | Level-4 actions per replicate | Mean | Deaths / restarts | Cost per replicate | Model calls |
|---|---|---|---|---|---|
| Unchanged (effort `high`) | 19, 19, 23, 23 | 21.0 | 0 / 0 | $1.88 | 32 |
| Decision check (effort `high`) | 19, 19, 23, 19 | 20.0 | 0 / 0 | $1.84 | 29 |

All eight replicates cleared the level; none hit a cost or action cap.

## What was tested

The decision check splits the agent's turns into decision points and plan steps.

- A turn is a **decision point** when no valid plan fixes the next action. A plan stops being
  valid at: the start of a level or attempt; its last action; a departure (the agent submits
  anything other than the next planned action, including RESET); or a surprise (the action changed
  nothing on screen, or a check the agent attached to the plan failed).
- At a decision point the agent must file `commit_plan`, a free tool call, answering three
  questions: what it could do, which route takes the fewest actions, and what the first uncertain
  step could cost. The harness shows what a restart would cost at that moment.
- On every other turn it takes the next planned action.

No "the screen changed a lot" trigger is used. In the public replays of all 25 games, an action
that changes more than 25% of the screen occurs in only three games (bp35 31% of actions, lf52 4%,
ls20 0.2%).

## Design

- Every replicate starts from the same saved state: the action-100 checkpoint of
  `opus55-matched-20261109` (levels 1 to 3 done in 98 actions, 2 actions into level 4).
- Each stops when level 4 is completed (`TYCHO_STOP_AFTER_LEVELS=4`, a new switch).
- The only difference between arms is `TYCHO_DECISION_CHECK=1`. Both arms run the same code.
- A replay with an invalid model key reproduced the saved state exactly before any paid call.

## Findings

1. **The 19-or-23 split is one choice on the first turn.** A new red block is visible at the top
   of the screen. Clicking it at once leads to the 19-action route. Walking two more steps first,
   then clicking it, costs 4 extra actions in backtracking. Five of eight replicates clicked at once.
2. **The earlier run's 23 was not a deficit.** The unchanged agent reaches the optimum in half of
   its replicates, so level 4 has an expected headroom of about 2 actions.
3. **The decision check surfaced the cheaper option but did not force it.** In the one
   decision-check replicate that took 23, the filed plan named both options ("move right twice ...
   or click red block now to probe") and chose the longer one to see more first.
4. **It cost nothing measurable here.** Output tokens rose 13% (8,216 against 7,289 per replicate),
   model calls fell (29 against 32), and cost per replicate was the same within noise.
5. **Decision points were more frequent than estimated:** 6 to 9 of 17 to 21 turns (about 40%),
   against an estimate of 10 to 30%. Plans were 1 to 6 actions long. The agent filed a plan and its
   first action in one response every time; no action was refused.

## Limits

- Four replicates per arm. Three short routes against two is what chance alone produces.
- Level 4 has no failed attempts in any run, so it cannot test the part of the decision check
  aimed at deaths and restarts. Those occur on levels 6 to 9 (120 of the 474 actions in the full run).
- One level of one game. Nothing here says how the check behaves elsewhere.

## Follow-up: levels 5 and 6, one replicate per arm ($83.27)

Both replicates start from the same saved state at the end of level 4 (`l4x-base-1`, 117 actions).

| Run | Level 5 | Level 6 | Level-6 failed attempts | Cost |
|---|---|---|---|---|
| Unchanged | 31 | 87 | 44 actions: one death, three resets | $39.54 |
| Decision check | 31 | 75 | 17 actions: one restart | $43.73 |
| Original full run | 35 | 68 | 17 actions: one restart | $45.50 |
| Optimum | 30 | 41 | | |

With one replicate per arm the 12-action difference on level 6 cannot be attributed to the check.

**The finding that does not depend on the arm.** All three runs opened level 6 with the same 16
actions and then chose RESET, believing the position unwinnable. It was not:

- Those 16 actions are the first 16 of an optimal solution. From the abandoned position the level
  is won in 25 more actions, 41 in total. The continuation was found with the local solver and
  replayed to a win in the game's own logic (`scripts/l6_verify.py`).
- Restarting instead costs at least 1 + 41 = 42 actions from that point.
- The decision check did not stop it. Its filed plan priced the restart at "RESET + 5 + 1 + 4 = 11
  actions to test" and stated that the upper area was "fully seen, no reds". The continuation
  starts with three moves right and a click at the top of the screen.
- After restarting, both replicates come back to the same moves (`... C(33,33) A3 A3`) and then
  continue with three moves right and a click at the top of the screen, as the solver does.

So the loss on level 6 is a wrong belief ("unwinnable", "fully seen"), reproduced in three of three
runs. Asking the agent to price a restart does not correct the belief it prices from.

The Mac slept for 28 minutes during these runs. Both resumed from where they were; no actions or
model calls were lost.

## Follow-up 2: restart check at the abandoned position ($26.75)

Run 2026-11-10. Four replicates start from one saved state: level 6 after the 16-action opening,
the turn before the earlier runs chose RESET (`l6pos-1`; its screen is identical to theirs).

- **Unchanged:** two replicates, same code, flag off.
- **Restart check** (`TYCHO_RESTART_CHALLENGE=1`): the first RESET the agent requests in an attempt
  is not committed. One message asks whether any part of the level is still unseen and reachable,
  and whether any object or action is untried. A second RESET is committed.

Each replicate was capped at 5 more actions.

| Replicate | Actions from the position | Restarted | Took the winning continuation | Cost |
|---|---|---|---|---|
| Unchanged 1 | C(27,39), then out of budget | not yet; its reasoning says "I'd reset anyway" | no | $4.30 |
| Unchanged 2 | C(33,51) C(27,38) RESET A4 A4 | yes | no | $2.65 |
| Restart check 1 | RESET (after the check) | yes | no | $2.96 |
| Restart check 2 | C(33,51) RESET (after the check) A4 A4 A4 | yes | no | $2.20 |

**Result.** The restart check changed nothing. Both replicates read the message and sent RESET
again in the next call (130 and 141 output tokens). None of the four took the continuation.

**Why.** The winning continuation starts with three moves right. Those moves scroll the screen up
by one tile and bring a red block into view at the top; before them it is one tile off screen
(compare the saved frame with the frame before `C(51,3)` in `l56-base-1`). Asked whether anything
was unseen, restart-check replicate 1 answered: "I've got the whole current state visible, so
there's nothing unseen left to check from here. Nothing in this state is untried either." It
treats the current screen as the whole level. All four replicates spent their thinking on a
missing-mechanic hypothesis (does undo keep gravity flipped?) and none walked to the end of the
corridor they stood in.

So the loss is an exploration gap, and a question does not close it: the agent answers the
question from the same belief. What would have closed it is three moves, not more reasoning.

**Limits.** Two replicates per arm, all from one saved state with one conversation history, on
one level of one game. It shows the check failing here; it does not measure a rate.

**Cost notes.**

- Saving the position took three paid steps ($14.63): a first attempt that left the opening at
  its seventh action ($5.81), a replay of level 5 that took 44 actions with a death and two resets
  ($7.10), and one attempt at the opening that followed it ($1.72). Four of five runs so far have
  taken this opening.
- The turn at the position is expensive: 7 to 21 model calls and up to 885,000 input tokens before
  one action. The cost cap is only checked between turns, so replicates overshot a $2.50 cap.

`scripts/l6_prefix.py` and `scripts/l6_verify.py` need the bp35 solver in `.cache/bp35_play/solver/`
(local only; it is derived from the game's source).

## Files

- `results.json` (level 4) and `results_levels_5_6.json`: per-replicate actions, cost, tokens, and
  filed plans. `results_restart_check.json`: the restart-decision runs.
- `tycho_patch/decision_check_on_top_of_local_patch.diff`: apply after
  `../tycho_opus55_matched_v1/tycho_patch/tycho_f68912a_local.diff`. Adds
  `tycho/agent/decision_check.py`, the hooks in `agent.py` (decision check and restart check), the
  stop switch, the level-prefix guard (`TYCHO_LEVEL_PREFIX_GUARD`), and tests (192 tests pass).
  With the flags off, prompts and tools are unchanged.
- `scripts/l4exp.sh` (`prep`, `dry`, `go`; call it by absolute path), `scripts/build_spec.py`,
  `scripts/analyze.py`, `scripts/analyze56.py`, `scripts/analyze_l6rc.py`. The launcher hardcodes
  the paths used on the original machine. For levels 5-6:
  `SRC_RUN=l4x-base-1 STOP_LEVELS=6 DRY_AT=117 ACTION_CAP=417 COST_CAP=56.1`. For the restart test:
  `SRC_RUN=l6pos-1 STOP_LEVELS=6 DRY_AT=177 ACTION_CAP=182 COST_CAP=22.45`, 4th argument `rc` for
  the restart-check arm.
- Full run records: `.cache/tycho/runs/l4x-*`, `l56-*`, `l6seed-1`, `l6start-*`, `l6pos-1` and
  `l6r-*` (local, not in the repository).
