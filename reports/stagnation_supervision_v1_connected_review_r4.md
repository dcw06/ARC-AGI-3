# Track 3 R4: deadline evidence and telemetry coverage

Review candidate only. GPU disabled, private, no live authority, no upload or GPU run.
R1, R2 and R3 notebooks, locks and reports remain unchanged. This successor
supersedes the disclosed R3 telemetry-cap limitation for the proposed durations.

## Deadline regression

Forced cancellation may leave host-status at ready without final policy counters.
The deadline regression now loads the complete retained trajectory through
load_verified (inventory, lengths and hashes), checks retained calls and steps,
and requires the external deadline error and independent cleanup receipts.
A failed run remains incomplete; graceful host finalization is still mandatory
for successful target acceptance, not for proving calls occurred before cutoff.

## Frozen telemetry schedule

Both proposed sessions sample at exactly 0.5 seconds between probe rounds,
including monitoring through worker cleanup. This replaces the inherited 0.25
second cadence; it does not increase any evidence or compute allocation.
The existing one-second maximum observed gap remains enforced by sampling and
independent replay. Slow probes or persistence still fail closed; this schedule
is not a claim that a real GPU will meet those timing limits.

| Session | Provider proposal | Internal ceiling | Conservative sample bound |
| --- | ---: | ---: | ---: |
| 1 | 5,400 s | 5,100 s | 10,201 |
| 2 | 4,800 s | 4,500 s | 9,001 |

The bound is floor(internal_seconds / 0.5) + 1, allowing an initial sample.
Probe time only reduces the possible sample count. The monitor rejects other
cadences and durations exceeding 5,100 seconds before probing. Both monitor
receipt and telemetry manifest retain sampling_interval_seconds; target replay
requires the frozen value. Existing 13,220-sample, 1 MiB raw-chunk, 16 MiB monitor
and 128 MiB aggregate limits remain unchanged. Cleanup reserves are unchanged.

## Validation and reproducibility

The accelerated-clock regression exercises every observe-loop iteration through
5,099.5 and 4,499.5 seconds (10,200 and 9,000 samples), including final stop and
GPU-empty checks. It writes actual lossless chunks through EvidenceStore and
independently reads them back. It checks measured output size and a conservative
uncompressed/base64 size bound including atomic replacement headroom.
Persistence checkpoints are batched for this capacity test; it does not simulate
real disk latency. The connected suite separately exercises the actual async
writer, monitor handshake, bounded evidence, deadlines and process cleanup.
The first capacity-test draft misplaced the synthetic stop file outside the
shared component directories; EvidenceStore correctly rejected it. The fixture
now places the stop receipt under control. No production allocation was relaxed.

Run from Linux with the project's offline development dependencies:

```sh
python -m scripts.derive_stagnation_supervision_v1 --check
python -m scripts.check_stagnation_supervision_v1_review_r4 --check
python -m scripts.verify_stagnation_supervision_v1_audit_inputs_r3 --check
python -m scripts.review_stagnation_supervision_v1_notebook_r4 --folder notebooks/stagnation-supervision-v1-review-r4
```

The R4 local-check receipt records exact test counts and source/test bindings.
The R4 package receipt records unpacked compilation, unauthorized-live refusal,
CPU three-arm rehearsal, independent trajectory/lifecycle replay and cleanup.
The existing pinned-tokenizer audit is reused only with exact ordered-request
verification; no request, prompt, model, decoding or output cap changed.

## Remaining limits

This is a CPU-reviewed successor, not GPU launch approval or measured real GPU
behaviour. A separately reviewed live authorization package, explicit source
approval and fresh compute reservation are still required. ls20 remains
exploratory and cannot provide the missing second qualified continuation control.
The false-interruption gate therefore remains not certifiable. Production
certification, workload admission and exact accounting remain open.
