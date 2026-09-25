# Action-effect history v1: review package

**Status: GPU-disabled review snapshot.** Authorized seconds are zero. There
has been no reservation, upload or model call. This package is for an
independent review. Source approval and a separate compute authorization
would follow only after that review.

## What the package contains

| Item | Location |
|---|---|
| Frozen protocol (question, cases, arms, stop rules, metrics, outcome classes) | `reports/action_effect_history_v1_protocol.md`, `research/action_effect_history_v1/protocol.json` |
| Case and environment bindings (initial state hashes, control sets, CPU compatibility check) | `reports/action_effect_history_v1_control_inventory.json`, `reports/action_effect_history_v1_environment_check.json` |
| Prompts and request construction (common baseline, one history field) | `research/action_effect_history_v1/contract.py` |
| Action-effect records and fixtures | `research/action_effect_v1/records.py`, `fixtures.json` |
| Model-service contract | `research/action_effect_history_v1/service.py` |
| Live path | `host.py`, `worker.py`, `monitor.py`, `resources.py`, `supervisor.py`, `scripts/action_effect_history_v1_launch.py` |
| Runner and failure-safe evidence | `runner.py`, `evidence.py` |
| Independent evaluator | `research/action_effect_history_v1/evaluate.py`, `scripts/evaluate_action_effect_history_v1.py` |
| Approval, reservation and one-shot upload tooling | `research/action_effect_history_v1/authority.py`, `scripts/action_effect_history_v1_package.py` |
| Token audit and budget proposal | `reports/action_effect_history_v1_token_audit.json`, `reports/action_effect_history_v1_budget.json` |
| Local rehearsal results | `reports/action_effect_history_v1_rehearsal_results.json` |
| Dependency manifests | `reports/phase4_v2_offline_package.json`, `config/` (bound by hash in the source lock) |

The source lock binds two sets by SHA-256:
- **`bindings`**: every runtime file. The notebook embeds these, and the
  authority re-verifies them inside the notebook before anything runs.
- **`review_documents`**: the protocol and reports, the tests, and the review,
  check, rehearsal and packaging tooling. The review script verifies these
  against the repository. They are left out of the notebook so the launch
  package, with its compressed authority sidecars, stays under the 900 KB
  upload guard.

The notebook runs only in live mode and refuses to run without authority
before installing anything.

## How to verify

```sh
python -m scripts.check_action_effect_history_v1          # every local suite; rewrites the rehearsal results
python scripts/review_action_effect_history_v1_notebook.py --folder notebooks/action-effect-history-v1-review-r1
```

The review script does four things:
1. Checks every binding and the metadata (private, offline, GPU off).
2. Executes the frozen notebook cell and requires a `PermissionError`, with no
   extracted source left behind.
3. Executes the **same cell with only `MODE` changed** to rehearsal, requiring
   the full connected study to complete and pass the independent output
   evaluator.
4. Runs the actual-snapshot approval, reservation, packaging and packaged-gate
   regression.

## What the local evidence cannot show

- **Model behaviour.** Whether the target model answers the new prompt and
  schema validly, or uses the history field at all. Rehearsals use a scripted
  model, and their behaviour classes are not results.
- **Target runtime.** vLLM startup time, GPU memory and real per-call latency
  on the target. The budget uses measured earlier runs plus margins, and is
  conditional on admission and clean stopping.
- **Generalization.** Anything beyond the three development cases. ar25
  informed the intervention, and all three cases were exposed before.

## Decisions already made

- Seeds are fixed at 0 in both blocks; block 2 is an order-reversed
  replication.
- Rates with a zero denominator are null.
- *Opportunities eliminated* is reported separately and never counted as
  reduced.
- All six pairs are required for an overall behaviour conclusion.
- Outcome classes are checked in a fixed precedence.
- cd82 and ft09 are excluded from case selection.
- The run deadline is enforced even mid-pair.
- Reliability is reported for every attempted episode.
