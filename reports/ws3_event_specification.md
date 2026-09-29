# Transition evidence v1: event vocabulary, schema and validation (Workstream 3)

Version `transition_evidence_v1`. Implementation:
- vocabulary: `research/transition_evidence_v1/vocabulary.py`;
- builder, comparator and validator: `research/transition_evidence_v1/transition.py`;
- independent reference: `research/transition_evidence_v1/reference.py`.

**The rule of the vocabulary.** Each dimension describes the retained evidence only. None states hidden game
state, assigns a cause, or judges an action.

## 1. Dimensions (never collapsed into one outcome label)

| Dimension | Values | Meaning |
|---|---|---|
| Dispatch | `acknowledged`, `failed`, `outcome_unknown` | What happened to the request. Failed and unknown always carry a reason. |
| Observation availability | `complete`, `partial`, `missing`, `not_applicable` | Judged against the interface contract: an acknowledged action returns at least one valid frame. `not_applicable`: a failed dispatch delivered nothing. |
| Frame comparability (per frame, per reference) | `comparable`, `dimensions_differ`, `unavailable` | Whether a cell-by-cell count is defined. |
| Visual effect | `no_observed_change`, `changed_then_returned`, `final_frame_differs`, `indeterminate` | Over the available returned frames, against the pre-action frame. |
| Environment events | `level_completed`, `level_count_decreased`, `terminal_state`, `reset_acknowledged`, `none_reported`, `not_observed` | Only what the environment reported, with the reported values and their source. |
| Progress | `confirmed`, `unknown` | `confirmed` only by an allowed signal (`levels_completed_increased`, `state_WIN`). Model interpretations (`hypothesis`) live in a separate record. |
| Continuity (within a segment) | `first_in_segment`, `matches_previous_final`, `differs_from_previous_final`, `gap_after_unknown_outcome`, `gap_after_missing_observation` | Whether an action started from the frame the previous one left observed. |

## 2. Examples and counterexamples

| Term | Example | Counterexample, not this term |
|---|---|---|
| `failed` | The request was rejected before acknowledgement. | "Nothing happened": a failed dispatch is not a no-op observation. Its visual effect is `indeterminate`. |
| `outcome_unknown` | A response timed out after the request was sent. | "The previous frame is still current": the next transition's continuity is `gap_after_unknown_outcome`. |
| `missing` | Acknowledged, but no frame came back, or every returned frame was invalid. | `no_observed_change`: missing frames never produce a zero-change count. |
| `no_observed_change` | Every returned frame equals the pre-action frame. | "The action had no effect": hidden state may have changed. The term describes the observations only. |
| `changed_then_returned` | An intermediate frame differed; the final frame equals the pre-action frame. | `no_observed_change`: something visibly happened. |
| `dimensions_differ` | A returned frame has a different height or width. | A count of 0: the count is `unavailable`, and the frame still differs. |
| `level_completed` | `levels_completed` increased (the source is recorded). | "Pixels changed": 93 archived transitions changed the final frame with no progress signal. |
| `terminal_state` | The reported state is not `NOT_FINISHED`. | "The agent died because of this action": it establishes neither death nor its cause. |
| `reset_acknowledged` | `full_reset` was reported. | "Progress was lost", or "the action was irrational". |
| `differs_from_previous_final` | The frame changed between two observations with no action-specific evidence (e.g. animation). | "The previous action caused it". The record never attributes causes. |

## 3. Record schema (one transition)

| Block | Fields |
|---|---|
| `identity` | `episode_id`, `action_index` |
| `action` | `proposal` (measured / absent), `dispatched` (`action_id`, `action_data`), `proposal_equals_dispatched` |
| `dispatch` | `status`, `reason` |
| `observations` | `before_frames_sha256`, `pre_frame_shape`, `availability` (`status`, `reason`) |
| `measurements` | `returned_frame_count`; per returned frame (`index`, `valid` or `reason`, `shape`, `sha256`, `vs_pre`, `vs_previous`); `any_returned_frame_differs`; `final_frame_equals_pre`; `visual_effect` (`status`, `reason`) |
| per-frame comparison | `comparability`, `changed_cells`, `changed_bbox_xyxy`, `changed_mask_sha256`, `differs` |
| `environment` | `events`, `reported` (levels before/after, state before/after, `full_reset` after), `source` |
| `progress` | `status`, `signals` or `reason`, `source` |
| history only | `segment`, `continuity` |

**References are stated.** `vs_pre` compares each returned frame with the pre-action frame, which is the last frame
of `before`. `vs_previous` compares each frame with the returned frame before it; frame 0 is compared with the
pre-action frame. Cells are `[x, y]`, with the frame read as `grid[y][x]`.

**Missing is never zero or false.** Every measurement is one of:
- `{'status': 'measured', 'value': v}`, where 0 and False are real values;
- `{'status': 'unavailable', 'reason': ...}`;
- `{'status': 'absent', 'reason': ...}`, meaning an older record format did not keep the field.

**Model statements** use a separate record (`record: model_statement`, `status: hypothesis`) and never modify a
transition record.

## 4. Validation rules (`transition.validate`, tested)

- Every value is inside the vocabulary. Every non-measured value carries a reason.
- A failed dispatch has availability `not_applicable` and visual effect `indeterminate`.
- An unknown outcome has availability `missing` and visual effect `indeterminate`.
- A missing observation never produces a measured change value.
- `no_observed_change` requires a measured absence of change.
- Progress is `confirmed` only by an allowed signal; `hypothesis` never appears in a transition record.
- An invalid returned frame breaks chronology: the next frame's `vs_previous` is `unavailable`.

## 5. Compatibility plan

- **`action_effect_record_v1` stays frozen and unchanged.** v1–v3 comprehension experiments depend on it.
- **Transition records are built from the raw evidence the existing producers already archive**
  (`scripts/replay_transition_evidence_v1.py` shows this on two archives).
- **Checked against the recorded v1 effects.** The replay compares recomputed values with every recorded
  `action_effect_record_v1` field: 148 transitions, 0 disagreements.
- **Fields an older format did not keep are marked `absent`**, never guessed. Example: a proposal that was not
  retained.
- **Future producers** should retain the proposal, every returned frame (including an empty list), and the
  environment source, so no field needs to be `absent`.
- **Shared fields for Workstreams 1 and 2** (observation and action identity, exact dispatched arguments,
  dispatch status, returned observations, level and reset boundaries, observed/computed/inferred status) are
  proposed here for review. They are not yet adopted by the other streams.
