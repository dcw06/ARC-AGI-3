# Stage B R6 one-shot GPU attempt

The R9 source review lock is
`fed295e46233285fa3c92ce190a1b9080fe19d791503d2e2da1ef63253028571`.
Explicit source approval and separate one-attempt compute authorization
were recorded, then a fresh 3,600-second reservation was created for
`gab1-0e774953d34141acbbd1e9c30ffdb837`.

The exact private, Internet-disabled package was verified before one
upload to <https://www.kaggle.com/code/daichongwei06/arc3-grounded-action-v1-r6>.
Kaggle accepted version 1 with no invalid source attachments. The launch
claim and reservation are **consumed**; no automatic retry is authorized.
The first read-only provider observation at 2026-09-24 22:40:26 UTC was
`KernelWorkerStatus.RUNNING` with no failure message. This is startup
status, not study acceptance.

Monitor with:

```sh
wsl -d Ubuntu --cd /mnt/c/Users/jjzzw/Desktop/AGI /home/jingjing/.local/share/agi/dev-env/bin/python -m scripts.observe_grounded_action_v1_r6
```

The 3,300-second internal limit, two episodes, at most two actions each,
12 study completions plus one canary, and no scored submission remain
bound in the reviewed source and authorization. Completion, downloaded
evidence, independent trajectory replay, cleanup, and exact provider
billing reconciliation remain pending. The initial quota change is
account-wide and cannot establish exact attempt billing.

The terminal provider status was `KernelWorkerStatus.ERROR`. All 27 files
were downloaded and hash-verified; independent evaluation found the first
prediction response used identical `no_change` values for prediction and
alternative. No game action occurred. See
`reports/perception_stage_b_r6_failure.md` and
`reports/perception_stage_b_r6_evaluation.json`. The consumed reservation
cannot be reused.
