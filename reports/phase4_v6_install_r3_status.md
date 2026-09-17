# R3 installation-check launch

Kaggle accepted version 1 at 2026-09-17 11:26:10 UTC:
https://www.kaggle.com/code/daichongwei06/arc3-phase4-v6-install-repair-r3

Terminal status observed at 11:37:20 UTC: ERROR. All attachment references were accepted.
Attempt: `p4-v6-install-r3-20260917T112448Z`.

One installation-only RTX PRO 6000 attempt, private and offline, with a fresh
1800-second reservation and 900-second internal deadline. Provider timeout was
requested at 1800 seconds; independent enforcement is not verified. No automatic
retry or model pilot is authorized. The launch claim is consumed.

The original r3 review snapshot remains unchanged. The separate execution lock
and launch review bind its source/artifact hashes, launcher and local resolver
evidence. Prior test and static wheel-inspection evidence remain applicable.
The Torch wheel contract and both install commands passed. The combined
environment then failed `pip check`: the second install upgraded NumPy from
2.2.6 to the frozen environment pin 2.4.4, which conflicts with numba 0.61.2
(`numpy>=1.24,<2.3`) and mistral-common 1.11.1 (`numpy>=1.25,<2.4` on Python
3.12). CUDA execution was not reached. Command success does not establish a
consistent dependency environment.

The current frozen requirements cannot coexist in one venv. Before another
GPU attempt, evaluate isolating the model service from the game environment,
or explicitly revising the dependency lock and its comparability assumptions.
Check the complete dependency set together before installing; do not skip
`pip check` or silently replace the frozen NumPy pin.

Probe elapsed time: 120.814 seconds. Account GPU usage increased 129.673 seconds;
exact per-attempt billing is unknown, so all 1800 reserved seconds remain held.
The attempt is consumed and no retry was launched. The failure result provides
no affirmative GPU/scratch cleanup receipts.

Evaluation: `reports/phase4_v6_install_r3_evaluation.json`.
Portable evidence: `evidence/phase4-v6-install-r3-failed-v1.zip`, including both
pip installation reports, stage logs and status/usage observations.

Monitor and retain status/usage from the Windows repository root:

```powershell
.cache/kaggle-windows-client/Scripts/python.exe scripts/observe_phase4_install_r3.py
```

Launch receipt: `reports/phase4_v6_install_r3_launch.json`.
Accounting: `config/phase4_v6_install_r3_compute_ledger.json`.
Observations: `reports/runs/phase4-v6-install-r3-20260917/provider-observations.jsonl`.
Prelaunch account usage: 26253.548 GPU-seconds. Exact per-attempt billing remains
unknown; retain the full reservation until reconciled.

R3 outputs were downloaded into a distinct evidence directory and evaluated by
`scripts/record_phase4_install_r3_result.py`; terminal status and usage are recorded.
The r1/r2 result scripts contain fixed attempt paths and must not be used to
overwrite those historical attempts.
