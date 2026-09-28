# Action feedback and interruptible subgoals — research draft

Status: provisional brainstorm, not an execution contract or compute authorization.
This additive plan records the September 23 discussion. It does not modify frozen
policies, historical decisions, the perception diagnostic, or Phase 4 exit gates.

## Research question

Given an explicit control specification and sufficiently reliable observations,
can the agent form testable subgoals, predict action effects, interrupt a plan
when new evidence reveals danger, and use progress, no-effect outcomes, and
deaths to improve level completion within fixed action and compute budgets?

## Knowledge to distinguish

- Interface facts: legal action IDs, parameters, coordinates, and invocation rules.
- Observations: visible objects, geometry, state changes, and exposed status signals.
- Hypotheses: action effects, hazards, dependencies, and possible winning conditions.

Knowing how to issue an action is not knowing what it does in an unfamiliar game.
Hypotheses must retain their evidence and uncertainty. Do not supply game solutions,
hidden state, source-derived mechanics, or holdout knowledge to the policy.

## Control and feedback loop

1. Check available actions and current observations.
2. Choose one bounded subgoal with an observable success condition and a reason
   it may contribute to the ultimate objective.
3. Before acting, predict an observable effect and record what would contradict it.
4. Execute one legal action and compare the resulting observation with the prediction.
5. Classify the result: progress, informative no-effect, unexplained no-effect,
   harmful transition, terminal failure, or uncertain outcome.
6. Continue, revise, suspend, or abandon the subgoal based on that evidence.

Do not automatically penalize an unchanged frame: an effect may be delayed, hidden,
or require sustained action, and a failed probe may still provide information.
Repeated ineffective actions without a new hypothesis are a separate diagnostic.
Death is an adverse task outcome, but an arbitrary numerical penalty is not yet
specified. First retain outcome categories; reward shaping is a separate experiment.

## New addition: interruptible subgoals and urgent threats

At each new observation, assess whether the current plan's assumptions still hold.
When evidence indicates an immediate threat to continued progress, suspend the
ordinary subgoal and select a bounded protective subgoal. Threats must be grounded
in observed transitions or explicitly labeled hypotheses, not inferred solely from
an object's color or appearance. Some tasks require risk; avoiding all risk is not
the ultimate objective.

Retain a compact record:

- active subgoal and observable success condition;
- interrupting evidence, suspected threat, and confidence;
- suspended subgoal, if any;
- protective action and predicted effect;
- observed outcome and whether protection actually improved;
- condition for resuming, revising, or abandoning the previous subgoal.

For example, the Minecraft discussion illustrated suspending resource gathering
when a nearby threat and critically low health become visible. The protective
subgoal is to establish separation or cover. This is an explanatory example,
not a Minecraft rule to inject into ARC games.

Issuing an escape action is not evidence of successful escape. Check whether
separation, accessibility, exposure, or another observable risk indicator changed.
If movement is blocked, revise the route instead of repeating the same command.
Reassess after each observation; do not execute a long unchecked escape sequence.
Resume the suspended plan only when its prerequisites remain valid and the
protective success condition is supported. Bound repeated switching and defensive
loops so that apparent caution cannot replace level progress indefinitely.

## Failure attribution

After damage or death, inspect a bounded sequence of preceding observations and
actions, not only the final action. Distinguish observed events from candidate
causes, delayed effects, and unresolved alternatives. A nearby object is not proof
of causation. Record unknown causes honestly. Where permitted and useful, choose
a discriminating, lower-risk test; do not require repeated deaths to establish a
rule. Preserve failure evidence across resets within the registered memory bounds.

## Staged experiments

1. Verify control-specification competence and basic perception independently.
   Synthetic fixtures can exercise loop logic before real-model perception works;
   they do not establish game-solving ability.
2. Compare the baseline with a bounded subgoal/prediction/outcome-update scaffold.
3. Separately compare that scaffold with and without explicit interruption and
   protective-goal handling. Hold observation access, model, controls, workload,
   seeds, and total action/compute ceilings constant. Register any token overhead.

Keep these as distinct comparisons: a combined treatment cannot isolate the
benefit of interruption from the benefit of the underlying feedback scaffold.
Freeze development cases, success criteria, uncertainty reporting, stop rules,
and a separate budget before execution. No new GPU run is authorized here.

Local fixtures should cover a newly appearing threat, blocked retreat, delayed
effects, ambiguous death cause, disappearance of a threat, safe resumption, and
oscillation between competing subgoals. Include benign situations to measure
unnecessary interruptions. Fixture labels stay evaluator-side.

## Evaluation

Primary outcome: level completion under the matched budget. Secondary diagnostics:

- control/schema validity and prediction accuracy;
- subgoal attainment and repeated ineffective actions;
- repeated failures under comparable observed conditions;
- justified versus unnecessary interruptions;
- actions from observable threat evidence to a protective response;
- verified protective success, blocked-action recovery, and appropriate resumption;
- action/token/time overhead and time lost to defensive loops;
- evidence support and uncertainty in failure explanations.

Freeze operational definitions before a run. Evaluate latent threat or cause
claims only where independent evidence supports them; otherwise mark them unknown.
Do not equate fewer actions, fewer deaths, or plausible explanations with improved
solving. A frozen action cap may expire even when protective behavior succeeds.

The hypothesis is that evidence-based revision and reprioritization improve
progress, not that penalties alone teach the correct explanation. Until tested,
this remains a research proposal rather than a demonstrated capability.
