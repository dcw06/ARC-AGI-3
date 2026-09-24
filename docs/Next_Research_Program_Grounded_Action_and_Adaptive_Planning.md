# Next research program: grounded action and adaptive planning

Date: September 23, 2026  
Evidence baseline: commit `3283cbf`  
Status: proposed development program, not a frozen experiment or compute authorization.

## Central question

Can the agent build an accurate understanding of an unfamiliar game, learn how
its actions affect it, and use subgoals, recovery, and deliberate restarting to
complete levels within a fixed budget?

Start local development now. Do not implement all capabilities as one treatment
or launch the entire program as one experiment. Preserve the existing runnable
baseline, frozen protocols, and archived decisions. Production certification and
exact billing reconciliation remain separate open work.

## Evidence informing the program

The paired perception R2 run archived at `3283cbf` completed with independently
replayable evidence. Image transport and processor/server token accounting worked.
All ten board answers were complete, valid JSON, but detection recall at the
frozen bounding-box IoU threshold was 0/11 reference objects for both text and
images. This does not prove that either representation cannot work.

Both interface probes emitted the requested legal click and non-coordinate action,
but classified all seven action IDs as coordinate-taking. Incorrect descriptions
therefore did not prevent correct action construction in these examples.

Relationship scores conditioned on matching objects cannot independently diagnose
geometric reasoning when no objects match. Likewise, a difficult multi-object
inventory may obscure simpler capabilities. Output burden, coordinate grounding,
object selection, and instruction interpretation remain hypotheses to distinguish.

## Research questions

1. **Controls:** Can the agent correctly invoke the supplied legal actions and
   distinguish interface syntax from unknown game effects?
2. **Grounding:** Can it locate a relevant object, distinguishing contours, colors,
   internal markings, rotations, and reflections where action-relevant?
3. **Action effects:** Can it predict and learn what one action changes, including
   delayed, transient, and no-visible-effect outcomes?
4. **Subgoals:** Can it choose a useful intermediate objective with observable
   success conditions and justified dependencies?
5. **Interruption and recovery:** Can it suspend a plan when new evidence reveals
   danger or invalidates an assumption, then verify that recovery actually works?
6. **Failure attribution:** Can it propose evidence-supported explanations for
   failure and change subsequent behavior without inventing causes?
7. **Strategic restarting:** Can it recognize when resetting is more promising
   than continuing, retain permitted knowledge, and improve the next attempt?
8. **Feedback incentives:** Does explicit outcome feedback or a registered penalty
   scheme improve completion beyond factual transition reporting?
9. **Integration:** Do individually useful mechanisms improve completion together
   within the total resource budget, including their overhead?

## Stage A — inspect existing failures offline

No model calls or GPU run are needed.

- Render predicted and reference boxes over each retained board, keeping text and
  image answers separate.
- Inspect coordinate scale, offsets, swapped axes, inclusive-boundary conventions,
  object selection, and apparent misunderstanding of the requested description.
- Separate measured observations from explanations. Test proposed transformations
  offline as diagnostic analyses, never as retroactive scoring corrections.
- Inspect control descriptions alongside actual emitted actions.
- Preserve original outputs, hashes, frozen scores, and all unsuccessful cases.

Deliverable: a short failure analysis with overlays, a case-by-case table, and
one prioritized hypothesis suitable for a prospective test. Do not claim a
universal failure mechanism from this small workload.

## Stage B — a minimal grounded-action experiment

Next bounded question:

> Can the agent identify one visible target, issue an appropriate legal action,
> predict a visible effect, and update its hypothesis from the result?

### Local implementation

- Construct a minimal request: current observation, actual legal action contract,
  and bounded relevant history. Avoid a mandatory exhaustive object inventory.
- Define a compact response: one intended target where applicable, one legal
  action, one predicted effect, and one distinguishable alternative outcome.
- Validate actions without silently rewriting the model's proposal. Retain rejected
  proposals and any separately labeled execution fallback.
- Integrate transition records with a shared monotonic episode clock and durable
  prediction retention before dispatch.
- Retain returned frames, exposed state/progress signals, action receipts, and
  observations needed to evaluate transient changes.
- Verify every consecutive record pair, including observation identity and
  cross-step chronology. Bind request/response hashes to actual retained content.
- Keep unknown, timed-out, and ambiguous dispatch outcomes distinct from no-effect.
  Do not replay an action merely because its acknowledgement is missing.

### Experimental boundary

Select the precise intervention after Stage A. Use an unchanged baseline and one
isolated candidate, with matched model, cases, seeds, observation access, and total
action/compute ceilings wherever applicable. A simplified prompt is itself a
treatment and must be recorded as such.

If evaluator-derived boxes or targets are supplied to isolate action learning,
label the condition **assisted**. It tests downstream competence given help,
not end-to-end perception. Keep it separate from an unassisted comparison.

Do not require perfect perception before interactive investigation. Require enough
retained evidence to distinguish an incorrect target from an incorrect action or
an incorrect causal prediction.

Deliverable: a locally tested, supervised runner and independently replayable
evaluator, followed by a frozen protocol and separately proposed GPU budget.

## Stage C — learn from transitions

Use the loop:

**Observe → predict → act → compare → revise.**

Distinguish three knowledge types:

- Given interface facts: legal IDs and argument conventions.
- Observed facts: visible objects, positions, changes, and exposed status.
- Learned hypotheses: action effects, hazards, dependencies, and goal conditions.

Track object identity with uncertainty rather than assuming every similar region
is the same persistent object. Classify outcomes as progress, informative no-effect,
unexplained no-effect, harmful transition, terminal failure, or unresolved outcome.
An unchanged final frame need not mean nothing happened.

Assess prediction accuracy and whether learned rules change later choices.
Plausible explanations alone are not evidence of causal learning. Where practical,
use a discriminating action to test competing explanations within the budget.

## Stage D — subgoals and adaptive recovery

Build scripted tests in parallel with Stages A–C. Introduce mechanisms separately
in real-model experiments so their contributions remain interpretable.

### D1. One bounded subgoal

Store the goal, its proposed link to completion, prerequisites, observable success
condition, action allowance, and conditions for abandoning it. Compare this
scaffold with the matched action-feedback baseline. Do not reward arbitrary
subgoal completion as though it were level completion.

### D2. Interruptible plans

Reassess assumptions after each observation. When evidence suggests a sufficiently
urgent threat, suspend the ordinary subgoal and choose a bounded protective one.
Record the evidence and confidence; do not infer danger from color alone.

Verify improvement: an escape command is not successful escape if the agent is
blocked. Revise ineffective actions, avoid repeated defensive loops, and resume
the earlier goal only when its prerequisites and safety assumptions still hold.
Risk avoidance is subordinate to the task objective, not an objective of its own.

### D3. Failure review

Inspect a bounded sequence of preceding transitions after damage or death. The
last action or nearest object is not necessarily the cause. Record alternatives
and unknowns honestly, then specify a changed strategy or informative test.
Do not require repeated deaths merely to establish a hypothesis.

### D4. Strategic restarting and rescue options

Before declaring an attempt unrecoverable, inspect available actions, resources,
and environmental opportunities for a feasible rescue. Conversely, do not preserve
a poor state merely to avoid recording a death or reset.

Compare continuing, recovering, and restarting based on:

- current recoverability and remaining opportunities;
- known or uncertain reset consequences;
- progress/resources lost and restored;
- remaining total time, actions, and reset allowance;
- the changed strategy for the next attempt.

Prefer an explicit reset when supported and appropriate. Do not assume death has
the same effect, or that resetting restores tools or other resources. Preserve
permitted learned knowledge while clearing obsolete episode state. Bound repeated
resets and charge all failed attempts and rebuilding to the experiment budget.

## Stage E — feedback and penalties, then integration

First retain factual outcome categories. Do not automatically penalize unchanged
screens: they can provide information or precede delayed effects. Death is an
adverse outcome but may be part of a useful restart decision.

Only after outcome classification is credible, compare factual feedback with one
explicitly registered incentive scheme. Specify whether the intervention is
prompt feedback, action-ranking logic, or training reward; these are different
mechanisms. A numeric penalty does not itself update model weights or explain
causation. Guard against optimizing the shaped score instead of finishing levels.

Combine mechanisms only after bounded comparisons provide evidence about their
individual effects. Re-measure combined overhead and interactions; individual
benefits do not guarantee a combined benefit.

## Local test matrix

Include correct and malformed actions, wrong coordinates, transient and delayed
changes, ambiguous effects, a new threat, blocked retreat, unnecessary interruption,
safe resumption, conflicting subgoals, uncertain death causes, recoverable states,
useful resets, costly resets, and repeated-reset loops. Keep fixture labels and
solution information evaluator-side. Scripted success proves implementation
behavior, not model competence or real-game performance.

## Measurement and safeguards

For interactive solving experiments, primary outcome is level completion under
the matched total budget. Diagnostic stages have narrower primary measures such
as localization or valid action issuance; neither implies solving success.

Secondary measures include prediction accuracy, repeated ineffective actions,
subgoal attainment, repeated comparable failures, justified/unnecessary
interruptions, verified recovery, useful/wasteful resets, and action/token/time
overhead. Report uncertainty and missing/censored evidence. Do not treat every
question on one board as an independent game.

Before each model experiment, freeze cases, scoring, controls, output limits,
resource ceilings, stop rules, interpretation, and compute authorization. Use
development-only data, no solution leakage, no scored submissions, and no
automatic retries. Preserve the runnable baseline and append new decisions.
Success in this research program does not close production lifecycle gates.

## Immediate implementation checklist

1. Produce Stage A overlays and a concise localization failure analysis.
2. Select one hypothesis and write the minimal grounded-action protocol draft.
3. Implement durable transition records and independently verifiable execution.
4. Test the runner and controller mechanisms locally with scripted fixtures.
5. Audit requests, token/output limits, offline dependencies, and resource costs.
6. Review and freeze one bounded experiment; request separate launch authorization.

No unchanged perception rerun is proposed. The completed R2 reservation is consumed
and provides no authority or assumed unused compute for this program.
