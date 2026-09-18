# V12 target validation and full pilot

Update at 2026-09-18 07:25 UTC: provider status ERROR. Target constrained canary passed and all 110 clients completed 7,582 requests with zero policy failures. The inherited evaluator incorrectly retained the old eight-token canary limit and rejected the valid 29-token v12 canary. See `reports/phase4_v12_pilot_failure.md` and `reports/phase4_v12_pilot_evaluation.json`. The queued observation below is historical.

The user selected the full v12 pilot on 2026-09-18: schema validation followed by all 110 clients within the existing eight-hour budget limit. A fresh single-attempt reservation was created; no consumed v11 reservation was reused.

Source approval binds review lock `c9123cab5b4409f4333bb01a4cda091a4f920e79fa70a30810375814e9b35542`. The GPU-disabled review remains unchanged. The separate 564,701-byte launch package was unpacked and checked locally: every source and authority hash matched, the notebook compiled, and the live authority gate accepted the bound reservation without performing GPU work.

Kaggle accepted version 1 at 2026-09-18 04:27:10 UTC with no reported attachment errors. At 04:27:29 UTC the status was `KernelWorkerStatus.QUEUED`, with no failure message. This is launch acceptance, not evidence of model readiness or successful schema enforcement.

Notebook: https://www.kaggle.com/code/daichongwei06/arc3-phase4-development-v12-pilot-r1

Monitor from the repository root in PowerShell:

```powershell
.\.cache\kaggle-windows-client\Scripts\python.exe scripts/observe_phase4_v12_pilot.py
```

Attempt: `p4-v12-pilot-20260918T042450Z`. Maximum provider timeout: 28,800 seconds. Internal lifecycle deadline: 27,540 seconds. Automatic retries: zero. Launch receipt: `reports/phase4_v12_pilot_launch.json`. Reservation ledger: `config/phase4_v12_pilot_compute_ledger.json`.

Evidence has been downloaded and archived; failure diagnosis and aggregate usage reconciliation are recorded. Exact provider billing remains unknown, and the full local reservation remains held. The original notebook verdict remains failed. Do not upload this consumed attempt again.
