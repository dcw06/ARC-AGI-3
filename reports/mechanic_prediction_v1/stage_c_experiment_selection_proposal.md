# Stage C: Informative Experiment Selection Proposal

Status: proposal only; proceed only after Stage B benchmark review and separate approval.

## Question

Given evidence consistent with multiple declared mechanisms, does an explicit experiment-selection procedure choose an available action whose possible observations distinguish those mechanisms, compared with ordinary action selection under the same budget?

## Design

For each reviewed ambiguous scenario, show the same evidence to both arms. Each arm chooses one currently available action and gives the predicted observation under each surviving explanation. Freeze action/call budgets, response schema, model/revision, tokenizer/template, decoding, request order, evidence bytes, and scenario schedule. Reveal the result only after the action is committed, then request a status update. Retain all previously compatible mechanisms and record every elimination with its supporting observation.

The evaluator enumerates only the scenario's declared mechanism space. An action is informative only if distinct surviving mechanisms predict different observable outcomes for that action. A changed action choice alone does not count as informative, and finite-space discrimination is not proof of a unique real-world mechanic.

## Measures and Gates

- Fraction of selected actions that distinguish at least two surviving mechanisms.
- Reduction in ambiguity within the declared space after the observed result.
- Prediction improvement on a subsequently proposed, unobserved action.
- Wasted actions and unsupported mechanism elimination.
- Hypothesis update supported by the newly returned evidence.

Keep synthetic results separate from any later real-game transfer. Freeze scoring, stop rules, development/evaluation separation, token accounting, and authorization only after independent review of Stage B. No GPU or live game calls are approved by this proposal.