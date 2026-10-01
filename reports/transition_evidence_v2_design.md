# Transition evidence v2: design draft r0 (not frozen; no compute)

**Status.** Draft for review, on branch `transition-evidence-v2` (from `5ff575b`). Code is in
`research/transition_evidence_v2/` and tests are in `tests/test_transition_evidence_v2.py`. Version 1 is not edited.
WS3 questionnaire v1 stays on version 1.

**Why.** Three of the four research tracks independently asked for the same additions:

| Need | Asked by | Why version 1 falls short |
|---|---|---|
| Set aside a region that changes on every action (a step bar or counter) | Tracks 1, 2 and 3 | On s5i5 every action changes the frame, so "same state" never repeats and "no observed change" never occurs. Track 3's detector misses every loop under a counter. |
| A stable record identifier | Track 2 | Each track built its own `episode_id#action_index`. |
| The level a failed or unknown action started from | Track 2 | Version 1 records no environment observation for these, so the level had to be carried forward by each consumer. |
| The available actions at each step | Track 3 | The producer receives them, but version 1 drops them. Proposed tests fall back to actions already seen. |

## 1. What the real development transitions show

These figures come from the 144 archived transitions of action-effect-history v1: 3 development games, 4 episodes
each, 1 returned frame per step.

| Game | Transitions | Unmasked visual effect | Where the changes are |
|---|---|---|---|
| ar25 | 48 | 48 `no_observed_change` | nothing changed at all |
| s5i5 | 48 | 48 `final_frame_differs` | **every** changed cell is in row 63, x 49–63. It is a bar that loses 1–2 cells per action and refills at each new episode. The playfield never changed. |
| wa30 | 48 | 45 differ, 3 unchanged | a moving block of 24–33 cells. 4 cells at row 63, x 60–63 also changed 16 times. Whether that is a second bar is not established. |

**What this means.** On s5i5, version 1 correctly reports that every frame differed. But a consumer asking "did my
click do anything to the playfield?" gets "yes" 48 times, when the answer was "nothing observed" every time.

**What it cannot show.** No cell changed on every action, so "set aside cells that always change" would not find the
s5i5 bar. It is a region whose cells change once each, in order.

## 2. The record

A version 2 record is version 1's record, **extended, never altered**.
- **How it is built.** `build` calls version 1's `build`, and `history` calls version 1's `history`, then each adds
  fields.
- **The guarantee.** `to_v1(record)` returns exactly version 1's record. This is tested on all 90 frozen v1 fixtures,
  with and without a mask.
- **Version 1's checks still apply.** `validate` runs them unchanged on the contained record.

| Addition | Content |
|---|---|
| `identity.record_id` | `<episode_id>#<action_index>` |
| `context` | `levels_completed_before`, `state_before`, `available_actions_before`. These are taken from the observation **before** the action, so they exist for failed and unknown dispatches too. |
| `environment.reported.available_actions_after` | For acknowledged actions only. Nothing after a failed or unknown action was observed, so `reported` stays null, as in version 1. |
| `masked` | The masked view (§3). It is `unavailable` with a reason when no mask is supplied, the result was not observed, or the mask is for another frame shape. |

**Available actions are never assumed.** If an observation omits them, the field is `absent` with a reason.

**Model statements.** `model_statement` additionally carries `about_record_id`.

## 3. The masked view

A mask is a list of inclusive rectangles for one frame shape, plus its provenance (`kind`, `source`, `basis`). The
masked view repeats version 1's rules on the cells **outside** the mask:
- per-frame outside and inside changed-cell counts;
- `any_returned_frame_differs_outside`, `final_frame_equals_pre_outside` and `visual_effect_outside`;
- `mask_region_changed`.

| Rule | Why |
|---|---|
| The unmasked measurements stay the record's primary measurements. | A mask is an interpretation of where to look. The full observation is never replaced. |
| Changes inside the mask are counted, not dropped. `no_observed_change` outside the mask says the inside changes are *set aside, not denied*. | A consumer can always see that the masked region moved. |
| A mask cannot create a change. If the unmasked effect is `no_observed_change`, the masked one must be too (validated). | The masked view can only ever say less changed. |
| A frame of another shape still *differs*. Its outside/inside counts are unavailable. | This is version 1's dimension-change rule. |
| Invalid frames leave the outside result undecided, as in version 1. | A missing observation never becomes a zero count. |
| The record never says *why* a region is masked. A test forbids "counter", "timer", "HUD", "score" and "budget" in it. | The record describes observations, not causes. |

**Checks.**
- Outside/inside counts agree with an independent brute-force count on 300 random frames and masks.
- Two deliberate faults in the mask test (ignore the rectangles; swap x and y) each fail 5 of the 16 tests.
- On the archive with a declared s5i5 mask, all 48 s5i5 transitions read `no_observed_change` outside the mask, and
  `mask_region_changed` is true in all 48. That mask was declared from the same transitions, so this describes what
  the view reports; it does not validate the mask.

## 4. The open decision: where masks come from

The record accepts a mask; it does not choose one. There are two sources, and they serve different purposes:

| | Declared mask | Online-detected mask |
|---|---|---|
| What it is | Rectangles a person or producer writes for a game, from stated development evidence | A detector proposes rectangles from **earlier transitions of the same episode only** |
| Works on an unseen game | No | Yes, if the detector does |
| Risk | It is game-specific knowledge. Used in an experiment, it must be declared before results, and its use labelled. | False masks hide real effects. Detector errors need their own benchmark, with hard negatives such as a block moving along the bottom edge (wa30). |
| Cost | Nothing to build | A small detector, with benchmark and evaluation as for Track 3's |

**Recommendation.**
- **For the research tracks on development games now:** use declared masks, frozen in each experiment's protocol
  before any results and labelled as declared.
- **For anything meant to run on unseen games:** an online detector is required. It would be a separate, versioned
  component; the provenance kind `detected_online` is reserved for it.
- Neither choice changes this record format.

## 5. What this draft does not include

- **Changed-cell lists.** Tracks 1 and 4 recompute them from raw frames. Version 1 records the count, bounding box and
  mask hash, and version 2 keeps that. Adding full lists is easy, but it can add up to 4,096 cells per frame to every
  record. Deferred until a track needs them in the record rather than recomputed.
- **Object identities** (Track 2's object-instance scope). They belong to perception, not to this record.
- **Masked continuity.** Version 1's continuity compares whole frames. A masked continuity is not added until a
  consumer needs it.
- **An online mask detector** (§4).

## 6. Migration

| Consumer | Change |
|---|---|
| WS3 questionnaire v1 | none: it stays on version 1 |
| Track 1 | use `record_id`. Read `visual_effect_outside` where its protocol declares a mask, and report the s5i5 repeat metric with the mask declared. |
| Track 2 | replace its own record id and carried-forward level with `record_id` and `context.levels_completed_before` |
| Track 3 | take legal test actions from `available_actions_before`, and re-run the detector benchmark with a masked state fingerprint for the step-counter families |
| Track 4 | none required. A masked variant would be a new question family, not a change to existing keys. |
