# Windows W1 checkpoint: revisable observational hypotheses

Built on the team's frozen `1ad910bcd3a541279c4a6f224cce15368bec74aa` baseline.
This is the first Windows module for the team's W1/W2 assignment. It reads Mac
M1 records, generates a small generic set of appearance-effect candidates,
commits forecasts before scripted dispatch, retains counterexamples, and exports
uncertainty to W2/M2. It does not yet learn movement sizes, traversability,
contact mechanics, object roles, objectives, or an executable world model.

## Use with M1

```python
from research.ls20_discovery_windows import M1View, HypothesisManager

view = M1View(memory.snapshot(), producer_commit=mac_commit_sha)
manager = HypothesisManager(view)
prediction = manager.predict({'action_id': 1, 'action_data': {}})
handoff = manager.export()
```

`M1View` accepts the raw snapshot payload, not Mac's disk envelope. It replays
initial observations and every transition, checking full observation/frame hashes,
episode/segment IDs, legal actions, timing, derived effect records, all returned
frames, and unknown-outcome suspension. It forwards the complete snapshot without
promoting derived regions or role hints to facts. Those derived fields are not
independently reconstructed by this adapter. The original M1 loader remains the
authority for its derived data. Its two reviewed algorithms share a version
string, so a full producer commit is mandatory.

The runtime import closure is standard library plus the existing portable
`research.action_effect_v1.records`. No game engine, supplied-rule detector,
solver, model, network, or private asset is imported. Action IDs remain opaque.

## Candidate language and revision

The generator learns candidates from observed transitions under three scopes:
exact action, public engine status, and exact action plus status. Exact actions
include click coordinates. A candidate predicts one of:

- `no_visible_change`;
- `visible_change`;
- `transient_change` (an intermediate change returns to the pre-action frame);
- `dimensions_changed` (takes precedence when any returned frame changes size).

These are appearance categories. They do not identify objects, causes, blocked
moves, progress, or winning conditions. Engine status is public metadata; the toy
uses distinct status strings to exercise context scoping. Real ls20 status need
not reveal a useful latent context.

One match is tentative; two matches mark a heuristic candidate supported. This is
not calibrated confidence or proof of a rule. A contradiction retires that exact
scope/outcome pair permanently while retaining both support and counterexamples.
Later evidence can create a previously absent outcome candidate or a different
scope. This deliberately limited language can still fail when the actual mechanic
depends on geometry, history, delay, or another missing condition.

Both comparison modes use the same generator and ranking. `immediate` selects
the highest-ranked applicable candidate. `competing` references at most four
candidates, while its outcome summary includes **all** applicable candidates so
the display limit cannot hide disagreement. `unknown_alternative` is always true.
Agreement is conditional on this candidate language and is never causal certainty.
All candidates are retained; this implementation replays history and is not
bounded for long live runs.

## Prospective execution and replay

```python
from research.ls20_discovery_windows import execute_step, replay_step

result = execute_step(memory, action, dispatch, run_directory,
                      producer_commit=mac_commit_sha, mode='competing')
score = replay_step(run_directory, step_index, mac_commit_sha)
```

The host supplies a single-threaded Mac-compatible memory and a dispatch callback.
Use one fresh run directory, reused throughout that episode. Before calling
dispatch, the wrapper exclusively creates, flushes and fsyncs the pre-state and
prediction files. Existing files block a retry. It then retains the result,
complete post-snapshot, and Mac-restorable memory. Dispatch exceptions or malformed
replies become `outcome_unknown`, which suspends predictions. A known pre-delivery
rejection must be explicitly returned as `dispatch_failed`.

The host must stop after any wrapper exception, including evidence-write failure.
This is not a deadline/budget supervisor, cross-process episode registry, or a
crash recovery controller. A fresh directory must not be used to evade an uncertain
dispatch. Checksums detect corruption but do not authenticate a publisher's
claimed chronology. Callback-order tests establish this implementation's ordering.

## Interface for Mac / W2 / M2

The implemented v1 [JSON schema](schema.json) replaces the earlier manual v0
proposal for this checkpoint; it is not a jointly approved shared contract.

| Field | Meaning |
|---|---|
| `context` | episode, segment, next transition index, latest frame ID, full observation hash, separate frame hash, legal actions, suspension flag |
| `snapshot_sha256` | complete M1 payload digest used by a forecast |
| `m1_producer_commit` | producer algorithm provenance; not a source-authentication claim |
| `scope` | segment, exact action or null, public status or null |
| `supporting_evidence` / `counterexamples` | episode/segment-qualified transition references |
| `predicted_labels` | prospective appearance candidates; score coverage separately from correctness |
| `unknown_alternative` | the true explanation need not be in the implemented language |
| `objective_hypotheses` / `candidate_targets` | empty in this checkpoint; W2 remains unimplemented |

M1 region IDs are observation-local, not persistent entity IDs. Region coordinates
are row/column and bounding boxes inclusive; ACTION6 uses native x/y. Mapping
logical cells to display pixels remains explicit adapter work. W1 does not output
coordinates in this checkpoint. ACTION6 requires integer x/y in 0..63; other
actions require empty data. RESET is external episode lifecycle, not action 0 here.
No-change, failed dispatch, missing result, and completed-level/reset boundaries
remain distinct. Predictions cannot continue when `context.suspended` is true.

## Run tests and diagnostics

Use a project Python 3.12 interpreter (native Windows works for this portable
module; existing Linux-only supervisors are unchanged). Schema tests additionally
need `jsonschema==4.26.0`; it is a test dependency, not a runtime requirement.

```sh
python -m unittest tests.test_ls20_discovery_windows_w1 tests.test_ls20_discovery_windows_schema tests.test_ls20_discovery_windows_replay
python scripts/demo_ls20_discovery_windows_w1.py --verify reports/ls20_windows_w1_v1/trace_fixed.json
python scripts/demo_ls20_discovery_windows_w1.py --verify reports/ls20_windows_w1_v1/trace_original.json
```

For a new actual M1 integration run, provide a checkout containing the reviewed
Mac package and use an output directory that does not exist:

```sh
git fetch origin teammate/mac-world-model mac-world-model-fixes-v1
git worktree add --detach ../mac-m1-source f4bf522e96b1642bed8772c29f153bfe44f98bd5
python scripts/demo_ls20_discovery_windows_w1.py --mac-source ../mac-m1-source --output reports/runs/windows-w1-new
```

The diagnostic checks M1 package bytes against [the pinned manifest](m1_sources.json)
before importing it. Hashing normalizes checkout CRLF to LF. Add `--mac-commit
c920f5d69ceb50239325738f9a188bb055ebdebd` with a matching original checkout to
exercise the earlier algorithm. Without `--mac-source`, it uses a clearly labeled
raw-only test double. Fixture outcomes stay evaluator-side and are exposed only
after a prediction is sealed.

Recorded results and limitations: [CPU checkpoint report](../../reports/ls20_windows_w1_v1/README.md).
