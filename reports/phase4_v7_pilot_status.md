# V7 development pilot — failed before model startup

At 2026-09-17 14:11:18 UTC, Kaggle reported `ERROR`. The split installation passed; the worker rejected the game directory with `ValueError: environment mount inventory differs from package`. Final evaluation failed. Source, dependency, scratch, process, and GPU cleanup receipts passed. Internal elapsed time was 132.544 seconds; aggregate account usage increased by 142.754 seconds (not exact per-attempt billing). The consumed eight-hour reservation remains retained, with no retry authorized.

Diagnosis: `reports/phase4_v7_pilot_failure.md`. Evidence and reconciliation: `reports/phase4_v7_pilot_evaluation.json`.

Kaggle accepted version 1 at 2026-09-17 13:34:05 UTC. The read-only observation at 13:34:29 UTC reported `RUNNING`, with no failure message or rejected attachments.

Notebook: https://www.kaggle.com/code/daichongwei06/arc3-phase4-development-v7-pilot

Attempt: `p4-v7-pilot-20260917T132406Z`. The single launch claim is consumed. The local accounting reservation remains 28,800 seconds; no automatic retry or release is authorized. The requested provider timeout is eight hours and the approved internal lifecycle limit is 27,540 seconds (7h39m), including cleanup.

The launch-ready notebook preserves the approved v7 source snapshot and adds the separately authorized execution sidecars. Its embedded source and authority gate passed locally before submission, without installation or GPU access. Launch and status do not establish pilot success.

From the repository root in PowerShell, monitor with:

```powershell
.\.cache\kaggle-windows-client\Scripts\python.exe scripts/observe_phase4_v7_pilot.py
```

Each observation is appended to `reports/runs/phase4-v7-pilot-20260917/provider-observations.jsonl`. The launch receipt is `reports/phase4_v7_pilot_launch.json`; quota baseline is `reports/phase4_v7_pilot_prelaunch.json`; accounting is `config/phase4_v7_pilot_compute_ledger.json`.

After termination, download and retain version 1 output, evaluate the authoritative `evaluation/notebook-result.json` and its bound evidence, verify cleanup and deadline compliance, and reconcile quota observations. Account quota deltas are not exact per-run billing. The full reservation remains retained until reconciliation; a provider `COMPLETE` status alone is insufficient evidence of success. Use the numeric `gpu_quota_seconds` fields because the SDK's serialized duration strings can lose whole days.
