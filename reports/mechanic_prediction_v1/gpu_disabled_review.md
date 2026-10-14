# GPU-Disabled Review Package

Status: review findings 1-4 remediated on a follow-up branch; assembled for independent review; not yet independently reviewed, approved, or authorized for model/GPU execution.

## Included

- Benchmark specification and prediction protocol.
- Eight-family synthetic fixtures, separate independent keys, shortcut report, request schedule, token/byte audit, and SHA-256 manifest under `research/mechanic_prediction_v1/`.
- Builder, finite-space oracle, independent key derivation, prompt/schema, shortcuts, scorer, grounding diagnostics, replay verifier, and focused tests.
- Stage C experiment-selection and Stage D transfer proposals.
- Hypotheses and their deterministic rules are visible in both model arms; model results would test rule application/prediction, not latent hypothesis discovery.
- Review archive text contents and bindings are LF-normalized; CPU tests verify all 26 manifest entries against packaged bytes.

## Explicit Exclusions

- No model weights, model API calls, GPU runner, live game dispatch, or GPU authorization.
- No reuse of previous approvals, test receipts, or GPU authorizations.
- No exact model-token measurement until a model and tokenizer are selected and pinned.

Run `python -m research.mechanic_prediction_v1.build` and `python -m unittest tests.test_mechanic_prediction_v1 tests.test_mechanic_prediction_v1_oracle -v` from the repository root for portable CPU construction and tests. The package is eligible for independent review only; any later model schedule requires a new review receipt and separate compute authorization.