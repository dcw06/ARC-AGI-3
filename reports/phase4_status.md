# Phase 4 — local preparation started

## Current handoff: reviewable target prescreen

The latest target protocol is `config/phase4_execution_protocol_v2.json`, with
`config/phase4_execution_lock_v2.json` binding the full packaged source/config
inventory. It supersedes the earlier target-profile draft for prospective
execution, without rewriting the Phase 2–3 archive or local preparation contract.
The executable notebook is `notebooks/phase4-prescreen-v2/profile.ipynb`; metadata
is private, offline and unscored. `make phase4-target-notebook` builds a review-only
copy. Nothing has been uploaded or run on a GPU.

V2 addresses the four pre-launch review findings. The bootstrap authorization
gate now uses only the standard library and runs with site packages disabled.
Worker errors override cancellation-ready state both during polling and after
termination. The final atomic checkpoint is retained before scratch deletion,
including errors appearing after the last poll or after worker exit.

The evaluator now requires retained protocol/lock copies, the reservation ledger,
GPU UUID/telemetry, resource peaks, successful worker evidence, the artifact and
tokenizer audit, and per-fixture server token usage for each fixed window. It
recomputes assignment counts, checks prompt-token parity and completion bounds,
and rejects missing evidence, nonfinite measurements, errors and breached limits.
The notebook retains the reservation ledger alongside its original claim.

The V1 lock and notebook are preserved as historical review artifacts and must
not be launched. Their supersession is not retroactive GPU evidence. The new
package remains review-only with zero authorization; no reservation, commit,
upload or GPU execution was made during this repair pass. A fresh review of V2
precedes any commit/approval/launch decision.

The frozen limits are 86 GiB device-wide VRAM, 128 GiB process-group RSS,
4 GiB worker scratch, 64 MiB retained measurement bound, 900 seconds each for
dependency setup and model/preflight startup, a 300-second request/queue bound,
10 seconds graceful process termination plus 5 seconds kill verification,
and the existing 27,540-second lifecycle including 600 seconds finalization.
These are conservative prospective limits, not observed measurements. GPU UUID
is discovered exactly once on an exclusive idle single RTX PRO 6000, retained
before model startup, and checked thereafter; it is not guessed before allocation.

The scope is explicitly **repeated fixture service performance** with the frozen
prefix cache still enabled. It cannot estimate uncached real-game throughput,
show improved game solving, or close Phase 4. Eight fixed 1,100-request windows
retain measured wall times and server token totals. Offline tokenizer counts
must match the server for every measured request. Capacity is recomputed as:

```text
C_nominal = floor(19800 * 8800 / sum(window_seconds))
guard_rate = 0.8 * min(1100 / window_seconds)
C_admit = min(C_nominal, floor(15840 * guard_rate))
```

All eight windows must complete without errors, `C_admit >= 8800`, and lifecycle
and cleanup checks must pass. These margins are empirical, not a statistical
confidence bound or hard capacity guarantee. Failures invalidate the attempt;
there is no selective window rerun, model restart or scheduler alternative.
After the windows, an extra completion is attempted while the supervisor
terminates the model process group. Success requires the group and all GPU
compute processes to disappear within 15 seconds. This tests process-level
model-service cancellation, not proof of a per-request server abort or that
decoding was active at the exact signal instant.

`config/phase4_compute_ledger.json` still authorizes **zero seconds**. To enable
execution, a reviewed approval reference and exactly 28,800 authorized seconds
must first be recorded. Only then can `scripts/phase4_budget.py ATTEMPT_ID`
create the single source-lock-bound reservation; a second reservation is rejected.
`scripts/build_phase4_target_notebook.py --reserved` refuses unreserved builds.
The launch gate now validates those prerequisites rather than always raising.
An approval boolean in the old draft cannot bypass it. The local output claim
prevents reuse of a run directory, but is not a distributed Kaggle replay lock:
the operator must launch the reserved notebook exactly once and reconcile provider
attempt inventory before considering any future execution.

The notebook charges setup/startup/failure time from the first cell and retains
the full eight-hour reservation even if output is missing. Provider startup
before the first cell and accounting reconciliation remain provider evidence,
not inferred from the local timer. Measured runtime never automatically releases
reserved compute. Output retains the execution lock, protocol, GPU binding,
claim, partial/final measurements and cost receipt; raw model text is not retained.
Worker scratch and temporary packaged source are cleaned. An incomplete cleanup
or unknown finalization cannot count as a pass.

After an authorized run, evaluate downloaded output with:

```bash
.venv/bin/python scripts/evaluate_phase4_prescreen.py /path/to/phase4-prescreen
```

No actual tokenizer/GPU/model-process validation has yet occurred. The notebook
and protocol are ready for review, not declared hardware-certified. After a
successful prescreen and accounting review, register a separate full-game
lifecycle certification covering environment dispatch, legal fallback, cancellation
and scorecard finalization. H1 stays untouched; advanced scheduling stays deferred.

## Earlier implementation milestones (historical scope)

`config/phase4_contract.json` freezes E1S-R, its model and prompt manifests,
the minimum FIFO scheduler (110 queue slots, eight workers, 300-second age
limit), the existing development game/seed inventory, local workload, metrics,
failure rules and local acceptance thresholds. Its lock detects contract drift.
Required SHA-256 bindings reject missing evidence and changed parent sources.
The Phase 2–3 archive, decisions and holdout ledger are unchanged.

The operating target is 27,540 seconds from lifecycle start, including model
startup and the 600-second finalization reserve. Admission stops at 26,940
seconds. This is not a 27,540-second inference allowance plus cleanup.

## Local evidence

`make phase4-load` uses the production `QueuedInferenceExecutor`, with 110
concurrent client threads making 80 sequential requests each. A seeded client
submission order and fixed rotating 1/8/32 KiB byte payloads exercise request
isolation and mixed service inputs. Callbacks hash bytes and simulate short
service delays; they do not tokenize prompts, encode images, load the model,
play games, or exercise continuous batching on vLLM. Thread interleaving and
measured timings are intentionally not claimed deterministic.

The first local run completed 8,800 requests with zero request failures and all
110 clients completing 80 requests. Its maximum observed queue size was 109.
These figures establish only this synthetic queue smoke/load result; throughput
is not a model capacity estimate. Reports explicitly keep `C_nominal` and
`C_admit` null and `target_gpu_certified` and `phase4_complete` false.
An additional full local run is retained in `reports/phase4_local_load.json`:
8,800 completed, zero failures, maximum queue size 106. Its contract, parent
and harness hashes identify the measured setup; differing timings and queue
peaks reflect local thread scheduling, not a scheduler comparison.

`make validate-phase4` combines the new queue/cutoff tests with existing
production-path fixtures for 110-client orchestration, hung-worker finalization,
ambiguous dispatch, degraded evidence storage and model startup failures.
The new tests cover FIFO order/overflow, stale and canceled requests, timeout
result rejection, callback failures without retries, T0 journal exhaustion and
the exact operating cutoff. These are component/integration fixtures, not a
single combined 110-client model-backed fault soak. Disk-backed evidence loss
may degrade while preserving T0/T1 and legal play; failure to journal a
transaction must deny dispatch.

## Remaining gates before target execution

### Supervised runner implementation

`make phase4-service-probe` now executes the exact generated requests in eight
1,100-request windows against a fake backend. `FAULT=startup`, `inference`,
`timeout`, `storage`, `finalization`, `hang`, or `finalization_hang` exercises
failure paths. Fault runs deliberately exit nonzero; tests assert that outcome.
The production model lifecycle/transport adapter is implemented separately in
`TargetServiceBackend`, but target launch is unconditionally disabled pending
a new approved execution lock and compute reservation. Editing a boolean in
the draft does not enable spending. No target-GPU runner certification is claimed.

The supervisor launches a dedicated process session and owns its entire process
group. It stops work at its scaled local admission cutoff, sends termination,
escalates to kill after bounded grace, and cleans only its own temporary directory.
This includes noncooperative inference and stalled finalization. Unknown cleanup
or missing results cannot masquerade as acknowledged finalization. An acknowledged
fake-service shutdown is not an official scorecard finalization acknowledgment.

Local controls are a 15-second lifecycle, two-second reserve, 2 GiB aggregate
process-group RSS and 16 MiB scratch ceiling, checked approximately every 20 ms
plus monitor latency. These are polling limits, not OS-enforced allocation caps;
short spikes can exceed them. `ps` must be permitted for the host-RSS monitor;
unavailable resource telemetry fails closed. This can require running local tests
outside a restrictive process-inspection sandbox. The target's GPU VRAM, host
RAM, disk and fault-soak thresholds are **not** inferred from these local limits.
The tests inject memory/disk telemetry breaches as well as real subprocess hangs.

The fake fault schedule injects startup failure before queue creation, inference
or timeout at callbacks, evidence-storage failure before measured windows, and
finalization failure/stall after the workload. Storage injection is a controlled
exception, not an actual disk-full event. Existing evidence-store degradation and
transaction tests remain separate. Target backend cancellation and full-game
integration remain prerequisites to enabling a live run. Artifact/context
preflight and VRAM monitoring are now implemented, as described below, but
have not been measured on the actual target.

### Target preflight and telemetry

`evaluation/phase4_preflight.py` verifies the full model tree using M0's hashing
algorithm; changed bytes, symlinks and unexpected layout fail closed. The launch
specification is SHA-bound and its 65,536-token context limit must match the audit.
Tokenization uses only the mounted artifact, the pinned Transformers version,
no remote code and no downloads. It includes the actual chat template, generation
prompt and thinking-disabled setting. No truncation is allowed, and prompt tokens
plus the 128-token completion allowance must fit. See the
[Transformers template contract](https://huggingface.co/docs/transformers/v4.57.0/chat_templating).

Where the exact model and tokenizer dependencies are installed, run the read-only
audit (full weight hashing may take time):

```bash
.venv/bin/python scripts/phase4_preflight.py --model-path /path/to/exact/model
```

The NVIDIA monitor requires exactly one RTX PRO 6000, a bound UUID and an explicit
VRAM ceiling. It checks device-wide memory before/after completions and polls
during service lifetime. Missing or ambiguous telemetry, changed identity and
over-limit samples fail closed; errors remain sticky. Polling is not an allocator
cap and may miss transient spikes. UUID and ceiling remain null in
`config/phase4_preflight_lock.json`, pending target configuration.

The adapter requires preflight before startup, cleans up on startup failure,
accepts only audited requests, and rejects missing server token counts or any
disagreement with offline prompt counts. Tests use fixture artifacts and mocked
tokenizers, GPU telemetry and service responses. No actual weights, GPU or model
inference were exercised. Server parity, sustained monitoring, in-flight
cancellation and full lifecycle behavior still require target evidence.
Preflight success grants no launch authority: the target gate stays closed until
a separately reviewed execution lock and compute reservation exist.

Offline request-shape preparation is now implemented in
`evaluation/phase4_workload.py`; inspect it with `make phase4-workload`.
It captures requests through the actual `E1Policy.propose` path with a recording
completion client, exercising 16/32/64-square grids and 0/1/79-transition history.
The nine deterministic requests span 1,707–30,700 serialized request bytes;
token counts remain unknown until measured with the frozen tokenizer/service.
E1S-R sends JSON grids as text to a multimodal-capable model, not image attachments.
No alternate image/prompt format is introduced. The 110-client/8,800-request
assignment is deterministic and hash-bound. These are generated shape fixtures,
not an empirical sample of real game trajectories.

`config/phase4_target_profile.json` proposes one eight-GPU-hour, private unscored
service prescreen, with eight fixed 1,100-request windows and a conservative
empirical throughput projection. It is explicitly a **draft**, with zero
authorized compute and no bound executable runner. The minimum-window haircut
and service headroom are prospective margins, not confidence bounds or a hard
capacity guarantee. A service prescreen cannot replace full-game certification.
All startup/failure time must be charged; no automatic reruns are proposed.

1. Capture and bind empirical E1S-R grid-text prompt-length/context mixtures.
   Freeze a full 110-client development-only workload manifest and seeds.
   The existing 15-game inventory is a provenance input, not 110 independent games.
2. Register a target protocol, runner hashes, repetitions, conservative sustained
   throughput bound and numeric fault/recovery thresholds before measurements.
   Freeze nominal capacity and headroom-adjusted admission capacity separately;
   the local contract reserves 20% service headroom, not a measured capacity.
3. Allocate explicit accelerator hours, notebook runs, game passes and restart
   contingency in a new prospective record. This preparation contract authorizes
   zero GPU hours, target runs, scored submissions and holdout runs; it transfers
   no Phase 2 budget. No expensive execution has been launched.
4. Measure startup, real mixed-load queues/service, memory/storage pressure,
   inference timeout and cancellation, legal degradation and finalization on the
   actual target. In-flight callback timeout does not prove model computation
   was canceled: backend/process cancellation remains a target gate. Require
   a complete lifecycle below 27,540 seconds and verified finalization.
5. Consider at most one advanced scheduler only after a measurable allocation
   failure. Register numeric improvement thresholds and a separate counterbalanced
   whole-workload comparison with paired-run uncertainty before execution.
   No alternative is admitted now; the minimum scheduler remains rollback.

The Phase 4 contract is deliberately scoped to local preparation, not a claim
that the target experiment contract or certification is finished. Further
protocols must be versioned rather than editing historical decisions. H1 remains
preserved. Scheduling reliability does not explain or remedy cd82's ineffective
clicks; action-selection improvement needs its own scoped development study.
