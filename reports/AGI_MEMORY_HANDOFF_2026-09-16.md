# AGI project — Windows handoff

Prepared September 16, 2026 (Asia/Shanghai).
This is a project/context handoff, not a full chat export or automatic transfer
of an assistant's private memory. No credentials are included.

## Start the next conversation with this

> Read this handoff and the repository's certification/phase4_v6/README.md,
> reports/phase4_v6_integrated_result.json and reports/phase4_status.md before
> changing anything. Continue the v6 development-pilot work. Preserve historical
> evidence and the dirty worktree. Do not launch a GPU run, authorize compute,
> access holdouts, or make a scored submission. First inspect the current code
> and identify the remaining offline-install and target-review blockers.

## Project and transfer warning

- Original project: `/Users/dcw06/Desktop/AGI`.
- Git HEAD at handoff: `4371fea` — Record V2 GPU prescreen pass and retain pending
  billing reservation. Earlier: `3a10d81` approval/reservation, `7f85a80` checkpoint.
- **Most subsequent lifecycle work is uncommitted or untracked. Cloning/pulling
  Git alone will NOT recover it.** Preserve the current working tree.
- Modified tracked files include README.md, config/phase4_compute_ledger.json and
  reports/phase4_status.md. New certification directories, tests, notebooks,
  reports and evidence ZIPs are also important.
- `docs/Preliminary_So_Reasoning_Agent_Proposal.md` is an unrelated untracked user
  file; preserve it. Do not overwrite or delete unrelated changes.
- The companion v6 evidence ZIP contains an exact review source snapshot, tests,
  notebook and retained local run. It is **not the entire project**, model weights,
  full development environment package, or model-service wheelhouse.
- Transfer the project working tree separately if continuing full development.
  Do not copy macOS `.venv` for execution on Windows/Linux: rebuild the environment.
  Keep `.kaggle`, access tokens, `.env` and other credentials out of shared bundles;
  authenticate separately. Do not treat `.lck` files as evidence.

## Windows execution constraints

The new runner uses POSIX process groups, `fcntl` file locks, `ps`, signals and
`/dev/stdout`. Native Windows Python is not a drop-in runtime. Use a compatible
Linux environment (for example WSL2) for these paths, and inspect dependencies
before running. WSL availability does not prove CUDA or target compatibility.
Repository paths are now relative in the portable archive, but old reports may
still contain absolute Mac paths. Do not rewrite archived evidence to fix paths.

## Scientific/phase status

- Phase 2–3 archived decisions must remain verifiable. E1S-R is provisionally
  retained; the demonstrated ineffective action selection was not sufficient to
  identify a memory/retrieval/animation/queueing treatment. Preserve
  `unsupported_other`, the no-candidate disposition and H1. No new treatment or
  holdout use has been authorized by the Phase 4 work.
- Phase 4 is **not complete**. Minimum fair FIFO scheduler remains selected.
  Advanced scheduling is deferred; no registered alternative has been compared.
- Current development load = 110 clients repeating 15 development games,
  independent scorecards, fixed seeds, maximum 80 actions/client. It is NOT the
  production one-scorecard/110-distinct-game lifecycle.
- Real-trajectory `C_nominal` and `C_admit` remain null. Never substitute fixture
  projections or scripted CPU timings for measured model-backed capacity.

## Completed GPU fixture prescreen and accounting

- Notebook: `daichongwei06/arc3-phase4-fixture-prescreen-v2`, provider version 1.
  Link: https://www.kaggle.com/code/daichongwei06/arc3-phase4-fixture-prescreen-v2
- Exactly one submitted private, unscored run was recorded. It passed its
  fixture-only evaluator: 8,800 requests, internal timer 1,074.16 seconds.
- Owner screenshot shows provider duration 1,083.8 seconds; another shows private
  Version 1 of 1, rounded 18m 4s, RTX PRO 6000. These are not exact charged GPU time.
- Complete interactive/failed-session inventory, exact billed time and provider
  timestamps remain unresolved. Owner statement is **“no additional sessions
  recalled”**, not verified session history.
- All 28,800 seconds of the prescreen reservation remain retained, zero release
  or transfer. That attempt is consumed. No retry or reuse is authorized.
- Historical fixture projections: C_nominal=419210, C_admit=252717. Fixture-only.

## Lifecycle revision history

- v1: frozen E1S-R development preparation, workload, seeds, limits and policy
  bindings. Preserve it; later work does not silently rewrite the freeze.
- v2: packaged 15 exact environments and 31 environment wheels. Local 110-client
  integration failed closed with 35 quarantines. Keep that failed result.
- v3: corrected lifecycle handling to stop after acknowledged GAME_OVER. The
  engine returns empty frames for a later non-reset action after terminal loss;
  the old loop only stopped on WIN. No reset, parser relaxation, fabricated frame
  or policy change. Local run passed: 75 action caps, 35 terminal losses, 7,722
  actions, 110 scorecard closes, zero quarantines. This was scripted, not model-backed.
- v4: review-only shared-model integration notebook, preserved unchanged.
- v5: prospective capacity design/calculator. Eight equal global wall-time windows;
  nominal completed requests/wall time; empirical guard = 0.8 × minimum window
  rate. Separate 20% service-budget headroom: 19,800 -> 15,840 seconds. This is an
  empirical margin, not a confidence interval or deterministic guarantee.
- v6: unified development pilot described below. Old component-status sections in
  its README/status report are historical; read the newest handoff first.

## Current v6 implementation

Key code under `certification/phase4_v6/`:

- `pilot.py`: outer owner, gated worker/monitor launch, readiness checks, bounded
  logs, cancellation/deadline handling, cleanup, evidence assembly/evaluation.
- `pilot_child.py`: real development environment worker and monitor child roles.
- `worker.py`, `measurement.py`: unchanged-policy inference wrapper, unique
  request IDs and submission/start/completion/return timestamps, client evidence.
- `evidence.py`: cross-process-locked shared 64 MiB store. Component budgets:
  control 1, monitor 16, worker 32, evaluation 8, logs 7 MiB. Temporary replacement
  peaks count; bounded failure receipts reserved; no truncation to fake success.
- `service.py`, `live_probes.py`: frozen shared model/probe adapters. Live authority
  is explicitly closed; do not bypass it or borrow v4/prescreen authority.
- `evaluate.py`: existing lifecycle/model validation plus timestamps, telemetry,
  scope and capacity checks. Injected resource evidence cannot certify a target run.
- `install.py`, `build_notebook.py`: bounded offline installation and review
  packaging. Engine/pilot imports must occur AFTER dependency installation.
- `run_local_pilot.py`, `package_local.py`: retained CPU pilot, comparison with
  archived v3 behavior, portable review/evidence package.

Worker release requires a retained initial GPU-shaped sample and nonce/PID/mode-
bound readiness. Local samples are explicitly injected. Monitoring continues
through worker/model-group termination; live mode additionally requires empty GPU
process inventory. Installation, startup and failures count toward elapsed time.

Frozen/proposed target envelope: 27,540-second lifecycle, 600-second finalization
reserve, 900-second install and model startup limits, 86 GiB VRAM, 128 GiB RAM,
4 GiB scratch, 64 MiB retained output; FIFO queue 110/eight model workers; E1S-R
request seed 0, max completion 128, context 65,536. Check protocol.json for details.

## Latest measured local result

`reports/phase4_v6_integrated_result.json` records:

- Retained run: `reports/runs/phase4-v6-integrated-local-20260916`.
- 110 actual development clients, 7,722 requests, 23.35467175 seconds, cleanup verified.
- Every client's request digests and action/state-hash sequences match the archived
  v3 scripted run. This is behavior invariance, not a paired performance experiment.
- Model responses scripted; GPU telemetry injected. No GPU/model inference.
- 17 process/integration tests passed, including monitor failure, worker failure,
  evidence exhaustion and cancellation. Related suite: 77 tests passed. Latest
  package suite: 2 tests passed. These were separate overlapping invocations;
  do not describe their sum as a single full-suite run.
- Archive hashes verified; local evaluation passed after fresh extraction using
  the archived sources. Historical v3 snapshot verification still passes.

## Current notebook and portable archive

Use **review-r2**, not the first v6 review artifact:

- `notebooks/phase4-lifecycle-v6-review-r2/profile.ipynb`
- `notebooks/phase4-lifecycle-v6-review-r2/review-source-lock.json`
- `evidence/phase4-v6-integrated-local-review-r2.zip`
- ZIP SHA-256:
  `39e2bf9cd66c0edcb9335827d07453dabedff6dcdc475f4aa556cbb58b8f70d0`

ZIP layout: `source/`, `notebook/`, `run/`, `inventory.json` with per-file sizes/hashes.
The initial v6 review notebook/archive is superseded and preserved: review caught
an import that could require engine dependencies before installation; r2 fixes
the order and has a regression test. Do not upload the superseded artifact.
The r2 notebook is private, GPU-disabled, internet-disabled and fails the
standard-library bootstrap gate before installation. Its source/protocol lock is
a REVIEW snapshot, not spending authority or a fully approved target freeze.

## Next work and blockers — important

1. Verify a **clean Linux x86_64/Python-3.12 offline installation/import** using
   both frozen environment and model-service wheelhouses. The Mac is Darwin ARM64
   and has no Docker executable; this was NOT verified there. Existing checksum
   checks and environment dependency-resolution dry run are not an install test.
2. The model wheelhouse is external Kaggle dataset
   `driessmit1/arc3-vllm-h100-wheelhouse-v3`. Packaged installer verifies both
   frozen manifest digests and its payload inventory. Model is Qwen3-VL-30B-A3B-
   Instruct-FP8; use the frozen operational binding, not a substitute.
3. Independently review the integrated target path: real telemetry timing,
   process topology, CUDA cleanup, evidence/log fit, exception paths and final
   timing accounting. Passing local tests is not proof of complete enforcement.
4. Only then approve a complete execution release/lock and separately authorize
   and reserve ONE proposed 28,800-second private, unscored pilot. Current v6
   authorized seconds = ZERO. The pilot uses hard workload/resource/deadline caps;
   it does not need an estimate from its own future results to permit launch.
5. After an authorized model-backed run, evaluate retained results, reconcile
   provider usage including failures, and review/freeze measured capacity with
   clearly stated scope. Production 110-distinct/one-scorecard gate remains separate.

No commit, push, notebook upload, new compute authority, holdout access or scored
submission was performed in the latest integration work. Do not infer any of those
permissions from this handoff.

## Useful local commands (Linux-compatible environment, dependencies installed)

```sh
python -m unittest tests.test_phase4_pilot_package_v6 -q
python -m unittest tests.test_phase4_pilot_v6 -q
python -m certification.phase4_v6.run_local_pilot --output /path/to/NEW/output
python -c 'from certification.phase4_v3.freeze import verify_snapshot; verify_snapshot()'
```

Process tests need process-table access. Local pilot needs the exact development
environment package, commonly at `reports/runs/phase4-v2-assets/environment_files`.
Restore it from `evidence/phase4-v2-development-offline.zip` using its manifest;
the v6 review ZIP alone does not contain environment engines or dependency wheels.
Notebook builders and packagers use exclusive output creation. Do not overwrite
historical artifacts to rerun them. Create a new review revision if code changes.
