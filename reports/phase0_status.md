# Plan 8 Phase 0 status

Date: 2026-09-07

Phase 0 is complete and Plan 8 is active. Local, manual-account, packaging,
mounted-runtime, scorecard-finalization, output, and scored Kaggle rerun gates
pass as recorded in `config/activation_record.json`.

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
- Added exact installed-runtime source hashing, Requests-compatible wire-byte
  serialization, a production reasoning safety margin, and fail-closed mounted
  startup validation before any environment action.
- Added evaluator-only typed normalized/official RHAE units and pinned scorer
  fixtures for initial reset, later reset, and visible no-op counters.
- Added explicit client-session cleanup, policy-exception containment, bounded
  queue age, and hung-worker isolation that preserves the finalization reserve.

Evidence:

- Project tests: 36 passing.
- Synthetic 110-client orchestration: one scorecard, one bootstrap per client,
  all clients accounted; hung workers do not consume the close reserve.
- Three independent local traces: 12 actions each with identical action trace;
  SHA-256 `1dfe912b5f012fab00e2d289a196e563fc608f1e83f154d064e14858e8f00171`.
- Three independent real local `ls20` development runs: 12 acknowledged actions
  each, no invalid action or uncaught exception, acknowledged close.
- Production transport against the pinned toolkit's local competition-mode REST
  gateway: passing, including scorecard, affinity, bootstrap, action, reset, and
  close behavior.
- Exact local dependency versions and five source hashes: passing.
- Kaggle kernel v1 failed safely before agent start because the official offline
  wheel bundle provides `arc-agi==0.9.8`, not the initially requested 0.9.9.
  The captured Kaggle profile pins and hashes 0.9.8 and its mounted dependencies;
  the only 0.9.8/0.9.9 framework-source difference is error-response logging.
- Kaggle kernel v2 completed successfully using the captured mounted profile.
  Its retained-output inventory contains only the expected 890-byte
  `submission.parquet`. No scored competition submission was spent.
- Installed scorer reset/no-op counter fixture and explicit score units: passing.
- Notebook build and output-policy validation: passing.
- Full gate command: `make validate-phase0` prints `LOCAL_PHASE0_PASSED`.

External activation evidence:

- Kaggle competition submission `56076246` completed successfully on 2026-09-07
  with public OfficialRHAEPercent 0.08. This is an E0 pipeline baseline, not a
  competitiveness claim.
- The notebook fails before acceptance when its runtime/source audit or
  scorecard finalization is not acknowledged. The completed scored submission
  therefore closes those fail-closed mounted gates.
- Mounted scorer source matches the locally executable initial-reset,
  later-reset, and visible-no-op fixture; the live submission was accepted.
- Kaggle accepted the generated `submission.parquet` contract.
- The account owner confirmed accepted rules, verified identity, solo team
  `dai_chongwei06` (canonical Kaggle owner `daichongwei06`), a signed-in
  allowance of two submissions per day, and the configured kernel ID on
  2026-09-07. Kaggle API competition access passes.
- The project license is Apache-2.0. Dependency provenance was corrected to
  record the ARC agent framework, `arc-agi`, and `arcengine` as MIT-licensed.

There are no remaining Phase 0 activation blockers. Later model-performance,
target-hardware profiling, and treatment gates begin in Phase 0F/M0 and Phase 1.
