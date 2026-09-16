# Preliminary proposal: consequence-driven reasoning for the agent

Date: 2026-09-15  
Status: exploratory design note for future agent changes

## Purpose and scope

Explore whether a bounded sequence of “so?” questions can help the agent connect
observations to useful actions. Each question asks: **What consequence does this
have for what I should do next, and how could I test it?**

This note records an idea from a conversation. It is not an admitted treatment,
an execution protocol, or evidence of improved performance. It does not change
the active policy, frozen experiments, phase decisions, compute authorization,
or holdout eligibility. Concurrent Phase 4 work proceeds under its own records.

## Origin: the conversation exercise

The exercise began with a statement, followed by repeated “so?” questions:

| Statement | Role in the conversation | Possible agent-design lesson |
| --- | --- | --- |
| A system can pass every test we wrote and still fail at the task we built it for. | Separates checks from the intended outcome. | Measure task progress as well as valid execution. |
| Time you spend with someone you love is time you cannot spend doing something else. | Identifies opportunity cost. | An action consumes time and budget that could support another action. |
| Loving someone involves choosing what you are willing to miss to be with them. | Connects a constraint to a choice. | Explain why a proposed action deserves its cost. |
| Someone can matter deeply to you and still feel neglected if you never make time for them. | Distinguishes intention from experienced effect. | A plausible intention is not evidence of a useful environment effect. |
| If you want them to feel loved, find out what makes your care reach them. | Proposes learning what produces the desired effect. | Use an observable test to investigate an uncertain action-effect relationship. |

These statements are conversational extensions, not a mathematical deduction.
In particular, the last statement introduces a goal. That is a warning for agent
design: fluent reasoning can silently add objectives or assumptions.

## Proposed reasoning structure

Use a bounded sequence of explicit records:

**Observation references → interpretation → uncertain hypothesis → predicted
consequence → one legal probe → observed result → revision.**

Each stage has a different evidential status:

1. **Observation:** cite retained transitions and available measurements.
2. **Interpretation:** state only what those observations support, including
   limitations and alternative explanations.
3. **Hypothesis:** propose a possible mechanic or condition; keep it unverified.
4. **Prediction:** specify an observable outcome before dispatch, with its scope
   and connection to the proposed action.
5. **Probe:** select one legal action that could advance the task or distinguish
   relevant alternatives within the available budget.
6. **Revision:** compare the prediction with the next observation and retain,
   weaken, reject, or leave the hypothesis unresolved as the evidence permits.

Repeating “so?” is not itself the capability. The candidate capability is making
the connection between evidence, uncertainty, expected consequences and action
explicit enough to test.

## Illustrative cd82 application

The retained review in `reports/phase2_cd82_evidence_review.md` describes repeated
clicks with no completed levels and final-grid changes confined to the bottom
row. The following is a proposed reasoning example, not a retrospective diagnosis
or treatment-admission record.

| Stage | Illustrative statement |
| --- | --- |
| Observation | “Repeated clicks did not complete a level; observed final-grid changes were confined to the bottom row.” |
| Interpretation | “These transitions do not establish that this click advances the task.” |
| Hypothesis | “The location may be ineffective, or its effect may depend on another condition.” |
| Proposed experiment | “Identify an evidence-supported alternative location or condition and predict a relevant observable difference before testing it.” |
| Decision | “If the probe is legal, affordable and informative, execute one action and inspect the result.” |

A different click is not automatically a discriminating experiment. The agent
must explain which alternatives it could distinguish and what differing outcomes
would mean. If it cannot, classify the action as exploratory rather than claiming
verified information gain.

Bottom-row changes must not automatically count as progress or useful support.
Their meaning remains uncertain. Missing intermediate frames also limit what can
be concluded from final-frame comparisons. This idea does not establish that the
existing failure was caused by a missing hypothesis/probe capability.

## Candidate interface and boundaries

An illustrative proposal record could contain:

- `evidence_refs`: retained observations or transitions supporting the proposal.
- `interpretation`: a bounded claim about those observations.
- `hypothesis`: a tentative explanation with explicit scope.
- `alternatives`: competing explanations where available.
- `goal_link`: how the action relates to task completion or a relevant uncertainty.
- `prediction`: a typed, precommitted observable predicate.
- `probe_action`: exactly one proposed legal action.
- `result_disposition`: a subsequent evidence-based update, separate from the
  pre-action proposal.

This is a design sketch, not a production JSON schema. A future implementation
must freeze field types, size limits, evidence-resolution rules and failure
behavior before execution. Do not add these fields to the frozen E1 schema.

Deterministic code should resolve evidence references, enforce budgets and legal
actions, evaluate supported predicates, and own dispatch and finalization. The
model proposes uncertain interpretations and actions; its wording cannot promote
a hypothesis to verified status or bypass controller guards.

Predicates should use the existing three-valued approach: match, mismatch or
unknown. Missing evidence yields unknown. Even a match does not establish general
mechanics or causal attribution; support remains scoped and subject to registered
rules and contrary evidence.

## Bounded execution and stopping

Start with single-action proposals. Persistent hypothesis memory, extra inference
turns and multi-action queues are separate design choices that must be explicitly
declared rather than bundled into this idea implicitly.

Stop the reasoning sequence when:

- A legal, testable action has been selected.
- Available evidence cannot support another useful inference.
- The next step merely repeats a claim or introduces an unsupported assumption.
- The reasoning, token, wall-time or action budget is exhausted.
- Cancellation, lifecycle state or ambiguous dispatch forbids further action.

The exact limits remain to be frozen. Any fallback behavior must also be defined
prospectively. A reasoning failure must preserve the runtime's existing safety
guarantees; an ambiguous dispatch must not trigger another probe.

## Risks to test

- **Unsupported inference:** repeated elaboration makes guesses sound established.
- **Goal drift:** the agent invents a subgoal without a link to completing the game.
- **Uninformative novelty:** different actions reduce repetition without helping.
- **Irrelevant support:** timer or unrelated pixel changes are treated as success.
- **Retrospective predictions:** the agent rewrites expectations after seeing results.
- **Cost growth:** additional prompts or context consume resources without benefit.
- **Model mismatch:** a formally valid deduction rests on incorrect game assumptions.

## Future evaluation

The idea fits provisionally near E5 hypothesis/probe work. Actual classification
and admission require a new review against the active experiment contract. The
existing no-treatment decisions remain historical conclusions under their evidence.

Before implementation or target execution:

1. Identify a reproduced development failure that this capability could address
   and record why simpler alternatives might or might not explain it.
2. Freeze the exact parent, candidate change, prompt/schema, inference-call and
   context policies, workload, seeds, budgets, thresholds and stop rules.
3. Define how probes are selected and how predictions are evaluated without
   trusting model assertions as environment facts.
4. Compare with E1S-R under matched resource limits, charging all reasoning,
   support-building and probe costs. Use the registered whole-workload comparison
   method when clients share compute; separate paired games are not independent
   resource-run replicates.
5. Measure official task outcomes, completed levels, resource use and reliability.
   Record repeated ineffective actions and prediction results as diagnostic
   measures. Reduced repetition or higher predicate match rates alone do not
   establish improved game solving.
6. Preserve provisional or negative conclusions when evidence is insufficient.
   Holdout access and GPU spending require their own applicable eligibility and
   authorization; this note grants neither.

## Questions to resolve when revisiting

- Can one structured inference request implement the idea, or are extra turns
  necessary and worth their cost?
- Which predicates can trusted runtime extraction evaluate on real observations?
- What evidence distinguishes a useful probe from arbitrary exploration?
- Does the candidate need persistent state, and if so, which separate treatment
  and evidence-retention rules govern it?
- What prospective result would justify adoption, rejection or another study?

## Related project records

- `docs/ARC-AGI-3_Project_Plan_8.md`: experiment, prediction and controller design.
- `reports/phase2_cd82_evidence_review.md`: limitations of the motivating example.
- `config/phase3_decision.json`: existing conditional no-treatment disposition.
- `evaluation/phase3.py`: offline predicate and support-gate preparation.
- `agent/e1_policy.py`: current structured single-action policy interface.

Resolve the active versions of these records when the proposal is revisited.
