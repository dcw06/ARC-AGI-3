# R4 split-environment installation check

Kaggle accepted version 1 at 2026-09-17 11:58:00 UTC:
https://www.kaggle.com/code/daichongwei06/arc3-phase4-v6-install-repair-r4

Terminal status observed at 12:02:34 UTC: ERROR. All attachment references were accepted.
Attempt: `p4-v6-install-r4-20260917T115636Z`.

One private offline RTX PRO 6000 installation-only attempt, with a new
1800-second reservation, a shared 900-second internal deadline, and provider
timeout requested at 1800 seconds. Independent provider cutoff enforcement is
not verified. No automatic retry or model pilot is authorized. The launch claim
is consumed. Prior reservations remain unchanged.

The r4 snapshot remains unchanged and hash-verified. The launch review also
binds the launcher, credential helper, split dependency audit and local evidence.
Both isolated environments resolved and installed their packages and passed
`pip check`. Game imports failed because inherited `MPLBACKEND` selected
`module://matplotlib_inline.backend_inline`, unavailable in the frozen game
venv. The NumPy conflict is resolved; CUDA checks were not reached.

Target evidence confirms scratch removal and an empty GPU process inventory.
Probe elapsed time was 139.779 seconds. Aggregate account usage increased
149.283 GPU-seconds; exact attempt billing remains unknown and the full
1800-second reservation is retained. No retry launched.

Evaluation: `reports/phase4_v6_install_r4_evaluation.json`.
Portable evidence: `evidence/phase4-v6-install-r4-failed-v1.zip`.

A prospective `HeadlessEnvironment` helper in
`certification/phase4_v6/headless_environment.py` sets `MPLBACKEND=Agg` and
routes `MPLCONFIGDIR` into owned scratch. A real WSL offline game installation
passed with Kaggle's inherited backend setting deliberately injected; game
imports and pip check succeeded, its sibling stayed empty, and scratch was
removed. Summary: `reports/phase4_headless_game_local.json`. Reproducer:
`scripts/validate_phase4_headless_game.py` (requires a fresh output directory).
This helper is not wired into the consumed r4 notebook. Integration into a new
review snapshot and target CUDA verification remain pending.

Monitor from the Windows repository root:

```powershell
.cache/kaggle-windows-client/Scripts/python.exe scripts/observe_phase4_install_r4.py
```

Launch receipt: `reports/phase4_v6_install_r4_launch.json`.
Accounting: `config/phase4_v6_install_r4_compute_ledger.json`.
Observations: `reports/runs/phase4-v6-install-r4-20260917/provider-observations.jsonl`.
Prelaunch account usage: 26383.221 GPU-seconds. Exact attempt billing is unknown;
retain the full reservation until reconciled.

R4 outputs and usage were downloaded and evaluated by
`scripts/record_phase4_install_r4_result.py`. Earlier result scripts have fixed attempt
paths and must not overwrite historical attempts. The model pilot's tokenizer/
service separation remains outside this installation check.
