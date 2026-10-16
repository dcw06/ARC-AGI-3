# RQ2, RQ4 and RQ5: current-agent baseline plan

October 15, 2026 · Draft v1 · Preparation and evaluation design; no execution authorization.

## Objective and scope

Determine whether the current agent can discover and correctly use controls, infer working rules, and complete
the first level of each of six public development games: **ls20, s5i5, cd82, ft09, ka59 and sc25**.
Measure the existing agent before changing its prompts, perception, memory, tools or planning. The primary
acceptance criterion is **engine-confirmed first-level completion in all six games within fixed budgets**.
Diagnostic scores explain failures; they do not substitute for completing a level.

The owner has reviewed the six level-1 worksheet entries. The retained private snapshot contains seven answer
fields per game and 94 annotated regions, including overlapping parent/child regions. It is an owner-reviewed
development reference. Some annotations originated as assistant drafts. It is not an independently validated
answer key, a hidden benchmark or evidence of agent performance. Raw boards, answers and private bindings stay
in the private workspace; public deliverables contain methods and sanitized summaries.

| Question | Operational question | Required output |
| --- | --- | --- |
| RQ2: controls and execution | Can the agent choose a legal, appropriate control, ground it to the intended object when needed, and verify its effect? | Proposed action, execution receipt and evidence-based effect classification |
| RQ4: rule discovery | Can it predict action effects from available evidence, choose informative probes and revise contradicted rules? | A short testable hypothesis, evidence references, prediction and update |
| RQ5: solving strategy | Can it combine perception, controls, rules and goal recognition into a successful bounded episode? | Actual first-level transition and a technically complete retained episode |

Levels 2–3 and cross-layout transfer belong to the later RQ7 study. They are excluded here.

## 1. Responsibilities and interfaces

| Owner | Responsibility | Handoff |
| --- | --- | --- |
| You, approximately 60% | Own RQ2/RQ4/RQ5 design, executable case construction, integration, model/game evaluation and diagnosis | Frozen baseline package and per-game report |
| Mac teammate, approximately 20% | RQ1 object-localization references and scoring | Frame-bound object IDs, roles, masks, parent IDs, ambiguity flags and targeting checks |
| Windows teammate, approximately 20% | RQ3 goal references and RQ6 similarity checks | Goal predicates, incomplete/completed contrasts, similarity/distractor labels and scoring |

You resolve scientific choices. Teammates cross-review labels and scoring before model queries. Their components
can be developed with public/synthetic fixtures; run them against private reference data locally unless broader
sharing is separately chosen. No account credentials, model weights or package contents are required for these handoffs.

## 2. Data preparation and design freeze

| Step | Work | Exit condition |
| --- | --- | --- |
| 2.1 Pin references | Bind the reviewed worksheet export, retained logs, game versions and SDK versions by hash. | Every case has an auditable source reference. |
| 2.2 Review semantics | Check player/target roles, interactive controls versus examples, and level-completion conditions. | Contradictions are resolved or explicitly marked ambiguous. |
| 2.3 Build executable labels | Convert narrative answers into action constraints, effect labels and goal checks. | Labels can be scored without interpreting the model's prose. |
| 2.4 Annotate later frames | Track relevant objects in each selected before/after state. | Moving objects never inherit stale starting-board masks. |
| 2.5 Construct cases | Build the RQ2/RQ4 inventory below and identify unavailable case types. | Case IDs, applicability, expected answers and denominators are fixed. |
| 2.6 Freeze evaluation | Pin agent commit, model/runtime, prompts, schemas, history policy, decoding, graders, budgets and stop rules. | Reviewable package and immutable case/answer manifests exist. |

Specific checks: sc25's moving piece starts on the right and its fixed goal is on the left. In ft09 level 1,
three groups are reference examples and the lower-right group is editable. Retain all nine 36-coordinate cells
within each annotated 324-coordinate group, while preserving their different roles.

Keep three concepts separate: **visible object mask**, **reference/target coordinates**, and **verified interaction
region**. A coordinate inside an object mask can be a correct localization answer without establishing that a
click there selects anything. Verify interaction regions independently where a test claims click success.
Clarify whether a label refers to a parent, child, outline, interior or foreground pattern before scoring it.

Use development cases to debug the harness, then freeze a separate evaluation case list before querying the
model. Separate runs/contexts prevent one case's answer from entering another case's prompt. Prefix-based
prediction cases expose only evidence available before the predicted action. Full teacher solutions, later
observations, engine source and answer keys must be inaccessible to the agent.

These six exposed games and reused trajectories support development diagnosis. Even a frozen case list does
not establish unexposed-game generalization. Repeated frames from one trajectory are correlated observations.

## 3. RQ2: control discovery, grounding and execution

### Case design

Propose **12 scored items per game, 72 total**, with four items in each category below. This is a pilot target;
confirm that the references support it before freezing the final inventory. Retain a case as insufficiently
supported rather than inventing a control or scoring an unavailable action type as a pass.

| Category | Input and task | Expected checks |
| --- | --- | --- |
| Control choice, four items | Observation, legal actions, a task and an explicitly bounded evidence history | Enumerate legal IDs, distinguish observed/unknown effects, choose an appropriate next action or report insufficient evidence |
| Grounding/context, four items | A specified intended object/control and current selection/state | Use a legal action; use the intended frame-bound interaction region for clicks; handle selection, directional or pattern controls as applicable |
| Effect verification, four items | Before observation, acknowledged action and after observation | Identify the affected object and classify the intended effect as shown, not shown or unresolvable from the supplied evidence |

Providing a legal-action list makes enumeration a consistency check. Discovery is measured by choosing controls
and establishing their effects. Click-only games use click controls; directional-only games must not be forced
into a click-targeting task. Case applicability and the final category counts are reported per game.

Include representative failure contrasts where evidence permits:

- A click inside an object versus a nearby-background click or a hole inside its bounding box.
- The right coordinates on a static example rather than an interactive control.
- The same action under different selected objects or modes.
- An already-selected object, where lack of visible change does not establish a selection failure.
- A blocked directional move and a successful move.
- A status-strip change without the intended object effect.
- A missing/uncertain acknowledgement or missing post-observation, requiring an unresolved result.

### Action contract and scoring

Before dispatch record the intended object ID, chosen legal action, coordinates if required, predicted effect
and evidence reference. Then retain the actual request, acknowledgement and resulting observation. Validate
strict coordinate types/ranges and action payloads immediately before dispatch. An invalid proposal counts
against the policy even when a guard prevents it from reaching the engine. Preserve the existing agent's
fallback behavior if it is part of the pinned baseline, and report when it supplies the action.

| Measure | Denominator / interpretation |
| --- | --- |
| Legal proposal rate | All required action proposals, including malformed/invalid ones |
| Target-coordinate hit rate | Applicable click cases with a specified target; score against the correct coordinate set |
| Verified intended-effect rate | Applicable effect cases; acknowledgement alone earns no effect credit |
| Selection/mode correctness | Cases where the current target or mode changes the meaning of an action |
| Effect-classification accuracy | All required effect judgments, including unknown/ambiguous cases |
| Repeated ineffective-action rate | Live repeated state/action pairs without a new supported reason or relevant state change |

A repeat can be useful for lengthening, movement or a genuinely new test. The repetition diagnostic must account
for those cases. Do not classify every repeated action as stagnation.

Report geometry and semantic failures separately. Parent and child masks can overlap; a hit on a parent does
not automatically satisfy a question that specified one child.

## 4. RQ4: rule inference and hypothesis testing

### Case design

Propose **12 scored items per game, 72 total**: four next-effect predictions, four probe choices, two rule-update
judgments and two uncertainty judgments. Freeze the actual supported inventory before evaluation.

| Task | What is supplied | What the agent must produce |
| --- | --- | --- |
| Predict an effect | A bounded action-effect prefix and proposed next action | A prediction before revealing the next outcome: affected object, movement/property/selection change, or justified uncertainty |
| Choose a probe | Two or more plausible hypotheses consistent with the supplied observations | A legal action whose possible outcomes distinguish them, plus the predicted differences; or recognition that no available probe distinguishes them |
| Update a rule | An earlier hypothesis and new agreeing/contradicting evidence | Retain, narrow or reject the hypothesis with specific evidence references |
| Bound a claim | Incomplete evidence, including similar-looking objects with unknown behavior | Distinguish observed effect, a supported working rule and an untested generalization |

Probe items require independently checked alternative outcomes. A single retained successful trajectory may
not contain such contrasts. Prepare them with bounded CPU-only engine checks after the case design is agreed,
or mark the item unsupported. A legal action that merely changes the screen is not necessarily informative.

Keep evidence-reading controls alongside inference cases. Otherwise a prediction error could come from failing
to read the supplied transition rather than failing to infer a rule. Use frame-specific object tracking to
separate target movement from animation, view changes and interface updates.

### Hypothesis record

Use short structured statements; do not require or score an elaborate internal reasoning narrative.

```json
{
  "hypothesis_id": "h1",
  "statement": "A testable relationship between this control and this object",
  "evidence_ids": ["transition_1"],
  "scope": "the observed mode and object",
  "status": "working",
  "next_probe": {"action_id": 6, "action_data": {"x": 0, "y": 0}},
  "predicted_effect": {"type": "unknown", "affected_object_id": null}
}
```

This illustrates a record format; it is not a game action recommendation or final response schema. Freeze the
executable schema separately, and check structured-output support against the pinned serving runtime on CPU.

### Measures

| Measure | Reading |
| --- | --- |
| Next-effect prediction accuracy | Correct discrete outcomes, with movement/size tolerances fixed before evaluation |
| Probe discrimination | Correct identification of which candidate hypotheses a probe can separate |
| Contradiction handling | Correctly narrows or rejects a rule when the new evidence contradicts it |
| Supported-claim rate | Rule claims remain within the evidence actually supplied |
| Uncertainty accuracy and coverage | Correct abstention on underdetermined cases, plus how often definite predictions are made |
| Evidence-reading accuracy | Detects upstream misreading of the transition supplied to the agent |

Allow multiple accepted hypotheses when the evidence does not identify a unique rule. Also test resolvable
cases so that answering unknown on everything cannot perform well. Report every score per game and task type.

## 5. RQ5: actual first-level completion

### Episode design

Run one development episode per game from its pinned initial level-1 state and seed, once the exact package is
reviewed and separately authorized. Use the same six-game list even if a game performed poorly in static
diagnostics. Technical/data failures can prevent execution, and those unstarted episodes remain explicit.

| Proposed pilot limit | Value / rule |
| --- | --- |
| Games and attempts | Six games; one attempt per game; no automatic retry |
| Action budget | At most 96 dispatched inputs per episode, counting explicit resets and ineffective inputs |
| Policy budget | At most 96 decision requests per episode; malformed/no-action responses still count |
| Episode time | At most 300 seconds per episode after its initial observation; overall lifecycle deadline takes precedence |
| Success stop | Stop immediately at the first engine-confirmed level transition |
| Resets | No reset in the primary attempt; a reset ends that attempt and remains recorded |
| External game operations | Local offline engine only; zero online game calls or scorecards |
| Runtime overhead | Startup probes, canaries and HTTP polling have separate bounded counts included in the package's total request ceiling |

These are proposed development budgets, not existing authorizations or a guarantee that the hardware can
finish every permitted request in the allotted time. An action cap and a time cap apply simultaneously. Final
limits and the exact total request ceiling must be frozen after CPU checks and a latency estimate, before
any model episode. Six episodes permit at most 576 policy decisions, with runtime probes counted additionally.

### Decision loop

1. Receive the current observation and legal controls.
2. Identify the relevant current object/target and its role using the existing agent pipeline.
3. Select a task: pursue the goal, test an unresolved rule, or revise a contradicted rule.
4. Record a legal proposed action, intended target and short predicted effect.
5. Validate and dispatch through the bounded existing execution interface.
6. Read the acknowledgement and next observation; verify the relevant effect.
7. Update the evidence history and working hypothesis if that capability already belongs to the baseline.
8. Stop on the first-level transition, a budget limit, technical failure or explicit attempt-ending reset.

This describes the behavior to assess. Do not add a new hypothesis ledger or planner before measuring the
current agent. Preserve and document its existing history, fallback, tool and prompting behavior.

The unassisted baseline receives permitted observations and action-effect history, without the teacher's
solution, reference masks or engine source. If correct masks or control descriptions are supplied as a separate
diagnostic arm, identify it as assisted and give it a separately frozen budget. Unassisted and assisted outcomes
must remain separately reported.

### What counts as success

Start at zero completed levels. Require a retained engine observation with `levels_completed >= 1`, reached
within the frozen limits, plus a technically complete lifecycle. A model saying it solved the game, matching
an image without triggering completion, or receiving a valid action acknowledgement is insufficient.
Whole-game `WIN` is unnecessary when the first-level counter has advanced.

Separate these result fields:

| Field | Meaning |
| --- | --- |
| `engine_level1_reached` | The engine recorded the first-level transition |
| `within_budget` | All action/request/time ceilings were respected |
| `technical_complete` | Required records, cleanup and finalization are verified |
| `baseline_pass` | All three conditions hold |
| `termination_reason` | Success, action cap, request cap, time cap, reset, invalid/uncertain execution or technical failure |

Retain an observed level transition even if cleanup/finalization later fails, but do not award a baseline pass
to that episode. Report requests/actions to completion, ineffective inputs, guard refusals and repeated states.
Missing episodes are not successes and must not disappear from the six-game report.

## 6. Scoring and decisions before improvements

The following are proposed engineering targets for a fully supported 12-item-per-game static inventory. Freeze
or revise them before model queries. If case counts change, freeze explicit integer requirements for the new
denominators; do not change thresholds after seeing results.

An item earns a correct result only when all of its required fields satisfy the frozen checks. Report individual
field scores as additional diagnostics. Keep missing, malformed, refused and technically interrupted responses
visible against the planned inventory; do not improve the apparent score by dropping them from the denominator.

| Component | Proposed target | Interpretation |
| --- | --- | --- |
| RQ2 static diagnosis | At least 11/12 correct per game; also report each metric and applicable denominator | Control/grounding/effect understanding is sufficiently consistent for this development pass |
| Execution guard | Zero invalid payloads dispatched | A harness invariant; separately report invalid proposals that it blocked |
| RQ4 static diagnosis | At least 10/12 correct per game, including both determinate and uncertainty items | Working inference target; individual task failures remain visible |
| RQ5 primary baseline | 6/6 technically complete first-level passes within budget | Meets the owner's six-game development baseline |

RQ2/RQ4 scores are diagnostic engineering targets. They should not cause selective omission of low-scoring
games from the planned RQ5 comparison. A score above threshold does not establish that any particular execution
is safe or correct. Conversely, a static failure can be useful even when a game is solved.

| Observed pattern | Investigation before selecting an improvement |
| --- | --- |
| Wrong target despite a sensible control | Review object identification, role labeling, coordinates and stale masks |
| Right object but wrong control or mode | Review control semantics, selection handling and effect verification |
| RQ2 strong, RQ4 weak | Review evidence reading, probe informativeness and rule updating |
| RQ2/RQ4 strong, RQ5 weak | Review goal predicates, action ordering, budget use and integration of the individual capabilities |
| Baseline strong across all six | Prepare RQ7 transfer cases before claiming general solving ability |

After baseline measurement, a correct-location assisted comparison can diagnose perception failures, while a
correct-control/effect-history comparison can diagnose semantic/inference failures. Change one input/component
at a time, retain the original baseline, and compare at matched budgets. Assistance demonstrates its own effect;
it does not establish unaided capability.

## 7. Evidence and implementation requirements

| Artifact | Required contents |
| --- | --- |
| Case record | ID, game/version, level, RQ/task, frame/source references, allowed inputs, expected structured result, applicability and scoring rule |
| Annotation provenance | Owner/assistant origin, review status, object/interaction masks, ambiguity and amended labels |
| Baseline lock | Agent/model/runtime versions, prompts, tools, schemas, history policy, decoding, budgets, graders and case manifest |
| Per-decision record | Observation, legal controls, proposed/dispatched action, intended object, prediction, evidence IDs, acknowledgement, post-observation and counters |
| Per-episode record | Initial state, full event sequence, engine completion evidence, stop reason, actual counts/time, cleanup and finalization |
| Independent evaluation | Replay-derived totals, contract checks, goal/cap checks, exact input hashes and per-game diagnostic scores |
| Report | All six outcomes, exact denominators, missing/ambiguous cases, failure examples and limits on claims |

CPU checks should exercise mask boundaries/holes, parent-child overlap, unavailable controls, strict payload
types, stale selections, acknowledgement loss, status-only changes, contradictory rule evidence and forged
completion summaries. The evaluator must reject altered/stale inputs and reconstruct totals from events.
Review the exact package built from the latest audited fixes; do not reuse a stale source lock.

Use the already audited process/deadline machinery. The bounded lifecycle includes installation, startup,
policy/game work, evidence writing, temporary-environment removal and cleanup. Late/interrupted finalization
cannot leave an accepted success receipt. CPU fault checks must cover these paths before a GPU package review.

Static evaluation and gameplay may need separate bounded packages. Measure setup and request latency before
assuming both fit in an hour. The owner's existing requirement for an enforced cap on the **entire GPU job**
remains in force; a per-agent deadline does not establish provider-side enforcement during mounting/setup.
Any launch requires its own concrete package review and authorization. This plan makes no submission,
reservation, live game action or compute request, and changes no previous study's attempt history.

## 8. Work order and deliverables

| Order | Deliverable | Planning effort |
| --- | --- | --- |
| 1 | Agree on the schemas, game/agent pins, semantic corrections and proposed pilot limits | 1–2 hours |
| 2 | Teammate object/goal/similarity references; your executable RQ2/RQ4 case inventory | 2–4 hours in parallel |
| 3 | CPU graders, fault checks and baseline runner integration | 2–4 hours |
| 4 | Review concrete static/gameplay packages and their exact budgets | Depends on remaining runtime/provider checks |
| 5 | Separately authorized model evaluation, collection and independent replay | Runtime estimated after setup/latency measurements |
| 6 | Six-game report and evidence-based improvement choice | 1–2 hours |

Allow approximately one to two focused working days for preparation/integration/analysis with parallel teammate
work. This is a planning range, not a compute-time promise. Finish this baseline before advancing to later-level
transfer or presenting improvements as established.
