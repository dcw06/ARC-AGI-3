# Track 2 evidence preservation stress results

Development diagnostics using deterministic writers and scripted readers on synthetic transitions. These results measure evidence availability and component checks, not model memory or game solving.

## Construction and scoring

48 continuous cases cover eight families, two seeded constructions each, and distractor delays of 0, 8 and 24 transitions. The extra hypothesis-pending family checks that repeated support remains a hypothesis before the contradiction family supplies a later correction.

The existing Track 2 faithful writer, independent fidelity checker, Stage 1 factual scorer, state-keyed retrieval and renderings are reused unchanged. Construction answer keys are explicitly declared and verified against the independent evaluator. The additional hypothesis-status task is scored separately; it does not alter the original Stage 1 endpoint.

Recent history defines the common token ceiling using its last six transitions. Structured memory and retrieved records must fit that same ceiling; their actual token counts can be lower. Selection uses current state and recency, never the question. All prompt counts use the four hash-verified pinned tokenizer assets. Full history and unbounded memory are diagnostic references only.

Scripted readers parse the actual rendered evidence, not hidden records or answer keys. Factual answers also agree with the existing package oracle. Retired entries, hypotheses and indeterminate dispatches cannot become exact-state factual observations.

## Factual recall and hypothesis diagnosis

These tasks are separate endpoints. The family and delay tables below combine them only as descriptive counts; they do not define an advancement criterion.

| Task | Arm | Correct / questions | Selection loss | Reader errors |
| --- | --- | --- | --- | --- |
| hypothesis_status | recent_raw | 4/12 | 8 | 0 |
| hypothesis_status | state_keyed_raw | 8/12 | 4 | 0 |
| hypothesis_status | memory | 9/12 | 3 | 0 |
| recall | recent_raw | 44/96 | 52 | 0 |
| recall | state_keyed_raw | 76/96 | 20 | 0 |
| recall | memory | 62/96 | 34 | 0 |

## Results by family

| Family | Arm | Correct / questions | Writer store loss | Selection loss | Reader errors |
| --- | --- | --- | --- | --- | --- |
| buried_evidence | recent_raw | 4/12 | 0 | 8 | 0 |
| buried_evidence | state_keyed_raw | 8/12 | 0 | 4 | 0 |
| buried_evidence | memory | 6/12 | 0 | 6 | 0 |
| contradicted_hypothesis | recent_raw | 8/24 | 0 | 16 | 0 |
| contradicted_hypothesis | state_keyed_raw | 12/24 | 0 | 12 | 0 |
| contradicted_hypothesis | memory | 9/24 | 0 | 15 | 0 |
| coordinates | recent_raw | 4/12 | 0 | 8 | 0 |
| coordinates | state_keyed_raw | 12/12 | 0 | 0 | 0 |
| coordinates | memory | 12/12 | 0 | 0 | 0 |
| hypothesis_pending | recent_raw | 6/18 | 0 | 12 | 0 |
| hypothesis_pending | state_keyed_raw | 14/18 | 0 | 4 | 0 |
| hypothesis_pending | memory | 12/18 | 0 | 6 | 0 |
| level_boundary | recent_raw | 8/12 | 0 | 4 | 0 |
| level_boundary | state_keyed_raw | 8/12 | 0 | 4 | 0 |
| level_boundary | memory | 6/12 | 0 | 6 | 0 |
| reset_boundary | recent_raw | 2/6 | 0 | 4 | 0 |
| reset_boundary | state_keyed_raw | 6/6 | 0 | 0 | 0 |
| reset_boundary | memory | 4/6 | 0 | 2 | 0 |
| transient_return | recent_raw | 2/6 | 0 | 4 | 0 |
| transient_return | state_keyed_raw | 6/6 | 0 | 0 | 0 |
| transient_return | memory | 4/6 | 0 | 2 | 0 |
| unobserved_dispatch | recent_raw | 14/18 | 0 | 4 | 0 |
| unobserved_dispatch | state_keyed_raw | 18/18 | 0 | 0 | 0 |
| unobserved_dispatch | memory | 18/18 | 0 | 0 | 0 |

## Results by distractor delay

| Delay | Arm | Correct / questions | Writer store loss | Selection loss | Reader errors |
| --- | --- | --- | --- | --- | --- |
| 0 | recent_raw | 36/36 | 0 | 0 | 0 |
| 0 | state_keyed_raw | 36/36 | 0 | 0 | 0 |
| 0 | memory | 22/36 | 0 | 14 | 0 |
| 8 | recent_raw | 6/36 | 0 | 30 | 0 |
| 8 | state_keyed_raw | 24/36 | 0 | 12 | 0 |
| 8 | memory | 25/36 | 0 | 11 | 0 |
| 24 | recent_raw | 6/36 | 0 | 30 | 0 |
| 24 | state_keyed_raw | 24/36 | 0 | 12 | 0 |
| 24 | memory | 24/36 | 0 | 12 | 0 |

## Where essential evidence is lost

The per-question rows in `results.json` name missing relevant steps and compare full-history truth, full-store truth and selected-package truth. A missing step alone is not an answer failure: another retained observation or a corrected hypothesis may provide the same information.

Recent history drops earlier observations once they leave the six-transition window. Current-state retrieval can recover earlier current-state records, but prioritizes them over evidence about a different historical state. Memory selection prioritizes current-state observations ahead of level hypotheses, so a corrected hypothesis or non-current observation may remain intact in the full store yet be omitted under the token ceiling. Selection stops at the first priority item that cannot fit, as the original protocol specifies.

For example, in `development-contradicted_hypothesis-0-d8`, both memory and retrieved-record packages retain step 0 but omit steps 1 and 2. Step 2 is the counterexample. The full-history and full-store verdict is contradicted, while the selected text supports only hypothesis_only. The reader therefore loses the correction despite a faithful writer. In `development-buried_evidence-0-d24`, the per-question step trace distinguishes retrieval of current-state evidence from loss of evidence about the historical non-current state.

Failed and unknown dispatches provide no visual fact. Their raw records retain distinct dispatch statuses, while the faithful memory store writes no factual observation for either. Correctly answering no_evidence does not prove that the memory retained the distinction between rejection and an uncertain outcome; this task does not score recall of dispatch-status metadata.

A temporary change is keyed as changed_then_returned, never no_observed_change. Reset retires segment conclusions while preserving historical exact-state observations. Level numbers remain part of the key even when the frame is identical across a level boundary.

## Attribution and controls

Writer fidelity is audited before selection. Writer-store loss or distortion is measured using the unbounded memory answer; integrity faults are recorded independently. Selection loss means the selected text supports a different answer from its full source. Reader error means the output does not match the evidence actually supplied. These flags can coexist. An incorrect full-history answer alone never identifies the failing component.

Faithful stores passing the original fidelity evaluator: 48/48. Writer runs with rejected or invalid operations: 0. Overclaiming negative-control stores with detected integrity faults: 36. Tests also isolate a lossy writer, bad selection and a deliberately wrong reader, including simultaneous store and reader errors.

## Leakage and request preparation

Fixture labels, construction logs, expected answers and component diagnoses stay outside requests. Requests contain only the unchanged prompt frame, rendered selected evidence and the question. Question wording and response limits are identical across arms. Requests have opaque IDs, and truth/package keys live in the evaluator-only sidecar. Leakage tests poison evaluator metadata and confirm that the resulting requests do not change.

`requests.jsonl` contains 324 inert request drafts. The manifest binds their hash, fixture and evaluator-key hashes, source hashes, model revision and tokenizer hashes. No submission, network client, authorization or GPU execution path is included. These exposed development cases are not eligible as fresh evaluation cases for a future confirmatory run.

## Reproduction

```bash
python -m research.evidence_memory_stress_v1.build --check
python -m unittest -v tests.test_evidence_memory_stress_v1
```

The builder verifies every retained output in memory with `--check`. Omitting that flag regenerates only this additive development package. Original notebooks, locks, approvals, reservations and historical evidence remain unchanged.
