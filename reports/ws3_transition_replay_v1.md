# Workstream 3: replay of archived trajectories through transition_evidence_v1

**The run.** `scripts/replay_transition_evidence_v1.py` wrote the write-once report
`reports/ws3_transition_replay_v1.json`. A second run refuses to overwrite it; the archives are only read.

**Sources**, each opened only after its archive hash matched its lock:

| Source | Archive SHA-256 | Transitions |
|---|---|---|
| action-effect-history v1 (development engine; 12 episodes) | from `reports/action_effect_history_v1_archive.json` | 144 |
| Stage B R8 (2 episodes, with model predictions and self-assessments) | from `reports/perception_stage_b_r8_archive.json` | 4 |

## What was found

| Check | Result |
|---|---|
| Recomputed against the recorded `action_effect_record_v1` fields (changed cells per frame, any/final change, returned-to-pre, level delta, reset) | **0 disagreements** in 148 transitions |
| Dispatch | all 148 acknowledged; every step returned exactly 1 frame (so no intermediate-frame evidence exists in these archives) |
| Visual effect | 93 `final_frame_differs`, 55 `no_observed_change` |
| Progress | **all 148 `unknown`**: no allowed progress signal was reported. The 93 visible changes are not progress. |
| Continuity | 134 `matches_previous_final`, 14 `first_in_segment`, no gaps |
| Proposal against dispatch | equal in all 148 (no fallback occurred) |

## Model statements (R8), kept as hypotheses and checked against computed facts

| Statement | n | Agrees | Disagrees |
|---|---|---|---|
| Prediction ("no_change") | 4 | 4 | 0 |
| Self-assessment verdict ("supported") | 4 | 4 | 0 |
| Self-assessment frame claim (`frame_0_changed: true`) | 4 | 0 | **4** |

- **The contradiction.** In every R8 step, the model correctly called its "no change" prediction supported, yet in
  the same response claimed frame 0 changed. The frames show no change.
- **What this shows.** A correct verdict can come with a false factual claim. So the model's statements must stay
  separate from measured facts, and must never overwrite them.
- **What it does not show.** It is an observed error pattern in 4 steps of one model and prompt. It is not a
  claim about the model's internal mechanism.

## How each statement is classified

| Class | In this replay |
|---|---|
| Directly observed | dispatch status, dispatched action, returned frames, environment fields |
| Mechanically computed | availability, visual effect, changed cells, events, progress, continuity |
| Human annotation | none |
| Model hypothesis | R8 predictions and self-assessments |

## Gallery (`reports/ws3_transition_replay_v1/`)

Each image shows the pre-action frame and the final returned frame, with changed cells outlined. The label gives
the action and the changed-cell count, and attributes no cause.

- **R8 steps (4 images)**, where the self-assessment claimed a change the frames do not show:
  - `r8-control-0-step00.png`, `r8-control-0-step01.png`;
  - `r8-target-1-step00.png`, `r8-target-1-step01.png`.
- **The largest archived visible change without a progress signal:** `b1-wa30-baseline-step01.png` (ACTION2, 33
  cells).
- **An archived step with no observed change:** `b1-ar25-baseline-step00.png`.

## Limits

- **No intermediate frames.** The archives never returned more than one frame. Transient, partial,
  missing-frame, unknown-outcome and dimension-change handling is covered only by the synthetic fixtures (90
  fixtures across 18 families; `tests/test_transition_evidence_v1.py`).
- **No progress signal.** No archived transition reported one, so confirmed progress is also exercised only on
  fixtures.
