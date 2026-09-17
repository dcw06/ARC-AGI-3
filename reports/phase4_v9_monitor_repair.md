# V9 monitor diagnostics and independent cleanup review

Implemented a new v9 source revision after v8 failed during model startup without retaining its rejected measurement. V7 and v8 source/notebook hashes remain intact. No GPU run, reservation, upload, or new compute authorization was created.

## Failure diagnostics

`monitor_diagnostics.py` collects the GPU, process-group RSS, and scratch measurements with individual probe durations. Rejected measurements retain the exact violated constraint, previous/current timestamps, sampling gap, configured limits, GPU identity and memory, and previous telemetry-write duration. Probe exceptions retain their active phase and elapsed time. Telemetry persistence errors retain their phase and duration in the monitor's reserved failure receipt. Rejected samples never enter valid telemetry.

The live GPU adapter returns raw measurements for immediate validation so a VRAM rejection can retain the observed value. The limits remain 86 GiB VRAM, 128 GiB RSS, 4 GiB scratch and a maximum one-second sampling gap. The 0.25-second polling sleep and existing serial probes remain unchanged: this repair makes delays diagnosable, and does not claim to resolve the unknown v8 triggering delay.

## Independent cleanup

The supervisor now attempts cleanup of every owned process group even if one cleanup attempt fails. In live mode, it then runs an independent GPU identity and compute-process inventory query, including when the monitor died before or after worker release. Each query is bounded by two seconds and the remaining lifecycle deadline. A missing command, timeout, malformed output, identity mismatch, remaining processes, failed group cleanup, or exhausted deadline cannot produce a verified cleanup result.

The result is retained separately at `control/gpu-cleanup.json`, including when the continuous monitor has no final receipt. Evidence-write failure invalidates verification and attempts a reserved control failure receipt. Successful independent cleanup never restores continuous-monitoring coverage, clears an earlier failure, or makes the pilot pass. Cleanup evidence persistence and final evaluation remain within the outer lifecycle/final-notebook deadline checks.

## Validation and review snapshot

23 Linux tests passed in 17.372 seconds:

```text
tests.test_phase4_v9_monitor_repair
tests.test_phase4_v9_review
tests.test_phase4_v9_bridge
tests.test_phase4_v9_game_assets
```

Coverage includes delayed GPU probes, RSS/scratch/VRAM rejection and exact boundaries, probe exceptions, telemetry-write failure, empty/occupied/malformed GPU process responses, identity mismatch, expired and exceeded deadlines, and monitor death that still triggers supervisor cleanup but cannot pass evaluation. Existing authority, process-group cleanup, final acceptance, bridge and game-staging checks also passed. GPU query behavior is mocked in local tests; target validation is still outstanding.

GPU-disabled notebook: `notebooks/phase4-lifecycle-v9-review-r1/profile.ipynb`.

Source lock SHA-256: `f8211f06a0a45efc137ffbeabeb1b218535c913eccbbb15e485f6c5276d4a3f3`.

Notebook SHA-256: `be4c973d5a354bb8ebd956e9e088c05a9738e0c085b63b97757ee358075549bc`.

The snapshot is ready for review. Its runtime authority remains closed; no claim of user approval of this hash or target GPU certification is made.
