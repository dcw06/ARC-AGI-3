# Mac M1: neutral proposals and persistent evidence

First milestone for the Mac assignment in the supplied team plan (pages 7 and 10).
Built on `1ad910bcd3a541279c4a6f224cce15368bec74aa`, branch
`teammate/mac-world-model`. This is a CPU evidence library, not a game-playing agent.
The original delivery below is the first M1 checkpoint. The subsequent
[M1 object-effects / M2 prototype](M1_M2_CHECKPOINT.md) adds prospective
predictions, counterexample retirement and bounded planning in separate modules.

## Run

From the **discovery worktree**, with its own environment:

```bash
.venv/bin/python -m unittest tests.test_ls20_discovery_mac_m1 -v
.venv/bin/python scripts/demo_ls20_discovery_mac_m1.py
open reports/runs/ls20-discovery-mac-m1/index.html
```

The demo writes six synthetic snapshots, a metrics summary, HTML with expandable
records, and a PNG overview. It restores every snapshot and checks exact equality.
No game engine, model, GPU, provider, credentials, or network calls are made.

## Interface and integration impact

```python
from research.ls20_discovery_mac import EvidenceMemory

initial = {'grid': [[2, 0]], 'state': 'NOT_FINISHED',
           'levels_completed': 0, 'legal_actions': [1, 2, 3, 4]}
memory = EvidenceMemory('toy-episode-1', initial)
memory.append(
    {'action_id': 1, 'action_data': {}},
    {'status': 'acknowledged', 'post': {**initial, 'grid': [[0, 2]]}},
    elapsed_seconds=0.01,
)
memory.save('memory.json')
restored = EvidenceMemory.load('memory.json')
assert restored.snapshot() == memory.snapshot()
```

Input accepts the existing `OfflineEngine.snapshot` fields (`grid`, `state`,
`levels_completed`, `legal_actions`) or replaces `grid` with `frames` to preserve
all returned frames. Optional `full_reset` starts a new spatial segment. The
existing `research.action_effect_v1.records` supplies palette validation and
acknowledged/failed/unknown outcome semantics. No game-specific geometry or solver
is imported. Existing adapters, shared schemas and Linux supervisors are unchanged.

Coordinates in proposals and cell histories are **row, column**. Bounding boxes
are inclusive `[top, left, bottom, right]`. Dispatched `action_data` retains the
existing native `x, y` convention. Action IDs are treated as opaque legal controls;
no direction, movement size or completion rule is encoded. Palette IDs 0..15 are
the existing raw interface range; none receives a semantic meaning.

All fields in `schema.json` describe the **snapshot payload**. The on-disk envelope
adds `payload` and `sha256`. JSON Schema checks structure; `EvidenceMemory.load`
replays raw transitions and checks all derived records, IDs and hashes for equality.
Checksums detect accidental corruption; they do not authenticate an external source.
Snapshots use a flushed/fsynced temporary file and atomic replacement. Call `save`
at the desired persistence boundary; append does not automatically write a journal.

W1 can consume `scenes`, `identity_candidates`, `events`, `hypotheses`, and raw
`observations`/`transitions` from a copy returned by `snapshot()`. Every transition
contains episode, segment, action, outcome, before/after hashes and elapsed time.
Timing defaults to zero; a real adapter must supply measured timing. The default
means unmeasured, not evidence of zero latency. A transition hash covers the entire
normalized public observation; raw frame hashes are separate. A lost response
suspends the episode; an external recovery adapter must start a new episode with
a fresh observation rather than treating the old image as current.

## What is factual, computed, or hypothetical?

- Raw: observed grids and public engine metadata, issued actions and dispatch outcomes.
- Computed: four-connected same-color region masks, shapes, crops, bounding boxes,
  adjacency, exact per-frame pixel changes, and repeated-state outcome discrepancies.
- Hypothetical: possible identity links and possible controlled-entity roles.

Every observed palette value is retained, including large background regions.
IDs (`o2:r3`) identify observation-local proposals, not ground-truth persistent
objects. The identity graph is the revisable tracking representation: every compatible
same-palette overlap or translated-shape match is retained, including historical
matches. Many-to-one and one-to-many links preserve merge/split alternatives.
Matching does not prove identity; disappearance does not prove occlusion. Links
always retain the alternative that the regions are different entities. Level/reset
boundaries do not reuse geometry. Different-sized frames are not compared cellwise.

A translated candidate after an action generates only a tentative control-role
hypothesis linked to its change event, and only when both the earlier and the later
region contain changed cells. Identical static marks and newly appearing copies
therefore produce no hint. Autonomous motion and identity mismatch
remain explicit alternatives. Even background motion can generate such a candidate;
there is no promotion to a confirmed role or causation claim in this milestone.
W1 should test these suggestions rather than treat them as discovered mechanics.

`cell_history` preserves every observed value, including temporary covers and newly
visible terrain. It does **not** assert which value is floor, which is an occluder,
or what lies underneath an object. Nothing overwrites observed pixels with a floor
color guess. Unchanged observations and failed requests remain distinct; neither
is automatically called a blocked movement. A return to the original final frame
retains intermediate changes. Same observed pre-state/action with different
observed outcomes creates a discrepancy event retaining both transition IDs.

## Known failures and next work

This is the smallest M1 evidence checkpoint, not completion of all M1 requirements:

- Within-episode recoloring breaks the same-palette identity heuristic. The demo
  retains this failure and the raw change. Globally permuting palette IDs is supported.
- Disconnected multi-color parts are not grouped into whole objects. Partial masks
  and many-to-many alternatives survive, but no co-motion grouping or identity
  resolution is implemented yet.
- Boundary adjacency is geometric evidence, not a verified encounter. Failed-edge
  inference, terrain layers, role promotion/retraction, and contact-effect inference
  need additional evidence and a shared W1 interface.
- Identity candidates compare each proposal with the previous scene, and search
  older scenes only for proposals unmatched there, stopping at the most recent
  compatible scene. Matching therefore grows linearly with history. Persistent
  memory is still unbounded: every frame keeps its raw grid and full region masks
  (about 140 KB per frame on real ls20 boards).
- Hidden-mode tests prove old evidence remains accessible; the evaluator supplies
  the cue-to-action rule. They do not demonstrate learning or a policy advantage.
- No W1 prospective prediction comparison, engine integration, game completion,
  cross-game generalization or M2 planner is claimed.

Next experiment: freeze a small generic W1 predictor and compare current/short
history, current scene proposals, and scene proposals plus event history on
evaluator-owned toy transitions. Record predictions **before** exposing outcomes;
measure both coverage and errors. Use failures to improve association/grouping
before introducing M2 short-horizon planning. Real ls20 evaluation additionally
requires Alan's pinned assets and initial-observation SHA256 inventory.
