# Coordinate diagnostic v2 replacement attempt

Final: COMPLETE observed 2026-09-22 19:49:07 UTC. Independent archived replay
passed. Baseline 15/28 correct; explicit indexing 16/28. The wording-promotion
threshold was not met. See [final disposition](phase4_coordinates_v2_disposition.md)
for results, checksums, replay, cleanup, and accounting limits. Reservation consumed.
The launch-time status below is historical.

Kaggle accepted version 1 at 2026-09-22 19:27:25 UTC. At 19:27:39 UTC,
the provider reported `KernelWorkerStatus.RUNNING`, with no failure message.
This status does not yet establish successful tokenizer verification or inference.

Run: https://www.kaggle.com/code/daichongwei06/arc3-phase4-coordinates-v2-r1

Attempt: `co2-a6d2e62a2d134105bb1603c67efce868`.
Review lock SHA-256: `19f625d726b98857d0787b7d495e0dbde8bd123028de548496d56550178f8a8a`.

The repair restores the original pinned tokenizer manifest, uses the runtime
verifier in the CPU audit, and retains expected/observed hashes on mismatch.
The previous revision and its consumed reservation are preserved. Cases and
token counts are unchanged: 56 diagnostic requests and one startup canary.

Validation: 24 local tests passed; all 802 packaged source bindings verified;
the GPU-disabled notebook compiled and rejected missing authority. Clean-checkout
archive replay passed, synthetic launch packaging passed, and a second upload
was rejected. See the v2 local checks, package review, token audit, and final checks.

The user's repair-and-launch request was recorded in separate source and compute
receipts. The fresh reservation was consumed before the single upload. The run
is private and unscored, with a 2,100-second provider ceiling, 1,980-second internal
deadline, zero environment actions/scorecards, and no automatic retry.

Monitor from the repository root:

```powershell
.cache/kaggle-windows-client/Scripts/python.exe scripts/observe_phase4_coordinates_v2.py
```

After completion, download and checksum outputs, replay independently, archive,
and reconcile usage. Exact provider billing remains unknown. Account-wide SDK
quota observations are retained but differ from raw provider duration fields;
they are not exact per-attempt billing. No diagnostic outcome, policy promotion,
or production Phase 4 completion is claimed while the attempt is running.
