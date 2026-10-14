# Mechanic Prediction Benchmark v1

Status: CPU construction and four-issue review remediation complete; model execution, independent review, tokenizer lock, and compute authorization are not complete.

## Research Claim

The benchmark asks whether an agent can predict the observable effect of a proposed action that is absent from the supplied action history, conditional on a finite declared hypothesis space. Each hypothesis exposes its explanation, action/mode/coordinate rules, and default outcome to both arms. The evaluator and an independent derivation separately apply those same visible rules to acknowledged observations. The answer is `determined` only if every compatible hypothesis predicts the same outcome category. If compatible hypotheses disagree, the answer is `not_determined`.

The revised Stage B comparison tests applying competing visible hypotheses to a novel action; it does **not** test latent hypothesis generation or discovery. That inference question requires a separate intervention. Certainty is scoped to the visible declared rule space, not a hidden table or every real-world explanation. Editing an evaluator hypothesis changes the rendered request bytes as well as the key.

## Coverage and Evidence

The construction contains 32 synthetic scenarios: two development and two evaluation scenarios in each of eight families. The four marker locations are fully crossed with underdetermination and all four determined effect categories: every marker position occurs with each label. Marker position is generated independently of hypothesis ambiguity and outcome.

| Family | Distinction represented |
| --- | --- |
| Click grounding | Wrong coordinate versus ineffective action |
| Movement constraints | Unavailable/failed dispatch versus a legal but ineffective movement |
| Delayed effects | Immediate unchanged frame followed by a later change |
| Transient effects | Intermediate change followed by return to the original frame |
| Object correspondence | A marked visual region moves; identity remains uncertain |
| State dependence | Same action/coordinate under different exposed modes |
| Coordinate specificity | Observed click versus nearby unobserved coordinate |
| Contradiction | Later observation eliminates an earlier compatible explanation |

Each history retains initial and pre-action observations, exact action data and coordinates, available action IDs, dispatch status, all returned frames, returned signals, and record IDs. Failed dispatch and unknown outcome carry no inferred effect. The novel proposed action is checked against the exact action-and-coordinate history.

Fixtures use small synthetic 8x8 integer grids and synthetic action IDs; they are not playable ARC tasks and their action IDs do not assert actual game mechanics. Perception and coordinate diagnostics are separate requests and schemas. Region movement keys report observed before/after bounds only; visual movement alone does not establish persistent identity. No object-role annotations are supplied to either prediction arm.

## Keys and Shortcuts

The evaluator oracle and `independent_keys.py` independently apply the visible rules to derive compatibility and answer status. The build fails if these derivations disagree. There are 16 determinable and 16 underdetermined scenarios. The public request omits scenario/family/split labels and evaluator-derived frame outcome labels; it includes the declared candidate hypotheses required to make the uncertainty key observable.

Nine shortcuts are scored before any model execution, including a position-only predictor fitted on development. Position-only achieves 0% accuracy on determinable evaluation scenarios; position is crossed with both determination states and every determined outcome. Always-unknown has 0% accuracy on determinable cases. The development-selected strongest shortcut is `final_frame_only`; it reaches 37.5% on determinable evaluation scenarios and cannot solve the benchmark.

Shortcut selection uses development data only. These are construction-time baseline results, not model results. The evaluation split is small and synthetic; it is a milestone check, not a generalization estimate. See the generated [shortcut report](shortcut_report.md) for all split-specific metrics.

## Endpoints and Unit

Primary endpoints are prediction accuracy on determinable scenarios, unsupported certainty on underdetermined scenarios, and evidence-reference correctness. Abstention is reported separately from accuracy. Secondary endpoints include independent perception/grounding accuracy, contradiction revision, valid-output rate, challenge-family results, prompt/completion resource measurements, and latency. No model latency or real model-token count exists yet.

The scenario is the analysis cluster. A paired arm call is not an independent scenario. Repeated diagnostic questions from a scenario must be summarized within that scenario before inference.

## Reused Work and Boundaries

The exact suggested paths `research/feedback_action_v1/` and `research/transition_evidence_v2/` are absent from this transferred workspace. Closest compatible contracts reused by inspection are `research/action_effect_v1/records.py`, `research/action_effect_v1/fixtures.py`, `research/action_effect_history_v1/contract.py`, `research/perception_v1/fixtures.py`, and the existing grounding-diagnostic tests. No prior frozen file was edited. Existing approvals, receipts, and GPU authorizations do not apply to this proposal.