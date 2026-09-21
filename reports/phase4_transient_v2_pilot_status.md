# Transient v2 R1 attempt status

The user explicitly approved both source and separate compute authorization with
"Yes I confirm both". Both receipts bind review lock
`5e0341ec0bd14a1b8ca054ff3df678ea71344d41ccd941058881253c7c8be842`.

Attempt: `tf2-32d9f8eae032409a9469a6f1e3c9c59f`.
One local 3,600-second reservation was created, the deterministic package verified,
and the launch claim consumed before the sole upload request. No retry is authorized.

Kaggle accepted version 1 at 2026-09-21 06:53:11 UTC:
https://www.kaggle.com/code/daichongwei06/arc3-phase4-transient-v2-r1

At 06:53:34 UTC the observed status was `KernelWorkerStatus.QUEUED`, with no failure
message. Running or completion has not yet been observed. The provider timeout
requested was 3,600 seconds. Six episodes, 120 policy calls plus one canary remain
the approved ceilings.

Read-only monitoring from the repository root:

```powershell
.\.cache\kaggle-windows-client\Scripts\python.exe scripts/observe_phase4_transient_v2.py
```

The launch receipt and prelaunch quota observation are retained in reports;
subsequent provider observations are in the ignored run-evidence directory.
The queued observation reports zero provider-reserved seconds; this does not undo
the local consumed reservation. Raw quota allowance (21,600 seconds) differs from
SDK-converted allowance (108,000 seconds), and the raw usage duration is malformed
(`3119.43.0s`). Exact billing is therefore not established by these observations.

Pending terminal status: download retained outputs, independently evaluate v2
trajectories and cleanup, archive/hash evidence, and reconcile usage. No solving
improvement or Phase 4 completion is claimed.

## Completed status and downloaded outputs

At 2026-09-21 22:08:31 UTC, Kaggle reported `KernelWorkerStatus.COMPLETE`
with no failure message. Download completed: 155 provider output files plus the
console log, 156 files totaling 7,265,430 bytes. File hashes are retained in
`reports/phase4_transient_v2_download.json`; raw files remain under the ignored
`reports/runs/phase4-transient-v2-r1-pilot/download` directory.

The target notebook reports `passed=true`, source removal, elapsed 754.450747112
seconds, and 60 acknowledged transitions per arm. Both arms report zero completed
levels. These are downloaded target results, not yet independently replayed local
acceptance. Independent evaluation, archival, and exact usage reconciliation
remain pending. No additional attempt is authorized.
