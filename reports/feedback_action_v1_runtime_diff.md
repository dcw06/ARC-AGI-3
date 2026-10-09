# Feedback-action v1 successor runtime v1: runtime-only diff against `687acc8`

This diff binds Track 1 to the verified runtime: `wheelhouse-replacement-audit` at `5a21dd3`, GPU-run review lock
`beeb6719…`.

The experiment's scientific configuration is unchanged byte for byte:
- prompts, arms and schemas;
- seeds and schedule;
- scoring and stop rules.

Every change below is a runtime binding, launch-harness integration, an inactive owner-gate implementation, a test
or a report.

## 1. Unchanged science (byte-identical to `687acc8`; asserted by `tests/test_feedback_action_v1_successor.py`)

| File | SHA-256 | Holds |
|---|---|---|
| `research/feedback_action_v1/adapter.py` | `26a84909…` | system prompt, PROCEDURE, both response schemas, carried-statement rules, parsing |
| `research/feedback_action_v1/evidence.py` | `8d095ba7…` | the evidence view shown to both arms |
| `research/feedback_action_v1/evaluate.py` | `019c1804…` | decision evaluator, denominators, minimums |
| `research/feedback_action_v1/live/protocol.json` | `d5c244fa…` | cases, schedule, sessions, caps, F2a/F5 thresholds |
| `research/feedback_action_v1/live/fake_server.py` | `d80eb516…` | CPU scripted completions |

The control-interface probes' newer explicit output template and computed control metadata were **not** added.

## 2. Changed tracked files

| File | Change | Effect on the experiment |
|---|---|---|
| `research/feedback_action_v1/live/policy.py` | Requests, the candidate schema check, the procedure parse and `session_spec` go through `owner_gates` | None while both owner decisions are `null`. Tests show the schema, requests and spec are then the committed ones |
| `research/feedback_action_v1/live/runner.py` (derived) | The F5 check compares with `max(dispatches, floor)`; the floor is `0` unless Gate B is recorded; the abort record gains `denominator_floor` | Committed F5 behaviour is identical. The abort record has one more field. The F5 boundary test expectation was updated to include it |
| `research/feedback_action_v1/derive.py` | Derives the launch harness from AEH v1: worker, host, supervisor, monitor, resources, the first-cell launch script and the evaluation script. Runtime substitutions are counted; the root depth is corrected for the deeper package | Runtime only |
| `research/feedback_action_v1/token_audit.py` | Forms from both sessions; tokenization in the model interpreter with the pinned stack; longest-response and grammar analysis for both free-text options | Measurement only |
| `tests/test_feedback_action_v1_live.py` | Derivation tests use the new derivation table; every harness source must be bound in the AEH r3 review lock | Tests |
| `tests/test_feedback_action_v1_dispatch.py` | F5 abort record now includes `denominator_floor: 0` | Tests |
| `tests/test_feedback_action_v1_token_audit.py` | Forms of both sessions; the exact audit must bind to them | Tests |
| `.gitignore` | Ignores Track 1's private operational records: approvals, account/permission/byte evidence, execution lock, reservation, launch claim and receipt, launch package | None |

## 3. New files

**Verified runtime controller, byte-identical** (git blobs equal; SHA-256 equal to the v2 GPU-run review-lock
bindings; checked by `derive_runtime.py --check`): `certification/direct_publisher_smoke_v1/`
- `__init__.py`, `host.py`, `install.py`, `server.py`, `preflight.py`;
- `proposal.json`, `trusted_manifest.json`, `trusted_requirements.lock`.

**Derived from the verified runtime** (`research/feedback_action_v1/derive_runtime.py`; sources read from their git
blobs and checked against recorded SHA-256 values):
- `live/binding.py`: the live gate;
- `live/notebook.py`: review snapshot and launch artifacts;
- `live/launch.py`: claim and receipt;
- `scripts/feedback_action_v1_package.py`: review-build, review-check, review-rehearse, launch-build;
- `runtime.verify_cache_disabled`: a verbatim function.

**Derived from AEH v1** (`derive.py`):
- `live/{worker,host,supervisor,monitor,resources}.py`;
- `scripts/feedback_action_v1_launch.py`;
- `scripts/evaluate_feedback_action_v1.py`.

**Hand-written glue:**

| File | Purpose |
|---|---|
| `live/runtime.json` | runtime binding: image, dataset/bundle pins, model snapshot (placeholders), server argv, game side, lifecycle |
| `live/runtime.py` | load/validate, competition mount, game-wheel verification, interpreter pair install (`prepare`), import closure |
| `live/game_requirements.lock` | 31 hash pins = the frozen competition wheel manifest |
| `live/authority.py` | the harness's authority interface over `binding.require_live` |
| `live/rehearsal.py` | CPU rehearsal transport faults; optional pinned tokenizer and xgrammar check; dispatch faults |
| `live/owner_gates.{json,py}` | Gates A and B, both `null` |
| `live/derivation.json` | the derivation record (sources, blob ids, SHA-256, substitution counts) |
| `live_evaluation.py` | independent session evaluation and two-session pooling |
| `scripts/rehearse_feedback_action_v1.py`, `scripts/check_feedback_action_v1_runtime.py` | connected rehearsal; installation check on replica mounts |

## 4. Old runtime pieces no longer on Track 1's live path

They are kept in the repository unchanged, because they belong to completed studies:
- `certification/phase4_integrated_v2/prepare.py`;
- `certification/phase4_v6/target_install_probe_r5.py` (`install_pair`, `MODEL_CHECK`);
- `certification/phase4_integrated_v2/model_process.py`, `config/operational_primary.yaml`,
  `config/m0_launch_spec_q3vl30.json` (with `--enable-prefix-caching`);
- `research/grounded_action_v1/artifact_contract.py`.

The test `Derivations.test_outdated_bindings_are_gone_from_the_live_path` checks that none of them is referenced from
Track 1's live closure.
