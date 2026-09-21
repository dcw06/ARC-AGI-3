# Closed-loop v1: offline frame and action inspection

The retained evidence identifies specific missed interactions and an observation
contract limitation. Removing examples did not resolve either. No prompt is
promoted, no policy/runtime/notebook is changed, and no new run is authorized or
launched by this inspection.

## Scope and reproducibility

All 600 action records across 30 episodes / 15 paired development games were
inspected programmatically. Initial frames for all 15 games and seven selected
before/intermediate/after cases were visually inspected. This is retrospective
analysis, not 600 individually human-reviewed images or a counterfactual test.
The input is the independently passed, hash-locked R1 evidence archive, SHA-256
`994dc62307777a1adf301986aa2548bb9dad84ab438963d20392736abd493f9d`.

Run `python scripts/inspect_phase4_closed_loop_v1.py` using standard-library Python
from the checkout. It verifies the archive, relevant frozen source bindings, and
the development-game source against the same offline manifest used by the run.
It neither instantiates games nor invokes a model. Source inspection is privileged
retrospective evidence; none of those mechanics were supplied to the policy.

- [Interactive offline frame viewer](phase4_closed_loop_v1_inspection/frames.html):
  choose any episode and action; every returned frame is shown in order.
- [Per-action audit](phase4_closed_loop_v1_inspection/audit.json): exact action,
  legal actions, observation filenames, changed-cell counts/bounds, and visible history.
- [Matched game-source excerpts](phase4_closed_loop_v1_inspection/source_excerpts.json):
  hashes and line-numbered ranges underlying mechanical interpretations.
- [Initial-frame montage](phase4_closed_loop_v1_inspection/initial_frames.png):
  game order is recorded in the audit.

Steps below are **one-based**; archived `step-00` is step 1. Case strips show
pre-action / maximally changed returned frame / final returned frame. Cyan crosses
mark selected clicks on the first image only. The palette is false color for
inspection; authoritative observations are numeric grids. Images in the viewer
are derived from retained frames, not synthetic reconstructions of game state.

## Confirmed observation-contract limitation

All 600 requests contain the correct current grid and the expected previous-grid
history. This is not evidence of a stale-frame or process-bridge corruption bug.
However, the frozen raw representation includes only one recent **action ID**,
not its `action_data`, and only final grids. All 570 noninitial requests have that
restricted history. With stateless calls, previous click coordinates cannot be
recovered from the history hash; unchanged images also cannot reveal where the
last click landed. Coordinates remain in the archived evidence, but not in the
policy-visible history. See `agent/representation.py:113` and `:236`, and
`certification/phase4_closed_loop_v1/contract.py:15`.

Of 600 transitions, **263 have unchanged final frames**. In **108** of those,
intermediate frames do change: 40 `ft09`, 40 `sc25`, and 28 `ls20` transitions.
The next request omits these transient signals. That omission is directly
established; the claim that exposing them would improve solving remains untested.
Separately, 159 transitions change only the bottom row. This geometric count is
not itself a UI classifier; `cd82` below is source-confirmed budget-bar activity.

## Concrete cases

| Game | Retained sequence and visible consequence | Missed interaction / interpretation |
|---|---|---|
| `ft09-0d8bbf25` | Original clicks `(12,34)` 20 times. No-example clicks `(32,16)` once, then `(32,32)` 19 times. Every action returns five frames, with up to 80 changed pixels, then the unchanged final board. | The no-example clicks still miss the interactive tile interiors: `(32,32)` is on the surrounding border. The lower-right outline flashes. Matched source selects `Hkx`/`NTi` tiles, changes their colors, and flashes the outline on this first-level miss path. Varying a click without grounding it in an actionable tile does not fix the interaction. |
| `sc25-635fd71a` | Both arms use only clicks. Original stays at `(12,34)`; all no-example y-coordinates are 14–28. The first response contains 22 frames; later responses contain 13. Every final frame is unchanged. | Neither arm clicks the visible lower 3×3 control grid (source-listed centers: x=25/30/35, y=50/55/60). The first action triggers an introductory demonstration regardless of the chosen action; later retained sequences flash the grid. Source distinguishes demonstration, invalid-click feedback, and slot toggles. The first demonstration must not be mistaken for a successful selected click. |
| `ar25-0c556536` | Both arms click 20 times, always on color-ID 9 background; zero pixel changes. Actions 1–7 remain available. | Source makes clicking a selection operation and directional actions the movement operation. Neither arm attempts movement. This establishes a missed action mode, not a proven winning move or knowledge of the model's internal interpretation. |
| `sk48-d8078629` | Both arms click 20 times, all at background/panel color IDs 5 or 4; every frame remains unchanged. | Source uses `sys_click` sprites to select a piece, then directional actions to manipulate it. Neither arm issues a directional action or selects a visibly different piece. As in `ar25`, coordinate diversity alone does not engage the required interaction mode. |
| `ls20-9607627b` | Both arms issue ACTION1 (“up”) 20 times. The first six actions move the visible piece; steps 7–20 return to exactly the same final frame, with six frames per response and up to 76 transiently changed pixels. | The piece reaches the top obstruction and keeps trying up. Source has a collision branch with feedback, consistent with the retained sequence. No other direction is tried despite all four being legal. The evidence supports failure to adapt after movement stops; it does not establish which alternative would solve the level. |
| `cd82-fb555c5d` | Both arms click empty color-ID 5 locations. Each arm has 13 changed final frames, each changing exactly one pixel on row 63. | Matched source identifies row 63 as the action-budget bar. The main board remains static for all 20 actions: the nonzero frame-change rate is not successful interaction. |
| `wa30-ee6fef47` | Both arms issue ACTION1 20 times. The visible piece moves on steps 1–2. Steps 3–20 leave the board above row 63 unchanged; five of those steps change only the bottom row. | Continued upward actions do not move the piece after step 2. Other legal actions are not explored. This is a retained-frame finding; no specific winning alternative or hidden collision state is claimed. |

Illustrations:
[ft09](phase4_closed_loop_v1_inspection/ft09.png),
[sc25](phase4_closed_loop_v1_inspection/sc25.png),
[ar25](phase4_closed_loop_v1_inspection/ar25.png),
[sk48](phase4_closed_loop_v1_inspection/sk48.png),
[ls20](phase4_closed_loop_v1_inspection/ls20.png),
[cd82](phase4_closed_loop_v1_inspection/cd82.png),
[wa30](phase4_closed_loop_v1_inspection/wa30.png).
The precise episode, step, and archived record for each strip are in
`audit.json` under `illustrated_cases`.

## Disposition and next local checks

Keep both prompts experimental. The evidence supports three distinct problems:
clicks not grounded in interactive locations, failure to switch action modes or
adapt after ineffective actions, and policy-input loss of click/animation history.
It cannot distinguish parsing, coordinate interpretation, game-rule inference,
and action selection as the model's internal cause. The input was textual numeric
grids, not rendered images; the inspection palette was never shown to the model.

The next proposed work is a separately reviewed **observation-contract change**:
retain the last action including coordinates, its final-state effect, and a bounded
description or selection of intermediate frames, without declaring UI changes to
be progress. Before model testing, use these archived cases as CPU-only fixtures:
`ft09`/`sc25` must retain transient feedback, `ar25` must retain the exact missed
click, `ls20` must expose stopped movement, and `cd82` must not count its budget
bar as task progress. Check payload size and token budgets before freezing anything.
These are proposed validation cases, not implemented policy changes.

Visible alternative interactions (tile interiors, lower-grid controls, another
legal direction) are hypotheses for local development checks, not demonstrated
successful counterfactuals. Do not encode game-specific source-derived answers
into a general policy or select a new GPU run from repetition statistics alone.

The 20-action cap still limits this to early progress. Zero completed levels does
not prove that either prompt can never help. Production one-scorecard / 110-distinct-
game certification, production `C_admit`, and exact billing remain open.
