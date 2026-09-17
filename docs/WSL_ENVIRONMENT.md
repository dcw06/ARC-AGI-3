# Local WSL environment

September 17 update: the local pilot test issue is addressed, and all **312 tests
pass**. See [the resolution report](../reports/windows_pilot_resolution.md).
The v6 local functional smoke budget is now explicitly 300 seconds; the original
60-second historical verdict is retained separately. GPU criteria are unchanged.
The setup results below describe the earlier installation checkpoint.

The development runtime is Ubuntu 24.04 / WSL2, Linux x86_64, Python 3.12.
The nine direct dependencies match `config/dependency_manifest.lock`; the
installed development environment contains 56 packages. System tooling includes
Git, Make, uv, pip, venv, build tools, unzip and rsync.

## Working directories

- Original Windows project: `C:\Users\jjzzw\Desktop\AGI`.
- Native Linux working copy: `/home/jingjing/AGI`.
- Development environment: `/home/jingjing/.local/share/agi/dev-env`.
- Isolated frozen environment-wheelhouse install:
  `/home/jingjing/.local/share/agi/offline-env`.

Both working copies' `.venv` links use the native Linux development environment.
Git history was restored from the included bundle at `fa5f524`; no remote was
added. The native copy ignores transferred executable-bit differences.

Use the native working copy for timing-sensitive tests. These are separate
working copies: edits do not synchronize automatically. Open the Linux copy
from Windows at `\\wsl.localhost\Ubuntu\home\jingjing\AGI`, or through an editor's
WSL integration. Avoid editing the same files in both copies independently.

From PowerShell:

```powershell
wsl -d Ubuntu --cd /home/jingjing/AGI
```

Then in Ubuntu:

```bash
source .venv/bin/activate
make test
```

To run Python against the original Windows working copy from PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/wsl-python.ps1 --version
```

The execution-policy argument applies only to that launcher process; no global
PowerShell policy was changed. Native Windows Python is not used by this project.

## Reinstall development dependencies

In the chosen working copy, run `bash scripts/setup_wsl.sh`. It reads the existing
dependency manifest, installs into `.venv`, checks dependencies, preserves the
transferred vendor framework and creates `.env` from the example only if absent.
Do not run the legacy `make setup` on the transferred vendor directory: that
target expects a Git clone, whereas this transfer contains the framework files.

Blank credential placeholders are present in `.env`; no API credentials were
provided or configured. Cached development environments and local tests need no
account authentication.

## Target runtime remains separate

The frozen 31-wheel game-engine bundle installs offline on Linux/Python 3.12 and
passes the `kaggle_2026_09_07` runtime audit, including source hashes and imports.
This does not verify the vLLM/model-service install. Its frozen Kaggle wheelhouse
and approximately 64.5 GB model artifact were not included in the transfer.
WSL currently exposes no NVIDIA runtime and has approximately 8 GiB RAM.

The complete model-service offline installation and target GPU review therefore
remain open. Existing GPU execution gates, reservations and historical evidence
are unchanged. No GPU job or submission was launched during setup.

## Validation records

All 546 transfer-inventory payloads matched their original sizes and SHA-256
hashes. Development and frozen-environment runtime audits passed. Detailed setup
and test results are recorded in `reports/windows_environment_setup.json`.

The full suite passed 304 of 305 tests. The 110-client pilot exceeded its frozen
deadline, including when rerun alone in the native Linux copy. Cleanup succeeded;
the retained failure is under `reports/runs/wsl-setup-local-pilot-20260917` in the
Linux copy. The comparison CLI also raises `KeyError: worker` after that failed
run. These are unresolved validation issues, not a passing lifecycle result.
No historical source or deadline was changed to make the checks pass.
