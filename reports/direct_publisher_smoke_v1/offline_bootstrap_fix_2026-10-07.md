# Offline virtual-environment bootstrap

The latest attempt reached the controller on CPython 3.12.13 and verified all 174 mounted wheels. It then failed during `python -m venv`: the child `ensurepip --upgrade --default-pip` exited 1. The retained log does not reveal the nested ensurepip error, so its exact cause remains unconfirmed. The model server never started and no model requests were issued. Owned installation process groups and temporary directories were removed, and the final lifecycle deadline check passed. GPU cleanup was not measured because installation failed before the GPU verification stage.

## Change

Create the fresh environment with `--without-pip`. Use the pinned host interpreter's pip with `--python <venv>/bin/python` for the existing hash-pinned offline installation and subsequent `pip check`. Import and exact-version checks continue to execute through the environment's own interpreter with `-I`. The host environment is not an installation target and its installed libraries are not inherited by the fresh environment.

This requires pip 22.3 or newer in the host interpreter. The [official pip documentation](https://pip.pypa.io/en/stable/topics/python-option/) describes this method for environments without pip. If host pip is missing or lacks `--python`, installation fails without downloading a bootstrap tool or changing the host. Host pip availability in the pinned Kaggle image still needs a CPU-only check before treating this as remotely validated.

The trusted 174-wheel manifest and hash-pinned requirements remain unchanged. Process ownership, descendant termination/reaping, shared installation deadline and final lifecycle deadline checks still cover all commands. No automatic fallback or retry is added.

When a live attempt fails before GPU verification, its cleanup message now says that the GPU verification stage was not reached. It no longer incorrectly describes that live attempt as a CPU rehearsal. Overall cleanup of owned processes/files does not establish measured GPU cleanup.

## Validation and review

Three new regressions use only CPU fixtures: a real hash-pinned pip install/import into a venv with ensurepip unavailable; rejection of a changed wheel hash; and accurate reporting of a live installation failure before GPU verification. All three fail on `fe63ce1619b4e79be0a5db72beaf6151b60d48ab` with three assertion failures and no test errors. See [baseline record](bootstrap_baseline_fe63ce1.json) and [log](bootstrap_baseline_fe63ce1.log).

The focused checks include these regressions and the existing startup-ownership, descendant, timeout and lifecycle tests. See [CPU checks](bootstrap_cpu_checks.json). The rebuilt [review r5](../../notebooks/direct-publisher-smoke-v1-review-r5/review-source-lock.json) has GPU disabled, reproduces byte-for-byte and refuses at the live gate in the [review check](../direct_publisher_smoke_review_check_r5.json). Prior public snapshots and private spent attempts remain unchanged.

All 68 focused tests pass on Linux CPython 3.12.3 with host pip 24.0; no tests are skipped. All 12 [CPU fixture rehearsals](bootstrap_rehearsals.json) behave as expected, including the complete nominal flow, hash/version refusal, server failures, cancellation and forced termination of descendants. Earlier rehearsal records remain unchanged. These results validate control code and fixture installation, not the real GPU runtime or the availability of host pip in Kaggle's pinned image.

This change is a new source-review candidate. Earlier private source approval and compute reservations do not authorize its changed hashes. No new provider submission or GPU attempt was performed while preparing this fix.
