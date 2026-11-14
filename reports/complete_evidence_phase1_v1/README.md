# Phase 1 diagnostic: is memory selection worth pursuing? (interim)

Started 2026-11-13. Protocol revision 11. No money spent: everything uses saved runs, a local tokenizer
and scoring model, and the free token-counting endpoint. No Opus request has been made.

**Decision so far: revise.** The measurements reject the starting representation at its specified
limits. They do not reject the memory-selection hypothesis. A revised lossless format carries the tn36
evidence within 1,024 and 2,048 Opus tokens: see [REVISED_FORMAT.md](REVISED_FORMAT.md).

| Phase 1 question | Answer so far | Basis |
|---|---|---|
| Does the needed evidence fit the proposed limits? | Not in the starting format; in a revised format, yes at 1,024 and 2,048 for the tn36 case | Measured |
| Is useful older evidence missing from Opus's input? | Yes in one development case (tn36); not assessable in most games | Automatic audit plus a case check, one saved run |
| Does it help when supplied? | Not tested | Needs a readable pack, then Opus requests |
| Can U's selections be compared with reviewer-grade and best-feasible sets? | Not yet | Needs reviewer grades |

## Decisions in force (2026-11-13)

1. Opus budgets stay at 512 / 1,024 / 2,048 while revised representations are tested. The scorer's pair
   limit may be tested at 8,192.
2. The second reviewer is unassigned until a person confirms. Another model does not satisfy R1. Machine
   encoding and size checks continue; reviewed training labels stay blocked.
3. The 96-request G2 batch is on hold. The next Opus work is a small, bounded M0 smoke check, after a
   useful pack fits and a person can read it.
4. M0 is incomplete: it still needs an Opus response and an outcome assessment.

## Data, and what it stands for

`opus55-competition-20261106T054112Z` (scorecard `09cc9d25`): the repository's stateless agent
(`research/claude_arc_v1`) with Opus 5.5, 25 games, 100 actions each, with every request and returned
frame saved.

**This run is a proxy for the proposed study, not a sample of it.** It matches the access rules in A.2
(one fresh request per action, no resumed session, no tools) but the agent saw its last 8 actions, only
the last frame of each response, and carried up to 8 self-written notes. It supports format measurements
and saved-decision diagnostics. It does not measure how a note-free agent would play.

All 25 games count as development-exposed.

## 1. Sizes: the starting format does not fit

Every lossless format decoded back to the original cells for all 2,475 records (0 mismatches).

Scoring-model tokens (`BAAI/bge-reranker-v2-m3`, revision `953dc6f`), all records, no cutting:

| Text | Median | 90th pct | Largest | Within its limit |
|---|---|---|---|---|
| Description, Q-exec-rle-v1, all frames | 3,662 | 22,801 | 568,136 | 0.3% within 768 |
| Description, last frame only | 2,597 | 4,176 | 6,004 | 0.3% within 768 |
| Description, last frame only, identical rows merged | 1,516 | 3,024 | 5,437 | 20% within 768 |
| Record, M-rle-v1, all frames | 3,007 | 12,642 | 557,362 | 4% within 1,276 |
| Record, last frame only, identical rows merged | 1,517 | 3,070 | 5,428 | 34% within 1,276 |
| Record, M-diff-v1 (changed cells only), all frames | 490 | 1,744 | 129,021 | 80% within 1,276 |

1,276 is what is left for a record when the description uses its full 768 of the 2,048 pair limit.

- **Pairs that fit as specified: 3 of 124,050** (every decision paired with every earlier record).
- One board alone has a median of 1,262 tokens, so the current board by itself exceeds 768 in 86% of
  decisions. Merging identical rows brings the median to 717.
- A third of responses return more than one frame (median 1, 90th percentile 8, largest 328).
- The loaded model accepts 8,192 tokens (`max_position_embeddings` 8,194), not 2,048.

Opus tokens (`claude-opus-5-5`), random sample of 200 records, 8 per game:

| Record format | Median | Fits 512 | Fits 1,024 | Fits 2,048 |
|---|---|---|---|---|
| M-rle-v1, all frames (starting spec) | 3,994 | 0% | 0% | 10.5% |
| M-rle-v1, last frame only | 3,237 | 0% | 0% | 15% |
| Merged rows, all frames | 2,529 | 1% | 18% | 41% |
| Merged rows, last frame only | 2,039 | 1.5% | 23% | 53% |
| M-diff-v1, all frames | 601 | 41.5% | 70% | 86.5% |
| M-diff-v1, last frame only | 494 | 52.5% | 80.5% | 91% |

"Fits" means one record alone is within the limit. The saved run's real requests had a median of 12,692
input tokens.

**About the Opus counts.** They come from the token-counting endpoint, which is free and which Anthropic
describes as an estimate: a real request can differ slightly. Every count in these reports is in
`data/opus_token_count_log.jsonl.gz` with its model ID, exact request payload and returned value (3,384
requests). The first sample was re-counted through that log and matched exactly.

## 2. Is older evidence missing? Automatic audit

The audit looks for the agent repeating an action from a board it had already acted from, where the
earlier try was older than the 8 actions it could see. **It reports a detected pattern, not a rate of
forgetting.** A repeat can be deliberate, and most forgetting would not show up as an exact repeat.

Most games move a step counter on every action, so boards never match exactly. The counter is estimated
from the run and blanked before boards are compared (`audit_repeats_masked.py`).

| Step | Count |
|---|---|
| Action records | 2,475 |
| Excluded: resets sent by the controller after a game over, not chosen by the model | 8 |
| Eligible actions | 2,467 |
| In the 15 games where a counter could be estimated | 1,493 |
| In the 10 games where it could not (coverage unknown) | 974 |
| Assessable: the agent stood on a board it had acted from earlier in the same attempt, out of view | 59 |
| Detected: it repeated an action already taken from that board | 27 |

- The 27 are 46% of the 59 assessable actions, 1.8% of the 1,493, and 1.1% of all eligible actions. The
  last two figures are diluted by actions where a repeat was never possible.
- Assessable actions occur in 5 games: tn36 27, lf52 22, cd82 5, ka59 4, vc33 1. Detected repeats: tn36
  20, cd82 3, ka59 3, lf52 1. In lf52 the agent returned to known boards 22 times and repeated once.
- The 10 games without a counter estimate are ar25, ft09, lp85, ls20, sb26, sc25, sk48, tr87, tu93 and
  wa30. Nothing can be said about them. In the other 10 games with a counter estimate, no board was
  revisited, or the estimate missed part of the counter; the audit cannot tell which.
- A further 34 repeats follow a reset or level change (bp35 21, su15 5, tn36 8): replaying a known path.
- 204 actions (8.3%) did nothing beyond moving the counter.
- The agent had notes. In 27% of note entries after action 8 the cited evidence was partly or wholly
  older than the visible window, so the notes were already carrying older information.

## 3. tn36: a focused development case

In tn36 the agent sets ten switches and presses "run". `tn36_case.py` checks each run against the saved
boards and against the exact notes the agent was given (`data/tn36_case.json`).

| | Runs |
|---|---|
| Runs in the game | 26 |
| From a board already run (counter row ignored) | 10 |
| ... returning frames identical to the earlier run | 10 |
| ... with the earlier run still among the 8 shown actions | 1 |
| ... with the earlier run out of view | 9 (6 in the same attempt, 3 across the reset) |
| ... of those 9, with any note citing an earlier run from that board | 1 |

- **The earlier result mattered.** In all 10 cases the earlier run predicted the repeat frame for frame,
  so the repeat produced no new information.
- **The notes mostly did not hold it.** In 8 of the 9 out-of-view repeats no note cited an earlier run
  from that board. In the ninth (action 45) one note cited the run at action 30 and said only that no run
  so far had left a lasting change.
- Example: at action 40 a note read "Five stem-only slots do not move the piece into the cup" (from the
  run at 39). Before action 55 that note was gone, and a new tentative note proposed the same setting.
- Up to 45 of the game's 99 actions went into those 9 repeats, counting each run and the switch clicks
  since the previous run.
- No run ever completed the level. This shows redundant tests that a record would have predicted; it does
  not show that the record would have led to a solution.

tn36 is one game. It supports a development case and says nothing yet about a cross-game training
problem. The long stalls elsewhere (lf52 from action 8, bp35 from action 17) are not repeats; from the
notes they look like undiscovered mechanics, but no reviewer has checked.

## 4. M0: first worked example (starting formats)

One tn36 decision run through formatting, scoring and selection: after 97 actions, where the agent
pressed "run" on the setting it had run at action 60. Saved-input-only, so M0 is not complete.

| Variant | Pairs scored | Rank of action 60 | One record, Opus tokens | Delivered at 512 / 1,024 / 2,048 |
|---|---|---|---|---|
| A. Starting spec, limits 768 / 2,048 | 0 of 95 | not scored | 18,861 | nothing |
| B. Full boards, last frame, merged rows | 95 | 91 of 95 | about 2,040 | no / no / no |
| C. Changed cells, all frames | 95 | 2 of 95 | 4,958 for a "run" record | no / no / no |
| D. Changed cells, last frame only | 95 | 21 of 95 | 118 | no / no / no |

B, C and D use an 8,192 pair limit.

- **A:** the description alone is 11,891 scorer tokens against a limit of 768.
- **B:** U's scores are nearly flat, and one record fills the whole 2,048 limit.
- **C:** U ranks earlier "run" presses first, but each is about 4,700 to 5,000 Opus tokens. They are also
  the only long records, so U may be ranking length.
- **D:** every record fits, but a "run" record reads "one counter cell changed"; the switch setting is in
  the unchanged part of the board.

So in the starting formats, what keeps the needed fact does not fit, and what fits drops it. The revised
formats in [REVISED_FORMAT.md](REVISED_FORMAT.md) address this. Files are in `m0_tn36_d97/`.

## Gate status

| Gate | Status | What is missing |
|---|---|---|
| G1 inputs retain the evidence | Starting format fails on size; revised format untested by reviewers | Two-reviewer exact-input checks, executable-versus-human description check |
| G2 reviewed evidence changes outcomes | On hold | A readable pack, the M0 smoke check, then the reserved study |
| G3 scoring can deliver improvement | Not started | Reviewer grades on 12 decisions |
| R1 independent human review | Not started | A second human reviewer, unassigned |

## Files

- `research/complete_evidence_v1/`
  - `records.py`: stored records from a saved run. `formats.py`: starting formats. `formats_v2.py`: revised
    formats and decoders. `check_formats_v2.py`: decoding check.
  - `measure_sizes.py`, `measure_opus_sizes.py`, `measure_sizes_v2.py`: sizes. `opus_count.py`: logged
    token counting.
  - `audit_repeats.py` (exact boards), `audit_repeats_masked.py`, `audit_inert_types.py`, `tn36_case.py`.
  - `m0_example.py`, `m0_revised.py`, `make_packet.py`.
- `data/`: `scorer_sizes.json`, `records.csv`, `decisions.csv`, `opus_sizes.json`, `opus_sample.csv` (first
  round); `sizes_v2.json`, `scorer_pairs_v2.csv`, `opus_sample_v2.csv` (revised formats);
  `repeat_audit*.json`, `inert_type_audit.json`, `tn36_case.json`; `opus_token_count_log.jsonl.gz`.
- `m0_tn36_d97/`, `m0_revised_tn36/`, `interpretability_packet/`: exact inputs and delivered texts.
- The Python environment is `.cache/complete_evidence/venv` (local, not in the repository).
