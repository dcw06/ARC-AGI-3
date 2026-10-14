# Mechanic Prediction Benchmark v1

Status: CPU construction complete; model execution, independent review, tokenizer lock, and compute authorization are not complete.

## Research Claim

The benchmark asks whether an agent can predict the observable effect of a proposed action that is absent from the supplied action history. For each scenario, the evaluator filters a finite, declared set of mechanisms against acknowledged observations. The answer is `determined` only if every surviving mechanism predicts the same outcome category. If consistent mechanisms disagree, the answer is `not_determined`.

This answer is scoped to the scenario's declared mechanism space. A hidden simulator rule is not evidence the agent received, and this benchmark does not enumerate every real-world explanation.

## Coverage and Evidence

The construction contains 32 synthetic scenarios: two development and two evaluation scenarios in each of eight families.

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

The evaluator oracle and `independent_keys.py` independently derive compatibility and answer status. The build fails if these derivations disagree. There are 16 determinable and 16 underdetermined scenarios. The public request omits scenario/family/split labels, mechanism explanations, answer categories derived from frames, and keys.

Eight shortcuts are scored before any model execution: repeat last outcome, ignore coordinates, assume available means effective, failed dispatch means no change, use final frame only, always no change, always unknown, and apply the most recent outcome everywhere. On the determinable set, their accuracies are 18.75%, 37.5%, 0%, 18.75%, 18.75%, 50%, 0%, and 18.75%, respectively. Always-unknown has 0% accuracy on determinable cases; always-no-change is overconfident on every underdetermined case. The strongest shortcut is wrong on eight determinable cases, all in the current evaluation split.

The strongest shortcut is selected on development data only. `always_no_change` is 100% accurate on development's eight determinable scenarios, then 0% accurate on evaluation's eight determinable scenarios (all eight are wrong). These are construction-time baseline results, not model results. The evaluation split is small and synthetic; it is a milestone check, not a generalization estimate.

## Endpoints and Unit

Primary endpoints are prediction accuracy on determinable scenarios, unsupported certainty on underdetermined scenarios, and evidence-reference correctness. Abstention is reported separately from accuracy. Secondary endpoints include independent perception/grounding accuracy, contradiction revision, valid-output rate, challenge-family results, prompt/completion resource measurements, and latency. No model latency or real model-token count exists yet.

The scenario is the analysis cluster. A paired arm call is not an independent scenario. Repeated diagnostic questions from a scenario must be summarized within that scenario before inference.

## Reused Work and Boundaries

The exact suggested paths `research/feedback_action_v1/` and `research/transition_evidence_v2/` are absent from this transferred workspace. Closest compatible contracts reused by inspection are `research/action_effect_v1/records.py`, `research/action_effect_v1/fixtures.py`, `research/action_effect_history_v1/contract.py`, `research/perception_v1/fixtures.py`, and the existing grounding-diagnostic tests. No prior frozen file was edited. Existing approvals, receipts, and GPU authorizations do not apply to this proposal.