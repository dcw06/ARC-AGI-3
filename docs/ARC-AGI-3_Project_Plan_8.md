---
title: "ARC Prize 2026 — ARC-AGI-3"
subtitle: "Plan 8, revision 8.4: Framework-Closed, Context-Continuous, Experiment-Valid Implementation"
author: "Project Team"
date: "5 September 2026"
revision: "8.4"
status: "Draft — proposed normative execution successor to Plan 7"
---

# Document purpose and authority

Upon completion of the Plan 8 activation gate, this document becomes the sole
normative implementation and experiment plan for the ARC-AGI-3 project. It then
supersedes Plans 2–7 for execution, experiment naming, acceptance decisions,
deployment, and definition of done. Until that gate is recorded as passed,
Plan 7 remains the active execution authority and Plan 8 remains a proposed
successor.

The strategic plan and Plans 2–7 remain background and design-history records.
They may explain why a decision exists, but they do not override Plan 8 after
activation. Findings discovered after activation must be recorded as a dated
amendment or a new plan rather than silently changing an experiment definition.

Plan 8 preserves Plan 7's full intended research scope and central
architecture:

- Deterministic code owns evidence, legal actions, budgets, lifecycle,
  validation, scheduling, and safety.
- A local model owns uncertain interpretation, hypotheses, goals, and proposed
  plans.
- Structured-action and bounded-workspace paradigms receive a controlled
  same-model comparison.
- Raw final-frame and animation-enriched observation bundles remain independently
  production-valid.
- Evidence retention is bounded, explicit, and degradation-safe.
- Advanced correspondence, executable models, search, and specialist calls
  remain conditional measured treatments.

Plan 8 carries forward and refines Plan 7's twelve normative corrections and
adds ten more:

1. One document and one versioned registry own experiment identifiers.
2. Published reproduction, normalized control, and competition-candidate
   results are different result classes.
3. The E1 2×2 estimates registered observation-bundle and harness/tool
   bundle effects only when all four cells use the same model and matched
   inference settings.
4. Statistical decisions distinguish game-level generalization from whole-run
   resource interference, with hierarchical testing, explicit crash handling,
   and selection-aware claims.
5. Live environment actions use a write-ahead journal and are never blindly
   retried after an ambiguous dispatch.
6. Predictions use a typed predicate language and three-valued evaluation.
7. Controller modes use an explicit deterministic transition table.
8. Evidence guarantees distinguish live safety state, normally mandatory
   evidence, optional exact evidence, and degraded availability.
9. Kaggle hidden execution has a scoped retained-output allowlist and ephemeral
   raw evidence in declared scratch roots.
10. Runtime accounting distinguishes global elapsed time from component busy
    time and queue time.
11. Scheduling uses a defined expected-value proxy without hidden or live
    baseline access; all-game accounting does not imply an unconditional model
    call for every game.
12. Current competition constraints are stored in a dated register and
    revalidated before every submission.
13. A declared framework adapter, not the upstream choose-action seam, owns the
    lifecycle loop, request-local dispatch, bounded evidence, and output policy.
14. Per-game model context, compaction, cache residency, eviction, and resumption
    are first-class registered treatments with correctness and resource tests.
15. E1 estimates final-frame-versus-animation-enriched observation-bundle and
    harness/tool-bundle effects; it does not isolate feature computation,
    abstract information, or reasoning paradigms.
16. Holdout consumption, treatment order, warm/cold state, and post-holdout
    changes follow a frozen exposure and randomization ledger.
17. Engineering completion and competition-performance success are separate
    gates.
18. Coupled components receive prospective interaction checkpoints rather than
    only greedy one-at-a-time acceptance.
19. Reset accounting distinguishes the initial play-start RESET from later
    level RESETs, ambiguous dispatch is never labeled as an official count,
    and reasoning-field limits are checked on the exact server-parsed value.
20. Executable-model evaluation separates mechanics fidelity, goal fidelity,
    next-action utility, and closed-loop score.
21. External rules, mounted authorities, registries, this plan, and code follow
    one explicit precedence chain with a parameter-closure gate.
22. Visual/grid/animation representation and public-supervision use are explicit
    registered policies rather than implicit harness behavior.

Revision 8.1 corrects the proposed plan before activation by requiring a
forensic inventory-exposure audit, raw transport-phase ownership, terminal
quarantine after unresolved dispatch, model screening and a minimum 110-client
scheduler before E1, safe-operation E1C by default, complete competition-rule
governance, explicit experiment/submission budgets, and a scope-shedding calendar.

Revision 8.2 corrects score and lifecycle semantics before activation: explicit
normalized-versus-percentage RHAE units; initial-play versus later-level RESET
accounting; separation of ambiguous local attempts from official counts;
question-specific authority precedence; a bootstrap schema without fabricated
pre-state; journaled scorecard open/close ambiguity; validation of the actual
server-parsed reasoning field; the exact freely-and-publicly-available external
input rule; and complete mounted-client transport-equivalence requirements.

Revision 8.3 corrects the remaining medium-priority execution semantics:
startup topology now accounts for Arcade.make's instance-wide lock; output
guarantees are scoped to retained notebook output and handled termination;
inference capacity distinguishes nominal expectation from safe admission;
queued actions require non-vacuous mandatory predicates; hypothesis status uses
machine-checkable evidence counters; and runtime game IDs are permitted only as
opaque infrastructure identity rather than static or policy-visible features.

Revision 8.4 applies review changes 2–5 before activation: an enforced
treatment-to-feature matrix and faithful-control execution contract; truthful
R/F observation-bundle estimands; whole-run evaluation and uncertainty for
shared-resource policies; and action-relevant queue dependencies with measured
discrimination-versus-repeated-support gates. The implementation calendar,
phase-budget allocation, and post-milestone schedule are not revised here.

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
- The currently installed RemoteEnvironmentWrapper.step catches transport and
  general exceptions and returns None, so it cannot distinguish proven
  pre-transport failure from ambiguous post-entry failure.
- The currently installed local and remote wrapper constructors immediately call
  reset, so Arcade.make performs the initial RESET before returning the wrapper.
  Without an explicit bootstrap transaction this command would precede ordinary
  adapter journaling and a later manual RESET could reset the level again. In the
  observed arc-agi 0.9.9 scorecard path, a successful initial full RESET starts a
  play but does not increment the play's scored action or reset counters; later
  level RESETs increment both. The mounted competition version remains
  authoritative and must be fixture-tested rather than inferred from the command
  name.
- scripts/play_local.py uses OperationMode.NORMAL and executes games
  sequentially. It is not a competition-parity runner.
- The observed Arcade.make holds one instance-wide lock across environment lookup,
  remote-wrapper construction, and the constructor RESET. Multiple threads on
  the same Arcade instance therefore do not make environments concurrently;
  startup must either stream play after serialized make acknowledgement or use a
  separately proven patched/per-client topology.
- Its --list path prints environment titles as well as IDs, so prior inventory
  handling requires the exposure audit below.
- The notebook builder packages only my_agent.py and installs only arc-agi and
  python-dotenv from the competition wheelhouse.
- The notebook builder defaults to T4 rather than the target RTX profile.
- notebooks/kernel-metadata.json contains a username placeholder and has no
  attached model or dependency sources.
- README.md still states five official submissions per day even though the live
  competition allowance is one, and .env.example uses the retired
  three.arcprize.org hostname.
- Makefile installs an open-ended arc-agi version and updates the framework tip;
  neither behavior satisfies the required production pins.
- .kaggle/access_token is absent and must remain ignored and untracked when
  supplied.
- Public payloads for ls20 and vc33 are downloaded. Both are exposed and belong
  in the development partition.
- The 25 public identifiers have been listed, but the provenance of that listing
  is not yet accepted as inventory-only: the current in-repository list command
  also prints each environment title. Until the exact listing path and operator
  exposure are audited, every title is treated as potentially exposed semantic
  metadata and no H1/H2 game is described as semantically untouched.
- The workspace is not a Git repository.
- The current local environment contains arc-agi 0.9.9 and arcengine 0.9.3;
  those versions are observations, not permanent pins until compatibility with
  the Kaggle-mounted framework is verified.
- The vendored framework revision currently observed is
  4743e7d0aaae0ded0d98a89a7e282e63564cd58b; record and revalidate it rather
  than silently pulling a newer revision.

Before the first submission:

- Accept the current competition rules.
- Supply and validate the correct Kaggle account and kernel identifier.
- Verify that the token exists, is non-empty, has restrictive permissions, and
  is ignored.
- Attach the competition, wheel, source, tokenizer, model, and native-library
  artifacts required by the selected candidate.
- Disable internet in notebook metadata.
- Verify the effective submission allowance in the Kaggle account.
- Complete required identity verification and confirm team membership before the
  entry and team-merger deadlines.
- Reconcile any conflict between the human-readable timeline and live platform
  metadata conservatively, recording both observations and using the earlier
  effective cutoff until the platform clarifies it.

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
| External inputs | Freely and publicly available external data, including pretrained models, as stated by the current competition overview; every input must also satisfy the applicable competition and winner-license rules, declared public provenance, and artifact-level license review |
| Evaluation inventory | 110 unseen games |
| Leaderboard split | 55 public and 55 private |
| Competition mode | Forced |
| Scorecards | One |
| Environment creation | At most one make per environment |
| In-flight score access | Unavailable |
| Reset behavior | During competition play, game resets are unavailable and RESET becomes a level reset; the initial RESET starts the play and its scored-counter treatment is determined by the exact mounted scorer fixture |
| Current reasoning-field limit | The observed arcengine path limits the compact-JSON UTF-8 encoding of the server-parsed reasoning field value to 16 KiB; freeze object-versus-JSON-string encoding, validate that field value, and apply a separate internal limit to the full request body |
| Scored action semantics | The methodology wording and observed toolkit behavior may differ for visible no-ops and for initial versus later RESETs; record the mounted fixture result, keep ambiguity separate, and never infer official counts from visible change alone |
| Current operational submission allowance | One submission per day; revalidate on the account |
| Final selections | Up to two; revalidate before final selection |
| Required submission filename | submission.parquet |
| Submission-size limit | 20,480 MB; revalidate before packaging |
| Maximum team size | 8 |
| Identity verification | Required |
| Current accelerator | RTX-class competition machine, presently g4-standard-48; revalidate before profiling and submission |
| Milestone 2 deadline | September 30, 2026 at 11:59 PM UTC |
| Entry deadline | October 26, 2026; the overview states 11:59 PM UTC while live metadata observed on September 4 reports 11:59 AM UTC, so use the earlier cutoff until resolved |
| Team-merger deadline | October 26, 2026 at 11:59 PM UTC; revalidate |
| Final deadline | November 2, 2026 at 11:59 PM UTC |
| Milestone publication | Public notebook and required open-source materials by the applicable deadline |
| Competition-data license | Apache 2.0 |
| Private sharing | No competition code or data sharing outside the registered team |
| Public competition-code sharing | Use the competition forum/notebooks and an OSI-approved license that permits commercial use |
| Winner license grant | Current rules state CC BY 4.0 for the winning submission/source and also require OSI-compliant open-source artifacts; record the artifact-level interpretation before eligibility claims |
| Winner obligations | Open-source system, model, and weights/parameters plus reproducible training/inference code, environment description, documentation, and the current required license grants |

If a live rule, Kaggle platform behavior, official scorer, or mounted framework
conflicts with this register, stop submission preparation, update the dated
entry, run compatibility tests, and record the change. Do not silently preserve
an obsolete value.

## 2.2 Scoring objective

Use two explicit score units. NormalizedRHAE is a fraction; OfficialRHAEPercent
is the percentage representation emitted by the observed official toolkit:

    normalized_level_score_l =
        min(1.15, (human_baseline_actions_l / agent_actions_l)^2)

    official_level_score_percent_l = 100 * normalized_level_score_l

An uncompleted level contributes zero. A normalized game score is the
level-index-weighted aggregation of normalized level scores, capped by its
weighted completed-level fraction and therefore bounded by 1.0. The official
percentage game score is 100 times that value and is bounded by 100. Total score
is the mean over the relevant game split in the same declared unit.

Every score field, threshold, estimator, report column, and fixture uses a unit
suffix or a schema type; bare `score` and `RHAE` numeric fields are invalid.
`agent_actions_l` comes from the authoritative scorer for official results. A
local replica uses the exact versioned scorer fixture and never substitutes a
locally conservative ambiguous-dispatch count for an official action count.

The September milestone objective is public-leaderboard RHAE. The final
competition objective is private-leaderboard RHAE. The agent must attempt valid
execution coverage across all 110 environments even though the two
leaderboards aggregate different 55-game splits.

Hidden-evaluation human baseline values belong exclusively to evaluator code.
They may not enter:

- prompts or model-visible evidence;
- model workspaces;
- controller state;
- action selection;
- inference allocation;
- scheduling features;
- learned scheduler targets or coefficients.

Public-development aggregate scores or score contributions may be used only in
a prospectively registered, game-level cross-validated offline-supervision arm.
The live scheduler receives no human-baseline value, public game ID, lookup
table, evaluator object, or hidden score. Reports separate this arm from a fully
baseline-free completion-window arm. If current competition rules or artifact
availability prohibit such use, the arm is disabled and the constraint register
records the reason.

Authority is question-specific. Current competition rules govern eligibility and
compliance. The live Kaggle competition backend and generated submission govern
actual lifecycle and numerical scoring behavior. The exact mounted client,
framework, and toolkit govern client serialization and compatibility only where
they do not conflict with observed live behavior. A local implementation is a
tested replica, never an authority. Record the scorer/toolkit version, score
unit, reset/no-op semantics, and fixtures for every experiment. An unresolved
conflict blocks the affected claim or submission; it is not resolved by placing
two disagreeing artifacts at the same authority rank.

## 2.3 Submission-output contract

The required submission file is platform-generated. `output_policy.yaml` declares
three disjoint filesystem scopes:

1. Retained notebook output root: the resolved competition output directory,
   presently `/kaggle/working` when confirmed by the mounted runtime. On normal
   return and handled failure, its default final-file allowlist contains exactly
   `submission.parquet`.
2. Ephemeral agent scratch root: a run-unique directory under a declared
   non-retained location such as `/tmp`. Hidden evidence, workspaces, and eligible
   caches may exist only here, under quotas and best-effort cleanup.
3. Platform/input/runtime-managed paths: read-only mounted inputs, interpreter and
   native-library state, and platform-managed caches outside the agent's output
   root. The agent neither treats these as notebook artifacts nor claims to erase
   platform-owned state.

Source, dependency, model, and configuration manifests belong in submitted
notebook source or declared read-only mounted inputs. Any necessary writable
copies, bytecode, compilation products, model caches, and temporary workspaces
must be redirected to the declared scratch root rather than the retained output
root.

Any additional retained production artifact or notebook-visible telemetry
requires a dated, explicit allowlist amendment after a rules, privacy, and
necessity review. It is disabled by default. Hidden frames, grids, animations,
game-specific trajectories, prompts, model responses, hypotheses, reasoning
transcripts, recordings, per-game diagnostics, raw profiler output, and core
dumps are never allowed in retained output or notebook-visible channels.

Standard output and standard error are limited to bounded, non-game-specific
lifecycle validity codes and finalization status. They may not contain exception
locals, request bodies, response bodies, paths that reveal evidence contents, or
per-game hidden information.

Notebook cell output, logging handlers, exception rendering, framework recording,
profiler output, scratch creation, and retained-root finalization must obey their
declared scope. The exact retained-root final-file guarantee applies after normal
return and tested handled-failure paths. SIGKILL, kernel OOM, host termination,
filesystem snapshots, swap, and platform behavior outside the process are outside
that cleanup guarantee; such a run is invalid rather than falsely reported as
verified clean.

## 2.4 Authority precedence and activation

When two requirements concerning the same question conflict, resolve them in
this order:

1. Current competition rules for eligibility, disclosure, licensing, and other
   normative compliance questions.
2. The live Kaggle competition backend and generated submission for actual
   lifecycle, accepted-command, and numerical scoring behavior.
3. The official scorer for score calculation, then the exact mounted client,
   framework, and toolkit for serialization and client compatibility.
4. The dated competition-constraint registry.
5. Frozen experiment, statistics, control, model, source, dependency, runtime,
   representation, context, success, output, and adapter registries.
6. This plan's defaults.
7. Implementation details and comments.

Platform behavior cannot relax a written eligibility rule, and client-library
behavior cannot redefine a live score. Lower authorities never silently override
higher ones. A discovered conflict blocks the affected experiment or submission
until it is recorded, resolved for the relevant question, and covered by a
compatibility test. Historical results retain the authority versions under which
they were produced.

Plan 8 activates only after the activation record confirms:

- every registry and schema required by E0 exists and validates; later-treatment
  registries may remain explicitly inactive but must exist and fail closure until
  their parameters are frozen;
- all normative parameters needed for E0 are closed;
- the framework-adapter strategy and mounted revision are frozen;
- the public-inventory retrieval path and all operator-visible metadata have been
  audited, and the truthfully classified exposure ledger and partition are
  hashed;
- the adapter can distinguish proven pre-transport failure from transport entry,
  or conservatively classifies every uncertain case as outcome_unknown;
- outcome_unknown has a tested terminal quarantine policy unless a current
  authoritative API supplies a read-only resynchronization mechanism;
- score units and the mounted initial-RESET, later-RESET, and visible-no-op
  counter semantics are fixture-tested and recorded without substituting local
  ambiguity bounds for official counts;
- scorecard open and close have journaled transport-phase and ambiguity policies;
- the startup topology is frozen against the mounted Arcade lock behavior and
  does not claim concurrent make without the required proof;
- the retained output root and non-retained scratch roots are resolved, writable
  products are routed correctly, and handled-exit guarantees are fixture-tested;
- a bounded competition-minimum inference queue, watchdog, and synthetic
  110-client load envelope exist before model comparisons;
- version control and secret/output exclusions are active.

Before any later experiment begins, a parameter-closure validator must confirm
that every threshold, seed, estimator, invalid-run rule, model and prompt hash,
representation, context policy, cap, quota, trigger, and comparison required by
that experiment is concrete and immutable. Placeholder or inherited-by-accident
values fail closed.

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
      -> M0 target-hardware model/engine screening
      -> bounded competition-minimum inference queue, watchdog, and load envelope
      -> published and normalized E0W competitive controls
      -> R raw observation path and F E0F observation path
      -> same-model E1 2x2 factorial or explicitly non-causal bundle tournament
      -> E1M per-game context/compaction treatment
      -> selected accepted or provisional operational primary
      -> E2 advanced evidence, animation, and correspondence
      -> E3 compact cross-level memory
      -> E4 exact retrieval and retrodiction
      -> E5 bounded hypotheses and discriminating probes
      -> E6 prediction-checked short queues
      -> E7 conditional executable model or scripts
      -> E8 conditional search over a verified model
      -> E9 conditional specialist request
      -> advanced score-aware scheduling and frozen candidates

Learned perception, reinforcement learning, test-time parameter adaptation, and
other extensions may be introduced through the same treatment registry. They
do not bypass the evidence, safety, statistics, or deployment contracts.

## 3.3 Framework adaptation contract

The upstream Agent.choose_action interface is not the production authority
because the current upstream loop owns dispatch, mutates or reads shared
GameAction payload state, retains an unbounded frame list, and enables recording
through orchestration defaults. Production therefore uses a versioned
CompetitionAgentLoop and CompetitionOrchestrator adapter.

The adapter owns:

- the scorecard-open, environment-make/bootstrap, action, and scorecard-close
  lifecycle transaction boundaries;
- the only environment-call boundary;
- the transport seam needed to classify whether transport was entered; it may
  not delegate production dispatch to a wrapper that catches exceptions and
  collapses pre-transport and post-transport failures into the same return value;
- immutable ActionDecision-to-request serialization;
- pre-dispatch journal commit and terminal transaction classification;
- bounded T0–T3 evidence insertion instead of upstream frame accumulation;
- separate exact lifecycle, local conservative, and authoritative scorer
  counters when the latter are available;
- per-game context/session handles and inference generations;
- client creation, the declared lock-compatible startup topology, queue
  admission, shutdown, and close;
- the make/bootstrap boundary, including the currently implicit constructor
  RESET, so no environment action occurs before a prepared journal record;
- disabling upstream recording, scorecard dumps, and prohibited diagnostics;
- exception containment and notebook-level finalization.

For every replaced or patched remote path, the adapter manifest freezes and its
fixtures verify behavioral equivalence for:

- URL construction, authentication headers, request method, and timeout policy;
- per-wrapper HTTP session use, the shared cookie jar, and cookie-lock ordering;
- scorecard ID, requested game ID, returned GUID, and session binding;
- action-data omission/inclusion and the selected reasoning encoding mode;
- response status handling, JSON decoding, FrameDataRaw validation, available
  actions, frame ordering, and last-response updates;
- redirect, retry, connection-error, malformed-response, and cancellation phase
  classification;
- logger and exception behavior under the production output policy.

A mocked request with the right URL is not sufficient compatibility evidence.
The patched transport must pass captured request/response fixtures from the exact
mounted client version and an end-to-end competition-parity smoke test.

The adapter may be implemented as overrides of upstream Agent/Swarm methods, a
packaged framework fork, or a deterministic version-pinned patch. The selected
mechanism must be declared before E0 and include:

- upstream source revision and mounted-file hashes;
- exact methods replaced or bypassed;
- an assertion that no alternate environment-call path is reachable;
- patch/build hashes and license provenance;
- compatibility tests against both local and mounted competition frameworks;
- captured transport-equivalence fixtures covering headers, cookies, GUIDs,
  reasoning encoding, response conversion, and last-response state;
- a fail-closed response to an unknown framework revision or signature.

For the currently observed remote wrapper, the selected adapter must bypass or
patch RemoteEnvironmentWrapper.step because it catches transport exceptions and
returns None. The adapter calls a pinned request-local transport function, or an
equivalent patched function with tested phase reporting, directly. It never uses
the upstream Agent.do_action_request path, which reads payload and reasoning from
mutable GameAction enum state. The replacement preserves the mounted wrapper's
session/cookie, authentication, GUID, response-conversion, available-action, and
last-response semantics unless a separately versioned compatibility correction
is proven. `reasoning_encoding_mode` records whether the server-parsed value is a
JSON object or a JSON string; the adapter may not silently change that type while
bypassing the wrapper.

The selected adapter strategy must also declare how Arcade.make and the wrapper's
constructor RESET are handled. With the current mounted call graph, create a
bootstrap transaction before calling make. Because no observation, GUID, legal
action set, or pre-state hash exists yet, that transaction uses the explicit
bootstrap schema rather than fabricating ordinary-action fields. Mark it
dispatched immediately before make, and pin or patch the constructor RESET
transport so it cannot retry or follow a redirect that repeats the command.
Acknowledge it only when make returns a wrapper with a valid initial observation
and bound session identity, then attach the returned GUID, observation hash, and
available actions. A missing/invalid initial observation becomes outcome_unknown
and terminal quarantine; never call reset to "repair" it. A version-pinned patch
may instead separate construction and RESET, but only after competition-parity
tests prove that it preserves the one-make contract. In either design, an exact
request-count fixture must demonstrate at most one RESET command.

The bootstrap command is recorded exactly once as a lifecycle command. Its
inclusion in scored action/reset counters is a separate, versioned fixture result.
In the observed arc-agi 0.9.9 path, a successful initial full RESET starts the
play and increments neither counter; later level RESETs increment both. The
controller never issues another bootstrap RESET after valid initialization.

my_agent.py is a thin registration and adapter entry point. It must not inherit
unsafe upstream lifecycle behavior merely to preserve the sample interface.

# 4. Normative registries and reproducibility

## 4.1 Required registries

Maintain these machine-readable artifacts:

| Artifact | Authority |
|---|---|
| config/competition_constraints.yaml | Current external and internal constraints |
| config/experiment_registry.yaml | Experiment IDs, factors, enforced feature manifests, parent deltas, controls, status, and supersession |
| config/statistics_protocol.yaml | Folds, seeds, isolated/whole-run units, paired workload blocks, estimators, thresholds, multiplicity, and crash handling |
| config/control_registry.yaml | Published and normalized controls |
| config/model_manifest.yaml | Models, tokenizers, quantization, engines, license, and hashes |
| config/source_manifest.yaml | Files and source hashes packaged into notebooks |
| config/dependency_manifest.lock | Exact Python/native dependencies and hashes |
| config/runtime_profiles.yaml | Hardware-specific measurements, C_nominal/C_admit, conservative admission bound, headroom, and limits |
| config/output_policy.yaml | Resolved retained roots, non-retained scratch roots, handled-exit guarantees, and local/sealed/Kaggle persistence rules |
| config/framework_adapter_manifest.yaml | Mounted revision, overridden seams, startup topology/lock behavior, hashes, and compatibility status |
| config/context_policy.yaml | Session continuity, compaction, cache residency, eviction, and resumption |
| config/representation_manifest.yaml | Image, grid, coordinate, crop, and animation representations |
| config/holdout_ledger.yaml | Public exposure, partition, run order, holdout consumption, and invalidation |
| config/success_criteria.yaml | Separate implementation and competition-performance gates |
| config/prediction_schema.json | Allowed predicates, action-relevant dependency bindings, queue support variants, and deterministic hypothesis-status policy |
| config/action_journal_schema.json | Action transaction states and fields |
| config/lifecycle_journal_schema.json | Scorecard-open, make/bootstrap, and scorecard-close transaction states, recovery, and ambiguity policy |
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
- Pin the framework adapter, overridden call graph, and only permitted
  environment-call boundary.
- Fail notebook construction on missing files, duplicate destinations,
  unresolved placeholders, hash mismatches, missing licenses, or undeclared
  runtime downloads.
- Fail experiment launch when its parameter-closure or holdout-eligibility check
  is incomplete.

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

- A current Qwen3.8-27B-FP8 Duck-style Kaggle notebook and source bundle, frozen
  at an immutable revision and re-audited for public accessibility, license, and
  mounted dependencies.
- A structured vision/action system based on the strongest reproducible
  open-source Reki/forge-style method.
- A bounded code/workspace system based on the strongest reproducible
  open-source Duck-style method.
- A deterministic state-graph/action-effect explorer using only registered
  policy-visible evidence and no game-specific solution knowledge.
- Any stronger publicly available and license-compatible Kaggle method
  identified before the control-registry cutoff.

Current hosted-model evaluations that cannot run under the offline Kaggle
hardware, access, and winner-eligibility constraints are recorded as diagnostic
capability ceilings, not eligible competition controls. They may motivate model
or reasoning choices but cannot satisfy the competitive-control gate.

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

### Faithful control execution

The E1 feature defaults in Section 5.4 apply to project E1 cells, not to faithful
published reproductions. A published control retains its original model-visible
tools, memory, prompts, action batching, and execution semantics. Compatibility
and isolation changes are recorded individually; any change to those policy
capabilities produces an adapted control, not a faithful reproduction.

A Duck-style control that writes and executes Python needs a declared control
runner with the target-runtime isolation proof required by Section 8.12. Its
Python execution is not replaced by the safe-operation language while retaining
the faithful-reproduction label. If that boundary cannot be demonstrated, mark
the Python control unavailable and use an eligible structured control or an
explicitly adapted safe-operation control. Published scores remain external
reference evidence and cannot stand in for a local reproduction result. This
availability decision precedes the control comparison; faithful reproduction
never overrides competition, evaluator-access, output, or resource restrictions.

The control manifest separately records which original policy capabilities are
preserved, which are changed, and whether the resulting runner is eligible for
production. A normalized control also records its own feature manifest; changing
model weights alone does not imply that it now has the project E1 defaults.

## 5.3 Canonical treatment identifiers

| ID | Treatment |
|---|---|
| E0 | Correct deterministic fallback and full execution path |
| M0 | Target-hardware model, quantization, engine, and reasoning-effort screening |
| E0W-S-PUB | Faithful published structured-action reproduction |
| E0W-C-PUB | Faithful published workspace reproduction |
| E0W-S-NORM | Structured normalized same-model control |
| E0W-C-NORM | Workspace normalized same-model control |
| E1S-R | Structured single-action policy with raw final-frame observations |
| E1S-F | Structured single-action policy with animation-enriched E0F observations |
| E1C-R | Safe-operation single-action workspace with raw final-frame observations |
| E1C-F | Safe-operation single-action workspace with animation-enriched E0F observations |
| E1C-PY | Conditional unrestricted-Python workspace after target-runtime isolation proof |
| E1M-RECON | Stateless calls with bounded reconstructed context |
| E1M-COMPACT | Per-game visible context with registered compaction |
| E1M-CACHED | Per-game prefix/KV-cached continuity when supported |
| E1M-PROG | Programmatic searchable interaction history |
| E2a | Advanced inter-action evidence |
| E2b | Advanced animation summary |
| E2c | Selective rich animation |
| E2d | Advanced correspondence and identity tracking |
| E3 | Durable/scratch/rejected-hypothesis memory |
| E4 | Exact retrieval and evidence-grounded retrodiction |
| E5 | Bounded competing hypotheses and discriminating probes |
| E6 | Prediction-checked one-to-four-action queues |
| E6-DISC | Queue gate requiring action-relevant discriminating support |
| E6-REPEAT | Queue gate also permitting scoped repeated support without a decision-relevant alternative |
| E7 | Conditional executable transition model or scripts |
| E8 | Conditional search over a verified model |
| E9 | Conditional specialist request |
| IX1 | Representation/animation × memory/retrieval interaction checkpoint |
| IX2 | Hypotheses × context continuity × prediction-checked queue checkpoint |
| IX3 | Executable model × verification/search × delegation checkpoint |

An experiment ID is never reused for a different treatment. Revisions append a
version suffix in the registry, such as E6.v2, while preserving the original
record.

Revision 8.4 changes E1 activation semantics, R/F interpretation, and E6 gate
semantics. Any affected previously frozen treatment receives a new version; its
earlier runs are not pooled or relabeled under the new definition. E6-DISC and
E6-REPEAT are conditional registered variants, not mandatory extra experiments.

## 5.4 Enforced treatment-to-feature matrix

Every run resolves an immutable feature manifest from the following defaults.
E1S-R, E1S-F, E1C-R, and E1C-F use the same activation settings except for their
declared observation and harness/tool factors. Available infrastructure does not
activate a policy feature.

| Policy capability | E1 default | First permitted treatment and boundary |
|---|---|---|
| Model proposal and environment dispatch | Exactly one action per proposal | E6 enables at most four, subject to the registered queue gate |
| Recent model-visible context | Fixed bounded window of permitted observations, actions, and model turns; stateless reconstruction | E1M tests visible compaction or other registered continuity modes |
| Durable structured mechanics, level scratch, and rejected-hypothesis memory | Disabled; no persistent model-authored memory store | E3 activates the three stores in Section 8.9 |
| Exact historical retrieval and retrodiction | Disabled outside the fixed recent window | E4 activates budgeted queries to eligible retained evidence |
| Active typed hypotheses and discriminating probes | Disabled; no status advancement or controller use | E5 activates the store and probe policy in Section 8.14 |
| Prediction-checked multi-action execution | Disabled; no queue accepted | E6 activates dependency records, predicates, gate variants, and Fast mode |
| Observation enrichment | R or F exactly as Section 8.6 | E2a–E2d add their registered evidence treatments |
| Workspace | None in S; fixed safe-operation vocabulary in C | E1C-PY changes executable capability only after isolation proof |
| Executable transition model, search, specialist | Disabled | E7, E8, E9 respectively, subject to prerequisites |
| Inference admission | Same frozen minimum fair scheduler in all cells | Advanced scheduling is a separate whole-run treatment |

E1 uses the Normal single-action policy plus lifecycle, error-recovery,
exhaustion, quarantine, and deadline handling. Hypothesis-driven Deep triggers,
Fast execution, and evidence-dependent semantic recovery are disabled until
their feature prerequisites are active. Recovery from syntax, model, or legal
action failure does not activate those later mechanisms.

The model may reason informally about mechanics inside its registered token
budget. Such text in a bounded recent transcript is not a typed hypothesis,
durable memory item, or authority for queue execution. E1M compaction summarizes
only its registered history; it does not silently enable E3 stores or E5 status
promotion. Bounded scratch calculations in E1C are proposal-local unless a later
registered continuity treatment explicitly permits persistence.

Schemas reject disabled fields, queue lengths, tools, retrieval requests, and
memory mutations rather than silently ignoring them. Prompts advertise only
enabled capabilities. Every later treatment declares an exact parent manifest
and feature delta. E6 may create scoped local dynamics-support records without
enabling E5 competing-hypothesis generation; inherited E5/E3/E4 features must be
identical in its one-action control. Launch-time closure, runtime validation,
and feature-negative fixtures enforce this matrix.

# 6. Evaluation protocol

## 6.1 Public-game partition

Before opening another public environment or exposing more metadata:

1. Reconstruct and record the command, API response fields, files, terminal
   output, document content, and operator involved in the existing inventory
   listing.
2. Record every source, frame, replay, play, title, description, tag, action-space
   signature, level count, or other semantic field already exposed. ls20 and vc33
   belong to development because their payloads are present.
3. Freeze the 25-game identifier inventory and the exact set of fields that were
   visible when it was obtained.
4. Record the partition algorithm, seed, and permitted inventory-only fields.
5. Assign a target of 15 development environments, expanding it as necessary to
   include every environment whose source, frame, replay, play, or policy-relevant
   semantic information was exposed.
6. Assign up to 5 H1 architecture-guardrail and up to 5 H2 candidate-guardrail
   environments only from the remaining eligible inventory.
7. Hash and archive the manifest and exposure audit.

If all 25 titles were displayed but no source, frame, replay, play, or
policy-relevant interpretation occurred, a randomized 15/5/5 partition may still
be used operationally, but H1/H2 are labeled reduced-exposure procedural
guardrails rather than semantically untouched holdouts. If semantic information
informed architecture, threshold, prompt, model, or treatment decisions, the
affected games are development games and are ineligible for H1/H2. If fewer than
ten eligible games remain, reduce or eliminate H1/H2 rather than misclassify
exposure.

Permitted stratification fields are limited to non-semantic information
available without make, frames, source, replay, or play. If a proposed field
requires exposure, do not use it.

Production source and packaged configuration contain no hard-coded public-game
ID literals, solution tables, per-ID lookup values, or ID-conditioned policy
branches. The adapter may receive and retain the current runtime game ID as an
opaque infrastructure key only for inventory validation, gateway requests,
journal/session binding, cache isolation, and cleanup. That opaque ID is not a
model-visible feature, scheduler feature, learned lookup key, or semantic policy
input. Local development reports may map opaque run keys back to public IDs;
sealed and hidden-production output may not.

## 6.2 Unit of generalization

The game is the unit of generalization. Multiple seeds reduce within-game
noise; they do not create additional game-level samples. The randomization and
uncertainty unit depends on resource coupling: isolated policy experiments may
use game-level units, while shared-resource comparisons require whole-run units
as specified in Section 6.10. Games sharing a scheduler are not independent
replicates merely because their policy state is isolated.

For each game and treatment:

1. Run the number of seeds frozen in the treatment record.
2. Aggregate seed results into one per-game value using the frozen estimator.
3. Compare treatment and control on paired game values.
4. Include untouched, failed, crashed, or timed-out games as zero for the
   primary full-set score unless the run meets the predeclared invalid-run rule.

The primary outcome is mean RHAE over the entire fixed evaluation set, stored
with an explicit NormalizedRHAE or OfficialRHAEPercent type. Secondary outcomes
are:

1. paired per-game RHAE difference in the same declared unit;
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
- isolated-policy versus shared-resource-whole-run execution mode, resource
  isolation or coupling, randomization unit, and uncertainty unit;
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
- whether environment seeds change benchmark-relevant game behavior, how a seed
  is supplied, and why the seed distribution represents the intended target;
- complete workload, paired run-block count, whole-run order, and clustered
  uncertainty procedure when computation is shared;
- the maximum game-runs, accelerator-hours, wall-clock hours, and failed-run
  allowance for the family;
- positive, negative, and inconclusive decision rules.

When the audit permits a fifteen-game development set, default development
analysis uses five predeclared folds of three games. If exposure expands the
development set, statistics_protocol.yaml freezes a rebalanced game-level fold
scheme before results.
Configuration choices for an outer fold may use only the other development
folds and previously frozen external evidence. Because the human implementer may
already know development environments, development cross-validation supports
internal selection rather than an untouched generalization claim.

If configuration selection differs by outer fold, the outer-fold estimate is an
estimate of the registered selection procedure, not the performance of one fixed
configuration. The final configuration selected using all development games has
no unbiased fixed-candidate estimate from those same games; reports
state this explicitly and do not relabel the procedure estimate as the final
candidate estimate.

The small development set is expected to be sparse, tied, heterogeneous, and low
powered. Before interpreting an Accepted result, report the attainable
permutation resolution, number of nonzero paired differences, confidence or
randomization interval, and sensitivity to any single game. When the frozen
practical-effect threshold is met but inferential resolution is inadequate,
assign statistical status Inconclusive and, if operationally useful, the
separate operational label Provisional primary rather than implying
high-confidence generalization.

H1 and H2 are catastrophic-regression guardrails of up to five games each:

- H1 may veto an architecture for a predeclared regression, invalidity, or
  resource failure.
- H2 applies a frozen aggregate candidate rule and deterministic tie-break.
- Neither H1 nor H2 establishes a positive significance claim.
- H2 participates in selection and is therefore not an untouched estimate.
- With five nonzero paired differences, the best-case exact two-sided
  sign-flip p-value is 0.0625; ties can make the attainable resolution worse.
- A smaller eligible guardrail has still weaker resolution and is not expanded
  with exposed games merely to preserve a nominal sample size.
- Their interpretation is further downgraded to reduced-exposure procedural
  guardrails if the inventory audit finds title or semantic-metadata exposure.

## 6.4 Exposure and holdout-consumption ledger

holdout_ledger.yaml is append-only and records every environment exposure,
permitted output, consuming decision, code/configuration hashes, and operator.

- Inventory-only handling does not consume a game when no frame, source,
  replay, play, title, description, tag, or other semantic metadata is exposed.
- Title-only or other semantic-metadata exposure is recorded even when it does
  not consume a procedural guardrail under the frozen reduced-exposure rule.
- Development games are always marked exposed.
- H1 is consumed once for its prospectively registered architecture guardrail.
- A design or threshold change informed by H1 moves those games to development
  for all later claims.
- H2 runs exactly once after candidate code, configuration, model, context,
  representation, output policy, and tie-break are frozen.
- Any policy-affecting post-H2 change invalidates the H2 candidate claim and is
  not repaired by rerunning the same assigned games.
- An invalid holdout run consumes the holdout unless the predeclared invalid-run
  rule proves that no usable policy result or semantic evidence was produced.
- No per-game H1/H2 values or qualitative observations reach the implementer.

Repeated Kaggle public-leaderboard submissions are adaptive operational
evidence. They are not called untouched external confirmation. Only an
unselected private or newly released evaluation can support that claim.

## 6.5 Run ordering and state control

Before execution, each isolated-policy experiment freezes a blocked or
counterbalanced order at the game-treatment-seed level. Shared-resource
experiments instead freeze paired complete-workload run blocks and counterbalance
treatment order between those blocks. Treatments never share a live adaptive
resource pool in a primary comparison. The record includes:

- cold versus warm model, tokenizer, kernel, filesystem, and inference-cache
  state;
- treatment ordering within game and game ordering within treatment;
- common random seeds where paired randomness is meaningful;
- whether a per-game context/cache is newly created, resumed, compacted, or
  evicted;
- machine/runtime drift checks and retry placement;
- batch composition and concurrent-client load.

Warmup runs use non-evaluation fixtures. A treatment may not systematically
receive warmer model state, more resident cache, or a more favorable queue.
Primary estimates use the predeclared seed estimator, never the maximum observed
seed or best rerun.

## 6.6 Multiplicity and selection

Use hierarchical gatekeeping:

1. Establish E0 correctness.
2. Establish reproducible competitive controls.
3. Test one predeclared primary E1 candidate contrast against the strongest
   applicable control.
4. Treat the E1 harness/tool, observation-bundle, and interaction contrasts as a
   declared family and apply the frozen familywise procedure.
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
- adaptive Kaggle public operational evidence;
- untouched private or newly released external confirmation, when available.

## 6.7 Decision classes

Statistical status:

- Accepted: within the declared public-development domain, the primary
  improvement reaches delta_min under the frozen
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

Acceptance is an operating decision for the declared public-development domain;
it is not a hidden-set generalization claim. An inconclusive result remains
inconclusive. It may support provisional shared
infrastructure but may not be presented as a performance improvement.

Reliability work may be accepted after eliminating a reproduced failure while
meeting a predeclared non-inferiority margin.

## 6.8 Same-model E1 factorial

The registered causal E1 2×2 of observation bundles and harness/tool bundles
requires all four cells to share:

- exactly the same base model and weights;
- the same quantization and inference engine;
- the same decoding parameters and seed policy;
- matched image and text preprocessing;
- equal wall-clock, token, call, action, reset, retry, and evidence ceilings;
- the same game and seed pairs;
- the same model-service and queue policy;
- identical evidence selection within an observation arm;
- the E1 feature manifest in Section 5.4, including single-action execution and
  disabled later-treatment stores, queries, and hypothesis/queue machinery.

The registered factors are:

| Cell | Paradigm | Observation |
|---|---|---|
| E1S-R | Structured single action | Raw final-frame R |
| E1S-F | Structured single action | Animation-enriched E0F F |
| E1C-R | Safe-operation single-action workspace | Raw final-frame R |
| E1C-F | Safe-operation single-action workspace | Animation-enriched E0F F |

Estimate:

- structured-schema versus workspace/tool-bundle effect within R;
- structured-schema versus workspace/tool-bundle effect within F;
- final-frame-versus-animation-enriched observation-bundle effect within S;
- final-frame-versus-animation-enriched observation-bundle effect within C;
- interaction effect.

R contains canonical final frames; F additionally exposes features derived from
intermediate animation frames that R cannot inspect. The difference therefore
includes evidence access as well as representation and precomputation. A target
color that flashes only in an intermediate frame can be available in F and
absent from R. This is a valid registered bundle contrast, not an isolated
feature-computation effect.

E1C-R may derive features from its permitted R inputs; equivalent reasoning
cannot be prohibited merely because E0F can compute the same quantity. It may
not import F artifacts, intermediate frames, hidden telemetry, evaluator state,
or uncharged preprocessing. All model-authored derivation time, tokens,
workspace calls, and outputs are charged to that cell.

Reports enumerate the evidence-access and tool/operation differences and use the
registered bundle estimands. They do not attribute an R/F gain specifically to
engineered perception, feature computation, or abstract information, and the
S/C contrast does not isolate a pure reasoning paradigm. A future isolated
precomputation study needs a new treatment ID, identical ordered frame access
and retrieval rights in both arms, matched resource ceilings, and a separately
frozen contrast; it is not an extra mandatory E1 experiment.

Each E1 comparison declares whether it estimates an isolated policy effect or
a complete shared-resource bundle effect under Section 6.10. A matched scheduler
implementation alone does not remove cross-game resource interference.

If one model cannot support all four cells, do not report causal factorial
effects. Run and label a model-plus-harness bundle tournament, then perform a
separate same-model subset comparison where possible.

## 6.9 Best-effort redacted guardrail evaluation

H1/H2 run in sealed_eval mode:

- Raw frames, deltas, animations, prompts, responses, hypotheses, reasoning,
  recordings, and per-step logs live only in a run-unique process-private
  directory under the declared non-retained scratch root, never under the
  retained notebook output root.
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

None of these cleanup statuses claims protection against SIGKILL, kernel OOM,
host termination, filesystem snapshots, swap, or platform behavior outside the
process.

Process-private storage, cleanup, and aggregate-only output provide redaction;
they do not prove implementer blinding when the same operator controls the host
and can alter or inspect the runner. Call H1/H2 sealed only when an independent
trusted runner or access-control boundary prevents the implementer from viewing
per-game evidence. Otherwise reports use the term process-redacted guardrail and
make no blinding claim.

A guardrail rerun occurs only under a predeclared invalid-run rule and only when no
usable policy result was emitted.

## 6.10 Isolated policy and complete-workload evaluation

Two execution modes answer different questions and cannot share an unqualified
performance label:

1. `isolated_policy`: each game-treatment play has a fixed resource allocation
   that another evaluation game cannot borrow or consume. Run sequentially or
   with demonstrated resource isolation; a common unpartitioned inference queue
   is not isolation. Paired game comparisons estimate behavior under those
   declared per-game limits. Shared-resource scalability is a separate result.
2. `shared_resource_whole_run`: one frozen candidate controls the entire fixed
   game workload, shared inference service, scheduler, cache residency, and global
   budget. Treatment assignment applies to a complete run. Changes in one game's
   resource use may change another game's outcome and belong to the treatment's
   measured total effect.

Scheduler comparisons, candidate load certification, and final candidate
selection require the second mode. Each paired run block executes candidate and
control separately against the same complete workload manifest, environment
versions, seed vector where supported, arrival/startup policy, hardware, global
time budget, and external background-load policy. Run order is counterbalanced
across blocks; caches and warmup follow the frozen cold/warm policy and no
candidate state crosses runs. The registered number of repeated run blocks is
concrete before execution.

Candidates may produce different trajectories, request counts, batch contents,
and admission decisions; these are outcomes, not quantities to equalize after
the run. All inventory entries, including unserved or failed games, stay in each
run's denominator. Do not mix candidate and control clients in one live adaptive
pool or use per-game treatment shuffling to claim their isolated causal effects.

The primary shared-resource contrast is the paired difference of whole-run
full-set mean NormalizedRHAE or OfficialRHAEPercent. Retain per-game paired
differences as diagnostic decompositions. For inference conditional on the fixed
workload, the randomization, sign-flip, or bootstrap unit is the paired whole-run
block; resample its games together, not independently. Repeated blocks measure
run variability and do not create new game-generalization samples. With too few
blocks for the frozen uncertainty rule, report descriptive/provisional results.
Do not apply independent game-level sign flips to a shared-pool result.

Any claim across game compositions additionally needs prospectively sampled or
held-out complete workload manifests and a hierarchical estimator that preserves
within-run dependence. A fifteen-game workload does not establish 110-game score
performance. Synthetic 110-client traffic establishes load behavior only; it
cannot supply missing real-game generalization evidence. Public-development
whole-run comparisons and Kaggle hidden execution retain their separate labels.

An invalidity event affecting shared infrastructure is classified at run level
under the frozen rule; candidate-caused exhaustion, crashes, or starvation cannot
be erased as infrastructure noise. Partial runs otherwise retain zeroes for
missing games. Per-game completion, action, admission, and cost diagnostics
explain allocation tradeoffs without replacing the whole-run decision metric.

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

For serialized service, the mean-latency calculation is a nominal expectation,
not a safe maximum:

    C_nominal = floor(B_model_service_busy / L_weighted_mean)

Derive the hard admission ceiling separately:

    C_admit = floor(B_effective_service / L_guard)

`B_effective_service` subtracts a registered service headroom from the model
service budget. `L_guard` is a conservative measured latency bound for the
declared mixed workload, selected prospectively from a registered upper quantile
or one-sided confidence bound and never from the same run after observing a
favorable tail. Require `C_admit <= C_nominal` unless a measured deterministic
bound proves otherwise.

For batching or multiple workers, replace latency division with a conservative
lower bound on sustained completed requests per global wall-clock second under
the actual mixed workload, multiplied by the effective service budget and rounded
down. Include batch-formation delay, cancellation, workspace time, cache misses,
long-generation tails, and memory pressure. A sample mean or best observed run is
never labeled a hard capacity ceiling.

Translate the measured capacity into:

- hard global call/token maxima;
- nominal expected capacity, conservative admission capacity, headroom, and the
  measured quantile/confidence rule that separates them;
- per-mode request ceilings;
- cheap bootstrap allowance;
- discretionary pool;
- maximum queue age;
- per-client soft deadline;
- global degrade and stop-admitting timestamps.

Before E1, implement a competition-minimum scheduler with a bounded queue,
per-game isolation, cancellation/stale-response rejection, a configured maximum
queue age, and a simple deterministic fair admission rule. Profile it with a
declared synthetic 110-client workload. This minimum scheduler is shared by all
E1 cells. Later score-aware ranking is a separate treatment and may not silently
change the E1 execution surface.

runtime_profiles.yaml also records a prospective research budget for every phase:
maximum accelerator-hours, full-game passes, target-hardware notebook runs,
Kaggle submissions, and contingency reserve. Exceeding a phase budget stops
optional treatments; it never causes tests, redaction, finalization reserve, or
holdout rules to be skipped.

## 7.4 Per-game context and cache contract

context_policy.yaml defines independently for each model/engine:

- stateless reconstruction, visible compaction, persistent session, prefix/KV
  cache, or programmatic-history mode;
- the exact model-visible state and whether hidden reasoning state can persist;
- context token and byte ceilings;
- compaction trigger, deterministic inputs, summary schema, and validation;
- per-game session identity and binding to the current pre-state hash;
- GPU/host/disk cache residency ceilings and eviction policy;
- resume behavior after eviction, process failure, or stale response;
- prohibition on cross-game prompt, cache, generated-state, and evidence reuse;
- telemetry for cache hit, rebuild, compaction, eviction, and context loss.

A resumed or cached context cannot authorize an action until its internal opaque
runtime-game-ID key, generation, evidence frontier, and pre-state hash match. The
runtime ID remains adapter metadata and is omitted from the model-visible context
manifest. Context loss degrades to registered reconstruction or fallback; it
never silently presents stale memory as current. Context variants are compared
under measured global-time and memory costs, not token count alone.

## 7.5 Watchdog, cancellation, and startup topology

An independent notebook-level watchdog owns the hard stop-admitting and
finalization deadlines. It does not depend on an agent thread or model worker
remaining responsive.

The inference adapter records whether the selected engine supports true
generation cancellation. If cancellation is unavailable, stale results are
discarded for correctness and the remaining compute exposure is included in
admission decisions. Worker termination is used only through a tested method
that preserves model-service and finalization integrity.

`framework_adapter_manifest.yaml` selects exactly one startup topology:

- `serialized_make_streaming_play` is the default for the observed Arcade
  implementation. One shared Arcade instance performs make calls through its
  instance-wide lock, but each acknowledged client becomes eligible for play
  immediately; the orchestrator does not wait for the remaining inventory.
- `patched_shared_arcade_concurrent_make` is allowed only when a pinned patch
  narrows or removes the make lock and tests prove one-scorecard identity,
  shared-cookie safety, exact one-make behavior, and wrapper/session isolation.
- `per_client_arcade_concurrent_make` is allowed only when tests prove that
  separate clients reuse the one acknowledged scorecard without opening defaults,
  preserve required shared cookies/authentication, and satisfy the same one-make
  and session-isolation invariants.

Submitting multiple threads to the unmodified shared Arcade.make does not count
as concurrent creation. In every topology, make admission is bounded, gateway
backoff and failure classification are frozen, partial inventory is explicit,
and play/inference concurrency is bounded independently from make concurrency.

# 8. Algorithm specifications

## 8.1 Immutable action decision

The controller creates an immutable ActionDecision containing:

    action_id
    action_data
    wire_reasoning
    local_rationale_reference
    source
    controller_mode
    expected_effect_predicates
    stop_condition_predicates
    evidence_references
    decision_id

Production code never calls GameAction.set_data() and never stores request
payloads on a shared enum instance.

action_data and wire_reasoning are immutable request values. The local rationale
reference is never serialized to the environment request; it points only to
permitted local evidence and is omitted entirely under production redaction when
the output policy requires it.

Before dispatch:

1. Re-read current legal actions.
2. Validate the action ID against the normalized current set.
3. Validate ACTION6 display coordinates as integers from 0 through 63.
4. Resolve the enum member without mutation.
5. Serialize fresh data and a minimal or empty wire-reasoning value using the
   frozen `reasoning_encoding_mode` required by the mounted interface.
6. Derive the value that the server will parse as the reasoning field. Validate
   the compact-JSON UTF-8 encoding of that value against the observed 16 KiB
   arcengine field limit and a separately configured production margin. Then
   serialize the complete request through the exact pinned production serializer
   without dispatch and validate it against a separate internal full-body limit.
   Fixtures cover the logical reasoning object, any intermediate JSON string,
   the server-parsed field value, and complete request bytes. The serializer must
   reproduce every escaping or encoding transform expected by the gateway,
   including the currently observed wrapper's nested reasoning serialization,
   without relying on that wrapper as the dispatch authority.
7. Create the write-ahead journal entry.

Full local reasoning, hypotheses, prompts, and model responses are never sent to
the environment merely because the API accepts a reasoning field. Local and
wire reasoning have separate schemas, byte limits, hashes, and output policies.

## 8.2 Write-ahead live-transaction journals

Every ordinary action decision has a monotonically increasing per-game sequence
and one of:

- prepared;
- failed_pre_dispatch;
- dispatched;
- acknowledged;
- outcome_unknown.

Required sequence:

1. Atomically commit prepared to the T0 journal with the pre-state hash, legal
   actions, decision, payload hash, budget reservation, and timestamp.
2. If a failure is proven before transport-function entry, atomically mark
   failed_pre_dispatch, release the action reservation, and do not dispatch.
3. Mark dispatched immediately before entering the pinned transport function.
4. Submit exactly once through that transport function.
5. On a valid response, atomically mark acknowledged and attach post-state,
   response metadata, and evidence references.
6. If dispatch may have occurred but no valid response exists, mark
   outcome_unknown and count the action against the local conservative spent
   bound without claiming that the server scored it.

The enforceable guarantee is at-most-one transport-function entry per decision,
not exactly-once environment effect. No exactly-once claim is made unless a
future authoritative API supplies and documents an idempotency mechanism.

Never automatically retry a live environment action after dispatched or
outcome_unknown. Model inference, parsing, and pre-dispatch construction retries
use separate counters and may never resubmit an ambiguous action.

Only a failure proven to occur before the transport call releases the action
reservation. Timeout, connection reset, malformed response, cancellation after
transport entry, or uncertainty about wrapper behavior defaults to
outcome_unknown.

The current RemoteEnvironmentWrapper.step cannot supply this classification
because it catches transport exceptions and returns None. Production may not use
that method as its dispatch authority unless a pinned patch exposes and tests the
required phase information. Once the transport function is entered, a failure is
never inferred to be pre-dispatch merely from an exception type or lack of a
response.

The pinned action transport disables and tests client-library, adapter, and
redirect-triggered automatic retries. A redirect, authentication challenge, or
retryable HTTP status is one transport entry and may not cause a second action
request. Network infrastructure outside the client remains outside the guarantee,
which is why the plan claims at-most-one client transport entry rather than
exactly-once effect.

After outcome_unknown, take no further environment action for that client unless
a current authoritative API exposes a tested read-only resynchronization call
that returns an observation bound to the same session and establishes the actual
post-state. The current plan assumes no such call. Therefore the default behavior
is to quarantine the client, cancel its model and queue work, preserve the spent
action classification, emit only permitted lifecycle status, and finalize it.
RESET is an environment action and is not a resynchronization mechanism.

The same journal semantics cover the initial constructor RESET currently hidden
inside Arcade.make, but the bootstrap transaction has a different prepared
schema. Before make it contains operation kind, decision/transaction ID,
scorecard ID, requested game ID, payload hash, reservation, and timestamp. GUID,
pre-state hash, legal actions, and an authoritative observation are explicitly
absent rather than filled with sentinels that could collide with real values.
Successful initial observation acknowledges the transaction and binds the GUID,
initial observation hash, and legal actions. Any ambiguous make/reset result
quarantines the client. No separate controller action is allowed between make and
this terminal classification.

Scorecard open and close use the lifecycle journal with the same transport-phase
states but operation-specific fields:

- Scorecard-open is prepared before transport, dispatched immediately before the
  request, and acknowledged only after a valid unique card ID is returned. An
  ambiguous open never triggers an automatic second open; without an
  authoritative recovery operation for the created card ID, it terminates the
  live run before any environment is made.
- Scorecard-close is prepared with the bound card ID and finalization manifest,
  dispatched immediately before transport, and acknowledged only after the
  authoritative close response or platform-generated submission confirmation.
  An ambiguous close is `finalization_unknown`. It is retried only when the exact
  backend documents or fixture-proves an idempotent close/recovery operation;
  otherwise no blind second close is sent.
- Open, make/bootstrap, action, and close transaction IDs occupy separate typed
  namespaces. No ordinary action counter includes scorecard lifecycle requests.

The lifecycle manifest records any authoritative status/recovery endpoint and
the exact retry decision for every phase. A generic HTTP exception class is not
evidence that an open or close request failed before reaching the server.

The T0 journal must remain available in bounded memory even when durable
evidence storage is degraded. If the prepared record cannot be committed to T0,
do not dispatch the action.

"Atomically commit" means one linearizable per-game in-process state transition
under the adapter's synchronization boundary. It does not imply survival of
process death, kernel failure, or host termination. A treatment may add a
durable write-ahead store only with explicit flush semantics and measured cost;
otherwise reports claim live transaction safety, not crash-durable recovery.

Pending journal state is not discarded in finally. Cleanup closes resources but
preserves the terminal journal classification.

## 8.3 Lifecycle and cap semantics

Maintain separate counters for:

- lifecycle commands attempted, acknowledged, and ambiguous;
- ordinary environment actions acknowledged and ambiguous;
- bootstrap play-start RESETs;
- later level RESETs acknowledged and ambiguous;
- conservative locally spent actions used for admission and cap safety;
- authoritative scorer-reported actions and resets when a final scorecard or
  official fixture makes them available;
- inference requests;
- parsing/repair attempts;
- workspace invocations;
- evidence retrievals;
- controller iterations.

Do not derive an `official_scored_actions` value from local transport state.
Acknowledged commands follow the mounted fixture's expected classification;
ambiguous commands contribute only to the conservative locally spent bound
because they may or may not have reached the scorer. The authoritative action and
reset totals, when available, are stored separately and reconciled against local
lower/upper expectations without overwriting the ambiguity record.

RESET is a command class, not unconditionally a scored-action subclass. The
implicit constructor RESET is recorded once as a bootstrap play-start command.
In the observed arc-agi 0.9.9 scorecard path it creates the play and increments
neither the action nor reset total. A later level RESET increments both totals in
that observed path. Toolkit-version fixtures verify both cases, plus visible
no-op actions, before every submission. After a valid initial observation,
Bootstrap must not send another RESET. A later RESET is permitted only by the
registered lifecycle policy, such as after GAME_OVER, and is separately
journaled.

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
- handles start, active play, level transition, GAME_OVER, exhaustion, WIN, and
  global deadline; ambiguous dispatch bypasses fallback and enters terminal
  quarantine;
- obeys competition reset behavior;
- cannot exceed validated action, reset, inference, retry, byte, or time caps;
- catches policy, model, parser, workspace, storage, and evidence failures;
- records a compact non-sensitive reason outside sealed/production redaction.

A no-visible-change result is scoped to an action plus context fingerprint. It
causes a decaying penalty, not a permanent claim that the action is a no-op.

## 8.6 Observation arms

representation_manifest.yaml freezes the complete model-visible encoding:

- rendered image dimensions, interpolation, palette, compression, and channel
  order;
- exact-grid text/binary serialization, axes, origin, orientation, separators,
  and truncation behavior;
- display-coordinate overlays and the mapping between image, grid, crop, and
  ACTION6 coordinates;
- crop selection, padding, labels, ordering, and maximum count;
- animation sampling, temporal order, timestamps/frame indices, and summary
  layout;
- multimodal token/byte accounting and model-specific preprocessing;
- representation version and deterministic fixtures.

No experiment may inherit an implicit representation from a notebook renderer,
model library, or workspace helper. Representation changes are treatments or
registered compatibility fixes.

R — raw final-frame bundle:

- current rendered observation;
- exact current grid;
- current available actions;
- game state and level metadata;
- the registered bounded window of recent actions, model turns, and canonical
  final frames;
- no engineered deltas, regions, animation summaries, intermediate frames, or
  ranked click candidates.

F — animation-enriched E0F bundle:

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

Intermediate-frame-derived features in F expose evidence absent from R. R/F
results therefore measure the complete observation-bundle change defined in
Section 6.8. Representation fixtures include an intermediate-only cue and prove
that neither the R prompt nor its workspace, retrieval, or model-facing error
channels can recover it from F telemetry. Animation analysis required elsewhere
in this plan may run behind R only as charged, policy-inaccessible telemetry;
it cannot affect R controller triggers, click selection, or scheduling.

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

These stores activate with E3, not merely because the storage implementation
exists. E1 has only its frozen recent-context window; E1M compaction is a
separate context treatment and does not implicitly enable this memory schema.

## 8.10 Model-visible context lifecycle

The context builder consumes only current T0 state and evidence/memory allowed
by the registered context treatment. It emits an ordered manifest of every
model-visible item, its evidence reference, token/byte cost, and omission or
compaction reason.

Every per-game context has:

- session_id and generation;
- internal opaque runtime-game-ID key plus current level/lifecycle identity; the
  ID key is excluded from model-visible content;
- evidence-frontier and pre-state hashes;
- visible-memory revision;
- continuity mode and cache handle, if any;
- compaction/eviction history;
- maximum age and resume eligibility.

Compaction produces a proposed bounded summary plus retained exact references.
Deterministic code validates schema, provenance, size, and contradictions before
the summary becomes visible memory. The uncompacted journal remains the evidence
authority subject to retention policy. A model-generated summary never becomes
verified merely by surviving compaction.

The E1M context family first compares stateless reconstruction and bounded
visible compaction. Persistent/KV-cached and programmatic-history variants enter
only when the selected local engine can package and isolate them under the same
competition artifact and runtime contracts.

## 8.11 Structured E1S policy

The baseline E1S response is a strict single-action schema containing:

- optional bounded intent/subgoal and rationale text for the current proposal;
- exactly one action ID and its action data.

Intent and rationale are unverified text. They receive no special persistence
beyond the registered recent-context window. Baseline E1S cannot update canonical
state, write structured memory, register hypotheses or predictions, retrieve
older evidence, or submit a queue. The controller alone owns lifecycle and
budget stop conditions.

Versioned schema extensions follow Section 5.4: E3 permits memory proposals; E4
permits historical evidence requests; E5 permits typed hypotheses and probes;
E6 permits dependency records, per-action expected effects, typed stop conditions,
and queues of at most four actions. Each extension activates only in its feature
manifest. E1M changes context construction without enabling these response fields.

Validation may repair bounded syntax only. It rejects disabled or unsupported
fields, illegal actions, invalid coordinates, oversized output, invalid
predicates, and budget violations. Under E6, a queue with more than one action
is invalid unless every continuation satisfies the non-vacuous, action-relevant
contract in Section 8.13 and its registered support gate in Section 8.14.
Validation never invents a replacement model action or converts an all-advisory
or irrelevant-predicate queue into a valid one.

## 8.12 Bounded E1C workspace

The default E1C treatment uses a fixed, non-Turing-complete safe-operation
language over immutable arrays and evidence queries in a separately launched,
resource-bounded worker. It:

- has no network;
- receives a sanitized environment;
- cannot access credentials, arbitrary filesystem paths, production objects,
  model artifacts, or evaluator state;
- cannot install packages;
- has bounded CPU, memory, output, files, and invocation count;
- cannot call arc_env or persist executable state between games;
- exposes only the registered R or F inputs and proposal-local scratch state;
- returns only the currently enabled E1S proposal schema, which contains one
  action in baseline E1.

The operation vocabulary, argument/output schemas, and invocation cap are frozen
as part of the C harness/tool factor. This safe-operation workspace is not
described as a Python REPL. Published Python controls use the separate execution
and fidelity classification in Section 5.2; no control gets an implicit exemption
from the isolation requirements below.

Full model-authored Python is a separate conditional E1C-PY treatment. It is
enabled only when the target Kaggle runtime demonstrates enforceable process,
filesystem, credential, native-code, and resource restrictions under adversarial
escape tests. AST filtering, an import allowlist, or a subprocess alone is not
such evidence. E1C-PY is disabled by default and is never required for the E1
factorial or milestone candidate.

## 8.13 Prediction predicate language

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
- scope and expiry;
- action/transition binding, observation field or region, and the typed
  next-action dependency it establishes when used to authorize continuation.

A material required expected-effect predicate is defined mechanically: it
constrains at least one post-action observation field to a strict subset of that
predicate family's valid outcome domain, is not a duplicate of an automatic
controller identity/legal/budget guard, and passes the family's registered
non-tautology validator. Examples of rejected predicates include an unconstrained
changed-cell range, membership in the complete game-state domain, or a disjunction
that accepts both every possible equality and difference outcome. Materiality is
therefore a schema result, not a model-supplied label.

Non-tautology is necessary but insufficient for continuation. Every later queued
action also declares a typed dependency set: the observed entity/region, expected
location or value, relevant local configuration, lifecycle scope, and supported
action-effect relation on which that action relies. Before the preceding action
is dispatched, each dependency is bound to a required post-action predicate and
an eligible support record. A finite, versioned predicate-to-dependency rule
table checks that the predicate establishes or preserves that dependency; a
free-text assertion that a predicate is relevant is rejected.

At least one required effect must establish a material dependency for the next
step, and every declared dependency must be checked. Unchanged dependencies may
use preservation predicates but do not replace the material-effect requirement.
For a movement queue, an expected translation of the bound player region and
the relevant destination configuration can qualify. A global hash difference,
generic changed-cell count, or timer/HUD animation alone cannot qualify as proof
of that movement. A whole-grid task may use a specific registered grid relation
when the next action depends on it; generic change remains insufficient.

Uncertain correspondence, an unsupported dependency type, an out-of-scope state,
or missing evidence makes the continuation invalid or UNKNOWN. The policy must
request another single action instead of widening a predicate after observing
the result. Registered validators establish relevance within the declared typed
model; they cannot prove that the model listed every real environmental
dependency. Reports retain that limitation and test closed-loop consequences.

Evaluation is three-valued:

- MATCH;
- MISMATCH;
- UNKNOWN.

For every queued action after the first, the proposal schema requires at least
one material, dependency-linked required expected-effect predicate for the
preceding action and complete declared-dependency coverage. Empty, all-advisory,
or action-irrelevant predicate lists are invalid. Independently of model output,
the controller injects mandatory continuation guards that require:

- the same session and context generation;
- an authoritative current observation at the expected evidence frontier;
- a lifecycle state that permits the next action;
- the queued action to remain in current normalized available_actions;
- current action-effect support, dependency bindings, correspondence status,
  and scope to pass the selected Section 8.14 gate;
- no unresolved dispatch, cancellation, or hard budget/deadline guard.

These controller guards cannot be removed, downgraded, or relabeled by the model.
A queued plan continues only when every required model predicate and every
controller guard is MATCH. A required MISMATCH cancels immediately. A required
UNKNOWN also cancels. Advisory predicates may be UNKNOWN without blocking only
when they were explicitly advisory before the preceding dispatch. The model
cannot relabel a mismatch or a previously required predicate.

Material prediction failure means any required predicate MISMATCH, a game-state
or legal-action surprise, a level transition not covered by the queue, or loss
of evidence required to validate continuation.

## 8.14 Hypothesis status and verification

E5 maintains zero to four active hypotheses. E6 may additionally maintain bounded
local dynamics-support records without activating competing-hypothesis generation.
`prediction_schema.json` freezes both schemas and their machine-checkable support
policy. Each record includes claim, typed scope and dependency bindings,
supporting and contradicting evidence IDs, registered prediction IDs,
action/stop recommendation, reversibility, risk, expiry, and exception count.
Hypotheses also include a proposed distinguishing probe where applicable. Neither
store is active in baseline E1.

A prediction is eligible for status advancement only when it was committed
before the referenced environment transition, names a required typed predicate,
has available evidence, and falls within the record's scope. For queue support,
the prediction must also satisfy Section 8.13's action-relevance and dependency
binding checks. Duplicate checks of one transition count once. Distinct
transition IDs are distinct observations, not a claim of statistical independence.
A prediction is discriminating only when at least two hypotheses registered
mutually incompatible required outcomes for the same probe/transition and the
disagreement concerns a dependency of the proposed continuation. The predicate
validator checks incompatibility and relevance; timer-only disagreements do not
verify movement mechanics.

The default deterministic status precedence and thresholds are:

1. Contradicted: at least one eligible required prediction is MISMATCH.
2. Retired: a frozen expiry, scope-exit, exception-limit, or explicit configured
   retirement condition is met and no new action may rely on the hypothesis.
3. Verified-for-plan: the selected gate below passes, no eligible required
   MISMATCH exists, all required evidence remains available, dependency bindings
   remain valid, and the typed scope covers the proposed use. This is bounded
   operational support for the specified steps, not proof of general mechanics.
4. Supported: at least one eligible MATCH and no eligible required MISMATCH.
5. Tentative: no eligible MATCH or MISMATCH has yet occurred.

The prospective E6 gate variants are:

- E6-DISC: at least two eligible action-relevant MATCH results on distinct
  transition IDs, including one validator-confirmed discriminating result.
- E6-REPEAT: the E6-DISC route, or at least three eligible action-relevant MATCH
  results for the same scoped action-effect relation across distinct transition
  IDs and at least two distinct dependency-scoped pre-state fingerprints, with
  no unresolved registered decision-relevant alternative. Fingerprints include
  the bound entity and relevant local configuration, exclude irrelevant timer/HUD
  changes, and retain a reference to the canonical full-state hash. The
  repeated-support route is limited to the
  observed typed local configuration class; it cannot extrapolate to a novel
  hazard, object identity, action relation, or unresolved irreversible choice.

The counts above are initial treatment defaults, frozen before testing. They do
not imply confidence levels. E6-REPEAT is the provisional gate to test when a
single repeatedly successful local behavior has no competing explanation;
runtime cannot choose whichever gate admits more actions unless that complete
policy was prospectively registered. Do not manufacture a competing hypothesis
solely to satisfy a discrimination requirement.

When registered hypotheses have incompatible action-relevant predictions or
different next-action/probe/stop recommendations under the proposed scope, code
sets `decision_relevant_alternatives`. Such unresolved alternatives block the
repeated-support route. The model cannot clear the flag by omitting a record;
contradiction, expiry, or retirement must follow the frozen evidence policy.
Absence of registered alternatives does not prove that no alternative exists.

Compare an admitted gate with the same parent's single-action policy under
matched total action, token, time, and inference ceilings. Where budget admits
both gates, compare E6-DISC and E6-REPEAT as a frozen multiplicity family. Charge
support-building probes and all extra inference to the gate treatment. Report
RHAE, action savings, calls saved, probes spent, blocked continuations, false
continuations, and scope failures. The one-action policy remains the default
unless closed-loop evidence supports an operational queue candidate. Neither
variant is required merely to complete an E1 comparison.

An accidental win does not verify mechanics unless it satisfies the same
pre-registered prediction rule. Every queued action after the first references
the verified-for-plan hypothesis/dynamics IDs and required predicates that cover
that step; a scope mismatch, downgraded status, or unavailable required evidence
cancels the queue.

## 8.15 Controller state machine

| Mode | Entry | Permitted behavior | Exit |
|---|---|---|---|
| Bootstrap | Before initial make, observed level transition, or authoritatively resynchronized state | Journal the current make-path constructor RESET before initial make; otherwise capture T0/T1 from the authoritative observation; never issue a duplicate RESET after valid initialization | Normal after valid observation; Quarantined after ambiguous initialization |
| Normal | Valid state without verified queue | One proposal and one action | Fast, Deep, Recovery, Exhausted, or Done |
| Fast | E6 enabled and action-relevant dependencies pass the registered support gate | Continue one queued action after dependency, predicate, and controller-guard checks | Normal on completion; Recovery on mismatch/unknown |
| Deep | Novelty, contradiction, irreversible choice, or registered uncertainty trigger | Retrieve bounded evidence and use deeper inference; one environment action | Normal or Recovery |
| Recovery | Prediction failure, loop, repeated no-change, or state inconsistency with an authoritative current observation | Cancel queue, retire/downgrade claims, select safe novel evidence; one action | Normal, Exhausted, or Done |
| Exhausted | Model/workspace budget unavailable or deadline degradation active | Deterministic fallback only | Done or level transition |
| Quarantined | Ambiguous dispatch without authoritative resynchronization, or untrusted lifecycle identity | No further environment action; cancel outstanding work and finalize client | Done only |
| Done | WIN or hard global termination point | No environment action; finalize client | Terminal |

Transition precedence is:

1. hard deadline or WIN;
2. ambiguous dispatch or untrusted lifecycle identity -> Quarantined;
3. recoverable state inconsistency with an authoritative observation;
4. prediction mismatch;
5. budget exhaustion;
6. deep trigger;
7. verified queue;
8. normal operation.

The exact trigger thresholds live in validated configuration and are included
in every experiment hash.

This table describes the complete controller. A run exposes only modes and
semantic transitions enabled by Section 5.4; inactive E5/E6 infrastructure
cannot trigger Deep or Fast behavior in E1.

## 8.16 Shared inference

The service provides:

- exactly-once model initialization;
- request and per-game state isolation;
- registered per-game context/cache lifecycle and hard residency ceilings;
- bounded queues;
- cancellation and stale-request rejection;
- request, client, and global deadlines;
- exception containment;
- queue/service/token/VRAM/RAM telemetry;
- deterministic degradation to fallback.

Model requests have unique IDs and may be retried only before a proposal is
committed to a live ActionDecision. Stale responses are discarded by
generation and pre-state hash.

## 8.17 Score-aware scheduling without hidden-baseline access

Every environment receives a cheap deterministic bootstrap sufficient to
create the one allowed session and obtain an initial observation when possible.
This does not imply a guaranteed expensive model call.

A model-service floor may be introduced only if a registered comparison shows
that it improves whole-run full-set mean RHAE or reliability. Otherwise calls
come from the shared admission policy.

For a game with n known win levels and next level index k:

    normalized_immediate_value = k / (n * (n + 1) / 2)

If n is missing or zero, use the configured conservative unknown-level value;
never divide by zero.

Rank discretionary work using:

    expected_value =
        P(complete_next_level_within_budget)
        * normalized_immediate_value
        * policy_visible_efficiency_proxy
        + bounded_future_option_value

    priority_rate =
        expected_value / max(expected_marginal_critical_path_seconds, t_min)
        + uncertainty_exploration_bonus_rate
        + aging_bonus_rate

Every term is measured in bounded normalized game contribution per second. The
denominator estimates marginal critical-path time attributable to admitting the
request, including queue, service, environment, and expected follow-up time; it
is not total remaining notebook time. Bonus rates have configured caps and may
not make a zero-feasibility request outrank a hard guard. The future-option term
counts only value not already included in the immediate term.

The live efficiency proxy may use only policy-visible features such as current
level action count, progress observations, prediction accuracy, loop/no-change
rate, model confidence calibration, and remaining budget. It never receives a
human baseline, evaluator score, public game ID, or per-game lookup value.

Compare two prospectively registered training regimes when permitted:

1. Baseline-free: completion within a fixed future action/time window.
2. Public-score-supervised: game-level cross-validated public score contribution
   or RHAE, with all rows from the evaluated game excluded from its training and
   calibration path.

The second regime is an offline public-development optimization treatment, not
a claim of baseline-free learning or hidden-set generalization. It is accepted
only by closed-loop paired whole-run evaluation and is disabled if provenance,
rules, or leakage audits fail.

Coefficients trained on public RHAE encode public-scoring information even when
no score is supplied at runtime. Reports state that fact explicitly. Such
coefficients are permitted only in the separately labeled public-supervised arm;
they never use hidden/live baselines or per-game identity and never enter the
baseline-free arm.

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

Each scheduler variant is evaluated in separate complete-workload runs under
Section 6.10. Per-game values are diagnostic decompositions, not independent
replicates of an allocation policy. Training/calibration folds exclude all rows
from each evaluated game; resulting fixed-workload performance claims still
retain the full-run resource coupling and selection limitations.

## 8.18 Competition-parity runner

scripts/play_competition_like.py exposes:

1. Official backend using the current official API and competition mode where
   available.
2. Instrumented local backend emulating lifecycle invariants for deterministic
   tests and clearly labeled as emulation.

Both enforce:

- one acknowledged scorecard open, with ambiguous-open termination and no blind
  second open;
- at most one make per environment;
- a fixed complete inventory before play;
- zeroes for untouched and failed environments;
- no in-flight score access;
- competition reset behavior;
- exact per-client and global deadlines;
- all clients terminating before close;
- journaled close/finalization on recoverable error paths, with
  finalization_unknown rather than a blind retry after ambiguous transport;
- explicit NormalizedRHAE versus OfficialRHAEPercent units and versioned
  initial-RESET, level-RESET, and visible-no-op scorer fixtures;
- hidden-production output policy when applicable.

Only a Kaggle end-to-end submission is authoritative for deployment.

## 8.19 Conditional advanced treatments

E7 executable model/scripts:

- Enter only after a registered trigger identifies repeated long-horizon,
  mechanics-consistency, or state-tracking failures that the selected textual
  system does not resolve within its matched budget.
- Use the E1C-PY isolation boundary only after its target-runtime proof; otherwise
  restrict E7 to the safe-operation language or disable it.
- Require prediction tests against real transitions.
- Measure mechanics/transition fidelity, goal fidelity, next-action utility,
  closed-loop RHAE, construction/repair/bypass decisions, and total cost
  separately.
- Disable when improved replay or transition fidelity does not translate into
  sufficient next-action or closed-loop value for its time and failure cost.

E8 verified search:

- Enter only when a compact state and transition model have sufficient
  registered predictive accuracy for the searched variables.
- Permit bounded belief-space or information-gathering search when unresolved
  hypotheses, rather than deterministic state transitions, are the search
  object; label this separately from verified deterministic search.
- Search never bypasses real-transition validation.
- Replan after each real action.

E9 specialist:

- Compare with spending the same token/time budget on the primary model.
- Return advice only through the normal proposal/evidence boundary.
- Never receive evaluator-only or cross-game state.

## 8.20 Prospective interaction checkpoints

Sequential acceptance is the default for attribution, but it is not assumed
that component value is additive. Freeze a small interaction family before
results at three checkpoints:

1. IX1 after E4: representation/animation × memory/retrieval.
2. IX2 after E6: hypotheses × context continuity × prediction-checked queues.
3. IX3 after E8: executable model × verification/search × delegation policy.

Each checkpoint compares complete registered bundles under matched global
ceilings and multiplicity control. A component rejected alone may enter only as
part of a prospectively registered bundle and may be described as an interaction
result, not an accepted marginal improvement.

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
      competition_loop.py
      framework_adapter.py
      runtime_audit.py
      output_policy.py
      production_main.py
      model_policy.py
      context.py
      representation.py
      scratchpad.py
      inference.py
      scheduler.py
      watchdog.py
      config.py

    evaluation/
      metrics.py
      counters.py
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
      framework_adapter_manifest.yaml
      context_policy.yaml
      representation_manifest.yaml
      holdout_ledger.yaml
      success_criteria.yaml
      scorer_fixture.json
      prediction_schema.json
      action_journal_schema.json
      lifecycle_journal_schema.json
      sealed_output_schema.json

    scripts/
      play_local.py
      play_competition_like.py
      check_kaggle_config.py
      validate_local_gateway.py
      validate_phase0.py
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
| action_journal.py | Live action plus scorecard/open, bootstrap/make, and close transaction state | Action selection |
| state.py | Typed bounded per-game state | I/O or model lifecycle |
| perception.py | Observation facts and candidates | Semantic facts not supported by evidence |
| animation.py | Temporal facts and candidates | Unverified intent |
| evidence.py | Retention, availability, and retrieval | Unbounded history |
| prediction.py | Predicate validation, action-relevant dependency checks, registered queue support gates, and deterministic hypothesis-status evaluation | Model authority or qualitative status promotion |
| controller.py | Modes, legal action, budgets, fallback | Provider-specific prompts |
| competition_loop.py | Per-client lifecycle and all-game orchestration | Raw environment calls or model interpretation |
| framework_adapter.py | Pinned upstream adaptation, the only environment-call boundary, lock-compatible startup topology, opaque runtime identity, and compatibility checks | Policy decisions or game-ID-conditioned behavior |
| runtime_audit.py | Fail-closed mounted distribution, source, signature, and wire-contract checks | Policy choice or environment calls |
| model_policy.py | Evidence selection and proposals | Environment calls |
| context.py | Per-game context construction, compaction, cache identity, and resumption | Cross-game mutable state |
| representation.py | Versioned model-visible image/grid/animation encodings | Semantic claims |
| scratchpad.py | Isolated analysis | Secrets, environment authority, or evaluator data |
| inference.py | Model lifecycle, serving, and nominal-versus-admission capacity accounting | Per-game policy memory |
| scheduler.py | Admission and priority without hidden/live baselines | Evaluator state or per-game score lookup |
| watchdog.py | Independent global stop-admission and finalization deadlines | Policy ranking |
| metrics.py | Official-score replication | Policy inputs |
| statistics.py | Frozen isolated-policy or paired-whole-run experiment decisions with the declared dependence structure | Retrospective threshold changes |
| sealed_eval.py | Best-effort aggregate-only H1/H2 execution | Policy decisions |
| config.py | Validated immutable configuration | Runtime mutable state |

# 10. Capacity-constrained implementation schedule

Dates are planning targets, not authority to compress validation. When work
exceeds the frozen phase budget, shed optional treatment scope and preserve
transaction safety, privacy, reproducibility, load testing, rollback, and
finalization reserve.

The minimum milestone path is G0, E0, M0, the competition-minimum scheduler and
110-client envelope, one current reproducible competitive control, one registered
E1 primary comparison, candidate load certification, and freeze. E2–E9 and IX1–
IX3 are a failure-driven research backlog, not mandatory calendar deliverables.

Before work starts, runtime_profiles.yaml and experiment_registry.yaml freeze:

- total and per-phase accelerator-hour and game-run budgets;
- maximum target-hardware notebook runs and scored Kaggle submissions;
- a contingency reserve for failed infrastructure runs;
- the order in which optional treatments are dropped;
- the latest dates for H1, H2, candidate freeze, rollback, and release.

## Phase 0 — Governance and competition-safe E0

Dates: September 4–7

Deliverables:

- Git initialization and ignore audit.
- Dated competition-constraint register including rules, licensing, identity,
  entry/team deadlines, submission allowance, filename, size limit, freely and
  publicly available external-input rule, score units, and reset/no-op action
  semantics.
- Forensic public-inventory exposure audit, truthfully classified partition, and
  append-only exposure ledger.
- Valid schemas for every E0 dependency; later-treatment registries exist in an
  explicit inactive state and fail parameter closure until frozen.
- Pinned adapter that owns raw transport-phase classification, fresh request
  serialization, the only environment-call boundary, and terminal quarantine
  after unresolved outcome_unknown.
- Captured mounted-client transport fixtures for authentication, sessions,
  cookies, identity binding, reasoning encoding, response conversion, and
  last-response state.
- Journaled scorecard open and close with explicit ambiguous-open and
  finalization_unknown behavior and no unproven retry.
- Journaled make/bootstrap handling for the currently implicit constructor RESET,
  including one lifecycle-command record, mounted-fixture scored-counter
  classification, and no repair reset after ambiguity.
- CompetitionAgentLoop and CompetitionOrchestrator with one declared
  lock-compatible startup topology, streaming admission of acknowledged clients,
  disabled recording, exact counters, output isolation, and independent
  finalization watchdog.
- Immutable ActionDecision, deterministic legal fallback, production-valid R
  path, a retained-output root whose handled-exit allowlist contains only
  submission.parquet, and a separate run-unique non-retained scratch root.
- Competition-minimum bounded inference queue with a deterministic fair admission
  rule and a declared synthetic 110-client load fixture.
- Basic official/emulated competition-parity runner and validated multi-file
  notebook packaging.

Exit gate:

- Three development runs have no invalid action or uncaught agent exception.
- Fixed-seed deterministic code traces are stable.
- No production call bypasses the adapter and journal; patched transport tests
  distinguish pre-transport failure and conservatively quarantine every
  ambiguous post-entry failure.
- The replacement transport passes the full mounted-client behavioral-equivalence
  fixture rather than only URL/payload mocks.
- The startup fixture proves that unmodified shared Arcade.make calls are treated
  as serialized; any concurrent-make topology proves its lock, scorecard, cookie,
  one-make, and session-isolation invariants.
- ACTION6 payload and reasoning cannot cross clients.
- Unknown mounted framework revisions and unresolved E0 parameters fail before
  any environment action.
- Upstream unbounded frame retention, recording, and scorecard logging are absent
  from hidden-production execution.
- One-make, one acknowledged scorecard open, no-live-score, reset/no-op counter,
  explicit-score-unit, all-games-count, close-transaction, output, and
  finalization invariants pass.
- The minimum scheduler has bounded queue length/age and survives the declared
  synthetic 110-client fault test.
- The activation record passes. Only then does Plan 8 supersede Plan 7.

A scored E0 Kaggle submission is spent only if needed to validate an unproven
deployment seam and only after the local/emulated exit gate passes. Do not spend
the daily submission merely to measure the known random fallback.

## Phase 0F/M0 — Evidence foundation and model viability

Dates: September 8–10

Deliverables:

- Immediate uint8 packing, T0–T3 bounded retention, stable hashes, evidence
  availability, and replacement of upstream frame accumulation.
- Minimal R and toggleable E0F F representations with coordinate and
  representation fixtures.
- Target-RTX cold-load, first-token, throughput, cancellation, VRAM, RAM, and
  offline-packaging profiles for a small frozen set of eligible models,
  quantizations, engines, and reasoning settings.
- A provisional M0 primary and fallback selected before E1 implementation.

Exit gate:

- Exact evidence round-trips byte-for-byte and loss is never silent.
- Storage failure preserves T0 and legal play.
- R cannot access F policy features.
- The provisional model/engine fits the offline artifact, memory, throughput,
  queue, and 7.65-hour projected execution envelope.

## Phase 1 — Current controls and E1 decision

Dates: September 11–16

Deliverables:

- Frozen current Qwen3.8 Duck-style control and the strongest eligible
  structured-action control at the provenance cutoff, with any unavailable
  Python reproduction and adapted substitute explicitly classified under
  Section 5.2.
- Published reproduction and, where justified, same-model normalized results.
- Strict single-action E1S and default safe-operation E1C implementations using
  the already frozen competition-minimum queue policy and enforced Section 5.4
  feature manifest. Published-control capabilities and fidelity are separately
  declared, including the Python runner's availability/isolation decision.
- Causal four-cell E1 only if one model supports all cells; otherwise an
  explicitly non-causal bundle tournament plus a smaller same-model comparison.
- Stateless reconstruction versus visible compaction only when context continuity
  is a demonstrated bottleneck; cached/programmatic modes remain optional.
- Hierarchical report, completed model/runtime table, offline dependency bundle,
  and one operational primary.

Exit gate:

- No factorial claim uses differing models, queue policies, or uncharged work.
- Disabled later-treatment features cannot execute in E1, and R/F claims name
  the observation bundle including intermediate-frame evidence access.
- Each comparison declares its isolated-policy or shared-resource-whole-run mode
  and uses the corresponding randomization and uncertainty unit.
- Every accepted cell fits measured safety and resource ceilings.
- Cross-validation reports the selection-procedure estimand separately from any
  final fixed candidate.
- Sparse/tied evidence that cannot support the frozen inferential rule receives
  Provisional primary status rather than an overstated acceptance claim.
- A full-run projection under the minimum scheduler fits the hard constraints
  using headroom-adjusted C_admit, not C_nominal or a best-run mean.

## Phase 2 — Failure-driven evidence and memory

Dates: September 17–20

Use diagnostics from the selected E1 system to choose at most the predeclared
number of E2a–E4 treatments. Do not implement all treatments by default. Each
chosen treatment needs a specific reproduced failure, prospective comparison,
compute allocation, and stop rule. IX1 runs only when two coupled components are
both plausible and budget remains.

## Phase 3 — Failure-driven hypotheses and queues

Dates: September 21–23

E5 and E6 enter only for reproduced orientation, hypothesis-collapse, probe, or
replanning failures. The typed prediction evaluator and controller correctness
tests may be shared infrastructure, but a multi-action queue is not accepted
without action-relevant dependency predicates, mandatory controller guards,
registered discrimination/repeated-support gates, and paired closed-loop
evidence against the same parent's single-action control. Ambiguous
dispatch always quarantines rather than entering Recovery. Run H1 once only after
architecture and resource behavior are stable and only under its truthful
untouched or reduced-exposure label.

## Phase 4 — Advanced scheduling and full-load certification

Dates: September 23–25

Compare the already-valid minimum scheduler with at most one registered advanced
policy: baseline-free completion prediction or, when permitted, separately
labeled cross-validated public-score supervision. Compare separate complete
workload runs with counterbalanced run order and paired-run uncertainty under
Section 6.10. Test priority units, aging,
batching/worker topology, storage/model/workspace faults, cancellation, and a
full 110-client official-like load. Freeze C_nominal, the conservative
latency/throughput bound, service headroom, and C_admit separately. Reject the
advanced scheduler if it does not improve full-set value or reliability within
the budget; retain the minimum fair scheduler as rollback.

Exit gate:

- Queue age is bounded and all failures degrade legally.
- No hidden/live baseline or game identity reaches live features.
- Clients stop admitting work before finalization reserve.
- Competition-like execution finishes below 7.65 hours with the selected model,
  evidence, context, and scheduler configuration.

## Phase 5 — Optional advanced-treatment decision

Date: September 25

This is a go/no-go decision, not a promise to implement E7, E8, E9, and IX3 in
one day. Admit at most one already-prototyped advanced treatment only when its
prerequisite failure, isolation, prospective experiment, remaining compute, and
freeze margin all pass. Otherwise defer E7–E9 and IX3 until after the milestone.

## Phase 6 — Candidate selection and freeze

Dates: September 25–26

Select a conservative candidate and, only when genuinely behaviorally distinct,
a higher-reasoning candidate using registered complete-workload comparisons.
Freeze manifests, hashes, reproducibility class,
output audit, full-load result, submission artifact, and known-valid rollback.
Apply the predeclared aggregate H2 rule once under its truthful exposure label.
Freeze no later than September 26.

The two final-submission slots are selected for expected private score and useful
behavioral diversity, not merely the two highest noisy public scores. The exact
diversity and tie-break rule is frozen before final selection.

## Phase 7 — Release and submission verification

Dates: September 27–30

Public-source, license, model-provenance, and reproduction materials are prepared
continuously from Phase 0; this window verifies rather than first creates them.
Revalidate constraints and account allowance, verify mounts and hashes, reproduce
from a clean checkout offline, audit the sole retained output artifact and
scratch-root cleanup classification, preserve a fresh kernel/rollback path, and
make the planned milestone submission. Do not introduce unmeasured policy changes
after freeze.

The milestone deadline is September 30 at 11:59 PM UTC, or October 1 at
7:59 AM China Standard Time.

## 10.1 Scored-submission budget

The live allowance is one scored submission per day and up to two final
selections. submission_plan in experiment_registry.yaml prospectively allocates
scored runs among deployment validation, current-control calibration, primary
architecture, candidate confirmation, and rollback. It records unused reserve,
kernel identity, code/config hashes, and whether a platform error consumed the
allowance. A successful scored run is never repeated without a decision it can
change; public score remains adaptive evidence.

# 11. Test plan

## 11.1 Unit tests

- Stable per-game seed derivation across processes.
- Legal-action normalization.
- No production set_data() calls.
- ACTION6 coordinate bounds and typed transforms.
- Exact 16 KiB compact-JSON boundary for the server-parsed reasoning field value,
  plus a separate below-boundary production-margin test.
- Exact logical-object, intermediate reasoning string, server-parsed field value,
  and full-request serialization fixtures for the pinned production serializer,
  including escaping and local/wire reasoning separation.
- Immutable request-local action and reasoning payloads.
- Action-journal state transitions.
- Lifecycle-journal scorecard-open, bootstrap/make, and scorecard-close state
  transitions, including ambiguous-open and finalization_unknown terminals.
- Ambiguous dispatch is never automatically retried.
- outcome_unknown enters Quarantined and cannot reach another environment action
  without a fixture-proven authoritative resynchronization capability.
- A pre-transport fixture may release an action reservation; timeout or failure
  after transport-function entry may not.
- The unpatched current RemoteEnvironmentWrapper.step is unreachable from the
  production dispatch call graph.
- Action transport has no implicit retry or redirect path capable of issuing a
  second command request.
- Exact action/reset/retry/call cap semantics.
- Initial-play RESET versus later-level-RESET scorer classification and no double
  counting; the fixture must match the exact mounted toolkit/backend behavior.
- A bootstrap journal record exists before current make-path constructor RESET
  without fabricated GUID, legal-action, observation, or pre-state fields; a
  successful initial observation acknowledges and records the lifecycle command
  exactly once without assuming it increments scored action/reset totals.
- Ambiguous make/constructor RESET quarantines, and valid make initialization is
  never followed by an automatic duplicate RESET.
- Packed-frame hash and compression round-trips.
- T0 preservation and T1–T3 degradation order.
- Evidence availability and verified-claim downgrade.
- Animation, transient, appearance, disappearance, and motion fixtures.
- R/F policy isolation and telemetry accounting.
- An intermediate-only visual cue reaches F but cannot reach any R policy,
  workspace, retrieval, trigger, or scheduler path.
- E1 feature-negative tests reject queues, typed predictions/hypothesis writes,
  durable memory, out-of-window retrieval, and inactive tool/mode access.
- Later-treatment parent manifests differ only by their registered feature delta;
  E1M compaction cannot activate E3/E5 stores.
- Deterministic representation fixtures and representation-hash changes.
- Context manifest, compaction provenance, cache identity, eviction, and safe
  resumption against generation/evidence/pre-state hashes.
- Prediction predicate schema and MATCH/MISMATCH/UNKNOWN behavior.
- Queue validation rejects empty, all-advisory, and action-irrelevant
  continuation predicates; each later action requires a family-validated
  non-tautological effect with complete typed dependency coverage plus
  non-removable session, generation, evidence-frontier, lifecycle, legal-action,
  ambiguity, budget, and deadline guards.
- Hypothesis/dynamics status uses only pre-registered action-relevant predictions,
  distinct transition IDs, validator-confirmed relevant incompatible outcomes or
  the frozen repeated-support route, evidence availability, typed scope, and
  frozen status precedence/thresholds.
- A ticking timer, irrelevant animation, unrelated matching region, or generic
  hash change cannot certify blocked movement or another unmet dependency.
- Duplicate transitions and identical dependency-scoped pre-state fingerprints,
  including full frames differing only by a timer, cannot satisfy the
  repeated-support diversity gate; unknown correspondence, a changed local
  configuration class, and missing dependencies reject continuation.
- Repeated scoped success without a competitor may qualify under E6-REPEAT;
  unresolved action-relevant alternatives block that route and cannot be dropped
  by model omission. E6-DISC retains its distinct stricter requirement.
- Opaque runtime game IDs are accepted only by infrastructure identity paths and
  are absent from model-visible context, scheduler inputs, learned lookup keys,
  and packaged static policy tables.
- Controller transition precedence.
- Stale inference-response rejection.
- Baseline-free scheduler feature audit.
- Public-score-supervised scheduler fold isolation and live baseline-denial
  audit, when that treatment is enabled.
- Scheduler zero/missing-win-level guard.
- Nominal inference capacity never becomes an admission ceiling; conservative
  admission uses registered headroom and an upper latency or lower-throughput
  confidence rule under tail-latency fixtures.
- Official RHAE fixture parity in both NormalizedRHAE and
  OfficialRHAEPercent, including explicit conversion and initial-RESET,
  later-RESET, visible-no-op, and ambiguous-action cases.
- External-input validation rejects any artifact that is not freely and publicly
  available or lacks the required provenance/license decision.
- Fold, seed, crash, tie, multiplicity, and status classification.
- Shared-resource inference resamples paired complete-run blocks, rejects
  independent per-game sign flips, and handles candidate-caused resource failure
  without excluding it as external infrastructure noise.
- Sealed output allowlist and cleanup status.
- Retained-output-root allowlist, scratch-root routing, and handled-exit cleanup
  classification.

## 11.2 Integration tests

- One scorecard open is acknowledged at most once; ambiguous open terminates
  without a blind second open.
- Scorecard close is journaled and becomes acknowledged or
  finalization_unknown; retry occurs only through a fixture-proven idempotent
  close/recovery operation.
- Every environment call crosses the adapter's single journaled dispatch seam.
- Replacement transport matches captured mounted-client fixtures for headers,
  session/cookie updates and locking, scorecard/game/GUID identity, reasoning
  encoding, status/JSON handling, FrameDataRaw conversion, available actions,
  and last-response updates.
- The initial RESET currently performed inside make crosses the bootstrap journal
  seam before transport and is terminally classified.
- Unknown framework revisions and unresolved parameters fail before play.
- Every environment is made at most once.
- No in-flight score request occurs.
- RESET follows competition semantics.
- Untouched, failed, and timed-out games are zero.
- All clients terminate before close.
- Missing and duplicate game IDs fail inventory validation.
- Action accepted plus response failure produces outcome_unknown.
- Model timeout, malformed output, cancellation, and stale response.
- Workspace timeout, forbidden operation, oversized output, and crash.
- Safe-operation E1C is the default; E1C-PY remains unreachable unless all
  target-runtime isolation gates pass.
- Faithful Python controls retain their actual tools and batching through a
  proven runner; safe-operation substitutions are labeled adapted controls.
- Exactly-once model initialization.
- `serialized_make_streaming_play` begins each acknowledged client without a
  full-inventory barrier while proving that unmodified shared Arcade.make calls
  remain serialized.
- Any enabled concurrent-make topology proves its lock patch or per-client
  construction, one-scorecard, cookie/authentication, one-make, and session
  isolation behavior.
- Notebook watchdog finalizes when agent or inference workers hang.
- Engines with and without true generation cancellation obey the declared
  compute-exposure policy.
- Level transition during a queue.
- Disk-full and evidence-store failure while play continues.
- 110 simultaneous clients with maximum queue-age enforcement.
- Synthetic 110-client fixtures declare inventory, latency, fault, and response
  distributions separately from real-game evidence.
- Whole-run treatment/control pairs have identical workload and global-budget
  manifests, isolated run state, counterbalanced order, and no mixed-treatment
  adaptive queue. A deliberately slow client demonstrates measurable cross-game
  allocation effects in the whole-run report.
- Global deadline triggers stop-admission and finalization.
- Local and official backends remain clearly labeled.
- Clean-checkout local bootstrap.
- Clean-checkout Kaggle offline execution with mounted artifacts.
- Hidden-production run leaves no prohibited retained artifact or notebook
  output and routes writable source copies, bytecode, compilation products,
  caches, workspaces, and hidden evidence to the declared scratch root.
- After normal and tested handled-failure exits, the resolved retained output
  root contains only submission.parquet. Forced SIGKILL/OOM and platform-owned
  state are reported outside the cleanup guarantee rather than as verified clean.
- Scored-submission budget rejects an unregistered or exhausted submission.

## 11.3 Closed-loop experiments

| Treatment | Primary comparison |
|---|---|
| E0 | Correct deterministic path versus current random implementation |
| M0 | Eligible model/engine/reasoning profiles under target-hardware resource and small frozen performance screens |
| E0W-S-PUB | Published structured system versus E0 |
| E0W-C-PUB | Published workspace system versus E0 |
| E0W-S-NORM | Same-model normalized structured control |
| E0W-C-NORM | Same-model normalized workspace control |
| E1 factorial | Four same-model single-action observation-bundle/harness-tool-bundle cells with enforced feature manifests |
| E1M context | Reconstruction versus compaction, cached continuity, and programmatic history as supported |
| E2a | Advanced inter-action evidence versus E0F |
| E2b | Advanced animation summary versus E0F summary |
| E2c | Selective rich animation versus summary only |
| E2d | Advanced correspondence versus lightweight regions |
| E3 | Durable/scratch memory versus bounded recent history |
| E4 | Exact retrieval/retrodiction versus summary-only context |
| E5 | Bounded hypotheses versus one unconstrained explanation |
| E6 | Registered action-relevant queue gate versus the same parent's one-action policy, charging support-building cost |
| E6-DISC / E6-REPEAT | Conditional discrimination-only versus scoped repeated-support gate comparison |
| Advanced scheduler / candidate selection | Paired separate complete-workload runs under the same global budget |
| E7 | Executable model/scripts versus selected E6 system |
| E8 | Verified search versus selected E7 or E6 system |
| E9 | Specialist request versus equal-budget primary-model reasoning |
| Interaction checkpoints | Prospectively registered coupled bundles versus selected additive baseline |

Fixed trajectories may establish correctness and cost. Policy acceptance
requires registered paired closed-loop evaluation.

# 12. Required reports and decisions

Every development experiment report includes:

- registry and source hashes;
- result class;
- model/harness/observation identity;
- framework-adapter, representation, and context-policy identity;
- fixed game, fold, and seed manifests;
- enforced feature manifest, parent delta, control-fidelity class, and R/F
  evidence-access difference;
- execution mode, complete workload, randomization/uncertainty unit, paired-run
  block count, and whole-run order where resources are shared;
- exposure-ledger state and blocked/counterbalanced execution order;
- full-set mean with an explicit NormalizedRHAE or OfficialRHAEPercent type and
  conversion provenance;
- paired per-game effects and uncertainty;
- delta_min and multiplicity family;
- accepted/rejected/inconclusive statistical status;
- separate operational status;
- raw and selection-aware estimates when applicable;
- coverage, completions, levels, and weighted completion;
- actions per completion and before first progress;
- invalid, no-change, loop, reset, death, and ambiguous-dispatch rates, with
  acknowledged, ambiguous, conservative-spent, and authoritative scorer action
  totals kept separate;
- prediction outcomes and queue breaks;
- queue gate, dependency-coverage failures, support-building probes, calls/actions
  saved, false continuations, and scope failures;
- memory revisions and evidence availability;
- context compactions, cache hits/rebuilds, evictions, and resume failures;
- model/workspace/fallback rates;
- calls, tokens, queue/service/client times, global elapsed time;
- consumed and remaining experiment game-run, accelerator-hour, notebook-run,
  and scored-submission budgets;
- peak RAM, VRAM, disk, and evidence bytes;
- worst regression and catastrophic-tail result.
- implementation-complete and competition-performance gate status.

The mandatory model/runtime decision table includes:

| Field | Required value |
|---|---|
| Constraint-register version | Hash and verified_at |
| Accelerator/runtime | Exact measured platform |
| Primary and fallback models | Source, revision, architecture, and license |
| Quantization/engine | Exact formats and parameters |
| Paradigm | E1S, safe-operation E1C, conditional E1C-PY, or measured hybrid |
| Result class | Published, normalized, or competition candidate |
| Observation | R or F plus animation policy |
| Context policy | Limits, continuity, and eviction |
| Framework adapter | Upstream revision, replaced seams, adapter hash, compatibility result |
| Startup topology | Serialized-make/streaming-play or proven concurrent-make mode, lock behavior, and fixture result |
| Transport compatibility | Headers, session/cookie, GUID, reasoning encoding, response conversion, and last-response fixture result |
| Lifecycle transactions | Scorecard open/close and make/bootstrap ambiguity and recovery policy |
| Score unit and counter semantics | NormalizedRHAE or OfficialRHAEPercent; initial RESET, later RESET, visible no-op, and ambiguous-action treatment |
| Representation | Image/grid/coordinate/crop/animation manifest hash |
| Proposal schema | Feature-gated model-output schema, token/byte limit, action-relevant dependency predicates, queue support gate, validation, and repair |
| Experiment execution | Isolated or whole-run mode, workload/global-budget hashes, paired-run blocks, and randomization/uncertainty units |
| Runtime identity policy | Opaque game-ID infrastructure uses and proof of policy/model/scheduler exclusion |
| Production artifact output | Resolved retained output root, submission.parquet-only handled-exit allowlist, scratch roots, and policy hash |
| Reproducibility | Bitwise, seed-stable, or distributional |
| Throughput | Sustained requests/hour plus conservative lower-bound rule |
| Latency | Queue/service/client p50/p90/p99 plus registered admission guard quantile/bound |
| Memory/storage | Peak VRAM, RAM, disk, and evidence |
| Calls/tokens | C_nominal, C_admit, service headroom, and hard global/per-mode maxima |
| Allocation | Bootstrap, discretionary, and admission rule |
| Caps | Environment, reset, model, workspace, and retry |
| Deadlines | Request, queue, client, stop-admitting, and global |
| Degradation | Tested fallback path |
| Scheduler proxy | Features, training target, and calibration |
| Holdout state | Exposure-ledger version, eligibility, consumption, and invalidation |
| Success gates | Frozen engineering and performance thresholds |
| Output/privacy | Production and sealed policies |

# 13. Principal risks and controls

| Risk | Control |
|---|---|
| Competing plans define different truth | Explicit authority precedence; Plan 8 controls only after recorded activation |
| Plan activates with unresolved placeholders | Parameter-closure validator fails closed before each experiment |
| Inventory listing exposed semantic titles | Forensic provenance audit, truthful exposure classification, and reduced-exposure labeling or holdout reassignment |
| Upstream loop bypasses transaction/evidence policy | Pinned framework adapter owns the only environment-call boundary |
| Wrapper hides whether transport was entered | Bypass or pin-patch wrapper with tested phase reporting; uncertain cases become outcome_unknown |
| Replacement transport loses cookies, GUID binding, reasoning encoding, or response state | Captured mounted-client equivalence fixtures plus a competition-parity smoke test |
| Wrapper constructor resets before ordinary dispatch | Prepare and dispatch a bootstrap transaction around make, record the play-start command once, fixture-test its scored-counter treatment, and prohibit duplicate initialization reset |
| Ambiguous action is reported as officially scored | Separate acknowledged, ambiguous, conservative-spent, and authoritative scorer totals |
| Initial RESET, later RESET, or no-op counter semantics differ across authorities | Question-specific precedence and exact mounted/live scorer fixtures |
| Scorecard open or close has an ambiguous transport outcome | Lifecycle journal; no blind second open or close; retry only through an authoritative idempotent recovery path |
| Agent acts after an ambiguous dispatch from stale state | Terminal client quarantine unless an authoritative read-only resynchronization call succeeds |
| Threads are mistaken for concurrent make calls despite Arcade's instance lock | Default serialized-make/streaming-play topology; concurrent make requires a proven lock patch or per-client construction contract |
| Experiment IDs change meaning | Versioned immutable experiment registry |
| Published reproduction is mistaken for causal comparison | Separate published, normalized, and candidate result classes |
| Different models invalidate the E1 factorial | Same model required or no causal registered-bundle claim |
| E1 silently enables the feature later attributed to E3/E5/E6 | Enforced feature matrix, capability-limited prompts/schemas, negative tests, and immutable parent deltas |
| Safe-operation tools are reported as faithful Python reproduction | Preserve original capabilities through a proven control runner or label the control adapted/unavailable |
| R/F gains are attributed only to feature computation | Name the observation-bundle estimand and disclose F's intermediate-frame evidence access |
| Shared-resource games are treated as independent allocation experiments | Separate complete-workload candidate/control runs, counterbalanced run blocks, and dependence-aware uncertainty |
| Repeated comparisons create false discoveries | Hierarchical gatekeeping and frozen multiplicity rules |
| Outer-fold estimate is mistaken for a fixed final candidate | Report selection-procedure and fixed-candidate estimands separately |
| Sparse fifteen-game evidence is overstated | Report attainable resolution and single-game sensitivity; use Provisional primary when power is inadequate |
| Development tuning is called generalization | Label internal selection evidence and keep H1/H2 as guardrails |
| Ambiguous API failure duplicates an action | Write-ahead journal and no post-dispatch automatic retry |
| Reasoning payload exceeds API limit | Validate compact-JSON UTF-8 bytes of the exact server-parsed reasoning field value below 16 KiB with a separate production margin |
| Wrapper serialization changes reasoning bytes or field type | Freeze reasoning_encoding_mode and test logical, intermediate-string, server-field, and full-request representations separately |
| Shared enum state crosses games | Immutable decisions and fresh payloads |
| Crop coordinates reach the API | Typed transform status and display validation |
| Evidence loss is silent | Availability state and claim downgrade |
| Stale or cross-game model context controls an action | Per-game generation/evidence/pre-state binding and safe reconstruction |
| Compaction turns a summary into false truth | Provenance validation; journal remains the evidence authority |
| Disk failure ends a viable game | Preserve T0 and degrade optional evidence |
| Raw hidden data reaches retained or notebook-visible output | Scoped retained-root allowlist, run-unique non-retained scratch root, redirected writable caches, and handled-exit audit |
| Process-kill cleanup is claimed stronger than the process can guarantee | Scope exact retained-root cleanup to normal/handled exits and mark SIGKILL/OOM/platform state outside the guarantee |
| Hidden or live human baseline leaks into policy | Evaluator boundary and scheduler feature audit; public supervision is offline and fold-isolated |
| All-game scoring is confused with model fairness | Cheap bootstrap separated from model-call admission |
| Early comparisons use an unrealistic queue policy | Competition-minimum scheduler and 110-client load envelope precede E1 |
| Scheduler priority combines incompatible units | Express value, uncertainty, and aging as bounded normalized-contribution rates |
| Mean latency is mistaken for a safe inference capacity | Separate C_nominal from headroom-adjusted C_admit using a registered upper-latency or lower-throughput bound |
| Runtime categories are double counted | Global elapsed clock is authoritative |
| Empty or all-advisory predictions vacuously authorize a queue | Require a material required effect predicate for each continuation plus non-removable controller guards |
| Timer or irrelevant animation satisfies a nominally non-vacuous queue prediction | Typed action-dependency bindings, finite relevance rules, complete dependency checks, and blocked-movement fixtures |
| Qualitative labels silently advance hypothesis status | Machine-checkable pre-registration, relevant discrimination or scoped repeated support, evidence, scope, precedence, and threshold rules |
| Mandatory competing hypotheses block repeatedly successful local behavior | Register E6-REPEAT and compare its scoped support route against discrimination-only and one-action controls where budget permits |
| Runtime game identity becomes a memorized policy feature | Permit opaque IDs only in adapter/journal/cache isolation and exclude them from model, scheduler, learned lookup, and static policy content |
| Queues continue on unverifiable predictions | Three-valued required-predicate and controller-guard cancellation |
| False mechanics become long plans | Fixture-validated deterministic verification status and step-scoped short queues |
| Accurate simulator still chooses the wrong goal/action | Separate mechanics, goal, next-action, and closed-loop utility gates |
| Greedy ablation misses component synergy | Prospective multiplicity-controlled interaction checkpoints |
| Workspace escapes or hangs | Demonstrated isolation or safe-operation fallback |
| Full Python is treated as the default workspace | Safe-operation E1C is default; E1C-PY is a separately gated conditional treatment |
| Stale model response controls a new state | Generation and pre-state hash validation |
| Uncancelled generation consumes finalization reserve | Independent watchdog and engine-specific compute-exposure policy |
| Local emulation is mistaken for Kaggle parity | Explicit backend labels and Kaggle authoritative smoke |
| One-person schedule attempts every research idea | Frozen compute budget and scope-shedding order; E2–E9 are failure-driven |
| Daily submissions are spent without decision value | Prospective scored-submission budget and preserved rollback reserve |
| RTX capacity, queueing, or kernel state prevents a run | Prevalidated lower-resource rollback, fresh-kernel artifact, and schedule reserve |
| Rules or hardware change | Dated constraint register and pre-submission revalidation |
| External artifact is accessible but not freely and publicly available | Enforce the exact competition external-data language before packaging |
| License blocks prize eligibility | Artifact-level license record and release audit |

# 14. Next 72 hours

Execute in this order:

1. Initialize Git and audit ignored secrets and generated artifacts.
2. Forensically audit the existing public-game listing path and operator-visible
   metadata. Correct the starting-state claim and freeze a truthful exposure
   classification before further listing or play.
3. Create the dated constraint register with the complete rules, deadline
   conflict, identity, team, sharing, filename, size, license, runtime, hardware,
   submission-limit, freely/publicly-available external-input, score-unit, and
   reset/no-op counter-semantics fields. Correct README.md, .env.example,
   Makefile, and notebook metadata so no operator-facing path retains the stale
   five-per-day limit, retired hostname, unpinned dependency, or unreviewed
   accelerator default.
4. Create and validate E0-required authority, constraint, source, dependency,
   output, adapter, holdout, journal, runtime, experiment, and success schemas;
   create later-treatment registries as explicitly inactive.
5. Freeze the framework adapter, including the raw transport function or pinned
   wrapper patch, its phase reporting, journaled make/constructor-RESET behavior,
   the only call boundary, scorecard-open/close ambiguity policy, and captured
   mounted-client compatibility fixtures for headers, sessions/cookies, identity,
   reasoning encoding, response conversion, and last-response state. Freeze the
   lock-compatible startup topology; default to serialized make with streaming
   play unless a concurrent topology passes its stronger proof. Do not use a
   wrapper that collapses transport failures to None as the ordinary dispatch
   authority.
6. Implement CompetitionAgentLoop and CompetitionOrchestrator, immutable
   ActionDecision, typed action/bootstrap/scorecard journal states, at-most-one
   transport entry, server-parsed reasoning-field and separate full-request byte
   validation, explicit RHAE units, reset/action accounting, and terminal
   quarantine after outcome_unknown.
7. Resolve the retained notebook output root, give it a handled-exit allowlist
   containing only submission.parquet, declare a separate run-unique
   non-retained scratch root, redirect every writable cache/workspace there, and
   prove that logging, recording, traceback locals, and handled cleanup cannot
   bypass the scoped policy.
8. Implement the bounded competition-minimum inference queue, independent
   watchdog, finalization reservation, and synthetic 110-client fault/load test.
9. Remove global RNG, static legal actions, hard-coded game-ID policy, enum
   mutation, off-by-one iteration, the full-inventory-before-play barrier,
   recording, and unbounded frame retention from the production path. Do not
   claim concurrent make merely because serialized Arcade.make calls were
   submitted from multiple threads.
10. Build E0, typed display coordinates, the official/emulated parity runner,
    and validated multi-file offline packaging.
11. Run deterministic E0, journal-fault, output, lifecycle, and 110-client tests.
    Spend a scored Kaggle submission only if an unresolved deployment seam makes
    the result decision-relevant.
12. Run the activation validator and activate Plan 8 only after every corrected
    condition passes and is recorded.
13. Begin minimal T0–T3 retention and R/F representation fixtures.
14. Freeze a small eligible M0 model/engine set and start target-RTX profiling
    before implementing model-dependent policy features.
15. Freeze the current-control cutoff, including a current Qwen3.8 Duck-style
    candidate and the strongest eligible structured-action candidate.

# 15. Definition of done

## 15.1 Implementation-complete gate

Plan 8 is implementation-complete when:

- Its activation record is valid and Plan 8 plus the versioned registries are
  the only normative execution source below external/mounted authorities.
- Every executed experiment passes its parameter-closure and holdout-eligibility
  validators.
- Both reproduction modes pass with declared inputs.
- The dated constraint register has been revalidated for the submission.
- Every external input is freely and publicly available under the current
  competition language and passes the separate artifact/license eligibility
  review.
- Existing inventory exposure is forensically audited and H1/H2 use a truthful
  untouched, reduced-exposure, or ineligible classification.
- Production contains no hard-coded public-game ID literals, solution tables,
  per-ID lookup values, or ID-conditioned policy branches. Runtime game IDs are
  opaque adapter/journal/cache-isolation keys and are absent from model-visible
  context, scheduler features, and learned lookup keys.
- No production path mutates shared GameAction state.
- The pinned adapter owns the only reachable environment-call boundary and an
  unknown mounted framework fails closed.
- For post-make actions, the production adapter owns raw transport entry or a
  tested pinned equivalent; the current exception-collapsing step wrapper is not
  the ordinary dispatch authority.
- The production transport passes exact mounted-client equivalence fixtures for
  headers, sessions, cookies, GUID binding, reasoning encoding, response
  conversion, available actions, and last-response state.
- The currently implicit constructor RESET has a typed bootstrap transaction
  before make with no fabricated pre-state, GUID, legal-action, or observation
  fields; it is acknowledged from the returned initial observation and recorded
  exactly once as a lifecycle command. Its scored action/reset treatment matches
  the mounted fixture, and successful initialization never triggers a duplicate
  reset.
- Scorecard open and close use lifecycle transactions. Ambiguous open cannot
  issue a blind second scorecard, and ambiguous close cannot issue a blind retry
  without a fixture-proven idempotent recovery operation.
- Every action is legal, request-local, bounded, journaled before dispatch, and
  terminally classified.
- Ambiguous environment actions are never automatically retried.
- An unresolved outcome_unknown quarantines and finalizes its client without
  another environment action.
- ACTION6 submits only validated display coordinates from 0 through 63.
- Local and wire reasoning are separated. The logical value, any intermediate
  JSON string, server-parsed reasoning field, and full request pass exact pinned
  serializer fixtures; the compact-JSON UTF-8 encoding of the server-parsed
  field is below the API field limit and the full request obeys its separate
  internal limit.
- Lifecycle counters distinguish acknowledged commands, ambiguous commands,
  bootstrap starts, later level RESETs, conservative locally spent actions,
  authoritative scorer-reported actions/resets, model calls, repairs,
  workspaces, and controller iterations.
- Initial-play RESET, later-level RESET, and visible-no-op scorer fixtures match
  the mounted authority. Ambiguous commands are never labeled as official
  scored actions.
- Competition parity enforces one acknowledged scorecard open, one make, no live
  score, reset semantics, complete inventory accounting, and an acknowledged or
  explicitly finalization_unknown close.
- A 110-client test has no cross-game state or unbounded queue age.
- The startup topology matches the mounted Arcade lock behavior. The default
  serializes make while streaming acknowledged clients into play; any concurrent
  make mode proves its lock, one-scorecard, cookie/authentication, one-make, and
  session-isolation contract. No topology has an avoidable full-inventory startup
  barrier.
- An independent watchdog preserves stop-admission and finalization under hung
  agent/inference workers.
- Global elapsed time, component busy time, queue time, and client time are
  reported distinctly.
- The upstream unbounded Python frame history is replaced.
- T0 state survives recoverable storage failure.
- T1–T3 retention and degradation are explicit and tested.
- Evidence loss downgrades dependent verified claims.
- Hidden Kaggle-style execution emits no prohibited retained artifact or
  notebook-visible output. Writable copies, bytecode, compilation products,
  caches, workspaces, and hidden evidence use the declared non-retained scratch
  root. After normal and tested handled-failure exits, the resolved retained
  output root contains exactly submission.parquet; SIGKILL/OOM/platform-owned
  state is outside the cleanup guarantee and cannot be labeled verified clean.
- Hidden-evaluation and live baseline values remain evaluator-only; any permitted
  public-score supervision is offline, fold-isolated, and separately labeled.
- Official RHAE fixtures match the mounted toolkit and type every value as
  NormalizedRHAE or OfficialRHAEPercent with explicit conversion.
- Published and normalized controls have separate provenance and results.
- Faithful Python controls preserve original execution capabilities through a
  proven runner; safe-operation substitutions are adapted, and unavailable
  controls cannot satisfy a reproduction gate using published scores alone.
- M0 model/engine screening and the competition-minimum scheduler/load envelope
  are frozen before model-dependent E1 comparisons.
- A causal E1 factorial uses one model across all four cells and only claims the
  registered observation-bundle and harness/tool-bundle estimands;
  otherwise no causal factorial claim is made.
- E1 reports the R/F intermediate-frame evidence-access difference and charges
  all workspace-derived computation; it makes no isolated precomputation claim.
- E1 uses the enforced single-action feature manifest. Later memory, retrieval,
  hypothesis, queue, and semantic-controller features are disabled until their
  registered treatments, with negative tests and immutable parent deltas.
- R and F are independently production-valid and policy-isolated.
- Model-visible representation is fully versioned and fixture-tested.
- Context construction, compaction, cache residency, eviction, loss, and
  resumption are registered, bounded, isolated per game, and state-hash safe.
- Statistical decisions use frozen folds, seeds, thresholds, crash handling,
  multiplicity, and rerun rules.
- Shared-resource scheduler and candidate decisions use separate complete-workload
  runs with matched global budgets, counterbalanced order, and paired whole-run
  uncertainty. Per-game diagnostics and synthetic load results are not promoted
  to independent run replicates or hidden-game performance evidence.
- Selection-procedure estimates are not presented as unbiased estimates of a
  final fixed candidate, and low-powered results retain provisional language.
- Exploratory results are not relabeled as accepted without replication.
- The exposure ledger enforces one-shot H1/H2 use and invalidates claims after
  policy-affecting post-holdout changes.
- H1/H2 use their truthful untouched, reduced-exposure, or ineligible
  classification and remain aggregate-only catastrophic-regression guardrails.
- Treatment order and cold/warm/cache state are frozen and counterbalanced or
  blocked as registered.
- Every multi-frame response receives bounded deterministic analysis.
- Rich animation is exposed only through registered triggers.
- Predictions use the typed three-valued evaluator.
- Queue continuations reject empty/all-advisory predicates, require at least one
  material action-relevant effect predicate and complete typed dependency coverage
  per later step, apply non-removable
  controller identity/lifecycle/legal-action/budget guards, and stop after the
  first required mismatch or unknown.
- Hypothesis/dynamics advancement uses pre-registered action-relevant predictions,
  distinct transitions, the registered discrimination or repeated-support gate,
  available evidence, typed scope, and frozen precedence/thresholds. Irrelevant
  visual changes cannot qualify, and qualitative model labels cannot advance
  status. Queue acceptance charges support-building cost and requires comparison
  with the same parent's single-action policy; verification is operational and
  scoped, not proof of general mechanics.
- Controller transitions follow the deterministic precedence table.
- Safe-operation E1C is the default and E1C-PY is unreachable unless the target
  runtime passes the registered adversarial isolation suite.
- Scheduler live features contain no hidden or live baseline; baseline-free and
  permitted public-score-supervised training regimes are separately labeled,
  fold-isolated, and leakage-tested.
- A bounded competition-minimum queue and synthetic 110-client envelope precede
  E1; advanced scheduling remains a separate treatment.
- Runtime profiles distinguish C_nominal from headroom-adjusted C_admit and derive
  hard admission from a registered conservative latency/throughput bound rather
  than a sample mean or best run.
- Cheap all-game bootstrap is distinct from model-service admission.
- E7–E9 enter only through their registered prerequisite and comparison.
- E7/E8 separately gate mechanics fidelity, goal fidelity, next-action utility,
  and closed-loop score; registered interaction checkpoints control bundle
  claims.
- Model/workspace/evidence failures degrade to legal fallback behavior.
- Final candidates have complete hashes, licenses, runtime profiles, output
  audits, rollback artifacts, and reproduction instructions.
- Experiment and scored-submission budgets are frozen, enforced, and retain the
  declared contingency and rollback reserve.
- The competition-like run finishes below 7.65 hours while reserving
  finalization time.
- Required public notebook, source, model information, licenses, and
  reproduction materials are released before the applicable prize deadline.

## 15.2 Competition-performance gate

Implementation completion does not imply competitive success. Before Phase 1
candidate tuning, success_criteria.yaml freezes concrete values and comparison
rules for:

- minimum full-development-set mean RHAE with an explicit normalized-fraction or
  official-percentage unit;
- minimum non-zero game coverage and completed levels;
- required improvement over E0;
- superiority or non-inferiority rule against the strongest frozen eligible
  competitive control;
- catastrophic-tail, invalid-run, and runtime/reliability ceilings;
- H1 veto and frozen H2 candidate rule;
- whole-run candidate comparison rule, complete workload/global-budget manifest,
  paired-run replication, and uncertainty unit for shared-resource execution;
- required valid end-to-end Kaggle competition rerun;
- milestone and final-candidate decision rules.

A candidate is competition-successful only when it passes the frozen internal
performance rule, survives its eligible guardrail, produces a valid all-game
Kaggle submission, and meets the runtime/output/license requirements. Public
leaderboard evidence is labeled adaptive. The private final score is reported
regardless of whether it confirms the public-development decision.

# 16. Decision principles

- Optimize hidden-set generalization and total mean RHAE.
- Preserve live safety state absolutely while making every other evidence
  guarantee explicit and testable.
- Compress access and optional history without pretending omitted evidence is
  exact.
- Treat every environment action as an irreversible transaction unless proven
  otherwise.
- Require predictions before long execution and check them after every action.
- Bind continuation predictions to the next action's observed dependencies and
  measure the cost and benefit of each support gate.
- Keep uncertain interpretation with the model and authority with deterministic
  code.
- Evaluate models and harnesses together for competition selection, but use
  same-model controls for causal harness claims.
- Prefer compact revisable mechanics over long narrative transcripts.
- Verification is routine; executable models and search are conditional.
- Statistical status and operational status are different facts.
- Shared-resource candidate quality is a whole-run outcome; isolated game tests
  and per-game diagnostics answer narrower questions.
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
- Current Qwen3.8 Duck-style Kaggle control candidate:
  https://www.kaggle.com/code/keithtyser/duck-qwen3-8-27b-fp8
- Current hosted-model diagnostic ceiling (not an eligible Kaggle control):
  https://arcprize.org/results/openai-gpt-5-6
- Corrected Kaggle submission-limit notice:
  https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/705405
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
