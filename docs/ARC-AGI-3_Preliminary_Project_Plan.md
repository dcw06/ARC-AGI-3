---
title: "ARC Prize 2026 — ARC-AGI-3"
subtitle: "Preliminary Project Plan"
author: "Project Team"
date: "4 September 2026"
---

# Document purpose

This document defines a preliminary engineering and research plan for building a competitive ARC-AGI-3 Kaggle agent. It converts the competition requirements into a staged program of work, measurable decision gates, and concrete deliverables through the final submission deadline.

The plan is intentionally provisional. Architecture choices will be revised when experiments provide evidence, but the evaluation discipline, hidden-set generalization requirement, and submission constraints should remain fixed.

# 1. Executive summary

ARC-AGI-3 tests whether an agent can discover the rules and goals of unfamiliar, interactive, turn-based environments and solve their sequential levels with human-like action efficiency. The agent receives color-grid observations of up to 64 × 64 cells, a small legal-action set, and sparse progress signals. It receives no instructions describing the mechanics or objective.

The proposed solution is a model-first hybrid agent built around six capabilities:

1. The strongest local multimodal reasoning model that satisfies Kaggle's runtime, memory, packaging, and license constraints.
2. Deterministic frame normalization, exact change analysis, and compact object candidates supplied to the model as evidence.
3. Persistent but compressed per-environment reflection and episodic memory.
4. A bounded beam of explicit hypotheses about mechanics, goals, and causal transitions.
5. Adaptive allocation between reasoning, discriminating interaction, short planning, and execution.
6. Deterministic legal-action, runtime, parsing, and failure guards with a model-independent survival path.

The project will establish a valid deterministic submission baseline and then build a minimal local-model vertical slice immediately. Symbolic and executable mechanisms will be added incrementally only when closed-loop ablations show that they improve completion or action efficiency enough to justify their runtime. A simple deterministic policy remains the operational fallback, but building a comprehensive symbolic solver is not a prerequisite for model integration.

The immediate target is the September 30 milestone. The final architecture will then be improved for robustness, compute efficiency, and private-set generalization ahead of the November 2 final deadline.

# 2. Objectives and success criteria

## 2.1 Primary objective

Develop a reproducible, open-source agent that achieves the strongest possible private-leaderboard ARC-AGI-3 score within Kaggle's nine-hour, no-internet execution environment.

## 2.2 Secondary objectives

- Build reusable infrastructure for interactive reasoning research.
- Produce interpretable trajectories showing how hypotheses and plans evolve.
- Minimize dependence on public-game-specific mechanics.
- Keep the solution reproducible under Kaggle's hidden competition rerun.
- Preserve reusable deterministic preprocessing and fallback infrastructure around a model-first competitive agent.

## 2.3 Success tiers

| Tier | Outcome | Evidence required |
|---|---|---|
| Foundation | Valid end-to-end Kaggle submission | Notebook completes, produces the required submission file, and records all games without infrastructure failure |
| Baseline | Non-random general behavior | Zero invalid actions, low no-op rate, loop detection, and reproducible trajectories |
| Functional | General level completion | Completes tutorial and non-tutorial levels across multiple held-out public games without game-ID logic |
| Competitive | Strong general performance | Sustained closed-loop improvement on sealed and diagnostic environments, followed by sparse confirming leaderboard evidence |
| Prize-ready | Reproducible and licensable | Source, model weights, dependencies, instructions, and final notebook satisfy competition eligibility requirements |

Leaderboard score will not be the only success measure. Levels completed, action efficiency, invalid-action rate, compute cost, and cross-game generalization will be tracked separately.

# 3. Fixed constraints and planning assumptions

## 3.1 Benchmark constraints

- Each environment is encountered without instructions.
- Observations are one or more frames of up to 64 × 64 cells using a 16-color palette.
- Each environment exposes a changing subset of seven numbered actions plus reset.
- `ACTION6` requires an `(x, y)` coordinate from 0 through 63.
- Environments contain sequential levels; later levels generally combine mechanics introduced earlier.
- Per-level RHAE is based on `(human_baseline_actions / agent_actions)^2`, with the current per-level cap of 1.15.
- Later levels receive larger weights, and a game cannot receive full completion credit unless all levels are completed.
- The 110 private environments are unseen and separate from the 25 public environments; generalization beyond public mechanics is therefore a core planning assumption.

## 3.2 Kaggle constraints

- Maximum CPU or GPU notebook runtime: nine hours.
- Internet access is disabled during evaluation.
- Model weights and nonstandard dependencies must be attached or packaged in advance.
- The gateway automatically generates the competition submission file.
- Competition mode allows a single scorecard and one creation of each environment.
- All evaluation environments contribute to the score, including untouched environments.
- Prize eligibility requires an open-source, reproducible solution and compatible component licenses.

## 3.3 Project assumptions

- Local development is on Apple Silicon; CUDA behavior must be validated on Kaggle.
- The existing random starter is plumbing-only and will not be retained as the real policy.
- Public environment source code may be inspected for engine understanding, but production behavior must not depend on public IDs or implementation details. Exposure to public games must be logged so a genuinely sealed internal holdout can be preserved.
- The strongest feasible local model, rather than the strongest model in isolation, will be selected using closed-loop score, latency, memory, packaging, and license evidence.
- A shared inference service will be required if a large local model is used because Kaggle starts multiple game agents concurrently.
- Deterministic preprocessing and fallback behavior must remain functional when model loading, inference, parsing, or queueing fails.
- Architecture changes will be accepted only when supported by per-component measurements or clear failure analysis.

# 4. Proposed system architecture

## 4.1 High-level flow

```text
Frame sequence
    ├── deterministic normalizer, delta analysis, and object candidates
    └── raw grid and selected rendered views
                         ↓
             Local reasoning/VLM policy
                         ↓
          Current understanding and short plan
               ┌─────────┴─────────┐
               ↓                   ↓
      Reflection memory      Hypothesis beam
                              H1 / H2 / H3
                                    ↓
                     Transition replay checker
               ┌──────────────┬──────────────┐
               ↓              ↓              ↓
          Confident       Uncertain      Contradicted
               ↓              ↓              ↓
        Reuse/execute   Cheapest probe   Rebuild/simplify
               └──────────────┴──────────────┘
                              ↓
                 Reason/act budget controller
                              ↓
               Legal-action and runtime guard
                              ↓
                      Environment action
                              ↓
                 Validate and update memory
```

The model consumes several complementary representations rather than becoming the only perception path. Exact deltas, stable-frame selection, legal actions, and state fingerprints are computed deterministically; the model receives them alongside raw grids, selected images, and compressed history. It proposes explanations, experiments, plans, and, when useful, partial executable transition models. Its output never bypasses schema validation, budget checks, or action guards.

## 4.2 Perception layer

Responsibilities:

- Normalize frame sequences and identify the current stable frame.
- Compute exact cell-level deltas after every action.
- Extract connected components and background candidates.
- Represent each component by color, area, bounding box, centroid, shape mask, symmetry, holes, and relationships.
- Track object movement, creation, deletion, recoloring, collision, and occlusion.
- Detect camera or scene transitions that should not be interpreted as ordinary object movement.
- Generate compact visual crops for the local vision-language or multimodal reasoning model.
- Preserve an invariant evidence summary containing the full changed-cell mask or hash, game state, level count, available-action changes, object counts, and color histograms.

Initial deterministic preprocessing should use NumPy only. Learned object-centric perception, including Slot Attention, should be considered only if controlled failures show that connected components and exact deltas cannot handle cases such as touching same-color objects, occlusion, disconnected object parts, or identity across scene changes.

## 4.3 Per-environment memory

Each `MyAgent` instance should maintain isolated memory containing:

- Current and previous stable states.
- Action history and resulting effects.
- Completed-level count and detected level boundaries.
- Known ineffective state-action pairs.
- Object identities and trajectories.
- Candidate mechanics and their supporting or contradicting evidence.
- Current subgoal and plan.
- State fingerprints and graph edges.
- Remaining action and time budgets.

Full raw frames should be retained only when needed for replay or selected evidence. Long histories should be compressed into structured summaries to control RAM, disk, and model context.

## 4.4 Exploration policy

Exploration should maximize expected information while controlling risk. The initial policy should:

- Use only currently available actions.
- Prefer reversible or low-risk probes when uncertainty is high.
- Avoid repeating an action that produced no change in the same state.
- For click environments, prioritize object centroids, rare colors, small button-like shapes, endpoints, intersections, and recently changed regions.
- Compare outcomes against explicit predictions.
- Escalate from local probes to broader exploration only when hypotheses remain indistinguishable.
- Preserve discovered execution sequences for later levels.
- Reuse known mechanics cheaply, but validate the first predicted transition in each new or changed level before committing to a longer plan.

The agent should use an initially rule-based adaptive reasoning controller rather than trusting uncalibrated model confidence. Observable triggers determine the reasoning tier:

- **Fast:** a validated plan is available and the previous prediction matched.
- **Normal:** one model pass is sufficient for an ordinary reversible decision.
- **Deep:** hypotheses disagree, an action is difficult to reverse, or a high-value plan requires simulation.
- **Recovery:** a prediction is contradicted, a no-op or loop repeats, parsing fails, or a game reset occurs.

The controller selects a reasoning tier `r` and legal action `a` using the following conceptual utility:

`U_t(r, a) = E[score progress] + lambda_t * information gain - mu_t * failure risk - kappa_t * action cost - eta_t * reasoning time`

The choice remains subject to the remaining action and wall-clock budgets. The weights may change as those budgets shrink. Environment-action cost and compute cost must be tracked separately because only the former directly affects RHAE while the latter determines whether the notebook finishes. The first implementation should use observable rule-based proxies for each term rather than assuming that model-generated probabilities are calibrated.

## 4.5 Hypothesis and world-model layer

The agent should maintain a bounded beam of two to four candidate explanations rather than committing to the first plausible story. A hypothesis record should include:

- Proposed objects and roles.
- Transition rule.
- Candidate goal or progress condition.
- Predicted outcome for candidate actions.
- Supporting observations.
- Contradicting observations.
- Confidence and complexity cost.
- The cheapest legal action expected to distinguish it from competing hypotheses.

Hypotheses should be ranked by predictive consistency, simplicity, expected progress, and the cost of obtaining more evidence. When execution adds value, a hypothesis may be converted into a partial Python transition function; it does not need to simulate the entire environment. All executable hypotheses must be checked against recorded transitions before they are used for planning.

Replay checking has three escalating levels:

1. **Outcome verification:** progress, death, level transition, and legal-action changes.
2. **Structural verification:** changed mask, object motion, color/count changes, and explicitly modeled relations.
3. **Exact verification:** equality of canonical stable frames when the environment is deterministic and exact reconstruction is worth the compute.

Structural verification is the default. Exact verification is conditional because animation, irrelevant pixels, stochasticity, and hidden state can make full-frame reconstruction expensive or misleading.

## 4.6 Planning and execution

Once useful dynamics are known, the agent should switch from exploration to execution. Milestone planning is deliberately short-horizon and may include:

- Graph search over observed states.
- Breadth-first or A* search only for demonstrably small deterministic state spaces.
- Model-predictive control over a small number of candidate action sequences.
- Program execution for discrete transformations.
- A short action queue invalidated immediately when an observation differs from prediction.

Plans should optimize expected level completion first and action efficiency second. A theoretically short plan that depends on a weak model should not outrank a slightly longer plan supported by stronger evidence.

## 4.7 Model-assisted reasoning

The primary comparison is an incremental treatment ladder rather than three independent architectures:

| Treatment | Added capability | Acceptance question |
|---|---|---|
| T0 — Model-first baseline | Deterministic preprocessing, strongest feasible local multimodal policy, structured reflection memory, legal/runtime guards, and short plans | Does it run closed-loop within the resource envelope and beat the deterministic fallback? |
| T1 — Bounded hypotheses | Two to four explicit hypotheses with predicted effects, contradictions, and discriminating probes | Does explicit uncertainty improve completion or reduce waste? |
| T2 — Partial executable hypotheses | Runnable transition functions only when execution helps | Does execution improve prediction or planning enough to pay for code generation and validation? |
| T3a — Structural replay verification | Outcome and structural checks against recorded transitions | Does routine verification prevent costly false plans? |
| T3b — Exact replay verification | Full canonical-frame reproduction in selected deterministic cases | Is the incremental benefit worth its compute? |
| T4 — Short model-based search | Simulate a small number of action sequences through validated models | Does search improve RHAE or later-level completion? |

Each treatment is an ablation over the previous one. T3b and T4 are conditional milestone features and should be deferred if they do not improve closed-loop score per unit of runtime. A textual-policy treatment must remain in the comparison because current ARC-AGI-3 evidence does not show that persistent executable models are universally superior.

Model-generated code must run behind a safety boundary with process isolation, strict wall-clock and memory limits, restricted imports or an AST allowlist, bounded output, a temporary working directory, and deterministic exception handling. Generated code must never modify the agent package, inference service, submission files, or credentials.

## 4.8 Shared inference and concurrency

The Kaggle framework creates multiple agent threads. A model must therefore be loaded once and shared safely. The design should include:

- A module-level model singleton.
- A bounded, thread-safe request queue.
- Optional dynamic batching.
- Per-game request priorities based on progress and remaining budget.
- Timeouts and a deterministic fallback policy.
- No mutable cross-game reasoning state.
- Safe handling of coordinate actions, whose SDK enum instances contain mutable payload data.

The initial capacity envelope is:

- Target no more than 85% of the nine-hour limit: 27,540 seconds.
- Simulate all 110 evaluation games during load testing.
- Use 80 actions per game as the provisional planning cap until score/runtime evidence supports another value.
- At 8,800 total actions, a worst-case design that invokes one serialized model call per action has only approximately 3.1 seconds of average service time per call before non-model overhead.
- Measure model calls per game, actions produced per call, generation tokens, inference latency, queue wait, starvation, and fallback rate.

This arithmetic is a planning envelope, not a claim that every game should consume 80 actions. The shared service should reduce model-call frequency through short validated action queues and cached mechanics while allocating deeper reasoning only to decisions where it is likely to change the outcome.

# 5. Engineering workstreams

## Workstream A — Environment and submission reliability

- Keep local and Kaggle entry points aligned.
- Initialize version control and pin Python, toolkit, framework commit, packages, model artifacts, and hashes.
- Decide immediately whether the milestone agent remains single-file or implement manifest-based multi-file notebook packaging before refactoring.
- Attach offline wheels and model weights correctly.
- Add preflight checks for imports, accelerator selection, disk paths, and credentials.
- Create sequential functional tests and a concurrent 110-game competition-load simulation.
- Make failure output concise and diagnostic.

## Workstream B — Perception and state representation

- Implement frame normalization, hashing, differencing, and connected components.
- Create stable object descriptors and relational features.
- Handle frame sequences and animations.
- Build visualization/debug outputs for trajectories.

## Workstream C — Exploration and memory

- Implement legal-action filtering and terminal-state behavior.
- Record state-action-effect triples.
- Add no-op suppression, loop detection, and undo awareness.
- Build click candidate generation and ranking.
- Preserve mechanics across sequential levels.

## Workstream D — Hypothesis formation and planning

- Define a bounded structured-hypothesis schema and competing-hypothesis update rules.
- Implement outcome, structural, and conditional exact replay checks.
- Add partial executable models and their isolated execution boundary.
- Add short state-graph search and reusable plan templates only for verified dynamics.
- Measure stratified prediction accuracy before spending actions on longer plans.

## Workstream E — Local-model and inference integration

- Establish a minimal model-driven closed-loop baseline early.
- Select the strongest feasible model based on closed-loop capability, license, VRAM, packaging, and inference speed.
- Define a strict structured-output protocol.
- Compare raw images, symbolic grids, object tables, and mixed representations.
- Implement shared serving, context compression, adaptive reasoning tiers, and failure recovery.
- Package all weights and runtime dependencies for offline Kaggle execution.

## Workstream F — Evaluation and experiment management

- Audit the three Milestone 1 systems and Rodionov's ablations at source level, recording representation, memory, planning, verification, context, model-call, concurrency, fallback, score, runtime, and license mechanisms.
- Establish environment-level development and holdout splits.
- Maintain a public-environment exposure log and seal the holdout before further inspection.
- Create repeatable runs with stable seeds.
- Store component-level and end-to-end metrics.
- Run ablations before accepting additional complexity.
- Evaluate policies through closed-loop rollouts; use fixed trajectories only for perception, prediction, parsing, and latency tests.
- Track sparse public-leaderboard submissions and their exact artifacts without treating leaderboard movement as the primary merge gate.

# 6. Evaluation strategy

## 6.1 Public-game protocol

Before further public-game inspection:

1. Create an exposure log identifying environments whose play, trajectories, or source have already been inspected; these become development environments.
2. Select at least five previously uninspected environments as a fixed sealed holdout using a recorded random seed.
3. Do not inspect sealed-holdout source code or use its individual failures for game-specific changes.
4. Maintain a separate rotating diagnostic set for ordinary iteration; rotating environments never regain sealed status.
5. Categorize development environments by action space and interaction style without encoding game-specific solutions.
6. Report development, diagnostic, sealed-holdout, and macro-average results separately.
7. Run stochastic components multiple times and report uncertainty rather than only the best seed.

The sealed holdout should be opened only at named architecture gates, not after every change. Public-leaderboard submissions are sparse confirmation tests and must not replace internal closed-loop evaluation.

## 6.2 Synthetic evaluation

Before Milestone 2, use small targeted engine environments only for unit, safety, and load testing:

- Navigation and collision.
- Click-object discovery.
- Object transformation and ordering.
- Hidden goal inference.
- Tool or key-like dependency chains without recognizable cultural symbols.
- Multi-stage mechanics introduced across levels.
- Distractors, irreversible errors, and deceptive no-op actions.

Broad procedural generation and meta-training are post-milestone work. Any later synthetic benchmark must separate not only random seeds but also mechanic combinations between development and holdout sets; otherwise it measures interpolation within the generator rather than generalization.

## 6.3 Required metrics

| Category | Metrics |
|---|---|
| Task progress | Games won, levels completed, weighted completion fraction |
| Action efficiency | Actions per level, local RHAE, actions before first progress |
| Exploration | Progress or hypothesis reduction per action, no-op ratio, repeated state-action pairs, reset count |
| Modeling | Outcome and structural prediction accuracy, changed-state versus unchanged-state accuracy, calibration, contradictions detected, falsification rate, revision latency |
| Reliability | Invalid actions, exceptions, timeouts, incomplete game threads |
| Compute | Model calls per game, actions per model call, tokens per call, inference and queue latency, peak RAM/VRAM, total runtime, fallback rate |
| Generalization | Development-holdout gap, synthetic-holdout gap, leaderboard variance |

## 6.4 Experiment acceptance rule

A change should be merged into the candidate agent only when it does at least one of the following without crossing a declared resource or reliability ceiling:

- Increases held-out levels completed.
- Improves action efficiency on already solved levels.
- Reduces failure or invalid-action rate.
- Reduces runtime or memory while preserving performance.
- Improves prediction accuracy or removes a documented failure mode.

Before the first measured baseline, the following provisional gates apply and may be tightened when distributions are known:

- Zero invalid actions and zero uncaught agent exceptions across three complete development-suite runs.
- Identical decision traces under a fixed seed for deterministic components; GPU/model outputs may use a documented tolerance when exact determinism is unavailable.
- No feature is accepted solely because it improves a single public game or one leaderboard submission.
- A score-improving feature may not increase projected full-run time above 7.65 hours or peak resources above the selected Kaggle machine limits.
- A compute optimization must preserve completed levels across repeated development runs and may not introduce a new sealed-holdout failure at an architecture gate.
- T1 through T4 are accepted only through closed-loop rollouts; fixed-trajectory gains alone are insufficient.

## 6.5 Milestone scope boundaries

The following are not required before September 30 unless earlier evidence identifies them as the cheapest remedy for a measured failure:

- Training DreamerV3- or MuZero-style neural world models.
- Test-time parameter training of the primary model.
- SOAR-style evolutionary fine-tuning or ADAS-style architecture search.
- Slot Attention or another learned object-segmentation system.
- Broad procedural benchmark generation.
- A general implementation of BFS, A*, model-predictive control, and program synthesis for every game type.

These methods remain in the post-milestone research backlog. Their principles may inform the system, but they must not displace the milestone's model baseline, evaluation loop, memory, guards, bounded hypotheses, and throughput work.

# 7. Preliminary schedule

## Phase 0 — Reproducible submission foundation

**Dates:** September 4–6

Deliverables:

- Initialize version control and pin the Python, toolkit, agent-framework, and package versions.
- Confirm the SDK, scoring, scorecard, reset, and Kaggle notebook lifecycle against the pinned versions.
- Accept the competition rules and configure the submission path now rather than near the entry deadline.
- Record public-game exposure and seal the internal holdout before further inspection.
- Download the public suite and remove public game-ID branches from the production policy.
- Replace global random state with stable per-agent state and deterministic legal fallback behavior.
- Add frame extraction, canonical-frame selection, hashing, state/action logging, and the first machine-readable report.
- Complete the first valid Kaggle submission using the fallback agent.

Exit gate: a clean checkout reproduces a valid local run and Kaggle submission; three development-suite runs contain no invalid actions or uncaught agent exceptions.

## Phase 1 — Minimal local-model vertical slice

**Dates:** September 7–10

Deliverables:

- Complete a source-level mechanism matrix for The Duck, Reki, Forge, and Rodionov's textual/executable/verification treatments; convert findings into an ablation backlog rather than copying systems wholesale.
- Select one primary model candidate and one smaller fallback candidate for early profiling.
- Provide raw grids, rendered frames, deterministic deltas, legal actions, and concise history to the model.
- Implement strict structured output, parsing repair, timeouts, and deterministic fallback.
- Measure closed-loop score, model calls, tokens, latency, RAM/VRAM, and packaging on actual Kaggle hardware.
- Confirm model and dependency licenses before further commitment.

Decision gate: select the strongest feasible baseline that can be packaged offline and projected to finish a 110-game run with at least 15% runtime margin. If no model meets the gate, reduce model size, call frequency, or context before adding agent complexity.

## Phase 2 — Memory, guards, and bounded reasoning

**Dates:** September 11–16

Deliverables:

- Connected components, click candidates, exact frame deltas, and stable state fingerprints.
- Concise reflection/episodic memory with bounded context and cross-level mechanic retention.
- Legal-action, no-op, dead-signature, repeated-state, cycle, reset, and deadline guards.
- Short one-to-four-action plans that are invalidated on any material prediction mismatch.
- A bounded two-to-four-hypothesis beam with predicted effects and cheapest discriminating probes.
- A rule-based fast/normal/deep/recovery reasoning controller.

Exit gate: T1 improves completed levels, reduces waste, or removes a documented failure relative to T0 in repeated closed-loop diagnostic runs without exceeding the resource envelope.

## Phase 3 — Transition-model ablations

**Dates:** September 17–21

Deliverables:

- Implement T2 partial executable transition hypotheses behind an isolated execution boundary.
- Implement T3a outcome and structural replay verification.
- Compare T0, T1, T2, and T3a through repeated closed-loop rollouts.
- Use fixed trajectories only for perception, prediction, parser, and latency diagnostics.
- Evaluate conditional T3b exact verification on a small deterministic subset without making it a required milestone feature.

Decision gate: retain only treatments with a defensible closed-loop gain per unit of runtime. Model strength, prompt/context changes, and architectural mechanisms must be reported separately so improvements are attributable.

## Phase 4 — Competition-load integration

**Dates:** September 22–25

Deliverables:

- Shared inference queue with backpressure, fairness, timeouts, and deterministic degradation.
- Concurrent 110-game load simulation rather than only sequential local evaluation.
- Final single-file or manifest-based multi-file notebook packaging, chosen consistently with the source architecture.
- Offline dependency/model bundle with artifact hashes.
- Full development-suite ablations plus a named sealed-holdout architecture gate.
- Kaggle runtime, queue, memory, VRAM, disk, and logging profile.

Exit gate: a competition-like run projects below 7.65 hours, no game thread starves or crashes, and model/infrastructure failures degrade to legal actions.

## Phase 5 — Candidate runs and milestone freeze

**Dates:** September 26–28

Deliverables:

- Produce two candidates with meaningfully different score/runtime risk profiles.
- Run full Kaggle reruns early enough to diagnose packaging or accelerator failures.
- Freeze the milestone candidate on September 28.
- Archive source, prompts, configuration, weights, dependency hashes, traces, and ablation evidence.

Exit gate: the frozen candidate completes a full Kaggle rerun and the public release artifact reproduces it from a clean checkout.

## Milestone 2 submission

**Deadline:** September 30, 11:59 PM UTC / October 1, 7:59 AM China Standard Time

Use September 29–30 only for release verification, queue delays, notebook failures, and final submission. Do not add unvalidated capabilities after the September 28 freeze.

## Phase 6 — Private-generalization improvements

**Dates:** October 1–12

Deliverables:

- Analyze milestone and leaderboard discrepancies.
- Expand synthetic environment diversity.
- Improve hypothesis revision and plan invalidation.
- Reduce dependence on public-game visual statistics.
- Add evidence-based adaptive routing and resource allocation.
- Evaluate T3b exact replay and T4 short model-based search where milestone evidence supports them.
- Investigate Dreamer/MuZero-inspired learned dynamics only as a separate research track with an explicit data and compute case.

## Phase 7 — Robustness and efficiency

**Dates:** October 13–22

Deliverables:

- Long-duration stress tests.
- Repeated long-duration concurrency and queue-fairness tests.
- Memory, disk, and logging reductions.
- Model quantization/batching optimization.
- Crash recovery and timeout fallbacks.
- Evaluate SOAR-style hindsight learning, test-time parameter adaptation, Slot Attention, or ADAS only against sealed evaluation and explicit overfitting controls.

Exit gate: repeated full runs complete without infrastructure failure or material score variance caused by the harness.

## Phase 8 — Final freeze and submission

**Dates:** October 23–November 2

Deliverables:

- Complete any team merger before October 26; competition rules should already have been accepted during Phase 0.
- Freeze dependencies, weights, source, configuration, and licenses.
- Produce two defensible final candidates with meaningfully different risk profiles.
- Re-run reproducibility and open-source audits.
- Select final submissions and archive all artifacts.

Final deadline: November 2, 11:59 PM UTC / November 3, 7:59 AM China Standard Time.

# 8. Immediate next 72 hours

1. Initialize version control and pin the toolkit, framework commit, Python environment, and current submission artifacts.
2. Create the public-game exposure log and select the sealed holdout from previously uninspected environments before further play or source inspection.
3. Download the remaining public environments without opening sealed-holdout source or trajectories.
4. Choose single-file milestone development or implement manifest-based multi-file packaging immediately; do not refactor beyond the notebook builder's packaging capability.
5. Implement legal-action filtering, correct `GAME_OVER` behavior, per-agent random state, and deterministic fallback.
6. Implement canonical-frame extraction, hashing, exact deltas, and a bounded per-game trajectory record.
7. Add no-op and repeated-state-action suppression.
8. Create machine-readable JSON and human-readable Markdown evaluation reports.
9. Run three deterministic development-suite baselines and archive their traces.
10. Complete the first valid Kaggle submission before beginning substantial model or planner work.
11. Prepare the smallest possible local-model notebook that proves offline weight loading, structured action output, and actual Kaggle inference latency.

# 9. Key risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Public-game or architecture-search overfitting | High | Critical | Exposure log, sealed holdout, sparse leaderboard use, targeted synthetic mechanics, no game-ID policies |
| Model too slow for 110 games | High | Critical | Early Kaggle profiling, explicit call/token budget, short action queues, shared serving, batching, adaptive calls, deterministic fallback |
| GPU or CUDA incompatibility | Medium | Critical | Early Kaggle smoke notebook, offline wheelhouse, pinned versions |
| Model becomes a single point of failure | Medium | Critical | Smaller fallback model where feasible, parsing repair, request timeouts, deterministic survival policy |
| Thread-safety or queue-starvation defects | High | High | Per-agent state isolation, concurrent 110-game tests, fair backpressure, serialized model service, coordinate-action protection |
| Context growth | High | High | Structured summaries, evidence retrieval, bounded raw-frame history |
| Invalid or wasteful actions | Medium | High | Dynamic legal-action guard, no-op memory, plan validation |
| Uncalibrated model confidence | High | High | Observable reasoning triggers, contradiction tests, calibration tracking, no reliance on self-reported confidence alone |
| Replay checker ignores inconvenient evidence | Medium | High | Invariant full-delta/state summary plus structural checks before model-selected relevant regions |
| Exact replay fails on animation or hidden state | Medium | Medium | Canonical stable frames, structural verification by default, exact verification only in demonstrated deterministic cases |
| Generated code hangs or mutates the submission | Medium | Critical | Process isolation, AST/import restrictions, time/memory/output limits, temporary workspace, deterministic fallback |
| Notebook packaging omissions | Medium | High | Manifest-based packaging and clean-room notebook tests |
| Dependency or framework drift | Medium | High | Pinned versions and commits, hashes, clean-checkout reproduction before every candidate freeze |
| Infrastructure timeout or queue delay | Medium | High | Early submissions, runtime margin, checkpoint-free deterministic restart behavior |
| Stochastic leaderboard variance | Medium | Medium | Stable seeds, multiple local runs, deterministic decoding where practical |
| Incompatible model/code license | Medium | Critical | License review before architecture commitment and release audit before prizes |
| Excessive framework complexity | Medium | Medium | Component ablations and a permanent simple fallback path |

# 10. Submission readiness checklist

## Technical

- Agent selects only currently available actions.
- Terminal and reset behavior is correct.
- No public game IDs or public solution tables affect production decisions.
- Deterministic preprocessing remains available independently of model inference.
- Model loads once and concurrent requests are controlled.
- A concurrent 110-game load test exercises queue fairness, deadline degradation, and shared mutable state.
- All custom source files are included in the generated notebook.
- All third-party packages and weights are available without internet.
- Peak runtime, RAM, VRAM, disk, and log output remain below safe limits.
- A full competition-like run finishes with at least 15% runtime margin.
- Failures fall back to a legal deterministic action instead of crashing a game thread.
- Generated code is isolated and cannot modify the agent, inference service, submission artifacts, or credentials.

## Evaluation

- The exposure log and fixed development/diagnostic/sealed splits are documented before further inspection.
- Baseline, ablations, and final candidate results are archived.
- Run-to-run variance is measured.
- Public leaderboard changes are compared with local held-out changes.
- Final candidates differ by a documented hypothesis, not only a random seed.
- Offline trajectory metrics are not used as substitutes for closed-loop policy evaluation.
- Changed and unchanged transition-prediction accuracy are reported separately.

## Reproducibility and eligibility

- Source code has an approved permissive license.
- Third-party code, models, and datasets have compatible licenses.
- Exact package and model versions are recorded.
- Build and submission instructions work from a clean checkout.
- No credentials, tokens, or private data appear in the source or notebook.
- Required public notebook/source release is prepared before the relevant prize deadline.

# 11. Decision principles

- Prefer measured generalization over public-game perfection.
- Begin with the strongest model that satisfies the measured resource envelope, not the strongest model in isolation.
- Keep deterministic perception evidence and a legal survival path independent of the model.
- Prefer explicit prediction and verification over unconstrained model confidence.
- Prefer structural verification routinely and exact replay only when the environment and expected value justify it.
- Prefer reversible information-gathering actions under uncertainty.
- Allocate reasoning using observable contradiction, risk, novelty, and deadline signals rather than self-reported confidence alone.
- Reuse learned mechanics across levels, but validate them on the first materially new transition.
- Preserve simple fallbacks for every learned or model-dependent component.
- Treat runtime, action budget, and context as jointly constrained resources.
- Introduce complexity only when it addresses a documented failure mode.
- Freeze submission candidates early enough to survive Kaggle infrastructure delays.

# 12. Reference material

- Kaggle competition: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3
- ARC-AGI-3 documentation: https://docs.arcprize.org/
- Technical report: https://arcprize.org/media/ARC_AGI_3_Technical_Report.pdf
- Official toolkit: https://github.com/arcprize/ARC-AGI
- Official agent framework: https://github.com/arcprize/ARC-AGI-3-Agents
- Official Kaggle starter: https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter
- ARC-AGI-3 Milestone 1 approaches: https://arcprize.org/blog/arc-prize-2026-milestone-1
- Rodionov, *Executable World Models for ARC-AGI-3 in the Era of Coding Agents*: https://arxiv.org/abs/2605.05138
- Rodionov, *Do Coding Agents Need Executable World Models, Simplification, and Verification to Solve ARC-AGI-3?*: https://arxiv.org/abs/2607.15439
- Shen et al., *Thinking vs. Doing: Agents that Reason by Scaling Test-Time Interaction*: https://arxiv.org/abs/2506.07976
- Wang et al., *Hypothesis Search: Inductive Reasoning with Language Models*: https://arxiv.org/abs/2309.05660

Post-milestone background methods:

- DreamerV3: https://doi.org/10.1038/s41586-025-08744-2
- MuZero: https://doi.org/10.1038/s41586-020-03051-4
- Test-Time Training: https://proceedings.mlr.press/v119/sun20b.html
- TTT layers: https://arxiv.org/abs/2407.04620
- SOAR: https://proceedings.mlr.press/v267/pourcel25a.html
- Slot Attention: https://proceedings.neurips.cc/paper/2020/hash/8511df98c02ab60aea1b2356c013bc0f-Abstract.html
- ADAS: https://arxiv.org/abs/2408.08435
