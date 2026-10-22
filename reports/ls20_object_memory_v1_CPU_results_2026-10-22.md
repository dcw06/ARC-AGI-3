# ls20: object-encounter memory and exploration across levels

**Implemented and tested; the real offline run completed 1 of the three requested levels.**
The final run used **114 directional moves**, then stopped with
`cross_contact_cap`. A fresh independent engine replay reproduced every retained
observation, object inventory, memory checkpoint, plan, action and outcome.

| Level | Moves | Unknown-object arrivals | Cross entries | Initial floor evidence | Engine result |
| --- | --- | --- | --- | --- | --- |
| 1 | 13 | 0 | 1 | current k4 | Completed |
| 2 | 101 | 2 | 8 | previously traversed color hypothesis | Stopped without a pass |
| 3 | — | — | — | — | Not reached |

## Watch the agent

**Level 1: passed in 13 moves.** The final frame shows the next board appearing.

![Level 1 replay](ls20_object_memory_v1_replay/level-1.gif)

**Level 2: both new rings encountered; level not completed.**

![Level 2 replay](ls20_object_memory_v1_replay/level-2.gif)

[Replay downloads, individual frames and saved encounters](ls20_object_memory_v1_replay/README.md)
include a self-contained interactive HTML viewer and a frame-by-frame action
log. GitHub displays the GIFs and PNGs; download the HTML to use its controls.

Arrival counts are observed entries, not counts of inferred object functions.
Completion comes from the engine counter, rather than pattern alignment,
coordinate arrival or a model's assertion. No action resets the game between
levels, and no additional reset or automatic episode retry is available.

## Implemented strategy

| Step | Behavior |
| --- | --- |
| Observe | Recognize the current player, two glyph displays, cross and additional connected visible marks |
| Remember | Keep a separate instance for each location and level, plus a translation-independent appearance hash |
| Encounter | Require observed player-footprint overlap and center arrival; save the before/after observation hashes and observed changes |
| Persist before acting | Fsync the encounter and full memory checkpoint before the next plan or dispatch |
| Explore | Prefer reachable, never-encountered instances over already encountered controls |
| Defer | Do not award visits for unreachable goals, blocked moves or absent objects; reconsider after terrain changes |
| Solve | Revisit controls when necessary, compare current patterns, then DFS to the aligned destination |
| Advance | Keep the encounter archive but discard stale geometry, routes and blocked edges on each engine level transition |

Two objects can share the same appearance and still be different, unvisited
instances. An object merely seen on screen is not yet encountered. A small
hollow ring can be encountered because the 5x5 player footprint overlaps its
occupied cells; standing in a larger empty hole earns no visit. Continuous
contact counts once until the player leaves.

The saved memory contains **11 encounter events** across
**2 observed levels**. The final `encounter-memory.json`
passed strict snapshot restoration and exactly matches the final controller
result. The fsynced journal also retains intermediate checkpoints.

The final run recorded **2 engine-side relocations**.
Each retained the actual transition and historical memory, credited no intended
target arrival, and cleared navigation before continuing. The runner issued no
reset request. A previous encounter remains history; it does not prove that an
object's earlier effects remain active after a relocation.

## Navigation safeguards and scope

DFS follows its computed route until a relevant change requires replanning.
The controller does not start a new DFS from every intermediate point: that can
reverse a necessary detour and oscillate. A newly discovered reachable instance
can preempt a known-control revisit. DFS checks the complete swept 5x5 footprint.
Iterative deepening searches route lengths in increasing order, finding a
minimum-move route in the current unweighted terrain model when search
completes. This does not establish an optimal exploration policy or account for
unknown object effects. Search is capped at 50,000 expansions, depth 96 and the
remaining action/deadline budget.

Unknown-object overlays cover only occupied cells. A remembered object that is
visibly absent does not turn a wall into passable floor. The current player's
hidden floor is an explicit color hypothesis, kept separate from observed
terrain. A tied k=4 vote may reuse a color actually traversed earlier in the run;
the journal labels this as a transferred hypothesis, not a newly proven fact.
When walls win the raw vote at a dead end, the sole viable sampled floor color
can also be reused if it was traversed earlier. The original vote stays intact.

This remains a deterministic, level-specific assisted controller. It uses
supplied palette and sprite conventions, five-cell controls, and the existing
cross/pattern/destination rules. Extra connected marks are object proposals;
the controller records changes after contact without inventing causal
functions. No hidden game state, engine source, demonstration route or future
frame is used for navigation.

**The requested three-level objective is not yet met.** The final real run
reached only level 2, where the cross-contact cap stopped further play. Both
new ring instances were encountered and saved, but level 2 did not complete;
level 3 was not reached. The memory records bar increases, but this controller
does not yet plan routes through previously observed bar-increase objects to
maintain the timer. Historical visits also do not imply that pattern state
persists after an engine-side relocation. Those limitations remain visible
rather than awarding a pass or silently retrying.

Unsupported sprite or panel changes, unresolved floor evidence, exhausted
budgets or repeated states stop the controller. Larger partially occluded
objects can conservatively remain unconfirmed encounters. These checks do not
establish unaided VLM rule learning, success on all later levels or transfer to
other games. There were **zero new VLM generations and zero GPU jobs**.

## Validation and preserved diagnostics

| Check | Result |
| --- | --- |
| New object/memory tests | 18 passed |
| New controller, terrain and replay tests | 36 passed |
| Iterative-deepening DFS tests, including an independent BFS oracle | 9 passed |
| Frozen-source Linux suite, including all earlier ls20 regressions | 152 passed, zero failures or skips |
| CPU dependency installation | Fresh environment, 31 hash-locked wheels, network isolated |
| Final real-engine evidence | 114 actual moves plus 114 independent replay moves; one initial reset per episode and two closed local scorecards; no in-episode reset RPC |
| Lifecycle | Owned process groups absent; temporary environment removed; final manifests verified |
| Source integrity | 97 frozen source files verified |
| Earlier work | 805 earlier files, prior GPU inventory and validated level-1 receipts unchanged |
| New model generations / GPU jobs / Kaggle writes | Zero / zero / zero |

All five earlier CPU diagnostics are preserved. `CPU-r1` stopped after nine moves
with a repeated-state cycle, and its fresh replay matched that failure. The
corrected runner retains the DFS route suffix. A committed synthetic maze
regression fails on the first frozen source and passes on the corrected source:
old code cycles after nine moves; the final code completes the fixture in 17.
The final results above come from a new source archive and fresh engine run,
rather than relabeling the diagnostic as successful.

`CPU-r2` passed level 1, then stopped after an unexpected relocation in level 2
at 37 total moves. Its independent replay matched that partial result. The
successor records and bounds such environment transitions within the same
episode. `CPU-r3` continued through two relocations but reached GAME_OVER at
81 total moves, before encountering either new ring. Plain DFS repeatedly chose
a long route. The final controller uses iterative deepening to search shorter
routes first; its graph distances independently match BFS on four disclosed
synthetic mazes. `CPU-r4` reached the first new ring and recorded its
bar increase from 8 to 84 cells, but stopped at a wall-dominated k=4 vote. The
final memory fallback retains that raw vote while reusing the sole sampled
floor color previously traversed in the run. `CPU-r5` encountered both rings but stopped with 15 moves left under the
96-move per-level limit; the modeled destination route needed 20. The final
CPU-only check uses a bounded 128 moves per level and 384 total, while search
depth remains capped at 96. The earlier source archives, logs, results and lifecycle
receipts are retained unchanged. Including all five diagnostic runs and their replays adds
508 real-engine moves, ten resets and ten closed local
scorecards to the final-run accounting above. All previous attempts remain
preserved.

| Binding | SHA256 |
| --- | --- |
| Initial observation | `df236a6079d88adad8562e696ffab5f91e6bd21e9efca15de52662f2796b4e4b` |
| Final tested source archive | `83e6b09c51cf5392812493c38325073782cd4787e8ae47c0054db70cbfd72564` |
| Final source inventory | `87bc6b68f54f64d4a6686bd72f330a44ce6f407e77745094a4574116a06a1dec` |
| Final real-engine result | `8b9a406943364e24372f644d8439b0aae944a4d9622a7869dbd729add655f8c8` |
| Saved encounter memory | `4dbb56b4172b84bf204ebcf56dafc45bf3ffcd43373869c4e8bcb8bf5e5499c7` |
| Event log | `326aac236e864dac18b7379e4369416c71deeeeb8d900994694a0495e31c57ba` |

The [integration guide](../research/ls20_object_memory_v1/README.md) explains the
memory semantics and assumptions. The
[CPU runner](../scripts/run_ls20_object_memory_v1.py) accepts a pinned existing
offline game environment and performs the fresh replay. At the user's request,
the 115 observed board images, action/encounter metadata and interactive replay
are now published in the linked replay folder. Full private event journals,
installation and audit records, approvals and provider-operation records remain
local. The original retained evidence is unchanged. CPU content validation and
lifecycle checks do not authorize a new GPU deployment.
