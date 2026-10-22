# ls20: k=4 floor-color estimate and navigation to the white cross

**Question:** Can initial-board color estimates, a VLM path-color judgment and
bounded exploration help the VLM navigate the player to the white cross?

This is an assisted pilot on the exposed level-1 starting board. It supplies
control meanings and visible player/cross geometry, but no solved move sequence.
The previous six-move attempt and its source remain unchanged.

| Stage | Procedure |
| --- | --- |
| Locate | Find the visible 5x5 orange-and-blue player and white cross; refuse ambiguous geometry |
| Estimate floor | Use the four nearest initially visible cells around the player center, with squared Euclidean screen distance |
| Vote | Unweighted color plurality; vote ties return null; equal-distance samples ordered by y, then x |
| Judge path | VLM sees the image, palette and estimate, then returns its own path-color ID or null |
| Explore if uncertain | Up to eight actual VLM-chosen moves toward different nearby color regions, followed by one reassessment |
| Navigate | VLM selects each directional action toward the cross; no correction or scripted fallback |
| Stop | Observed player center reaches the initial cross center, 24 total moves, terminal state, invalid answer or deadline |

Training data are the initial board's visible pixels, excluding the entire
original player footprint, cross cells and bottom interface rows 60–63. Later
frames never enter training. At later positions the original board may already
show the queried floor, which is retained visible evidence rather than a new
hidden-floor prediction. Color IDs refer to the fixed renderer's RGB palette.

The estimate concerns floor near the player's center, not its orange/blue
sprite. Vote fraction is agreement among four samples, not a calibrated
probability. The VLM can disagree with the estimate. An uncertain reassessment
remains null; the runner never replaces it with the kNN prediction.

Exploration tries different nearby regions within the action budget. It cannot
guarantee access to every visible color. Retained before/after evidence records
which regions were attempted and whether the player moved. A blocked move,
movement without a special event, and an untried region are different evidence.
None alone establishes a color's general function. The last 16 moves remain
available for navigation if all eight exploration moves were used.

Success is exact center alignment with the cross's initial center. The engine's
completed-level counter is reported separately. This is not a full-level
solution, object-discovery benchmark, or controlled comparison proving a kNN
benefit. The geometry detector is specific to this exposed board and fails
closed if the assumed visible piece cannot be identified.

The independent audit reconstructs all image/text requests and kNN results,
replays actual actions in the real offline engine, and derives the stop reason
and counters. Existing lifecycle deadlines, process cleanup, native token
checks, provider completion and exact-source authority checks are retained.

Proposed cap: one RTX PRO 6000; requested session timeout 3,600 s, worker 3,300 s,
admission cutoff 3,000 s; at most 27 generations/model HTTP requests (one
canary, up to two color assessments, up to 24 policy replies), 25 offline
actions including one reset and one local scorecard. Canary max16 new tokens;
other replies max256. Zero online game calls/submissions; private account-only,
internet/TPU off, one attempt and no automatic retries. Provider overhead may
extend total time beyond one hour. No GPU authority is supplied by this code.

Check derivation with `python scripts/derive_ls20_knn_path_v1.py --check` and
contracts with `python -m unittest tests.test_ls20_knn_path_v1`.
