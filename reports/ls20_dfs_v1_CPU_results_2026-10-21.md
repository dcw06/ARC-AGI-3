# ls20: DFS and stall-triggered reassessment

**Implemented. DFS reached the white cross in eight moves in the real offline
game, and a fresh replay independently reproduced every action and state.**
The same result held with the previous VLM color answer and with kNN alone.

| Real-engine CPU case | Color input | Moves | Cross reached | Independent replay |
| --- | --- | --- | --- | --- |
| Retained VLM judgment | Color 3 from the completed k=4 GPU attempt; reused without inference | 8 | Yes | Matches |
| kNN only | Initial-board k=4 estimate, color 3 | 8 | Yes | Matches |

The image-derived route was **UP, UP, UP, UP, LEFT, LEFT, DOWN, LEFT**. It moved
the player from **(36, 47)** to the cross center at **(21, 32)**, with no blocked
moves. Eight pixels in the lower-left reference panel changed after contact.
The engine's completed-level counter remained zero: reaching the cross is not
the full level objective.

## Integrated recovery behavior

| Situation | Controller response |
| --- | --- |
| Normal navigation | DFS computes a route from visible pixels and the selected path color |
| Candidate move | Check the entire 5x5 footprint at all intermediate positions |
| One blocked move | Remember that directed edge as blocked; replan rather than repeat it |
| Two consecutive blocked moves | Request a new VLM color assessment even if the original answer was confident |
| No usable route or repeated-position cycle | Also request reassessment |
| New assessment is uncertain | Allow up to eight VLM-chosen color probes, then reassess; retain null if still uncertain |
| No model callback available | Stop when new VLM evidence is needed; do not invent an answer |
| Unexpected movement, action cap or deadline | Stop and retain the observations |

Recovery is implemented and its scripted callback tests pass. Neither successful
real-engine case needed it. **No new live VLM color assessment or exploration
ran**, so this does not establish how reliably the VLM will recover from stalls.

DFS, rather than the VLM, selected all eight navigation actions. The planner
reads visible starting/current pixels and explicitly supplied control meanings;
it reads no hidden engine state, demonstration route or future frames. It uses
the existing board-specific player/cross detector and assumes the chosen floor
color beneath occluding player/cross pixels. Newly uncovered cells replace the
player-floor assumption. This is assisted navigation on the exposed board,
not evidence that the VLM learned to plan, discover objects or solve the level.

DFS is not shortest-path search. Its neighbor order prefers positions closer to
the goal, with ties by action ID. The observed eight-move route is longer than
the separately known six-move route; the implementation does not claim optimality.

## Validation and accounting

| Check | Result |
| --- | --- |
| New DFS/controller/replay tests | 22 passed |
| Focused connected Linux suite including kNN and six-move regressions | 55 passed; zero failures or skips |
| Real CPU game dependency installation | 31 hash-locked wheels, no network |
| CPU cases | Two actual episodes and two independent replay episodes |
| Per actual episode | One reset, eight dispatches, one closed local scorecard |
| Combined actual and replay accounting | 32 dispatches, four resets and four closed local scorecards |
| GPU jobs / new model generations / provider writes | Zero / zero / zero |
| Cleanup | Owned groups absent; temporary environment removed; final receipts and logs verified |
| Previous evidence | 805 earlier files and the completed k=4 run's evidence inventory unchanged |

The first CPU diagnostic also reached the cross, but its worker hashed a log
before final stdout completed. That diagnostic is retained separately. The
runner now excludes the active log from the worker inventory and seals it in
the parent after worker exit and cleanup. The final results above come from a
fresh source archive and two fresh CPU cases; every final manifest entry checks.

| Reproducibility binding | SHA256 |
| --- | --- |
| Initial observation | `df236a6079d88adad8562e696ffab5f91e6bd21e9efca15de52662f2796b4e4b` |
| Final checked CPU source archive | `5d04a542ed6aaece75b993588224796070d2313dd99acd11f24255538ca34005` |
| Final checked source inventory | `f960b8fe6bb0ecbca3582e2b111790abbb642c510939a7ba43ef2e845b380c22` |
| Earlier VLM evaluation supplying color 3 | `8f419361cd4ba22c585ead45f9e2453bdfb8b73b85fe9238e7352c5a59e68be3` |
| DFS CPU result with retained color | `e7af7d268c370169cc579ecbd936e1a1ad041575e91f59708e1d86c0be51611d` |
| DFS CPU result with kNN color | `d00ab7eadc8ebdc1cc027f26a5a6505d5f55a3149b502b254c8db2bca1e574f8` |

The [controller and integration guide](../research/ls20_dfs_v1/README.md) expose
the VLM callback hook. [The CPU runner](../scripts/run_ls20_dfs_v1.py) executes
without new model calls and independently replays the route. New live inference
still needs a separately reviewed package and fresh compute authority. Previous
GPU attempts remain consumed and preserved. Raw frames and the visual replay
stay private; this report contains aggregate results only.
