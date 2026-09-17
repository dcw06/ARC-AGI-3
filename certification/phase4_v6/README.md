# v6 — local measurement integration, target execution disabled

## September 17: target-gate review and separate installation proposal

See `reports/phase4_v6_target_review_20260917.md` for the current gate disposition.
The target evaluator now requires actual GPU cleanup and rejects canceled admission.
Telemetry uses lossless, hash-checked chunks under the existing 16 MiB component
budget; no samples or timing precision are discarded. Known model/compiler caches
are routed into monitored scratch, and completion checks include evaluation and
result publication. These changes remain pending real target validation.

`notebooks/phase4-v6-install-check-proposal-r1` is a separate installation-only
proposal: a fresh venv, both frozen wheelhouses, dependency checks, exact package
versions and a CUDA smoke test. It loads no model and runs no development pilot.
Its GPU-enabled metadata describes the proposed session; uploading it spends
compute and is not authorized. Its proposed 1,800-second reservation is separate
from the later 28,800-second pilot and from the consumed prescreen reservation.

`notebooks/phase4-lifecycle-v6-review-r3` is the new GPU-disabled source/protocol
review snapshot. It is not an approved execution lock. Historical r2 stays intact.

## September 17: portable local CPU smoke validation

The current development runner uses a bounded 300-second local CPU smoke budget
with a 10-second finalization reserve. The former 90-second runner budget also
reused the historical v3 evaluator's separate 60-second cutoff, making a complete
local run fail on slower hosts. `evaluate_local_smoke` retains the unmodified v3
verdict under `historical_v3_evaluation` and applies the explicitly supplied local
budget only to the local functional verdict. Non-time resource limits, complete
client/request evidence and cleanup remain required. A smoke pass is not a v3
timing pass, measured model capacity, or target certification. Historical results
are not reevaluated or relabeled under this new scope.

Checkpoint snapshots now copy scalar timeline events and list containers under
their locks, then serialize and persist outside the inference-completion lock.
Clients already finished at collection time share a checkpoint; no client or
request evidence is discarded. Failed CLI runs retain the original error and
leave invariance checks unset rather than indexing a missing worker result.

The target protocol's 27,540-second lifecycle, 600-second reserve and closed
authority gate are unchanged. Existing review-r2 notebook/archives remain exact
historical snapshots; they do not include these source changes. A future review
package must be a new revision.

## Current handoff: integrated pilot and review-r2 notebook

The newest implementation is `pilot.py` plus `pilot_child.py`. It unifies the
worker, monitor, control/evaluator records and bounded process logs under the
shared 64 MiB store and first-cell clock. The outer process directly owns worker
and monitor groups. Worker release requires a nonce/PID/mode-bound ready record
backed by a retained validated GPU-shaped sample. Local mode labels that sample
injected; live mode is authority-gated before probes/model imports.

The monitor remains running while the outer runner terminates the worker/model
group. Only after group absence is verified does the outer send stop-monitor;
the live adapter then requires an empty GPU process inventory. The final sample
and receipt precede evaluation. Monitor errors, worker errors, cancellation,
log/evidence exhaustion and unknown cleanup fail the run. Mandatory evidence is
not truncated to manufacture a pass. Model stdout is captured through the bounded
worker pipe; each process log has a 3 MiB cap, installation 1 MiB, inside the shared
7 MiB log allocation. Atomic replacement peaks count against the shared budget.

The actual-environment local pilot passed: 110 clients, 7,722 requests, 23.35 s,
verified cleanup. Every client's request digests and action/state-hash sequence
matched the archived v3 scripted run. This is a behavior-invariance check, not a
randomized performance comparison or GPU/model evidence. Seventeen process tests
passed including normal workload, monitor/worker failure, evidence exhaustion and
cancellation; the related 77-test regression suite and two latest packaging tests
also passed in separate invocations (overlapping test counts).

Current review notebook:
`notebooks/phase4-lifecycle-v6-review-r2/profile.ipynb`.
Its exact source/protocol/tests inventory is bound by `review-source-lock.json`.
GPU and internet are disabled, visibility private, execution authority closed.
Both environment and model-service dependency installation are included with
artifact verification. The bootstrap gate runs under `python -S` before install;
pilot/engine imports occur only after install. The initial review notebook and
archive are superseded (import-order correction) and preserved, not launchable.

`reports/phase4_v6_integrated_result.json` binds the corrected portable archive.
All archived file hashes verified, and local evaluation passed after extraction
into a fresh directory using the archived sources. This is a review snapshot,
not an approved GPU execution freeze. A source/protocol freeze for spending must
follow installation verification and independent target review.

Remaining launch gates:

1. **Clean Linux x86_64/Python-3.12 installation/import validation with the frozen
   environment and vLLM wheelhouses.** This host is Darwin ARM64 with no Docker
   executable; the model wheelhouse is an external Kaggle attachment. No clean
   target-compatible install was possible here. Existing resolver/checksum checks
   and packaged install code are not installation evidence.
2. Review the integrated target path, especially real GPU telemetry timing,
   process topology, bounded model logs and evidence fit. Local injected probes
   do not establish CUDA behavior. A one-second gap limit and bounded output can
   legitimately fail a target run; do not relax them after viewing results.
3. Approve a complete execution lock/release gate and separately authorize/reserve
   the proposed single 28,800-second attempt. There is no boolean bypass and no
   reuse of the retained prescreen reservation. The pilot uses hard request,
   resource and deadline caps; it does not require capacity from its own future
   results to launch. Capacity estimates stay null until measured/reviewed.

Local execution:

```sh
MPLCONFIGDIR="$PWD/.cache/matplotlib" XDG_CACHE_HOME="$PWD/.cache" .venv/bin/python -m certification.phase4_v6.run_local_pilot --output /path/to/new/evidence-directory
```

The following sections describe component-development history; their unintegrated
status statements are superseded by this current handoff where explicitly covered.

This additive revision preserves v1–v5 and the v4 review notebook. It is not a
complete target revision, approved execution freeze, or compute authorization.
Running worker.py directly raises PermissionError. Local tests inject completions.

## Live adapter and shared-clock/evidence wiring — September 16

`live_probes.py` implements adapters for the existing exclusive GPU binding,
UUID-bound sampling, owned worker-group RSS, scratch byte accounting and GPU
process inventory. Construction is gated before agent imports or hardware queries.
The gate intentionally remains closed: v6 has no approved source lock/reservation,
and neither the old v4 gate nor completed prescreen reservation may authorize it.
Adapter unit tests mock both authority and hardware functions; they are not live
probe verification. This does not implement a target-ready launch command.

Monitor records now carry the supplied first-cell monotonic origin and relative
sample/start/end times. `monitor_fields` validates the retained receipt and sample
inventory, checks exact clock conversions and resource limits, and produces fields
for the v6 evaluator without discarding or rebasing observations. The evaluator
rejects injected resource evidence before generating any capacity candidate. Outer
records now retain the same origin plus worker release/observed-stop timestamps.
Those describe leader lifetime, not proof that all GPU descendants have stopped.

`evidence.py` provides a POSIX cross-process-locked writer with component budgets:
control 1 MiB, monitor 16 MiB, worker 32 MiB, evaluation 8 MiB, logs 7 MiB (64 MiB
total). Replacements charge the temporary peak; each component reserves 4 KiB
for a bounded failure receipt. Symlinks, unbudgeted files and nonfinite JSON fail.
The monitor supports this shared store and its clock/evidence-to-evaluator path
is tested. All other producers must migrate before this becomes a whole-output
guarantee: the local outer/worker paths still use their earlier writers and limits.

Five adapter/store/clock tests and seventeen monitor/measurement/capacity tests
passed (22 total). The new integration test keeps its injected evidence label and
proves it cannot satisfy the model-backed evaluator. Historical snapshot and diff
checks passed. No live probe, model execution, upload or compute approval occurred.

Next target work: migrate all producers to one shared clock/store, wire the live
monitor's GPU-bound ready record into the outer gate, keep sampling through actual
GPU cleanup, publish bounded logs and assemble the complete independent report.
Then validate clean offline installation and build/review a new gated notebook.

## Implemented and checked

- A measured inference wrapper preserves the frozen executor, opaque isolation
  key and policy callback. All requests receive unique event IDs and monotonic
  submission, service-start, service-end and caller-return times. Failed and late
  callbacks stay failed; missing/unfinished requests cannot become capacity data.
- The new 110-client worker retains these events and joins request digests to IDs.
  Workload timing starts before clients launch and ends after all clients return.
  Workers still alive after queue close prevent a complete checkpoint claim.
- Atomic checkpoint writes reject nonfinite JSON, symlinks and aggregate directory
  bytes including the temporary-write peak. They do not truncate old evidence on
  a size rejection. This writer requires an exclusively owned directory and one
  serialized writer; it is not yet integrated into an outer evidence publisher.
- Added evaluator checks require the existing v4 model/lifecycle checks, matching
  timeline inventory, complete caller timestamps and telemetry enclosing worker
  lifetime. GPU sampling gaps above a proposed one second fail. This is a review
  threshold, not a proven continuous resource bound or an approved protocol freeze.
- Capacity candidates use the v5 rule only after those checks. C_admit remains null
  and Phase 4 remains incomplete. Timing arithmetic cannot authenticate artifacts;
  a reviewed execution/evidence inventory remains necessary.

Seven new tests passed, including a 110-client mocked-lifecycle comparison of v4
and v6 that preserves all client/request digests, 1:1 event inventory, timeouts,
telemetry rejection, and bounded-write preservation. Together with the four v5
tests, 11 tests passed; the combined related local regression suite passed all
65 tests. Historical snapshot verification and git diff checks also passed.
The mocked lifecycle is not actual environment dispatch,
GPU/model inference, or a prospective whole-workload performance comparison.

## Outer ownership prototype — local CPU tests

`outer.py` now launches the worker and monitor as two explicitly owned session
groups. `gated_exec.py` holds the worker before model/agent imports until both
Popen handles exist and an ownership record is saved. EOF or failed monitor
launch denies worker execution. The monitor receives a PID to observe; it must
not spawn or detach worker/model processes. The frozen model launcher inherits
the worker group, but target descendant behavior still needs verification.

The outer deadline includes a supplied first-cell clock and reserves cleanup
time. It signals both groups even after group leaders exit, escalates to SIGKILL,
reaps its children, and checks process-table absence before claiming cleanup.
Cancellation is retained and cannot produce a nominal completion pass.

The outer runner now additionally requires an atomic, bounded monitor-ready
acknowledgement before releasing the worker. The record binds a fresh random
nonce, exact worker/monitor PIDs and an explicit local-CPU evidence kind. A stale
record, extra fields, wrong IDs, malformed/oversized JSON or symlink fails closed.
Readiness has its own timeout bounded by the global admission cutoff; process
liveness and elapsed time are rechecked after retaining the acknowledgement.
An alive process alone no longer grants worker release. This is a local handshake,
not evidence that a GPU has been bound or initialized. GPU-ready labels are
rejected until a separately reviewed target handshake exists.

Eleven real-process CPU tests cover normal exit, monitor hangs/crashes/early exit,
worker crash, TERM-ignoring descendants surviving leader exit, failed monitor
launch, exhausted first-cell time and missing/malformed/late readiness. These
plus two handshake validation tests passed (13 total); the 11 measurement/capacity
tests also passed on September 16. Process tests require process-table access. They
are not CUDA cancellation or integrated environment evidence. Commands' stdout
is discarded in this prototype; target packaging must add bounded failure logs.
Detached descendants and failure of the outer process itself are not contained
by POSIX group ownership alone; the provider remains the outermost kill boundary.

## Unfinished target blockers

### Resource-monitor integration — injected probes, September 16

`monitor.py` now validates GPU binding/VRAM, RAM and scratch samples through
injected probe functions. Readiness is published only after a complete first
sample has been validated and durably retained. Later identity changes, resource
breaches, probe exceptions and excessive sampling gaps are terminal. There is no
retry that could hide missing observations. Binding and telemetry are retained
in a dedicated single-writer directory; 4 KiB is reserved for a small final
failure receipt, including when the next telemetry checkpoint exceeds its budget.
An actual disk-write failure can still prevent publication and must fail the run.

The fixture-only subprocess entrypoint connects this monitor to the outer runner's
real startup gate and process cleanup. Its GPU/RAM/scratch values are injected,
not measured; even valid-shaped GPU UUID data is explicitly non-target evidence.
There is no live CLI mode. Six monitor tests, fourteen outer/handshake tests and
eleven measurement/capacity tests passed (31 total). Historical verification and
diff checks passed. No frozen runtime/model configuration or notebook changed.

The following target integration work remains; a local pass does not remove it:

1. Integrate the tested outer ownership prototype into a new notebook path. Do not
   nest the v4 supervisor unchanged: its independently launched worker would escape
   the new ownership inventory. Extend the local readiness handshake with actual
   GPU binding and monitor initialization, and verify target descendant topology.
2. Integrate telemetry interval recording, aggregate retained-output accounting,
   bounded failure receipts and the v6 evaluator into that new supervisor. The
   existing v4 supervisor does not produce the newly required coverage fields.
   The injected monitor currently uses its own monotonic interval and directory
   budget. Convert to the shared first-cell clock, add actual GPU cleanup evidence,
   and reconcile all per-component budgets before feeding the target evaluator.
   The local outer prototype's 64 KiB whole-output bound is not the final 64 MiB
   target evidence budget; do not simply place full target telemetry under it.
3. Verify clean target-compatible offline installation of engine AND model-service
   dependencies. Environment wheel resolution alone is not enough.
4. Review/freeze the pilot protocol, including timing instrumentation and diagnostic
   invariance under actual environments. Build a new notebook and source/evidence
   lock, then seek separate explicit GPU authority and independent allowance checks.

The outer watchdog is locally implemented and tested, but no integrated target
cleanup pass is claimed. No GPU run, upload, model load, budget change, or
production gate closure occurred.
