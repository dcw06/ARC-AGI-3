# Stage B R3 one-shot GPU attempt

The reviewed R6 source lock SHA-256 is
`3afce33e6d3e7bbe763b3850cccb9e8cf901c11a8aec390c4e09ef78a8266da3`.
The source and compute decisions were recorded separately, and one
3,600-second provider reservation was created for attempt
`gab1-75481e91d3704b17980b7bb5d9f0dea0`.

The exact private, Internet-disabled notebook package was verified before
one upload to
`https://www.kaggle.com/code/daichongwei06/arc3-grounded-action-v1-r3`.
Kaggle returned version 1 with no invalid source attachments. The launch
claim and reservation are **consumed**; no automatic retry is authorized.
The first read-only provider observation, at 2026-09-24 17:30:35 UTC,
reported `KernelWorkerStatus.RUNNING` and no failure message.

Monitor with:

```sh
wsl -d Ubuntu --cd /mnt/c/Users/jjzzw/Desktop/AGI /home/jingjing/.local/share/agi/dev-env/bin/python -m scripts.observe_grounded_action_v1_r3
```

Completion, downloaded evidence, independent trajectory replay, cleanup,
and exact billing reconciliation are still pending. A provider status of
`RUNNING` alone is not study acceptance or Phase 4 certification.

The terminal provider status was `KernelWorkerStatus.ERROR`. The 27 files
were downloaded and evaluated; see `reports/perception_stage_b_r3_failure.md`
and `reports/perception_stage_b_r3_evaluation.json`. The attempt stopped at
game bootstrap after a successful model canary, before any study call or
game action. The reservation remains consumed and exact billing is open.
