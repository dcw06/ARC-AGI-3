# Split model/game environment repair

The r4 installation proposal uses separate fresh virtual environments while
preserving the frozen wheelhouses and game dependency pins. No dependency lock
was silently relaxed, and no GPU attempt was launched.

## Evidence for the split

`scripts/audit_phase4_split_dependencies.py` checks the 174-package model set
from r3's hash-verified pip installation report and all 31 hash-verified game
wheels. It evaluates dependency versions and markers for the recorded target
Linux x86_64 / Python 3.12.13, including referenced extras.

Both sets pass this static metadata audit separately. Combining them reproduces
the NumPy conflicts with numba and mistral-common. This is a metadata check,
not proof of imports, ABI compatibility or GPU operation.

| Environment | Direct pins relevant to the split |
| --- | --- |
| Model | vLLM 0.19.0, Torch distribution 2.10.0, Transformers 4.57.6, NumPy 2.2.6 |
| Game | arc-agi 0.9.8, arcengine 0.9.3, requests 2.33.1, NumPy 2.4.4, pydantic 2.13.2, python-dotenv 1.2.2 |

The explicit model NumPy pin records the version already selected by r3's
frozen model wheelhouse. Torch runtime 2.10.0+cu128 and CUDA build 12.8 remain
required. The game process has CUDA visibility disabled.

## R4 installation proposal

`certification/phase4_v6/target_install_probe_r4.py` creates two isolated venvs,
using the verified pip-free bootstrap. It resolves each complete dependency
set offline before installing either, retains resolution/install reports, and
runs `pip check` separately. Both environments share one absolute 900-second
deadline; time is not reset for the second environment.

Separate import checks require all distributions to reside in their own venv.
The game check rejects Torch, vLLM and Transformers visibility. The model check
rejects arc-agi/arcengine visibility, preserves the exact Torch build checks,
and performs the existing vLLM extension and CUDA tensor smoke checks.
Scratch cleanup and GPU-process inventory are recorded on failure as well as
success; a failed cleanup cannot produce a pass.

Notebook: `notebooks/phase4-v6-install-check-proposal-r4/`.
It is a local, hash-bound review snapshot with no upload, new reservation or
launch claim. Consumed r1/r2/r3 sources and notebooks remain unchanged.

## Local validation

Fourteen focused tests passed, covering resolution-before-install ordering,
distinct NumPy pins, one shared deadline, resolution failure, cleanup on error,
leftover GPU process rejection, frozen bootstrap/version regressions, and
importing the notebook's embedded r4 source in a fresh isolated interpreter.

`scripts/validate_phase4_split_game.py` performed a real offline game install
in WSL Python 3.12 alongside an empty sibling interpreter. All 31 wheel hashes
matched; game imports and dependency checks passed; the sibling remained empty;
scratch was removed. It did not install the model environment or use a GPU.

Results: `reports/phase4_split_dependency_audit.json` and
`reports/phase4_split_game_local.json`. Portable local evidence:
`evidence/phase4-split-environment-local.zip`.

## Remaining integrated-pilot work

This repairs the installation proposal, not the full model pilot. The current
`certification/phase4_v6/pilot_child.py` creates the shared model service inside
the game workload process. Its service path performs local Transformers
tokenization before HTTP inference. Merely choosing a different Python binary
for the vLLM server does not isolate that tokenizer dependency.

Before a new integrated pilot freeze, move tokenization and token-count auditing
to the model-side process and make the cross-process request/response contract
explicit. Preserve request hashes, tokenizer/server token parity, cancellation,
owned-process cleanup, monitoring and the shared deadline across that boundary.
Review the control/monitor processes' dependencies and interpreter selection as
part of that change. Alternatively, a deliberate dependency-lock revision needs
its own compatibility/comparability review; it is not implemented here.

Full target installation, actual model imports/CUDA execution and the integrated
pilot remain unverified. R4 may expose other target issues even though the known
NumPy conflict is removed structurally.
