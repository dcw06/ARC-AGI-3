# Repaired installation check: separate authorization

The user requested: "Can you start a new GPU run" after the installation
bootstrap repair checkpoint d98a9d2. This authorizes one new installation-only
attempt with the same previously accepted limits: 1800 GPU-seconds reserved,
900-second internal deadline, no automatic retries, private offline RTX PRO
6000 notebook. Model loading, gameplay, model pilot and scored submissions
remain outside this attempt. No old reservation or launch claim is reused.

Revision r2 integrates the locally validated pip-free venv bootstrap, installs
the frozen model-service and environment wheels, checks exact runtime versions,
CUDA and vLLM extension imports, and verifies cleanup. Host pip and named stage
diagnostics are retained. Nine focused tests passed under WSL Python 3.12.
The original r1 notebook and source remain unchanged. Kaggle preflight passed;
the previous attempt is ERROR and account GPU reserved time is zero.

The review-source-lock binds the notebook, repair sources, frozen dependency,
launcher and its credential helper. This is a new installation check, not
evidence that the target installation has already passed. Provider timeout is
requested at 1800 seconds; independent enforcement is not verified. Retain
the full reservation until attempt-specific billing is available.
