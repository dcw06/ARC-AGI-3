# Track 3 session 1, attempt 1: technical failure before readiness (sanitized)

**Status: consumed and preserved; not retried.** The notebook and raw outputs stay private and account-only. No model
was started, no game action was taken and no study data exists, so there is no outcome to report (protocol §9).

| Item | Value |
|---|---|
| Attempt | `ssv1rt2-s1-c5ebca7f7b444bb3b63b6c90b3cf306b`, submitted October 11, 2026, 20:50 UTC, in one push (provider version 2) |
| Package | private review r7, lock `e5e6b0d5…` (public review r4, lock `b9f16600…`, plus the four private bindings) |
| Approvals | Gate 4, source, compute (session 1 only) and launch, as four separate owner answers |
| Provider status | RUNNING at 20:52:58, ERROR by 20:54:58 UTC |
| Independent live evaluation | technically incomplete; no run evidence; monitor failure receipt; the evaluating checkout's review lock verified |

## What happened

**Install and bind.** Installation passed in 131.6 s against the 450-s window. The monitor then bound the real GPU: one
RTX PRO 6000 with 102.6 GB.

**The first sample.** At 133.3 s the monitor started its sampling clock, and its first sample violated the frozen
sampling-gap limit (1 s between samples):

| Probe in the first sample | Time |
|---|---|
| GPU (`nvidia-smi`) | 0.012 s |
| Host RSS of the worker's process group | 5.45 s |
| Scratch | 0.0004 s |
| Gap since the clock started | 5.47 s |

The monitor stopped before readiness. The supervisor therefore never released the worker, and the worker correctly
refused to start. The model host was never started.

**Cleanup was certified.**
- Process groups were absent and child ownership was verified.
- Independent GPU cleanup found 0 GPU processes.
- Scratch was removed.
- The fail-closed finalization recorded the guard, the lifecycle as finalized, and the extracted source as removed.
- The first-cell lifecycle took 140.5 s.

## Cause

The RSS probe's module import had already been paid during GPU binding, before the clock started. The probe's
subprocess also runs under a 1-s timeout, which would raise rather than return. So the 5.45 s was a one-time cost of
the first `ps` process creation in the fresh container.

Track 1's first probe on the same machine type and runtime lineage took 0.03 s, and its steady-state samples were tens
of milliseconds. Every CPU rehearsal passed because these costs are absent on a warm local machine.

The exact kernel-level mechanism is not established from the retained evidence.

## Repair (runtime only; the science and the frozen limits are unchanged)

**The change.** Each probe now runs once, untimed, before the sampling clock starts (`ATTEMPT1_REPAIRS` in
`scripts/derive_stagnation_supervision_runtime_v2.py`, applied to the derived `monitor.py`).

**What stays the same.**
- The 0.5-s interval and the 1-s gap limit.
- The RAM, scratch and VRAM limits.
- Monitor readiness after a durable first sample.

A probe that is persistently slow still fails closed.

**Regression** (`tests/test_ssv_runtime_v2_attempt1_monitor.py`):
- the unchanged pre-fix monitor logic reproduces the target failure;
- the repaired monitor completes;
- a slow probe after the warm-up still fails closed.

## What follows

A replacement attempt needs:
1. a new review lock;
2. Gate 4 evidence re-bound to it;
3. new, separate source, compute and launch decisions.

Attempt 1 stays consumed. Session 2 is not authorized.
