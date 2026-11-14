# Staged review packet: 12 development decisions

Protocol revision 11, the G3 full-history subset. Prepared 2026-11-14. Not yet reviewed by anyone.

The purpose is to find out whether the selected records matter, not whether they look tidy. So the
order is fixed: questions first, then the history, then the pack, then the type label.

## Rules for every reviewer

- Work alone. Do not discuss a case with the other reviewer until both of you have saved all four
  stages for it.
- Do the stages in order, one case at a time. **Save each stage's form before opening the next stage's
  folder.** Later folders reveal things that would change earlier answers.
- Do not open the reports in the folders above this one, the format-check results, the other
  reviewer's files, or anything about what happened after the decision.
- Saved forms are not edited afterwards. If you change your mind, write a new file ending `_revised` and
  keep the first.

## The four stages, per case (`cases/D01/` and so on)

| Stage | Open | Do | Save as |
|---|---|---|---|
| 1 | `stage1/decision_input.txt` (what the model gets) and `stage1/decision_view.html` (the same boards as pictures) | Write the important questions a careful player would have before choosing the next action. Say which the input already answers. | `submissions/<you>_<case>_stage1.json` from `forms/stage1_questions.json` |
| 2 | `stage2/history_view.html` (every past action up to the decision) | For each question, find the past observations needed to answer it, and the groups of observations that would be enough on their own. Mark each as an observed event, a supported limited conclusion, or an unresolved hypothesis. | `..._stage2.json` |
| 3 | `stage3/pack_B2.txt` and `stage3/pack_contents.json` | Judge which of your needed observations are in the pack, and whether they can be read from the pack text alone. | `..._stage3.json` |
| 4 | `stage4/assigned_type.json` | Say whether the effect type assigned by rule is meaningful for this case. | `..._stage4.json` |

## Things to know

- The pictures use display colours for the sixteen digits. The model sees digits, not pictures; stage 3
  is judged on the text.
- The records in each pack were chosen by the case-selection rule, not by a reviewer and not by a scoring
  model. It is a real possible answer that a pack's record does not matter for any question.
- Two packs (D06, D07) are larger than the 2,048-token working allowance. They are included so the
  evidence can still be judged; `pack_contents.json` says so.
- "Not a memory problem" in the stage 2 form is for needs that no past record can meet: something never
  discovered, or a reasoning or planning gap.
- Stage 1 questions must not contain their answers, a rule you learned from the history, or the numbers
  of useful past actions.

## What this is and is not

- Two reviewers working this way give independent judgments that can be compared before discussion.
- AI agents may be used as reviewers for a rehearsal, but another model does not satisfy the protocol's
  human review (R1). Record who or what each reviewer was.
- `subset_frozen.json` lists the 12 cases, the seed, and a hash of every file in `cases/`.
