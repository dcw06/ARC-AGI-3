---
title: "ARC Prize 2026 — ARC-AGI-3"
subtitle: "Plan 7: Normative, Experiment-Valid, Transaction-Safe Implementation"
author: "Project Team"
date: "4 September 2026"
status: "Active — normative execution successor to Plan 6"
---

# Document purpose and authority

This document is the sole normative implementation and experiment plan for the
ARC-AGI-3 project. It supersedes Plans 2–6 for execution, experiment naming,
acceptance decisions, deployment, and definition of done.

The strategic plan and Plans 2–6 remain background and design-history records.
They may explain why a decision exists, but they do not override Plan 7. When a
conflict exists, Plan 7 controls. Findings discovered after this document is
activated must be recorded as a dated amendment or a new plan rather than
silently changing an experiment definition.

Plan 7 preserves Plan 6's full intended research scope and central
architecture:

- Deterministic code owns evidence, legal actions, budgets, lifecycle,
  validation, scheduling, and safety.
- A local model owns uncertain interpretation, hypotheses, goals, and proposed
  plans.
- Structured-action and bounded-workspace paradigms receive a controlled
  same-model comparison.
- Raw and engineered observation treatments remain independently
  production-valid.
- Evidence retention is bounded, explicit, and degradation-safe.
- Advanced correspondence, executable models, search, and specialist calls
  remain conditional measured treatments.

Plan 7 adds twelve normative corrections:

1. One document and one versioned registry own experiment identifiers.
2. Published reproduction, normalized control, and competition-candidate
   results are different result classes.
3. The E1 2×2 factorial is causal only when all four cells use the same model
   and matched inference settings.
4. Statistical decisions use a frozen protocol with game-level units,
   hierarchical testing, explicit crash handling, and selection-aware claims.
5. Live environment actions use a write-ahead journal and are never blindly
   retried after an ambiguous dispatch.
6. Predictions use a typed predicate language and three-valued evaluation.
7. Controller modes use an explicit deterministic transition table.
8. Evidence guarantees distinguish live safety state, normally mandatory
   evidence, optional exact evidence, and degraded availability.
9. Kaggle hidden execution has an output allowlist and ephemeral raw evidence.
10. Runtime accounting distinguishes global elapsed time from component busy
    time and queue time.
11. Scheduling uses a defined baseline-free expected-value proxy; all-game
    accounting does not imply an unconditional model call for every game.
12. Current competition constraints are stored in a dated register and
    revalidated before every submission.

The plan assumes one primary implementer. Its ordering expresses technical and
experimental dependencies, not a reduction of the intended research scope.

# 1. Verified starting state

As of September 4, 2026:

- agent/my_agent.py is a random policy with an ls20-specific branch.
- It seeds module-global randomness from wall-clock time and Python hash().
- It enumerates GameAction members rather than the current legal-action set.
- It mutates shared GameAction enum instances with set_data() and reasoning.
- The upstream loop uses action_counter <= MAX_ACTIONS, making its apparent cap
  off by one.
- The official framework creates one agent thread per game and retains an
  unbounded Python frame list by default.
- scripts/play_local.py uses OperationMode.NORMAL and executes games
  sequentially. It is not a competition-parity runner.
- The notebook builder packages only my_agent.py and installs only arc-agi and
  python-dotenv from the competition wheelhouse.
- notebooks/kernel-metadata.json contains a username placeholder and has no
  attached model or dependency sources.
- .kaggle/access_token is absent and must remain ignored and untracked when
  supplied.
- Public payloads for ls20 and vc33 are downloaded. Both are exposed and belong
  in the development partition.
- The 25 public identifiers have been listed without opening the remaining
  environments.
- The workspace is not a Git repository.
- The current local environment contains arc-agi 0.9.9 and arcengine 0.9.3;
  those versions are observations, not permanent pins until compatibility with
  the Kaggle-mounted framework is verified.

Before the first submission:

- Accept the current competition rules.
- Supply and validate the correct Kaggle account and kernel identifier.
- Verify that the token exists, is non-empty, has restrictive permissions, and
  is ignored.
- Attach the competition, wheel, source, tokenizer, model, and native-library
  artifacts required by the selected candidate.
- Disable internet in notebook metadata.
- Verify the effective submission allowance in the Kaggle account.

# 2. Competition contract

## 2.1 Dated constraint register

Maintain config/competition_constraints.yaml. Every entry contains:

- value;
- source URL or platform observation;
- verified_at timestamp;
- verifier;
- whether the value is a hard rule, platform behavior, or internal target;
- next required revalidation event.

The initial September 4 register must include:

| Constraint | Initial value |
|---|---|
| Submission mechanism | Kaggle notebook only |
| Hard CPU/GPU runtime | 9 hours |
| Internet | Disabled |
| External inputs | Freely and publicly available data/models, subject to current rules and licenses |
| Evaluation inventory | 110 unseen games |
| Leaderboard split | 55 public and 55 private |
| Competition mode | Forced |
| Scorecards | One |
| Environment creation | At most one make per environment |
| In-flight score access | Unavailable |
| Reset behavior | Level reset; full game reset unavailable |
| Current operational submission allowance | One submission per day; revalidate on the account |
| Final selections | Up to two; revalidate before final selection |
| Current accelerator | RTX-class competition machine, presently g4-standard-48; revalidate before profiling and submission |
| Milestone 2 deadline | September 30, 2026 at 11:59 PM UTC |
| Final deadline | November 2, 2026 at 11:59 PM UTC |
| Milestone publication | Public notebook and required open-source materials by the applicable deadline |

If a live rule, Kaggle platform behavior, official scorer, or mounted framework
conflicts with this register, stop submission preparation, update the dated
entry, run compatibility tests, and record the change. Do not silently preserve
an obsolete value.

## 2.2 Scoring objective

For a completed level l:

    level_score_l =
        min(1.15, (human_baseline_actions_l / agent_actions_l)^2)

An uncompleted level contributes zero. A game score is the level-index-weighted
aggregation of its level scores, capped by its weighted completed-level
fraction. Total score is the mean over the relevant game split.

The September milestone objective is public-leaderboard RHAE. The final
competition objective is private-leaderboard RHAE. The agent must attempt valid
execution coverage across all 110 environments even though the two
leaderboards aggregate different 55-game splits.

Human baseline values belong exclusively to evaluator code. They may not enter:

- prompts or model-visible evidence;
- model workspaces;
- controller state;
- action selection;
- inference allocation;
- scheduling features;
- learned scheduler targets or coefficients.

The official Kaggle scorer and currently mounted official toolkit are
authoritative. A local implementation is a tested replica, never an authority.
Record the scorer/toolkit version and fixtures for every experiment.

## 2.3 Submission-output contract

The required submission file is platform-generated. Production output uses an
explicit allowlist:

- the required submission artifact;
- source and dependency manifests when allowed;
- aggregate non-sensitive lifecycle telemetry approved by the current rules;
- no hidden frames, grids, animations, game-specific trajectories, prompts,
  model responses, hypotheses, reasoning transcripts, recordings, or per-game
  hidden diagnostics.

Notebook cell output, logging handlers, exception rendering, framework
recording, profiler output, temporary directories, and final filesystem state
must all obey the same contract.

# 3. Executive architecture

## 3.1 Authority boundary

Deterministic code owns:

- canonical observations and evidence availability;
- legal-action normalization;
- action payload construction;
- coordinate conversion;
- write-ahead action journaling;
- exact counters and deadlines;
- model and workspace validation;
- prediction evaluation;
- controller modes;
- inference admission and scheduling;
- competition lifecycle;
- reporting and artifact policy.

The model may propose:

- current goal and subgoal;
- mechanics and uncertainty;
- competing hypotheses;
- evidence requests;
- discriminating probes;
- one action or a short predicted plan;
- memory additions, revisions, or retirements;
- bounded analysis code or safe operations in E1C.

The model may not:

- call arc_env;
- mutate production or evaluator state;
- select its own resource budget;
- select the controller mode;
- declare its own hypothesis verified;
- expose evaluator-only human baselines;
- bypass legal-action or coordinate validation;
- decide what hidden-run data persists.

## 3.2 Dependency path

    G0 governance, constraints, reproducibility, and artifact policy
      -> E0 legal deterministic fallback and transaction-safe execution
      -> published and normalized E0W competitive controls
      -> R raw observation path and F E0F observation path
      -> same-model E1 2x2 factorial or explicitly non-causal bundle tournament
      -> selected accepted or provisional operational primary
      -> E2 advanced evidence, animation, and correspondence
      -> E3 compact cross-level memory
      -> E4 exact retrieval and retrodiction
      -> E5 bounded hypotheses and discriminating probes
      -> E6 prediction-checked short queues
      -> E7 conditional executable model or scripts
      -> E8 conditional search over a verified model
      -> E9 conditional specialist request
      -> score-aware shared scheduling and frozen candidates

Learned perception, reinforcement learning, test-time parameter adaptation, and
other extensions may be introduced through the same treatment registry. They
do not bypass the evidence, safety, statistics, or deployment contracts.

# 4. Normative registries and reproducibility

## 4.1 Required registries

Maintain these machine-readable artifacts:

| Artifact | Authority |
|---|---|
| config/competition_constraints.yaml | Current external and internal constraints |
| config/experiment_registry.yaml | Experiment IDs, factors, controls, status, and supersession |
| config/statistics_protocol.yaml | Folds, seeds, estimators, thresholds, multiplicity, and crash handling |
| config/control_registry.yaml | Published and normalized controls |
| config/model_manifest.yaml | Models, tokenizers, quantization, engines, license, and hashes |
| config/source_manifest.yaml | Files and source hashes packaged into notebooks |
| config/dependency_manifest.lock | Exact Python/native dependencies and hashes |
| config/runtime_profiles.yaml | Hardware-specific measured limits |
| config/output_policy.yaml | Local, sealed, and Kaggle production persistence rules |
| config/prediction_schema.json | Allowed prediction predicates and validation |
| config/action_journal_schema.json | Action transaction states and fields |
| config/sealed_output_schema.json | Aggregate-only H1/H2 output |

Every experiment result references immutable versions or hashes of all
applicable registries.

## 4.2 Reproduction modes

Support:

1. Local bootstrap: a clean checkout plus declared network-fetched or
   pre-cached dependencies and selected development environments.
2. Kaggle offline reproduction: a clean checkout plus declared mounted
   competition, dependency, model, tokenizer, and native artifacts, without a
   runtime secret or internet.

Never claim that a clean checkout is self-contained when mounted artifacts are
required.

Record one of three reproducibility levels:

- Bitwise: identical output bytes are expected and tested.
- Seed-stable: control flow and decisions are stable for a fixed seed within a
  declared platform, but numeric/model details may differ.
- Distributional: stochastic GPU/model output is not bitwise stable; the
  declared repeated-run distribution is the reproducibility target.

The reproducibility level must be stated separately for deterministic code,
model inference, and end-to-end play.

## 4.3 Source and artifact discipline

Before policy development:

- Initialize version control.
- Ignore secrets, environment payloads, recordings, caches, generated
  notebooks, temporary evidence, and model caches.
- Pin Python, arc-agi, arcengine, framework revision, notebook builder,
  inference engine, Python packages, native libraries, model, tokenizer,
  quantization, prompts, and configuration.
- Hash all mounted artifacts.
- Test compatibility with the exact Kaggle-mounted framework.
- Fail notebook construction on missing files, duplicate destinations,
  unresolved placeholders, hash mismatches, missing licenses, or undeclared
  runtime downloads.

# 5. Controls and experiment registry

## 5.1 Result classes

Do not use one label for incompatible forms of evidence.

- Published reproduction: preserves the published model-plus-harness as
  closely as competition compatibility permits.
- Normalized control: runs a control harness with a common selected model and
  matched ceilings for causal comparison.
- Competition candidate: the complete bundle submitted for score, regardless
  of whether its components support a causal claim.

A published reproduction may establish competitiveness. Only a normalized
same-model comparison may establish a harness or observation-factor effect.

## 5.2 Initial controls

Freeze an as-of-date eligible candidate set in control_registry.yaml. Initial
sources include:

- A structured vision/action system based on the strongest reproducible
  open-source Reki/forge-style method.
- A bounded code/workspace system based on the strongest reproducible
  open-source Duck-style method.
- Any stronger publicly available and license-compatible Kaggle method
  identified before the control-registry cutoff.

For every control, record:

- result class;
- source URL and immutable revision;
- author and license;
- original model and normalized model, if different;
- prompt and harness hashes;
- artifact hashes;
- compatibility patches;
- hardware and engine;
- action, call, token, time, and evidence ceilings;
- reproduction result and known deviation from the publication.

The strongest reproducible control means the highest full-set mean official
RHAE among the frozen eligible controls under the applicable comparison
profile. Coverage, catastrophic tail behavior, reliability, and cost break
ties in that order. It does not mean the strongest method that might exist
somewhere outside the frozen candidate set.

A later public control is added under a new registry version and used
prospectively. It does not retroactively change a classified historical
experiment.

## 5.3 Canonical treatment identifiers

| ID | Treatment |
|---|---|
| E0 | Correct deterministic fallback and full execution path |
| E0W-S-PUB | Faithful published structured-action reproduction |
| E0W-C-PUB | Faithful published workspace reproduction |
| E0W-S-NORM | Structured normalized same-model control |
| E0W-C-NORM | Workspace normalized same-model control |
| E1S-R | Structured policy with raw minimal observations |
| E1S-F | Structured policy with E0F engineered observations |
| E1C-R | Bounded workspace with raw minimal observations |
| E1C-F | Bounded workspace with E0F engineered observations |
| E2a | Advanced inter-action evidence |
| E2b | Advanced animation summary |
| E2c | Selective rich animation |
| E2d | Advanced correspondence and identity tracking |
| E3 | Durable/scratch/rejected-hypothesis memory |
| E4 | Exact retrieval and evidence-grounded retrodiction |
| E5 | Bounded competing hypotheses and discriminating probes |
| E6 | Prediction-checked one-to-four-action queues |
| E7 | Conditional executable transition model or scripts |
| E8 | Conditional search over a verified model |
| E9 | Conditional specialist request |

An experiment ID is never reused for a different treatment. Revisions append a
version suffix in the registry, such as E6.v2, while preserving the original
record.

# 6. Evaluation protocol

## 6.1 Public-game partition

Before opening another public environment:

1. Record every exposed game. ls20 and vc33 belong to development.
2. Freeze the 25-game identifier inventory.
3. Record the partition algorithm, seed, and permitted inventory-only fields.
4. Assign 15 development environments, including exposed games.
5. Assign 5 H1 architecture-guardrail environments.
6. Assign 5 H2 candidate-guardrail environments.
7. Hash and archive the manifest.

Permitted stratification fields are limited to non-semantic information
available without make, frames, source, replay, or play. If a proposed field
requires exposure, do not use it.

Production policy contains no public game IDs, solution tables, or
game-specific branches.

## 6.2 Unit of generalization

The game is the unit of generalization. Multiple seeds reduce within-game
noise; they do not create additional game-level samples.

For each game and treatment:

1. Run the number of seeds frozen in the treatment record.
2. Aggregate seed results into one per-game value using the frozen estimator.
3. Compare treatment and control on paired game values.
4. Include untouched, failed, crashed, or timed-out games as zero for the
   primary full-set score unless the run meets the predeclared invalid-run rule.

The primary outcome is mean official RHAE over the entire fixed evaluation
set. Secondary outcomes are:

1. paired per-game RHAE difference;
2. non-zero coverage and fully completed games;
3. weighted level-completion fraction;
4. levels completed;
5. actions per completed level and actions before first progress;
6. prediction, exploration, reliability, and compute diagnostics.

Structural diagnostics guide engineering when score is zero. They never
replace RHAE for final candidate acceptance.

## 6.3 Frozen statistical protocol

Before an experiment family begins, statistics_protocol.yaml freezes:

- game manifest and fold manifest;
- treatment and control hashes;
- seed count and aggregation;
- primary contrast;
- minimum practical effect delta_min;
- uncertainty estimator and confidence level;
- exact sign-flip/permutation handling of ties and zero differences;
- crash, timeout, and missing-result treatment;
- non-inferiority margin for reliability-only changes;
- catastrophic tail thresholds;
- multiplicity family;
- sequential stopping or fixed sample rule;
- rerun rule;
- positive, negative, and inconclusive decision rules.

Default development analysis uses five predeclared folds of three games.
Configuration choices for an outer fold may use only the other twelve games
and previously frozen external evidence. Because the human implementer may
already know development environments, development cross-validation supports
internal selection rather than an untouched generalization claim.

H1 and H2 are five-game catastrophic-regression guardrails:

- H1 may veto an architecture for a predeclared regression, invalidity, or
  resource failure.
- H2 applies a frozen aggregate candidate rule and deterministic tie-break.
- Neither H1 nor H2 establishes a positive significance claim.
- H2 participates in selection and is therefore not an untouched estimate.
- With five nonzero paired differences, the best-case exact two-sided
  sign-flip p-value is 0.0625; ties can make the attainable resolution worse.

## 6.4 Multiplicity and selection

Use hierarchical gatekeeping:

1. Establish E0 correctness.
2. Establish reproducible competitive controls.
3. Test one predeclared primary E1 candidate contrast against the strongest
   applicable control.
4. Treat the E1 paradigm, observation, and interaction contrasts as a declared
   family and apply the frozen familywise procedure.
5. Enter E2–E9 sequentially only after their prerequisite treatment is
   operationally stable.
6. Within any set of simultaneous variants, apply Holm correction or the
   frozen alternative specified before results are observed.

Exploratory comparisons are reported as exploratory and cannot become accepted
without a prospectively registered replication.

Selecting the strongest control and the strongest candidate on the same
results creates selection optimism. Reports distinguish:

- raw candidate estimate;
- selection-adjusted or outer-fold estimate where available;
- H1/H2 aggregate guardrail result;
- Kaggle external confirmation.

## 6.5 Decision classes

Statistical status:

- Accepted: the primary improvement reaches delta_min under the frozen
  uncertainty and multiplicity rule, stays within resource ceilings, and
  avoids catastrophic tail regression.
- Rejected: materially worse, beyond a resource ceiling, or beyond the tail
  threshold.
- Inconclusive: neither accepted nor rejected.

Operational status:

- Primary.
- Provisional primary.
- Competitive-control primary.
- E0 fallback.
- Disabled.

An inconclusive result remains inconclusive. It may support provisional shared
infrastructure but may not be presented as a performance improvement.

Reliability work may be accepted after eliminating a reproduced failure while
meeting a predeclared non-inferiority margin.

## 6.6 Same-model E1 factorial

The causal E1 2×2 requires all four cells to share:

- exactly the same base model and weights;
- the same quantization and inference engine;
- the same decoding parameters and seed policy;
- matched image and text preprocessing;
- equal wall-clock, token, call, action, reset, retry, and evidence ceilings;
- the same game and seed pairs;
- the same model-service and queue policy;
- identical evidence selection within an observation arm.

The factors are:

| Cell | Paradigm | Observation |
|---|---|---|
| E1S-R | Structured action | Raw minimal R |
| E1S-F | Structured action | Engineered E0F F |
| E1C-R | Bounded workspace | Raw minimal R |
| E1C-F | Bounded workspace | Engineered E0F F |

Estimate:

- paradigm effect within R;
- paradigm effect within F;
- observation effect within S;
- observation effect within C;
- interaction effect.

If one model cannot support all four cells, do not report causal factorial
effects. Run and label a model-plus-harness bundle tournament, then perform a
separate same-model subset comparison where possible.

## 6.7 Best-effort sealed evaluation

H1/H2 run in sealed_eval mode:

- Raw frames, deltas, animations, prompts, responses, hypotheses, reasoning,
  recordings, and per-step logs live only in a process-private temporary
  directory outside output paths.
- Standard output exposes only non-visual lifecycle validity codes.
- Per-game values remain internal; retained output follows the aggregate
  sealed-output schema.
- Framework recording, debug rendering, prompt dumps, traceback locals, and
  evidence export are disabled.
- Cleanup is attempted on normal return, exceptions, handled signals, finally
  paths, external supervision, and next-start stale-directory scrubbing.
- Core dumps are disabled when possible.

Cleanup status is one of:

- verified_clean;
- cleanup_attempted;
- cleanup_unverified.

No status claims protection against SIGKILL, kernel OOM, host termination,
filesystem snapshots, swap, or platform behavior outside the process.

A sealed rerun occurs only under a predeclared invalid-run rule and only when no
usable policy result was emitted.

# 7. Runtime and resource contract

## 7.1 Clock taxonomy

Track:

- global_elapsed: authoritative monotonic time from notebook start;
- startup_elapsed: install, import, engine, model, and tokenizer load;
- model_service_busy: wall time during which the shared inference service is
  actively servicing requests;
- environment_wait: client time awaiting environment responses;
- deterministic_cpu_busy: cumulative CPU processing time;
- queue_wait: per-request and aggregate inference wait;
- client_elapsed: per-game wall time;
- finalization_elapsed: scorecard close and output verification.

Component busy and wait times may overlap and are not added to determine
deadline safety. global_elapsed is authoritative.

## 7.2 Initial envelope

| Limit | Initial target |
|---|---:|
| Kaggle hard runtime | 32,400 seconds |
| Operational completion target | 27,540 seconds |
| Startup target | 900 seconds |
| Shared model-service busy ceiling | 19,800 seconds |
| Environment/deterministic planning allowance | 3,300 seconds |
| Finalization reservation | 600 seconds |
| Operating reserve represented in the planning envelope | 2,940 seconds |
| Hard-limit buffer beyond operational target | 4,860 seconds |

The planning allowances may be used to reserve work, but admission and
shutdown decisions use global_elapsed and the finalization reservation.
Target-accelerator measurements replace provisional component ceilings while
preserving the 9-hour hard limit.

Before candidate selection, record:

- cold load and first-request time;
- sustained requests/hour under mixed 110-client traffic;
- queue and service p50/p90/p99;
- peak VRAM, host RAM, disk, and evidence bytes;
- calls and tokens per game distribution;
- time to first environment observation and first model action;
- maximum queue age;
- cancellation latency;
- projected finalization time.

## 7.3 Inference capacity

For serialized service:

    C_max = floor(B_model_service_busy / L_weighted_service)

For batching or multiple workers, use sustained completed requests per global
wall-clock second under the actual mixed workload. Include batch-formation
delay, cancellation, workspace time, and memory pressure.

Translate the measured capacity into:

- hard global call/token maxima;
- per-mode request ceilings;
- cheap bootstrap allowance;
- discretionary pool;
- maximum queue age;
- per-client soft deadline;
- global degrade and stop-admitting timestamps.

# 8. Algorithm specifications

## 8.1 Immutable action decision

The controller creates an immutable ActionDecision containing:

    action_id
    request_local_data
    request_local_reasoning
    source
    controller_mode
    expected_effect_predicates
    stop_condition_predicates
    evidence_references
    decision_id

Production code never calls GameAction.set_data() and never stores request
payloads on a shared enum instance.

Before dispatch:

1. Re-read current legal actions.
2. Validate the action ID against the normalized current set.
3. Validate ACTION6 display coordinates as integers from 0 through 63.
4. Resolve the enum member without mutation.
5. Serialize fresh data and reasoning dictionaries.
6. Validate that reasoning JSON is at most 16 KiB UTF-8 after compact
   serialization, with a configured compatibility margin.
7. Create the write-ahead journal entry.

## 8.2 Write-ahead action journal

Every decision has a monotonically increasing per-game sequence and one of:

- prepared;
- failed_pre_dispatch;
- dispatched;
- acknowledged;
- outcome_unknown.

Required sequence:

1. Atomically commit prepared to the T0 journal with the pre-state hash, legal
   actions, decision, payload hash, budget reservation, and timestamp.
2. Mark dispatched immediately before crossing the environment-call boundary.
3. Submit exactly once.
4. On a valid response, atomically mark acknowledged and attach post-state,
   response metadata, and evidence references.
5. If failure is proven to occur before dispatch, mark failed_pre_dispatch and
   release the action reservation.
6. If dispatch may have occurred but no valid response exists, mark
   outcome_unknown and count the action as spent.

Never automatically retry a live environment action after dispatched or
outcome_unknown. Model inference, parsing, and pre-dispatch construction retries
use separate counters and may never resubmit an ambiguous action.

The T0 journal must remain available in bounded memory even when durable
evidence storage is degraded. If the prepared record cannot be committed to T0,
do not dispatch the action.

Pending journal state is not discarded in finally. Cleanup closes resources but
preserves the terminal journal classification.

## 8.3 Lifecycle and cap semantics

Maintain separate counters for:

- environment actions accepted or ambiguously dispatched;
- resets;
- inference requests;
- parsing/repair attempts;
- workspace invocations;
- evidence retrievals;
- controller iterations.

Differentiate:

- official server-enforced level termination;
- project hard global deadline;
- per-game soft abandonment or degradation policy;
- framework-loop safety cap;
- model/workspace retry cap.

Do not infer or reconstruct hidden human baselines to set policy caps. An
arbitrary per-game MAX_ACTIONS must not silently terminate later levels. Cap
definitions, reset scope, and counter-reset events live in validated
configuration and are exercised by lifecycle tests.

## 8.4 ACTION6 coordinates

Use:

- ScenePoint: a logical position in a crop, detected object, or inferred grid.
- DisplayPoint: the API display coordinate, with integer x and y from 0 to 63.
- CoordinateTransform: source bounds, scale, offset, clipping, and provenance.

Every ScenePoint must map explicitly to a DisplayPoint before validation. If no
reliable transform exists, generate candidates directly in display space.

A transform is reliable only when its declared invariants pass deterministic
checks. Reliability is a typed status, not a model adjective:

- exact;
- tested;
- tentative;
- unavailable.

Only exact or tested transformations may submit a mapped coordinate. Tentative
and unavailable mappings require direct display-space candidates.

## 8.5 Deterministic fallback

The permanent fallback:

- contains no game-specific branch or solution table;
- samples only normalized current available_actions;
- uses one random.Random instance per game with a stable digest seed;
- generates ACTION6 points from ranked visible candidates and deterministic
  unexplored display points;
- handles start, active play, level transition, GAME_OVER, exhaustion, WIN,
  ambiguous dispatch, and global deadline;
- obeys competition reset behavior;
- cannot exceed validated action, reset, inference, retry, byte, or time caps;
- catches policy, model, parser, workspace, storage, and evidence failures;
- records a compact non-sensitive reason outside sealed/production redaction.

A no-visible-change result is scoped to an action plus context fingerprint. It
causes a decaying penalty, not a permanent claim that the action is a no-op.

## 8.6 Observation arms

R — raw minimal:

- current rendered observation;
- exact current grid;
- current available actions;
- game state and level metadata;
- bounded recent actions and canonical final frames;
- no engineered deltas, regions, animation summaries, intermediate frames, or
  ranked click candidates.

F — E0F:

- every R input;
- stable hashes;
- basic inter-frame and inter-action changed-cell masks;
- frame and distinct-frame counts;
- changed-cell counts and bounding box;
- transient cells;
- palette additions/removals;
- connected same-color regions;
- unambiguous appearance, disappearance, and translation candidates;
- ACTION6 display-space candidates;
- bounded animation summary.

The raw path remains independently deployable. F is not assumed beneficial.
Evaluator-only feature computation behind R must be inaccessible to policy and
must have its cost separately reported. A comparison that charges hidden
telemetry differently between arms is invalid.

## 8.7 Evidence retention

Evidence tiers:

| Tier | Meaning |
|---|---|
| T0 live safety | Latest canonical frame, state, legal actions, budgets, and pending action journal; never evicted while the game is viable |
| T1 normally mandatory | Submitted action, response metadata, canonical final frame, compact delta, and retention status for every transition |
| T2 bounded summary | Intermediate-frame and animation summaries |
| T3 optional exact | Complete ordered intermediate-frame sequence and rich crops/timelines |

Pack retained grids immediately as contiguous numpy uint8 arrays. The canonical
hash includes algorithm/version, shape, dtype, byte order, frame order, and
bytes. Select and freeze the hash and compression algorithms in configuration.

Keep only a bounded recent ring and T0 live state in RAM. Stream eligible exact
blobs to the content-addressed store and append a compact transition index.
Never retain the upstream unbounded list of nested Python grids.

Availability is explicit:

- exact;
- summarized;
- omitted_capacity;
- evicted_pressure;
- unavailable_storage;
- corrupt.

T1 is guaranteed under validated normal resource limits, not under arbitrary
disk or host failure. If persistent storage fails, preserve T0, continue legal
play, emit degradation state, and apply deterministic bounded eviction.

Every durable model claim records:

- supporting transition IDs;
- required evidence tier;
- current evidence availability;
- whether the claim is tentative, supported, verified, contradicted, or
  retired.

Evidence supporting a verified durable claim is pinned or promoted within a
declared quota. If required evidence becomes unavailable, the claim is
downgraded to summary-supported or tentative; it cannot remain verified
silently.

Evidence degradation never terminates an otherwise viable game.

## 8.8 Animation and correspondence

For every multi-frame response, compute deterministic bounded metadata:

- returned and distinct frame counts;
- frame-to-frame changed cells and masks;
- union bounding box;
- transient cells;
- per-color additions/removals;
- appearing/disappearing regions;
- unambiguous motion candidates;
- uncertain temporal ordering;
- whether the final frame hides a material event.

Expose rich animation only when a recorded trigger fires:

- unresolved motion or temporal order;
- a transient signal;
- ambiguous final-state delta;
- a prediction failure plausibly explained by animation;
- a model request admitted within budget.

E2d advanced correspondence is a separate treatment. It is entered only when a
documented failure is attributable to unstable identity tracking and simpler
region/delta/animation evidence is insufficient.

## 8.9 Working memory

Maintain isolated per-game stores:

1. Durable memory: supported or verified mechanics, invariants, hazards,
   procedures, and counterexamples.
2. Level scratch: current objects, subgoal, active hypotheses, candidate plan,
   unresolved evidence, and cheapest useful probe.
3. Rejected-hypothesis ledger: claim, contradiction evidence, scope, and
   reconsideration conditions.

All items have token, count, and byte limits. Summaries append revisions; they
never rewrite the underlying journal. Cross-game mutable memory is prohibited
during evaluation.

## 8.10 Structured E1S policy

E1S returns a strict schema:

- proposed state update;
- hypothesis additions/revisions;
- intent and subgoal;
- one action or a proposed queue of at most four;
- typed expected-effect predicates per action;
- typed stop conditions;
- optional evidence request;
- optional memory proposal.

Validation may repair bounded syntax only. It rejects unsupported fields,
illegal actions, invalid coordinates, oversized output, invalid predicates, and
budget violations. It never invents a replacement model action.

## 8.11 Bounded E1C workspace

E1C may analyze immutable evidence through a separately launched disposable
process. It:

- has no network;
- receives a sanitized environment;
- cannot access credentials, arbitrary filesystem paths, production objects,
  model artifacts, or evaluator state;
- cannot install packages;
- has bounded CPU, memory, output, files, and invocation count;
- cannot call arc_env or persist executable state between games;
- returns only the E1S proposal schema.

AST filtering or an import allowlist alone is not isolation. Full
model-authored Python is enabled only when the target runtime demonstrates
enforceable process and filesystem restrictions.

Otherwise E1C uses a fixed non-Turing-complete safe-operation language over
arrays and evidence queries. The safe-operation variant receives its own
registry field; it is not silently treated as unrestricted Python.

## 8.12 Prediction predicate language

Allowed predicate families include:

- game_state equals or belongs to a set;
- levels_completed changes by an exact amount;
- available_actions equals, adds, removes, or contains values;
- frame hash equals or differs;
- changed-cell count lies in a range;
- change bounding box satisfies a relation;
- palette adds/removes declared colors;
- a declared region appears, disappears, recolors, or translates;
- no visible change under a specified fingerprint;
- a declared animation event occurs;
- progress evidence satisfies a registered detector.

Each predicate declares:

- required evidence;
- exact or tolerant comparison;
- tolerance;
- required versus advisory status;
- scope and expiry.

Evaluation is three-valued:

- MATCH;
- MISMATCH;
- UNKNOWN.

A queued plan continues only when all required predicates MATCH. A required
MISMATCH cancels immediately. UNKNOWN cancels by default unless the predicate
was explicitly advisory before dispatch. The model cannot relabel a mismatch.

Material prediction failure means any required predicate MISMATCH, a game-state
or legal-action surprise, a level transition not covered by the queue, or loss
of evidence required to validate continuation.

## 8.13 Hypothesis status and verification

Maintain two to four active hypotheses. Each includes claim, scope, supporting
and contradicting evidence, observable predictions, cheapest distinguishing
probe, reversibility, risk, and exception count.

Status changes are deterministic:

- Tentative: proposed but not predictively tested.
- Supported: at least one nontrivial prediction matches.
- Verified-for-plan: repeated or independently discriminating predictions
  match and no active contradiction remains.
- Contradicted: a required prediction fails.
- Retired: no longer useful or outside scope.

An accidental win does not verify mechanics. A long queue requires
verified-for-plan dynamics relevant to every queued step.

## 8.14 Controller state machine

| Mode | Entry | Permitted behavior | Exit |
|---|---|---|---|
| Bootstrap | New level/game or recovered unknown state | Start/reset legally, capture T0/T1 evidence, one action maximum | Normal after valid observation |
| Normal | Valid state without verified queue | One proposal and one action | Fast, Deep, Recovery, Exhausted, or Done |
| Fast | Relevant plan predicates and dynamics verified | Continue one queued action after predicate check | Normal on completion; Recovery on mismatch/unknown |
| Deep | Novelty, contradiction, irreversible choice, or registered uncertainty trigger | Retrieve bounded evidence and use deeper inference; one environment action | Normal or Recovery |
| Recovery | Prediction failure, loop, repeated no-change, ambiguous dispatch, or state inconsistency | Cancel queue, retire/downgrade claims, select safe novel evidence; one action | Normal, Exhausted, or Done |
| Exhausted | Model/workspace budget unavailable or deadline degradation active | Deterministic fallback only | Done or level transition |
| Done | WIN or hard global termination point | No environment action; finalize client | Terminal |

Transition precedence is:

1. hard deadline or WIN;
2. invalid/ambiguous state recovery;
3. prediction mismatch;
4. budget exhaustion;
5. deep trigger;
6. verified queue;
7. normal operation.

The exact trigger thresholds live in validated configuration and are included
in every experiment hash.

## 8.15 Shared inference

The service provides:

- exactly-once model initialization;
- request and per-game state isolation;
- bounded queues;
- cancellation and stale-request rejection;
- request, client, and global deadlines;
- exception containment;
- queue/service/token/VRAM/RAM telemetry;
- deterministic degradation to fallback.

Model requests have unique IDs and may be retried only before a proposal is
committed to a live ActionDecision. Stale responses are discarded by
generation and pre-state hash.

## 8.16 Baseline-free score-aware scheduling

Every environment receives a cheap deterministic bootstrap sufficient to
create the one allowed session and obtain an initial observation when possible.
This does not imply a guaranteed expensive model call.

A model-service floor may be introduced only if a registered comparison shows
that it improves full-set mean RHAE or reliability. Otherwise calls come from
the shared admission policy.

For a game with n known win levels and next level index k:

    normalized_immediate_value = k / (n * (n + 1) / 2)

If n is missing or zero, use the configured conservative unknown-level value;
never divide by zero.

Rank discretionary work using:

    expected_value =
        P(complete_next_level_within_budget)
        * normalized_immediate_value
        * baseline_free_efficiency_proxy
        + bounded_future_option_value

    priority =
        expected_value / expected_remaining_global_time
        + uncertainty_exploration_bonus
        + aging_bonus

The denominator is clamped to a positive configured minimum and includes queue,
service, environment, and expected follow-up time on the global critical path.

The efficiency proxy may use only policy-visible, baseline-free features such
as current level action count, progress observations, prediction accuracy,
loop/no-change rate, model confidence calibration, and remaining budget. Its
training target is completion within a fixed future action/time window, never
RHAE or a human baseline.

The future-option term is bounded and represents the value of unlocking later
levels. It cannot exceed the remaining normalized game contribution.

Hard guards override rank:

- stale or canceled request;
- global finalization reservation;
- per-game or global cap;
- unsafe/unknown lifecycle;
- memory failure requiring degradation;
- starvation maximum queue age when the registered policy includes one.

Report the effect of any fairness/aging rule separately from expected-value
ranking.

## 8.17 Competition-parity runner

scripts/play_competition_like.py exposes:

1. Official backend using the current official API and competition mode where
   available.
2. Instrumented local backend emulating lifecycle invariants for deterministic
   tests and clearly labeled as emulation.

Both enforce:

- one scorecard;
- at most one make per environment;
- a fixed complete inventory before play;
- zeroes for untouched and failed environments;
- no in-flight score access;
- competition reset behavior;
- exact per-client and global deadlines;
- all clients terminating before close;
- close/finalization on recoverable error paths;
- hidden-production output policy when applicable.

Only a Kaggle end-to-end submission is authoritative for deployment.

## 8.18 Conditional advanced treatments

E7 executable model/scripts:

- Enter only after a measured failure attributable to planning or long-horizon
  transformation.
- Use the E1C isolation boundary.
- Require prediction tests against real transitions.
- Disable when its measured value does not exceed its time and failure cost.

E8 verified search:

- Enter only when a compact state and transition model have sufficient
  registered predictive accuracy for the searched variables.
- Search never bypasses real-transition validation.
- Replan after each real action.

E9 specialist:

- Compare with spending the same token/time budget on the primary model.
- Return advice only through the normal proposal/evidence boundary.
- Never receive evaluator-only or cross-game state.

# 9. Target repository layout

    agent/
      my_agent.py
      action.py
      action_journal.py
      state.py
      perception.py
      animation.py
      evidence.py
      prediction.py
      controller.py
      model_policy.py
      scratchpad.py
      inference.py
      scheduler.py
      config.py

    evaluation/
      metrics.py
      statistics.py
      sealed_eval.py
      reports.py

    config/
      competition_constraints.yaml
      experiment_registry.yaml
      statistics_protocol.yaml
      control_registry.yaml
      model_manifest.yaml
      source_manifest.yaml
      dependency_manifest.lock
      runtime_profiles.yaml
      output_policy.yaml
      prediction_schema.json
      action_journal_schema.json
      sealed_output_schema.json

    scripts/
      play_local.py
      play_competition_like.py
      profile_models.py
      run_experiment.py
      compare_treatments.py
      build_submission_notebook.py
      validate_submission.py

    tests/
      unit/
      integration/
      failure/
      fixtures/

    reports/
      runs/
      comparisons/
      decisions/

Ownership rules:

| Module | Owns | Must not own |
|---|---|---|
| my_agent.py | Framework integration | Game-specific mechanics or model internals |
| action.py | Immutable actions and coordinates | Policy choice |
| action_journal.py | Live action transaction state | Action selection |
| state.py | Typed bounded per-game state | I/O or model lifecycle |
| perception.py | Observation facts and candidates | Semantic facts not supported by evidence |
| animation.py | Temporal facts and candidates | Unverified intent |
| evidence.py | Retention, availability, and retrieval | Unbounded history |
| prediction.py | Predicate validation and evaluation | Model authority |
| controller.py | Modes, legal action, budgets, fallback | Provider-specific prompts |
| model_policy.py | Evidence selection and proposals | Environment calls |
| scratchpad.py | Isolated analysis | Secrets, environment authority, or evaluator data |
| inference.py | Model lifecycle and serving | Per-game policy memory |
| scheduler.py | Baseline-free admission and priority | Human baselines |
| metrics.py | Official-score replication | Policy inputs |
| statistics.py | Frozen experiment decisions | Retrospective threshold changes |
| sealed_eval.py | Best-effort aggregate-only H1/H2 execution | Policy decisions |
| config.py | Validated immutable configuration | Runtime mutable state |

# 10. Sequential implementation schedule

## Phase 0 — Governance, transaction safety, controls, and valid submission

Dates: September 4–6

Deliverables:

- Git initialization and ignore audit.
- Plan 7 activated as normative authority.
- Dated competition-constraint register.
- Public inventory and 15/5/5 partition.
- Source, dependency, model, output, action-journal, control, experiment, and
  statistics registry skeletons.
- Published-control candidate cutoff and provenance audit.
- Multi-file notebook packaging.
- Immutable ActionDecision.
- Write-ahead action journal with ambiguous-dispatch handling.
- Exact lifecycle counters and cap taxonomy.
- Legal deterministic fallback.
- Production-valid R path.
- Hidden-production output allowlist.
- Basic official/emulated competition-parity runner.
- First valid E0 Kaggle submission.

Exit gate:

- Three development runs have no invalid action or uncaught agent exception.
- Fixed-seed deterministic code traces are stable.
- ACTION6 payload and reasoning cannot cross game threads.
- Action journal passes pre-dispatch, acknowledged, and ambiguous-dispatch
  failure tests.
- One-make, one-scorecard, no-live-score, reset, all-games-count, and close
  invariants pass.
- Production output contains no raw hidden-style evidence.
- E0W candidates are frozen or marked non-reproducible with evidence.

## Phase 0F — Minimal bounded evidence foundation

Dates: September 7–9

Deliverables:

- Immediate uint8 packing.
- T0–T3 retention implementation.
- Bounded memory rings replacing upstream history.
- Stable versioned hashes.
- Transition index and evidence-availability states.
- E0F delta, animation, region, and click-candidate features.
- Claim promotion/downgrade behavior.
- Independent R/F serialization.
- Measured RAM and disk ceilings.

Exit gate:

- Exact evidence round-trips byte-for-byte.
- Memory stays within configured rings and index ceilings.
- Disk and store failures preserve T0 and legal play.
- Evidence loss is never silent.
- R cannot access E0F policy features.

## Phase 1 — Model, normalized controls, and E1 decision

Dates: September 10–14

Deliverables:

- Target-accelerator model, quantization, and engine profiles.
- Published and normalized E0W results.
- Shared inference service.
- Strict E1S implementation.
- Isolated Python or safe-operation E1C implementation.
- Frozen prediction schema.
- Causal same-model four-cell E1 experiment when feasible.
- Otherwise, explicitly non-causal bundle tournament plus same-model subset.
- Hierarchical/multiplicity-corrected report.
- Completed runtime and model decision table.
- Offline model/tokenizer/native dependency notebook.

Exit gate:

- All treatment cells meet safety/resource validation or are rejected.
- No factorial claim uses differing base models.
- Statistical and operational statuses are separate.
- One operational primary is selected without assuming F is beneficial.
- The full-run projection fits hard constraints.

## Phase 2 — Advanced evidence, animation, continuity, and correspondence

Dates: September 15–18

Deliverables:

- E2a advanced inter-action evidence.
- E2b advanced animation summaries.
- E2c selective rich animation.
- E2d conditional advanced correspondence.
- E3 durable/scratch/rejected memory.
- E4 exact retrieval and retrodiction.
- Evidence-linked memory revisions.
- Paired, registered ablations.

Exit gate:

- Every treatment has accepted, rejected, inconclusive, or provisional status.
- Verified claims retain or explicitly lose their required evidence.
- Rich animation is admitted only by recorded triggers.
- No result is promoted through an exploratory comparison alone.

## Phase 3 — Hypotheses and prediction-checked plans

Dates: September 19–22

Deliverables:

- E5 bounded hypothesis beam.
- Discriminating probe ranking.
- Typed three-valued prediction engine.
- Deterministic controller state machine.
- E6 one-to-four-action queues.
- Loop, no-change, death, contradiction, and ambiguous-dispatch recovery.
- Registered paired comparisons.
- One sealed H1 guardrail run after accepted internal evidence.

Exit gate:

- Queues continue only on required predicate matches.
- A required mismatch or unknown cancels under the registered rule.
- Accidental wins do not verify mechanics.
- H1 emits only the sealed aggregate schema.

## Phase 4 — Scheduling and 110-client behavior

Dates: September 23–25

Deliverables:

- Clock taxonomy instrumentation.
- Baseline-free completion and efficiency proxies.
- Cheap all-game bootstrap and measured model-admission policy.
- Expected-value scheduler with future option, uncertainty, and aging terms.
- Batching/worker topology experiment.
- Full 110-client official-like load simulation.
- Storage, queue, model, workspace, and deadline failure injection.
- Updated full-run projection.

Exit gate:

- No indefinite starvation under the registered maximum queue-age policy.
- No baseline value or baseline-derived target reaches scheduler features.
- All failures degrade to legal behavior.
- Clients stop admitting work before the finalization reservation.
- The competition-like run remains below the operational target.

## Phase 5 — Conditional advanced work

Date: September 26

Eligible treatments are E7 executable models/scripts, E8 verified search, and
E9 specialist calls. Each requires its prerequisite failure evidence,
prospective experiment record, resource accounting, and accepted result before
entering a candidate.

## Phase 6 — Candidate selection and freeze

Dates: September 27–28

Deliverables:

- Conservative and higher-reasoning competition candidates.
- Complete candidate manifests and reproducibility classification.
- Accepted internal selection evidence against the strongest applicable
  reproducible control.
- One sealed H2 aggregate guardrail under a frozen candidate rule.
- Selected hashes and rollback candidate.
- Freeze by September 28.

## Phase 7 — Release and submission verification

Dates: September 29–30

Use this window for:

- constraint revalidation;
- effective submission-allowance check;
- mount and hash verification;
- clean-checkout and offline reproduction;
- license and public-release audit;
- production-output audit;
- known-valid rollback submission;
- final milestone submission.

Do not introduce unmeasured policy changes after freeze.

The milestone deadline is September 30 at 11:59 PM UTC, or October 1 at
7:59 AM China Standard Time.

# 11. Test plan

## 11.1 Unit tests

- Stable per-game seed derivation across processes.
- Legal-action normalization.
- No production set_data() calls.
- ACTION6 coordinate bounds and typed transforms.
- Exact 16 KiB reasoning serialization boundary with compatibility margin.
- Immutable request-local action and reasoning payloads.
- Action-journal state transitions.
- Ambiguous dispatch is never automatically retried.
- Exact action/reset/retry/call cap semantics.
- Packed-frame hash and compression round-trips.
- T0 preservation and T1–T3 degradation order.
- Evidence availability and verified-claim downgrade.
- Animation, transient, appearance, disappearance, and motion fixtures.
- R/F policy isolation and telemetry accounting.
- Prediction predicate schema and MATCH/MISMATCH/UNKNOWN behavior.
- Controller transition precedence.
- Stale inference-response rejection.
- Baseline-free scheduler feature audit.
- Scheduler zero/missing-win-level guard.
- Official RHAE fixture parity.
- Fold, seed, crash, tie, multiplicity, and status classification.
- Sealed output allowlist and cleanup status.
- Production output allowlist.

## 11.2 Integration tests

- One scorecard opens and closes exactly once.
- Every environment is made at most once.
- No in-flight score request occurs.
- RESET follows competition semantics.
- Untouched, failed, and timed-out games are zero.
- All clients terminate before close.
- Missing and duplicate game IDs fail inventory validation.
- Action accepted plus response failure produces outcome_unknown.
- Model timeout, malformed output, cancellation, and stale response.
- Workspace timeout, forbidden operation, oversized output, and crash.
- Exactly-once model initialization.
- Level transition during a queue.
- Disk-full and evidence-store failure while play continues.
- 110 simultaneous clients with maximum queue-age enforcement.
- Global deadline triggers stop-admission and finalization.
- Local and official backends remain clearly labeled.
- Clean-checkout local bootstrap.
- Clean-checkout Kaggle offline execution with mounted artifacts.
- Hidden-production run leaves no prohibited artifact or notebook output.

## 11.3 Closed-loop experiments

| Treatment | Primary comparison |
|---|---|
| E0 | Correct deterministic path versus current random implementation |
| E0W-S-PUB | Published structured system versus E0 |
| E0W-C-PUB | Published workspace system versus E0 |
| E0W-S-NORM | Same-model normalized structured control |
| E0W-C-NORM | Same-model normalized workspace control |
| E1 factorial | Four same-model paradigm/observation cells |
| E2a | Advanced inter-action evidence versus E0F |
| E2b | Advanced animation summary versus E0F summary |
| E2c | Selective rich animation versus summary only |
| E2d | Advanced correspondence versus lightweight regions |
| E3 | Durable/scratch memory versus bounded recent history |
| E4 | Exact retrieval/retrodiction versus summary-only context |
| E5 | Bounded hypotheses versus one unconstrained explanation |
| E6 | Prediction-checked queues versus one action per proposal |
| E7 | Executable model/scripts versus selected E6 system |
| E8 | Verified search versus selected E7 or E6 system |
| E9 | Specialist request versus equal-budget primary-model reasoning |

Fixed trajectories may establish correctness and cost. Policy acceptance
requires registered paired closed-loop evaluation.

# 12. Required reports and decisions

Every development experiment report includes:

- registry and source hashes;
- result class;
- model/harness/observation identity;
- fixed game, fold, and seed manifests;
- full-set mean official RHAE;
- paired per-game effects and uncertainty;
- delta_min and multiplicity family;
- accepted/rejected/inconclusive statistical status;
- separate operational status;
- raw and selection-aware estimates when applicable;
- coverage, completions, levels, and weighted completion;
- actions per completion and before first progress;
- invalid, no-change, loop, reset, death, and ambiguous-dispatch rates;
- prediction outcomes and queue breaks;
- memory revisions and evidence availability;
- model/workspace/fallback rates;
- calls, tokens, queue/service/client times, global elapsed time;
- peak RAM, VRAM, disk, and evidence bytes;
- worst regression and catastrophic-tail result.

The mandatory model/runtime decision table includes:

| Field | Required value |
|---|---|
| Constraint-register version | Hash and verified_at |
| Accelerator/runtime | Exact measured platform |
| Primary and fallback models | Source, revision, architecture, and license |
| Quantization/engine | Exact formats and parameters |
| Paradigm | E1S, E1C, safe-operation E1C, or measured hybrid |
| Result class | Published, normalized, or competition candidate |
| Observation | R or F plus animation policy |
| Context policy | Limits, continuity, and eviction |
| Output policy | Schema, token/byte limit, and repair |
| Reproducibility | Bitwise, seed-stable, or distributional |
| Throughput | Sustained requests/hour |
| Latency | Queue/service/client p50/p90/p99 |
| Memory/storage | Peak VRAM, RAM, disk, and evidence |
| Calls/tokens | Hard global and per-mode maxima |
| Allocation | Bootstrap, discretionary, and admission rule |
| Caps | Environment, reset, model, workspace, and retry |
| Deadlines | Request, queue, client, stop-admitting, and global |
| Degradation | Tested fallback path |
| Scheduler proxy | Features, training target, and calibration |
| Output/privacy | Production and sealed policies |

# 13. Principal risks and controls

| Risk | Control |
|---|---|
| Competing plans define different truth | Plan 7 is sole normative authority |
| Experiment IDs change meaning | Versioned immutable experiment registry |
| Published reproduction is mistaken for causal comparison | Separate published, normalized, and candidate result classes |
| Different models invalidate the E1 factorial | Same model required or no causal factorial claim |
| Repeated comparisons create false discoveries | Hierarchical gatekeeping and frozen multiplicity rules |
| Development tuning is called generalization | Label internal selection evidence and keep H1/H2 as guardrails |
| Ambiguous API failure duplicates an action | Write-ahead journal and no post-dispatch automatic retry |
| Reasoning payload exceeds API limit | UTF-8 compact-JSON byte validation below 16 KiB |
| Shared enum state crosses games | Immutable decisions and fresh payloads |
| Crop coordinates reach the API | Typed transform status and display validation |
| Evidence loss is silent | Availability state and claim downgrade |
| Disk failure ends a viable game | Preserve T0 and degrade optional evidence |
| Raw hidden data reaches public output | Production allowlist and ephemeral evidence |
| Human baseline leaks into policy | Evaluator boundary and scheduler feature audit |
| All-game scoring is confused with model fairness | Cheap bootstrap separated from model-call admission |
| Runtime categories are double counted | Global elapsed clock is authoritative |
| Queues continue on unverifiable predictions | Three-valued required-predicate cancellation |
| False mechanics become long plans | Deterministic verification status and short queues |
| Workspace escapes or hangs | Demonstrated isolation or safe-operation fallback |
| Stale model response controls a new state | Generation and pre-state hash validation |
| Local emulation is mistaken for Kaggle parity | Explicit backend labels and Kaggle authoritative smoke |
| Rules or hardware change | Dated constraint register and pre-submission revalidation |
| License blocks prize eligibility | Artifact-level license record and release audit |

# 14. Next 72 hours

Execute in this order:

1. Initialize Git and audit ignored secrets and generated artifacts.
2. Activate Plan 7 as the sole execution authority.
3. Create the dated competition-constraint register and revalidate the Kaggle
   account.
4. Freeze and hash the 25-game 15/5/5 partition.
5. Create the experiment, control, statistics, model, source, dependency,
   runtime, output, prediction, action-journal, and sealed-output schemas.
6. Freeze the published-control candidate set and provenance cutoff.
7. Extend notebook packaging to a validated multi-file allowlist.
8. Implement immutable ActionDecision and write-ahead journal states.
9. Remove global RNG, static legal actions, game-specific policy, enum mutation,
   and the off-by-one loop.
10. Implement typed display coordinates and transform validation.
11. Implement exact counter taxonomy and guarded lifecycle.
12. Add the 16 KiB reasoning-byte guard.
13. Add the hidden-production output allowlist.
14. Build E0 and the basic competition-parity runner.
15. Implement T0–T3 uint8 evidence retention and availability.
16. Implement independently valid R and toggleable E0F F paths.
17. Produce deterministic E0 runs and the first valid Kaggle submission.
18. Begin published-control reproduction and target-accelerator profiling.

# 15. Definition of done

Plan 7 is implemented when:

- Plan 7 and the versioned registries are the only normative execution source.
- Both reproduction modes pass with declared inputs.
- The dated constraint register has been revalidated for the submission.
- Production contains no public-game IDs or solution tables.
- No production path mutates shared GameAction state.
- Every action is legal, request-local, bounded, journaled before dispatch, and
  terminally classified.
- Ambiguous environment actions are never automatically retried.
- ACTION6 submits only validated display coordinates from 0 through 63.
- Reasoning payloads pass compact UTF-8 byte validation below the API limit.
- Lifecycle counters distinguish actions, resets, model calls, repairs,
  workspaces, and controller iterations.
- Competition parity enforces one scorecard, one make, no live score, reset
  semantics, complete inventory accounting, and orderly close.
- A 110-client test has no cross-game state or unbounded queue age.
- Global elapsed time, component busy time, queue time, and client time are
  reported distinctly.
- The upstream unbounded Python frame history is replaced.
- T0 state survives recoverable storage failure.
- T1–T3 retention and degradation are explicit and tested.
- Evidence loss downgrades dependent verified claims.
- Hidden Kaggle-style execution emits no prohibited raw artifact or output.
- Human baselines remain evaluator-only, including scheduler training.
- Official RHAE fixtures match the mounted toolkit.
- Published and normalized controls have separate provenance and results.
- A causal E1 factorial uses one model across all four cells; otherwise no
  causal factorial claim is made.
- R and F are independently production-valid and policy-isolated.
- Statistical decisions use frozen folds, seeds, thresholds, crash handling,
  multiplicity, and rerun rules.
- Exploratory results are not relabeled as accepted without replication.
- H1/H2 remain aggregate-only catastrophic-regression guardrails.
- Every multi-frame response receives bounded deterministic analysis.
- Rich animation is exposed only through registered triggers.
- Predictions use the typed three-valued evaluator.
- Queues stop after the first required mismatch or disallowed unknown.
- Controller transitions follow the deterministic precedence table.
- E1C isolation is demonstrated or the safe-operation variant is used.
- Scheduler features and targets are demonstrably baseline-free.
- Cheap all-game bootstrap is distinct from model-service admission.
- E7–E9 enter only through their registered prerequisite and comparison.
- Model/workspace/evidence failures degrade to legal fallback behavior.
- Final candidates have complete hashes, licenses, runtime profiles, output
  audits, rollback artifacts, and reproduction instructions.
- The competition-like run finishes below 7.65 hours while reserving
  finalization time.
- Required public notebook, source, model information, licenses, and
  reproduction materials are released before the applicable prize deadline.

# 16. Decision principles

- Optimize hidden-set generalization and total mean RHAE.
- Preserve live safety state absolutely while making every other evidence
  guarantee explicit and testable.
- Compress access and optional history without pretending omitted evidence is
  exact.
- Treat every environment action as an irreversible transaction unless proven
  otherwise.
- Require predictions before long execution and check them after every action.
- Keep uncertain interpretation with the model and authority with deterministic
  code.
- Evaluate models and harnesses together for competition selection, but use
  same-model controls for causal harness claims.
- Prefer compact revisable mechanics over long narrative transcripts.
- Verification is routine; executable models and search are conditional.
- Statistical status and operational status are different facts.
- All-game accounting does not require equal compute allocation.
- Use global elapsed time for deadline safety.
- Introduce complexity through measured, prospectively registered treatments.
- Freeze early enough that deployment failure can use a known-valid rollback.

# 17. Primary references

- Kaggle competition:
  https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3
- Kaggle data:
  https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data
- Kaggle rules:
  https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules
- ARC-AGI-3 documentation:
  https://docs.arcprize.org/
- Game schema:
  https://docs.arcprize.org/game-schema
- Actions:
  https://docs.arcprize.org/actions
- Scoring methodology:
  https://docs.arcprize.org/methodology
- Competition mode:
  https://docs.arcprize.org/toolkit/competition_mode
- Official toolkit:
  https://github.com/arcprize/ARC-AGI
- Official agent framework:
  https://github.com/arcprize/ARC-AGI-3-Agents
- ARC-AGI-3 technical report:
  https://arcprize.org/media/ARC_AGI_3_Technical_Report.pdf
- Milestone 1 review:
  https://arcprize.org/blog/arc-prize-2026-milestone-1
- OpenAI Astra evaluation:
  https://arcprize.org/blog/astra
- PRO-LONG:
  https://arxiv.org/abs/2607.20064
- Executable World Models for ARC-AGI-3:
  https://arxiv.org/abs/2605.05138
- Executable-model component study:
  https://arxiv.org/abs/2607.15439
- Tycho:
  https://arxiv.org/abs/2607.28287
- Animation experiment:
  https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/734369
