---
title: "ARC Prize 2026 — ARC-AGI-3"
subtitle: "Plan 2: Measured Closed-Loop Implementation"
author: "Project Team"
date: "4 September 2026"
status: "Proposed — implementation companion to the active project plan"
---

# Document purpose

This document converts `ARC-AGI-3_Project_Plan.md` into a concrete implementation sequence for the current repository. The active project plan remains the strategic source of truth; Plan 2 specifies what to build first, how the algorithms interact, what files should own each responsibility, and what evidence is required before adding complexity.

The plan starts from the repository's actual state:

- `agent/my_agent.py` is a random policy with a public-game-specific branch.
- The submission notebook packages only `my_agent.py` and has no local model source or attached weights.
- The vendored LLM, multimodal, LangGraph, SmolAgents, and OpenClaw agents are examples, not offline competition-ready implementations.
- The framework runs game agents concurrently, so model inference and mutable action data require explicit coordination.

# 1. Executive decision

Build the milestone agent as a measured closed loop with two clearly separated responsibilities:

1. **Deterministic code owns truth and safety.** It extracts exact evidence, records transitions, filters legal actions, detects no-ops and loops, enforces budgets, validates model output, and checks predictions.
2. **The local model owns uncertain interpretation.** It proposes goals, mechanics, discriminating probes, memory revisions, and short action plans from selected evidence.

"Model-first" does not mean that model integration is the first line of code. It means the primary policy will use the strongest feasible local model, while a correct deterministic kernel is built first so the model can be evaluated safely.

The milestone critical path is:

```text
E0 legal deterministic fallback
  -> E1 minimal local-model policy
  -> E2 deterministic mixed perception
  -> E3 compact memory
  -> E4 evidence retrieval and retrodiction
  -> E5 bounded competing hypotheses
  -> E6 prediction-checked short plans
```

Executable world models, general search, specialist agents, learned perception, and test-time parameter training remain conditional.

# 2. Success definition

## 2.1 Milestone outcome

By September 30, the candidate should:

- Complete a full competition-like run without invalid actions, uncaught agent exceptions, starved game threads, or missing scorecard entries.
- Load all dependencies and model artifacts without internet access.
- Use one shared local-model instance with bounded, fair inference scheduling.
- Preserve an exact per-game transition record while keeping the active model context compact.
- Use raw grids, rendered images, deterministic differences, object descriptions, and selected crops only when each representation earns its cost.
- Maintain no more than four active hypotheses and select low-risk probes that distinguish them.
- Execute one action under uncertainty and no more than four actions under verified dynamics.
- Cancel a plan immediately when a material prediction fails.
- Project below 7.65 hours for a complete Kaggle evaluation, leaving a 15% margin under the nine-hour limit.

## 2.2 Non-goals for the initial milestone

Do not place the following on the critical path:

- DreamerV3- or MuZero-style neural world-model training.
- Reinforcement learning or fine-tuning on public game identities.
- Test-time parameter training of the primary model.
- Slot Attention or another learned segmentation stack.
- A permanent multi-agent debate or role hierarchy.
- General BFS, A*, model-predictive control, or program synthesis for every game.
- A simulator that must explain every pixel before the policy can act.

# 3. Immediate repository decisions

## 3.1 Remove known baseline defects

The first implementation change should repair `agent/my_agent.py`:

- Remove every game-ID condition, including the `ls20` action weighting.
- Draw actions only from `latest_frame.available_actions`.
- Use an isolated `random.Random` instance with a stable, recorded seed.
- Never mutate process-global random state.
- Derive `ACTION6` coordinates from bounded click candidates inside the current grid dimensions.
- Define explicit behavior for `NOT_PLAYED`, active play, level transition, `GAME_OVER`, and deadline degradation.
- Record the reason for every fallback action.
- Prevent repeated known no-op state-action pairs unless recovery explicitly permits a retry.

The corrected fallback is a permanent safety path, not a temporary throwaway baseline.

## 3.2 Choose multi-file packaging now

Use a small multi-file agent and update `scripts/build_notebook.py` before the agent is split. The builder should package an explicit allowlist of source files, recreate the package under `/tmp`, copy it into the Kaggle framework, and fail if a declared file or import is missing.

Avoid recursive inclusion of arbitrary repository files. An explicit manifest makes the offline artifact auditable and prevents tests, credentials, caches, or public-game material from entering the notebook accidentally.

## 3.3 Protect the evaluation boundary

Before inspecting more environments:

- Record games whose source, trajectories, or mechanics have already been observed.
- Treat those games as development data.
- Select at least five uninspected games using a recorded seed and seal them as the architecture holdout.
- Maintain a rotating diagnostic set separate from the sealed holdout.
- Never add production branches keyed by game ID.

# 4. Proposed source layout

Keep the first architecture small:

```text
agent/
  __init__.py
  my_agent.py          framework adapter and lifecycle
  state.py             dataclasses, enums, transition and hypothesis schemas
  perception.py        canonical frames, hashes, diffs, components, click candidates
  evidence.py          append-only event log and deterministic queries
  controller.py        modes, guards, fallback policy, queue validation
  model_policy.py      prompt assembly, structured response parsing, repair
  inference.py         shared model loading, queueing, timeouts, degradation
```

Add `search.py` only if E7 or E8 passes its entry gate. Do not create a general framework of plugins or agent roles during the milestone.

## 4.1 Ownership rules

| Module | Owns | Must not own |
|---|---|---|
| `my_agent.py` | Framework integration and one-step orchestration | Game-specific mechanics or model internals |
| `state.py` | Typed immutable records | I/O or inference |
| `perception.py` | Deterministic observation-derived features | Semantic guesses presented as facts |
| `evidence.py` | Lossless writes and exact retrieval | Model-written summaries as the only record |
| `controller.py` | Legal actions, modes, budgets, fallbacks, queue checks | Provider-specific prompting |
| `model_policy.py` | Context selection, schema parsing, model proposals | Direct environment actions |
| `inference.py` | Model lifecycle, scheduling, telemetry | Per-game mutable memory |

# 5. Algorithm specifications

## 5.1 Canonical observation

For every environment response:

1. Preserve the complete frame sequence in the event record.
2. Use the final frame as the initial canonical observation unless animation testing identifies a better stable-frame rule.
3. Record shape, palette values, available actions, game state, level count, action count, and time budget.
4. Hash the canonical grid using its shape, dtype, and contiguous bytes. Do not use Python's process-randomized `hash()`.
5. Treat a shape change, level increment, or status change as a scene boundary before interpreting pixel motion.

The initial implementation should support grids smaller than 64 by 64 and multiple frames per observation. It must not require an exact 64-by-64 input.

## 5.2 Exact transition difference

Given compatible canonical grids `before` and `after`, compute:

- Boolean changed-cell mask.
- Number and fraction of changed cells.
- Bounding box of the changed region.
- Per-color counts before, after, added, and removed.
- Connected changed regions.
- Whether the transition is a no-op, local change, global transformation, or scene boundary.

If shapes differ, retain both complete grids and classify the result as a scene boundary rather than padding silently.

## 5.3 Connected components

Compute four-connected components independently for every color. Do not permanently discard the most common color as background; instead, mark background likelihood as a feature.

Each component record should contain:

- Stable observation-local ID.
- Color and area.
- Bounding box and centroid.
- Binary shape mask normalized to its bounding box.
- Border contact and likely-background features.
- Neighboring component colors and distances.
- Membership in the current changed-cell mask.

Begin with deterministic flood fill or union-find using NumPy-compatible data. Learned segmentation is considered only after a documented component failure affects closed-loop decisions.

## 5.4 Component correspondence

Match previous and current components in two passes:

1. Accept unambiguous exact matches using color, area, translated shape mask, and displacement.
2. Greedily assign remaining pairs in increasing deterministic cost order.

The provisional matching cost should combine:

```text
color mismatch penalty
+ normalized area difference
+ normalized centroid distance
+ shape-mask disagreement
+ neighborhood disagreement
```

Record unmatched components as creations or deletions. Record uncertain matches as candidates, not facts. Replace greedy matching with a more expensive assignment algorithm only if correspondence errors become a measured bottleneck.

## 5.5 Click candidate generation

For `ACTION6`, create candidates from:

- Component centroids and interior points.
- Small isolated or button-like components.
- Rare-color components.
- Newly created or recently changed components.
- Endpoints and intersections of thin structures.
- Centers of unexplored regions when object-derived candidates are exhausted.

Deduplicate coordinates, clamp them to the actual grid bounds, and rank them provisionally by:

```text
novelty
+ rare-color evidence
+ recent-change relevance
+ button-like geometry
+ expected hypothesis discrimination
- prior no-op penalty
- repeated-state penalty
- irreversible-risk penalty
```

Store the individual score terms so later ablations can explain why a click was selected.

## 5.6 Lossless transition record

Every action produces an append-only `TransitionRecord` containing at least:

```text
game, level, attempt, step
pre-action frame sequence and canonical hash
available actions
chosen action and coordinate data
selection source: model, queued plan, or fallback
model proposal, expected effect, and stop condition
post-action frame sequence and canonical hash
exact and structural differences
state, level, and score changes
queue continuation or invalidation reason
timing, token, timeout, and fallback telemetry
```

The write path must be deterministic. Model summaries may reference transition IDs but may not replace or edit recorded evidence.

## 5.7 Compact working memory

Maintain three isolated stores per game:

1. **Durable memory:** confirmed mechanics, cross-level invariants, hazards, reusable procedures, and important counterexamples.
2. **Level scratch:** current objects, current subgoal, active hypotheses, candidate plan, unresolved observations, and cheapest useful probe.
3. **Rejected-hypothesis ledger:** rejected claim, contradiction evidence, scope, and conditions for reconsideration.

Apply explicit size limits. When compaction is necessary, retain referenced transition IDs so every important conclusion remains auditable against exact evidence.

## 5.8 Bounded hypotheses

Keep two to four active hypotheses. Each must state:

- Claim and scope.
- Evidence for and against, using transition IDs.
- Predicted result of candidate actions.
- Cheapest distinguishing probe.
- Expected progress, cost, reversibility, and risk.
- Complexity and exception count.
- Status: tentative, supported, verified-for-plan, contradicted, or retired.

Use a provisional transparent ranking rather than model confidence alone:

```text
hypothesis value =
    predictive coverage
  + verified predictions
  + expected progress
  - contradictions
  - complexity
  - exception count
```

Use a separate probe utility:

```text
probe utility =
    expected hypothesis reduction
  + expected progress
  - action cost
  - no-op likelihood
  - irreversible risk
```

Initially treat these as ordered features or simple configurable weights. Do not tune weights on a single exposed game.

## 5.9 Controller modes

Use a small deterministic state machine:

| Mode | Entry trigger | Behavior | Exit trigger |
|---|---|---|---|
| Bootstrap | Game not started or no evidence | Legal reset/start behavior, establish first observation | Active game observed |
| Normal | One leading explanation and reversible choice | One model call; take one action or verified short queue | Prediction match, novelty, or contradiction |
| Fast | Current verified queue and previous prediction matched | Continue with minimal model work | Queue end or material mismatch |
| Deep | Competing hypotheses, novel transition, or irreversible decision | Retrieve more evidence and request larger reasoning budget | Discriminating plan selected |
| Recovery | No-op, loop, contradiction, parse failure, death, or stagnation | Cancel queue, revisit evidence, choose safe novel probe or fallback | New informative transition |
| Done | Terminal completion or hard deadline | Stop cleanly | None |

Self-reported confidence must not select a mode. Only observable state, prediction accuracy, novelty, risk, and remaining budgets may do so.

## 5.10 Model input and output

The normal model request should contain:

- Current rendered image and exact grid when affordable.
- Current deterministic difference and compact object table.
- Legal actions and real coordinate bounds.
- Durable memory, level scratch state, and active hypotheses.
- Selected earlier transitions relevant to the current decision.
- Remaining action, model-call, token, and wall-clock budgets.

Require a strict response:

```json
{
  "state_update": "concise revisable interpretation or null",
  "hypothesis_updates": [],
  "mode": "probe",
  "subgoal": "determine whether ACTION1 moves component c3",
  "actions": [
    {
      "action": "ACTION1",
      "data": null,
      "expected_effect": "component c3 moves upward while other components remain stable",
      "stop_if": "c3 does not move or another persistent component changes"
    }
  ],
  "memory_update": null
}
```

Validation order:

1. Parse JSON or the model's native structured format.
2. Repair syntax or schema representation only.
3. Reject unknown fields where strictness prevents ambiguity.
4. Check that every action is currently legal.
5. Validate coordinate types and bounds.
6. Enforce mode-dependent queue length.
7. Require an observable expected effect and stop condition for queued actions.
8. Fall back deterministically if validation fails.

Repair must never invent a different action.

## 5.11 Deterministic fallback policy

The fallback should prioritize survival and information:

1. Handle required start or reset behavior.
2. Exclude illegal actions.
3. Exclude known no-op state-action pairs when an alternative remains.
4. Prefer legal actions not yet tried from the current stable state.
5. For `ACTION6`, choose the highest-ranked untried click candidate.
6. Avoid actions associated with repeated immediate death unless no alternative remains.
7. Break ties using the per-agent seeded RNG and record the tie-break.

This policy should be independently runnable with model inference disabled.

## 5.12 Prediction-checked queues

- Allow one action in Bootstrap, Deep, or Recovery mode.
- Allow one action during uncertain Normal mode.
- Allow up to four actions only when the relevant mechanics are verified and every action has a distinct expected effect.
- Compare every observed transition with the queued expectation before selecting the next action.
- Cancel immediately on mismatched status, legal-action set, persistent-object change, changed region, progress event, or no-op expectation.
- Do not infer that a mechanic is correct solely because a level completed.

Start with outcome and structural prediction checks. Require exact next-grid prediction only for transitions already shown to be deterministic and where exactness improves a decision.

## 5.13 Shared inference

Load the selected model once per process. All game agents submit requests to a bounded service that provides:

- Per-game request isolation.
- At most one queued request per game unless explicitly justified.
- Fair round-robin or aging-based scheduling.
- Request deadlines and cancellation.
- Optional batching only after serialized inference works correctly.
- Queue-wait, inference, token, memory, and timeout telemetry.
- Deadline degradation to shorter context, smaller model, or deterministic fallback.

Do not attach coordinate data or reasoning by mutating shared `GameAction` enum instances. Construct request-local action payloads at the environment boundary.

## 5.14 Conditional search

Add a small search tool only when all of the following are true:

- A compact state representation is available.
- Relevant transitions have high structural prediction accuracy.
- The required plan exceeds the reliable direct-reasoning horizon.
- A closed-loop failure has been attributed to planning rather than perception or model misunderstanding.

Use BFS for small unweighted deterministic spaces and A* only when a defensible admissible or safely biased heuristic is available. Replan after every real action. Never allow a generated simulator to bypass real-transition verification.

# 6. Implementation phases

## Phase 0 — Correctness, packaging, and evaluation boundary

**Dates:** September 4–6

Deliverables:

- Exposure log and sealed holdout selected before additional inspection.
- Multi-file notebook manifest and clean-room packaging smoke test.
- Repaired deterministic fallback with dynamic legal actions.
- Stable per-agent seeds and deterministic decision traces.
- Lifecycle, terminal-state, coordinate, no-op, and loop guards.
- Machine-readable run summary.

Exit gate:

- Three complete development runs with zero invalid actions and zero uncaught agent exceptions.
- Identical deterministic decision traces under the same seed.
- Generated notebook imports and runs without internet.

## Phase 1 — Perception and exact evidence

**Dates:** September 7–10

Deliverables:

- Canonical observations, stable hashes, and exact differences.
- Connected components and deterministic correspondence.
- Ranked click candidates.
- Append-only transition records and query helpers.
- Unit tests using synthetic grids, including non-64-by-64 and multi-frame observations.

Exit gate:

- Exact difference tests pass for unchanged, local-change, global-change, and scene-boundary cases.
- Component extraction is deterministic.
- Click actions are always bounded and exhibit a lower no-op rate than uniform random clicks on the development set.

## Phase 2 — Minimal local-model vertical slice

**Dates:** September 7–10, in parallel with the latter part of Phase 1

Deliverables:

- One primary and one smaller fallback model profiled on actual target hardware.
- Offline weights and dependencies attached to a smoke notebook.
- Minimal prompt containing current evidence and legal actions.
- Strict output schema, parser, timeout, and deterministic fallback.
- Closed-loop E1 results compared with E0.

Decision gate:

- Keep the primary candidate only if it improves non-random progress and projects within runtime, VRAM, artifact, and license limits.
- Otherwise reduce model size, call frequency, or context before adding reasoning layers.

## Phase 3 — Continuity and bounded reasoning

**Dates:** September 11–16

Deliverables:

- Durable memory, level scratch state, and rejected-hypothesis ledger.
- Two-to-four-hypothesis beam with explicit evidence references.
- Fast, Normal, Deep, and Recovery controller behavior.
- One-action probing and prediction validation.
- One-to-four-action queues for verified mechanics.

Exit gate:

- E3 through E6 improve levels completed, action efficiency, or a documented failure mode relative to the previous accepted treatment.
- Rejected hypotheses are not repeatedly proposed without new evidence.
- Queue-break reasons are recorded and materially incorrect queues stop after one mismatching action.

## Phase 4 — Competition-load inference

**Dates:** September 17–21

Deliverables:

- One shared model instance.
- Bounded fair request queue with timeouts and deadline degradation.
- Concurrent 110-game load simulation.
- Per-game and global inference telemetry.
- Optional dynamic batching experiment after serialized correctness.

Exit gate:

- No game thread crashes or starves.
- All unfinished games retain a wall-clock allocation.
- Model failure degrades to legal actions.
- Projected full evaluation remains below 7.65 hours.

## Phase 5 — Evidence-driven optional algorithms

**Dates:** September 17–21

Enter this phase only for a documented failure that survived Phases 0–4.

Possible treatments:

- Partial executable transition functions.
- Structural replay over earlier transitions.
- BFS or A* over a verified compact model.
- A specialist visual or code-reasoning call.

Exit gate:

- The treatment improves closed-loop completion or action efficiency enough to justify its runtime and complexity.
- Offline simulator accuracy alone is insufficient.

## Phase 6 — Integration and candidate freeze

**Dates:** September 22–28

Deliverables:

- Full development and named sealed-holdout architecture runs.
- Offline Kaggle notebook with hashes for source, weights, and dependencies.
- Runtime, RAM, VRAM, queue, disk, and log profile.
- Two candidates with meaningfully different score/runtime risk profiles.
- Frozen milestone candidate by September 28.

Exit gate:

- Clean checkout reproduces the selected notebook.
- Full competition-like run completes inside the safety margin.
- All accepted components have an archived ablation result.

## Phase 7 — Submission verification

**Dates:** September 29–30

Use this period only for notebook reruns, packaging correction, infrastructure delays, artifact verification, and final submission. Do not add unmeasured algorithms after the freeze.

# 7. Evaluation and tests

## 7.1 Unit tests

Required test groups:

- Grid hashing determinism across processes.
- Differences for no-op, movement, recoloring, creation, deletion, and shape changes.
- Connected components at borders, with holes, and with repeated colors.
- Component correspondence under translation, split, merge, creation, and deletion.
- Click candidates on small, rectangular, and maximum-sized grids.
- Strict response parsing with missing, extra, malformed, and illegal actions.
- Queue cancellation for every material mismatch category.
- Stable fallback traces under a fixed seed.

## 7.2 Integration tests

- Model unavailable at startup.
- Model timeout during active play.
- Invalid model JSON and out-of-range coordinates.
- Level transition during a queued plan.
- Game-over and reset behavior.
- Multiple agents requesting inference simultaneously.
- Global deadline degradation.
- Clean-room generated-notebook import and run.

## 7.3 Closed-loop experiments

Report each incremental treatment against the previous accepted system:

| Treatment | Primary comparison |
|---|---|
| E0 | Correct fallback versus current random policy |
| E1 | Minimal local model versus E0 |
| E2 | Mixed perception versus raw grid/frame only |
| E3 | Compact memory versus bounded recent history |
| E4 | Exact evidence retrieval and retrodiction versus summary only |
| E5 | Bounded hypotheses versus one unconstrained explanation |
| E6 | Prediction-checked queues versus one model call per action |

Fixed trajectories may test perception, parsing, prediction, and latency. Policy acceptance requires repeated closed-loop rollouts.

## 7.4 Required metrics

- Games won, levels completed, and completion fraction.
- Actions per completed level and actions before first progress.
- Invalid, no-op, repeated, reset, and death rates.
- Schema validity, fallback rate, and hypothesis revision latency.
- Outcome and structural prediction accuracy, separated for changed and unchanged states.
- Queue length, actions per model call, and queue-break rate.
- Input/output tokens, inference latency, queue wait, peak RAM/VRAM, and total runtime.
- Development, diagnostic, sealed-holdout, and leaderboard gaps.

# 8. Merge and escalation gates

Accept a change when it provides at least one measured benefit without breaking reliability or resource ceilings:

- More held-out levels completed.
- Better action efficiency on already completed levels.
- A documented failure eliminated.
- Lower runtime or fewer model calls with preserved completion.
- Better prediction accuracy that changes closed-loop decisions.
- Better reliability under concurrency or deadline pressure.

Reject or defer a change when:

- Its only gain is on one exposed public game.
- It relies on a best seed or selective rerun.
- It improves an offline proxy but not closed-loop behavior.
- It raises the projected full run above 7.65 hours.
- It adds a framework, role, model, or simulator without a measured decision benefit.
- Its output cannot be validated or safely bypassed.

# 9. Principal risks and controls

| Risk | Control |
|---|---|
| Plan scope exceeds implementation capacity | Treat E0–E6 as the only mandatory ladder and enforce gates |
| Public-game overfitting | Exposure log, sealed holdout, no game-ID logic |
| Model dominates runtime | Early hardware profiling, short queues, adaptive calls, smaller fallback |
| Model hallucination corrupts memory | Lossless code-owned evidence and referenced summaries |
| Weak world model makes search harmful | Structural verification before search and replanning after every action |
| Context grows without bound | Separate durable/scratch/rejected memory and retrieve evidence by ID |
| Concurrent agents starve one another | One fair bounded inference service and 110-game load tests |
| Shared mutable action data crosses games | Request-local action payloads and per-game state isolation |
| Notebook omits a module or weight | Explicit packaging manifest and clean-room smoke test |
| Optional frameworks add unavailable dependencies | Implement the critical path with the smallest pinned dependency set |

# 10. Next 72 hours

Execute in this order:

1. Create the exposure log and select the sealed holdout before inspecting additional games.
2. Add a source manifest to the notebook builder and prove a small multi-file agent packages correctly.
3. Replace the current policy's global RNG, game-ID branch, and static action list.
4. Implement legal fallback behavior, lifecycle handling, and bounded `ACTION6` coordinates.
5. Add canonical-frame hashes, exact transition differences, and append-only transition records.
6. Add no-op and repeated-state-action suppression.
7. Create focused unit tests for steps 3–6.
8. Run and archive three deterministic development baselines.
9. Prepare the smallest offline model-loading notebook and measure one structured inference call on the target accelerator.

Do not begin general search, executable world modeling, or learned perception during these 72 hours.

# 11. Definition of done

Plan 2 is successfully implemented when:

- The production policy contains no public-game identifiers or solution tables.
- Every environment action is legal and has a recorded selection reason.
- Every observation and transition is recoverable from the evidence record.
- Model-facing state is compact, bounded, and linked to exact evidence.
- Model output cannot bypass action, coordinate, queue, runtime, or terminal-state guards.
- Incorrect predictions stop queued execution immediately.
- Model or infrastructure failure produces a legal deterministic fallback rather than a crashed thread.
- The same artifact passes unit, integration, concurrent-load, clean-room notebook, and closed-loop holdout gates.
- The final candidate completes within the declared Kaggle runtime and resource margins.

# 12. Relationship to the other plans

- `ARC-AGI-3_Project_Plan.md` remains the active strategic and evidence-driven plan.
- `ARC-AGI-3_Project_Plan_2.md` is its repository-specific implementation companion.
- `ARC-AGI-3_Preliminary_Project_Plan.md` and the older DOCX remain historical records and should not override the active design or Plan 2 implementation gates.
