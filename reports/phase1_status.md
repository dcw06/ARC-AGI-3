# Plan 8 Phase 1 status

Date: 2026-09-12

Status: local implementation, parameter closure, the actual mixed-prompt
target-RTX resource gate, the four-cell execution, and the dated control
freeze/availability decision passed. A post-run dependence audit correctly
classifies version 5 as descriptive shared-resource evidence, not causal
factorial inference. Both frozen published bundles closed as
production-ineligible rather than remaining ambiguously pending. Phase 1 exit
is complete: the counterbalanced whole-run execution and all downloaded log
hashes validated. The unavailable published-control reproduction and same-model
normalization dispositions are closed fail-safe. E1S-R remains the runnable
`Provisional primary` with E0 fallback because all block-level results tied at
zero. No scored submission was spent.

The first complete mixed-prompt target run (private Kaggle kernel version 2)
retained valid evidence but failed closed: E1S-F produced 0/8 strict responses
at the 128-token ceiling, and the original nine-request E1C-F worst-case
projection exceeded the operational target by 323 seconds. Before any game-cell
run, the common prompt was amended to require action-only JSON under 64 tokens,
the workspace cap was reduced from eight to seven operations, and resource
acceptance was changed from a single cross-cell worst case to the frozen
cell-specific call ceilings. All future cells restart on this amended contract.

Private Kaggle kernel version 3 then passed the amended target-RTX gate. Every
cell produced 8/8 strict-valid responses. The headroom-adjusted full-run totals
were `7702.21` seconds (E1S-R), `9635.58` (E1S-F), `20847.83` (E1C-R), and
`24788.63` (E1C-F), all below `27540`. The slowest full-workload cell had
`C_admit=78697` for `70400` requests. Cold load was `236.18` seconds,
cancellation recovery `0.187` seconds, peak VRAM `77538000896` bytes, and peak
RAM `14612037632` bytes. The frozen evidence is
`reports/e1_profiles/q3vl30-mixed-v3.json` with SHA-256
`e83f750635fc862bba8138229c97bcd8c5dd7ae56e4a99dc31a48ce9acf157a7`.

## Completed locally

- Bound every E1 cell to `M0-Q3VL-30B-A3B-FP8`, exact revision
  `d9748a51ae66354c4dad665aab2c71f26cf2c8cd`, `vllm==0.19.0`, and
  `instruct_non_thinking`.
- Implemented strict stateless E1S-R/E1S-F and safe-operation E1C-R/E1C-F.
  Final responses contain exactly one legal action; no parser repair is allowed.
- Integrated all model requests through the bounded minimum fair queue. Model
  requests, prompt/completion tokens, inference elapsed time, workspace calls,
  and workspace elapsed time are charged to per-client counters.
- Implemented the non-Turing-complete, spawn-isolated workspace with eight
  registered operations, immutable inputs, bounded time, additional address
  space, output, file-descriptor, file-write, environment, and invocation
  authority.
- Added JSON-native F payloads while preserving the R/F boundary and excluding
  game ID and session GUID from model-visible context.
- Froze all 15 development game/seed pairs and five balanced cross-validation
  folds. H1 and H2 remain unused.
- Froze distinct selection-procedure and final-fixed-candidate estimands, an
  exact one-sided paired sign-permutation rule, and `Provisional primary` for
  fewer than five nonzero pairs or otherwise insufficient evidence.
- Replaced the provisional M0-shape projection with the measured mixed-prompt
  target-RTX profile. Each cell uses its frozen request ceiling, and both E1C
  full-workload cells admit all `70400` requests with headroom.
- The complete local suite has 102 passing tests. `make validate-phase1` validates
  the implementation, parameter closure, canonical whole-run evidence, and
  final exit gate.
- Added the private, unscored `notebooks/e1-q3vl30` RTX profile bundle. It runs
  an E1S-R canary first, profiles all four frozen mixed request shapes from one
  model load, checks strict protocol output and cancellation recovery, samples
  RAM/VRAM, verifies the frozen model tree, and recomputes `C_admit`.
- Added the private, unscored `notebooks/e1-four-cell` causal experiment bundle.
  It preflights the exact 15 public games before dependency installation/model
  load, seeds both environment and model requests per frozen pair, runs every
  cell through the same eight-worker `minimum_fair_v1` queue, retains charged
  model/tool counters, and recomputes the three registered paired factorial
  contrasts plus cross-validated selection from the exact score matrix.
  Kaggle version 1 failed before model load because `evaluation/metrics.py` was
  absent from the embedded bundle; its log is retained under
  `reports/runs/e1-four-cell/v1`. An isolated-bundle import regression now
  covers that seam. Version 2 completed its environment loops but is invalid
  causal evidence: all 4216 inference attempts received HTTP 404 at the
  accidentally doubled `/v1/v1/chat/completions` path, so every action came
  from fallback. Its JSON and logs are retained under
  `reports/runs/e1-four-cell/v2`. The client now normalizes the API prefix,
  completed-inference counts must equal request counts, and a real completion
  canary runs before the first scorecard.
- Version 3 passed its real completion canary and ran every environment loop,
  but failed closed after growing prompt context caused incomplete inference
  transport. Only 87/1061 E1S-R, 46/1061 E1S-F, 129/1097 E1C-R, and 48/1058
  E1C-F requests completed; every fixed-set mean was zero, so no causal result
  was accepted. Its evidence is retained under `reports/runs/e1-four-cell/v3`
  with SHA-256
  `f6df1212c492d84efba845681a2a99041cba65334325b3e6f43c6d968feb1b7c`.
- This observed context-continuity failure activated the predeclared visible
  compaction condition. Feature manifest E1.v3 now retains one recent
  transition in every cell and exposes total, retained, and omitted counts plus
  a stable rolling full-history hash. Model, engine, reasoning, games, seeds, folds,
  queue, action surface, and both factorial assignments remain unchanged. All
  cells restart together. Kaggle kernel version 4 began before the lifetime
  transition-count audit completed and is predeclared superseded; it cannot be
  accepted against E1.v3 even if it completes.
- Kaggle kernel version 5 completed the corrected feature/context contract. All 5671
  model requests completed, with zero transport failures, queue failures, or
  parser repairs; all four scorecards finalized with acknowledgment. Every
  cell mean was 0.0. A subsequent dependence audit found that the eight games
  active within a cell shared one inference queue, making the comparison a
  `shared_resource_whole_run` experiment. Version 5 has one fixed-order block,
  so its game-level contrast calculations are diagnostic only and it supports
  no causal factorial claim. The frozen tie-break names E1S-R as the fixed E1
  diagnostic candidate with `Provisional primary` status only. The run took 11,346.80
  seconds, below the 27,540-second envelope. Canonical evidence is
  `reports/e1_results/e1-causal-four-cell-v5.json`, SHA-256
  `f186192705e061734bf7bb93dd64f2afbe2f5538eaf828a04a123fca9515eb9d`;
  the hierarchical result is in `reports/e1_causal_four_cell.md`.
- Frozen a corrective two-block whole-run design in
  `config/e1_whole_run_protocol.yaml`. Treatment order is exactly reversed
  across the blocks, the paired complete-workload block is both randomization
  and uncertainty unit, and every treatment starts a fresh model process,
  queue, Arcade/session set, and policy state. The regenerated private notebook
  at `notebooks/e1-four-cell/profile.ipynb` is projected at 23,330.02 seconds,
  leaving 4,209.98 seconds inside the 27,540-second envelope.
- The corrective whole-run completed both reverse-order blocks and eight fresh
  treatment runtimes in 23,344.80 seconds. Every scorecard finalization was
  acknowledged; inference requests equaled completions, with zero transport
  failures, queue failures, or parser repairs. Every cell mean and all three
  factorial contrasts were 0.0, so there were zero nonzero blocks and no
  estimable effect. The frozen sparse rule retains E1S-R as `Provisional
  primary`. Canonical evidence is
  `reports/e1_results/e1-whole-run-four-cell-v1.json`, SHA-256
  `7ca485b51f38955ca73b148e3396426f09ea6ade911c170a2dc203f6ef5bb245`.

## Frozen control and runner decision

The September 9 inventory found a newer visible Duck candidate than the earlier
Qwen3.8-27B v12 snapshot: `wuliao0/duck-qwen3-8-anim-base`, using a Qwen3.8
Flash Next NVFP4 artifact. The notebook snapshot is recorded by SHA-256 in the
control registry. Its observed published score is inventory metadata only and
is not substituted for a project reproduction.

The post-cutoff public inventory audit ran at `2026-09-11T15:54:00Z`. It keeps
the September 9 notebook bytes and excludes later revisions under the frozen
registry's prospective-only rule. The current published workspace control is
therefore frozen as `duck-qwen3.8-flash-next-nvfp4-anim`, notebook SHA-256
`72d6f35147b5d1c422a2959cc378727df6b688c4f478c2aa9ad3580b4a247122`.

Its faithful runner is unavailable. The captured Python tool uses a child
CPython process, `-I -S`, a temporary working directory, a reduced environment,
resource limits, and import/builtin allowlists, but provides no enforceable
filesystem, credential, native-code, or syscall boundary and has no target-RTX
adversarial escape pass. Section 8.12 explicitly says those partial controls
are insufficient. Production therefore never executes its model-authored
Python. `E1C-F` is recorded separately as an adapted safe-operation substitute;
it is not described as a faithful or normalized Duck reproduction.

The strongest frozen published structured reference is `reki-milestone1`,
notebook SHA-256
`3cb34c4a04140535081afa611159fc303ccd29481bd34a62e3bc6aa44bff0618`.
Its notebook and exact Gemma 4 model are Apache-2.0, but its attached public
`ruichardliu/vllm-0230-offline` distribution reports an `unknown` license.
Forge is not a fallback because its required wheelhouse returned HTTP 403 in
the audit. Under the registry's fail-closed rule, neither captured published
structured bundle is currently production-eligible. The project-owned,
Apache-2.0 `E1S-R` implementation is the eligible structured fallback and is
explicitly not called a Reki/Forge reproduction.

The machine-readable decisions and all prompt, harness, model, runtime, and
metadata hashes are in `config/control_registry.yaml`; the evidence narrative
is in `reports/phase1_control_freeze.md`.

## Phase 1 exit gate

Passed. Per-game values remain diagnostic; the paired complete-workload run
block is the validated randomization and uncertainty unit.

The dated inventory and license/availability decisions are complete. Faithful
published reproduction is closed as unavailable because there is no eligible
published runner, and same-model normalization is not justified without one.
Deliverable 6 is complete: the hierarchical report, model and
runtime table, runtime-use offline bundle, and runnable E1S-R `Provisional
primary` with E0 fallback are frozen in
`reports/phase1_hierarchical_decision.md` and
`config/operational_primary.yaml`. E1 version 5 remains a descriptive record;
the counterbalanced block-valid experiment is complete, but its all-zero sparse
evidence supports only a provisional primary and no factorial acceptance claim.

## Primary sources

- <https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview>
- <https://www.kaggle.com/code/wuliao0/duck-qwen3-8-anim-base>
- <https://arcprize.org/blog/arc-prize-2026-milestone-1>
- <https://github.com/Tufalabs/duck-harness>
- <https://www.kaggle.com/code/ruichardliu/milestone1-2nd-solution>
- <https://www.kaggle.com/code/mbmmurad/arc-agi-3-lb-0-86-3rd-place-candidate-milestone>
