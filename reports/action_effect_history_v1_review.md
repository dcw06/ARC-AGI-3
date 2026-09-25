# Action-effect history v1: review package

**Status: GPU-disabled review snapshot.** Authorized seconds are zero. There
has been no reservation, upload or model call. This package is for an
independent review. Source approval and a separate compute authorization
would follow only after that review.

## Changes in r3 (review of r2 at `63d732e`)

r2 is preserved and superseded. Three evaluator gaps found in review are
fixed. Their regressions are in the same negative suite, and all fail against
r2's source:

1. **Dispatch receipts.** Every acknowledged step must carry an acknowledged
   offline-engine receipt. Its journal entry must be an acknowledged action
   whose fields match the step exactly:
   - the decision ID `{episode_id}-{step}`;
   - the action ID;
   - the payload hash, recomputed from the action;
   - the pre- and post-state hashes.

   Prepared fields must match the same values, sequence numbers must be
   consecutive, and the transaction ID must name the game. A failed or unknown
   dispatch must not carry an acknowledged receipt.
2. **Schedule identities.** The pair list must equal the frozen schedule
   (ID, block, game, arm order). Every episode's ID, pair, block, game, arm and
   position must equal its schedule slot. Episodes must form an in-order prefix
   of the schedule. Episodes for pairs that never ran, and games that are not
   frozen cases, are rejected.
3. **Frozen deadlines.** The output evaluator takes the limit from the frozen
   protocol: 3,300 s live, or the rehearsal harness's declared 2,400 s, which
   is never above the live limit. A report whose internal limit or admission
   cutoff conflicts is rejected. Both first-cell and supervisor durations are
   compared against the frozen value.

## Changes in r2 (review of r1 at `075114c`)

r1 is preserved and superseded. Three failure-detection gaps found in review
are fixed. Each has a regression in `tests/test_action_effect_history_v1_negative.py`,
and every one of those regressions fails against r1's source:

1. **Failed closure.** A failed client or scorecard closure now marks the
   episode `technical_failure`, keeping its play outcome as
   `play_stop_reason`, and stops the run. It appears in reliability as
   `closure_failures`. Replay rejects any complete episode without a
   successful closure receipt.
2. **Independent replay.** Replay no longer trusts runner verdicts. It
   re-derives every call's validity (a `stop` finish, token parity, completion
   bounds, response hash and size), and checks every pre-state against the
   preceding observation. It checks terminal states against stop reasons, and
   the final observation against the last observed state. It checks call and
   action accounting per episode and per run, pair composition, and whether a
   `complete` label is justified. A forgery re-hashed into the manifest passes
   the integrity check but fails replay.
3. **Lifecycle evidence.** The output evaluator now requires:
   - a first-cell cleanup record with no errors, non-empty groups including
     the recorded worker and monitor groups, a finished log drain and a
     supervisor return code of 0;
   - a notebook receipt with no error, the study complete and dependency trees
     removed (live) or not applicable (rehearsal);
   - GPU cleanup confirming the groups are absent;
   - verified run evidence.

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
python scripts/review_action_effect_history_v1_notebook.py --folder notebooks/action-effect-history-v1-review-r3
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
