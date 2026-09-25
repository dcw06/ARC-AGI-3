# Stage B R8 pilot status

**Historical initial-status snapshot.** Kaggle later reported `COMPLETE`.
The downloaded and independently evaluated two-arm result is recorded in
`reports/perception_stage_b_r8_disposition.md`. The `RUNNING` observation
below is only the initial provider state.

The private, unscored R8 notebook was uploaded once to
https://www.kaggle.com/code/daichongwei06/arc3-grounded-action-v1-r8.
Kaggle accepted provider version 1 at 2026-09-25 01:32:51 UTC. The
one-use attempt `gab1-2b4f10a6f6b949aaa26aa457b9f56272` is consumed;
no automatic retry is authorized.

The initial read-only observation at 2026-09-25 01:33:14 UTC was
`KernelWorkerStatus.RUNNING`, with no failure message. The account-wide
GPU `time_used` reading was 12,998.053782 seconds; this is not an exact
bill for this attempt. The completed workload and independent result
remain to be downloaded and evaluated.

Monitor from the project root:

```powershell
wsl -d Ubuntu -- /home/jingjing/.local/share/agi/dev-env/bin/python -m scripts.observe_grounded_action_v1_r8
```

Provider observations append to
`reports/runs/phase4-grounded-action-v1-r8/provider-observations.jsonl`.
