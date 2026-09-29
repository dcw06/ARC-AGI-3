# Workstream 3: existing action-effect evidence — audit and gap report

Written 2026-09-29, on branch `ws3-action-effects`. CPU only; no model calls.

**Audited:**
- `research/action_effect_v1/records.py` (`action_effect_record_v1`, `EffectHistory`, `policy_view`);
- `research/action_effect_v1/fixtures.py`;
- the history field in `research/action_effect_history_v1/contract.py`;
- two archives: action-effect-history v1 (12 episodes, 144 steps) and Stage B R8 (2 episodes, 4 steps, with model
  predictions and self-assessments).

**The frozen v1 record is not changed.** v1–v3 comprehension experiments depend on it. The new code
(`research/transition_evidence_v1/`) reads the same raw evidence and adds only what is missing.

## Inventory

| Capability | Already available? | Missing or ambiguous | Proposed extension (new code only) |
|---|---|---|---|
| Exact pre-action observation | Yes. Archives keep `before` (frames, levels, state, reset, canonical hash); the record keeps `pre_frames_sha256`. | The record states no reference frame when `before` has several frames. v1 implicitly uses the last. | State the reference: the last pre-action frame. Keep every before-frame hash. |
| Proposed versus dispatched action | Partly. Archives keep the raw model response (call) and the dispatched `action` (step). | No record field holds the proposal next to the dispatched action, nor whether they match. A fallback would be invisible in the record. | `action.proposal` (measured, unparsed or absent) and `action.proposal_equals_dispatched`. |
| Action arguments, including click coordinates | Yes (`action_id`, `action_data`). | — | None. |
| Dispatch outcome | Yes, as three statuses; failed and unknown keep a reason (`detail`). | In `policy_view`, a failed or unknown dispatch shows `null` effect fields, and so does a dimension change. The same null has two meanings (documented in v1/v2). | Typed measurements: `measured` / `unavailable` (with reason) / `absent` (older format). Never a bare null. |
| Ordered returned frames | Yes: every returned frame's change count against the pre-action frame, and a hash of all returned frames. | **Two gaps.** No differences between consecutive returned frames. And an acknowledged action with **no returned frames makes `effect_record` raise** (`changed[-1]` on an empty list): the case cannot be recorded. | Per-frame `vs_pre` and `vs_previous` comparisons. Observation availability (`complete` / `partial` / `missing` / `not_applicable`) with reasons. Invalid frames kept as invalid, never as zero change. |
| Frame comparisons | Yes: exact counts; `None` when dimensions differ; `final_frame_changed`; `any_frame_changed`; `returned_to_pre_frame`. | A dimension change is only a `None` count. `returned_to_pre_frame` is not exposed in the policy view. No changed-cell location. | Typed comparability (`comparable` / `dimensions_differ` / `unavailable`); a changed-cell bounding box and mask hash; the visual effect as its own dimension. |
| Environment state and progress | Partly: `level_delta`, `reset`, `state_after` are copied from the post-observation. | No provenance, no statement of which signals count as progress, and no terminal-state event. Visual change and progress are not separated. Nothing prevents treating any change as progress. | Environment events (`level_completed`, `level_count_decreased`, `terminal_state`, `reset_acknowledged`, `none_reported`, `not_observed`) with the reported values and their source. Progress is `confirmed` only by an allowed signal (`levels_completed_increased`, `state_WIN`), otherwise `unknown` with a reason. |
| Reset and level boundaries | Yes. `EffectHistory` starts a segment after a reset or level change. | A terminal state does not end a segment. | Segments also end after a terminal state. |
| Cross-step continuity | Implicit only. No field says whether an action started from the frame the previous one left. | After an unknown outcome, nothing marks the gap; continuity can be assumed silently. | Per-transition continuity: `first_in_segment`, `matches_previous_final`, `differs_from_previous_final` (e.g. animation between observations), `gap_after_unknown_outcome`, `gap_after_missing_observation`. |
| Observation and action identifiers | In archives: episode id, step index, call index, decision id, canonical hashes. | The record itself carries no episode or step identity. | An `identity` block (episode, action index), plus frame hashes. |
| Model interpretations | Kept only as raw responses, and R8 predictions and assessments as step fields. | No separation rule: nothing stops a model claim overwriting a measured fact. | A separate `model_statement` record (status `hypothesis`) that never modifies a transition record. |
| Intermediate frames in the archives | — | **Not exercised.** Every archived step (148 of 148) returned exactly one frame, so transient-change handling has no live coverage. | Synthetic fixtures only, until a source that returns several frames is archived. |

## What was not added

- **No second logging system.** The new records are built from the evidence the existing producers already keep.
- **No game rules, reward or penalty.**
- **No counter or board detector.** The fixtures' "counter-only" case recolours a small region at a seeded
  position.
- **No change to any frozen v1–v3 artifact.**

## Findings worth attention

1. **An acknowledged action with no returned frames cannot be recorded by `action_effect_record_v1`: it raises.**
   The frozen experiments never hit the case, since every archived step returned a frame. Any future producer
   should record it explicitly (`availability: missing`), as transition_evidence_v1 does.
2. **Visual change is not progress in the archived data.** 93 of 148 replayed transitions changed the final
   frame; none carried an allowed progress signal.
3. **Model self-assessments can contradict the frames they assess** (see the replay report). In all 4 R8 steps,
   the model called its "no change" prediction "supported", which was correct, while claiming frame 0 changed,
   which was false. Measured facts and model statements must stay separate.
