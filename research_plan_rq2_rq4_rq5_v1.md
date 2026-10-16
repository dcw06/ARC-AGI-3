# RQ2, RQ4 and RQ5: current-agent baseline plan

October 15, 2026 · Draft v2 · Preparation and evaluation design; no execution authorization.

## Objective and scope

Determine whether the current agent can discover and correctly use controls, infer working rules, and complete
the first level of each of six public development games: **ls20, s5i5, cd82, ft09, ka59 and sc25**.
Measure the existing agent before changing its prompts, perception, memory, tools or planning. The primary
acceptance criterion is **engine-confirmed first-level completion in all six games within fixed budgets**.
Diagnostic scores help investigate failures; they do not uniquely identify their causes or substitute for
completing a level. Completion establishes success in the observed attempt, not a particular internal strategy.

The owner has reviewed the six level-1 worksheet entries. The retained private snapshot contains seven answer
fields per game and 94 annotated regions, including overlapping parent/child regions. It is an owner-reviewed
development reference. Some annotations originated as assistant drafts. It is not an independently validated
answer key, a hidden benchmark or evidence of agent performance. Raw boards, answers and private bindings stay
in the private workspace; public deliverables contain methods and sanitized summaries.

| Question | Operational question | Required output |
| --- | --- | --- |
| RQ2: controls and execution | Can the agent choose an appropriate control, execute the proposal faithfully and recognize the resulting effect? | Separate proposal, dispatch and effect-recognition results; supplied-target tests are component diagnostics |
| RQ4: rule discovery | Can it interpret evidence, reason about supplied possibilities, discover useful relationships during play and use them? | Separate conditional-inference scores, naturally occurring discovery evidence and subsequent behavioral consistency |
| RQ5: solving strategy | Can it combine perception, controls, rules and goal recognition into a successful bounded episode? | Actual first-level transition and a technically complete retained episode |

Levels 2–3 and cross-layout transfer belong to the later RQ7 study. They are excluded here.

### Separate evaluation conditions

| Condition | Inputs and behavior | Permitted conclusion |
| --- | --- | --- |
| Unchanged-agent gameplay | Existing observations, prompts, tools, history, output format and fallbacks; passive recording only | How the current agent actually acts and whether these episodes succeed |
| Prompted component tests | Explicit target, prediction, hypothesis or effect questions, using frozen diagnostic prompts | Performance on those supplied tasks; not unchanged-agent gameplay or autonomous discovery |
| Assisted gameplay | Additional masks, control explanations or curated history supplied as a separately reviewed intervention | The effect of that assistance under the tested conditions; not a unique cause of baseline failure |

Keep prompts, manifests, budgets and results distinct across these conditions. Shared model weights do not make
different prompts or information conditions the same agent baseline. Diagnostic answers must never enter the
gameplay context or persistent agent memory. Do not tune the baseline on diagnostic results before its frozen
gameplay is collected. Additional comparisons need their own review and authorization.

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

Classify each reference claim as a directly observed fact, an independently tested relationship, or a remaining
interpretation, and retain its scope and supporting evidence. A successful human sequence does not establish
that every step was necessary or that the narrated rule is universal. Cross-review should look for alternative
valid actions, strategies and explanations, rather than only confirm the proposed answer. Do not make matching
the human route a scoring requirement. Unsupported interpretations remain unscored or explicitly ambiguous.

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

Keep human-selected-state diagnostics separate from evidence collected on states reached by the agent itself.
Record state/history provenance, selection and mode in each case. A good score on a human prefix does not show
that the agent retained or understood the relevant evidence in its own episode. After collecting the baseline,
inspect its encountered states for failure analysis. New cases motivated by those failures are exploratory;
they do not enter the original frozen score or become confirmatory tests of an improvement trained on them.

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

Providing a legal-action list makes enumeration a consistency check. Supplied-target and supplied-transition
questions measure conditional grounding and evidence interpretation. Autonomous control discovery needs
evidence from the agent's own choices and observed effects. Click-only games use click controls;
directional-only games must not be forced into a click-targeting task. Case applicability and the final
category counts are reported per game.

Include representative failure contrasts where evidence permits:

- A click inside an object versus a nearby-background click or a hole inside its bounding box.
- The right coordinates on a static example rather than an interactive control.
- The same action under different selected objects or modes.
- An already-selected object, where lack of visible change does not establish a selection failure.
- A blocked directional move and a successful move.
- A status-strip change without the intended object effect.
- A missing/uncertain acknowledgement or missing post-observation, requiring an unresolved result.

### Action contract and scoring

For unchanged-agent gameplay, passively retain the original policy output before dispatch, the actual request,
acknowledgement and resulting observation. Preserve the existing prompts, history and output contract. Record
intended objects, predictions and evidence references only if the baseline already emits them; otherwise mark
them unobserved. An evaluator's inferred target is an attribution, not a recorded agent intention. Do not add
model calls, required rationale fields or reference object IDs to obtain otherwise unavailable information.

Prompted component tests may explicitly request a target, prediction or evidence reference. Record those
answers before revealing the outcome, and identify the extra task and information. If a controlled execution
check dispatches a proposal, use the actual interface and pinned engine from a reproducible state, and retain:

| Stage | Check | What is not established by this stage alone |
| --- | --- | --- |
| Proposal | The proposed action is legal and appropriate for the supplied task and evidence | That the interface executed it |
| Dispatch | The submitted action matches the proposal, and the engine accepted or rejected it | That the intended object effect occurred |
| Effect and recognition | Compare the engine outcome with the task; separately score the agent's interpretation | A correct supplied-transition answer does not establish execution ability |

Controlled execution checks are separate from the six primary episodes; they cannot repair, restart or supply
history to those attempts. Their actions and model requests need separately bounded, reviewed accounting.
If they are absent, report RQ2 execution as assessed only through gameplay, not through static answers.

Validate strict coordinate types/ranges and action payloads immediately before dispatch. An invalid proposal
fails the policy's proposal-validity check even when a guard blocks it. Preserve the existing baseline fallback
and identify every action it supplies; distinguish policy proposals from fallback and dispatched actions.

| Measure | Denominator / interpretation |
| --- | --- |
| Legal proposal rate | All required action proposals, including malformed/invalid ones |
| Target-coordinate hit rate | Applicable click cases with a specified target; score against the correct coordinate set |
| Proposal-to-dispatch fidelity | Actual execution checks; report policy, fallback and dispatched payloads separately |
| Verified intended-effect rate | Executed cases with a stated task or recorded intention; acknowledgement alone earns no effect credit |
| Selection/mode correctness | Cases where the current target or mode changes the meaning of an action |
| Effect-classification accuracy | All required effect judgments, including unknown/ambiguous cases |
| Repeated ineffective-action rate | Recorded repeats with no relevant observed effect; interpret using mode/history and report uncertainty about unobserved intent |

A repeat can be useful for lengthening, movement or a genuinely new test. The repetition diagnostic must account
for those cases. An ineffective action can still provide useful information. Do not classify every repeat as
stagnation, or accept an asserted reason alone as proof that it was a useful experiment.

Report geometry and semantic failures separately. Parent and child masks can overlap; a hit on a parent does
not automatically satisfy a question that specified one child.

## 4. RQ4: rule inference and hypothesis testing

### Separate the capabilities being measured

| Capability | Evidence required | Interpretation limit |
| --- | --- | --- |
| Evidence interpretation | Correctly identifies changes in a supplied transition | Does not show the agent noticed or retained them during play |
| Conditional inference | Predicts effects or discriminates and updates supplied hypotheses | Does not establish autonomous hypothesis generation |
| Autonomous discovery | During unchanged gameplay, identifies an uncertainty and investigates it where the baseline exposes that behavior | If no such record exists, discovery is unobserved; do not invent a rationale from a successful action |
| Operational use | Later choices and predictions respond consistently to relevant evidence and changed conditions | Behavioral consistency supports use of a relationship, not proof of an internal reasoning mechanism |

The static inventory below primarily tests the first two capabilities. Assess the latter two from existing
gameplay outputs and behavior where the evidence permits. Do not add a hypothesis planner to make them visible.
A missing verbal rule does not establish absence of useful behavioral knowledge, and a correct verbal rule
does not establish that the policy follows it.

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
or mark the item unsupported. Preserve the relevant engine state and history when constructing contrasts;
similar-looking screenshots do not guarantee equivalent selection, mode or hidden state. Accept alternative
probes that satisfy the same discrimination criterion. A legal action that merely changes the screen is not
necessarily informative.

Keep probe informativeness separate from its usefulness for the current goal. An informative probe may waste
scarce actions, and advancing the goal can be reasonable without resolving every rule. Report whether relevant
uncertainty was reduced, whether that information mattered to the decision, and its observed resource cost.
Do not require complete game-rule knowledge when sufficient knowledge already supports an appropriate action.

Keep evidence-reading controls alongside inference cases. Otherwise a prediction error could come from failing
to read the supplied transition rather than failing to infer a rule. Use frame-specific object tracking to
separate target movement from animation, view changes and interface updates.

### Hypothesis record

Use short structured statements in prompted component tests; do not require or score an elaborate internal
reasoning narrative. In unchanged gameplay, retain only the hypothesis fields already produced by the agent.

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
Treat every statement as a reported claim. Compare prospective predictions with outcomes and later choices;
do not treat a plausible explanation as proof of the cause of an earlier action.

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
Distinguish factual correctness from evidential support: a correct guess can be unsupported, while a justified
uncertainty judgment need not supply the hidden true rule. Never grade a broader rule as established solely
because it agrees with the reference narrative.

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

This primary condition measures solving without recovery through resets. A reset can be a legitimate learning
or recovery action in another task, so an attempt-ending reset does not establish a general inability to learn.
Do not silently introduce a recovery condition or a replacement attempt after observing failure.

### Decision loop

1. Supply the current observation and legal controls through the unchanged baseline interface.
2. Run the existing policy with its existing prompts, tools, history and output contract.
3. Passively retain its original output and any naturally emitted targets, predictions or hypotheses.
4. Apply the bounded execution guard, preserve the existing fallback behavior, and record what is dispatched.
5. Retain the acknowledgement and next observation; independently assess the resulting effect.
6. Update only the history or other state that the baseline already maintains, using its existing rules.
7. Stop on the first-level transition, a budget limit, technical failure or explicit attempt-ending reset.

The evaluator may investigate object selection, exploration, rule revision and effect recognition from this
trace, but must mark unobserved intentions or hypotheses as such. Evaluator annotations never feed back to the
policy. Do not add a new hypothesis ledger, planner or prediction request before measuring the current agent.

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
Six successful episodes meet this development acceptance criterion; they do not establish a stable success
rate across repeated attempts, new initial states or unseen games. A level transition alone also does not
establish that the agent discovered a particular rule rather than found a successful action sequence.

## 6. Scoring and decisions before improvements

The following are proposed engineering targets for a fully supported 12-item-per-game static inventory. Freeze
or revise them before model queries. If case counts change, freeze explicit integer requirements for the new
denominators; do not change thresholds after seeing results.

An item earns a correct result only when all of its required fields satisfy the frozen checks. Report individual
field scores as additional diagnostics. Keep missing, malformed, refused and technically interrupted responses
visible against the planned inventory; do not improve the apparent score by dropping them from the denominator.

Report distinct layers rather than interpreting every failed item as a cognitive error:

| Layer | Required reporting |
| --- | --- |
| Technical availability | Planned, attempted, completed and missing cases, with infrastructure/refusal/interruption reasons |
| Response validity | Parseable outputs and field-contract failures, distinguishing policy output from transport failures |
| Semantic correctness | Per-field and whole-item correctness among available valid answers, with those denominators explicit |
| Overall acceptance | Fully correct items against the complete planned inventory; unavailable cases remain visible and cannot earn credit |

Conditional semantic accuracy does not replace the overall acceptance score or demonstrate full coverage.
Mixed field failures and infrastructure losses must remain distinguishable when selecting an improvement.

| Component | Proposed target | Interpretation |
| --- | --- | --- |
| RQ2 static diagnosis | At least 11/12 correct per game; also report each metric and applicable denominator | Meets the supplied-task engineering target; actual execution and autonomous control discovery need separate evidence |
| Execution guard | Zero invalid payloads dispatched | A harness invariant; separately report invalid proposals that it blocked |
| RQ4 static diagnosis | At least 10/12 correct per game, including both determinate and uncertainty items | Meets the conditional-inference target; not certification of autonomous discovery or behavioral use |
| RQ5 primary baseline | 6/6 technically complete first-level passes within budget | Meets the owner's six-game development baseline |

RQ2/RQ4 scores are diagnostic engineering targets. They should not cause selective omission of low-scoring
games from the planned RQ5 comparison. A score above threshold does not establish that any particular execution
is safe or correct. Conversely, a static failure can be useful even when a game is solved.

| Observed pattern | Investigation before selecting an improvement |
| --- | --- |
| Wrong target despite a sensible control | Review object identification, role labeling, coordinates and stale masks |
| Right object but wrong control or mode | Review control semantics, selection handling and effect verification |
| RQ2 strong, RQ4 weak | Review evidence reading, probe informativeness and rule updating |
| RQ2/RQ4 strong, RQ5 weak | Compare supplied information and human-selected states with the actual episode before investigating goals, ordering, budgets or integration |
| Baseline strong across all six | Prepare RQ7 transfer cases before claiming general solving ability |

These patterns generate competing explanations; none uniquely locates a failed component. RQ2 and RQ4 share
perception, evidence reading and response-format demands, so their aggregate scores are not independent skill
measurements. Resolve interpretations using individual transitions, errors and information conditions.

After baseline measurement, separately reviewed assistance can test whether added locations, control
descriptions or history improve performance. Retain the original baseline and record all extra information,
prompt changes and costs. Masks may reveal relevance or roles; curated histories may bypass memory and
discovery. Compare equivalent pre-action states/histories and matched resource limits where feasible, and
inspect information differences beyond token counts. Whole-episode assistance can change which states are
visited, so its aggregate effect cannot isolate one component. Improvement shows the assistance helped;
non-improvement does not rule out the targeted weakness when other bottlenecks remain. Neither result uniquely
establishes the cause of the original failure or demonstrates unaided capability.

## 7. Evidence and implementation requirements

| Artifact | Required contents |
| --- | --- |
| Case record | ID, evaluation condition, human/agent-state provenance, game/version, level, RQ/task, state/history references, allowed inputs, accepted alternatives, applicability and scoring rule |
| Annotation provenance | Owner/assistant origin, review status, observed/tested/interpreted claim status, scope, object/interaction masks, ambiguity and amended labels |
| Baseline lock | Unchanged agent/model/runtime versions, prompts, tools, schemas, history policy, decoding and fallbacks; separate diagnostic/assistance manifests, budgets and graders |
| Per-decision record | Original policy output, observation, legal controls, fallback and dispatched actions, acknowledgement, post-observation and counters; naturally emitted intentions/predictions distinguished from evaluator attributions and unobserved fields |
| Per-episode record | Initial state, full event sequence, engine completion evidence, stop reason, actual counts/time, cleanup and finalization |
| Independent evaluation | Event-derived totals and contract/goal/cap checks; separate engine-state replay findings, exact input hashes and scores by evaluation condition |
| Report | All six outcomes, coverage/validity/semantic/acceptance denominators, missing/ambiguous cases, exploratory analyses, failure examples and limits on claims |

CPU checks should exercise mask boundaries/holes, parent-child overlap, unavailable controls, strict payload
types, stale selections, acknowledgement loss, status-only changes, contradictory rule evidence and forged
completion summaries. The evaluator must reject altered/stale inputs and reconstruct totals from events.
Review the exact package built from the latest audited fixes; do not reuse a stale source lock.

Distinguish record validation from engine-state validation. Hashes, contracts and event-derived totals establish
record consistency, not that the recorded observations truly followed from those actions. Where reproducible,
independently replay dispatched actions through the pinned engine from the retained initial state/seed and
compare observations, progression and relevant state, preserving timing/randomness inputs where needed.
Unexplained divergence prevents an independently engine-verified result even if the summary matches. Preserve
the original evidence. If replay cannot reproduce a case, report what was and was not independently verified;
record-only validation must not be presented as engine-state validation.

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
| 1 | Agree on the separate evaluation conditions, unchanged baseline interface, claim limits, schemas, pins and proposed pilot limits | Re-estimate after checking existing baseline outputs |
| 2 | Teammate object/goal/similarity references; your RQ2/RQ4 cases with claim provenance and accepted alternatives | Depends on independent contrast checks and supported inventory |
| 3 | CPU graders, controlled execution checks, passive baseline recording, engine replay and fault checks | Estimate after inspecting reusable audited components |
| 4 | Review concrete static/gameplay packages and their exact budgets | Depends on remaining runtime/provider checks |
| 5 | Separately authorized unchanged gameplay and isolated component evaluation, collection and independent validation | Runtime estimated after setup/latency measurements |
| 6 | Six-game report, explicitly exploratory diagnosis on encountered states and evidence-based improvement choice | Depends on missing evidence and adjudication needs |

The previous one-to-two-day estimate is not a commitment for the expanded validation work. Re-estimate after
checking reusable tooling and unsupported cases. Finish the unchanged baseline before feeding diagnostic
findings into agent improvements, advancing to later-level transfer or presenting improvements as established.

## 9. Draft v2 review changes

This revision separates unchanged gameplay, prompted diagnostics and assisted comparisons; removes new
intention/hypothesis requirements from the baseline; connects proposals to dispatch and effects; distinguishes
conditional inference from discovery and use; qualifies reference claims and accepts alternative solutions;
separates human and agent state distributions, reported claims and behavior, and technical versus semantic
scores; limits causal claims from assistance; and distinguishes record checks from engine replay. It also
makes the no-reset and single-attempt interpretation limits explicit. This is a planning revision only and
authorizes no implementation, upload, model evaluation, game action or compute.
