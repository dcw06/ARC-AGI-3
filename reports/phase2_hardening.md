# Phase 2 remaining-gap hardening

Phase 2 remains open. The user reported launching the V1 diagnostic run; its
source lock, parent policy and capture behavior have not been changed. No V2
run or treatment has been launched by this work.

## Evidence-backed admission

The former failure-record validator accepted syntactically correct declared
hashes. `validate_failure_structure` now names that limited check explicitly.
`validate_failure_record(require_admitted=True)` additionally resolves a failure
through `config/phase2_admission_index.json` and independently replays both full
run envelopes against the frozen parent lock. The treatment validator performs
the same admission check after its structural/feature/threshold validation;
selection validation cannot bypass it. The initially empty index admits nothing.

Index entries, keyed by failure_id, contain lock, runs (exactly two), and
attribution_review references. Every reference is {path, sha256}; paths must
resolve beneath the project/evidence root and hashes must match actual bytes.
Reproduction run IDs, file hashes, trajectory signatures and transition IDs
must resolve to those envelopes. The current adapter supports the registered
cd82/104759 reproduction protocol only; other failures remain fail-closed until
their own prospective execution validators exist.

A matching unproductive trajectory does not infer causality. A separate retained
review must name a reviewer, rationale, failure ID, exactly one missing capability,
the sorted exact run hashes, excluded alternative causes and concrete transition
references formatted run_id/transition_id. This is a human attribution decision,
not a claim that hash checks establish the truth of a causal explanation.
E2a–E2d and E4 additionally require exact referenced sequence evidence; an
omission cannot count as exact. E3 still requires its own supported-mechanic and
recurrence diagnosis in the review. No review has been written or admitted here.

## Versioned, policy-inert sequence capture

V1 preserves final frames only and remains valid for that declared purpose.
`evaluation/phase2_sequences.py` provides the separate V2 observer. It retains
ordered uint8 sequence blobs with the existing canonical hashes, binds them to
the unchanged parent diagnostic bundle, and checks final-frame correspondence.
Caps are 256 frames/sequence, 1 MiB/sequence, 32 MiB raw retained sequence blobs,
and the recorder's transition capacity (80 in this runner). Base64 expansion is
bounded separately by those caps. Capacity omission and capture errors are
explicit; exceptions preserve the parent transition and legal-play path.
CPU capture time is recorded, and wall time is included in supervised execution.
No intermediate evidence, evaluator game IDs, memory or retrieval enters E1.

V2 uses an explicit entry point and a hash-frozen capture extension around the
unchanged V1 runner. It does not silently replace V1 imports in the current run.
Sidecars use .sequences rather than .json so the frozen V1 envelope assembly does
not misidentify them as additional parent bundles. Download validation checks
the extension lock, sidecar provenance, contents and explicit omissions.

## Whole-attempt and family accounting

The new append-only ledger reserves 7200 seconds for the user-reported current
attempt. Prior attempt inventory is unconfirmed; new execution is blocked, not
assumed to have six spendable hours. Successful, failed and uncertain attempts
all count. Unknown costs retain reservations. Reconciliations require retained,
hashed evidence binding attempt_id, charged_accelerator_seconds and
scope=all_accelerator_time_including_setup_and_failures. Evidence should derive
from provider runtime records, especially when installation failed or the kernel
was externally killed. These records remain attestations of provider usage;
the tool cannot independently discover unreported Kaggle attempts.

The V2 outer supervisor starts its cost record before installation and owns all
setup, worker/model processes and cleanup under a single process-group timeout.
It writes heartbeat/final cost evidence and kills descendant processes on exit.
An external kernel kill may prevent the final write: reconcile provider usage
or keep the full reservation. Notebook timing excludes provider provisioning
before notebook code, so the family ledger uses complete provider-accounted
accelerator time rather than silently assuming those intervals are free.

Use:

```bash
make phase2-budget
.venv/bin/python scripts/phase2_budget.py discover --attempt-id PRIOR_ID --seconds CONSERVATIVE_SECONDS
.venv/bin/python scripts/phase2_budget.py reconcile --attempt-id ATTEMPT_ID --seconds CHARGED_SECONDS --evidence path/to/provider-cost.json
.venv/bin/python scripts/phase2_budget.py confirm-inventory --evidence path/to/provider-inventory.json
```

Inventory evidence contains attempt_ids matching every recorded attempt. A new
discovered historical attempt invalidates prior inventory confirmation. Unknown
or outstanding attempts block a new reservation. Once reconciled, reserve a
distinct new attempt (if a new run is justified) and build its capture lock:

```bash
.venv/bin/python scripts/phase2_budget.py reserve --attempt-id cd82-v2-ATTEMPT --seconds 7200
.venv/bin/python scripts/build_phase2_diagnostic_notebook_v2.py --attempt-id cd82-v2-ATTEMPT
```

The ordinary `make phase2-cd82-v2-notebook` builds an execution-disabled notebook.
It cannot begin environment play. No push target is added, and no scored
submission is authorized. Retain each pre-launch capture lock with its attempt.

## Truthful status and CLI behavior

`phase_2_live_status` is explicitly open. Older immutable no-treatment and
conditional-implementation records are historical dispositions, not proof that
the current diagnostic work is complete. Their validators now print this scope.
The reproduction CLI exits 2 when integrity is valid but the target failure was
not reproduced. `--report-only` permits integrity/report inspection without
claiming reproduction. Reports always state phase2_complete=false and show the
family ledger, capture version and need for provider cost reconciliation.

Next: download and review V1; reconcile its actual runtime and prior-attempt
inventory; decide whether retained evidence suffices or a separately funded V2
capture is justified. Close with an evidence-backed no-treatment decision or
admit exactly one justified delta and perform its prospective comparison.
