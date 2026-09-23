# Integrated ar25 v1: submitted once

Final: COMPLETE observed 2026-09-23 00:08:57 UTC. Frozen independent replay
passed. Control: eight actions, zero levels. Structured: invalid inventory JSON
at the 2,048-token cap, zero actions; downstream stages unobserved. See
[final disposition](phase4_integrated_v1_disposition.md). Reservation consumed.
The submission-time status below is historical.

Kaggle accepted version 1 at 2026-09-22 23:23:43 UTC. At 23:23:58 UTC the
provider reported `KernelWorkerStatus.RUNNING`, with no failure message.
Running status does not establish model readiness or successful study completion.

Run: https://www.kaggle.com/code/daichongwei06/arc3-phase4-integrated-v1-r1

Attempt: `ic1-b2b8f5dbc51747ffa4f15af59ff85ed8`.
Reviewed source lock: `e254bd8f0ce129535b4a6e8b1ac0e963ffb6ba58be19aaf2b0a744acb9beb372`.
Provider cap: 3,600 seconds; internal lifecycle: 3,300 seconds. Two private,
unscored development episodes, at most eight actions each and 25 study calls
plus one startup canary. No automatic retry or production certification.

The previous attempts to execute the submission command were blocked by automatic
approval review before process creation; the reservation remained unused and no
claim/launch receipt existed. The user then answered “OK start the GPU run” to
the explicit confirmation naming this executable, bundled project source and
retained development observations, exact private Kaggle destination, and 3,600-second
compute cap. After revalidation, the launch helper consumed the existing reservation
before its single upload. The launch receipt records provider acceptance without
invalid attachment sources. No historical notebook was reused.

Monitor from repository root:

```powershell
.cache/kaggle-windows-client/Scripts/python.exe scripts/observe_phase4_integrated_v1.py
```

After terminal status, download/checksum/archive all outputs and logs, independently
replay trajectories and final cleanup, then apply the human scoring rubric where
mechanical metrics are insufficient. Reconcile provider observations separately:
exact billed seconds remain unknown, and account-wide SDK quota/raw duration
disagreement remains unresolved. The consumed reservation must not be reused.
