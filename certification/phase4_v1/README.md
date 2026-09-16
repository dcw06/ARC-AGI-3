# Frozen development lifecycle preparation v1

The source/config/workload bindings in `lock.json` freeze **preparation**, not
target execution eligibility. The earlier draft in
`reports/phase4_full_game_certification_protocol_draft.md` is background; numeric
requirements and acceptance thresholds for this revision are in `contract.json`.
Do not edit a frozen revision after handoff; introduce a new revision for changes.

## What is frozen

E1S-R policy, model configuration, feature manifest and production adapter/queue
sources are hash-bound. `workload.json` contains 110 explicit opaque client rows,
cycling through the 15 development game/seed pairs in their frozen order. Each
row permits 80 actions, request seed 0 (the operational-primary setting), and
128 completion tokens. This is intentionally distinct from older experiment
runners that used the environment seed for model requests. It is a development
reliability run, not another E1 causal comparison or Phase 2 reproduction.

Each row owns an independent adapter, environment and scorecard; shared inference
uses an opaque client key rather than game ID. E1 observations/prompts are not
rewritten. Dispatch checks cancellation again after policy return. Finalization
is attempted after policy construction/loop failures, and a receipt must match
the opened scorecard. No missing policy may silently substitute E0.

`budget.json` proposes **one separate 28,800-second reservation**, with zero
authorized seconds and zero prescreen credit. No launch command exists in this
package. The completed prescreen's eight hours remain retained.

## Local evidence

The actual offline `ls20-9607627b` engine was exercised at development seed
104801 for three two-action smoke cases: nominal scripted E1 proposals, injected
completion failure with legal fallback, and cancellation after completion before
dispatch. All three scorecards were finalized with local framework receipts.
Scripted completion is not model inference. Local scorecards are not remote
competition acknowledgements. No attempt to solve games or access holdouts occurred.

The regression suite also rejects missing policies, factory failures, empty or
wrong-card receipts, close exceptions and missing action journals. Existing queue,
timeout, T0 journal and deadline tests were rerun: **19 tests passed** in total.
Hashes, package versions and final-lock output paths are recorded in
`reports/phase4_lifecycle_v1_preparation.json`.

```sh
.venv/bin/python -m unittest tests.test_phase4_lifecycle tests.test_phase4 -q
.venv/bin/python certification/phase4_v1/local_probe.py --fault none --output /tmp/p4-new-nominal.json
.venv/bin/python certification/phase4_v1/local_probe.py --fault policy_error --output /tmp/p4-new-fallback.json
.venv/bin/python certification/phase4_v1/local_probe.py --fault cancel --output /tmp/p4-new-cancel.json
```

Outputs are exclusive-create; use fresh filenames. Local environment artifacts
are ignored by git; restore the exact engine/metadata hashes recorded in the
preparation manifest before rerunning these commands. They are not downloaded
automatically. For a clean checkout, the environment package is an explicit
external dependency, not yet a complete target notebook artifact.

## Before target launch

Still required: all 15 exact environment artifacts and dependencies packaged and
hash-bound; the full 110-client orchestration under an external deadline/resource
supervisor; measured real-trajectory capacity/admission bound; GPU UUID telemetry,
process cleanup and independent full-result evaluator; reviewed offline notebook;
independent allowance verification and explicit new approval/reservation.

The synchronous client unit cannot terminate hung calls. Its local tests do not
prove server-side decoding abort, remote finalization, 110-client performance,
or target memory/storage compliance. These remain target-integration gates, not
implicit passes. The nominal target run admits no injected-fault segment; a later
registered revision and allocation are required for one.

Repeated development games and an 80-action cap do not establish the plan's
110-distinct-game or unrestricted lifecycle coverage. A future bounded load pass
must retain that scope and cannot automatically close Phase 4. Advanced scheduling
remains deferred and H1/H2 remain untouched.
