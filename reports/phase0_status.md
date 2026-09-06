# Plan 8 Phase 0 status

Date: 2026-09-06

Local Phase 0 implementation and validation pass. Plan 8 is not yet activated;
Plan 7 remains normative until the mounted Kaggle and manual-account checks in
`config/activation_record.json` pass.

Implemented:

- Initialized Git and verified secret/generated-output exclusions.
- Froze the IDs-only 15/5/5 public partition. H1 and H2 are conservatively
  classified as reduced-exposure guardrails because the prior listing path
  could show titles.
- Added versioned constraint, authority, experiment, runtime, output, adapter,
  holdout, dependency, source, model, context, representation, statistics, and
  success registries and journal/output schemas.
- Replaced the production upstream choose-action path with a direct lifecycle
  adapter, immutable request-local actions, bounded T0 journals, no automatic
  retries or redirects, and terminal quarantine after ambiguous dispatch.
- Added a bounded per-client loop, streaming all-game orchestrator, deterministic
  legal fallback, bounded fair queue, and independent deadline supervisor.
- Added an offline multi-file Kaggle notebook build using `/tmp` scratch and an
  exact handled-exit retained-output allowlist of `submission.parquet`.

Evidence:

- Project tests: passing.
- Synthetic 110-client orchestration: one scorecard, one bootstrap per client,
  all clients accounted.
- Three independent local traces: 12 actions each with identical action trace;
  SHA-256 `1dfe912b5f012fab00e2d289a196e563fc608f1e83f154d064e14858e8f00171`.
- Real local `ls20` adapter smoke: one bootstrap, three acknowledged actions,
  acknowledged close.
- Notebook build and output-policy validation: passing.

External activation blockers:

- Capture exact mounted Kaggle client/framework hashes and run the gateway
  transport-equivalence smoke.
- Fixture-test mounted initial RESET, later RESET, and visible-no-op scorer
  semantics.
- Confirm the generated `submission.parquet` and retained-output contract in a
  Kaggle competition rerun.
- Accept rules and confirm identity, team, kernel ID, and current submission
  allowance in the Kaggle account.
