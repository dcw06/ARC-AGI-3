# Mac teammate catch-up and M1 checkpoint — 2026-10-24

## Source and assignment

Read the supplied `ARC_AGI3_Team_Research_Plan.pdf` (12 pages). Its Mac ownership
is M1, revisable object representation and evidence memory, followed by M2,
inferred transition models and bounded planning. The pasted handoff asks to start
with the smallest useful M1 milestone; this delivery follows that order.

Verified checkout: `/Users/elena/projects/ARC-AGI-3-discovery`, branch
`teammate/mac-world-model`, HEAD `1ad910bcd3a541279c4a6f224cce15368bec74aa`.
The tree was clean before changes. No applicable AGENTS.md was found in the
checkout or its ancestor directories. Read README, Makefile, setup helper, public
engine snapshot adapter, existing representation and action-effect records, and
the supplied-rule geometry interface. No other checkout or reference solver was
modified; no newer branch was merged, and no commit or push was made.

Keep historical results distinct: the plan reports an instructed VLM attempt with
0 completed levels in 40 moves, a separate 6/6 supplied-route-following attempt
without a level pass, and a deterministic pattern/DFS level-1 pass in 15 moves.
Later object-memory replay at cbed437 is separate development evidence, not this
frozen baseline or an uninstructed VLM result.

## Environment verification

`make setup` initially failed because its shell PATH did not find uv. Re-running
`make setup UV=/Users/elena/.local/bin/uv` completed without changing any pins.
This installed a fresh worktree-local environment, not a copied environment.

| Item | Verified result |
|---|---|
| OS/architecture | macOS 26.6.2, arm64 |
| Python | 3.12.15, discovery `.venv/bin/python` |
| uv | 0.12.23 |
| Framework revision | 4743e7d0aaae0ded0d98a89a7e282e63564cd58b |
| Dependency check | 57 packages compatible |
| Original portable suite | 102 tests passed, 16.830 s |
| New M1 suite | 26 tests passed, 0.039 s in the recorded run |
| Real game assets | `scratch/ls20-baseline/` absent; offline engine integration blocked |
| Model/GPU/game actions | 0 / 0 / 0 |

Setup records are under ignored `reports/runs/setup-mac/`: `environment.json`,
`installed-packages.txt`, `baseline-tests.txt`, and `m1-tests.txt`. Transitive
dependencies were resolved by the existing setup recipe and frozen in that record;
the Makefile pins themselves were not altered. A temporary pypdf installation
outside the project environment was used only to read the supplied plan.

## Implementation

New isolated module: `research/ls20_discovery_mac/` (`scene.py`, `memory.py`,
`schema.json`, `__init__.py`, README). New focused tests:
`tests/test_ls20_discovery_mac_m1.py`. New replayable visual diagnostic:
`scripts/demo_ls20_discovery_mac_m1.py`.

Reuses the portable action-effect record contract and accepts the existing public
engine snapshot shape. No shared-interface, source-evaluator, supplied-rule
detector or Linux supervisor changes. The runtime import closure consists of
standard library modules and the existing rule-neutral action-effect records.
Pillow is used only by diagnostics, jsonschema only by schema tests; both are
already installed by the pinned setup's dependency closure.

The core decision is to preserve uncertainty instead of installing game semantics:
all colors become observation-local region proposals, with masks, internal crops,
shape and adjacency. Compatible identity links retain alternatives; merge/split
and occlusion ambiguity do not erase raw evidence. Tentative control-role hints
are linked to action-associated translation evidence, never promoted to fact.
Cell history preserves covers and newly observed terrain without assigning floor
labels. Per-frame changes, unchanged frames, failed dispatches and missing outcomes
stay distinct. A missing outcome stops further appends rather than assuming a
current state. Atomic snapshots reconstruct exactly from retained raw inputs.

## Results and failures

| Fixture/check | Result | What it establishes |
|---|---|---|
| All 16 palette IDs and global permutation | Pass | No fixed player/background color or geometry role constant |
| Exact mask, ring crop, bbox and adjacency | Pass against literal expected answers | Basic region geometry |
| Relocation and duplicate shapes | Pass | Compatible identities survive without forced assignment |
| Merge/split; partial/full occlusion | Pass | Multiple and historical links retained |
| Recoloring within episode | Known identity failure retained | Raw change survives; recolored identity is not recovered |
| Terrain covered/revealed | Pass | Earlier pixels are retained, not replaced by an assumption |
| Transient return to same image | Pass | Final-frame-only no-op shortcut avoided |
| Same visible state/action, different results | Pass | Conflicting transition references survive |
| Failed/unknown request | Pass | No invented observation; unknown outcome suspends episode |
| Tampered derived event with recomputed checksum | Rejected | Restore verifies reconstruction, not checksum alone |
| Hidden-mode pair | Same last two frames; distinct initial cues retained | Information retention only |

Hidden-mode comparison (fixed evaluator rule, not learned): a two-frame raw view
and a current-scene-only view cannot distinguish either cue; persistent memory
retains the correct cue in both cases (2/2). This is a deterministic constructed
counterexample to current-image sufficiency, not an estimated success rate or
evidence that a hypothesis policy improved. The toy's required action comes from
the evaluator and is not supplied to the memory module.

Six diagnostics restored exactly. Snapshot sizes: relocation 3,943 bytes;
merge/split 6,816; occlusion 5,528; recoloring failure 3,229; each hidden-mode trace
8,671. These are tiny synthetic cases, not a scalability benchmark. HTML includes
full masks and provenance; the generated PNG was visually inspected.

## Remaining scope

M1 is a **first checkpoint**, not finished research. Missing: co-motion grouping,
multi-color/disconnected object hypotheses, resolved persistent identity,
evidence-based role revision, semantic terrain/encounters/failed-edge inference,
and a matched-policy prospective comparison. The all-history matching baseline
can grow quadratically and needs a bounded candidate index before longer runs.
M2 models/planning are not implemented in this checkpoint, as requested by the
handoff's M1-first sequence.

Alan still needs to supply authorized `ls20-9607627b` files, initial observation,
and SHA256 inventory. No substitute assets or online mode were used. Next CPU
experiment: integrate a frozen generic W1 predictor with these records, commit
predictions before observation, and compare short history versus persistent
memory on held-out toy variants. Only then use model failures to choose the next
M1 refinement and an M2 planning prototype. No rule discovery, ls20 solving or
cross-game transfer has been established by these tests.

## Review fixes, October 25

A review of `c920f5d` ran the memory on real ls20 boards. The 115 frames of the
object-memory replay published at `cbed437` are exact `png(grid, cell=7)` renders,
so `grid_from_png(raw, cell=7)` recovers the real 64x64 grids without the asset
handoff. Two problems appeared and are fixed on `mac-world-model-fixes-v1`:

- **Control hints were mostly noise.** Any same-colour, same-shape match to the
  previous frame with a non-zero offset produced a hint, including identical static
  marks, even after an action that changed nothing. A hint now also requires
  changed cells in both the earlier and the later region.
- **Identity matching grew quadratically.** Every proposal was compared with every
  earlier frame of the level. It is now compared with the previous frame, and only
  proposals unmatched there search back to their most recent compatible frame, so
  reappearance after occlusion is still linked. This supersedes the remaining-scope
  note above about a bounded candidate index.

| Real ls20 run, 114 moves | `c920f5d` | Fixed |
|---|---:|---:|
| Control hints / on the player | 1,189 / 113 | 226 / 113 |
| Identity links | 161,589 | 3,572 |
| Mean time per move, first / last ten | 0.033 / 0.234 s | 0.024 / 0.038 s |
| Snapshot / save / load | 45 MB / 7.1 s / 20.1 s | 16 MB / 4.4 s / 8.0 s |

Player positions come from the replay's recorded centres; this is a check of the
hint filter, not evidence that the memory identifies the player. All 31 tests pass
on Linux (Python 3.12); four of the five new ones fail on `c920f5d`, and the fifth
guards reappearance after a three-frame occlusion. CPU only: no model, GPU or game
action.
