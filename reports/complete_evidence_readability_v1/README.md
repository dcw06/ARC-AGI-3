# Readability rehearsal: can one older action record be read in either compressed format?

Prepared 2026-11-14. Protocol revision 11. One frozen tn36 example, two inputs, same 2,048-token
older-memory allowance. Training and the 96-request G2 batch stay paused.

**Status: steps 1 to 3 are done; both formats passed the reader check.** Two independent AI agents read
the exact inputs, one format each, and both recovered all eight checked facts with nothing contradicting
the frames. The readers were agents, not people. Step 4 (four Opus requests) has not been authorised and
no Opus request has been made.

This page now contains the correct answers. A person who reads it can no longer serve as a blind reader
of this example.

| Step | Status |
|---|---|
| 1. Freeze one example and establish the correct answers | Done |
| 2. Two inputs at the same allowance, tokens counted | Done; both fit |
| 3. Two independent readers answer from the exact inputs | Done with two AI agents: A pass, B pass. No human has read them |
| 4. Four fresh Opus requests | Waiting for explicit authorisation |
| 5. Decision | Open |

## 1. The frozen example

- **Decision:** tn36, saved stateless run `opus55-competition-20261106T054112Z`, after 46 actions. The
  agent's next action was to press "run".
- **Earlier record:** the "run" at action 12, 34 actions earlier and outside the 8 actions the agent
  could see.
- **Why this one:** of the tn36 repeats found in Phase 1, it is the only one that is in the same attempt,
  out of view, and has a mixed switch setting. A mixed setting makes "all the same colour" a wrong guess.
  It was chosen by that rule, before either input was built.

Saved in `frozen/`:

| File | Content |
|---|---|
| `source_frames.npz` | Original cells: current board, the board before action 12, its 7 returned frames, and the two recent actions |
| `common_context.txt` | Current board (observation `o46`), legal actions, the two most recent actions |
| `older_memory_A.txt`, `older_memory_B.txt` | The older-memory section of each input |
| `questions.txt` | The questions and the answer form |
| `input_A.txt`, `input_B.txt` | Each complete input as Opus would receive it |
| `requests.json` | The exact request bodies, settings included |
| `token_counts.json` | Token counts |

Both records decode back to the original board and all 7 frames, cell for cell.

**The three questions**, asked in a fixed form so answers can be checked item by item:

1. What colour was each of the ten switches immediately before the earlier action?
2. What happened when it ran: frames returned, where one named block was in frame 3, how many cells of
   the last frame differ from the board before, whether the level was completed, and a short description.
3. Is that switch configuration the same as the current one, and which switches differ?

The questions say where the ten switches and the block are. A reader has no other way to know what
"switch" means; the saved agent learned it from play.

**Correct answers**, computed from the original frames, not from either text, and in no input. They were
kept sealed in `sealed/evaluation_record.json` (with the rubric and board identities) until both readers
had saved their answers.

| Item | Correct answer |
|---|---|
| Bars before the earlier action, left to right | 1, 1, 1, 1, 1 |
| Stems before the earlier action, left to right | 5, 1, 1, 1, 1 |
| Frames returned | 7 |
| The piece in frame 3 | columns 34-37, rows 13-16 (four columns right of where it started) |
| Cells of the last frame that differ from the board before | 1: row 1, column 50, colour 9 to 3 |
| Level completed | no (state NOT_FINISHED, level 0 before and after) |
| Same configuration as the current board | yes; no switch differs. The two boards differ in 35 cells, all in row 1 |

What the frames show: in frame 1 the clicked block (rows 51-59, columns 32-40) turns colour a. In frames
2 to 6 it is colour 9 again, a colour-9 outline steps across the five switch positions one per frame, and
the piece sits at columns 34-37. In frame 7 everything is as before the action except the one row-1 cell.

## 2. The two inputs

Same record, same common context, same questions, same settings. Only the older-memory section differs.

| | A | B |
|---|---|---|
| Format | `M-key-v1`: the earlier board in full once, then ordered changes | `M-ref-v1`: the earlier board as differences from the supplied current board, then ordered changes |
| Older-memory section, Opus tokens | 1,956 | 1,060 |
| Within the 2,048 allowance | yes | yes |
| Record alone | 1,676 | 728 |
| Whole request (system, context, memory, questions) | 5,309 | 4,413 |

- The older-memory count includes the section header, the provenance line, the reading instructions and
  the record. B is not padded to A's length.
- Common context is 2,703 tokens, the questions 586, the system text 85.
- B's reference board is the current board in the same input, observation `o46`. Its cell hash is
  `25a34f0fca8800b4...`; the full value and the event-log hash are in the sealed record.
- Counts are estimates from the token-counting endpoint for `claude-opus-5-5`; each is logged with its
  payload in `../complete_evidence_phase1_v1/data/opus_token_count_log.jsonl.gz`.
- A sits 92 tokens under the allowance. A second record would not fit beside it.

The current board in the common context uses the saved agent's own layout (hex digits in groups of
eight). The recent history uses the saved agent's changed-cell runs. Neither uses A's or B's syntax, so
the reading instructions inside the allowance are the only explanation of the record.

## 3. Reader check (done with two AI agents)

On 2026-11-14 two agents were started fresh for this check. **They are AI agents on this session's
subagent model, not people and not Opus.** A human reading of the same inputs has not happened.

- Reader 1 received input A only; reader 2 received input B only. Each got a folder holding its input,
  the instructions (`agent_readers/instructions_given.md`, the text of `human/README.md` cut down to one
  read) and the blank form.
- Each was told to open nothing else, to run no code, and to save its answers once.
- Both saved before either was scored. The first submissions are kept unchanged and read-only:
  `agent_readers/reader1_A.json` (sha256 `68c0046cbc7c25e3...`) and `agent_readers/reader2_B.json`
  (`1b5faab369d3b109...`).

| Item | Reader 1, input A | Reader 2, input B |
|---|---|---|
| Bars | correct | correct |
| Stems | correct | correct |
| Frames returned | correct | correct |
| Piece columns in frame 3 | correct | correct |
| Piece rows in frame 3 | correct | correct |
| Cells different in the last frame | correct | correct |
| Level completed | correct | correct |
| Same configuration, switches that differ | correct | correct |
| Free-text description | not contradicted | not contradicted |
| Contradictory statements | none | none |
| **Result** | **pass** | **pass** |

Every statement in the two descriptions was checked against the original frames by code
(`agent_readers/judgement.json`). `scores.json` holds the item scores.

**What the readers found hard.** Neither issue caused a wrong answer; both are defects in the reading
instructions that a later version should fix.

- Both readers noticed that a change line can name cells that do not actually change (row 16, columns
  30-33 set to colour 4 when columns 31-32 already were), so the listed ranges do not add up to the
  stated cell count. The instructions do not say this.
- Reader 1 noticed the instructions describe a "net before>last" line that this record does not contain.
- Reader 2 noted that in B the earlier switch colours are never printed: they must be read off the
  current board and carried back through "before vs current". It did so correctly.
- Both noted the piece is not a solid block, so its position is a bounding box.

**How far to trust this.**

- I cannot observe the agents' tool use directly. Each reported opening only its three files and running
  no code; the tool counts the session recorded (five each: three reads, one write, one report) agree.
- Each agent's context arrived with this project's memory index, titles only. The titles do not contain
  the answers. Reader 1 and reader 2 both disclosed it.
- Two agents on one model are not independent in the way two people are, and one reader per format means
  no within-format agreement was measured.
- This does not count towards R1, and it is not the two-human check of this example.

## 4. Opus requests (not authorised, not sent)

`readability_run.py` sends nothing without `--send`. The plan it will follow:

| Setting | Value |
|---|---|
| Requests | Exactly 4: A twice, B twice, in a seeded random order, each a fresh stateless call |
| Model and settings | `claude-opus-5-5`, effort `high`, adaptive thinking; identical for all four |
| Output limit | 8,000 tokens per request, thinking included |
| Time limit | 300 seconds per request, no retries |
| Spending stop | $0.80 at list price; worst case for all four is $0.72 |
| Refusal or error | Recorded as that request's result; no fallback model, no resend |

Every response is saved whole with its reported usage in `responses/`. Answers are scored on facts only.
Nothing here tests whether the agent would solve the level.

The requests would go through the Anthropic API key in the repository's `.env`. The remaining credit on
that key is about $5 by my estimate, not a checked balance.

## 5. Decision (open until the Opus responses exist)

So far: both formats passed the reader check, so neither needs repair before the Opus requests. The next
decision is explicit authorisation for the four requests under the $0.80 stop.

| Observed result | Next action |
|---|---|
| Both formats communicate the facts correctly | Take both into the cross-game development checks; examine whether compact B stays understandable |
| Only one format works | Continue with that format and investigate the other's failure |
| Neither works | Revise the representation or the reading instructions |
| Responses are inconsistent or the reviews disagree | Record as unresolved and diagnose the disagreement |

"Communicates the facts correctly" is fixed in the sealed rubric: all eight checked items right, and
nothing in the free-text description contradicting the frames. "Cannot determine" is reported separately
from a wrong answer.

## Limits

- One record, one game, one decision. The earlier and current settings in this example were chosen from a
  repeat, so a reader who always answers "same" is not caught on question 3. Questions 1 and 2 do not have
  that weakness.
- A pass shows the facts can be read. It does not show that Opus would use them when choosing an action.
- G1 to G3 and R1 still decide whether training may expand.

## Code

`research/complete_evidence_v1/readability_case.py` (builds everything above), `readability_run.py`
(the four requests), `readability_judge.py` (scoring).
