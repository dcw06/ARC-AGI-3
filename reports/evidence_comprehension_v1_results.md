# Evidence comprehension v1: live results

Attempt `ecv1-4458251ee9aa4e1b9ca39844a1c3a70b`, from review package r3 (lock `fa425fd0…c051`), on
Kaggle (version 1, one RTX Pro 6000).
- **Independent evaluation:** `reports/evidence_comprehension_v1_live_evaluation.json`.
- **Archive:** `evidence/evidence-comprehension-v1-live.tar.xz` (1,348 files, SHA-256
  `82ff8481…aee4`), locked by `reports/evidence_comprehension_v1_live_archive.json`. Replaying it
  reproduces the evaluation exactly.

## Technical result

| Check | Result |
|---|---|
| Technically complete (independent evaluator, live mode) | **yes**: no lifecycle errors, run evidence verified, no call errors |
| Calls | 1,308 of 1,308 answered (654 per pass); 0 invalid, 0 missing, 0 timed out |
| Prefix caching | Off: launched with `--no-enable-prefix-caching`. At the final check the server had processed 4,130,013 prompt tokens with 0 prefix-cache queries and 0 hits. |
| Cancellations | None needed. The slowest call took 1.8 s, and the mean was 0.26 s. |
| Two-pass agreement | **Every answer identical** between the passes, in every group |
| Time | Model startup 416 s; questions 363 s; first cell 916 s against the 3,300 s internal limit. Account GPU use was 0.26 h (about 936 s) of the 3,600 s authorized. |

## Gate results (pre-registered; both-correct accuracy)

| Family | Correct | Accuracy | Best shortcut | Accuracy where the best shortcut is wrong | Label |
|---|---|---|---|---|---|
| available_actions | 42 / 44 | 0.955 | 0.159 | 0.946 (n=37) | **criterion_met** |
| coordinate_actions | 25 / 44 | 0.568 | 0.523 | 0.095 (n=21) | **below_accuracy_floor** |
| recall_action | 100 / 107 | 0.935 | 0.533 | 0.860 (n=50) | inconclusive |
| outcome_class | 91 / 105 | 0.867 | 0.381 | 0.800 (n=65) | inconclusive |
| observed_effect | 98 / 110 | 0.891 | 0.664 | 0.973 (n=37) | inconclusive |
| tried_unchanged | 15 / 44 | 0.341 | 0.659 | 0.133 (n=15) | **below_accuracy_floor** |

These labels describe this diagnostic's criterion under this prompt. They do not describe general
comprehension.

## What the errors show (descriptive)

- **coordinate_actions:** all 19 errors came when ACTION6 was **not** available. The key was `[]`,
  and every time the model answered `[6]`. It reported which action takes coordinates *in general*
  instead of which available action does. Whether that comes from the control text ("ACTION6 is the
  only action that takes arguments") or from a failure to read `legal_actions` in this question, this
  diagnostic cannot say.
- **tried_unchanged:** 29 errors. In 16 the model omitted actions that belonged, in 11 it added
  actions that did not, and in 2 it did both. This is the question closest to step 3 ("what have I
  already tried here without effect"), and it is the weakest result.
- **outcome_class:** 8 of the 14 errors read a **changed-then-returned** (transient) entry as
  no change. The remaining errors are scattered, mostly around steps that are not shown.
- **observed_effect:** mostly the same transient confusion, plus an unknown outcome read as not
  observed. Accuracy on the shortcut-disagreement questions (0.973) was higher than overall accuracy
  (0.891).
- **recall_action:** mostly correct. The shortfall is on questions where the latest entry is not
  the answer.

## Descriptive comparisons (not gated)

- **Grids (matched archived observations, with versus without grids; 66 questions each):** no
  consistent direction. Answers differed on 7 questions: 3 favoured the grids and 4 the no-grid
  versions. The samples are small, and no cause is attributed.
- **Legacy versus corrected history description (34 each):** the corrected description got 2
  questions right that the legacy one did not (one recall, one observed_effect). The legacy
  description never did better. Small sample.
- **Determinism:** with prefix caching off, both passes produced byte-identical answers. The earlier
  action-effect-history run, with caching on, had byte-identical requests answered differently. This
  is consistent with caching contributing to that variance, but this run was not designed to test
  it.

## How the result is used (per the protocol)

The protocol's condition for proceeding to step 3 is that observed_effect, outcome_class and
tried_unchanged all meet the criterion. **That condition is not met:**
- tried_unchanged is below the floor;
- outcome_class and observed_effect are inconclusive.

Coordinate availability is also below the floor. So the next step is to investigate how these
families are read, not to start evidence-guided action selection. The protocol names three candidate
causes, and this diagnostic cannot choose between them:
- the evidence presentation;
- the diagnostic prompt;
- the model's capability.

The error patterns point at specific targets:
- transient changes being read as no change;
- availability not being intersected with the control rules;
- the multi-step "still-current frame" reasoning behind tried_unchanged.

Scope: development contexts and a scripted question set only. This says nothing about
generalization or solving.
