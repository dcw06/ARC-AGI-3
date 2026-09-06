# ARC-AGI-3 Final Team Project Plan

**Status:** Team execution plan  
**Effective date:** September 5, 2026  
**Milestone 2 deadline:** September 30, 2026 at 11:59 PM UTC  
**Final competition deadline:** November 2, 2026 at 11:59 PM UTC  
**Detailed engineering reference:** `docs/ARC-AGI-3_Project_Plan_8.md`

## 1. Purpose

This document tells the team what to build, who owns each decision, how work is
accepted, and what must be true before a Kaggle submission. It is the operational
version of Project Plan 8.

Project Plan 8 remains the detailed technical specification. This document
supersedes it only for work ordering, ownership, status reporting, and gate
decisions. It does not weaken Plan 8's safety, evaluation, or reproducibility
requirements.

When sources disagree, use this order:

1. Current Kaggle competition rules for eligibility, licensing, publication,
   and compliance.
2. The live Kaggle competition backend and generated submission for actual
   lifecycle and scoring behavior.
3. The official scorer and exact mounted client for scoring and serialization.
4. The dated constraint registry in this repository.
5. This team plan.
6. Project Plan 8 for detailed implementation requirements.
7. Code comments and historical plans.

A conflict with a higher authority is recorded and resolved before the affected
submission or claim proceeds.

## 2. Mission and success conditions

### 2.1 Mission

Build an offline Kaggle notebook agent that safely plays all 110 hidden
ARC-AGI-3 games, uses the available RTX-class runtime effectively, and maximizes
mean Relative Human Action Efficiency (RHAE) without relying on game-specific
hidden information.

### 2.2 Milestone 2 success

By September 30, the team must have:

- a public, reproducible Kaggle notebook that qualifies under the milestone
  rules;
- a valid competition rerun covering the complete 110-game inventory;
- a model, tokenizer, engine, dependencies, source, prompts, and configuration
  identified by immutable versions or hashes;
- no known invalid-action, cross-game-state, duplicate-dispatch, or lifecycle
  violation in the certified candidate;
- a measured end-to-end runtime below the 7.65-hour operational target, leaving
  finalization reserve inside the 9-hour hard limit;
- a candidate that passes the frozen internal performance rule against the
  strongest reproduced eligible control;
- a known-valid fallback submission artifact;
- a dated record of milestone publication and license compliance.

The Evaluation Owner must freeze the numerical performance thresholds in
`config/success_criteria.yaml` before candidate comparisons begin. Until then,
no result may be labeled accepted.

### 2.3 Final competition success

By November 2, the team must have:

- up to two frozen, valid final candidates selected under a predeclared rule;
- a complete private-score-oriented selection rationale;
- a clean reproduction and license package;
- compliance with the winner obligations applicable to source, system, model,
  weights or parameters, environment, and inference documentation.

Milestone-publication requirements and final-winner obligations are tracked as
separate legal/compliance entries. They must not be treated as identical without
an authoritative source or organizer clarification.

## 3. Team ownership

Assign one named person to every role. One person may hold multiple roles, but
every deliverable has exactly one accountable owner.

| Role | Accountable for | Assigned person |
|---|---|---|
| Project Lead | Priorities, decisions, blockers, gate approval, team coordination | TBD |
| Platform Owner | Framework adapter, lifecycle, journals, packaging, watchdog, output | TBD |
| Model Owner | Model selection, inference engine, quantization, prompts, context | TBD |
| Agent Owner | Evidence, representations, policy, memory, predictions, controller | TBD |
| Evaluation Owner | Partitions, controls, experiments, statistics, reports | TBD |
| Release Owner | Kaggle account, metadata, submissions, licensing, publication, rollback | TBD |

### 3.1 Decision rights

- The Project Lead decides priority and stops work that cannot pass its gate.
- The Platform Owner can block a submission for lifecycle, output, or runtime
  integrity failures.
- The Evaluation Owner can reject a performance claim that was not prospectively
  registered or used an invalid comparison.
- The Release Owner can block a submission for an unresolved rule, license,
  account, artifact, or publication issue.
- The Model and Agent Owners decide implementation details inside frozen
  interfaces and budgets.
- Changes after candidate freeze require Project Lead, Evaluation Owner, and
  Release Owner approval and create a new candidate hash.

## 4. Confirmed competition contract

The Release Owner maintains `config/competition_constraints.yaml`, including a
source URL, verification timestamp, verifier, authority type, and next
revalidation event for every item.

Initial September 5 values:

| Constraint | Working value |
|---|---|
| Submission mechanism | Kaggle notebook only |
| CPU/GPU runtime limit | 9 hours |
| Operational runtime target | 7.65 hours |
| Internet during submission | Disabled |
| Hidden evaluation inventory | 110 games |
| Public/private split | 55 games / 55 games |
| Competition mode | Forced |
| Scorecards | One |
| Environment creation | At most one `make` per environment |
| In-flight score access | Unavailable |
| Reset behavior | Competition RESET is a level reset; initial-start accounting must match the mounted scorer fixture |
| Daily scored submissions | One; revalidate in the account before use |
| Final selections | Up to two |
| Required submission file | `submission.parquet` |
| Submission-size limit | 20,480 MB; revalidate before packaging |
| Maximum team size | 8 |
| Identity verification | Required |
| Current machine class | `g4-standard-48`; profile the actual mounted accelerator |
| Milestone 2 | September 30, 2026 at 11:59 PM UTC |
| Operational entry cutoff | October 26, 2026 at 11:59 AM UTC until the backend/timeline discrepancy is resolved |
| Team-merger deadline | October 26, 2026 at 11:59 PM UTC; revalidate |
| Final deadline | November 2, 2026 at 11:59 PM UTC |
| Competition-data license | Apache 2.0 |
| Winner license currently stated | CC BY 4.0 plus the competition's open-system/model/weights obligations; obtain artifact-level review |

### 4.1 External data and tools

Do not reduce the rule to a single phrase. Record separately:

1. The notebook Code Requirements permit freely and publicly available external
   data, including pretrained models.
2. The competition rules also describe a Reasonableness path for external data,
   models, or tools that are reasonably accessible at minimal cost.
3. Runtime artifacts must be attachable and usable with internet disabled.
4. Every artifact must have recorded provenance and a license decision.
5. Any artifact relying on the Reasonableness path requires Release Owner review
   and, when material, written organizer clarification before candidate freeze.

The team's default is to use free and public artifacts. This is an internal
conservative policy, not a claim that the Reasonableness rule does not exist.

Primary sources:

- Competition: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3
- Rules: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules
- Scoring: https://docs.arcprize.org/methodology
- Competition mode: https://docs.arcprize.org/toolkit/competition_mode

## 5. Scoring objective

Use explicit score units everywhere. Bare numeric fields named `score` or `RHAE`
are invalid.

```text
NormalizedRHAE level score
    = min(1.15, (human_baseline_actions / agent_actions)^2)

OfficialRHAEPercent level score
    = 100 * NormalizedRHAE level score
```

An uncompleted level contributes zero. Game scores use the official level-index
weights and are capped by the weighted completed-level fraction. The competition
score is the mean over the applicable game split.

The scorer or backend supplies official action counts. Local conservative action
counts protect budgets but never replace official counts in reported RHAE.

## 6. System design

### 6.1 Authority boundary

Deterministic code owns:

- legal actions and action serialization;
- coordinate validation;
- evidence availability and state hashes;
- transaction journals and exact local counters;
- model-output validation;
- controller mode, budgets, deadlines, and scheduler admission;
- lifecycle, output, reporting, and cleanup policy.

The model may propose:

- goals and subgoals;
- mechanics and competing hypotheses;
- evidence requests and probes;
- one action or a short prediction-checked queue;
- memory changes;
- bounded analysis operations in an enabled workspace treatment.

The model never calls the environment, sets its own budget, bypasses validation,
declares a hypothesis verified, or accesses evaluator-only baselines.

### 6.2 Production flow

```text
Validate complete game-ID inventory
  -> journal and open one scorecard
  -> serialize each make/bootstrap operation
  -> admit each acknowledged client to play immediately
  -> build bounded evidence and per-game context
  -> request one model proposal
  -> validate proposal, legal action, coordinates, budget, and state binding
  -> commit prepared action journal entry
  -> enter transport at most once
  -> acknowledge response or quarantine outcome_unknown
  -> repeat under controller and deadline rules
  -> terminate all clients
  -> journal scorecard close
  -> verify current-run-bound submission confirmation
  -> audit retained output
```

The complete game-ID manifest is frozen before the first `make`. Environment
creation remains serialized where required by the mounted `Arcade.make` lock,
but play may start as soon as an individual client is acknowledged. There is no
requirement to construct every environment before starting play.

### 6.3 Framework adapter

The Platform Owner implements a versioned `CompetitionAgentLoop` and
`CompetitionOrchestrator`. The production path must not use the upstream agent
loop as lifecycle authority because that loop retains unbounded frames, owns
dispatch, and uses mutable action payload state.

Before E0 certification, choose and record exactly one adapter strategy:

- raw pinned transport owned by the adapter;
- pinned patch exposing transport phase from the official wrapper; or
- another versioned implementation that passes the same compatibility fixtures.

The strategy must preserve and test URL construction, authentication, session and
cookie behavior, scorecard/game/GUID binding, reasoning serialization, response
validation, available actions, frame order, last-response state, timeouts,
redirect behavior, and retry behavior.

### 6.4 Transaction rules

Every make/bootstrap, environment action, scorecard open, and scorecard close is
journaled before transport.

Ordinary action states are:

```text
prepared -> failed_pre_dispatch
prepared -> dispatched -> acknowledged
prepared -> dispatched -> outcome_unknown
```

Rules:

- Release a reserved action only after a proven pre-transport failure.
- Enter the selected transport function at most once per decision.
- Never retry automatically after transport entry or uncertainty.
- Treat timeout, connection loss, malformed response, or post-entry cancellation
  as `outcome_unknown` unless authoritative evidence proves otherwise.
- Quarantine a client after unresolved `outcome_unknown`.
- RESET is an environment action, not a recovery read.
- Do not label local ambiguity bounds as official scorer counts.

The initial constructor RESET is represented by a bootstrap transaction prepared
before `make`. It contains no fabricated pre-state, GUID, legal actions, or
observation. A successful returned observation acknowledges and completes the
bootstrap exactly once.

A close becomes acknowledged only after either:

- a valid authoritative close response; or
- a documented and fixture-proven confirmation that is uniquely bound to the
  current run and scorecard.

The existence of a `submission.parquet` file by itself is not sufficient proof
of close acknowledgement. Otherwise use `finalization_unknown`.

### 6.5 Action contract

`ActionDecision` is immutable and request-local. It contains:

- action ID;
- action data;
- minimal wire reasoning;
- local rationale reference;
- prediction and stop predicates;
- evidence references;
- decision, generation, and pre-state identity.

Before dispatch:

1. Re-read the current legal-action set.
2. Validate the proposed action.
3. Validate ACTION6 display coordinates as integer `x` and `y` values from 0
   through 63.
4. Build a fresh payload without mutating `GameAction`.
5. Validate the exact server-parsed reasoning representation below the mounted
   16 KiB limit and the complete request below the internal body limit.
6. Commit the prepared journal record.

### 6.6 Evidence and context

Evidence tiers:

- T0: current authoritative observation, legal actions, lifecycle, counters,
  hashes, and pending journal state. T0 must remain in bounded memory.
- T1: recent raw observations needed for reconstruction.
- T2: deterministic deltas, regions, motion, and animation summaries.
- T3: optional rich history, model traces, or workspace products.

Storage degradation removes T3, then T2, then unnecessary T1. It never removes
T0 or silently leaves a claim verified after its evidence disappears.

Every game has its own context/session/cache identity. A resumed response can
control an action only when its game key, generation, evidence frontier, and
pre-state hash match. No prompt, cache, generated state, or memory crosses games.

### 6.7 Inference and scheduling

The shared inference service provides one initialized model service, bounded
queues, per-game isolation, cancellation or stale-result rejection, deadlines,
and deterministic fallback.

Measure nominal and safe admission capacity separately:

```text
C_nominal = floor(model_service_budget / weighted_mean_latency)
C_admit   = floor(effective_service_budget / conservative_latency_guard)
```

For batching or multiple workers, use a conservative lower bound on sustained
throughput under the actual mixed workload.

The minimum scheduler is deterministic and fair. It must exist before advanced
score-aware scheduling. Every environment receives cheap bootstrap, but model
calls may be allocated unequally using policy-visible information.

For an advanced scheduler:

- probabilities and efficiency proxies are dimensionless;
- `expected_value` is measured in normalized game contribution;
- `priority_rate` and bonus rates are measured in normalized contribution per
  second;
- the efficiency proxy is explicitly bounded and calibrated;
- future-option value is probability-weighted expected incremental contribution,
  not raw remaining potential;
- no hidden/live baseline or game-ID lookup reaches runtime features.

## 7. Policies and treatments

### 7.1 Required controls

| ID | Purpose |
|---|---|
| E0 | Legal deterministic fallback and lifecycle validation |
| E0W-S-PUB | Reproduction of an eligible published structured-action system |
| E0W-C-PUB | Reproduction of an eligible published workspace system |
| E0W-S-NORM | Same-model normalized structured control, when valid |
| E0W-C-NORM | Same-model normalized workspace control, when valid |

The current Duck/Qwen Kaggle notebook is a control candidate, not an assumed
successful reproduction. Its exact notebook, source bundle, model, engine,
configuration, and observed result must be frozen. A failed or partial
reproduction remains labeled failed or partial.

Hosted systems that cannot run under Kaggle's offline rules are diagnostic
references only. GPT-5.6 is an earlier hosted diagnostic; the September 3 Astra
evaluation is the current hosted capability ceiling referenced by this plan.

### 7.2 Primary E1 comparison

When one model supports every cell, compare:

| Cell | Harness | Observation |
|---|---|---|
| E1S-R | Structured action | Raw minimal observation |
| E1S-F | Structured action | Precomputed deterministic features |
| E1C-R | Bounded workspace | Raw minimal observation |
| E1C-F | Bounded workspace | Precomputed deterministic features |

All four cells must share model, weights, engine, quantization, decoding,
preprocessing, queue policy, games, seeds, and resource ceilings.

Call this a controlled factorial comparison by default. Use causal language only
when the experiment registry additionally freezes and validates:

- the unit and mechanism of treatment assignment;
- randomized or valid counterbalanced order;
- cache/session reset and carryover controls;
- no cross-cell interference through shared inference state or queues;
- common-randomness handling;
- the exact estimand and its assumptions.

If these conditions fail, report a bundle comparison, not a causal factor effect.

### 7.3 Conditional improvements

Advanced treatments enter only after a recorded failure and prospective test:

| Treatment | Trigger |
|---|---|
| E1M | Context loss, reconstruction cost, or stale memory |
| E2 | Missing visual change, motion, animation, or correspondence evidence |
| E3 | Cross-level forgetting or memory contamination |
| E4 | Retrieval or retrodiction failure |
| E5 | Hypothesis collapse or poor discriminating probes |
| E6 | Replanning overhead that a short verified queue may reduce |
| E7 | Long-horizon mechanics inconsistency requiring executable state |
| E8 | Verified model exists but action selection needs search |
| E9 | Repeated specialist-solvable failure with sufficient budget |

Every treatment must declare its control, primary outcome, budget, stop rule,
failure rule, and interaction family before results are viewed.

## 8. Evaluation protocol

### 8.1 Public-game handling

The Evaluation Owner must first audit what public IDs, titles, frames, source,
replays, or gameplay have already been exposed.

Then:

1. Freeze the 25-game public inventory and exposure ledger.
2. Put every semantically exposed game in development.
3. Create up to five H1 architecture guardrails and five H2 candidate guardrails
   only from eligible remaining games.
4. Label title-exposed sets as reduced-exposure procedural guardrails.
5. Reduce or eliminate H1/H2 rather than falsely claim untouched status.

H1/H2 are aggregate catastrophic-regression guardrails. They do not establish a
positive generalization claim. If the same implementer controls and can inspect
the runner, call the process redacted, not blinded or sealed.

### 8.2 Unit and estimand

The game is the unit of generalization. Repeated seeds reduce within-game noise;
they do not increase the number of games.

Seed aggregation must match deployment:

- For a fixed deterministic production seed, evaluate that exact seed.
- For a stochastic one-run deployment, use the arithmetic mean of independent
  repetitions as the primary estimate of expected deployment score.
- Report the median only as a secondary robustness statistic.
- Never select the best seed or best rerun.

The primary outcome is full-set mean RHAE in an explicit unit. Untouched, failed,
timed-out, or crashed games count as zero unless the run satisfies a predeclared
invalid-run rule.

### 8.3 Statistical validity

Before an experiment begins, freeze games, folds, seeds, estimator, practical
effect threshold, uncertainty method, crash handling, multiplicity family,
resource budget, and decision rule.

Do not call a sign-flip or permutation result exact merely because all
permutations were enumerated. The protocol must state:

- the randomization mechanism or exchangeability/symmetry assumption;
- treatment-order randomization and carryover controls;
- treatment of zero differences and ties;
- the domain of inference.

Without a defensible randomization or exchangeability basis, report the result as
a descriptive paired sensitivity analysis. Public-development inference is not
an untouched hidden-game generalization claim.

Report statistical and operational status separately:

- Statistical: Accepted, Rejected, or Inconclusive.
- Operational: Primary, Provisional primary, Competitive-control primary, E0
  fallback, or Disabled.

## 9. Workstreams and deliverables

### WS0 — Governance and reproducibility

**Owner:** Project Lead  
**Supporting roles:** Evaluation Owner, Release Owner

Deliverables:

- initialize Git and protect secrets;
- create the constraint, experiment, statistics, control, model, source,
  dependency, runtime, output, adapter, context, representation, holdout,
  success, prediction, action-journal, lifecycle-journal, and sealed-output
  registries or schemas;
- pin framework, Python, packages, native libraries, model, tokenizer,
  quantization, prompts, and notebook builder;
- define local-bootstrap and Kaggle-offline reproduction commands;
- maintain the decision log and supersession history.

Done when:

- schemas validate;
- required parameters for the next experiment are concrete;
- secrets and generated outputs are ignored;
- a clean checkout can reconstruct the declared local environment.

### WS1 — Competition execution and safety

**Owner:** Platform Owner

Deliverables:

- `CompetitionAgentLoop` and `CompetitionOrchestrator`;
- version-pinned framework adapter and compatibility fixtures;
- immutable actions and fresh request payloads;
- bootstrap, action, open, and close journals;
- bounded evidence storage and disabled upstream recording;
- lock-compatible serialized-make/streaming-play topology;
- independent watchdog and finalization path;
- competition-like local runner and 110-client synthetic fault/load test;
- notebook output and scratch routing.

Done when:

- no environment call bypasses the adapter;
- no ambiguous action is retried;
- no payload or context crosses clients;
- one scorecard and at-most-one make per environment are enforced;
- the runner handles all 110 clients with bounded queue age and memory;
- handled exits preserve the required submission and expose no prohibited hidden
  evidence.

### WS2 — Model and inference

**Owner:** Model Owner

Deliverables:

- exact eligible model and fallback model manifests;
- tokenizer, quantization, engine, wheel, and native-library bundles;
- target-machine cold-load, first-token, throughput, latency, cancellation,
  VRAM, RAM, and disk profiles;
- shared inference service with bounded requests and per-game isolation;
- frozen prompts, decoding configuration, context policy, and fallback behavior;
- published-control reproduction package.

Done when:

- the primary and fallback models load with internet disabled;
- their licenses and public provenance are accepted;
- safe admission capacity is measured rather than inferred from a best run;
- the selected model fits the full-run runtime and memory envelope;
- the control result is reproducible or truthfully labeled partial/failed.

### WS3 — Agent intelligence

**Owner:** Agent Owner

Deliverables:

- E0 deterministic legal fallback;
- raw and deterministic-feature observation paths;
- bounded frame/delta/animation evidence;
- structured policy and bounded-workspace policy;
- per-game context, memory, prediction, and hypothesis schemas;
- deterministic controller and short prediction-checked queues;
- failure-triggered advanced treatments.

Done when:

- every proposed action is legal and state-bound;
- ACTION6 coordinates are correct in display space;
- model failure degrades to E0;
- evidence loss downgrades dependent claims;
- stale responses and unverifiable queue continuations cannot act;
- enabled features have passed their registered comparison.

### WS4 — Evaluation and selection

**Owner:** Evaluation Owner

Deliverables:

- exposure audit and partition ledger;
- frozen controls and experiment registry;
- corrected statistical protocol;
- paired game-level evaluation reports;
- runtime/reliability/performance decision table;
- H1/H2 aggregate guardrail decisions where eligible;
- candidate selection and tie-break record.

Done when:

- every result references immutable code/configuration/model hashes;
- score units are explicit;
- seed aggregation matches deployment;
- causal language is used only when assignment and interference assumptions pass;
- adaptive public leaderboard evidence is labeled adaptive;
- candidate decisions follow frozen thresholds.

### WS5 — Kaggle release and compliance

**Owner:** Release Owner

Deliverables:

- accepted rules, identity verification, and team/account readiness;
- valid kernel ID and metadata;
- attached public model, tokenizer, wheel, source, and dependency artifacts;
- internet-disabled notebook configuration;
- submission budget and run ledger;
- milestone publication package;
- final winner-obligation and license checklist;
- frozen candidate and rollback artifacts.

Done when:

- the exact candidate reproduces from a clean Kaggle run;
- all mounts and hashes match the manifest;
- the notebook generates the required current-run submission;
- publication and license conditions are documented separately for the milestone
  and final winner case;
- rollback can be submitted without rebuilding unverified artifacts.

## 10. Delivery gates and dates

Workstreams may proceed in parallel, but no gate is passed by calendar date alone.

### G0 — Authority and repository baseline

**Target:** September 7  
**Owners:** Project Lead and Release Owner

- Team roster assigned.
- Git and secret protections active.
- Competition constraints revalidated.
- Kernel/account/team/identity status recorded.
- Public-game exposure audit complete.
- Core registries validate.
- Model and control candidates identified with provenance.

### G1 — Safe E0 execution

**Target:** September 10  
**Owner:** Platform Owner

- Adapter strategy frozen.
- E0 uses current legal actions and immutable payloads.
- Bootstrap and lifecycle journals work.
- Ambiguous outcomes quarantine without retry.
- Competition-like runner and notebook packaging execute end to end.
- Deterministic and fault-injection tests pass.

### G2 — Model/control viability

**Target:** September 13  
**Owners:** Model Owner and Evaluation Owner

- Primary and fallback models load offline.
- Target-hardware profile recorded.
- Published control reproduction classified.
- Minimum inference queue and fallback work.
- Success thresholds and experiment comparisons frozen.

### G3 — Primary E1 decision

**Target:** September 18  
**Owners:** Agent Owner and Evaluation Owner

- Required E1 cells run under matched configuration.
- Context and representation behavior are versioned.
- Statistical assumptions and seed estimand are valid.
- One operational primary and one fallback are selected.
- No unsupported causal or generalization claim is made.

### G4 — Failure-driven improvement decision

**Target:** September 22  
**Owners:** Project Lead and Agent Owner

- Failure analysis identifies which, if any, E2-E6 treatment is justified.
- Every admitted treatment has a registered comparison and stop rule.
- Non-improving or unreliable treatments are disabled.
- Candidate configuration is functionally complete.

### G5 — Full-load certification

**Target:** September 25  
**Owners:** Platform Owner and Model Owner

- Full 110-client load and fault tests pass.
- Runtime is below 7.65 hours with finalization reserve.
- C_nominal and C_admit are separately measured.
- Memory, storage, queue age, cancellation, and degradation pass.
- Candidate and rollback notebooks run offline with exact mounts.

### G6 — Candidate freeze

**Deadline:** September 26  
**Owners:** Project Lead, Evaluation Owner, Release Owner

- Candidate code, prompts, model, engine, configuration, manifests, and notebook
  are hashed and immutable.
- H2 candidate guardrail is applied once if eligible.
- Submission and tie-break decisions are recorded.
- Any later functional change creates a new candidate and requires recertification.

### G7 — Milestone release

**Window:** September 27–30  
**Owner:** Release Owner

- Clean Kaggle reproduction completed.
- Constraint register and account allowance revalidated.
- Public notebook and required open-source materials published under the verified
  milestone interpretation.
- Planned scored submission made before September 30 at 11:59 PM UTC.
- Result, hashes, runtime, output audit, and known limitations archived.

### G8 — Final competition

**Window:** October 1–November 2  
**Owner:** Project Lead

- Continue only registered post-milestone treatments.
- Revalidate entry and team status before the conservative October 26 cutoff.
- Freeze final candidates with enough time for clean reruns.
- Select up to two final submissions using the predeclared expected-private-score
  and behavioral-diversity rule.

## 11. Immediate assignments: September 5–7

| Priority | Task | Accountable role | Required output |
|---:|---|---|---|
| 1 | Assign named owners and open the decision log | Project Lead | Completed roster and daily cadence |
| 2 | Initialize Git; audit `.env`, `.kaggle`, generated notebooks, payloads, and recordings | Project Lead | Clean ignore/secret report |
| 3 | Revalidate rules, dates, allowance, identity, team, external-data language, and publication duties | Release Owner | `competition_constraints.yaml` |
| 4 | Fix kernel ID, accelerator metadata, mounts, internet flag, and package manifest | Release Owner | Valid kernel metadata draft |
| 5 | Freeze adapter strategy and map every upstream lifecycle/transport seam | Platform Owner | Adapter manifest and call graph |
| 6 | Implement immutable action decisions and E0 legal fallback | Platform Owner | Passing action/coordinate tests |
| 7 | Implement bootstrap/action/open/close journal state machines | Platform Owner | Passing transaction tests |
| 8 | Freeze primary and fallback model candidates and inspect public provenance/licenses | Model Owner | Model manifest |
| 9 | Start offline model-load and target-machine profiling path | Model Owner | Initial runtime profile |
| 10 | Audit public-game exposure and freeze development/guardrail eligibility | Evaluation Owner | Holdout/exposure ledger |
| 11 | Freeze score units, seed estimand, E1 comparison, thresholds, and test assumptions | Evaluation Owner | Statistics and success configs |
| 12 | Implement T0 evidence, bounded frame retention, and per-game isolation | Agent Owner | Evidence/context tests |

The Project Lead reviews blockers at the end of each day. A blocked task must name
the missing evidence, responsible owner, next action, and decision deadline.

## 12. Scored-submission policy

The Release Owner creates a dated submission ledger before the first scored run.
Each proposed submission must state the decision it can change.

Submission categories:

1. Deployment/lifecycle validation.
2. Reproduced-control calibration.
3. Primary candidate comparison.
4. Candidate confirmation.
5. Frozen milestone or final candidate.
6. Rollback reserve.

Rules:

- Never submit an unregistered code/configuration/model combination.
- Never repeat a successful scored run without a decision it can change.
- Treat public leaderboard results as adaptive evidence.
- Preserve at least one known-valid rollback candidate.
- Revalidate the live daily allowance before every planned submission.
- Archive kernel, source, model, configuration, and output hashes for every run.

## 13. Test and certification checklist

### 13.1 Unit tests

- Stable per-game seeds across processes.
- Legal-action normalization.
- No production `GameAction.set_data()`.
- ACTION6 coordinate and transform validation.
- Exact reasoning-field and request serialization limits.
- Immutable request-local payloads.
- Action and lifecycle journal transitions.
- No retry after ambiguous dispatch.
- Bootstrap RESET recorded once without fabricated state.
- Initial and later RESET counter fixtures.
- Score parity in NormalizedRHAE and OfficialRHAEPercent.
- Bounded evidence and T0 preservation.
- Context/session/cache isolation.
- Stale inference rejection.
- Prediction MATCH/MISMATCH/UNKNOWN behavior.
- Controller precedence and queue cancellation.
- Scheduler unit, bound, and capacity checks.
- Statistical estimator and randomization-assumption validation.
- External-artifact provenance and license validation.

### 13.2 Integration tests

- One acknowledged scorecard open and safe ambiguous-open behavior.
- At most one make for each inventory entry.
- Mounted-client transport equivalence.
- Serialized make with streaming play.
- All environment calls cross the journaled adapter seam.
- No in-flight score request.
- Ambiguous action quarantines its client.
- All clients terminate before close.
- Close acknowledgement requires authoritative current-run evidence.
- Model timeout, malformed output, cancellation, and fallback.
- Exactly one model-service initialization.
- 110-client bounded queue and fault test.
- Global deadline stops admission and preserves finalization.
- Clean local bootstrap and clean Kaggle offline reproduction.
- Hidden production output contains no prohibited game evidence.
- Submission ledger rejects unregistered or exhausted runs.

### 13.3 Candidate certification

A candidate is certifiable only when:

- code, model, artifacts, prompts, and configuration are frozen;
- required unit and integration tests pass;
- the complete 110-client workload fits the measured runtime envelope;
- no known lifecycle or cross-game isolation defect remains;
- internal score/reliability rules pass;
- license and publication reviews pass;
- a valid rollback exists.

## 14. Reporting

Every experiment report contains:

- experiment and treatment IDs;
- code, configuration, model, source, dependency, representation, context, and
  adapter hashes;
- backend and hardware;
- game manifest, exposure status, seeds, order, and cache state;
- explicit score units and per-game paired results;
- estimator, assumptions, uncertainty, multiplicity, and decision rule;
- invalid actions, no-change, reset, death, timeout, crash, and ambiguity rates;
- latency, tokens, calls, VRAM, RAM, disk, and global runtime;
- statistical status and operational status;
- decision, owner, timestamp, and next action.

Every candidate report additionally contains:

- primary and fallback model/license records;
- startup topology and adapter compatibility result;
- lifecycle and close-confirmation status;
- C_nominal, C_admit, and finalization reserve;
- full-load certification;
- Kaggle submission/output result;
- known limitations and rollback instructions.

## 15. Team operating cadence

### Daily

- Fifteen-minute status review: completed, next, blocker, decision needed.
- Update the task board and decision log.
- Reconcile code/configuration changes with manifests.
- Review experiment and accelerator-budget consumption.
- Release Owner checks whether any rule/platform observation changed.

### Before every experiment

- Freeze treatment and control hashes.
- Validate all required parameters.
- Confirm game/holdout eligibility.
- Confirm seed estimator and statistical assumptions.
- Confirm compute and run budget.

### Before every Kaggle submission

- Revalidate competition constraints and daily allowance.
- Verify exact kernel, model, dataset, and dependency sources.
- Confirm internet is disabled and target accelerator is selected.
- Run clean offline packaging and output audit.
- Record the decision the submission can change.
- Confirm rollback remains available.

### After every Kaggle submission

- Record public score as adaptive evidence.
- Archive hashes, runtime, status, and platform observations.
- Decide once: accept, reject, investigate, or leave inconclusive.
- Do not modify the frozen candidate in place.

## 16. Final definition of done

The project is done for a given deadline only when:

1. The submitted notebook is valid and covers the complete hidden inventory.
2. Lifecycle, action, context, and output invariants pass.
3. The model and all artifacts are reproducible offline and license-reviewed.
4. Runtime remains below the operational target with finalization reserve.
5. Performance passes the frozen candidate rule against the applicable control.
6. Statistical claims match their actual assumptions and evidence.
7. Milestone and winner obligations are separately verified and satisfied when
   applicable.
8. Candidate and rollback hashes, reports, and reproduction instructions are
   archived.

Implementation completion, competitive performance, and prize eligibility are
three separate decisions. None implies either of the others.

## 17. Technical references

- Detailed project specification: `docs/ARC-AGI-3_Project_Plan_8.md`
- Kaggle competition:
  https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3
- Kaggle rules:
  https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules
- Scoring methodology:
  https://docs.arcprize.org/methodology
- Competition mode:
  https://docs.arcprize.org/toolkit/competition_mode
- Official toolkit:
  https://github.com/arcprize/ARC-AGI
- Official agent framework:
  https://github.com/arcprize/ARC-AGI-3-Agents
- Current Duck/Qwen control candidate:
  https://www.kaggle.com/code/keithtyser/duck-qwen3-8-27b-fp8
- Earlier GPT-5.6 diagnostic:
  https://arcprize.org/results/openai-gpt-5-6
- Current Astra diagnostic ceiling:
  https://arcprize.org/blog/astra

