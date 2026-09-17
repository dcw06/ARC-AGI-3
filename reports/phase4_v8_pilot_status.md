# V8 repaired development pilot — failed during model startup

At 2026-09-17 14:57:39 UTC, Kaggle reported `ERROR`. Game staging and installation passed; the monitor failed with a combined resource/sampling-gap error during model startup. The exact rejected measurement was not retained. See `reports/phase4_v8_pilot_failure.md` and `reports/phase4_v8_pilot_evaluation.json`. GPU cleanup remains unverified; other cleanup receipts passed. The attempt is consumed and no retry was submitted.

Kaggle accepted version 1 at 2026-09-17 14:25:11 UTC with no rejected attachments. At 14:25:38 UTC the status was `RUNNING`, with no failure message.

Notebook: https://www.kaggle.com/code/daichongwei06/arc3-phase4-development-v8-pilot

Attempt `p4-v8-pilot-20260917T142353Z` is consumed. One fresh eight-hour reservation, 7h39m internal lifecycle deadline, no automatic retry. Previous attempts remain separately accounted for. The repaired staging path passed local regression checks; running status does not establish target success.

Monitor from the repository root:

```powershell
.\.cache\kaggle-windows-client\Scripts\python.exe scripts/observe_phase4_v8_pilot.py
```

The launch receipt, quota baseline, and observations are in `reports/phase4_v8_pilot_launch.json`, `reports/phase4_v8_pilot_prelaunch.json`, and `reports/runs/phase4-v8-pilot-20260917/provider-observations.jsonl`. On termination, retain the version 1 output and evaluate the final notebook receipt, monitor evidence, cleanup, deadline, and quota delta. Exact provider billing remains unknown; full local reservation remains retained pending reconciliation.
