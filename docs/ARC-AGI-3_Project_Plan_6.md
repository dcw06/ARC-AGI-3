---
title: "ARC Prize 2026 — ARC-AGI-3"
subtitle: "Plan 6: Competition-Correct, Controlled, Degradation-Safe Implementation"
author: "Project Team"
date: "4 September 2026"
status: "Proposed — execution successor to Plan 5"
---

# Document purpose

This document supersedes `ARC-AGI-3_Project_Plan_5.md` for implementation
planning. It preserves Plan 5's central architecture and full technical scope:
deterministic code owns evidence, budgets, validation, and safety, while a
local model owns uncertain interpretation. The E1 paradigm/observation 2×2
bake-off remains a required measured comparison.

`ARC-AGI-3_Project_Plan.md` remains the strategic source of truth. When an
execution detail conflicts with an older execution document, Plan 6 controls.
Plans 2–5 remain design-history records.

Plan 6 retains Plan 5's corrections and adopts seven post-review changes:

1. Execution coverage over all 110 evaluation games is distinguished from the
   separate 55-game public and 55-game private leaderboard aggregations.
2. E0 remains the correctness and safety baseline, while reproducible
   competitive controls `E0W-S` and `E0W-C` anchor performance claims.
3. E1 becomes a 2×2 comparison of agent paradigm and observation treatment so
   the effect of E0F is not confounded with the E1 paradigm comparison.
4. Evidence retention is prioritized and degradation-safe. Unknown future
   animation length is never treated as reservable, and evidence degradation
   never terminates an otherwise viable game.
5. Five-game H1/H2 evaluations are catastrophic-regression guardrails, not
   statistical-significance tests. Development cross-validation owns treatment
   acceptance.
6. Discretionary scheduling uses normalized marginal level value rather than
   raw level index.
7. Sealed evaluation is an explicitly scoped best-effort security property.
   It never claims guaranteed cleanup under unhandleable process or host
   failures.

The plan assumes one primary implementer. Its sequence expresses technical
dependencies, not a reduction of the intended research scope.

# 1. Verified starting state

The repository currently has the following properties:

- `agent/my_agent.py` is a random policy with an `ls20`-specific branch.
- It seeds the module-global random generator from wall-clock time and Python
  `hash()`.
- It enumerates all `GameAction` members rather than the current legal actions.
- It mutates shared `GameAction` enum instances with `set_data()` and
  `reasoning`.
- The upstream loop uses `action_counter <= MAX_ACTIONS`, so its apparent cap
  is not exact.
- The official framework creates one agent thread per game.
- `scripts/play_local.py` uses `OperationMode.NORMAL` and runs games
  sequentially. It is a development runner, not a competition-parity runner.
- The notebook builder packages only `my_agent.py` and installs only `arc-agi`
  and `python-dotenv` from the competition wheelhouse.
- `notebooks/kernel-metadata.json` has no model or dataset source and contains
  a username placeholder.
- `.kaggle/access_token` is absent and must remain untracked when supplied.
- Public payloads for `ls20` and `vc33` are downloaded. Both are exposed and
  must remain in the development partition.
- The 25 public environment identifiers have been listed without opening the
  remaining environments.
- The workspace is not a Git repository, so clean-checkout reproduction is not
  yet available.

Before the first Kaggle submission, perform a non-secret account preflight:

- Competition rules accepted.
- Kaggle kernel ID contains the correct username.
- `.kaggle/access_token` exists, is non-empty, has restrictive permissions,
  and remains ignored.
- Required competition, dependency, and model sources are attached.
- Internet is disabled in notebook metadata.

# 2. Executive decision

Build a measured closed-loop agent with two separated responsibilities:

1. **Deterministic code owns truth, budgets, and safety.** It retains evidence
   according to an explicit priority order, normalizes legal actions, owns
   request-local action data, analyzes frame sequences, enforces resource
   limits, validates model output, checks predictions, and selects controller
   mode.
2. **The local model owns uncertain interpretation.** It proposes goals,
   mechanics, discriminating probes, memory revisions, and short plans from
   selected evidence. In E1C it may use a bounded analysis workspace, but that
   workspace never submits actions or mutates production state.

The dependency-correct milestone path is:

    E0 correctness + reproducible packaging + legal deterministic fallback
      -> reproducible E0W-S and E0W-C competitive controls
      -> raw minimal observation path + optional E0F feature treatment
           canonical frames + deltas + animation summaries + click candidates
      -> 2×2 E1 comparison
           paradigm: E1S structured policy versus E1C bounded workspace
           observation: raw minimal path versus E0F feature treatment
      -> E1 accepted or explicitly provisional primary paradigm
         + completed measured decision table
      -> E2 advanced evidence retrieval + selective animation exposure
      -> E3 compact cross-level memory
      -> E4 retrodiction and evidence-grounded revision
      -> E5 bounded hypotheses + one-action prediction checks
      -> E6 prediction-checked short queues
      -> E7 conditional advanced correspondence
      -> E8 conditional executable models, search, or specialist requests

Learned perception, reinforcement learning, test-time parameter training,
unrestricted code execution, and permanent multi-agent debate are not required
control paths. They may be tested only through the treatment protocol.

# 3. Objectives and success criteria

## 3.1 Competition objective

Maximize public-leaderboard ARC-AGI-3 Relative Human Action Efficiency (RHAE)
for the September milestone and final private-leaderboard RHAE for the final
competition, within Kaggle's offline runtime, hardware, and reproducibility
constraints while producing valid execution coverage for all 110 unseen
evaluation environments.

For a completed level `l`:

    level_score_l =
        min(1.15, (human_baseline_actions_l / agent_actions_l)^2)

An uncompleted level contributes zero. A game's score is the level-index
weighted aggregation of its level scores, capped by its weighted
completed-level fraction. Kaggle partitions the 110 evaluation environments
into 55 used for the public leaderboard and 55 used for the private
leaderboard. The agent must cover all 110 environments, while each leaderboard
score is aggregated over its designated split; untouched games in the relevant
split count as zero. The official installed `arc-agi` implementation and Kaggle
scorer are authoritative if documentation and a local reimplementation
disagree.

## 3.2 Evaluation hierarchy

For any fixed evaluation set, use this order:

1. Mean official RHAE across the entire fixed set, including untouched games.
2. Paired per-game RHAE differences between treatment and control.
3. Coverage: games with non-zero score and games fully completed.
4. Weighted level-completion fraction.
5. Levels completed.
6. Actions per completed level and actions before first progress.
7. Predeclared structural-progress and prediction diagnostics.

Structural diagnostics guide engineering when RHAE is zero or statistically
inconclusive. They do not replace RHAE for final policy acceptance.

Maintain three baseline roles:

- **E0:** deterministic legal fallback used to establish correctness, safety,
  and degradation behavior.
- **E0W-S:** the strongest reproducible open-source structured-action control
  that can be packaged under the competition constraints.
- **E0W-C:** the strongest reproducible open-source constrained-code or
  workspace control that can be packaged under the competition constraints.

Record provenance, license, model, prompt, source hash, artifact hash, and any
necessary compatibility changes for both E0W controls. A control that cannot be
reproduced is reported but cannot anchor an acceptance claim. The strongest
reproducible control is the control with the highest primary mean RHAE under
equal ceilings; coverage and tail behavior break ties. A hybrid claim must be
tested against each component and the strongest standalone control.
If neither published control reproduces, implement a provenance-recorded
reference control from its published method and validate it before making a
final performance claim.

Human baselines may be used only by evaluator code. They must not enter policy
prompts, model workspaces, action allocation, controller decisions, or
model-visible evidence.

## 3.3 Milestone outcome

By September 30, the selected candidate should:

- Produce a valid Kaggle submission before the final verification window.
- Pass a competition-parity run without invalid actions, uncaught exceptions,
  cross-game payloads, starved clients, or missing scorecard entries.
- Load all source, models, tokenizers, native libraries, and wheels offline
  from declared mounted artifacts.
- Use a measured primary model topology.
- Demonstrate accepted development-protocol improvement over the strongest
  reproducible competitive control, or accepted gain from combining with that
  control, before final selection.
- Retain action evidence according to the declared priority order while
  bounding active model context, RAM, disk, and action count.
- Produce deterministic animation metadata for every multi-frame response.
- Use one action under uncertainty and no more than four actions under verified
  dynamics.
- Stop a queued plan after its first material prediction failure.
- Finish below 7.65 hours in a competition-like load test.
- Publish required source, licenses, notebook, manifests, and reproduction
  instructions before the milestone deadline when pursuing milestone
  eligibility.

## 3.4 Treatment outcomes

Before every policy, model, perception, memory, or planning comparison, record:

- Treatment and control identifiers.
- Fixed game set and paired game seeds.
- Agent RNG and, where controllable, model decoding seeds.
- Model, quantization, prompt, representation, and context policy.
- Equal wall-clock, token, call, action, reset, and retry ceilings.
- Primary outcome and minimum practical effect `delta_min`.
- Uncertainty procedure and confidence level.
- Catastrophic tail-regression threshold.
- Crash, timeout, and missing-result handling.

Use seed-aggregated paired per-game results as the unit of generalization.
Estimate uncertainty with a predeclared paired bootstrap or paired permutation
procedure appropriate to the game count. Report the point estimate, interval,
dispersion, coverage, and worst regression.

Treatment acceptance is performed on development games through predeclared
cross-validation or repeated paired evaluation. H1 and H2 do not supply
statistical acceptance because each contains only five game-level units.

Classify the statistical result as:

- **Accept:** the primary improvement reaches `delta_min`, meets the
  uncertainty rule, preserves resource ceilings, and avoids catastrophic tail
  regression.
- **Reject:** the treatment is materially worse, exceeds a resource ceiling,
  or crosses the tail-regression threshold.
- **Inconclusive:** neither acceptance nor rejection conditions are met.

An inconclusive result is never relabeled as accepted. Reliability changes may
be accepted when they eliminate a reproduced failure and remain within a
predeclared non-inferiority margin.

## 3.5 Provisional advancement

Statistical outcome and implementation status are separate fields.

After E1:

- If an E1 treatment is accepted against the strongest reproducible E0W
  control, it becomes the selected primary paradigm.
- If the comparison is inconclusive and at least one treatment remains within
  safety and resource ceilings, designate one **provisional primary** using a
  predeclared tie-break order:
  1. higher RHAE point estimate;
  2. higher non-zero coverage;
  3. fewer invalid/crashed games;
  4. better prediction/structural diagnostics;
  5. lower inference cost and tail latency.
- If all E1 treatments are rejected, the strongest reproducible E0W control
  remains the operational primary while E1 is repaired or rerun under its
  predeclared replication rule. E0 remains the permanent failure fallback.

Provisional advancement permits implementation of shared infrastructure only.
It does not displace the strongest E0W competition control or justify claims of
policy improvement, use of H1/H2, or final candidate selection. Before final
selection, an E1-derived candidate must
demonstrate accepted development-protocol improvement over the strongest
reproducible competitive control, or demonstrate that a predeclared
combination with that control improves primary RHAE or coverage without
violating the tail-regression rule.

The Phase 1 decision table remains mandatory whether E1 is accepted,
provisional, or rejected.

## 3.6 Runtime and inference budget

The operational target is 7.65 hours, or 27,540 seconds:

| Budget | Provisional ceiling |
|---|---:|
| Offline install, import, and model load | 900 seconds |
| Environment I/O, deterministic work, and recording | 3,300 seconds |
| Shared model service | 19,800 seconds |
| Scorecard close and artifact finalization | 600 seconds |
| Operating reserve inside the target | 2,940 seconds |
| Total | 27,540 seconds |

These are initial ceilings. Target-accelerator measurements replace them.

Let:

- `G = 110`, the evaluation game count.
- `A` be the measured action cap per game.
- `B_model` be model-service wall-clock budget.
- `L_weighted` be sustained mean service time under mixed traffic.

For serialized service:

    C_max = floor(B_model / L_weighted)

For batching, derive capacity from sustained completed requests per wall-clock
second, including queueing and batch-formation delay.

## 3.7 Mandatory Phase 1 decision table

The archived decision table must contain:

| Field | Required value |
|---|---|
| Accelerator and runtime | Exact measured environment |
| Primary model | Source, version, architecture, license |
| Quantization and load mode | Exact format and parameters |
| Agent paradigm | E1S, E1C, safe-operations E1C, or measured hybrid |
| Evidence status | Accepted, provisional, or E0 fallback |
| Observation representation | Image, grid encoding, animation policy |
| Context policy | Normal/deep limits and eviction |
| Output policy | Token limit, schema, repair rule |
| Cold load / first request | Measured seconds |
| Sustained throughput | Requests/hour under mixed client load |
| Latency | Queue and service p50/p90/p99 |
| Memory | Peak VRAM, RAM, disk, and evidence bytes |
| Total model calls/tokens | Hard maxima |
| Guaranteed allocation | Calls/tokens per game |
| Discretionary allocation | Pool size and priority rule |
| Action/reset/retry caps | Exact tested values |
| Timeouts | Queue, request, per-game, global deadlines |
| Degradation strategy | Measured fallback path |
| Utility estimate | Paired RHAE gain per inference-second |

Infrastructure work may proceed under provisional status. H1 evaluation,
candidate claims, and final selection may not.

# 4. Reproducibility and evaluation boundary

## 4.1 Reproducibility contract

Before policy development:

- Initialize version control.
- Verify that `.env`, `.kaggle`, downloaded environments, recordings, caches,
  generated notebooks, and model caches remain ignored.
- Pin Python, `arc-agi`, framework revision, notebook builder, Python
  dependencies, and native inference dependencies.
- Record compatibility with the framework supplied by Kaggle.
- Record source, wheel, model, tokenizer, configuration, and prompt hashes.
- Add clean-checkout bootstrap and compatibility smoke tests.

Name two reproduction modes:

1. **Local bootstrap:** clean checkout plus declared network-fetched or
   pre-cached dependencies and selected development games.
2. **Kaggle offline reproduction:** clean checkout plus declared
   Kaggle-mounted competition, dependency, and model artifacts; no runtime
   internet or secret.

Never claim that a clean checkout runs offline without naming its required
mounted artifacts.

## 4.2 Public-game partition

Before starting or inspecting any additional public environment:

1. Record all exposed games. `ls20` and `vc33` belong to development.
2. Freeze the 25-game identifier inventory.
3. Predeclare the partition seed and permitted stratification fields.
4. Select:
   - 15 development environments, including exposed games;
   - 5 H1 architecture-gate environments;
   - 5 H2 candidate-gate environments.
5. Hash and archive the manifest before any candidate is opened.

Permitted stratification fields must be non-semantic and available without
calling `make`, viewing frames, opening source, or playing the game. Permitted
examples are:

- Number of levels, if exposed by inventory metadata.
- Action-space signature, only if exposed directly by inventory metadata
  without starting the environment.
- Stable identifier/version fields used solely for deterministic assignment.

Do not stratify on descriptive task tags, mechanics, frames, source, replay
content, human outcomes, agent outcomes, or derived difficulty. If a permitted
field is unavailable without exposure, do not use it; fall back to the recorded
seed while preserving exposed games in development.

H1/H2 are catastrophic-regression guardrails, not estimates of the private
distribution and not statistical-significance tests:

- **H1 architecture gate:** one planned sealed evaluation after E5/E6 is
  internally stable and development cross-validation has accepted it. H1 may
  veto an architecture for a predeclared catastrophic regression, invalid-run
  rate, or resource failure; it may not establish a positive treatment claim.
- **H2 candidate gate:** one planned sealed evaluation under a predeclared
  candidate-selection rule. H2 applies aggregate guardrail thresholds and a
  deterministic tie-break rule; it does not use a five-game significance test.

Because H2 participates in candidate selection, it is a final validation gate,
not an untouched estimate of private performance. Kaggle submissions remain
sparse external confirmation. Multiple seeds reduce within-game noise but do
not increase the number of game-level generalization units. With five pairs,
the minimum exact two-sided sign-flip permutation p-value is `2/32 = 0.0625`.

## 4.3 Best-effort sealed evaluation mode

`sealed_eval` is a best-effort control that minimizes developer-visible tuning
information escaping H1 or H2 while allowing the policy to observe the
environment during execution. It is not an absolute deletion or
confidentiality guarantee.

During a sealed run:

- Raw frames, deltas, animation strips, prompts, model responses, hypotheses,
  reasoning, recordings, and per-step logs live only in a process-private
  temporary directory outside notebook output directories.
- The directory has restrictive permissions, an unpredictable name, and is
  passed only to the evaluator and its supervised children.
- Standard output and logs contain only non-visual lifecycle validity codes.
- The evaluator calculates per-game values internally but emits only
  predeclared aggregate metrics. Any paired estimate or interval from a
  five-game gate is descriptive and is never labeled statistically
  significant.
- Human baselines remain evaluator-only.
- Debug rendering, framework recording, traceback locals, prompt dumps, and
  evidence export are disabled.
- Cleanup is attempted from normal-return, exception, handled-signal,
  `finally`, and external-supervisor paths. Startup also scrubs stale sealed
  directories from prior interrupted runs, and core dumps are disabled where
  the runtime permits.
- Retained artifacts are limited to hashes, aggregate metrics, redacted
  validity codes, and cleanup status.

Cleanup status distinguishes at least `verified_clean`, `cleanup_attempted`,
and `cleanup_unverified`. `verified_clean` means the evaluator checked that its
known temporary paths were absent after cleanup; it does not prove that the
host, filesystem, swap, platform logs, or terminated runtime retained no copy.
No mechanism in this plan claims to cover `SIGKILL`, kernel OOM, abrupt host
termination, storage snapshots, or platform behavior outside the process's
control.

A rerun is allowed only under a predeclared invalid-run rule and only when no
usable policy result was emitted. The sealed evaluator itself receives unit
tests for output redaction, normal cleanup, exception cleanup, handled-signal
cleanup, supervisor cleanup, startup scrubbing, and output-schema enforcement.

## 4.4 Deployment manifests

Maintain:

1. **Source manifest:** explicit allowlist of embedded agent modules and
   configurations.
2. **Dependency manifest:** wheels, native libraries, CUDA assumptions, hashes,
   sizes, licenses, and offline installation order.
3. **Model manifest:** Kaggle source, weights, tokenizer, templates,
   quantization, hashes, sizes, license, mount paths, and load mode.

The notebook builder fails on missing sources, unresolved imports, unexpected
artifacts, hash mismatches, placeholder kernel IDs, incompatible license
allowlists, or internet-enabled metadata.

# 5. Repository layout and ownership

Target layout:

    agent/
      __init__.py
      my_agent.py          framework adapter and guarded lifecycle
      action.py            frozen decisions and coordinate types
      state.py             compact per-game state and hypotheses
      perception.py        canonical grids and inter-action features
      animation.py         deterministic intra-action summaries
      evidence.py          prioritized packed evidence and retrieval
      controller.py        modes, budgets, legal guards, queues, fallback
      model_policy.py      prompt assembly and structured responses
      scratchpad.py        isolated Python or fixed safe operations
      inference.py         shared model service and scheduling
      metrics.py           evaluator-only RHAE and statistics
      sealed_eval.py       best-effort H1/H2 redaction and cleanup
      config.py            validated run and budget configuration

    packaging/
      source_manifest.txt
      dependency_manifest.json
      model_manifest.json

    evaluation/
      public_partition.json
      competitive_controls.json
      experiment_registry.jsonl
      budget_decision_table.json
      sealed_output_schema.json

    tests/
      unit/
      integration/
      synthetic/

    scripts/
      build_notebook.py
      play_local.py
      play_concurrent.py
      play_competition_like.py
      load_test_inference.py
      compare_treatments.py

Ownership rules:

| Module | Owns | Must not own |
|---|---|---|
| `my_agent.py` | Framework integration and orchestration | Game-specific mechanics |
| `action.py` | Immutable decisions and display coordinates | Policy selection |
| `state.py` | Typed compact per-game state | I/O or model loading |
| `perception.py` | Observation-derived features | Semantic claims presented as facts |
| `animation.py` | Frame-sequence facts and motion candidates | Unverified intent labels |
| `evidence.py` | Prioritized packed retention and degradation telemetry | Unbounded Python frame history |
| `controller.py` | Legal actions, modes, budgets, fallback | Provider-specific prompting |
| `model_policy.py` | Context selection and proposals | Direct environment calls |
| `scratchpad.py` | Constrained analysis | Environment authority or secrets |
| `inference.py` | Model lifecycle and scheduling | Per-game mutable memory |
| `metrics.py` | Evaluator-only RHAE and statistics | Policy-visible baselines |
| `sealed_eval.py` | Best-effort holdout isolation and aggregate outputs | Policy decisions or absolute cleanup claims |
| `config.py` | Validated constants and budgets | Runtime state |

# 6. Algorithm specifications

## 6.1 Immutable action execution

The controller produces a frozen `ActionDecision`:

    ActionDecision
      action_id: integer
      data: immutable request-local payload or empty
      reasoning: immutable request-local mapping
      source: structured_model, scratchpad_model, queued_plan, or fallback
      expected_effect: optional structured prediction
      stop_condition: optional structured condition

Production code must not call `GameAction.set_data()`.

At submission:

1. Re-read the current legal-action set.
2. Validate the action ID.
3. For ACTION6, validate display-space wire coordinates in `0..63`.
4. Resolve the enum member without mutating it.
5. Construct fresh data and reasoning dictionaries.
6. Call `arc_env.step(action, data=fresh_data, reasoning=fresh_reasoning)`.
7. Record the exact submitted decision.
8. Clear pending request state in a `finally` block.

Override the upstream loop and action request boundary so action-cap semantics,
cleanup, packed evidence, and request-local payloads are controlled by Plan 6.

## 6.2 ACTION6 coordinate model

Use distinct types:

    ScenePoint
      x, y in a detected or cropped logical region

    DisplayPoint
      x, y in the API display space, each integer in 0..63

    CoordinateTransform
      source region, scale, offset, clipping, and transform provenance

Candidate generation may reason over a crop, component, logical grid, or
observed frame. Before submission it must explicitly map the candidate to a
`DisplayPoint`. The controller validates only the display point against API
wire bounds. It never submits crop-local or logical coordinates directly.

If no reliable transform exists, generate candidates directly in display space.
Record both source and mapped coordinates for later prediction checks.

## 6.3 Deterministic fallback

The permanent fallback must:

- Contain no game-ID branch or solution table.
- Draw only from normalized current `available_actions`.
- Use a per-agent `random.Random` seeded by a stable digest.
- Generate ACTION6 `DisplayPoint` values through ranked visible candidates and
  wire-valid exploration points.
- Handle start, active play, level transition, GAME_OVER, exhaustion, and
  terminal completion.
- Respect competition-mode level-reset semantics.
- Catch policy, parsing, inference, workspace, storage, and evidence failures.
- Record a reason for every decision outside sealed developer output.
- Enforce exact action, reset, retry, call, token, byte, and wall-clock budgets.

`no_visible_change` is evidence scoped to an action and context fingerprint,
not proof of a latent no-op. Apply a decaying penalty and permit deliberate
retry after a material context or hypothesis change.

## 6.4 Competitive controls and observation factors

Reproduce two competitive controls before claiming policy progress:

- `E0W-S`: a strong open-source vision/structured-action agent.
- `E0W-C`: a strong open-source code/workspace agent, constrained only as
  required for safe and reproducible competition execution.

Compatibility changes must be minimal, recorded, and tested. Do not silently
add Plan 6 features to a control. Each control receives the same accelerator,
model-access opportunity, wall-clock accounting, action rules, and leaderboard
coverage requirements as the corresponding treatment unless an unavoidable
difference is explicitly labeled.

Freeze the selected control source revisions, manifests, compatibility
patches, and profiles before E1. A later public control may be added
prospectively, but it must not replace a weaker control retroactively in
already classified experiments.

Define two observation treatments independently of agent paradigm:

- **R — raw minimal:** current rendered observation, exact current grid,
  available actions, game-state metadata, and a bounded recent history of
  actions and canonical final frames. It excludes engineered deltas, regions,
  intermediate animation frames, animation summaries, and ranked click
  candidates.
- **F — E0F:** the same raw inputs plus the engineered E0F evidence described
  below.

The raw path remains production-valid and available as a final candidate. E0F
is never assumed beneficial merely because it is shared infrastructure.

## 6.5 E0F minimal evidence foundation

E0F is shared infrastructure completed before E1. It must be deliberately
minimal but production-valid:

- Canonical final observation plus bounded summaries of all response frames;
  retain the complete ordered response sequence when capacity permits.
- Stable packed hashes.
- Basic inter-frame and inter-action changed-cell masks.
- Number of frames, distinct frames, changed-cell counts, transient cells, and
  change bounding box.
- Palette additions/removals.
- Connected same-color regions.
- Basic appearance, disappearance, and unambiguous translation candidates.
- Basic ACTION6 display-space candidates.
- Strict size/token serialization shared by E1S and E1C.

Within the F arm, E1S and E1C receive the same E0F evidence and candidate API.
The R arms receive neither. Phase 2 may add advanced evidence, retrieval, and
selective rich animation, but may not retroactively make the E1 comparison
depend on unavailable components.

## 6.6 Prioritized packed observation retention and bounded memory

For every environment transition, retain information in this strict priority
order:

1. Submitted action and response metadata.
2. Canonical final frame.
3. Compact inter-action delta.
4. Bounded intermediate-frame summaries.
5. Complete ordered intermediate-frame sequence when capacity permits.

Convert retained frames immediately to contiguous `numpy.uint8`. Validate
shape, values, frame order, and metadata. Hash the packed shape plus bytes with
a stable content hash, stream retained exact blobs to the content-addressed
store, and append a compact transition index containing the retention tier and
availability of optional evidence. Keep only a bounded recent ring and latest
canonical frame in RAM. Preserve the level-completing action, metadata, final
frame, delta, and bounded summary before clearing level scratch.

Do not retain the upstream framework's unbounded list of nested Python frame
grids. Override `main`, `append_frame`, or the adapter boundary so the
framework receives only the bounded compatibility state it needs.

Evidence storage has measured limits:

- Maximum packed RAM per game.
- Maximum packed RAM globally.
- Maximum optional exact-sequence bytes per game.
- Maximum optional exact-sequence bytes globally.
- Maximum transition-index bytes.
- Maximum retrieval working set.

The API does not publish a maximum response-frame count, so the controller does
not claim to reserve capacity for an unknown future sequence. Before acting, it
reserves only the fixed mandatory tier: action/metadata, final-frame slot, and
compact delta/summary capacity. On receipt, it processes intermediate frames
incrementally to produce bounded summaries and determines the packed size of
the full sequence. It retains that sequence atomically only if the whole
sequence fits the optional capacity; otherwise it marks the sequence omitted.
Under pressure it evicts or declines optional complete sequences before
degrading bounded summaries, compact deltas, final frames, or action metadata.

Evidence degradation emits explicit telemetry describing what was retained,
summarized, evicted, or omitted. It never terminates an otherwise viable game.
If persistent storage is unavailable, the controller continues with bounded
in-memory mandatory evidence and deterministic eviction rather than entering a
terminal evidence state.

Lossless compression and deduplication are implementation details selected by
measurement for evidence retained exactly. Compression must preserve exact
array shape, order, dtype, and bytes. Hash collisions are guarded by
length/shape checks and byte comparison when an existing key is reused.

## 6.7 Advanced animation analysis

For every response, compute deterministic metadata:

- Number of returned and distinct frames.
- Frame-to-frame changed-cell counts and masks.
- Union bounding box.
- Transient cells present only in intermediate frames.
- Per-color additions and removals.
- Appearing and disappearing regions.
- Approximate motion paths for unambiguous regions.
- Candidate temporal order, explicitly marked uncertain when ambiguous.
- Whether the final frame hides material transition information.

Default F-arm model input contains the final rendered frame, compact exact grid
representation, inter-action delta, and animation summary. The R arm does not
receive the delta or animation summary. Deterministic animation analysis may
still run behind the policy boundary for evaluator telemetry without entering
R-arm prompts or decisions.

Expose cropped timelines or full animation strips only when a deterministic
trigger fires:

- Motion or temporal order is decision-relevant and unresolved.
- A transient signal appears.
- Final-state deltas are ambiguous.
- A prediction failure may be explained by intermediate frames.
- The model requests animation evidence within budget.

Record added bytes, image tokens, latency, and paired RHAE contribution.

## 6.8 Inter-action features and click candidates

Between compatible canonical grids compute:

- Changed cells and bounding regions.
- Color additions/removals.
- Legal-action changes.
- Simple translation/recoloring candidates.
- Scene-boundary detection when shapes change.

Generate ACTION6 source candidates from:

- Centroids and interior points of same-color regions.
- Small isolated or button-like regions.
- Rare colors.
- Newly changed or transient regions.
- Endpoints and intersections of thin structures.
- Display-space centers of unexplored regions.

Rank with ordered features for novelty, salience, change relevance,
hypothesis discrimination, contextual no-change, repetition, and irreversible
risk. Map candidates through an explicit `CoordinateTransform` to
`DisplayPoint`; wire validation remains `0..63`.

## 6.9 Compact working memory and evidence

Maintain three isolated logical stores per game:

1. **Durable memory:** verified mechanics, invariants, hazards, reusable
   procedures, and important counterexamples.
2. **Level scratch:** current objects, subgoal, active hypotheses, candidate
   plan, unresolved evidence, and cheapest useful probe.
3. **Rejected-hypothesis ledger:** rejected claim, contradiction evidence,
   scope, and reconsideration conditions.

All claims reference exact transition IDs. Model summaries append revisions but
cannot replace evidence. Apply explicit token, item, byte, RAM, and disk
ceilings.

Each transition index records pre/post hashes, legal actions, submitted
decision, animation/inter-action evidence references, progress, queue result,
inference telemetry, and the exact retention/degradation status. Sealed runs
retain these only ephemerally.

## 6.10 E1 2×2 paradigm and observation bake-off

All four treatment cells share:

- Immutable action boundary.
- Deterministic fallback.
- The same base model when the weights support both paradigms.
- Identical evidence-selection and animation-exposure policy within each
  observation arm.
- Equal wall-clock, token, call, action, reset, retry, and evidence-byte
  ceilings.
- The same game/seed pairs.

The four cells are:

| Cell | Paradigm | Observation treatment |
|---|---|---|
| `E1S-R` | Multimodal structured action | Raw minimal R |
| `E1S-F` | Multimodal structured action | Engineered E0F |
| `E1C-R` | Bounded analysis workspace | Raw minimal R |
| `E1C-F` | Bounded analysis workspace | Engineered E0F |

Estimate the paradigm effect within R and F, the observation effect within S
and C, and their interaction. Do not pool away a harmful observation effect.
Any of the four cells may become the operational primary.

### E1S — Multimodal structured-action policy

The model receives selected evidence and returns a strict structured response:
revisable state update, hypothesis updates, intent, subgoal, one-to-four
actions, observable predictions, stop conditions, and optional memory updates.

Validation repairs syntax only, rejects unsupported fields, validates actions
and display coordinates, enforces queue limits, and falls back without
inventing an action.

### E1C — Bounded analysis workspace

The model may write analysis code against read-only evidence APIs. The
workspace:

- Has no network access.
- Cannot read environment variables, credentials, arbitrary filesystem paths,
  or production objects.
- Cannot install packages.
- Uses bounded CPU time, memory, output bytes, and invocation count.
- Receives immutable copies or serialized evidence from its assigned R or F
  observation arm.
- Runs in a separately launched process and disposable directory.
- Cannot call `arc_env`, submit actions, mutate state, or persist executable
  state between games.
- Returns only a structured proposal through the E1S validation boundary.

AST filtering and import allowlists are not treated as isolation. Model-authored
Python proceeds only if the target runtime demonstrates sanitized environment,
explicit input/output descriptors, disposable filesystem, process limits, and
enforceable filesystem/process restrictions.

If those guarantees are unavailable, E1C becomes **safe-operations E1C**: the
model composes a fixed, non-Turing-complete set of array and evidence-query
operations. This remains a first-class E1 treatment rather than being replaced
by E1S by default.

### E1 decision

Compare official RHAE, paired per-game differences, score per inference-second,
coverage, failures, storage, and tail regressions across the four cells and the
reproducible E0W controls. If different base models are used, label the result
as a model-plus-harness bundle and run a same-model comparison where possible.

Assign accepted, provisional, rejected, and operational statuses according to
Sections 3.4–3.5. Complete the decision table before Phase 2.

## 6.11 Bounded hypotheses and controller modes

Maintain two to four active hypotheses, each with:

- Claim and scope.
- Supporting and contradicting transition IDs.
- Observable predictions.
- Cheapest distinguishing probe.
- Expected progress, reversibility, and risk.
- Complexity, exception count, and status.

Controller modes are deterministic:

| Mode | Behavior |
|---|---|
| Bootstrap | Start/reset legally and capture initial evidence |
| Normal | One proposal and one action under uncertainty |
| Fast | Continue a verified short queue with minimal model work |
| Deep | Retrieve evidence and spend a bounded deeper request |
| Recovery | Cancel queues and choose safe novel evidence |
| Exhausted | Use deterministic fallback only |
| Done | Stop after win or hard global deadline |

The model may describe intent but cannot select controller mode or override
budgets.

## 6.12 Prediction-checked execution

- Use one action in Bootstrap, Deep, Recovery, and uncertain Normal operation.
- Permit up to four queued actions only when relevant dynamics are verified and
  every action has an observable prediction.
- Check each real transition, including animation evidence, before continuing.
- Cancel on mismatched status, legal actions, region structure, visible change,
  animation event, or progress.
- Preserve and retrospect on level-completing transitions.
- Do not treat an accidental win as verified mechanics.

## 6.13 Competition-parity runner

`scripts/play_competition_like.py` provides two explicit backends:

1. **Official backend:** uses the official API and
   `OperationMode.COMPETITION` when available.
2. **Instrumented local backend:** emulates the same lifecycle invariants for
   deterministic tests but is labeled emulation and never presented as an
   official competition-mode result.

Both enforce:

- One scorecard for the run.
- At most one `make` per environment.
- A fixed evaluation inventory established before play.
- Untouched and failed-to-start games included as zero.
- No scorecard access until close.
- RESET interpreted as a level reset under competition rules.
- One concurrent agent client per game unless a measured alternative is used.
- Exact global and per-game deadlines.
- Close/finalization in cleanup paths.

The parity report includes invariant checks, missing-game accounting, reset
semantics, payload isolation, thread completion, and scorecard closure. A
Kaggle end-to-end smoke submission remains the authoritative deployment check.

## 6.14 Shared inference and score-aware allocation

The service provides exactly-once initialization, request isolation, bounded
queues, cancellation, deadlines, exception containment, and queue/service/
token/memory telemetry.

Every game receives a measured initial service floor because all games count.
Remaining calls come from a shared pool with aging and starvation bounds.

Rank discretionary work by estimated incremental RHAE per inference-second
using policy-legal information only:

    next_level = levels_completed + 1
    normalized_level_weight =
        next_level / (win_levels * (win_levels + 1) / 2)

    estimated_marginal_utility =
        estimated_probability_of_next_level_completion
        * normalized_level_weight
        * estimated_squared_action_efficiency
        / expected_remaining_inference_and_environment_time

Human baseline values from held-out/evaluation metadata may not enter the
estimate. `estimated_squared_action_efficiency` is a policy-legal proxy
calibrated on development games; it is not computed from a held-out human
baseline. Apply the service floor, aging, starvation bound, and deadline guard
after utility ranking so uncertain games cannot be permanently excluded.

Batching or multiple workers are accepted when they improve sustained
closed-loop RHAE within memory and deadline ceilings.

## 6.15 Conditional advanced work

Enter E7 after a measured failure is attributable to unstable identity
tracking that simpler delta, animation, or region features cannot resolve.

Enter E8 when a compact state exists, relevant predictions are accurate,
failure is attributable to planning, and expected RHAE gain fits remaining
compute. Search never bypasses real-transition verification.

# 7. Sequential implementation schedule

## Phase 0 — Correctness, partition, packaging, and E0

**Dates:** September 4–6

Deliverables:

- Git initialization and ignore audit.
- Account/credential preflight without committing secrets.
- Frozen public inventory and predeclared non-semantic 15/5/5 partition.
- Compatibility record and three deployment-manifest schemas.
- Provenance and license records for candidate E0W-S and E0W-C controls.
- Multi-file notebook packaging skeleton.
- Frozen `ActionDecision` and request-local submission.
- ACTION6 `ScenePoint`/`DisplayPoint` separation.
- Exact action limit and guarded lifecycle.
- Legal deterministic fallback.
- Production-valid raw minimal observation path.
- Sequential and concurrent payload-isolation tests.
- Competition-parity runner skeleton and lifecycle contract tests.
- First valid E0 Kaggle submission and reproducibility smoke tests for both E0W
  controls.

Exit gate:

- Zero invalid actions and uncaught exceptions in three development runs.
- Zero ACTION6 coordinate/reasoning crossover.
- Deterministic traces for fixed seeds.
- One-`make`, one-scorecard, no-live-score, and all-games-count tests pass.
- Kaggle offline smoke test succeeds with declared artifacts.
- E0W-S and E0W-C either reproduce under equal-ceiling profiles or are marked
  non-reproducible with the blocking evidence retained.

## Phase 0F — Minimal shared evidence foundation

**Dates:** September 7–9

Deliverables:

- Immediate `uint8` frame packing.
- Prioritized streaming content-addressed evidence prototype.
- Bounded in-memory rings replacing unbounded framework history.
- Canonical frame and stable hashes.
- Minimal inter-frame/inter-action deltas.
- Minimal deterministic animation summary.
- Minimal connected regions and ACTION6 display candidates.
- Strict shared E1 evidence serialization.
- Measured preliminary RAM/disk byte ceilings.
- Explicit R/F observation toggles with no E0F leakage into the raw arm.

Exit gate:

- E1S and E1C can consume the R and F observation APIs without changing their
  action boundary.
- Evidence selected for exact retention round-trips byte-for-byte.
- Synthetic frame/animation/candidate tests pass.
- Memory does not grow with action count beyond configured rings and store
  indexes.
- Storage pressure follows the declared priority order, emits degradation
  telemetry, and does not terminate an otherwise viable game.

## Phase 1 — Model, representation, and paradigm decision

**Dates:** September 10–14

Deliverables:

- Target-accelerator model and quantization profiles.
- Minimal shared inference service.
- E1S structured-action treatment.
- Isolated-Python E1C when enforceable, otherwise safe-operations E1C.
- Image/grid representation comparison.
- Shared E0F animation-input policy.
- Paired four-cell `E1S-R`/`E1S-F`/`E1C-R`/`E1C-F` closed-loop report against
  E0 and the reproducible E0W controls.
- Paradigm, observation, and interaction-effect estimates.
- Accepted/rejected/inconclusive statistical classification.
- Accepted/provisional/E0W-primary/E0-fallback operational classification.
- Completed mandatory decision table.
- Offline model/tokenizer/native dependency notebook.

Exit gate:

- All E1 treatments satisfy safety and resource validation or are rejected.
- The decision table has no missing fields.
- One operational primary is designated under Section 3.5 without assuming
  E0F is beneficial.
- The full-run projection fits time, VRAM, RAM, disk, artifact, and license
  ceilings.
- Infrastructure may continue under provisional status; H1 and final selection
  may not.

## Phase 2 — Advanced evidence, animation, and continuity

**Dates:** September 15–18

Deliverables:

- Advanced appearance/disappearance/motion summaries.
- Selective animation crop/timeline exposure.
- Production evidence retrieval.
- Durable, scratch, and rejected-hypothesis memory.
- Level-boundary retrospection.
- E2 through E4 paired ablations.
- Final measured evidence byte ceilings.

Exit gate:

- Mandatory retained evidence remains recoverable within configured limits;
  optional exact animation sequences expose explicit availability status.
- Animation summaries pass synthetic correctness tests.
- Rich animation is exposed only by recorded triggers.
- Treatments retain their statistical classifications; inconclusive
  infrastructure may be used provisionally but not called accepted.

## Phase 3 — Hypotheses and guarded plans

**Dates:** September 19–22

Deliverables:

- Bounded evidence-linked hypotheses.
- One-action discriminating probes.
- Outcome, structural, and animation prediction checks.
- One-to-four-action verified queues.
- Full deterministic controller modes.
- E5/E6 paired comparisons.
- Accepted cross-validated development-set RHAE improvement over the strongest
  reproducible competitive control before H1.
- One best-effort sealed H1 catastrophic-regression evaluation.

Exit gate:

- The architecture entering H1 has accepted cross-validated development
  evidence against the strongest reproducible control.
- Incorrect queues stop after one mismatching action.
- H1 outputs only the sealed aggregate schema and makes no five-game
  significance claim.
- H1 records cleanup status under the best-effort sealed property.

## Phase 4 — Competition scheduling and load behavior

**Dates:** September 23–25

Deliverables:

- Measured per-game service floor and discretionary pool.
- Incremental-RHAE-per-second priority scheduling.
- Starvation bounds and deadline degradation.
- Batching/worker topology experiment.
- Full competition-parity concurrent runner.
- 110-client inference, storage, and failure-injection tests.
- Updated full-run projection.

Exit gate:

- No game crashes or indefinite starvation.
- Model/workspace/storage failures degrade legally.
- Competition invariants pass under concurrent load.
- Projected runtime remains below 7.65 hours.

## Phase 5 — Evidence-driven advanced work

**Dates:** September 26

Eligible treatments include E7 correspondence, E8 executable transition
functions, structural replay, verified search, or bounded specialist requests.
Each retains accept/reject/inconclusive classification and may not bypass
safety, evidence, or competition-mode gates.

## Phase 6 — Candidate selection and freeze

**Dates:** September 27–28

Deliverables:

- Conservative and higher-reasoning candidates.
- Accepted cross-validated development evidence against the strongest
  reproducible competitive control for every candidate entering H2.
- One best-effort sealed H2 guardrail evaluation under the predeclared
  deterministic selection rule, without a significance claim.
- Selected artifact with hashes and complete profiles.
- Candidate freeze by September 28.

## Phase 7 — Release and submission verification

**Dates:** September 29–30

Use this window for infrastructure recovery, mount verification, public
notebook/repository publication, license checks, reproduction checks, and final
milestone submission. Do not add unmeasured policy changes after freeze.

The deadline is September 30 at 11:59 PM UTC, corresponding to October 1 at
7:59 AM China Standard Time.

# 8. Evaluation and tests

## 8.1 Unit tests

- Stable seed derivation across processes.
- Legal-action normalization and exact cap semantics.
- Immutable decisions and absence of production `set_data()` calls.
- `ScenePoint` to `DisplayPoint` mapping and `0..63` wire validation.
- Concurrent unique ACTION6 payload isolation.
- Packed grid/frame-sequence hash determinism.
- Exact pack/compress/retrieve round-trips.
- Bounded in-memory ring behavior.
- Mandatory retention-priority and optional-evidence availability behavior.
- Storage-pressure degradation without game termination.
- Inter-frame transient, appearance, disappearance, and motion cases.
- Inter-action movement, recoloring, creation, deletion, and scene boundaries.
- Selective animation triggers and token accounting.
- Click candidates across crops, rectangular regions, and display space.
- Context-scoped no-change penalties.
- Strict model/workspace response validation.
- Python isolation or fixed safe-operation restrictions.
- Queue cancellation on every mismatch class.
- Evaluator-only baseline isolation.
- Official RHAE fixture parity.
- Paired statistical report and provisional-status separation.
- Sealed output allowlist, cleanup-status reporting, startup scrubbing, and
  best-effort cleanup across enumerated testable failure classes.

## 8.2 Competition-parity integration tests

- One scorecard is opened and closed exactly once.
- Each environment is made at most once.
- No in-flight score call is possible.
- RESET uses level-reset semantics.
- Untouched, failed, and timed-out games count as zero.
- All clients terminate before global close.
- Missing games and duplicate identifiers fail validation.
- Official and emulated backends are labeled distinctly.
- Scorecard closes after agent exceptions and interrupts.

## 8.3 Deployment and failure integration tests

- Missing username, token, source, model, wheel, tokenizer, or license.
- Framework/SDK compatibility mismatch.
- Model unavailable, timeout, cancellation, malformed output.
- Workspace timeout, forbidden operation, oversized output, crash.
- Exactly-once model initialization under concurrent construction.
- Level transition during a queue.
- GAME_OVER, reset exhaustion, global deadline, clean termination.
- 110 simultaneous inference clients with starvation bounds.
- Evidence-store concurrency, byte ceilings, disk-full simulation, retention
  priority, and continued legal play after degradation.
- Clean-checkout local bootstrap with declared dependencies.
- Clean-checkout Kaggle offline run with declared mounts.
- Best-effort sealed H1/H2 run with raw data outside notebook output paths,
  aggregate-only retained output, and explicit cleanup status.

## 8.4 Closed-loop experiments

| Treatment | Primary paired comparison |
|---|---|
| E0 | Correct deterministic fallback vs current random policy |
| E0W-S | Reproduced structured-action competitive control vs E0 |
| E0W-C | Reproduced workspace competitive control vs E0 and E0W-S |
| E1S-R | Structured policy with raw minimal observations vs E0W controls |
| E1S-F | Structured policy with E0F vs E1S-R and E0W controls |
| E1C-R | Workspace policy with raw minimal observations vs E1S-R and E0W controls |
| E1C-F | Workspace policy with E0F vs E1C-R, E1S-F, and E0W controls |
| E1 factorial | Paradigm, observation, and interaction effects across all four cells |
| E2a | Advanced inter-action evidence vs E0F |
| E2b | Advanced animation summary vs E0F summary |
| E2c | Selective rich animation vs summary-only input |
| E3 | Durable/scratch memory vs bounded recent history |
| E4 | Exact retrieval/retrodiction vs summary-only context |
| E5 | Bounded hypotheses vs one unconstrained explanation |
| E6 | Prediction-checked queues vs one model call per action |
| E7 | Advanced correspondence vs lightweight regions |
| E8 | Verified model/search/specialist vs selected E6/E7 |

Fixed trajectories may test correctness and cost. Policy acceptance requires
paired closed-loop rollouts and development cross-validation. Zero-score
diagnostics may justify provisional infrastructure advancement but not final
selection. Final policy claims are anchored to the strongest reproducible E0W
control rather than E0 alone.

## 8.5 Required reporting

Every development experiment report includes:

- Mean official RHAE over the full fixed set.
- Paired per-game differences and uncertainty.
- `delta_min`, acceptance rule, and statistical classification.
- Separate implementation status, including provisional status when used.
- Non-zero coverage, full games, weighted completion, and levels.
- Actions per completed level and before first progress.
- Invalid, no-change, repetition, reset, and death rates.
- Prediction accuracy, queue breaks, memory revisions.
- Animation triggers, extra tokens, and RHAE per token/second.
- Model/workspace/fallback rates.
- Calls, tokens, queue wait, latency, RAM, VRAM, evidence bytes, and runtime.
- Worst per-game regression and catastrophic-tail status.

Sealed H1/H2 reports emit only the predeclared aggregate subset and never raw or
per-game developer-visible evidence. Five-game intervals are descriptive;
reports contain no positive statistical-significance decision.

## 8.6 Run artifacts

Development runs archive source commit/dirty status, manifests, hashes,
accelerator/runtime versions, partition/seeds, experiment record, decision
table, machine-readable metrics, exact evidence references, and closed
scorecard.

Sealed runs retain only hashes, aggregate metrics, redacted validity codes, and
cleanup status. Their raw evidence is placed in the process-private temporary
directory and subjected to the best-effort cleanup property in Section 4.3.

# 9. Merge and escalation gates

Accept infrastructure work when it eliminates a reproduced failure, preserves
policy performance within the declared margin, and remains within resource
ceilings. An inconclusive policy treatment may use infrastructure
provisionally when Section 3.5 permits it.

Accept policy improvement claims only under Section 3.4. Reject or defer when:

- It has not been compared with the strongest reproducible E0W control.
- Gain occurs on one exposed game only.
- It depends on a best seed or selective rerun.
- It improves only an offline proxy.
- It violates paired resource ceilings.
- It exceeds runtime, RAM, VRAM, disk, or evidence-byte limits.
- It reduces the guaranteed service floor below the measured minimum.
- It adds an unvalidated control path or coordinate transform.
- It crosses the catastrophic tail threshold.
- It requires ordinary H1/H2 tuning.
- It leaks sealed frames, prompts, responses, logs, or per-game results.

# 10. Principal risks and controls

| Risk | Control |
|---|---|
| 110-game execution is confused with leaderboard scoring | Separate coverage from public/private 55-game aggregation |
| Random E0 makes weak gains look competitive | Reproduce E0W-S and E0W-C controls |
| E0F is confounded with agent paradigm | Run the E1 paradigm/observation 2×2 comparison |
| E1 comparison depends on later features | Freeze R and E0F before E1 |
| Zero RHAE deadlocks infrastructure | Explicit provisional advancement |
| Provisional evidence becomes a performance claim | Final selection requires accepted gain over the strongest reproducible control |
| Local runner diverges from Kaggle | Competition-parity runner plus Kaggle smoke |
| Public baseline leaks to policy | Evaluator-only metrics boundary |
| Five-game holdout is treated as significant | H1/H2 are guardrails; development cross-validation owns acceptance |
| Holdout evidence leaks through logs/artifacts | Best-effort sealed isolation, redaction, and cleanup status |
| Sealed cleanup is stated as absolute | Explicit failure-class limits and no absolute deletion claim |
| Partition uses semantic information | Predeclared inventory-only fields |
| Framework history exhausts RAM | Packed streaming store and bounded rings |
| Evidence cap forces silent loss or game termination | Priority retention, degradation telemetry, and continued play |
| Final frame hides causal evidence | Mandatory animation summary |
| Rich animation consumes excess compute | Triggered exposure and cost accounting |
| Wrong paradigm is hardened early | Retained four-cell E1 measured bake-off |
| Python workspace becomes unsafe | Demonstrated OS isolation or safe operations |
| Shared enum state crosses threads | Frozen decisions and fresh payloads |
| Crop coordinates reach the API | Typed transforms and display validation |
| Inference starves games | Service floor, aging, deadlines |
| Scheduler favors games merely because they have more levels | Normalize next-level weight within each game |
| Search trusts a false model | Prediction gate and real-action replanning |

# 11. Next 72 hours

Execute in this order:

1. Initialize Git and audit ignored secrets/artifacts.
2. Complete account, token-presence, rules, and attachment preflight.
3. Freeze the 25-game inventory and 15/5/5 partition using only permitted
   metadata; keep `ls20` and `vc33` in development.
4. Select, license-audit, and reproduce E0W-S and E0W-C competitive controls.
5. Add source, dependency, model, control, and sealed-output schemas.
6. Extend notebook packaging for multiple modules and mount validation.
7. Implement frozen `ActionDecision`, exact caps, and request-local submission.
8. Add typed ACTION6 display coordinates and transform validation.
9. Remove global RNG, unstable seeding, game-ID policy, and static action lists.
10. Add guarded lifecycle and concurrent payload-isolation tests.
11. Add the competition-parity runner contract and official-backend smoke path.
12. Implement the production-valid raw minimal observation path.
13. Implement `uint8` packing, bounded rings, hashes, priority retention, and
    non-terminal evidence-degradation telemetry.
14. Implement toggleable E0F deltas, animation summaries, regions, and click
    candidates without contaminating the raw observation arm.
15. Produce deterministic E0, E0W, R, and F runs and the first valid Kaggle
    submission.
16. Begin four-cell E1 model and accelerator profiling.

# 12. Definition of done

Plan 6 is implemented when:

- Both reproduction contracts pass with declared inputs.
- Production policy contains no public-game IDs or solution tables.
- No production path mutates `GameAction` state.
- Every action is legal, request-local, bounded, and recorded.
- ACTION6 validates API display coordinates in `0..63` and never submits
  unmapped crop/logical coordinates.
- Exact action/reset/retry semantics are tested.
- Competition parity enforces one scorecard, one `make`, no live score, level
  reset semantics, and zeroes for untouched games, while reports distinguish
  110-game execution coverage from the two 55-game leaderboard aggregations.
- A 110-client test shows no crossover or indefinite starvation.
- The upstream unbounded Python frame history is replaced.
- Retained frames are stored as packed `uint8` with streaming deduplication and
  bounded RAM.
- Evidence follows action/metadata → final frame → compact delta → bounded
  intermediate summary → optional complete sequence priority.
- Storage pressure emits degradation telemetry and never terminates an
  otherwise viable game.
- Human baselines are evaluator-only.
- Official RHAE calculations match the toolkit.
- E0W-S and E0W-C are reproducible, provenance-recorded competitive controls;
  a non-reproducible published control has been replaced by a validated,
  provenance-recorded reference implementation of its published method.
- Raw minimal R and engineered E0F F paths are independently production-valid.
- The four E1 cells isolate paradigm, observation, and interaction effects.
- E1S and E1C share evidence and resource ceilings within each observation arm.
- E1 outcome and operational status are recorded separately.
- Provisional advancement never appears as accepted performance.
- Final candidates demonstrate accepted cross-validated development improvement
  over the strongest reproducible competitive control, or accepted gain from a
  predeclared combination with it.
- Every multi-frame response receives deterministic animation analysis.
- Rich animation reaches the model only through budgeted triggers.
- Model-facing state is bounded and evidence-linked.
- Python workspace isolation is demonstrated or E1C uses fixed safe operations.
- Model/workspace failure produces a legal fallback.
- Incorrect queued predictions stop after one mismatch.
- H1/H2 are catastrophic-regression guardrails and make no five-game
  significance claims.
- H1/H2 use best-effort sealed mode, place raw data outside notebook output
  directories, retain only hashes, aggregate metrics, redacted validity codes,
  and cleanup status, and state the failure classes cleanup cannot guarantee.
- The partition remains 15 development, 5 H1, and 5 H2.
- Final artifacts pass unit, integration, sealed, concurrent-load,
  offline-notebook, and closed-loop gates.
- Competition-like runtime remains below 7.65 hours.
- Prize-eligibility materials are public under compatible licenses before the
  milestone deadline when eligibility is pursued.

# 13. Primary references

- Kaggle competition:
  https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3
- Kaggle data and 110-game evaluation:
  https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data
- ARC-AGI-3 documentation: https://docs.arcprize.org/
- Game schema: https://docs.arcprize.org/game-schema
- Actions: https://docs.arcprize.org/actions
- Scoring methodology: https://docs.arcprize.org/methodology
- Competition mode: https://docs.arcprize.org/toolkit/competition_mode
- Official toolkit: https://github.com/arcprize/ARC-AGI
- Official agent framework: https://github.com/arcprize/ARC-AGI-3-Agents
- Milestone 1 review:
  https://arcprize.org/blog/arc-prize-2026-milestone-1
- Animation experiment:
  https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/734369
