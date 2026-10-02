# Transition evidence v2: design r2 (record format draft; declared mask table frozen; no compute)

**Status.**
- **Where it lives.** Branch `transition-evidence-v2`. Code is in `research/transition_evidence_v2/` and tests are in
  `tests/test_transition_evidence_v2.py`.
- **What is frozen.** The declared mask table (`declared_masks.json`, declared_masks_v1) is frozen. The record format
  is still a draft until the validation fixes below are reviewed.
- **What is unchanged.** Version 1 and WS3 questionnaire v1 are untouched. This decision includes no GPU launch and no
  compute authorization.

**The decision applied in r1.** Use declared masks, under these conditions:
- validation is fixed first, with regressions;
- the initial declared mask covers s5i5 only;
- both views are preserved, and a mask never suppresses anything else;
- migration is kept separate from intervention;
- the mask is tested in a controlled comparison;
- online detection is a separate question.

## Changes in r2 (review of 19c211b)

| Finding | Fix | Regression |
|---|---|---|
| **P2: "exact" verification accepted type-changing edits.** Python equality treats `True == 1` and `6 == 6.0`. Masked flags edited to 0/1 passed both checks; a float action id failed `validate` but passed `verify`. | New type-sensitive `same()` is used for every reconstruction and consistency comparison. Boolean fields and counts must have exactly their types: masked flags, full-frame `differs`/`any`/`final`, frame validity, `available_actions_changed`. The dispatched action must be an integer id in the vocabulary, with integer coordinates only. `verify` and `verify_history` now also run `validate`, so a structurally invalid record never verifies. | 0/1 for each boolean group; float action ids, dispatched and available; type changes in `verify_history` |
| **P2: available-action lists accepted nonexistent ids** (`[8]`, `[999]`). | `ACTION_VOCABULARY = 0..7`, from the repository's ARC diagnostic action schema. Whether a policy may *choose* RESET is a separate rule, enforced by the action validator. Reported lists are retained as reported and refused by `validate`/`verify`, never silently repaired. | `[8]`, `[999]`, `[-1]`, `[1, 8]` and `['1']`, before and after the action; the full `0..7` list passes |
| **P2: the starting state could contradict the environment report.** | For acknowledged transitions, `context.state_before` must equal `environment.reported.state_before`, as the level already had to. | `GAME_OVER` against a reported `NOT_FINISHED` is refused by `validate` and `verify`. A failed dispatch has no report to disagree with. |

**Found while adding the regressions.** A dispatched action id of `1.0` also passed `validate`: neither version 1 nor
r1 checked the dispatched action's types. It is now checked as above. The model's own proposal is retained as produced
and is not type-checked.

**Checks.**
- 31 v2 tests and v1's 16 pass.
- All 144 archived development transitions validate and verify.
- The two deliberate mask faults each fail 8 of the 31 tests.

## Changes in r1

| Condition | What was done |
|---|---|
| **Fix validation first** | r0's `validate` accepted 15 of 16 probed contradictions and crashed on the 16th. It now refuses all of them. 31 regression cases (19 context and action, 12 masked view) cover: malformed or untyped context fields; malformed, duplicated, unsorted or bool action lists; levels that contradict the environment's report; `reported` after an unobserved action; masked counts that do not add up to the full-frame count; `differs_outside` against its count; summaries that contradict the masked frames; a mask for another frame shape; truncated or shifted frames; and extra fields. |
| A record alone cannot reveal a consistent forgery | For example, two changed cells moved from outside to inside with the summary recomputed. New `verify(record, raw, mask)` and `verify_history(records, raws, masks)` rebuild from raw evidence and require an exact match. A test shows such a forgery passes `validate` and fails `verify`. |
| **Initial mask: s5i5 only, frozen** | `declared_masks.json` is pinned by its SHA-256 in `masks.py` and refused if edited (tested). Its contents: game `s5i5-18d95033`; frame 64×64; one rectangle, row 63, x 49–63; source archive `evidence/action-effect-history-v1-complete.zip` with its locked hash (cross-checked against the lock); provenance `declared`. It is described as **a region selected from development evidence, not established as irrelevant to the task**. Games are matched on their full id. **ar25 is unmasked:** nothing changed there. **wa30 is unmasked:** its bottom-edge changes are ambiguous. |
| **Both views preserved** | Every record keeps the full-frame measurements, the outside-region measurements and the inside-region counts. |
| **Never suppress** | A test shows that with and without the mask, the record's dispatch, environment events, progress, context, available actions, full measurements and observations are identical. This holds even when the only visible change is inside the region while a level completes, the state becomes WIN and the available actions change. Failed and unknown dispatches have no masked view. |
| Available-action changes | New `environment.reported.available_actions_changed` is measured when both sides were retained, so an action-set change is a reported fact of its own. |
| **Wording** | The masked reason reads "no observed change outside the declared region; changes inside it are set aside, not denied, and this does not establish that the action had no effect" (tested). The record never names a cause for the region. |

**Checks.**
- 25 v2 tests and v1's 16 pass.
- All 144 archived development transitions validate and match exactly what their raw evidence rebuilds.
- Two deliberate faults in the mask test (ignore the rectangles; swap x and y) each fail 8 of the 25 tests.

## 1. What the real development transitions show

These figures come from the 144 archived transitions of action-effect-history v1: 3 development games, 4 episodes
each, 1 returned frame per step.

| Game | Unmasked visual effect | Where the changes are | Declared region |
|---|---|---|---|
| ar25 | 48 `no_observed_change` | none | none |
| s5i5 | 48 `final_frame_differs` | every changed cell is in row 63, x 49–63: 1–2 cells per action, restored at each new episode | row 63, x 49–63 |
| wa30 | 45 differ, 3 unchanged | a moving block of 24–33 cells; 4 cells at row 63, x 60–63 also changed 16 times | none (ambiguous) |

**What the s5i5 region shows.** With the region declared, all 48 s5i5 transitions read "no observed change outside the
declared region", and the region changed in all 48.

**Not an independent validation.** The region was selected from these same 48 transitions. They are development
evidence for the declaration, not a test of it.

## 2. The record

A version 2 record is version 1's record, **extended, never altered**. `to_v1(record)` returns exactly version 1's
record on all 90 frozen v1 fixtures, with and without a mask. Version 1's checks run unchanged on the contained
record.

| Addition | Content |
|---|---|
| `identity.record_id` | `<episode_id>#<action_index>` |
| `context` | `levels_completed_before`, `state_before`, `available_actions_before`, from the observation **before** the action, so they exist for failed and unknown dispatches too |
| `environment.reported.available_actions_after`, `available_actions_changed` | For acknowledged actions only. Nothing after a failed or unknown action was observed, so `reported` stays null. |
| `masked` | Present only when a mask is supplied and applies; otherwise `unavailable` with a reason. It holds the mask itself, per-frame `changed_outside`/`changed_inside`/`differs_outside`, the outside summaries, and `mask_region_changed`. |

**Available actions are never assumed.** If an observation omits them, the field is `absent` with a reason.

## 3. Migration is separate from intervention

| A track may | Without a new experiment version? |
|---|---|
| Adopt `record_id`, `context` (including the level for failed and unknown actions) and the available actions | **Yes.** These are reported facts the producer already had; using them changes no treatment. |
| Compute the masked view and **report** it alongside full-frame metrics | **Yes**, as long as it does not reach the model or the policy. |
| Put masked measurements into a **prompt, a memory or a stagnation detector** | **No.** That changes what the agent sees or does. It is a new experiment version, with the mask named in its frozen protocol and labelled as declared. |

## 4. Controlled comparison (protocol outline; nothing scheduled or authorized)

**The question.** Does declared-mask assistance change behaviour on s5i5, with everything else fixed?

- **Arms.**
  - **Unmasked:** the full-frame view only.
  - **Declared-mask-assisted:** the same, plus the masked view where the track's experiment uses evidence (prompt,
    memory or detector).
  - Same model, decoding, prompts apart from the masked fields, games, seeds, horizons and budgets.
- **Games.** s5i5 is the only game where the arms differ. ar25 and wa30 are run in both arms as controls where the
  arms must behave identically: any difference there is variance or a defect, not a mask effect.
- **Reported separately, never combined into one score:**
  - **repetition:** exact repeats after no observed change in the same state, full-frame and outside-region,
    reported side by side;
  - **detector errors:** Track 3's false triggers and misses, under each fingerprint;
  - **reliability:** invalid outputs, dispatch failures, unknown outcomes and interruptions;
  - **levels completed.**
- **Evidence limits.** The 48 archived transitions are development evidence, not a validation set. Run-to-run variance
  must be measured, for example with a repeated unmasked episode. Any claim is limited to s5i5 under this declared
  region.

## 5. Online detection is a separate question

**The question.** Can an agent identify regions worth tracking separately, from earlier observations only, without
excluding task-relevant changes?

- **Status.** It is not built here. The provenance kind `detected_online` is reserved for it.
- **Benchmark requirements.**
  - **Hard cases:** moving objects near borders (wa30's block is the archived example); stationary objects that later
    become interactive; transient animation; and resource indicators.
  - **Abstention** is a permitted answer. When the detector is uncertain, the consumer uses the full-frame view.
  - **Errors** are scored asymmetrically: excluding a task-relevant change is the costly error.
- **Relation to the format.** Neither declared nor detected masks change this record format.

## 6. Not included

| Item | Reason |
|---|---|
| Changed-cell lists | Tracks 1 and 4 recompute them. They can add up to 4,096 cells per frame to every record. |
| Object identities | They belong to perception. |
| Masked continuity | Not needed by any consumer yet. |
| An online detector | See §5. |
