# Stage B R7 pilot status

The private, unscored R7 notebook was uploaded once to
https://www.kaggle.com/code/daichongwei06/arc3-grounded-action-v1-r7.
Kaggle accepted provider version 1 at 2026-09-25 00:19:37 UTC. The
one-use attempt `gab1-c507bf9ce1d54bc2ab34296a11d0f5f5` is consumed;
no automatic retry is authorized.

The initial read-only observation at 2026-09-25 00:20:13 UTC was
`KernelWorkerStatus.RUNNING`, with no failure message. The account-wide
GPU `time_used` reading was 12,392.44248 seconds; this is not an exact
bill for this attempt. The completed workload and independent result
remain to be downloaded and evaluated.

Monitor from the project root:

```powershell
wsl -d Ubuntu -- /home/jingjing/.local/share/agi/dev-env/bin/python -m scripts.observe_grounded_action_v1_r7
```

Provider observations append to
`reports/runs/phase4-grounded-action-v1-r7/provider-observations.jsonl`.
