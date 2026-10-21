# Action-effect choice v2: why the feedback fields remained unknown

The retained requests contained enough information to answer both retrospective
fields in all four second-phase calls. The model nevertheless abstained. This
audit identifies an input-use failure on these exposed cases; it cannot identify
the model's internal reason or establish which intervention will fix it.

| Game, both arms | Original selected forecast | Actual changed cells | Required observed-change answer | Required forecast check | Both recorded answers |
| --- | --- | --- | --- | --- | --- |
| ls20 | 5–64 cells | 2 | yes | mismatched | unknown |
| s5i5 | 1–4 cells | 1 | yes | matched | unknown |

Each row represents two calls, one per arm. The frozen metric counts every
changed cell, including interface changes. It does not ask whether an object
moved or whether the action made progress. The numerical observations alone
determine these retrospective answers.

## What the audit established

| Possible explanation | Evidence and conclusion |
| --- | --- |
| Missing previous outcome | Excluded for these calls: the last summary row contains the exact changed-cell count. Its before/after images also match the actual executed transition. |
| Wrong action or forecast attached | Excluded: the summary action, executed action and original selected candidate match. The original forecast is unchanged. |
| Restored history mistaken for the study action by the host | Excluded: all second calls identify study index 1, game step 3 and the immediately preceding study action at historical step 2. The matching summary row is present. Whether the model used that linkage remains unknown. |
| Summary arithmetic or evaluator error | The audit independently counted the retained grid differences, matched the displayed PNGs and summary counts, and recomputed both retrospective labels. They agree with the evaluator. |
| Schema forces unknown | Excluded at the request-contract level: the schema allows yes/no/unknown and matched/mismatched/unknown. The correct determinate labels are allowed. This audit does not rerun the decoder or inference. |
| Response token exhaustion | Excluded: these replies used 45 or 47 of 256 completion tokens and ended normally with `stop`. |
| Prompt-token ceiling | No ceiling overrun: these requests used 2,506–3,040 of 8,192 allowed prompt tokens, independently recounted previously. |
| Extra compare-and-review instruction resolves it | It did not resolve it in these calls: both arms produced identical parsed replies at corresponding phases. No broader treatment-effect claim follows. |

The input already supplies a computed pixel-change summary. This failure
therefore does not require a hypothesis that the model could not visually
detect a one-cell change: it could have used the supplied count instead.

## Plausible mechanisms, still untested

The model receives six images, object metadata, two historical transitions,
candidate forecasts, a previous selected forecast and separate study-phase
metadata in one user message. Both history records are labelled historical,
although the latest is now the executed study action. The relevant facts must
be linked across these fields. The prompt also broadly permits `unknown` and
does not give a short extraction-and-comparison procedure. These are plausible
interface burdens, not established causes. Generation had thinking disabled;
there is no retained reasoning trace establishing why the answers were chosen.

## Recommended successor preparation

Keep the completed pilot and its scoring unchanged. Do not spend another full
gameplay budget merely to establish that the old four-field format is accepted.
The remaining question is whether making verified executed feedback explicit
helps the policy use it.

| Step | Proposed work | What it would establish |
| --- | --- | --- |
| 1. Compute an executed-feedback receipt on CPU | Bind the exact preceding study event, full action, immutable forecast and actual before/after grids. Derive changed count, count category, visible-change status and matched/mismatched status. | Deterministic bookkeeping the host can verify without asking the VLM to repeat it. |
| 2. Check boundaries and provenance | Cover 0, 1, 4, 5, 64 and 65 changed cells; an original unknown forecast; missing evidence; repeated identical actions at different event indices; and mismatched action/forecast identities. Refuse inconsistent bindings. | Correct arithmetic and event identity without treating unavailable evidence as known. |
| 3. Freeze a small successor comparison | Compare the existing factual summary with a clearly named, verified last-study-action feedback block. Keep model, images, candidate actions, generation settings and future outcome withholding fixed. Treat it as an interface-package comparison, including added labels/tokens. | Whether explicit feedback presentation changes subsequent policy use on exposed development cases. |
| 4. Evaluate future decisions separately | Measure new forecasts against independently replayed reference branches and report subsequent choices. Do not award feedback-reading credit for labels the host itself supplied. | Policy behavior after verified feedback, separated from supplied bookkeeping. |

The receipt may use only the action already executed and its observed result.
It must never include an unexecuted candidate's reference outcome, future frame,
game rule, usefulness label or recommended next action. A nonzero pixel change
still does not imply progress. An original unknown forecast remains unknown;
it must not be rewritten after the result arrives. Missing or contradictory
records must be surfaced rather than guessed. Future candidate predictions
must continue to permit uncertainty.

If the research goal is specifically unaided feedback reading, use a separate
small reader probe that asks the model to extract and compare the original
facts without supplying the derived labels. That probe measures a different
question from a planner assisted by verified host feedback. Neither a receipt
nor an explicit-label interface would demonstrate that the model learned game
rules or improved object recognition.

These are preparation recommendations. No successor runtime, prompt, schema,
protocol or source lock was changed by this diagnosis. No new compute or launch
is authorized by the consumed pilot attempt.

## Evidence and preservation

The read-only audit checked all four second-phase request/response pairs against
the prior independent evaluation and its exact run inventory. It validated
request hashes, complete HTTP reply binding, explicit study phase, action and
forecast identities, summary counts, previous before/after PNGs and the current
image. All 22 files in the evaluated evidence directory were unchanged afterward.
It made zero provider calls, model generations, GPU launches or game dispatches.

| Binding | SHA256 |
| --- | --- |
| Private review lock | `81bd5bf4b1c831a1ff5b5eb9e372966ea6e2b04fc48ddadf30d70dc64a63e035` |
| Prior independent evaluation | `17c31034505edb9d252df1eadaf0cb5f0db3bf8f111b4e7f0099e5479a056fc2` |
| Evaluated run inventory | `236c9db32578db58d4ed9664cb484fcf22efd6808dfd014e348a304fc5b65484` |
| Read-only diagnosis helper | `be64d3cc4c63a9ba65ad785810684c5906a48b69b429f57b4de58b09f4875c2d` |
| Diagnosis receipt | `66f72794acf977fd2765bfcb440fcb8be581b18917536b9262be649db94cdc25` |

The helper and detailed receipt remain in the private git-ignored workspace at
`.cache/github-review/action-effect-choice-live-v2-2026-10-20/diagnose_feedback.py`
and `feedback-diagnosis-r1/diagnosis.json`. The
[completed pilot report](action_effect_choice_v2_attempt1_results_2026-10-20.md)
retains the original technical and descriptive results.
