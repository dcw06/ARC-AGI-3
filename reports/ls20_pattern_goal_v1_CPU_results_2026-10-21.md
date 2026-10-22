# ls20 level 1: pattern recognition and DFS

**The controller passed the exposed first level in the real offline engine.**
It recognized the reference and destination patterns, reached the white cross
in 8 moves, observed the reference rotate into alignment, then reached the
destination in 7 more moves. The engine's completed-level counter increased
from **0 to 1**. No action was taken in the next level.

| Real-engine CPU check | Path-color input | Moves to cross | Moves to destination | Engine level-1 pass | Fresh independent replay |
| --- | --- | --- | --- | --- | --- |
| Retained VLM judgment | Previously recorded color 3; no new inference | 8 | 7 | Yes | Matches every retained event |
| kNN only | Initial-board k=4 estimate, color 3 | 8 | 7 | Yes | Matches every retained event |

Both checks used the same exposed board, so they are software validation of
two input paths, rather than independent evidence of generalization.

## What the agent now does

| Step | Implementation |
| --- | --- |
| Find the patterns | Locate two bounded blue-on-black glyph panels in the visible board; use their different display scales to identify reference and destination |
| Compare their shapes | Remove exact integer display scaling, preserve holes and disconnected marks, and compare all four rotations without allowing reflections |
| Align the patterns | If they differ, use DFS to reach the cross; inspect the actual resulting reference pattern before choosing the next phase |
| Repeat a rotation if needed | Leave the cross and re-enter it, within the shared move and contact caps |
| Reach the destination | After an observed exact match, use DFS to the destination center |
| Verify success | Require an increased engine level counter; matching patterns or arriving at coordinates alone cannot award a pass |

The recognizer found that the initial reference needed one clockwise quarter
turn. After cross contact, the observed normalized patterns matched exactly.
There were no blocked moves, exploration probes or color reassessments.

DFS generated the following route from the visible terrain and selected floor
color; it was not copied from a demonstration:

| Phase | Computed and executed actions | Observed endpoint |
| --- | --- | --- |
| Reach cross | UP, UP, UP, UP, LEFT, LEFT, DOWN, LEFT | Cross center (21, 32) |
| Reach destination | UP, RIGHT, RIGHT, RIGHT, UP, UP, UP | Engine advances to level 2 |

DFS does not guarantee the shortest route. Each move is checked against the
block's full 5x5 footprint, including intermediate positions. Newly uncovered
terrain replaces earlier assumptions. After alignment, only the recognized
destination panel's interior receives the supplied traversability exception;
other black or patterned regions remain obstacles.

## Scope and limitations

**Deterministic recognition and DFS selected the phases and actions.** The
retained VLM supplied only a previously recorded color answer, and the kNN-only
check needed no VLM answer. This is a useful level-specific controller, not
evidence that the VLM learned the rules or solved the level unaided.

The implementation uses supplied control and game-rule knowledge: five-cell
directional movement, cross contact as a rotation opportunity, and destination
entry after pattern alignment. Recognition also assumes this level's palette,
two bounded glyph panels and their relative display scales. Panel positions,
glyph contents and the action route are computed rather than hardcoded.
The controller consumes visible observations and the engine's public level
counter; it does not inspect hidden engine state, game source or future frames.

Missing or ambiguous panels, a changed destination, an unexplained glyph
mismatch, unexpected movement or exhausted budgets stop the controller.
The inherited recovery hook can request a new VLM color assessment after
blocked moves or a failed route, and can probe when the color is uncertain.
Those branches passed scripted tests; they were not needed in these real
episodes and received no new live VLM validation.

## Validation and accounting

| Check | Result |
| --- | --- |
| Pattern-recognition regressions | 12 passed |
| New phase-controller, terrain and replay regressions | 22 passed |
| Connected Linux suite, including earlier DFS, kNN and six-move regressions | 89 passed, zero failures or skips |
| Real CPU installation | Fresh environment; 31 hash-locked game wheels, network isolated |
| Actual checks | Two episodes, each with one reset, 15 moves and one closed local scorecard |
| Independent replay | Two fresh episodes; all observations, actions, comparisons, plans and outcomes matched |
| Combined actual and replay accounting | 60 moves, four resets, four closed local scorecards |
| GPU jobs / new model generations / Kaggle writes | Zero / zero / zero |
| Timing and cleanup | Outer CPU check completed in about 103 seconds; owned groups absent and temporary environment removed |
| Evidence integrity | All 87 tested source files and both final run manifests verified |
| Earlier work | 805 earlier files, the completed kNN GPU evidence inventory and the prior cross-only DFS receipts verified unchanged |

The independent content audit checks replayed behavior. The CPU parent
lifecycle receipt separately checks process exit, final log hashes and cleanup.
Neither is a certification of a new GPU deployment. All previous attempts and
their results remain preserved.

| Reproducibility binding | SHA256 |
| --- | --- |
| Initial observation | `df236a6079d88adad8562e696ffab5f91e6bd21e9efca15de52662f2796b4e4b` |
| Tested CPU source archive | `ed58972ae62b8f63c9ba5a89588678fb89700e7f4fc251a8b74172b49fb86d02` |
| Tested source inventory | `eeecba684c0e8629395c2b33552df10cf2c0ddfabd4f72030a586f68f23d27e8` |
| Earlier evaluation supplying color 3 | `8f419361cd4ba22c585ead45f9e2453bdfb8b73b85fe9238e7352c5a59e68be3` |
| Result using retained VLM color | `d73be8fc26112a8cd884def60f3770abbb684166439e5d093442de2070d79077` |
| Result using kNN color | `61908afa872e1b9ea7e5701c12bd2878f3ea8277a685ff47bb134ead9c143fc3` |

The [integration guide](../research/ls20_pattern_goal_v1/README.md) documents the
recognizer, controller and VLM callback. The
[CPU runner](../scripts/run_ls20_pattern_goal_v1.py) runs the controller and fresh
replay against an existing pinned offline environment. Raw observations and the
interactive visual replay remain private. No new GPU package was launched.
