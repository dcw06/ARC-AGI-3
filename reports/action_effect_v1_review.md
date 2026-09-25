# Action-effect records and change fixtures v1

This is step 4 of the post-R8 plan, reordered after the four-action diagnosis:
change detection and action-effect records first. Localization and geometry
fixtures stay queued as a secondary track and do not block the history
comparison. There are no model calls and no GPU runs.

## Record contract (`research/action_effect_v1/records.py`)

`effect_record(pre, action, outcome)` is built from exactly three inputs: the
pre-action observation, the dispatched action, and the dispatch outcome. Its
effect fields are:

| Field | Meaning |
|---|---|
| `action_id`, `action_data` | Exactly what was dispatched. Coordinates are kept, so two clicks at different cells stay distinct |
| `status` | `acknowledged`, `dispatch_failed` (rejected or never delivered) or `outcome_unknown` (sent, result not observed) |
| `returned_frame_count` | Frames the engine returned |
| `changed_cells_by_frame` | Cells differing from the last pre-action frame, per returned frame; `null` for a dimension change |
| `final_frame_changed`, `any_frame_changed`, `returned_to_pre_frame` | Derived from the counts. The last one captures a change that is followed by a return to the original frame |
| `level_delta`, `reset`, `state_after` | Level counter change, full reset flag, game state |

The record is bound to its inputs by `pre_frames_sha256` and
`returned_frames_sha256`, plus the engine's canonical hashes when they are
supplied.

**Failures never become no-ops.** For `dispatch_failed` and `outcome_unknown`,
every effect field is `null`, never `0` or `false`. A reason is required, and
anything else is rejected.

**What a policy may see.** `policy_view()` exposes only the action, its
status, the frame count, the changed-cell counts, whether the final frame
changed, the level delta, and whether the game reset. It contains no hashes,
no diagnostics, no recommendation, no object classification, and nothing
from the offline counterfactual probes.

`EffectHistory` keeps records in order. It starts a new segment after an
acknowledged reset or level change, and reports how many earlier entries were
omitted.

## Fixtures (`research/action_effect_v1/fixtures.json`)

All 11 single-action cases are built deterministically from the committed
ar25 development frame, or from small synthetic grids. They are perception and
record tests, not playable environments. Action IDs are arbitrary labels,
chosen so they do not mirror any game's observed behaviour.

- The same action type at two different coordinates.
- Identical frames.
- Movement: object A shifted one cell.
- Disappearance: object B removed.
- A colour-only change: A's colour 5 → 8.
- An intermediate change followed by a return to the original frame.
- A level-counter change with unchanged pixels.
- A dimension change.
- A failed dispatch.
- An unknown outcome.

A seven-step history sequence covers a level transition, a reset and a failed
dispatch.

Labels are computed mechanically by `effect_record`. The tests re-check every
count with an independent implementation, which compares sets of differing
coordinates. They also check each case's intended property: for example, the
colour change equals A's colour-5 cell count, and the disappearance equals
B's cell count. Regeneration is byte-identical:
`python -m scripts.build_action_effect_fixtures --check` (SHA-256
`078414ec…1198`).

## Compatibility with R8

Records built from the four archived R8 transitions give `acknowledged`,
`[0]` changed cells, `final_frame_changed: false` and a level delta of 0. They
are bound to R8's exact pre- and post-canonical hashes. The R8 archive replay
is unchanged and still verifies. The R8 runner and its frozen protocols were
not modified.

## Tests

`tests/test_action_effect_v1.py` has 8 passing tests covering:
- deterministic regeneration;
- the independent re-check;
- intended properties;
- failure safety;
- input-only purity;
- the policy-view field set;
- invalid-input rejection;
- history segmentation;
- R8 compatibility.

## Next

Freeze the bounded comparison. The baseline keeps the existing
action-ID-only history. The candidate adds recent action arguments and these
effect records, labelled as tool-assisted feedback. Both arms get identical
coordinate instructions and control descriptions. If those need correcting,
a new common baseline is frozen first and its departure from R8 is
documented.

The metrics are reported separately:
- exact repetition after no visible effect;
- action-type selection and diversity;
- the rate of observable change;
- level completion and action cost.

Neither diversity nor pixel change counts as solving. ar25 is a development
case for this comparison. Geometry and localization work remains queued.
