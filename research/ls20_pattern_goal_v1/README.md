# ls20 level 1: recognize patterns, rotate at the cross, DFS to the destination

The agent compares the reference display with the destination's glyph, uses the
white cross until their observed orientations match, and then uses DFS to reach
the destination. **Success requires the engine's completed-level counter to
increase.** Matching pixels or arriving at a coordinate cannot award a pass.

| Stage | Behavior |
| --- | --- |
| Recognize | Discover two bounded glyph panels from current visible palette pixels |
| Normalize | Remove only exact integer display scaling; retain holes and disconnected glyph marks |
| Compare | Exact binary-mask equality and all four clockwise rotations; no reflection or fuzzy match |
| If already aligned | Navigate directly to the destination |
| If not aligned | DFS to the cross and resample the actual reference pattern |
| If another rotation is needed | Leave the cross and re-enter it; reserve both moves |
| After observed alignment | Open the narrowly identified destination overlay for planning and DFS to its center |
| Confirm | Check the engine level counter before interpreting any replacement-level image |

The phase controller reads the reference from its initially recognized bounds
after every action. The frozen destination glyph and its exact pixel crop must
remain unchanged while unoccluded. The player may cover the destination during
entry; a completed level may replace every original object, so no stale
detector runs before checking the counter.

Recognition is assisted and specific to this exposed ls20 level: background
palette color 5, glyph color 9, two rectangular panels with a complete background
border, and a larger-scale reference versus a smaller-scale destination. Panel
locations and glyph values are not hardcoded. Missing/ambiguous panels or an
unexplained mismatch stop the controller. Symmetric patterns retain every
matching rotation; the controller does not invent a unique orientation.

DFS retains the existing five-cell directional controls and full 5x5 swept
footprint check. The only new traversability exception is the recognized
destination panel interior, enabled after an exact observed pattern match.
Other patterned/black regions remain obstacles. This is an explicit supplied
game-rule assumption, not a general inference that all panels are walkable.
Newly uncovered terrain persists across phase and color changes.

Blocked moves trigger replanning. Two consecutive blocked moves, no usable
route or a repeated-position cycle can request a fresh VLM color judgment even
after a confident answer. Unknown colors retain the bounded exploration hook.
Visible topology/reference changes invalidate stale blocked-edge assumptions.
Without a model callback, the agent stops when it needs new VLM evidence.

Limits: 40 actual moves, at most 4 cross contacts, 8 exploration moves within the
total, 2 color reassessments, and 11 model callbacks including up to 1 initial assessment.
No reset or episode retry is available after the initial bootstrap. DFS is not
shortest-path search; an over-budget route is refused. The caller must own the
process lifecycle, count requests before sending, audit native tokens and
enforce a final deadline. Controller results deliberately do not certify a GPU
lifecycle.

## CPU runner and replay

`scripts/run_ls20_pattern_goal_v1.py` runs the complete level controller in an
owned Linux/WSL CPU worker against an existing pinned offline game environment.
Use `--help` for the initial-observation hash, game receipt/interpreter, optional
retained color assessment, action cap and new output-directory arguments. It
installs nothing and makes no model or provider call. A fresh engine then
replays every retained action, pattern comparison, plan and outcome.

The VLM callback API remains available through
`research.ls20_pattern_goal_v1.controller.run_episode`. The VLM supplies color
assessment/probes; the deterministic recognizer and DFS choose the task phases
and navigation actions. A CPU success is therefore a planner-assisted result,
not proof that the VLM learned the rules or solved the game on its own. New live
inference requires its own reviewed package and fresh compute authority.

Tests: `python -m unittest tests.test_ls20_pattern_recognition_v1
tests.test_ls20_pattern_goal_v1`. The earlier cross-only and GPU experiments
remain unchanged.

The [real-engine CPU results](../../reports/ls20_pattern_goal_v1_CPU_results_2026-10-21.md)
record a level-1 pass in 15 moves for both retained-color and kNN-only inputs,
with a fresh independent replay for each. No new VLM inference was needed.
