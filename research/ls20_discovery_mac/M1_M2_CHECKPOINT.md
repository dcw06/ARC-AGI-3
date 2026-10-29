# M1 object effects and M2 bounded planning prototype

This extends the Mac assignment after the Alan M1 fixes and Rain W1 integration.
It does not complete M1/M2 research or claim ls20 solving. The runtime is CPU-only.
No original M1 module, schema or public snapshot field is changed.

## Work now possible and delivered

| Work | Delivered here | Boundary |
|---|---|---|
| Object-level changes | Candidate displacements, mask changes, unmatched regions, conditional adjacency changes | Same-palette region heuristic, not true entity tracking |
| Grouping evidence | Tentative co-motion groups, explicit many-to-many uncertainty | No resolved multicolor/disconnected object identity |
| Predictive model | Appearance/action/status-scoped displacement candidates and exact visible-state transition candidates | Two supports is heuristic; not causal proof or a full simulator |
| Prospective evaluation | Exclusive fsynced prediction before callback, result/memory retention, independent reconstruction | Local single-threaded toy protocol, not production supervision |
| Revision | Retain conflicting outcomes; retire contradicted scope for the segment | No automatic learning of new history/geometry preconditions |
| Planning | Bounded BFS on supported observed edges; one action before checking/replanning | Cannot imagine novel geometric routes or unknown effects |
| Memory comparison | Same predictor with current-only, two-transition and full-history inputs | Constructed diagnostic, not a statistically estimated advantage |
| Policy comparison | Same initial learned graph; reactive, prediction-only, and bounded planning | Weak fixed reactive policy; supplied training and goal |
| W1 compatibility | Original four M1 files still match Rain's fixed-source manifest; actual W1 replay repeated | Extensions are separate outputs, not inserted into Rain's schema |

## Use

```bash
.venv/bin/python -m unittest tests.test_ls20_discovery_mac_m2 -v
.venv/bin/python scripts/demo_ls20_discovery_mac_m2.py --output reports/runs/my-new-m2-run
```

The output directory must not already exist. The demo retains predictions, results,
restorable M1 snapshots, summary, model/effect JSON and an HTML diagnostic. Open
`index.html` locally. All goals and toy dynamics live in the evaluator script;
runtime modules receive only observations/actions and an explicitly supplied goal.

```python
from research.ls20_discovery_mac.object_effects import transition_effects
from research.ls20_discovery_mac.models import fit, predict, plan
from research.ls20_discovery_mac.prospective import execute, verify

effects = transition_effects(memory.snapshot())
models = fit(memory.snapshot())
forecast = predict(memory.snapshot(), action)
proposal = plan(memory.snapshot(), {
    'kind': 'supplied_diagnostic_goal', 'state_key': target_visible_state_hash,
}, horizon=4, max_expansions=100)
# If proposal has actions, execute its FIRST action only:
result = execute(memory, proposal['actions'][0], dispatch, run_directory,
                 planned=proposal)
# Inspect the actual result and make a fresh plan, never execute the old suffix.
verify(run_directory)
```

`m2_schema.json` validates the prediction/plan output structures. Semantic validity
is checked by the runtime and replay; schema alone cannot prove provenance.
`transition_effects` emits episode/transition/observation references. Internal
`before:rN`/`after:rN` IDs refer to re-extracted pair-local regions; use the enclosing
observation references when resolving them. Do not treat them as persistent IDs.
New masks and displacements are in row/column coordinates; actions keep the
existing native x/y contract. ACTION6 must have x/y; others must have empty data.

`fit` returns evidence-linked alternatives. State keys include final grid, public
status, completed-level count and legal actions. They intentionally omit history;
hidden-state differences can therefore falsify an edge. Conflicting targets retire
the entire state/action scope, even if later repetitions favor one target. The
planner only admits one-target scopes with at least two observed supports.
This is empirical transition-table learning plus graph search, not synthesis of
general game mechanics. It will often abstain on new boards.

Appearance-scoped displacement models can predict at a new position, but are
conditional on the extraction's unproven identity correspondence. They ignore
terrain and may fail at a blocker. They are scored separately and never supply
unobserved geometric edges to the planner. Ambiguous correspondence is unscored,
not counted as correct. Multi-frame returns are preserved by M1 but not fitted as
one-action displacement examples. Co-motion is a grouping proposal, not a role.

The first two comparison policies both choose the lowest action ID; the
prediction-only policy does not alter action selection. Observer forecasts are
logged in all arms for comparable diagnostics. All arms start with identical
scripted training evidence. The planner's constructed one-step success is not a
strong baseline comparison. Additional dispatches update retained memory, so this
is not a general frozen-model multi-step ablation.

## Reliability limits

Pass snapshots produced by trusted `EvidenceMemory`; this extension does not
validate arbitrary external input snapshots at every `fit` call. Rain's `M1View`
validates raw evidence and the M1 loader validates derived reconstruction.
The log seals a pre-state and prediction using exclusive creation plus fsync.
Existing files block retry. Unknown/malformed callbacks suspend the episode.
Any other exception (including disk failure after dispatch) requires the host to
STOP; changing directories does not make a retry safe. No cross-process registry,
deadline supervisor, automatic recovery or crash-resume feature is implemented.
Checksums and source inventories bind data but do not authenticate claimed time.

## Team integration and remaining work

Rain's W1 is still the owner of competing mechanic hypotheses. These limited Mac
candidate functions exercise the M2 interface until richer W1 rules exist; they
do not replace W1 or silently interpret its appearance labels as movement rules.
Share the object-effect records and agree an executable-rule handoff with Rain.
W2 currently has no goal hypotheses, so `supplied_diagnostic_goal` is mandatory.
Accepting a future W2 objective will require a new reviewed adapter/schema.

Remaining M1: persistent entity resolution, richer grouping/recoloring, terrain
layers, semantic encounters/failed edges, robust role revision and evidence
selection at scale. Remaining M2: richer conditional models and alternative
execution, missing-precondition recovery, object-conditioned W1 integration,
goal-conditioned W2 integration, held-out prospective comparisons, meaningful
reactive baselines and measured compute limits. Rebuilding from all history is
not suitable for long live runs. Real offline ls20 validation requires Alan's
authorized asset bundle, seed-0 initial observation and SHA256 inventory.

No GPU, model/API call, online game, competition submission or GitHub push is
part of this checkpoint.
