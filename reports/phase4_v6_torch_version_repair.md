# Torch package/build version repair

The frozen wheel was downloaded without GPU compute and its full SHA-256
verified against the existing frozen SHA256SUMS manifest. Both wheelhouse
manifest hashes also matched the original lock.

| Field | Verified value |
| --- | --- |
| Wheel | `torch-2.10.0-3-cp312-cp312-manylinux_2_28_x86_64.whl` |
| Bytes | 915622781 |
| SHA-256 | `98c01b8bb5e3240426dcde1446eed6f40c778091c8544767ef1168fc663a05a6` |
| Distribution METADATA version | `2.10.0` |
| `torch/version.py` runtime version | `2.10.0+cu128` |
| `torch/version.py` CUDA build | `12.8` |

Inspection used ZIP reads and Python AST literal parsing; wheel code was not
executed. The recorded dependency metadata also contains the CUDA 12.8 runtime
packages. The historical model manifest already distinguished wheel build
`2.10.0-3` from runtime version `2.10.0+cu128`.

## New r3 probe

`certification/phase4_v6/target_install_probe_r3.py` installs `torch==2.10.0`
and checks the installed distribution version as `2.10.0`. It separately
requires `torch.__version__ == '2.10.0+cu128'` and `torch.version.cuda == '12.8'`,
plus the existing GPU availability, device, CUDA tensor and vLLM extension
checks. CUDA requirements have not been relaxed.

Before installing anything, it verifies the frozen wheelhouse and statically
checks the Torch wheel against the newly retained metadata/build evidence.
That evidence is embedded and hash-bound in the r3 notebook. The original r1
and consumed r2 sources, notebook locks, launch claims and reservations remain
unchanged.

Local review snapshot: `notebooks/phase4-v6-install-check-proposal-r3/`.
This snapshot has no execution authorization or reservation and was not
uploaded. Model loading and the model pilot remain outside its scope.

## Validation and limits

Eighteen focused tests passed in WSL Python 3.12, including separate package,
runtime and CUDA mismatch rejection, bootstrap failure/deadline tests, and
importing the notebook's embedded source in a fresh isolated Python process.

An actual offline Linux pip dry-run against the verified wheel rejected
`torch==2.10.0+cu128` and accepted `torch==2.10.0`. It used an empty isolated
venv and `--no-deps`; it establishes wheel selection only. Full dependency
resolution, installation, driver compatibility and CUDA execution remain
unverified. No new GPU session was started.

Evidence summaries:

- `reports/phase4_torch_wheel_inspection.json`
- `reports/phase4_torch_resolution_local.json`
- `evidence/phase4-torch-version-repair.zip` (manifests, extracted metadata and local logs)

The full wheel stays in the ignored local inspection directory under
`reports/runs/phase4-torch-wheel-inspection/`.

Reproduction: `scripts/inspect_phase4_torch_wheel.py` fetches and verifies the
wheel; `scripts/validate_phase4_torch_resolution.py` performs the Linux-only
dry-run using `/usr/bin/python3` as host pip. The latter requires a fresh
`reports/runs/phase4-torch-resolution-local` output directory.
