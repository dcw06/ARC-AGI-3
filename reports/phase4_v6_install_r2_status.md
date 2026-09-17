# Repaired installation check r2

Kaggle accepted one new installation-only attempt on 2026-09-17 at 10:48:03 UTC.
Version 1: https://www.kaggle.com/code/daichongwei06/arc3-phase4-v6-install-repair-r2

Terminal status observed at 10:57:32 UTC: ERROR. All submitted attachment
references were accepted. Target installation and CUDA validation remain blocked.

The bootstrap repair passed on Linux x86_64 / Python 3.12.13 with host pip
24.1.2: empty venv creation, isolation checks and host-pip targeting succeeded.
All 178 model wheelhouse payloads and 31 environment wheels passed hash checks.
Installation failed because the resolver offers torch 2.10.0, but r2 requires
torch==2.10.0+cu128. No CUDA validation or model loading occurred.

The original model notebook builder already installs torch==2.10.0
(`scripts/build_m0_profile_notebook.py:178`). The r2 probe incorrectly retained
the stricter distribution requirement from r1. Before another revision, inspect
the frozen wheel's METADATA and torch/version.py, distinguish distribution
version from runtime build version, and test offline dependency resolution.
Do not simply weaken the CUDA 12.8 requirement or change the consumed snapshot.
Kaggle sitecustomize also reports missing wrapt in the empty venv; those messages
did not prevent the four bootstrap stages from passing and are not the fatal
resolver error.

Probe elapsed time was 32.386 seconds. Account GPU usage increased 41.272 seconds;
this is an aggregate delta, not exact per-attempt billing. Full 1800-second
reservation retained. No new launch authorized or submitted.
Evidence and evaluation are preserved in
`evidence/phase4-v6-install-r2-failed-v1.zip` and
`reports/phase4_v6_install_r2_evaluation.json`.

The new attempt `p4-v6-install-r2-20260917T104442Z` has its own 1800-second
reservation and a consumed launch claim. The notebook's internal limit is
900 seconds, with provider timeout requested at 1800 seconds. No retries are
authorized. The old failed attempt and its retained reservation are unchanged.

The r2 notebook embeds the repaired empty-venv bootstrap and preserves named
stage logs. Nine focused tests passed in WSL Python 3.12 before submission.
The source/protocol artifact hashes were verified before claiming the attempt.
No model weights or model pilot are included.

From the Windows repository root, fetch and retain a status/usage observation:

```powershell
.cache/kaggle-windows-client/Scripts/python.exe scripts/observe_phase4_install_r2.py
```

Receipts: `reports/phase4_v6_install_r2_launch.json`,
`reports/phase4_v6_install_r2_preflight.json`, and
`reports/runs/phase4-v6-install-r2-20260917/provider-observations.jsonl`.
Authority and accounting: `config/phase4_v6_install_r2_execution_lock.json`
and `config/phase4_v6_install_r2_compute_ledger.json`.

Version-1 outputs, bootstrap stage evidence, terminal status and quota were
downloaded and recorded by `scripts/record_phase4_install_r2_result.py`.
The older r1 result scripts have fixed r1
paths and must not be used to overwrite that attempt. Exact per-attempt billed
usage is unknown; retain the full reservation until reconciled. Account usage
before launch was 26212.276 GPU-seconds; aggregate differences alone do not
establish exact per-attempt billing.
