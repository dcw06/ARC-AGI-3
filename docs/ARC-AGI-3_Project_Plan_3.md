---
title: "ARC Prize 2026 — ARC-AGI-3"
subtitle: "Plan 3: Budgeted Single-Developer Implementation"
author: "Project Team"
date: "4 September 2026"
status: "Proposed — revised execution companion to the active strategic plan"
---

# Document purpose

This document is the execution-ready successor to ARC-AGI-3_Project_Plan_2.md. It incorporates the technical review of Plan 2 while preserving its central architecture: deterministic code owns evidence and safety, while a local model owns uncertain interpretation.

ARC-AGI-3_Project_Plan.md remains the strategic source of truth. This document owns implementation order, repository boundaries, quantitative budgets, test gates, and milestone release work. ARC-AGI-3_Project_Plan_2.md remains unchanged as a design-history record.

The plan assumes one primary implementer. No phase depends on parallel engineering unless ownership is explicitly reassigned.

The plan starts from the repository's verified state:

- agent/my_agent.py is a random policy with a public-game-specific branch.
- The current action path mutates shared GameAction enum instances.
- The Kaggle notebook packages only my_agent.py and installs only arc-agi and python-dotenv.
- notebooks/kernel-metadata.json has no attached model or dataset source.
- Kaggle's framework creates one thread per game, while scripts/play_local.py runs games sequentially.
- Only ls20 and vc33 are currently downloaded.
- The workspace is not yet a Git repository, so clean-checkout reproduction is not currently possible.

# 1. Executive decision

Build a measured closed-loop agent with two separated responsibilities:

1. **Deterministic code owns truth, budgets, and safety.** It records exact evidence, normalizes legal actions, owns request-local action data, detects visible repetitions, enforces compute limits, validates model output, and checks predictions.
2. **The local model owns uncertain interpretation.** It proposes goals, mechanics, discriminating probes, memory revisions, and short plans from selected evidence.

The single-developer milestone path is:

    E0 reproducible packaging + immutable action boundary + legal fallback
      -> E1 one shared offline model + measured service budget
      -> E2 exact deltas + lightweight click candidates + lossless references
      -> E3 compact cross-level memory
      -> E4 evidence retrieval + retrodiction
      -> E5 bounded hypotheses + one-action prediction checks
      -> E6 prediction-checked short queues

The following are conditional and must not delay E0 through E6:

    E7 advanced components and component correspondence
    E8 executable transition models, search, or specialist calls

Learned perception, reinforcement learning, test-time parameter training, general program synthesis, and permanent multi-agent debate are not milestone requirements.

# 2. Objectives and success criteria

## 2.1 Competition objective

Maximize official ARC-AGI-3 score on unseen environments within the Kaggle runtime, offline execution, hardware, and reproducibility constraints.

Local experiments cannot reproduce the hidden human-action baselines. Use this metric hierarchy:

1. Games completed.
2. Weighted level-completion fraction, using level indices and win_levels where available.
3. Levels completed.
4. Actions per completed level.
5. Actions before first level progress.
6. Predeclared structural progress proxies only when neither treatment completes a level.

Infrastructure correctness is necessary but does not substitute for progress on the first five outcomes.

## 2.2 Milestone outcome

By September 30, the selected candidate should:

- Produce at least one valid end-to-end Kaggle competition submission before the final verification window.
- Complete a competition-like run without invalid actions, uncaught agent exceptions, cross-game action data, starved clients, or missing scorecard entries.
- Load the model, tokenizer, native libraries, wheels, and agent source without internet access.
- Use exactly one primary model instance per process.
- Beat E0 on the predeclared development and rotating diagnostic protocol according to the metric hierarchy above.
- Preserve exact observation evidence through content-addressed references while bounding active model context.
- Execute one action under uncertainty and no more than four actions under verified dynamics.
- Stop a queued plan after the first material prediction failure.
- Finish below 7.65 hours in the full-run projection and competition-like load test.
- Publish the required source, license, notebook, model/dependency manifest, and reproduction instructions by the milestone deadline if pursuing the milestone prize.

## 2.3 Treatment acceptance

Policy, model, perception, memory, and planning changes are accepted on development and rotating diagnostic sets when:

- The median result across predeclared seeds improves the highest available metric in the hierarchy; or
- The primary outcome is non-inferior within a threshold declared before the run and a secondary outcome materially improves.

Every report must include dispersion and the worst observed regression. A best seed or selective rerun is not an acceptance result.

Reliability and infrastructure changes may be accepted for eliminating a reproduced failure if they preserve policy performance within a predeclared non-inferiority threshold.

The sealed holdout is not used for ordinary merge decisions. It is split before inspection and opened only at the named architecture and candidate gates in Section 3.4.

## 2.4 Runtime and inference budget

The operational target is 7.65 hours, or 27,540 seconds. Use this initial allocation:

| Budget | Initial ceiling |
|---|---:|
| Offline install, import, and model load | 900 seconds |
| Environment I/O, deterministic policy work, and recording | 3,300 seconds |
| Shared model service | 19,800 seconds |
| Scorecard close and artifact finalization | 600 seconds |
| Operating reserve inside the 7.65-hour target | 2,940 seconds |
| Total | 27,540 seconds |

These are initial ceilings, not estimates. Phase 1 replaces them with measurements from the target accelerator.

Let:

- G be the number of evaluated games, currently planned as 110.
- A be the exact configured action cap per game.
- B_model be the measured wall-clock model-service budget.
- L_weighted be sustained average service time per completed request under representative mixed normal and deep traffic.

For serialized service:

    C_max = floor(B_model / L_weighted)

For batching, calculate C_max from sustained completed requests per wall-clock second in the concurrent load harness, including queueing and batch-formation delay. Isolated single-request latency is not sufficient.

Before E1 is accepted, record:

- Cold-load and first-request time.
- Sustained requests per second with 110 synthetic clients.
- Normal and deep request latency distributions.
- Input and output tokens per request.
- Maximum total calls and tokens.
- Initial guaranteed calls per game.
- Size of the shared discretionary call pool.
- Queue timeout and hard request deadline.
- Deadline-degradation thresholds.

Reserve an initial service floor for every game, then spend the remaining pool according to estimated marginal score value with a starvation bound. Do not use unrestricted strict round-robin after the service floor has been met.

# 3. Phase 0 repository decisions

## 3.1 Establish reproducibility

Before policy development:

- Initialize version control.
- Verify that .env, .kaggle, downloaded environments, recordings, caches, and generated notebooks remain ignored.
- Pin Python, the arc-agi SDK, local framework revision, notebook builder, Python dependencies, and native inference dependencies.
- Record the compatibility boundary with the framework supplied by the Kaggle competition dataset.
- Add a clean-checkout bootstrap and smoke test.
- Record source, wheel, model, tokenizer, and configuration hashes.

The Kaggle-supplied framework can change independently of the vendored local copy. A compatibility smoke test must validate the actual competition-facing Agent and FrameData contract.

## 3.2 Replace the mutable action boundary

Define a frozen internal ActionDecision owned by one game agent:

    ActionDecision
      action_id: integer
      data: immutable request-local coordinate payload or empty
      reasoning: immutable request-local mapping
      source: model, queued plan, or fallback
      expected_effect: optional structured prediction
      stop_condition: optional structured condition

Production code must not call GameAction.set_data().

The framework adapter must:

1. Normalize latest_frame.available_actions, which arrives as integer IDs, into validated action IDs.
2. Store at most one pending ActionDecision on the individual MyAgent instance.
3. Override the action-submission boundary so arc_env.step() receives a fresh data dictionary and reasoning mapping directly.
4. Clear the pending decision in a finally block.
5. Reject an action if its ID is no longer legal at submission time.
6. Keep decision construction and environment submission free of shared mutable enum state.

Add a 110-client race test in which every client uses unique ACTION6 coordinates and reasoning. Zero payload or reasoning crossover is required.

Also make the action limit exact. The upstream loop currently uses a less-than-or-equal condition, so the adapter must not assume that MAX_ACTIONS means exactly that many actions.

## 3.3 Repair the deterministic fallback

The permanent fallback must:

- Remove every game-ID condition, including the ls20 branch.
- Draw only from normalized latest_frame.available_actions.
- Use a per-agent random.Random instance.
- Derive the seed from a recorded global seed and a stable digest of game ID; never use Python hash() or wall-clock time.
- Derive ACTION6 coordinates from current grid bounds and ranked candidates.
- Define behavior for NOT_PLAYED, active play, level transition, GAME_OVER, deadline exhaustion, and terminal completion.
- Catch policy, parsing, inference, and evidence-query failures before they escape the game thread.
- Record a reason for every decision.
- Enforce reset, retry, action, model-call, token, and wall-clock budgets.

A visually unchanged transition is not a permanent no-op fact. Record it as no_visible_change for the action under a specific context fingerprint. Apply a decaying or context-scoped penalty and permit a deliberate retry after the level, state, history, legal actions, or active hypothesis changes.

## 3.4 Protect the evaluation boundary

Before inspecting additional game source, trajectories, replays, or mechanics:

1. Record every already exposed environment.
2. Retrieve the accessible public-game inventory without opening source or playing sealed candidates.
3. Select partitions using a recorded seed.
4. Keep exposed games in development.
5. Maintain a rotating diagnostic set for normal policy decisions.
6. Create a sealed holdout of at least five games if the accessible inventory permits.
7. Split the sealed holdout a priori into H1, the architecture-gate subset, and H2, the final-candidate subset.

Named holdout gates:

- **H1 architecture gate:** once after E5 or E6 is internally stable.
- **H2 candidate gate:** once during candidate selection, before final freeze.

Do not inspect H1 or H2 mechanics after a run. Aggregate results may guide high-level decisions, but the environments do not return to development or diagnostic sets.

If fewer than five unexposed games are accessible, document the limitation and use the largest feasible sealed set. Do not silently relabel exposed games as holdout.

Kaggle leaderboard submissions are sparse external confirmation, not the daily optimizer.

## 3.5 Separate deployment manifests

Maintain three distinct manifests:

1. **Source manifest:** explicit allowlist of agent modules and configuration files embedded in the notebook.
2. **Dependency manifest:** exact wheels, shared libraries, CUDA/runtime assumptions, hashes, sizes, licenses, and offline installation order.
3. **Model manifest:** Kaggle model or dataset source, weight files, tokenizer, templates, quantization, hashes, sizes, license, expected mount paths, and load mode.

Update scripts/build_notebook.py and notebooks/kernel-metadata.json from these manifests. The builder must fail on a missing source file, unresolved import, absent model source, unexpected artifact, hash mismatch, or incompatible license declaration.

Do not assume two models can reside in VRAM or that a fallback can be loaded cheaply near the deadline. Phase 1 must choose one measured degradation strategy:

- The primary model with shorter context or smaller reasoning budget.
- A second simultaneously resident model, only if measured VRAM and throughput permit it.
- A conditionally loaded or offloaded model, only if load cost is demonstrably recoverable.
- Deterministic fallback without a second model.

# 4. Proposed repository layout

Keep the production agent small:

    agent/
      __init__.py
      my_agent.py          framework adapter, lifecycle, top-level failure guard
      action.py            frozen ActionDecision and request-local submission
      state.py             immutable records, controller state, hypotheses
      perception.py        canonical frames, deltas, lightweight click candidates
      evidence.py          content-addressed frames, transitions, exact queries
      controller.py        modes, budgets, legal guards, fallback, queue checks
      model_policy.py      prompt assembly, response schema, syntax-only repair
      inference.py         singleton model, request queue, telemetry, degradation
      config.py            validated run and budget configuration

    packaging/
      source_manifest.txt
      dependency_manifest.json
      model_manifest.json

    tests/
      unit/
      integration/
      synthetic/

    scripts/
      build_notebook.py
      play_local.py
      play_concurrent.py
      load_test_inference.py

Add search.py only if E8 passes its entry gate.

## 4.1 Ownership rules

| Module | Owns | Must not own |
|---|---|---|
| my_agent.py | Framework integration and guarded one-step orchestration | Game-specific mechanics or shared action payloads |
| action.py | Immutable decisions and direct environment submission | Policy selection |
| state.py | Typed immutable records and per-game state | I/O or model loading |
| perception.py | Observation-derived features | Semantic guesses presented as facts |
| evidence.py | Lossless content-addressed writes and exact retrieval | Model summaries as the only record |
| controller.py | Legal actions, modes, budgets, fallbacks, queue checks | Provider-specific prompting |
| model_policy.py | Context selection, schema parsing, model proposals | Direct environment calls |
| inference.py | Model lifecycle, scheduling, telemetry | Per-game mutable memory |
| config.py | Validated constants and budgets | Runtime state |

# 5. Algorithm specifications

## 5.1 Immutable action execution

The controller produces an ActionDecision, not a mutated GameAction. At the final boundary:

1. Re-read the current legal-action set.
2. Validate the decision ID and coordinate bounds.
3. Resolve the corresponding GameAction enum without mutating it.
4. Call arc_env.step(action, data=fresh_dict, reasoning=fresh_dict).
5. Record the submitted immutable decision.
6. Clear pending data even when the environment call raises.

The adapter must prove request isolation under concurrent ACTION6 calls.

## 5.2 Canonical observations

For every environment response:

1. Preserve each unique frame sequence in the content-addressed evidence store.
2. Use the final frame as the initial canonical observation unless animation tests justify a different stable-frame rule.
3. Record shape, palette, legal action IDs, game state, levels_completed, win_levels, local action counter, and locally computed monotonic time remaining.
4. Hash shape, dtype, and contiguous grid bytes with a stable digest.
5. Treat shape, level, or status changes as scene-boundary features without discarding the causal transition that produced them.

The action that completes a level is high-value evidence. Record its pre-state, action, visible result, and progress event before clearing level scratch memory. Run a bounded retrospective before starting the next level.

Support grids smaller than 64 by 64 and observations containing multiple frames.

## 5.3 Exact transition differences

For compatible canonical grids, compute:

- Changed-cell mask.
- Changed-cell count and fraction.
- Bounding box and connected regions of visible change.
- Per-color counts before and after.
- Per-color additions and removals.
- Legal-action-set changes.
- Object-independent structural features such as translations and recoloring candidates.
- Classification as no_visible_change, local visible change, global visible change, or scene boundary.

If shapes differ, retain both complete grids and mark a scene boundary rather than padding silently.

No visible change is an observation, not proof that the environment's latent state is unchanged.

## 5.4 Lightweight click candidates

ACTION6 candidate generation must not wait for advanced correspondence. Generate early candidates from:

- Centroids and interior points of simple same-color regions.
- Small isolated or button-like regions.
- Rare colors.
- Newly changed regions.
- Endpoints and intersections of thin structures.
- Centers of unexplored spatial regions when object-derived candidates are exhausted.

Deduplicate coordinates, clamp them to actual grid bounds, and retain score terms:

    novelty
    + rare-color evidence
    + recent visible-change relevance
    + simple geometric salience
    + expected hypothesis discrimination
    - contextual no-visible-change penalty
    - repeated-state penalty
    - irreversible-risk penalty

Treat these initially as ordered features or simple configurable weights.

## 5.5 Conditional advanced components

Four-connected per-color components may be used as a lightweight feature in E2, but sophisticated cross-frame correspondence belongs to E7.

Enter E7 only after a closed-loop failure is attributed to unstable identity tracking and simpler delta or region features cannot resolve it.

If enabled, component records include color, area, box, centroid, normalized shape mask, border contact, background likelihood, neighborhood features, visible-change membership, and uncertainty. Repeated identical components must remain ambiguous candidates rather than receive invented identities.

Use exact unambiguous matches first. Add greedy or assignment-based correspondence only when it improves a measured decision.

## 5.6 Lossless frame and transition evidence

Store each unique frame or frame sequence once using a stable content digest and compact binary representation. Transition records reference frame IDs rather than duplicating pre- and post-action JSON arrays.

Every TransitionRecord contains:

    game, level, attempt, step
    pre-observation ID and canonical frame ID
    legal action IDs
    submitted ActionDecision
    selection source
    expected effect and stop condition
    post-observation ID and canonical frame ID
    exact and structural visible differences
    game-state and levels-completed changes
    queue continuation or invalidation reason
    inference, queue, token, timeout, and fallback telemetry

Competition frames do not expose live official score. Attach scorecard results only after the scorecard closes.

Set measured RAM and disk ceilings before the candidate freeze. If projected lossless recording exceeds them, improve representation or compression before the run; never silently discard evidence while claiming losslessness.

## 5.7 Compact working memory

Maintain three isolated stores per game:

1. **Durable memory:** verified mechanics, cross-level invariants, hazards, reusable procedures, and important counterexamples.
2. **Level scratch:** current objects, subgoal, active hypotheses, candidate plan, unresolved observations, and cheapest useful probe.
3. **Rejected-hypothesis ledger:** rejected claim, contradiction evidence, scope, and reconsideration conditions.

Apply explicit item, token, and byte limits. Memory statements reference transition IDs. Model summaries may append revisions but may not edit or replace exact evidence.

## 5.8 Bounded hypotheses

Keep two to four active hypotheses. Each contains:

- Claim and scope.
- Supporting and contradicting transition IDs.
- Predictions for candidate actions.
- Cheapest distinguishing probe.
- Expected progress, reversibility, and risk.
- Complexity and exception count.
- Status: tentative, supported, verified-for-plan, contradicted, or retired.

Rank hypotheses by transparent ordered evidence:

    predictive coverage
    verified predictions
    expected progress
    contradictions
    complexity
    exception count

Rank probes separately:

    expected hypothesis reduction
    expected progress
    action cost
    contextual no-visible-change likelihood
    irreversible risk

Do not tune numeric weights on one exposed game.

## 5.9 Deterministic controller modes

| Mode | Entry trigger | Behavior | Exit trigger |
|---|---|---|---|
| Bootstrap | No active observation or start required | Legal start/reset and initial evidence | Active state observed |
| Normal | Leading explanation and reversible action | One model call and one action | Prediction result or novelty |
| Fast | Verified queue and prior prediction matched | Continue with minimal model work | Queue end or mismatch |
| Deep | Competing hypotheses or irreversible decision | Retrieve evidence and use bounded deep request | Probe or plan selected |
| Recovery | Visible repetition, contradiction, parse failure, death, or stagnation | Cancel queue and choose safe novel evidence | Informative transition |
| Exhausted | Model or per-game compute allocation spent | Deterministic fallback only | Terminal state |
| Done | Win or hard global deadline | Stop cleanly | None |

Only deterministic evidence, risk, prediction accuracy, and remaining budgets select a controller mode. The model may label its action intent, but it does not select controller mode.

## 5.10 Model contract

The normal request contains only budgeted evidence:

- Current rendered image if supported and affordable.
- Exact grid or compact grid encoding.
- Current delta and lightweight region table.
- Legal action IDs and true coordinate bounds.
- Durable memory, level scratch, and active hypotheses.
- Retrieved transitions relevant to the current decision.
- Remaining action, call, token, and wall-clock allocation.

Require a strict structured response:

    {
      "state_update": "concise revisable interpretation or null",
      "hypothesis_updates": [],
      "intent": "probe",
      "subgoal": "determine whether ACTION1 moves region r3",
      "actions": [
        {
          "action": "ACTION1",
          "data": null,
          "expected_effect": {
            "kind": "translation",
            "target": "r3",
            "direction": "up"
          },
          "stop_if": {
            "prediction_mismatch": true
          }
        }
      ],
      "memory_update": null
    }

Validation order:

1. Parse JSON or native structured output.
2. Repair syntax or schema representation only.
3. Reject ambiguous or unsupported fields.
4. Validate action IDs against the current legal set.
5. Validate coordinate types and actual bounds.
6. Enforce controller-selected queue length.
7. Require observable predictions for queued actions.
8. Convert to immutable ActionDecision values.
9. Fall back deterministically if validation fails.

Repair must never invent or substitute an action.

## 5.11 Contextual fallback policy

The fallback prioritizes survival and useful evidence:

1. Handle required start or bounded level reset.
2. Exclude illegal actions.
3. Penalize, but do not permanently blacklist, context-matched no-visible-change actions.
4. Prefer legal actions not tried in the current context.
5. For ACTION6, choose the highest-ranked untried candidate.
6. Penalize actions associated with repeated immediate death.
7. Permit explicit retry when context or hypotheses change.
8. Break ties with the per-agent seeded RNG and record the tie-break.

The fallback runs independently with inference disabled.

## 5.12 Prediction-checked execution

- Use one action in Bootstrap, Deep, and Recovery.
- Use one action during uncertain Normal operation.
- Permit up to four queued actions only when relevant dynamics are verified and every action has a distinct prediction.
- Compare every real transition with the queued expectation before the next queued action.
- Cancel on mismatched status, legal actions, persistent-region structure, visible changed region, progress event, or expected/no-expected visible change.
- Preserve the level-completing action and run a retrospective before resetting scratch memory.
- Do not treat accidental level completion as proof of the proposed mechanic.

Begin with outcome and structural checks. Require exact next-grid prediction only after demonstrated deterministic transitions and only when it improves action selection.

## 5.13 Shared inference and global allocation

E1 must provide a thread-safe singleton model loader. Every MyAgent obtains a lightweight client to the same bounded service.

The minimal E1 service provides:

- Exactly-once model initialization.
- Per-game request isolation.
- At most one queued request per game.
- Serialized correctness before batching.
- Request deadline, cancellation, and exception containment.
- Queue wait, service time, token, memory, timeout, and fallback telemetry.

Phase 4 adds:

- Guaranteed initial allocation per game.
- A shared discretionary call pool.
- Aging or starvation bounds.
- Priority based on estimated marginal official-score value, progress, later-level opportunity, uncertainty, and remaining cost.
- Optional dynamic batching after serialized correctness.
- Deadline degradation to shorter context, reduced reasoning, a measured fallback model, or deterministic policy.

Batching is accepted only on sustained concurrent throughput, closed-loop outcomes, and deadline behavior—not peak tokens per second alone.

## 5.14 Conditional executable models and search

Enter E8 only when:

- A compact state representation exists.
- Relevant transitions have high structural prediction accuracy.
- A failure is attributed to planning rather than perception or incorrect mechanics.
- The plan exceeds the reliable direct-reasoning horizon.
- The expected benefit fits the remaining runtime and complexity budget.

Use BFS for small unweighted deterministic spaces. Use A* only with a defensible heuristic. Replan after every real action. A generated simulator never bypasses real-transition verification.

# 6. Sequential implementation schedule

## Phase 0 — Reproducibility and action correctness

**Dates:** September 4–7

Deliverables:

- Version-control initialization and ignore audit.
- Pinned SDK/framework compatibility record.
- Exposure inventory and seeded development, diagnostic, H1, and H2 manifests.
- Three deployment manifests.
- Multi-file notebook packaging skeleton.
- Frozen ActionDecision and request-local submission override.
- Repaired legal deterministic fallback.
- Exact action, reset, retry, and deadline handling.
- Sequential and 110-client synthetic race tests.
- First valid E0 Kaggle submission.

Exit gate:

- Zero invalid actions and zero uncaught agent exceptions in three complete development runs.
- Zero coordinate or reasoning crossover in the 110-client race test.
- Exact configured action limits.
- Identical deterministic traces for the same seed.
- A clean checkout builds and runs the E0 notebook without internet.

## Phase 1 — Shared local-model vertical slice

**Dates:** September 8–11

Deliverables:

- Primary model candidates profiled on the actual target accelerator.
- Exactly-once singleton model loading.
- Serialized bounded request service used by all game agents.
- Minimal prompt with current evidence and legal actions.
- Strict response schema and immutable decision conversion.
- Offline weights, tokenizer, wheels, and native libraries attached through manifests.
- Completed runtime and service-budget worksheet.
- 110-client mixed normal/deep throughput test.
- Closed-loop E1 comparison with E0.

Exit gate:

- E1 beats E0 under the treatment-acceptance rule.
- Exactly one primary model instance exists under concurrent construction and requests.
- Full-run projection fits every declared time, VRAM, RAM, disk, artifact, and license ceiling.
- The selected degradation strategy is measured rather than assumed.

If E1 fails, reduce model size, context, reasoning budget, or call frequency. Do not add elaborate perception or planning to an infeasible inference stack.

## Phase 2 — Exact evidence and compact continuity

**Dates:** September 12–15

Deliverables:

- Stable canonical observations and exact visible differences.
- Content-addressed compact frame store.
- Transition records referencing frames without duplication.
- Lightweight click candidates.
- Durable memory, level scratch, and rejected-hypothesis ledger.
- Level-boundary retrospective.
- Context-scoped no-visible-change handling.
- E2 through E4 ablations.

Exit gate:

- Evidence is exactly recoverable within measured storage ceilings.
- E2 through E4 pass the treatment-acceptance rule on development and diagnostic sets.
- Rejected hypotheses are not repeatedly proposed without new evidence.

Do not implement sophisticated component correspondence in this phase unless it has already passed the E7 entry condition.

## Phase 3 — Hypotheses and guarded plans

**Dates:** September 16–19

Deliverables:

- Two-to-four-hypothesis state with evidence references.
- Discriminating one-action probes.
- Outcome and structural prediction checks.
- One-to-four-action verified queues.
- Normal, Fast, Deep, Recovery, Exhausted, and Done behavior.
- Queue-break and hypothesis-revision telemetry.
- E5 and E6 comparisons.

Exit gate:

- E5 and E6 pass the treatment-acceptance rule.
- Incorrect queues stop after one mismatching action.
- Accidental early-level wins do not become verified mechanics without supporting evidence.
- H1 is run once only after the architecture is stable enough to justify the gate.

## Phase 4 — Competition scheduler and load behavior

**Dates:** September 20–23

Deliverables:

- Initial per-game service floor and discretionary call pool.
- Starvation bounds and marginal-value prioritization.
- Deadline-aware degradation.
- Optional batching experiment.
- Concurrent public-game subset runner.
- 110-client synthetic service and failure-injection test.
- Per-game and global resource report.

Exit gate:

- No game thread crashes or remains indefinitely starved.
- Model failures degrade to legal deterministic decisions.
- Measured aggregate service throughput supports the declared call budget.
- Full-run projection remains below 7.65 hours.

## Phase 5 — Evidence-driven optional work

**Dates:** September 24–26

This phase may be skipped.

Eligible treatments:

- Advanced component identity and correspondence.
- Partial executable transition functions.
- Structural replay.
- BFS or A* over a verified compact model.
- A specialist visual or code-reasoning request.

Exit gate:

- The treatment passes the policy acceptance rule.
- Closed-loop completion or action efficiency justifies runtime and complexity.
- Offline simulator, tracking, or visual accuracy alone is insufficient.

## Phase 6 — Candidate selection and freeze

**Dates:** September 27–28

Deliverables:

- Conservative and higher-reasoning candidates with explicit risk profiles.
- One H2 final-candidate evaluation.
- Offline notebook with source, dependency, model, configuration, and license hashes.
- Runtime, RAM, VRAM, disk, queue, and log profile.
- Candidate freeze by September 28.

Exit gate:

- Clean checkout reproduces the selected artifact.
- Competition-like run completes within the safety margin.
- Accepted policy components have archived comparisons.
- H2 remains excluded from further tuning.

## Phase 7 — Release and submission verification

**Dates:** September 29–30

Use this window only for:

- Notebook reruns and infrastructure recovery.
- Artifact and mount-path verification.
- Public notebook and repository publication.
- Open-source license and third-party notice verification.
- Reproduction-instruction verification.
- Final milestone submission.

Do not add unmeasured algorithms after the freeze.

The milestone publication and submission deadline is September 30 at 11:59 PM UTC, corresponding to October 1 at 7:59 AM China Standard Time.

# 7. Evaluation and tests

## 7.1 Unit tests

Required groups:

- Stable seed derivation across processes.
- Integer available-action normalization.
- Exact action-cap semantics.
- Immutable ActionDecision validation.
- No GameAction mutation in production paths.
- Concurrent unique ACTION6 coordinates and reasoning.
- Grid hash determinism.
- Difference handling for no visible change, movement, recoloring, creation, deletion, and shape changes.
- Level-boundary evidence retention.
- Click candidates on small, rectangular, and maximum-size grids.
- Content-addressed deduplication and exact recovery.
- Context-scoped no-visible-change penalties and permitted retries.
- Strict response parsing for missing, extra, malformed, ambiguous, and illegal actions.
- Queue cancellation for every material mismatch.
- Stable fallback traces under fixed seeds.
- Runtime and call-budget accounting.

## 7.2 Integration tests

- Model unavailable at startup.
- Exactly-once model initialization under concurrent agent creation.
- Model timeout and cancellation during active play.
- Invalid structured output and out-of-range coordinates.
- Level transition during a queued plan.
- GAME_OVER, reset budget, exhausted mode, and clean termination.
- 110 simultaneous synthetic inference clients.
- Per-game service floor, starvation bound, and discretionary prioritization.
- Primary-model degradation strategy.
- Global deadline exhaustion.
- Storage ceiling projection.
- Missing source, wheel, tokenizer, model, or license manifest entries.
- Clean-checkout offline notebook import and run.
- Concurrent public-game subset execution.

## 7.3 Closed-loop experiments

| Treatment | Primary comparison |
|---|---|
| E0 | Correct immutable fallback versus current random policy |
| E1 | Shared minimal local model versus E0 |
| E2 | Exact delta and lightweight click evidence versus current observation only |
| E3 | Compact durable/scratch memory versus bounded recent history |
| E4 | Exact retrieval and retrodiction versus summary-only context |
| E5 | Bounded hypotheses versus one unconstrained explanation |
| E6 | Prediction-checked queues versus one model call per action |
| E7 | Advanced component correspondence versus lightweight regions |
| E8 | Conditional executable model/search/specialist versus E6 or E7 |

Fixed trajectories may evaluate parsing, perception, storage, predictions, and latency. Policy acceptance requires repeated closed-loop rollouts on development and rotating diagnostic sets.

## 7.4 Holdout protocol

- Never use H1 or H2 for ordinary treatment acceptance.
- Run H1 only at the architecture gate.
- Run H2 only at candidate selection.
- Record configuration before opening either gate.
- Do not inspect source, frames, trajectories, or per-step explanations after the runs.
- Report aggregate results, all seeds, uncertainty, and failures.
- Never move a sealed environment into the development set during the competition.

## 7.5 Required metrics

### Competition outcomes

- Games completed.
- Weighted level-completion fraction.
- Levels completed.
- Actions per completed level.
- Actions before first progress.

### Exploration and reasoning

- Invalid, no-visible-change, repeated, reset, and death rates.
- Schema validity and deterministic fallback rate.
- Hypothesis contradiction and revision latency.
- Outcome and structural prediction accuracy.
- Queue length, actions per model call, and queue-break rate.
- Level-to-level transfer and repeated rejected hypotheses.

### Compute and deployment

- Cold-load and first-request time.
- Completed requests per wall-clock second under concurrency.
- Normal and deep latency distributions.
- Queue wait and batch-formation delay.
- Input/output tokens and tokens per game.
- Guaranteed and discretionary calls consumed per game.
- Peak RAM, VRAM, disk, and total runtime.
- Artifact sizes, hashes, licenses, and mount-path checks.

### Reliability and generalization

- Uncaught exceptions, timed-out games, starved clients, and missing scorecard entries.
- Cross-game coordinate or reasoning contamination.
- Development, diagnostic, H1, H2, and leaderboard gaps.

## 7.6 Run artifact

Archive together:

- Source commit and dirty-worktree status.
- Source, dependency, and model manifests.
- Model, tokenizer, prompt, and configuration hashes.
- Accelerator and runtime versions.
- Predeclared seeds and data partitions.
- Budget worksheet.
- Event evidence and machine-readable summary.
- Closed scorecard when available.

# 8. Merge and escalation gates

Accept an infrastructure or reliability change when it:

- Eliminates a reproduced failure;
- Preserves policy outcomes within a threshold declared before the test; and
- Remains within resource ceilings.

Accept a policy, model, perception, memory, or planning change only when it passes Section 2.3 on development and diagnostic sets.

Reject or defer a change when:

- Its only gain occurs on one exposed game.
- It depends on a best seed or selective rerun.
- It improves only an offline proxy.
- It raises the projected run above 7.65 hours.
- It reduces the guaranteed service floor below the declared minimum.
- It adds a model, framework, simulator, role, or tracking system without a measured decision benefit.
- Its output cannot be validated or safely bypassed.
- It requires H1 or H2 for routine tuning.

# 9. Principal risks and controls

| Risk | Control |
|---|---|
| Shared GameAction data crosses threads | Frozen ActionDecision, direct request-local submission, 110-client race test |
| Model instances multiply across agents | Exactly-once singleton established in E1 |
| Serialized inference misses the deadline | Aggregate throughput budget, service floor, call pool, degradation |
| Strict fairness wastes compute on hopeless games | Initial floor followed by marginal-value priority with starvation bound |
| Model or wheels are absent offline | Separate source, dependency, and model manifests |
| Fallback model exceeds VRAM or loads too late | Measure and select one explicit degradation mode |
| Plan exceeds one-developer capacity | Sequential E0–E6 path; E7/E8 optional |
| Public-game overfitting | Exposure log, diagnostic rotation, H1/H2 sealed gates, no game-ID policy |
| Local tests miss Kaggle concurrency | Concurrent public runner plus 110-client synthetic harness |
| Current directory cannot reproduce | Initialize version control and clean-checkout test in Phase 0 |
| Evidence duplicates frames | Content-addressed compact store with transition references |
| Live logs claim unavailable score | Record progress during play and attach scorecard after close |
| Visible no-change is mistaken for latent no-op | Context-scoped decaying penalty and explicit retry |
| Winning action is lost at a scene boundary | Preserve causal transition and run level retrospective |
| Model hallucination corrupts memory | Code-owned evidence with transition references |
| Search uses a false world model | Prediction gate and real-action replanning |
| Milestone entry is technically valid but prize-ineligible | Explicit public release, license, notices, and reproduction gate |

# 10. Next 72 hours

Execute in this order:

1. Initialize version control and verify ignored secrets and generated artifacts.
2. Create the exposure inventory and select development, diagnostic, H1, and H2 partitions before inspecting more games.
3. Add the source, dependency, and model manifest schemas.
4. Extend the notebook builder for an explicit multi-file source manifest and manifest validation.
5. Implement frozen ActionDecision and the request-local environment boundary.
6. Remove global RNG, wall-clock/hash seeding, game-ID logic, and static action enumeration.
7. Add exact action caps, lifecycle guards, bounded coordinates, and top-level exception fallback.
8. Add the 110-client action-isolation race test.
9. Implement stable canonical hashes, minimal exact deltas, and content-addressed frame references.
10. Produce and archive three deterministic E0 runs.
11. Build the smallest offline singleton-model smoke notebook.
12. Measure cold load, sustained concurrent service throughput, VRAM, and structured-output validity.

Do not begin advanced correspondence, search, executable world models, learned perception, or specialist roles during this window.

# 11. Definition of done

Plan 3 is implemented when:

- The repository reproduces from a clean checkout without secrets or downloaded development games.
- The production policy contains no public-game identifiers or solution tables.
- No production path calls GameAction.set_data().
- Every environment action is legal, request-local, bounded, and recorded with a reason.
- The configured action cap has exact tested semantics.
- A 110-client race test shows no coordinate or reasoning crossover.
- Exactly one primary model instance serves every game.
- The measured service budget, not isolated latency, supports the full-run projection.
- Source, dependencies, native libraries, model assets, tokenizer, paths, hashes, and licenses have separate validated manifests.
- Every observation and transition is recoverable without duplicating adjacent frame arrays.
- During play, records distinguish visible progress from unavailable official score.
- No-visible-change evidence is contextual and retryable.
- Level-completing actions remain available to cross-level retrospection.
- Model-facing state is compact, bounded, and linked to exact evidence.
- Model output cannot bypass action, coordinate, queue, model-call, token, runtime, or terminal-state guards.
- Incorrect predictions stop queued execution after one mismatch.
- Model or infrastructure failure produces a legal deterministic decision rather than a crashed thread.
- E1 beats E0 under the predeclared outcome protocol.
- H1 and H2 are used only at their named gates.
- The same artifact passes unit, integration, concurrent-load, clean-checkout, offline-notebook, and closed-loop gates.
- The final candidate finishes within the declared resource margins.
- Milestone source and reproduction materials are public under a compatible open-source license before the prize deadline, if milestone eligibility is pursued.

# 12. Relationship to the other plans

- ARC-AGI-3_Project_Plan.md remains the active strategic and evidence-driven plan.
- ARC-AGI-3_Project_Plan_3.md is the current repository-specific execution proposal.
- ARC-AGI-3_Project_Plan_2.md is the immediate predecessor and remains unchanged for traceability.
- ARC-AGI-3_Preliminary_Project_Plan.md and the older DOCX remain historical records.

# 13. Primary references

- Kaggle competition: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3
- ARC-AGI-3 documentation: https://docs.arcprize.org/
- Scoring methodology: https://docs.arcprize.org/methodology
- Competition mode: https://docs.arcprize.org/toolkit/competition_mode
- Official toolkit: https://github.com/arcprize/ARC-AGI
- Official agent framework: https://github.com/arcprize/ARC-AGI-3-Agents
- Milestone 1 review: https://arcprize.org/blog/arc-prize-2026-milestone-1
