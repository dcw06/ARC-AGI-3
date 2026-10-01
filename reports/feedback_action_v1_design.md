# Feedback-action v1: design, evaluator and CPU rehearsals (Track 1, milestones A–C)

**Status: development work only.** No model was called. There was no GPU, Kaggle, network, upload, reservation or
approval. Every result below comes from scripted model outputs in synthetic environments. Scripted outputs test
the plumbing and the evaluator. They say nothing about how a model behaves.

## 1. Question and hypothesis

**Question.** When the agent has accurate action-effect evidence, does an explicit procedure for testing and
revising a hypothesis lead to better decisions than the evidence alone?

**Hypothesis.** A short structured hypothesis-testing procedure:
- reduces unjustified repetition;
- improves prediction accuracy.

Whether it improves level completion is an empirical question. It is not assumed.

**Why this, now.** Evidence comprehension v3 (§3) found that the model reads single history entries well but
reasons poorly across entries. `tried_unchanged` stayed below the floor even with tool eligibility. Action-effect
history v1 found that history alone did not steer the model toward untried actions (ar25). The structured procedure
targets that gap: it makes the model state which entries bear on its next action and what it expects to see.

## 2. The isolated treatment

| | Baseline | Candidate |
|---|---|---|
| Observation | from the existing pipeline, unchanged | identical |
| Evidence (`action_effect_history`) | `evidence.view` from `transition_evidence_v1` records | identical |
| System prompt | `SYSTEM_PROMPT` | `SYSTEM_PROMPT` + one paragraph, `PROCEDURE` |
| Response | `{"action": …}` (frozen `arc_action_v12` schema) | `{"hypothesis_test": …, "action": …}`. The `action` sub-schema is byte-identical. |
| Completion cap | 128 tokens | 640 tokens |
| Action validation | `certification.phase4_transient_v2.action_contract.validate_action` | the same function |
| Dispatch rule | dispatched if and only if the action is valid | the same. An invalid `hypothesis_test` block does not block dispatch; it is counted separately. |

`adapter.strip_procedure(candidate_request) == baseline_request` holds for all 62 rehearsal decision points
(tested). The user message, and therefore the observation and evidence, is byte-identical between arms.

**Extra cost per call.** The candidate adds 1,007 system-prompt characters and 1,636 response-schema characters,
and up to 512 more completion tokens. Prompt tokens need the model tokenizer, so they are reported in characters
here. **The arms are not compute-matched.** The candidate's extra tokens will be reported per call and per episode.

**The procedure's six fields:**
- Hypothesis, with a status: `new`, `retained` or `revised`.
- Evidence supporting: references.
- Evidence conflicting: references.
- Next action: the shared `action` field.
- Predicted observable result.
- What a different result would imply.

## 3. Prediction and evidence-reference schema (`adapter.HYPOTHESIS_TEST`)

- **Reference:** `{"ref": "T<n>", "claim": <closed vocabulary>}`, at most 4 per list.
  - `T<n>` is the episode-wide `action_index` from the transition record.
  - The claims can all be checked mechanically against that record: `no_observed_change`,
    `changed_then_returned`, `final_frame_differs`, `indeterminate`, `dispatch_failed`, `outcome_unknown`,
    `level_completed`, `reset_acknowledged`, `same_state_as_now`, `different_state_from_now`.
- **Prediction:** a closed vocabulary only.
  - `visual_effect` is one of `no_observed_change`, `changed_then_returned` or `final_frame_differs`.
  - `level_completed` is a boolean.
  - `changed_region_xyxy` is optional. It must contain every cell that differs from the pre-action frame in any
    returned frame.
  - Free text (`hypothesis`, `if_different`) is capped at 240 characters, retained, and **never scored**. A test
    shows that changing it leaves the evaluation unchanged.

**The shared evidence view (`evidence.py`):**
- Contents: the current segment only, at most 8 entries, oldest first.
- Each entry gives:
  - the ref and the exact dispatched action;
  - dispatch status;
  - observed `from_state` and `to_state`: frame-hash ids, `not_observed` after a failed or unknown dispatch;
  - visual effect, final-frame changed cells, events, progress and continuity.
- Unmeasured values are the string `unavailable`, never 0 or null.

## 4. Independent evaluator (`evaluate.py`)

**Independence.** The evaluator imports only `hashlib`, `json` and the contract's import-free `reference.py`; a test
enforces this. It re-parses raw model output and recomputes the following from raw transitions:
- the shown window;
- per-action evidence status;
- citation truth;
- prediction outcomes.

It agrees with the evidence view's window at every rehearsal decision.

| Check | Rule |
|---|---|
| Cites only earlier observations | Each citation is one of: `supported`, `wrong_claim`, `failure_read_as_no_change`, `earlier_not_shown` (before a reset or level boundary, so the model could not see it), `not_earlier` (future or invented), `malformed`. |
| Untested ≠ ineffective | The evidence status of the chosen exact action (id plus coordinates), over the shown window: `no_change_same_state`, `transient_same_state`, `changed_same_state`, `indeterminate_same_state`, `tested_other_state`, `outcome_unknown_only`, `failed_only`, `untested`. Citing a failed or unknown dispatch as `no_observed_change` is counted separately. |
| Contradictions | A prediction is *incorrect* when the next transition falsifies it. The following decision is scored as one of: `recognized` (status `revised` and the falsifying ref cited as conflicting), `revised_not_cited`, `cited_not_revised`, `not_recognized`, `procedure_invalid`. |
| Legal actions | Recomputed against the legal actions recorded with the decision. |
| Observable prediction | Must be within the closed vocabulary, with a well-formed region and no region with `no_observed_change`. Scored as `correct` / `incorrect` / `unscoreable` (failed, unknown or indeterminate dispatches are unscoreable). |
| Repetition | `exact_repeats_after_no_change_same_state` is reported together with how many such repeats were followed by a visible change or a level completion. **Repetition is not equated with waste.** |

## 5. Decision-boundary fixtures (`fixtures.py`, `fixtures.json`)

Ten deterministic, synthetic, development-only fixtures. Expectations are written by hand from the construction;
the evaluator is tested against them. All raw transitions pass `transition.validate`.

| Fixture | Decision boundary |
|---|---|
| `exact_repeat_no_change_same_state` | ACTION1 into a wall, still in that state |
| `same_action_other_coordinate` | ACTION6 at (1,1) changed nothing; (5,5) is untested, not ineffective |
| `tested_in_other_state` | ACTION1 changed nothing in an earlier state; the agent has since moved |
| `failed_dispatch` | `failed_only`: untested, not ineffective |
| `unknown_outcome` | executed but never observed: `outcome_unknown_only` |
| `changed_then_reverted` | a flash that returned: not "no change" |
| `necessary_repeat` | two invisible presses; the third completes the level (known mechanism) |
| `contradicts_hypothesis` | the prior prediction `final_frame_differs` was falsified by `no_observed_change` |
| `after_level_boundary`, `after_reset_boundary` | the window is empty; earlier refs are `earlier_not_shown` |

**Rule (`check_rules`).** Only synthetic fixtures may declare `progress_keys` (actions known to make progress). A
`real_game` fixture with them is rejected, because real games must not assume one uniquely correct next action. **No
real-game fixture exists yet**; see open questions.

## 6. CPU rehearsals (`rehearsal.py`; scripted outputs; synthetic environments)

The closed loop runs: observe → shared evidence view → adapter → scripted model → adapter parse → dispatch if
valid → raw transition. The environments are:
- `DelayedSwitch`: invisible presses, then a level;
- `PushToGoal`: walls, goal, an optional move limit with `full_reset`;
- `Clicker`: ACTION6 target, decoy flash.

Faults are injected per dispatch index. All 16 trajectories are deterministic, and all invalid outputs are retained.

| Scenario / arm | Decisions / dispatched | Invalid (retained) | Citations | Predictions | Other |
|---|---|---|---|---|---|
| invalid_structured_output / baseline | 5 / 2 | action: not_json 1, illegal 1, truncated 1 | – | – | stop: decision budget |
| invalid_structured_output / candidate | 5 / 2 | same; procedure: not_json 1, truncated 1, unobservable_prediction 1 (action still dispatched) | – | correct 1 | |
| missing_and_invented_references / candidate | 4 / 4 | procedure: missing_reference 1 | not_earlier 2, wrong_claim 1, supported 1 | correct 3 | |
| delayed_effect / both | 6 / 6 | – | candidate: supported 8 | candidate: correct 2, incorrect 4 | 4 exact repeats after no change, **2 followed by a level**; WIN in both arms |
| unknown_dispatch_outcome / candidate | 5 / 5 | – | **failure_read_as_no_change 1**, supported 3 | unscoreable 2, correct 2, incorrect 1 | dispatch: 3 acknowledged, 1 failed, 1 unknown |
| reset_and_level_boundaries / candidate | 6 / 6 | – | earlier_not_shown 2, supported 3 | correct 5, incorrect 1 | reset at T2, level at T4 |
| action_budget_exhausted / both | 2 / 2 | – | – | – | stop: action budget |
| completion_budget_exhausted / candidate | 3 / 3 | – | – | correct 3 | stop: completion budget (900 of 1,500 tokens; the next 640-token call would not fit) |
| decision_budget_exhausted_all_invalid / both | 3 / 0 | not_json 3 | – | – | stop: decision budget; nothing dispatched |
| contradiction_revised / candidate | 2 / 2 | – | supported 2 | correct 1, incorrect 1 | revision: recognized 1 |
| contradiction_ignored / candidate | 2 / 2 | – | – | incorrect 2 | revision: not_recognized 1; 1 exact repeat |
| coordinate_actions / both | 4 / 4 | – | candidate: supported 3 | candidate: correct 2, incorrect 2 | 1 repeat at (1,1); revision: revised_not_cited 1, not_recognized 1; WIN |

**Retained finding about the metric (from the delayed-effect rehearsal).** A hypothesis that is *right* about
the mechanism ("presses accumulate") but predicts the wrong timing is scored `incorrect` twice per level. Each time,
it is followed by `not_recognized` revision. "Revision after contradiction" therefore cannot be read as good by
itself: continuing to repeat was necessary there. The protocol below reports it descriptively, beside level
outcomes, and never as a success criterion.

## 7. What the eventual experiment can and cannot establish

**It can show:**
- whether the procedure changes behaviour on a few development games: exact repeats after no change, choice of
  untested actions;
- how often the model's predictions are mechanically correct;
- whether it cites evidence it was shown, and only that;
- whether it revises after falsification;
- the cost in tokens and time.

**It cannot show:**
- generalization: all 15 development games are exposed, and the cases are few;
- a solving improvement without a level-completion difference;
- causation between the procedure's free text and the action;
- that the model "understands" anything, since free text is never scored;
- an effect size below the model's run-to-run variance at temperature 0 (AEH v1 observed non-determinism).

Steps of one trajectory are not independent samples. The unit of analysis is the episode.

**The baseline has no predictions.** Prediction accuracy is therefore a candidate-only descriptive metric, not a
between-arm comparison. A prediction-only arm, which separates "predicting" from "testing hypotheses", is an open
question.

## 8. Dependencies on the transition contract (`transition_evidence_v1`, consumed read-only)

| Need | Status |
|---|---|
| `build`, `history`, `validate`, `frame_sha256` (view); `reference.facts`, `reference.sequence`, `reference.flat` (evaluator) | used as is |
| **A per-frame changed-cell list or bbox in `reference.py`** | missing. The evaluator recomputes changed cells itself (`changed_cells_any_frame`) for region predictions. A shared field would remove this duplication. |
| **An observed-state identity** | missing. The view and the evaluator each derive one from frame hashes, `S-` + 12 hex characters. A contract field would make "same state" a shared definition. |
| **A HUD or counter mask** | missing. As in s5i5, a per-action counter makes `no_observed_change` never apply on real games, so repeat metrics and predictions degrade there. Proposed in AEH v1 results; needs the contract. |
| **The proposal and adapter decision, retained by producers** | the contract keeps `proposal`. A closed-loop producer should also retain the `hypothesis_test` block as a `model_statement` record (`transition.model_statement`), never inside the transition record. Not wired yet. |

## 9. Files

- `research/feedback_action_v1/`:
  - `evidence.py`
  - `adapter.py`
  - `evaluate.py`
  - `environments.py`
  - `fixtures.py`, `fixtures.json`
  - `rehearsal.py`
- `tests/test_feedback_action_v1.py`: 31 tests.
- `reports/feedback_action_v1_protocol_draft.md`
