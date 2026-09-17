# Authorized installation check — September 17, 2026

## Final result: failed at clean-environment bootstrap

At 09:58:44 UTC, Kaggle reported `ERROR`. The downloaded probe result is failed:
the fresh virtual environment's `ensurepip` subprocess exited with status 1.
The parent `venv` command did not expose the subprocess's underlying error in
the retained log, so its exact cause is unresolved. The probe assumed this
bootstrap would work on the target; that assumption was not established.

Before failure, both frozen manifest digests and all **178 model-wheelhouse
payloads and 31 environment wheels** verified. Neither dependency installation
nor CUDA validation was reached. No model or development pilot was run.
Internal probe elapsed time was **32.318900168 seconds**. This is not a clean
installation pass and does not close the target installation gate.

Account GPU usage increased by **41.249 seconds** between retained observations.
This is an aggregate quota change, not verified per-attempt billing or a complete
session inventory. Exact billed time remains unknown; all **1,800 reserved
seconds** remain retained. The attempt is consumed and no retry is authorized.

Evaluation and per-file hashes: `reports/phase4_v6_install_evaluation.json`.
Original outputs remain under `reports/runs/phase4-v6-install-20260917/output`.
The next preparation step is a revised clean-environment bootstrap with explicit
stage-level diagnostics and local offline validation. Any new target attempt
requires a new reviewed artifact and separate authorization; do not modify or
resubmit version 1.

## Launch and monitoring history

At 09:28:10 UTC the provider still reported `QUEUED`. The user noted scheduling
may take several hours, so frequent local polling was stopped. No Kaggle
cancellation or resubmission was sent.

One private installation-only session was accepted by Kaggle as **version 1** at
2026-09-17 09:13:46 UTC:
[ARC3 Phase4 v6 Clean Installation Check](https://www.kaggle.com/code/daichongwei06/arc3-phase4-v6-clean-installation-check).
Kaggle derived the actual slug from the title; the returned URL is authoritative.
No dataset or competition attachment was rejected.

The requested provider timeout is 1,800 seconds. The frozen probe's internal
ceiling is 900 seconds. This is the installation check only: no model attachment,
model pilot, gameplay, holdout, or scored submission. No retry is authorized.
The attempt is consumed even if it fails or never produces sufficient evidence.

The latest status is retained in
`reports/runs/phase4-v6-install-20260917/provider-observations.jsonl`.
The one-shot claim is `config/phase4_v6_install_launch_claim.json`; the upload
response is `reports/phase4_v6_install_launch.json`. The 1,800-second reservation
remains retained pending completion and provider usage reconciliation.

Authentication used the native Linux working copy's `.kaggle/access_token`
directly, without copying or displaying its value. WSL HTTPS to Kaggle timed out;
Windows HTTPS worked. An isolated Windows API client was therefore installed in
`.cache/kaggle-windows-client` using Kaggle 2.2.4 / kagglesdk 0.1.37. This is upload
tooling only, not a change to the Linux project or target runtime.

Prelaunch account quota displayed 7.27 GPU hours used and 22.73 hours remaining
out of 30. Later observations retain exact `timedelta.total_seconds()` fields.
The SDK's raw JSON duration serialization omits whole days and mishandles
fractional seconds, so use the explicitly retained numeric seconds instead.
Account quota is not an exact per-session billing record; a delta alone does not
prove this run's charge or exclude other sessions.

The later eight-hour model pilot remains unauthorized. The old prescreen
reservation is unchanged and cannot fund this attempt.
