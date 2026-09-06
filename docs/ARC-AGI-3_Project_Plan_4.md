---
title: "ARC Prize 2026 — ARC-AGI-3"
subtitle: "Plan 4: RHAE-Aligned, Animation-Aware Single-Developer Implementation"
author: "Project Team"
date: "4 September 2026"
status: "Proposed — execution successor to Plan 3"
---

# Document purpose

This document supersedes `ARC-AGI-3_Project_Plan_3.md` for implementation planning. It preserves Plan 3's central architecture—deterministic code owns evidence, budgets, and safety while a local model owns uncertain interpretation—and incorporates the subsequent technical review.

`ARC-AGI-3_Project_Plan.md` remains the strategic source of truth. When an execution detail conflicts with an older execution document, Plan 4 controls. Plan 3 and Plan 2 remain design-history records.

Plan 4 makes six material changes:

1. Official Relative Human Action Efficiency (RHAE), not games completed, is the primary evaluation outcome.
2. E1 compares a minimal multimodal structured-action policy with a minimal model using a bounded Python analysis workspace.
3. Every transition receives deterministic animation analysis; full animation is shown to the model only when its expected value justifies the token cost.
4. Phase 1 must produce a measured model-and-budget decision table before Phase 2 begins.
5. Policy treatments use paired budgets, a minimum practical effect, uncertainty analysis, and accept/reject/inconclusive outcomes.
6. The 25 public environments are partitioned into 15 development, 5 H1 architecture holdout, and 5 H2 candidate holdout environments.

The plan assumes one primary implementer. No phase depends on parallel engineering unless ownership is explicitly reassigned.

# 1. Verified starting state

The repository currently has the following properties:

- `agent/my_agent.py` is a random policy with an `ls20`-specific branch.
- It seeds the module-global random generator from wall-clock time and Python `hash()`.
- It enumerates all `GameAction` members rather than using the current legal-action set.
- It mutates shared `GameAction` enum instances with `set_data()` and `reasoning`.
- The framework's agent loop uses `action_counter <= MAX_ACTIONS`, so the apparent cap is not exact.
- The Kaggle framework creates one agent thread per game; `scripts/play_local.py` runs games sequentially.
- The notebook builder packages only `my_agent.py` and installs only `arc-agi` and `python-dotenv` from the competition wheelhouse.
- `notebooks/kernel-metadata.json` has no model or dataset source and still contains a username placeholder.
- `.kaggle/access_token` is absent; it must remain untracked when supplied.
- Public environment payloads for `ls20` and `vc33` are downloaded. Both are exposed and must belong to development.
- The workspace is not a Git repository, so clean-checkout reproduction is not yet available.

Before the first Kaggle submission, perform a non-secret credential and account preflight:

- Competition rules accepted.
- Kaggle kernel ID contains the correct username.
- `.kaggle/access_token` exists, is non-empty, has restrictive permissions, and remains ignored.
- Required competition and model sources are attached.
- Internet is disabled in notebook metadata.

# 2. Executive decision

Build a measured closed-loop agent with two separated responsibilities:

1. **Deterministic code owns truth, budgets, and safety.** It records exact evidence, normalizes legal actions, owns request-local action data, analyzes frame sequences, enforces resource limits, validates model output, checks predictions, and selects controller mode.
2. **The local model owns uncertain interpretation.** It proposes goals, mechanics, discriminating probes, memory revisions, and short plans from selected evidence. In one E1 treatment, it may also write bounded analysis code, but that code never submits environment actions or mutates production state.

The milestone path is:

    E0 reproducible packaging + immutable action boundary + legal fallback
      -> [E1S minimal multimodal structured-action policy
          versus
          E1C minimal policy with bounded Python analysis workspace]
      -> E1 selected primary paradigm + measured decision table
      -> E2 exact inter-frame/inter-action evidence + click candidates
      -> E3 compact cross-level memory
      -> E4 evidence retrieval + retrodiction
      -> E5 bounded hypotheses + one-action prediction checks
      -> E6 prediction-checked short queues

The following remain conditional:

    E7 advanced component correspondence
    E8 executable transition models, search, or specialist requests

Learned perception, reinforcement learning, test-time parameter training, unrestricted code execution, and permanent multi-agent debate are not milestone requirements.

# 3. Objectives and success criteria

## 3.1 Competition objective

Maximize official ARC-AGI-3 RHAE on the 110 unseen evaluation environments within Kaggle's offline runtime, hardware, and reproducibility constraints.

For a completed level `l`:

    level_score_l = min(1.15, (human_baseline_actions_l / agent_actions_l)^2)

An uncompleted level contributes zero. A game's score is the level-index-weighted aggregation of its level scores. The competition score is the mean across all evaluated games, with untouched games counted as zero and the final score capped according to the official implementation.

The official `arc-agi` scoring implementation is authoritative if prose and a local reimplementation disagree.

## 3.2 Evaluation hierarchy

For any fixed evaluation set, use this order:

1. Mean official RHAE across the entire fixed set, including untouched games as zero.
2. Paired per-game RHAE differences between treatment and control.
3. Coverage: games with non-zero score and games fully completed.
4. Weighted level-completion fraction.
5. Levels completed.
6. Actions per completed level and actions before first progress.
7. Predeclared structural progress diagnostics only when neither arm achieves measurable RHAE.

Public human baselines may be used by the evaluation harness to calculate exact RHAE. They must not be exposed to the policy, prompt, model workspace, action allocator, or controller.

H1 and H2 also use exact official RHAE because they are held-out public environments whose baselines are available to the evaluator. A baseline-free proxy is used only for an environment on which the evaluator genuinely lacks a human baseline, and it may not replace official RHAE where RHAE is available.

## 3.3 Milestone outcome

By September 30, the selected candidate should:

- Produce at least one valid end-to-end Kaggle competition submission before the final verification window.
- Complete a competition-like run without invalid actions, uncaught agent exceptions, cross-game action data, starved clients, or missing scorecard entries.
- Load the model, tokenizer, native libraries, wheels, framework, and agent source without internet access from declared mounted artifacts.
- Use one measured primary model service unless a different topology demonstrates superior RHAE within the same resource ceilings.
- Beat E0 under the paired official-RHAE protocol.
- Preserve exact observation evidence while bounding active model context.
- Produce deterministic animation metadata for every multi-frame response.
- Execute one action under uncertainty and no more than four actions under verified dynamics.
- Stop a queued plan after the first material prediction failure.
- Finish below 7.65 hours in the full-run projection and competition-like load test.
- Publish the required source, license, notebook, model/dependency manifest, and reproduction instructions before the milestone deadline if pursuing the milestone prize.

## 3.4 Treatment acceptance

Before every policy, model, perception, memory, or planning comparison, record:

- Treatment and control identifiers.
- Fixed game set and paired game seeds.
- Agent RNG and, where controllable, model decoding seeds.
- Model, quantization, prompt, representation, and context policy.
- Equal wall-clock, token, model-call, action, reset, and retry budgets.
- Primary outcome and minimum practical effect `delta_min`.
- Uncertainty procedure and confidence level.
- Catastrophic tail-regression threshold.
- Handling of crashes, timeouts, and missing results.

Use paired per-game results. Estimate uncertainty with a paired bootstrap or paired permutation procedure appropriate to the sample size. Report the point estimate, interval, dispersion, coverage, and worst regression.

Classify the treatment as:

- **Accept:** primary improvement is at least `delta_min`, uncertainty meets the predeclared rule, resource ceilings are preserved, and no catastrophic tail regression occurs.
- **Reject:** the treatment is materially worse, exceeds a resource ceiling, or crosses the catastrophic tail-regression threshold.
- **Inconclusive:** neither acceptance nor rejection conditions are met.

An inconclusive result is not silently promoted. It may be rerun only under a predeclared replication rule.

Reliability changes may be accepted for eliminating a reproduced failure when paired performance remains within a predeclared non-inferiority margin.

## 3.5 Runtime and inference budget

The operational target is 7.65 hours, or 27,540 seconds:

| Budget | Provisional ceiling |
|---|---:|
| Offline install, import, and model load | 900 seconds |
| Environment I/O, deterministic work, and recording | 3,300 seconds |
| Shared model service | 19,800 seconds |
| Scorecard close and artifact finalization | 600 seconds |
| Operating reserve inside the target | 2,940 seconds |
| Total | 27,540 seconds |

These figures are provisional ceilings, not invented precision. Phase 1 replaces them with target-accelerator measurements.

Let:

- `G = 110`, the evaluation game count.
- `A` be the measured and configured action cap per game.
- `B_model` be the model-service wall-clock budget.
- `L_weighted` be sustained mean service time under representative mixed traffic.

For serialized service:

    C_max = floor(B_model / L_weighted)

For batching, derive capacity from sustained completed requests per wall-clock second, including queueing and batch-formation delay.

## 3.6 Mandatory Phase 1 decision table

Phase 2 may not begin until an archived decision table contains:

| Field | Required value |
|---|---|
| Accelerator and runtime | Exact measured environment |
| Primary model | Source, version, license, architecture |
| Quantization and load mode | Exact format and parameters |
| Agent paradigm | E1S, E1C, or measured hybrid |
| Observation representation | Image, grid encoding, animation policy |
| Context policy | Normal/deep input limits and eviction |
| Output policy | Token limit, schema, repair rule |
| Cold load / first request | Measured seconds |
| Sustained throughput | Requests/hour under mixed 110-client load |
| Latency | Queue and service p50/p90/p99 |
| Memory | Peak VRAM, RAM, and disk |
| Total model calls/tokens | Hard maxima |
| Guaranteed allocation | Calls/tokens per game |
| Discretionary allocation | Global pool size and priority rule |
| Action/reset/retry caps | Exact tested values |
| Timeouts | Queue, request, per-game, and global deadlines |
| Degradation strategy | Measured fallback path |
| Utility estimate | Paired RHAE gain per inference-second |

False precision before profiling is prohibited. Proceeding without the completed table is also prohibited.

# 4. Reproducibility and evaluation boundary

## 4.1 Reproducibility contract

Before policy development:

- Initialize version control.
- Verify that `.env`, `.kaggle`, downloaded environments, recordings, caches, generated notebooks, and model caches remain ignored.
- Pin Python, `arc-agi`, local framework revision, notebook builder, Python dependencies, and native inference dependencies.
- Record the compatibility boundary with the framework supplied by the Kaggle competition dataset.
- Record source, wheel, model, tokenizer, configuration, and prompt hashes.
- Add a clean-checkout bootstrap and compatibility smoke test.

Two reproduction modes must be named separately:

1. **Local bootstrap:** clean checkout plus declared network-fetched or pre-cached dependencies and selected public games.
2. **Kaggle offline reproduction:** clean checkout plus declared Kaggle-mounted competition, dependency, and model artifacts; no internet or secret is required at runtime.

The phrase "clean checkout runs offline" is not used without naming the required mounted artifacts.

## 4.2 Public-game partition

Before inspecting any additional source, trajectory, replay, or mechanics:

1. Record all already exposed environments. `ls20` and `vc33` are development games.
2. Retrieve the 25-game public inventory without opening unexposed source or playing sealed candidates.
3. Select a partition using a recorded seed:
   - 15 development environments, including all exposed games.
   - 5 H1 architecture-gate environments.
   - 5 H2 final-candidate environments.
4. Hash and archive the partition manifest.

The development set may contain a rotating diagnostic subset for routine comparisons. H1 and H2 are relative architecture guards, not claims that public performance represents the private distribution.

Named gates:

- **H1 architecture gate:** one planned evaluation after E5 or E6 is internally stable.
- **H2 candidate gate:** one planned evaluation during final candidate selection.

Do not inspect H1/H2 mechanics, frames, source, trajectories, replays, or per-step explanations after evaluation. The evaluation harness may calculate exact aggregate and paired RHAE while withholding baselines and raw evidence from the policy and developer-facing tuning report.

A rerun after an infrastructure failure is allowed only under a predeclared invalid-run rule and only when no usable policy result was revealed.

Kaggle submissions are sparse external confirmation, not the daily optimizer.

## 4.3 Deployment manifests

Maintain:

1. **Source manifest:** explicit allowlist of agent modules and configurations embedded in the notebook.
2. **Dependency manifest:** wheels, shared libraries, CUDA assumptions, hashes, sizes, licenses, and offline install order.
3. **Model manifest:** Kaggle source, weights, tokenizer, templates, quantization, hashes, sizes, license, mount paths, and load mode.

The notebook builder fails on missing source, unresolved imports, absent model sources, unexpected artifacts, hash mismatches, placeholder kernel IDs, incompatible licenses, or internet-enabled metadata.

# 5. Repository layout and ownership

    agent/
      __init__.py
      my_agent.py          framework adapter, lifecycle, top-level guard
      action.py            frozen decisions and request-local submission
      state.py             immutable records, controller state, hypotheses
      perception.py        canonical grids and inter-action features
      animation.py         intra-action frames, transient cells, motion summaries
      evidence.py          exact content-addressed evidence and retrieval
      controller.py        modes, budgets, legal guards, fallback, queue checks
      model_policy.py      prompt/context assembly and structured responses
      scratchpad.py        bounded read-only analysis workspace
      inference.py         model service, scheduling, telemetry, degradation
      metrics.py           official RHAE aggregation and paired experiment reports
      config.py            validated run and budget configuration

    packaging/
      source_manifest.txt
      dependency_manifest.json
      model_manifest.json

    evaluation/
      public_partition.json
      experiment_registry.jsonl
      budget_decision_table.json

    tests/
      unit/
      integration/
      synthetic/

    scripts/
      build_notebook.py
      play_local.py
      play_concurrent.py
      load_test_inference.py
      compare_treatments.py

Add search-specific production code only if E8 passes its entry gate.

Ownership rules:

| Module | Owns | Must not own |
|---|---|---|
| `my_agent.py` | Framework integration and guarded orchestration | Game-specific mechanics |
| `action.py` | Immutable decisions and direct submission | Policy selection |
| `state.py` | Typed per-game state | I/O or model loading |
| `perception.py` | Observation-derived features | Semantic guesses presented as facts |
| `animation.py` | Frame-sequence facts and bounded motion candidates | Unverified intent labels |
| `evidence.py` | Lossless writes and exact retrieval | Summaries as the only record |
| `controller.py` | Legal actions, modes, budgets, fallback | Provider-specific prompting |
| `model_policy.py` | Context selection and model proposals | Direct environment calls |
| `scratchpad.py` | Constrained analysis execution | Environment action authority or secrets |
| `inference.py` | Model lifecycle, scheduling, telemetry | Per-game mutable memory |
| `metrics.py` | Evaluator-only RHAE and statistics | Policy-visible human baselines |
| `config.py` | Validated constants and budgets | Runtime state |

# 6. Algorithm specifications

## 6.1 Immutable action execution

The controller produces a frozen `ActionDecision`:

    ActionDecision
      action_id: integer
      data: immutable request-local coordinate payload or empty
      reasoning: immutable request-local mapping
      source: structured_model, scratchpad_model, queued_plan, or fallback
      expected_effect: optional structured prediction
      stop_condition: optional structured condition

Production code must not call `GameAction.set_data()`.

At submission:

1. Re-read the current legal-action set.
2. Validate the decision ID and coordinate bounds.
3. Resolve the corresponding enum member without mutating it.
4. Call `arc_env.step(action, data=fresh_dict, reasoning=fresh_dict)`.
5. Record the exact submitted decision.
6. Clear pending data in a `finally` block.

Override the upstream loop where necessary so the configured action cap has exact semantics and cleanup occurs on every exit path.

## 6.2 Deterministic fallback

The permanent fallback must:

- Contain no game-ID condition or solution table.
- Draw only from normalized current `available_actions`.
- Use a per-agent `random.Random` seeded by a stable digest.
- Generate ACTION6 coordinates from actual grid bounds and ranked candidates.
- Handle start, active play, level transition, GAME_OVER, exhaustion, and terminal completion.
- Catch policy, parsing, inference, scratchpad, and evidence failures.
- Record a reason for every decision.
- Enforce exact action, reset, retry, call, token, and wall-clock budgets.

`no_visible_change` is evidence scoped to an action and context fingerprint, not proof of latent no-op behavior. Apply a decaying penalty and allow deliberate retry after a material context or hypothesis change.

## 6.3 Exact observations

For every environment response:

1. Preserve the full ordered frame sequence.
2. Deduplicate exact frames with stable content hashes.
3. Retain the final frame as the stable canonical state when appropriate.
4. Record shape, palette, legal actions, game state, levels completed, win levels, counters, and monotonic time remaining.
5. Preserve the causal transition that completes a level before clearing scratch memory.
6. Support rectangular and sub-64×64 grids.

The canonical state and animation trace are separate views of the same response. Selecting the final frame as canonical must never discard intermediate evidence.

## 6.4 Mandatory animation analysis

For every response, compute inexpensive deterministic metadata:

- Number of returned frames and distinct frames.
- Stable hashes and frame-to-frame changed-cell counts.
- Intra-action changed-cell masks and union bounding box.
- Transient cells present only in intermediate frames.
- Per-color additions and removals through the sequence.
- Appearing and disappearing regions.
- Approximate motion paths for unambiguous regions.
- Candidate causal order, explicitly marked uncertain when ambiguous.
- Whether the final frame alone hides material transition information.

Default model input includes the final rendered frame, exact/compact grid representation, inter-action delta, and animation summary.

Expose cropped timelines or full animation strips only when a deterministic trigger fires, such as:

- Motion path or causal order is decision-relevant and unresolved.
- A transient signal appears.
- Final-state deltas are ambiguous.
- A prediction failed in a way intermediate frames may explain.
- The model explicitly requests animation evidence within budget.

Record the additional image/token cost and compare its paired RHAE gain. Unconditional full-animation prompting is not the default.

## 6.5 Inter-action differences and click candidates

Between compatible canonical grids, compute changed cells, bounding regions, color additions/removals, legal-action changes, and simple translation/recoloring candidates. Shape changes are scene boundaries and preserve both grids.

Generate ACTION6 candidates from:

- Centroids and interior points of same-color regions.
- Small isolated or button-like regions.
- Rare colors.
- Newly changed or transient regions.
- Endpoints and intersections of thin structures.
- Centers of unexplored regions when object candidates are exhausted.

Rank with ordered features for novelty, salience, change relevance, hypothesis discrimination, contextual no-change, repetition, and irreversible risk. Do not tune numeric weights on a single exposed game.

## 6.6 Compact working memory and evidence

Maintain three isolated stores per game:

1. **Durable memory:** verified mechanics, invariants, hazards, reusable procedures, and important counterexamples.
2. **Level scratch:** current objects, subgoal, active hypotheses, candidate plan, unresolved evidence, and cheapest useful probe.
3. **Rejected-hypothesis ledger:** rejected claim, contradiction evidence, scope, and reconsideration conditions.

All statements reference exact transition IDs. Model summaries append revisions but cannot replace evidence. Apply explicit token, item, byte, RAM, and disk ceilings.

Each transition records pre/post observation references, legal actions, submitted decision, exact inter-frame and inter-action evidence, progress, queue result, and inference telemetry.

## 6.7 E1 paradigm bake-off

Both E1 treatments share:

- The same immutable action boundary.
- The same deterministic fallback and click candidates.
- The same model service when the selected weights support both treatments.
- The same observation evidence and animation exposure policy.
- Identical total wall-clock, token, call, action, reset, and retry budgets.
- The same game/seed pairs.

### E1S — Multimodal structured-action policy

The model receives selected evidence and returns a strict structured response containing a revisable state update, hypothesis updates, intent, subgoal, one-to-four proposed actions, observable predictions, stop conditions, and optional memory updates.

Validation parses or repairs syntax only, rejects unsupported fields, validates actions and coordinates, enforces controller queue length, and falls back without inventing an action.

### E1C — Bounded Python analysis workspace

The model may write analysis code against read-only evidence APIs. The workspace:

- Has no network access.
- Cannot read environment variables, credentials, arbitrary filesystem paths, or production objects.
- Cannot install packages.
- Uses an import allowlist and bounded CPU time, memory, output bytes, and invocation count.
- Receives immutable copies or serialized views of selected frames, deltas, regions, and history.
- Runs in an ephemeral directory or isolated subprocess.
- Cannot call `arc_env`, submit actions, mutate controller state, or persist executable state between games.
- Returns only a structured proposal through the same validation boundary as E1S.

The workspace is an analysis instrument, not an alternate control plane.

Python AST filtering and an import allowlist alone are not a security boundary. E1C may proceed only if the target runtime supports a separately launched process with a sanitized environment, explicit file descriptors or serialized inputs, a disposable working directory, operating-system resource limits, and enforceable filesystem/process restrictions. If those guarantees cannot be demonstrated on Kaggle, replace arbitrary Python with a fixed, non-Turing-complete set of array and evidence-query operations; do not execute model-authored Python in the agent process.

### Bake-off decision

Compare mean official RHAE and paired per-game RHAE under equal budgets. Also report score per inference-second, coverage, failure rate, and tail regressions.

If treatments use different base models, do not attribute the entire difference to the harness. Run a same-model comparison where possible or label the result as a model-plus-harness bundle comparison.

Select E1S, E1C, or a narrowly defined hybrid before Phase 2. Additional candidate/arbiter machinery is excluded unless it later passes an independent treatment gate.

## 6.8 Bounded hypotheses and controller modes

Maintain two to four active hypotheses, each with claim, scope, supporting/contradicting transition IDs, predictions, cheapest distinguishing probe, expected progress, reversibility, risk, complexity, exception count, and status.

Controller modes remain deterministic:

| Mode | Behavior |
|---|---|
| Bootstrap | Start/reset legally and capture initial evidence |
| Normal | One model proposal and one action under uncertainty |
| Fast | Continue a verified short queue with minimal model work |
| Deep | Retrieve evidence and spend a bounded deeper request |
| Recovery | Cancel queues and choose safe novel evidence |
| Exhausted | Use deterministic fallback only |
| Done | Stop after win or hard global deadline |

The model may describe intent but cannot select controller mode or override budgets.

## 6.9 Prediction-checked execution

- Use one action during Bootstrap, Deep, Recovery, and uncertain Normal operation.
- Permit up to four queued actions only when relevant dynamics are verified and each action has an observable prediction.
- Check every real transition, including animation evidence, before executing the next queued action.
- Cancel on mismatched status, legal actions, region structure, visible change, animation event, or progress.
- Preserve and retrospect on the level-completing transition.
- Do not treat an accidental win as verified mechanics.

## 6.10 Shared inference and score-aware allocation

The minimal service provides exactly-once model initialization, request isolation, bounded queues, cancellation, deadlines, exception containment, and queue/service/token/memory telemetry.

Every game receives a measured initial service floor because all 110 games count. Remaining calls come from a shared pool with starvation bounds.

Rank discretionary work by estimated incremental RHAE per inference-second, using only policy-legal information:

    estimated probability of next-level completion
      × estimated level-index value
      × expected action-efficiency retention
      ÷ expected inference and environment time

Human baseline values from hidden or held-out evaluation metadata may not enter this estimate. Calibrate generic priors on development games only.

Batching or multiple workers are accepted only when they improve sustained closed-loop RHAE within memory and deadline ceilings. "Exactly one instance" is not a goal by itself; one loaded primary service is the default topology until measurements justify another.

## 6.11 Conditional advanced work

Enter E7 only after a measured failure is attributed to unstable identity tracking that simpler delta, animation, or region features cannot resolve.

Enter E8 only when a compact state exists, relevant predictions are accurate, failure is attributable to planning, and the expected RHAE gain fits the remaining compute budget. Search never bypasses real-transition verification.

# 7. Sequential implementation schedule

## Phase 0 — Correctness, partition, and E0

**Dates:** September 4–7

Deliverables:

- Git initialization and ignore audit.
- Credential/account preflight without committing secrets.
- Correct 15/5/5 public partition before further exposure.
- Pinned compatibility record and three deployment manifests.
- Multi-file notebook packaging skeleton.
- Frozen `ActionDecision` and request-local submission.
- Exact action limit and guarded lifecycle.
- Legal deterministic fallback.
- Sequential and 110-client action-isolation tests.
- First valid E0 Kaggle submission.

Exit gate:

- Zero invalid actions and uncaught exceptions in three development runs.
- Zero ACTION6 coordinate/reasoning crossover.
- Deterministic traces for fixed seeds.
- Kaggle offline smoke test succeeds with declared mounted artifacts.

## Phase 1 — Model, representation, and paradigm decision

**Dates:** September 8–11

Deliverables:

- Target-accelerator model and quantization profiles.
- Minimal shared inference service.
- E1S structured-action treatment.
- E1C constrained-workspace treatment.
- Image/grid representation comparison.
- Selective animation-input smoke test.
- Paired E1S/E1C/E0 closed-loop report.
- Completed mandatory decision table.
- Offline model/tokenizer/native dependency notebook.

Exit gate:

- A selected E1 paradigm beats E0 under the official-RHAE acceptance rule.
- The decision table has no missing required fields.
- The full-run projection fits time, VRAM, RAM, disk, artifact, and license ceilings.
- Phase 2 remains blocked if this gate fails.

## Phase 2 — Exact evidence, animation, and continuity

**Dates:** September 12–15

Deliverables:

- Stable canonical observations.
- Mandatory intra-action animation summaries.
- Exact inter-action differences.
- Selective animation timeline/crop exposure.
- Content-addressed evidence.
- Lightweight click candidates.
- Durable, scratch, and rejected-hypothesis memory.
- Level-boundary retrospection.
- E2 through E4 paired ablations.

Exit gate:

- Evidence is exactly recoverable within storage ceilings.
- Animation summaries pass synthetic correctness tests.
- Additional animation input is used only by recorded triggers.
- Accepted E2–E4 treatments meet the statistical rule.

## Phase 3 — Hypotheses and guarded plans

**Dates:** September 16–19

Deliverables:

- Bounded hypotheses with evidence references.
- One-action discriminating probes.
- Outcome, structural, and animation-aware prediction checks.
- One-to-four-action verified queues.
- Full deterministic controller modes.
- E5/E6 paired comparisons.
- One H1 architecture evaluation after internal stability.

Exit gate:

- Accepted E5/E6 treatments meet the statistical rule.
- Incorrect queues stop after one mismatching action.
- H1 remains sealed from inspection and ordinary tuning.

## Phase 4 — Competition scheduling and load behavior

**Dates:** September 20–23

Deliverables:

- Measured per-game service floor and discretionary pool.
- Incremental-RHAE-per-second priority implementation.
- Starvation bounds and deadline degradation.
- Optional batching/worker experiment.
- Concurrent public subset runner.
- 110-client service and failure-injection tests.
- Updated full-run projection.

Exit gate:

- No game crashes or indefinite starvation.
- Model and scratchpad failures degrade to legal decisions.
- Aggregate throughput supports the decision table.
- Projected runtime remains below 7.65 hours.

## Phase 5 — Evidence-driven optional work

**Dates:** September 24–26

Eligible treatments include advanced correspondence, executable transition functions, structural replay, verified search, or a bounded specialist request. Each requires a paired official-RHAE acceptance result; proxy accuracy alone is insufficient.

## Phase 6 — Candidate selection and freeze

**Dates:** September 27–28

Deliverables:

- Conservative and higher-reasoning candidates.
- One H2 evaluation under the predeclared candidate rule.
- Selected artifact with hashes and complete profiles.
- Candidate freeze by September 28.

## Phase 7 — Release and submission verification

**Dates:** September 29–30

Use this window for reruns, infrastructure recovery, mount-path verification, public notebook/repository publication, license verification, reproduction checks, and final milestone submission. Do not add unmeasured policy changes after the freeze.

The deadline is September 30 at 11:59 PM UTC, corresponding to October 1 at 7:59 AM China Standard Time.

# 8. Evaluation and tests

## 8.1 Unit tests

- Stable seed derivation across processes.
- Legal-action normalization and exact action-cap semantics.
- Immutable decision validation and absence of production `set_data()` calls.
- Concurrent unique ACTION6 payload isolation.
- Grid and frame-sequence hash determinism.
- Inter-frame transient, appearance, disappearance, and simple-motion cases.
- Inter-action movement, recoloring, creation, deletion, no-change, and scene boundaries.
- Selective animation triggers and token accounting.
- Click candidates across rectangular and maximum grids.
- Evidence deduplication and recovery.
- Context-scoped no-change penalties.
- Strict model and scratchpad response validation.
- Workspace import, filesystem, environment, network, resource, and action-authority restrictions.
- Queue cancellation on every mismatch class.
- Evaluator-only baseline isolation.
- Official RHAE fixture parity with the toolkit.
- Paired statistical report and three-way outcome classification.

## 8.2 Integration tests

- Missing Kaggle username, token, source, model, wheel, tokenizer, or license entries.
- Framework/SDK compatibility mismatch.
- Model unavailable, timeout, cancellation, and malformed output.
- Scratchpad timeout, forbidden operation, oversized output, and crash.
- Exactly-once model initialization under concurrent construction.
- Level transition during a queue.
- GAME_OVER, reset exhaustion, global deadline, and clean termination.
- 110 simultaneous inference clients with starvation bounds.
- Storage ceiling projection.
- Clean-checkout local bootstrap with declared dependencies.
- Clean-checkout Kaggle offline run with declared mounts.
- Concurrent public-game subset execution.

## 8.3 Closed-loop experiments

| Treatment | Primary paired comparison |
|---|---|
| E0 | Correct deterministic fallback vs current random policy |
| E1S | Minimal multimodal structured policy vs E0 |
| E1C | Bounded analysis workspace policy vs E0 and E1S |
| E2a | Exact inter-action deltas vs selected E1 |
| E2b | Mandatory animation summary vs final-frame-only evidence |
| E2c | Selective animation exposure vs summary-only input |
| E3 | Durable/scratch memory vs bounded recent history |
| E4 | Exact retrieval/retrodiction vs summary-only context |
| E5 | Bounded hypotheses vs one unconstrained explanation |
| E6 | Prediction-checked queues vs one model call per action |
| E7 | Advanced correspondence vs lightweight regions/animation |
| E8 | Verified model/search/specialist vs selected E6/E7 |

Fixed trajectories may test correctness and cost. Policy acceptance requires paired closed-loop rollouts.

## 8.4 Required reporting

Every experiment report includes:

- Mean official RHAE over the full fixed set.
- Paired per-game RHAE differences and uncertainty.
- `delta_min`, acceptance rule, and result classification.
- Non-zero coverage, full games, weighted level completion, and levels.
- Actions per completed level and before first progress.
- Invalid, no-change, repetition, reset, and death rates.
- Prediction accuracy, queue breaks, and memory revision metrics.
- Animation triggers, extra tokens, and RHAE per added token/second.
- Model/scratchpad failure and deterministic fallback rates.
- Calls, tokens, queue wait, service latency, RAM, VRAM, disk, and runtime.
- Worst per-game regression and catastrophic-tail status.

## 8.5 Run artifact

Archive source commit and dirty status, manifests, hashes, accelerator/runtime versions, partition and seeds, predeclared experiment record, decision table, machine-readable metrics, exact evidence references, and closed scorecard.

# 9. Merge and escalation gates

Accept infrastructure work only when it eliminates a reproduced failure, preserves policy performance within the declared margin, and remains within resource ceilings.

Accept policy work only under Section 3.4. Reject or defer work when:

- Its gain occurs on one exposed game only.
- It depends on a best seed or selective rerun.
- It improves only an offline proxy.
- It violates paired resource equality.
- It raises projected runtime above 7.65 hours.
- It reduces the guaranteed service floor below the measured minimum.
- It adds an unvalidated control path.
- It crosses the catastrophic tail threshold.
- It requires H1/H2 for ordinary tuning.

# 10. Principal risks and controls

| Risk | Control |
|---|---|
| Metric selects the wrong candidate | Official mean and paired per-game RHAE are primary |
| Public baseline leaks to policy | Evaluator-only metrics boundary and isolation tests |
| Final-frame analysis misses causal evidence | Mandatory animation summaries and selective timelines |
| Animation consumes moves through token latency | Triggered exposure and RHAE-per-token accounting |
| Wrong agent paradigm is hardened early | Equal-budget E1S/E1C bake-off |
| Scratchpad becomes an unsafe control plane | Read-only inputs, subprocess limits, no action authority |
| Small noisy gains are accepted | Minimum effect, paired uncertainty, inconclusive state |
| Tail regressions hide behind mean gains | Predeclared catastrophic-regression gate |
| Holdout is too small | Fixed 15/5/5 partition |
| Public holdout overstates private generalization | H1/H2 treated only as relative architecture guards |
| Shared enum data crosses threads | Frozen decisions and direct request-local submission |
| Inference starves games | Service floor, utility scheduling, aging, deadlines |
| Symbolic budgets survive into implementation | Hard Phase 1 decision-table gate |
| Offline artifact is incomplete | Three manifests and mount-aware smoke tests |
| Clean-checkout claim is ambiguous | Separate local and Kaggle reproduction contracts |
| Search trusts a false world model | Prediction gate and real-action replanning |

# 11. Next 72 hours

Execute in this order:

1. Initialize Git and audit ignored secrets/artifacts.
2. Complete Kaggle username, token-presence, rules, and attachment preflight without committing credentials.
3. Inventory the 25 public games and freeze the 15/5/5 partition; place `ls20` and `vc33` in development.
4. Add source, dependency, and model manifest schemas.
5. Extend notebook packaging for multiple source files and mount validation.
6. Implement frozen `ActionDecision`, request-local submission, and exact action caps.
7. Remove global RNG, unstable seeding, game-ID policy, and static action enumeration.
8. Add lifecycle failure guards and the 110-client payload-isolation test.
9. Implement canonical hashes plus minimal inter-frame and inter-action deltas.
10. Produce three deterministic E0 runs and the first valid Kaggle submission.
11. Build minimal E1S and E1C smoke paths sharing one validation boundary.
12. Start target-accelerator profiling for the Phase 1 decision table.

# 12. Definition of done

Plan 4 is implemented when:

- Both reproduction contracts pass with their declared inputs.
- Production policy contains no public-game IDs or solution tables.
- No production path mutates `GameAction` state.
- Every action is legal, request-local, bounded, and recorded.
- Exact action/reset/retry semantics are tested.
- A 110-client test shows no payload crossover or indefinite starvation.
- Human baselines are evaluator-only.
- Official RHAE calculations match the toolkit.
- The selected E1 paradigm won a paired equal-budget comparison.
- The Phase 1 decision table is complete and measured.
- Every multi-frame response receives deterministic animation analysis.
- Full animation reaches the model only through budgeted triggers.
- Exact evidence remains recoverable within storage limits.
- Model-facing state is bounded and references exact evidence.
- The scratchpad cannot access secrets, network, arbitrary files, production state, or the environment action interface.
- Model or scratchpad failure produces a legal fallback decision.
- Incorrect queued predictions stop after one mismatch.
- Policy treatments have accept/reject/inconclusive reports with minimum effects and tail gates.
- The public partition remains 15 development, 5 H1, and 5 H2; H1/H2 are used only at named gates.
- The final artifact passes unit, integration, concurrent-load, offline-notebook, and closed-loop gates.
- The full-run projection and competition-like run remain below 7.65 hours.
- Prize-eligibility materials are public under compatible licenses before the milestone deadline when eligibility is pursued.

# 13. Primary references

- Kaggle competition: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3
- Kaggle data and 110-game evaluation description: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data
- ARC-AGI-3 documentation: https://docs.arcprize.org/
- Game schema: https://docs.arcprize.org/game-schema
- Scoring methodology: https://docs.arcprize.org/methodology
- Competition mode: https://docs.arcprize.org/toolkit/competition_mode
- Official toolkit: https://github.com/arcprize/ARC-AGI
- Official agent framework: https://github.com/arcprize/ARC-AGI-3-Agents
- Milestone 1 review: https://arcprize.org/blog/arc-prize-2026-milestone-1
- Animation experiment: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/734369
