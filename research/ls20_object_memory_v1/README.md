# ls20: encounter memory, new-object exploration and multi-level DFS

This successor carries encounter memory across level transitions. It seeks
reachable objects it has not yet encountered, then revisits known controls as
needed to align the visible patterns and reach the destination. A level pass
requires the engine's completed-level counter to increase.

**Current real-engine result:** level 1 completes; both new level-2 rings are
encountered and saved, but level 2 does not yet complete. Level 3 was not reached.
See the [CPU results and remaining limitation](../../reports/ls20_object_memory_v1_CPU_results_2026-10-22.md).

| Situation | Behavior |
| --- | --- |
| A new board appears | Recognize its player, panels, cross and additional visible marks; clear old routes and blocked edges |
| A new object is seen | Save a distinct level-local instance and its visible appearance; seeing is not encountering |
| Several similar objects exist | Keep separate location identities, even if their appearance hashes match |
| An object is encountered | Save before/after observation hashes and observed pattern/floor evidence before planning another move |
| A reachable, unvisited object exists | Prefer it over revisiting an already encountered control |
| An object cannot be reached | Defer it for the current terrain state; do not mark it visited; reconsider after relevant changes |
| All reachable new objects are exhausted | Use the cross again if alignment is needed, or navigate to the aligned destination |
| A level is completed | Keep the encounter archive, but use new instance identities and geometry for the next board |
| The engine unexpectedly relocates the player | Save the actual transition, credit no intended encounter, discard the route and replan within the same episode |

## What the memory means

An encounter requires an observed arrival: the actual player center lies in
the object's bounds and the player's occupied footprint intersects its retained
occupied cells. The object must be visible immediately before or after arrival.
This accommodates a small ring whose center is empty while avoiding credit for
standing in a large empty hole. Continuous overlap counts once, until the player
leaves. A planned route, blocked move or stale invisible object earns no visit.

The journal saves an encounter and a complete memory checkpoint before the next
plan or action. The CPU runner uses an fsynced journal and also writes the final
`encounter-memory.json`. Snapshot restoration validates event counts, identities,
appearance records and observation hashes. Identical-looking instances on a new
level remain new instances. An imported archive does not authorize visits in a
new bootstrap scope.

Memory records what changed after contact. It does not infer a causal function
such as teleportation, color switching or refilling from one observation.
Engine level transitions are recorded separately: a replacement image proves
counter advancement but cannot show the final overlap on the old board.

## Navigation and supplied knowledge

The recognizer and DFS are deterministic. No VLM call is made by this runner.
The existing supplied conventions remain: five-cell directional moves, a 5x5
player sprite, palette-specific player/cross recognition, two glyph panels with
different display scales, cross interaction for rotation, and destination entry
after exact observed pattern alignment. Extra object proposals are connected
visible marks, rather than proof of semantic object discovery.

The current k=4 floor estimate retains its raw votes. A tied candidate can be
selected from a color actually traversed earlier in this run. At a dead end,
walls may win the vote; a historical floor color can then be reused only when
it is the sole viable sampled floor candidate. The journal labels either
transfer as a hypothesis and keeps the original vote unchanged. Unresolved or
conflicting evidence stops the controller. Color changes are re-estimated from
current observations.

DFS checks the full swept footprint. Unknown-object overlays cover only their
occupied cells, not surrounding walls or an entire enclosing region. An absent,
unoccluded object's old footprint is never reopened from memory. The floor
currently hidden by the player is an explicit color hypothesis; newly visible
pixels elsewhere retain their observed values. The destination panel is opened
only after an exact pattern match.

The controller retains a computed DFS route while its goal and traversability
remain valid. It replans after relevant changes or a blocked move. Recomputing
a fresh DFS from every intermediate position can reverse a detour and oscillate;
the route suffix is retained to avoid that failure.

Iterative-deepening DFS searches route depths in increasing order, avoiding the
first long detour that plain DFS may return. This matters when the visible bar
expires before a reachable new object. Search is bounded by the remaining
action depth, 50,000 expansions and the caller deadline. Each encounter also
records visible yellow-interface cell counts before and after contact, without
inferring a refill function from one event.

New objects receive priority among navigable candidates. Reference displays,
off-lattice centers, locked destinations and unreachable objects cannot be
treated as reachable goals. Required control revisits remain possible, including
leaving and re-entering the cross for another rotation. The search finds a
minimum-depth route in the current modeled movement graph; this does not cover
unknown object effects or establish an optimal overall exploration policy.

## Bounded CPU check

`scripts/run_ls20_object_memory_v1.py` bootstraps one existing pinned offline
game environment, runs the controller, then starts one fresh independent replay.
It never resets between levels. Defaults: three requested level completions,
384 moves total, 128 per level (configurable up to 192), eight cross entries per level, and no automatic
retries. Search and repeated-state checks add further bounds. No online game
calls, new model generations, GPU jobs or provider writes are made.

The engine may move the player back without a reset request. Such an observed
relocation does not start a new episode or award an intended-target visit. Its
before/after hashes and visible yellow-bar cell counts are recorded without
assuming a cause. Memory is checkpointed and navigation is rebuilt; the third
relocation in one level stops the controller. There is still only one bootstrap
and no additional reset RPC.

Use `--help` for the initial-observation pin, game-environment receipt and
interpreter, new output directory, deadline and level/action limits. The replay
reconstructs every inventory, memory checkpoint, plan, action and outcome. Its
content validation is separate from the parent CPU lifecycle receipt.

Unsupported sprite or panel changes fail closed and preserve the journal.
Implementing the strategy does not establish success on every later level;
real-engine results and remaining limitations are reported separately.
