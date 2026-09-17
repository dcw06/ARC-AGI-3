# R5 installation check

Kaggle accepted version 1 at 2026-09-17 12:12:19 UTC:
https://www.kaggle.com/code/daichongwei06/arc3-phase4-v6-install-repair-r5

Terminal status observed at 12:18:02 UTC: COMPLETE. The installation check passed.
All attachment references were accepted.
Attempt: `p4-v6-install-r5-20260917T121119Z`.

R5 integrates the locally verified HeadlessEnvironment helper into the split
installation probe, setting MPLBACKEND=Agg and placing Matplotlib configuration
inside owned scratch. Seven focused tests passed, including backend override,
split-environment checks and isolated embedded-notebook imports. Prior notebook
sources are preserved.

One private offline RTX PRO 6000 installation-only attempt; a new 1800-second
reservation, one shared 900-second internal deadline, and provider timeout
requested at 1800 seconds. Independent provider cutoff enforcement is not
verified. The claim is consumed, with no automatic retry or model pilot allowed.

Monitor from the Windows repository root:

```powershell
.cache/kaggle-windows-client/Scripts/python.exe scripts/observe_phase4_install_r5.py
```

Launch receipt: `reports/phase4_v6_install_r5_launch.json`.
Accounting: `config/phase4_v6_install_r5_compute_ledger.json`.
Observations: `reports/runs/phase4-v6-install-r5-20260917/provider-observations.jsonl`.
Prelaunch account usage: 26532.504 GPU-seconds. Exact attempt billing is unknown;
retain the full reservation until reconciled.

Verified result: all 178 model payloads and 31 game wheels matched their frozen
hashes. Both isolated environments resolved and installed offline, passed
dependency checks and runtime isolation assertions. Model runtime: Python
3.12.13, Torch distribution 2.10.0/runtime 2.10.0+cu128, vLLM 0.19.0,
Transformers 4.57.6, CUDA build 12.8, RTX PRO 6000 Blackwell Server Edition,
driver 580.159.04. The CUDA tensor operation and vLLM extension import passed.
Scratch removal and empty GPU process inventory passed. Probe elapsed time was
133.001 seconds, below the shared 900-second limit.

Aggregate account usage increased 143.263 GPU-seconds to 26675.767. The full
1800-second reservation remains retained pending exact billing. No retries or
additional sessions launched.

Evaluation: `reports/phase4_v6_install_r5_evaluation.json`.
Portable evidence: `evidence/phase4-v6-install-r5-passed-v1.zip`.
Evidence archive SHA-256:
`7eab12700172f0e3e0683509d917c6c71aba242efb7cfd3893de70d0312d5a2d`.

This closes target offline installation verification for the split r5 path.
No model weights were loaded and no gameplay/pilot was run. The integrated
pilot still needs tokenizer/service separation, monitoring/deadline review,
a new approved source/protocol/notebook freeze, and separate pilot authority.

R5 outputs were downloaded and both environment stages, runtime/CUDA checks and
cleanup receipts were evaluated by `scripts/record_phase4_install_r5_result.py`.
Earlier result scripts contain fixed historical paths and must not be reused
to overwrite prior attempts. The model pilot's tokenizer/service separation
remains outside this installation check.
