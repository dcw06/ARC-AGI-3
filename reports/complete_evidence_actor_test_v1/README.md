# One controlled test: does useful older memory improve Opus's prediction?

Prepared and run 2026-11-15. Protocol revision 11. The six Opus requests were authorised by the user and
sent once. Training and the full G2 batch stay paused.

**Result: no benefit observed on this case, because there was no headroom.** All six responses predicted
the result exactly, with or without memory (F1 1.0 in every request). Opus worked out the answer from the
decision-time input alone, by extending the click it could already see. The case therefore says nothing
about whether memory helps when the input is not enough.

Two things did differ, and neither was a planned outcome: with the useful record Opus stated "high"
confidence both times against "low" in all four control requests, and it used fewer thinking tokens.

This is one development case. It cannot establish G2, which needs reserved decisions, several games and
controlled answers.

## The case

- **Game and decision:** vc33, after 43 actions (development case D10).
- **Action to predict:** a click at x=24, y=56. It is the action the saved agent actually took next, so
  its recorded result is the answer.
- **Useful memory:** action 38, the same click made five actions earlier. The history reviewer named it
  as sufficient for this uncertainty in the agent review.
- **Why memory should matter here:** the decision-time input already shows this click once (action 42),
  but from a different state, and the result of that click is not the answer. Action 38 was made with the
  two affected compartments in the same state as now.

Checked without opening the answer:

| Check | Result |
|---|---|
| The useful record's action is the action to predict | yes |
| Rows 50-58, columns 10-40 identical before action 38 and now | yes |
| Whole board before action 38 against the current board | 91 cells differ, all in row 0 and rows 33-47 |

Checked after the design was frozen, from the sealed answer (three yes/no flags only):

| Flag | Value |
|---|---|
| The useful record's play-area change equals the answer | yes |
| The irrelevant record's play-area change equals the answer | no |
| The click in the recent history (action 42) equals the answer | no |

So the test is valid as a test of useful memory: the supplied record predicts the result exactly, and
neither control does.

## The three inputs

Same system text, same decision-time input, same question, same settings. Only the older-memory section
differs.

| Condition | Older-memory section | Section tokens | Whole request tokens |
|---|---|---|---|
| none | absent | 0 | 3,179 |
| useful | B version 2 pack holding action 38 | 758 | 3,930 |
| irrelevant | B version 2 pack holding action 41 | 806 | 3,978 |

- Both packs are inside the 2,048 allowance with instructions, header and provenance counted.
- Both packs carry the same header wording, so nothing labels one as the useful one.
- **The irrelevant record was chosen by rule**, not by hand: older than the two recent actions, same level
  and attempt, one frame, changes something in the play area, touches none of the cells the useful record
  changes, is not the action to predict, and was not cited for this uncertainty. Of the 12 records that
  qualify, action 41 has the pack closest in size to the useful one.
- Action 41 is a click on a different block in the same level. It shows the game's general mechanic, so
  it is a fair control for "any record from this game helps".
- Token counts are estimates from the counting endpoint, logged with their payloads.

**The question** asks for the rectangles of cells whose colour will differ in the last returned frame,
with their new colour; whether anything outside row 0 changes; whether the level is completed; a
confidence level; and one or two sentences on what the answer relied on.

## Scoring, fixed before the answer was computed

`research/complete_evidence_v1/actor_test_score.py`, sha256 `03db93e8fdf48bd3...`, recorded in
`frozen/design.json` before the sealed answer was written.

- **Primary outcome:** F1 between predicted and actual changed cells in rows 1 to 63, where a cell counts
  only with the right new colour. Row 0 is the counter strip and is left out of the primary score.
- **Secondary:** the same over all rows; exact match; level completed; any change outside row 0.
- A malformed or missing answer scores 0 and is reported as invalid.

Reading rule, also fixed in advance:

| Observed | Reading |
|---|---|
| Mean F1 of useful exceeds both none and irrelevant by at least 0.10 | Benefit observed on this case |
| Either difference is below 0.10 | No benefit observed on this case |
| The two requests of any condition differ by more than 0.5 | Unresolved |

If the no-memory condition already scores near 1, the case had no headroom and says nothing about memory.

## The requests

Sent once by `actor_test_run.py --send` after the user's go-ahead. The plan was:

| Setting | Value |
|---|---|
| Requests | 6: none, useful and irrelevant, two each, in a seeded random order |
| Model and settings | `claude-opus-5-5`, effort `high`, adaptive thinking; identical for all six |
| Each request | A fresh stateless call; 8,000 output tokens (thinking included); 300 seconds; no retries |
| Refusal or error | Recorded as that request's result; no fallback model, no resend |
| Spending stop | $1.20 at list price; worst case for all six is $1.05 |

The requests would use the API key in the repository's `.env`. Its remaining credit is about $4.70 by my
estimate, not a checked balance. The readability rehearsal's four requests cost $0.23 against a $0.72
worst case, so the likely cost here is well under the worst case.

## Results

The answer, from the recorded result of action 44: one frame returned; rows 56-57, columns 18-23 turn
from 3 to 0; rows 56-57, columns 30-33 turn from 0 to 3; one counter cell in row 0 (column 44) turns
from 7 to 4; the level is not completed. That is 20 play-area cells and one counter cell.

| Request | Order sent | Play-area F1 | Exact | Level and row-0 items | Stated confidence | Input tokens | Output tokens (thinking) | Cost |
|---|---|---|---|---|---|---|---|---|
| none 1 | 5th | 1.0 | yes | both right | low | 3,179 | 1,936 (1,659) | $0.051 |
| none 2 | 1st | 1.0 | yes | both right | low | 3,179 | 2,856 (2,563) | $0.070 |
| irrelevant 1 | 2nd | 1.0 | yes | both right | low | 3,978 | 2,466 (2,206) | $0.065 |
| irrelevant 2 | 3rd | 1.0 | yes | both right | low | 3,978 | 2,466 (2,162) | $0.065 |
| useful 1 | 6th | 1.0 | yes | both right | high | 3,930 | 1,787 (1,503) | $0.052 |
| useful 2 | 4th | 1.0 | yes | both right | high | 3,930 | 1,686 (1,425) | $0.049 |

- **Primary outcome:** mean F1 is 1.0 in all three conditions. Useful minus none is 0.0 and useful minus
  irrelevant is 0.0. By the rule fixed in advance: **no benefit observed on this case**.
- All six also predicted the counter cell correctly, so the all-rows F1 is 1.0 too.
- All six ended normally; none hit the output limit, none was refused. Total cost $0.353 at list price.
  The billed input tokens equal the estimates exactly.

**Why there was no headroom.** The four control responses all gave the same reasoning: action 42 in the
recent history moved a two-row unit from the right container into the strip at columns 18-23, so the same
click should move the last remaining unit. Two of them added that they were assuming this ("may be a
floor that cannot drain"). The guess was right. Before the run I confirmed that action 42's result was not
the answer; I did not test whether the answer could be inferred from it, and it could.

**What the useful record changed.** Both useful responses cited the record directly ("exactly as in the
older record"; "the stored record e38 shows the same click with the region in the same state as now").
So Opus read the B version 2 pack and used it. The observable effects were on certainty and effort, not
on the prediction:

| | none | irrelevant | useful |
|---|---|---|---|
| Stated confidence | low, low | low, low | high, high |
| Mean thinking tokens | 2,111 | 2,184 | 1,464 |

These two measures were not planned outcomes, there are two requests per condition, and stated confidence
is self-report. Treat them as observations worth testing, not as results.

## What this means for the next test

- **The case selection was the weak point, not the format.** A valid test needs a decision where the
  no-memory input does not already imply the answer. A recent action of the same kind is a sign that it
  does.
- **Screen for headroom first.** Candidates from the agent review where the recent history holds no
  analogue of the action to predict: D11 (what ACTION5 does; ACTION5 does not appear in the decision
  input) and D04 (the tn36 disc click). Their sets fit at 1,611 and 1,812 tokens.
- **A cheaper screen exists.** Running only the no-memory condition on a candidate, twice, shows whether
  there is headroom before the other four requests are spent.
- **If confidence is of interest**, it needs its own planned outcome, for example a prediction the model
  may decline to make, scored for both accuracy and willingness.

## Limits

- **One case, two requests per condition.** It can show a clear effect or none; it cannot estimate a rate.
- **Readability and use are tested together.** Opus has read B version 1 on one tn36 example. It has not
  read B version 2 or its instructions. A failure here could be a reading failure.
- **The useful record was picked by an AI reviewer and confirmed by me against the answer.** That makes
  this a test of what good selection could deliver, not of any automatic selector.
- **Prediction, not play.** A better prediction does not show the agent would choose a better action.
- **I know the answer.** The three eligibility flags tell me what it is. Opus's inputs were frozen and
  hashed before the answer was computed, and none of them contains it.

## Files

- `frozen/`: `input_none.txt`, `input_useful.txt`, `input_irrelevant.txt` (each complete input),
  `requests.json` (exact request bodies), `design.json` (design, rules, token counts, hashes),
  `source_frames.npz`. All read-only.
- `sealed/answer_key.json`: the recorded result of action 44. Not part of any input; opened for scoring
  after the responses were saved.
- `responses/`: the six responses, whole and read-only. `scores.json`: the scores. `run_record.json`:
  usage, cost and response hashes.
- Code: `research/complete_evidence_v1/actor_test_prep.py`, `actor_test_score.py`, `actor_test_run.py`.
