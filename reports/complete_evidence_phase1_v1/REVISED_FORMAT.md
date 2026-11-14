# Revised record formats: does the tn36 evidence survive within budget?

Run 2026-11-13. Opus budgets unchanged at 512 / 1,024 / 2,048 tokens. No Opus request was
made; all work is on saved inputs, a local scorer and logged token counts.

**Result.** One lossless format passes the tn36 test at 1,024 and 2,048 tokens and fails at 512.

- `M-ref-v1` writes the earlier board as its differences from the current board. The needed record is
  706 to 720 Opus tokens (959 to 973 with its reading note), against 18,853 in the starting format.
- It shows the earlier switch setting and the full returned animation, and decodes back exactly.
- At 512 it fits only if the six intermediate frames are left out (150 tokens), which loses the animation.
- The self-contained lossless format fits 2,048 only. The lossy regional format fits 2,048 only and, in
  one of the two decisions, leaves out three of the five stem switches.

Human reading of the delivered text has not happened, so "visibly preserves" is checked here only by
decoding. This is one game.

## Formats

All rules are fixed and the same for every game (`research/complete_evidence_v1/formats_v2.py`).

| Format | What it writes | Exact? |
|---|---|---|
| `M-key-v1` | The board before the action once (identical rows merged), then each returned frame as ordered changes. Identical frames are written once. | Yes, on its own |
| `M-ref-v1` | The same, but the board before the action is given as its differences from the current board. | Yes, together with the current board |
| `M-region-v1` | Cells that have changed at some point in that level so far, a 9x9 window around a click, a padded box around the change, then ordered changes. | No: other cells are not given |
| `Q-key-v1` | Search description: legal actions, the current board, the last two responses as `M-ref-v1`. | Yes |

Each frame is written against the previous frame or the board before the action, whichever is shorter,
or in full if that is shorter still. A reading note of 227 to 289 Opus tokens explains the syntax.

Decoding check: `M-key-v1` returned every cell for all 2,475 records; `M-ref-v1` and `M-region-v1` were
correct on 1,000 random decision-record pairs (40 per game). `M-region-v1` gives a median of 17% of the
board's cells.

`M-ref-v1` depends on the current board being in the same input. Opus always has it. The scorer has it
because the description contains it.

## tn36 acceptance

Two saved decisions where the agent pressed "run" on a switch setting it had already run with the earlier
run out of view. The needed record is my unreviewed guess; either listed record would do.

- **Decision 54** (before action 55): same setting as the runs at actions 19 and 39, same attempt.
- **Decision 97** (before action 98): same setting as the run at action 60, before a reset.

Opus tokens for the needed record, decision 54 / decision 97:

| Format | Record | With reading note | Fits 512 | Fits 1,024 | Fits 2,048 | Switch setting given | Animation kept |
|---|---|---|---|---|---|---|---|
| Starting spec (`M-rle-v1`, all frames) | 18,853 / 18,861 | not counted | no | no | no | yes | yes |
| `M-key-v1` | 1,654 / 1,668 | 1,874 / 1,888 | no | no | yes | yes | yes |
| `M-ref-v1` | 706 / 720 | 959 / 973 | no | yes | yes | yes | yes |
| `M-ref-v1`, last frame only | 150 / 150 | 403 / 403 | yes | yes | yes | yes | no |
| `M-region-v1` | 1,121 / 1,261 | 1,403 / 1,543 | no | no | yes | 21 of 30 cells / all | yes |
| Changed cells only (`M-diff-v1`, last frame) | 118 / 118 | not counted | yes | yes | yes | no | no |

- "Switch setting given" was checked by decoding the delivered text and comparing the 30 switch cells
  (five bars, five stems) with the saved board.
- In `M-ref-v1` the setting appears as "before vs current: 24 cells" followed by one line for the counter
  row: every other cell, the switches included, was as it is now. That is exact, but a reader has to take
  "same as now" as the statement of the setting. Whether that counts as visible is a reviewer's call.
- `M-region-v1` at decision 54 omits the stems of slots 2, 4 and 5. They had never been toggled by then,
  so they were not "state cells". A switch that has not changed yet is invisible to this format.
- The last-frame-only record says "frames 1-6/7: not included" and that the last frame differs from the
  board before by one counter cell. It keeps "nothing lasting changed" and drops what the program did.

The delivered texts are in `m0_revised_tn36/` (`d54_M-ref-v1_needed_e19.txt` and so on).

### What the untrained scorer did

U scored every older record against the `Q-key-v1` description (855 and 1,226 scorer tokens), and the
shared rule filled each budget. Selection uses a provisional similarity formula (`sim-v0`).

| Format | Rank of needed record, decision 54 (of 52) | Decision 97 (of 95) | Needed record delivered by U |
|---|---|---|---|
| `M-key-v1` | 43 and 46 | 1 | at 2,048 in decision 97 only |
| `M-ref-v1` | 4 and 8 | 23 | at 2,048 in decision 54 only |
| `M-region-v1` | 21 and 17 | 63 | never |

- U's ranks swing between formats and decisions. Two decisions cannot say which format suits it.
- With `M-ref-v1` at 1,024, a reviewer-grade pick (the needed record alone) fits and U does not deliver it
  in either decision. That is the kind of gap G3 is meant to measure; here it is two examples.
- Scoring took 0.5 to 0.9 seconds per pair on an Apple M4 (pairs of 970 to 1,950 tokens).

## Cross-game sizes

Exact rules as above, no per-game tuning. Opus tokens for the same 200 records as before (8 per game),
each paired with a random later decision:

| Record format | Median | Fits 512 | Fits 1,024 | Fits 2,048 |
|---|---|---|---|---|
| Starting spec (`M-rle-v1`, all frames) | 3,994 | 0% | 0% | 10.5% |
| `M-key-v1` | 1,247 | 7.5% | 33.5% | 80.5% |
| `M-ref-v1` | 602 | 40% | 72.5% | 91.5% |
| `M-ref-v1`, last frame only | 491 | 50.5% | 80% | 92% |
| `M-region-v1` (lossy) | 831 | 15.5% | 58% | 88.5% |
| Changed cells only (`M-diff-v1`, all frames; lossy) | 601 | 41.5% | 70% | 86.5% |

- `M-ref-v1` is exact and fits about as often as the lossy changed-cells format.
- `M-region-v1` is larger than `M-ref-v1` and loses information, so it has no advantage here.
- Games differ. With `M-ref-v1` at 1,024, all 8 sampled records fit in 7 games, and fewer than half fit
  in bp35 (0 of 8, median 9,963), lp85 (1), tu93 (2), r11l (3) and sk48 (3).
- "Fits" is one record alone. A set of two or more needs more room, and the reading note costs 260 tokens
  once per request if it is charged to the budget.

Scorer tokens, 4,813 decision-record pairs from 500 decisions (20 per game):

| | Median | Within 768 / 2,048 | Within 2,048 / 4,096 | Within 4,096 / 8,192 |
|---|---|---|---|---|
| `Q-key-v1` description | 1,306 | 17% within 768 | 76% within 2,048 | 96% within 4,096 |
| Pair with `M-ref-v1` | 515 (record) | 16.5% | 75% | 95% |
| Pair with `M-key-v1` | 819 (record) | 16.5% | 75% | 95% |

- The description, not the record, is what breaks the starting 768 limit: one current board has a median
  near 700 scorer tokens before the two recent responses are added.
- The loaded model accepts 8,192 tokens. At that limit 95% of pairs fit; the largest description is
  48,315 tokens, so some decisions still fail.

## Reading packet

`interpretability_packet/` holds one delivered record from each of six games (bp35, lf52, ls20, cd82,
ka59, vc33) in all three formats, chosen by a fixed rule from the size sample, with the current board
each `M-ref-v1` record refers to. No reviewer has read it. Machine decoding shows the cells are there;
it does not show a person or Opus can use them.

## What this does and does not establish

- A useful evidence pack for the tn36 case fits at 1,024 and 2,048 in an exact format. It does not fit
  at 512 without dropping frames.
- Nothing here shows Opus reads `M-ref-v1` correctly. M0 is still incomplete: it needs an Opus response
  and an outcome assessment.
- tn36 is one development case. In the saved run the earlier result did matter there and the notes mostly
  did not hold it (see the README), but one game is not a cross-game training problem.
- Opus token counts are estimates from the token-counting endpoint (free; a real request can differ
  slightly). Every count is in `data/opus_token_count_log.jsonl.gz` with its model ID, exact payload and
  returned value: 3,384 requests, all `claude-opus-5-5`.

## Next steps, in order

1. A person reads the tn36 texts and the packet and says whether the setting and outcome are readable.
2. If so, a small M0 smoke check with a fixed cap, on approval. Proposed: the two tn36 decisions, three
   inputs each (shared input only; plus the needed `M-ref-v1` record; plus a same-length unrelated
   record), two requests per input, 12 requests in total, outcome fixed beforehand as "does not press run
   on the already-run setting". A pass allows further diagnostics; it is not G2.
3. The 96-request G2 batch and any reviewed training labels stay on hold.
