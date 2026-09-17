# Clean-environment bootstrap repair — September 17, 2026

Full-pilot follow-up: v7 now integrates the split environments and model-side
tokenizer/audit bridge. The implementation and new notebook are frozen for
source approval; see [v7 review](phase4_v7_review.md). No GPU pilot is authorized
or launched by this implementation work.

**Latest outcome: r5 passed target offline installation and CUDA smoke checks.**
Both isolated environments, game imports, vLLM extension import, CUDA tensor
operation and cleanup succeeded on RTX PRO 6000 / Python 3.12.13 / CUDA 12.8.
See [r5 verified result](phase4_v6_install_r5_status.md). Model loading and the
integrated pilot remain pending. Earlier entries below document repair history.

R4 follow-up: both split installs and dependency checks passed on target, but
game imports inherited an unavailable notebook plotting backend. Explicit `Agg`
selection passed a local reproduction; see [r4 status](phase4_v6_install_r4_status.md).
The prospective helper is not yet integrated into a new notebook revision.

Latest follow-up: r3 installed both dependency sets but failed their combined
dependency check. A separate r4 proposal now isolates the model and game
environments; see [split environment repair](phase4_v6_split_environment_repair.md)
for local evidence and remaining pilot integration work. No r4 run was launched.

Follow-up: the repaired bootstrap passed on Kaggle in r2, which then failed
because the probe confused Torch's package version with its runtime build
version. That mismatch is now verified and corrected in the separate r3 review
snapshot; see [Torch version repair](phase4_v6_torch_version_repair.md).
No r3 GPU run has been launched.

The replacement bootstrap passed a real, offline Linux/Python 3.12 installation
using the frozen environment wheels. This is a head start for the next target
probe, not a new GPU run or a target-installation pass.

## Change

`certification/phase4_v6/clean_environment.py` creates a fresh venv with
`--without-pip`, verifies it contains no installed distributions or pip, and uses
the host's pip with `--python <venv-python>` to install into that interpreter.
This avoids the failing implicit `ensurepip` step while keeping dependencies
isolated from host site-packages. Pip documents this workflow explicitly:
[Managing a different Python interpreter](https://pip.pypa.io/en/stable/topics/python-option/).

Each command has a named stage and retained stderr/stdout, with stage start/end
times, success/failure, and error details. The existing bounded process/log
runner is reused. Expired stages cannot launch, failed stages cannot be retried
in place, and existing environments cannot be silently reused. Install commands
require exact pins, use only binary distributions and `--no-index`, and retain
pip's installation report. No pip upgrade or dependency download is performed.

This removes the failed dependency on ensurepip; it does not establish why that
subprocess failed in Kaggle. Version 1's source, notebook, lock and failure
evidence remain unchanged. The new helper is not wired into that consumed
notebook or into an approved launch path.

## Local evidence

Runner: `scripts/validate_phase4_bootstrap_repair.py`.
Host: WSL Linux x86_64, Python 3.12, system pip 24.0.

- All 31 frozen environment wheels matched their registered sizes and SHA-256s.
- The new venv began with no installed packages, no pip, and user site disabled.
- Frozen toolkit/engine dependencies installed offline and `pip check` passed.
- Exact six direct versions and actual `arc_agi` / `arcengine` imports passed.
- Every installed distribution was located inside the new venv.
- All eight stages passed in approximately 18.3 seconds through the final check.
- Temporary scratch and the test venv were removed afterward.
- Six focused tests passed, including real failing-subprocess diagnostic capture,
  expired-deadline rejection, and the original installation-proposal tests.

Evidence: `reports/runs/phase4-v6-bootstrap-repair-local-20260917/`, including
`stages.log`, `stages.json`, `install_frozen_environment.json`, and `summary.json`.
The compact result is also retained as `reports/phase4_v6_bootstrap_repair_local.json`.

To repeat locally, choose a **new** output directory:

```sh
.venv/bin/python scripts/validate_phase4_bootstrap_repair.py \
  --host-python /usr/bin/python3 \
  --output reports/runs/phase4-v6-bootstrap-repair-local-NEW
```

The remaining work is to integrate this helper into a new installation-probe
revision, retain host-pip/version and stage evidence on target, and review that
artifact before seeking any new session authority. Model-service wheels and CUDA
were not installed or tested locally. Existing compute reservations and launch
claims are unchanged; no new attempt is authorized by this repair.
