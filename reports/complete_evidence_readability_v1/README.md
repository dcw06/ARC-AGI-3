# Readability rehearsal: can one older action record be read in either compressed format?

Prepared 2026-11-14. Protocol revision 11. One frozen tn36 example, two inputs, same 2,048-token
older-memory allowance. Training and the 96-request G2 batch stay paused.

**Result, stated narrowly:** Opus recovered the specified facts from both formats on one
coordinate-assisted tn36 example. Automatic retrieval, gameplay benefit and R1 remain untested. The
inputs, hashes, rubric, item scores, usage and the $0.226 cost are archived in `ARCHIVE.json`.

**Status: complete. Both formats communicated the facts correctly.** With corrected reading instructions
(version 2), Opus answered all eight checked items correctly in all four requests: A twice, B twice.
Before that, two AI agents had each read one format (version 1) and also got all eight right. No human has
read the inputs, and this is one record in one game.

This page now contains the correct answers. A person who reads it can no longer serve as a blind reader
of this example.

| Step | Status |
|---|---|
| 1. Freeze one example and establish the correct answers | Done |
| 2. Two inputs at the same allowance, tokens counted | Done; both fit |
| 3. Two independent readers answer from the exact inputs | Done with two AI agents: A pass, B pass. No human has read them |
| 4. Four fresh Opus requests | Done on version 2, authorised 2026-11-14: 4 of 4 answered, all items correct, $0.23 |
| 5. Decision | Both formats go into the cross-game development checks |

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

## 2. The two inputs (version 1)

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

## 4. Version 2: corrected reading instructions

The agent readers found two defects in the version 1 instructions. Version 2 fixes them and freezes new
inputs in `frozen_v2/`. Version 1 (`frozen/`), its hashes and the agent-reader results are untouched.

What changed, and nothing else:

- A range in a change line may include cells that already had that colour.
- The cell count in a header is defined: the number of cells whose colour differs from the reference
  board named in that header. It can be smaller than the number of cells the lines cover.
- The "net before>last" block is marked optional, with the condition under which it appears.
- B says the board before the action is not printed and is rebuilt by applying the lines to the current
  board, and its header line names that board: observation `o46`.

Validation:

| Check | Result |
|---|---|
| Both records decode to the original board and all seven frames | yes |
| Record text, common context, questions | identical to version 1 (compared byte for byte) |
| Sealed answers and rubric | identical |
| Older-memory section, A / B | 2,035 / 1,192 tokens, both within 2,048 |
| Whole request, A / B | 5,388 / 4,545 tokens |
| Hashes | `frozen_v2/manifest.json`; `input_A.txt` `050670528c5a0582...`, `input_B.txt` `4d47d31e20d7f7e8...`, `requests.json` `8934ce9f5771b11b...` |

**A recorded size failure.** The first wording of the corrected instructions put A's older-memory section
at 2,085 tokens, over the allowance (kept in `frozen_v2_draft1_over_limit/`). Only the instruction
wording was shortened; no evidence was removed. A is now 13 tokens under the allowance, so the
instructions for this format have no room left to grow at 2,048.

The agent readers read version 1. Nobody has reader-checked the version 2 wording.

## 5. Opus requests

Authorised by the user on 2026-11-14 and sent once, on version 2, by `readability_run.py --version 2 --send`.

| Setting | Value |
|---|---|
| Requests | 4: A twice, B twice, seeded order B1, A2, B2, A1; each a fresh stateless Messages call |
| Model and settings | `claude-opus-5-5`, effort `high`, adaptive thinking; identical for all four |
| Limits | 8,000 output tokens and 300 seconds per request, no retries, no fallback model, stop at $0.80 |

| Request | Input tokens | Output tokens (thinking) | Seconds | Cost | Checked items correct | Free text |
|---|---|---|---|---|---|---|
| A1 | 5,388 | 1,929 (1,545) | 17.7 | $0.060 | 8 of 8 | not contradicted |
| A2 | 5,388 | 2,045 (1,668) | 18.0 | $0.063 | 8 of 8 | not contradicted |
| B1 | 4,545 | 1,770 (1,389) | 16.4 | $0.054 | 8 of 8 | not contradicted |
| B2 | 4,545 | 1,569 (1,178) | 15.2 | $0.050 | 8 of 8 | not contradicted |

- **A: pass. B: pass.** No incorrect items and no contradictory statements in any response.
- All four ended normally (`end_turn`); none hit the output limit, none was refused.
- Total cost $0.226 at list price, worked out from the reported usage.
- The billed input tokens equal the token-counting estimates exactly (5,388 and 4,545).
- Remarks on the free text: A2 calls the changed cell a "top-row cell" while giving it correctly as x=50,
  y=1; B2 adds hedged guesses ("apparently checking each switch", "looks like a progress or timer bar").
  Neither is a claim about cells that the frames contradict.

Every response is saved whole and read-only in `responses_v2/`, with usage. `scores.json` has the item
scores and `judgement_opus_v2.json` the judgement with file hashes.

## 6. Decision

| Observed result | Next action |
|---|---|
| **Both formats communicate the facts correctly** (observed) | **Take both into the cross-game development checks; examine whether compact B stays understandable** |
| Only one format works | Continue with that format and investigate the other's failure |
| Neither works | Revise the representation or the reading instructions |
| Responses are inconsistent or the reviews disagree | Record as unresolved and diagnose the disagreement |

Both formats pass on this example: two agent readers on version 1 and four Opus responses on version 2,
with no disagreement between repeats. B does it in 843 fewer older-memory tokens than A.

What goes into the cross-game checks:

- Both formats with the version 2 instructions, on the protocol's development cases.
- For B, cases where the earlier board differs from the current one in many cells, and cases across a
  reset or level change, where "same as now" carries less.
- For A, the fact that one record already fills the 2,048 allowance.

## Limits

- One record, one game, one decision. The earlier and current settings in this example were chosen from a
  repeat, so a reader who always answers "same" is not caught on question 3. Questions 1 and 2 do not have
  that weakness.
- A pass shows the facts can be read. It does not show that Opus would use them when choosing an action.
- Two requests per format is enough to catch gross failure, not to estimate an error rate.
- The questions told the reader where the switches and the piece are. In play Opus gets no such pointer.
- G1 to G3 and R1 still decide whether training may expand.

## Code

`research/complete_evidence_v1/readability_case.py` (builds the inputs; pass `2` for version 2), `readability_run.py`
(the four requests), `readability_judge.py` (scoring).
