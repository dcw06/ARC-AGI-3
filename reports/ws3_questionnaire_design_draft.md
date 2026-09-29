# Workstream 3: factual transition questionnaire — design draft r0 (for review; nothing frozen; no compute)

**Status.** A draft built and tested offline on branch `ws3-action-effects`:
`research/transition_evidence_v1/questionnaire.py`, and `tests/test_ws3_questionnaire_draft.py` (9 tests), which
passes alongside the 16 transition tests. No model has been called. Nothing is frozen: the thresholds, sizes and the
experiment choice below are proposals for review.

## Question

Before asking the model why something happened, can it read **what** happened after an action? That means keeping
these apart:
- dispatch;
- observation availability;
- visual change;
- reported environment events;
- progress;

and not asserting causes the evidence does not establish.

**Out of scope.**
- Selecting which past actions qualify: Workstream 1 covers that.
- Hypotheses and predictions: Phase D.
- Action selection: Phase E.

## Experiment choice (one primary comparison)

| Option | Reference | Candidate | What success would mean |
|---|---|---|---|
| **B: computed assistance (recommended)** | `raw_evidence`: dispatch status and reason, the frame before the action, the returned frames exactly as returned (including invalid ones), and environment fields before and after | `raw_plus_computed_record`: the same plus one field, `computed_measurements`, derived from the transition_evidence_v1 record and labelled "computed by a deterministic tool" | The computed record helps the model read transitions. That is **tool assistance**, not unaided frame reading. |
| A: presentation of the same computed facts | the computed facts in one form (e.g. compact fields) | the same facts in another form (e.g. plain phrases) | A more usable presentation. |

**Why B.**
- The live agent receives raw frames, so the first open question is whether computed transition evidence helps at
  all.
- The replay found the model claiming a frame change that raw frames contradict.
- In Workstream 1, v2 showed the model reads computed per-entry fields fairly well.

A presentation comparison (A) is a natural follow-up if B shows the computed record helps. The two changes are not
combined in the first comparison.

## Families (10, all factual; mechanically keyed)

| Family | Answers | Error pattern it isolates |
|---|---|---|
| `dispatch_status` | acknowledged / failed / outcome_unknown | treating every action as delivered |
| `observation_availability` | complete / partial / missing / not_applicable | treating failed or unknown dispatches as complete observations |
| `any_frame_differs` | yes / no / cannot_tell | final-frame-only reading (misses transients); failed or unknown read as no change |
| `final_equals_initial` | yes / no / cannot_tell | failed or unknown read as unchanged |
| `count_defined` | defined / undefined_dimensions_differ / undefined_no_valid_final_frame | inventing a count where none is defined |
| `level_completion_reported` | yes / no / not_observed | change read as level completion |
| `progress_status` | confirmed / unknown | change read as progress; absence of a report read as no progress |
| `claim_descriptive` | supported / contradicted / not_established | claims about execution and change, including failed or unknown |
| `claim_progress` | supported / not_established | "the environment reported progress" when only pixels changed |
| `claim_causal` | contradicted / not_established | "this action caused the change": a sequence alone never establishes a cause; the claim is contradicted only when no change occurred |

There is no "was this action good?" question.

## Cases

**Source and partitions.**
- Single transitions are drawn from fresh fixture sequences: the same 18 construction families as the transition
  fixtures, with new seeds `ws3-questionnaire-development` and `ws3-questionnaire-withheld`.
- A whole sequence stays in one partition. The raw evidence has opaque identifiers and no fixture labels (tested).
- **Frames:** synthetic 10–16 cell grids. The archived real frames (64 × 64, AEH v1 and R8) would be a descriptive
  transfer check only: previously exposed, and without intermediate frames.

**Three key derivations must agree, or the build fails:**
1. the transition record;
2. the import-free reference;
3. the fixture construction.

**Balanced selection.**
- Each family's questions are drawn so every answer key has the same cap. Claims are balanced per claim and key.
- Each key is filled round-robin across strata of (visual effect, dispatch status), so transients, change without
  progress, and failed or unknown dispatches are all represented.

**Withheld coverage** (per condition): 812 questions over 323 transitions and 189 sequences.

| Family | n | Best predeclared shortcut (accuracy) | Questions where it is wrong |
|---|---|---|---|
| dispatch_status | 80 | always acknowledged (0.40) | 48 |
| observation_availability | 112 | failed or unknown as complete (0.64) | 40 |
| any_frame_differs | 96 | failed or unknown as no change (0.78) | 21 |
| final_equals_initial | 96 | failed or unknown as no change (0.78) | 21 |
| count_defined | 76 | always defined (0.42) | 44 |
| level_completion_reported | 88 | change means progress (0.73) | 24 |
| progress_status | 64 | change means progress (0.62) | 24 |
| claim_descriptive | 72 | failed or unknown as no change (0.86) | 10 |
| claim_progress | 64 | change means progress (0.81) | 12 |
| claim_causal | 64 | sequence as cause (0.78) | 14 |

**The predeclared shortcuts** include every trivial baseline the plan names:
- always unknown / cannot tell / not established;
- any change means progress;
- a failed or unknown dispatch read as no change;
- final frame only;
- a sequence taken as a cause;
- always acknowledged, complete or defined.

`undefined_dimensions_differ` is limited to 12 questions by the construction pool. It would be enlarged before
freezing if the review requires it.

## Metrics (proposed)

**Per family and condition:**
- accuracy;
- accuracy where the best shortcut is wrong;
- invalid and missing responses;
- paired improvements and regressions;
- a context-level (sequence) bootstrap.

**Error-cost metrics, reported separately.** A single accuracy number hides these:
- **false visible-change claims:** answering "yes" or "supported" where no valid frame differs;
- **false no-change claims:** "no" or "yes, unchanged" where the evidence cannot decide, especially after failed or
  unknown dispatches;
- **false progress claims:** "confirmed", "yes" or "supported" without a reported signal;
- **unsupported causal assertions:** any "supported" on `claim_causal`;
- **unknown-outcome handling:** accuracy on unknown-outcome cases.

Also reported: tokens and latency. The tool-processing cost of the candidate is negligible, since it is
deterministic and CPU-only.

## Decision rules — decisions for reviewers (not reused from Workstream 1 without checking)

1. **Criterion.** Proposed: at least 0.90 accuracy overall and at least 0.90 on best-shortcut-disagreement
   questions, with at least 10 of them, per family. Both passes must be correct. This matches Workstream 1, but here
   the costs are asymmetric (below).
2. **Asymmetric error costs.** Proposed hard limits under the candidate:
   - unsupported causal assertions at most 2% of `claim_causal`;
   - false progress claims at most 2% of the progress families.

   Should these gate the verdict, or only be reported?
3. **Coverage.** Minimum questions and disagreement items per family, fixed at freeze. Should `count_defined`'s
   rare key be enlarged?
4. **Experiment.** B, as recommended, or A?
5. **Repetition.** Two withheld passes (both-correct scoring), as in Workstream 1. Development is asked once.
6. **Transfer.** Include the archived real frames as a descriptive group, or not?

## Workload and budget (draft estimate)

- **Calls:** about 3,578 scheduled: withheld 812 × 2 conditions × 2 passes, plus development 165 × 2 conditions.
- **Prompt tokens:** about 2.7 M, estimated from character counts. The largest prompt is about 1,600 tokens.
- **Runtime:** well inside one attempt at v2's measured rates. Exact token counts, the runtime scenarios and the
  budget proposal come at freeze, from the pinned tokenizer.
- **Runner:** the Workstream 1 supervised runner would be reused by derivation, as v3 was, and no GPU run happens
  before separate approval.

## Next

Review this draft. Then freeze it: final families and thresholds, the pinned-token audit, the protocol, and the
derived runner and GPU-disabled package. That is Milestone D.
