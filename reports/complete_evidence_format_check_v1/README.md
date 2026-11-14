# Cross-game format check: 20 development decisions, formats A and B

Run 2026-11-14. Protocol revision 11, Appendix D. No Opus generation request was made: Opus token counts
come from the free token-counting endpoint (estimates, each logged with its payload). Training and the
full G2 batch stay paused.

**Result.** Both formats rebuilt every original frame in all 20 cases. B's complete pack fits more often
than A's, and neither fits at 512.

| Complete older-memory pack fits | 512 | 1,024 | 2,048 |
|---|---|---|---|
| A (`M-key-v1`) | 0 of 20 | 1 of 20 | 13 of 20 |
| B (`M-ref-v1`) | 0 of 20 | 11 of 20 | 18 of 20 |

- **512 cannot hold a complete pack.** The header and reading instructions alone are 359 tokens for A and
  464 for B, before any record.
- **B never costs more evidence than A.** Its records are smaller in 18 cases and one token larger in 2.
- **B has a defect across levels.** In the two earlier-level cases it falls back to printing the full
  board, so it carries A's content with B's longer instructions, which then say the board "is not printed".
- **Two cases fail 2,048 in both formats:** a 5-frame bp35 record and a 44-frame vc33 record.
- **The proposed scorer limits fail in 18 of 20 cases** because the description exceeds 768 tokens. At
  4,096 / 8,192, 19 of 20 pass.

Whether each record is sufficient evidence for its decision has not been judged; that and CBC wait for
human review.

## How the 20 cases were frozen

`cases_frozen.json` (sha256 `ed7da7392f356ca6...`, read-only) was written by
`research/complete_evidence_v1/dev_cases.py` before any record was formatted or counted.

- **Source:** the saved stateless run `opus55-competition-20261106T054112Z`, one episode per game.
- **Games:** only the seven already used for development (bp35, lf52, ls20 named in the protocol; tn36,
  cd82, ka59, vc33 used in Phase 1). The other 18 games supply no development case, so the reserved 12
  decisions can still come from separate episodes.
  **Correction, 2026-11-14:** this line first said the other 18 games "are untouched". That was wrong. The
  Phase 1 size benchmark measured every record of every game and token-counted 8 sampled records per game,
  so those 18 games have format-development exposure. The exact exposure is in
  `../complete_evidence_format_check_v2/exposure_ledger.json`. No result in this report changes.
- **A case** is a decision plus the earlier record or records a reader would need. Every earlier record
  is at least 9 actions before its decision.
- **Types** are assigned by fixed rules from the frames, in this order. No person has reviewed them.

| Type | Rule |
|---|---|
| Level/reset | The earlier record is from an earlier level (2 cases) or an earlier attempt of the same level (2 cases) |
| Delayed | 3 or more returned frames, with an intermediate frame that differs from the last |
| Conflicting | Two records, same action, same level and attempt: one changed the board, the later one did nothing |
| Spatial | One returned frame whose change is mostly one shape moved to a new place |
| Ordinary | One returned frame, same level and attempt, none of the above |

- Choices among eligible candidates are random with seed 20261114, spread across games.
- "Changed" and "did nothing" ignore the step counter, estimated as in the Phase 1 audit.

Eligible candidates per game (level/reset / delayed / conflicting / spatial / ordinary):

| Game | Candidates |
|---|---|
| bp35 | 0 / 51 / 0 / 0 / 0 |
| lf52 | 0 / 58 / 0 / 0 / 0 |
| ls20 | 57 / 1 / 0 / 68 / 2 |
| tn36 | 40 / 19 / 0 / 0 / 61 |
| cd82 | 19 / 18 / 12 / 6 / 50 |
| ka59 | 22 / 2 / 8 / 55 / 24 |
| vc33 | 54 / 3 / 1 / 18 / 32 |

What I had already seen before freezing: Phase 1 size statistics for these games, including that bp35
records are large. The rules and the seed do not use sizes.

Limits of the sample:

- Both earlier-attempt cases are tn36, the only one of the seven games with a one-frame record before a
  reset. bp35 and lf52 supply only delayed cases, because every response there returns several frames.
- Each type comes from at least two games; the 20 cases cover all seven.
- The sample is mixed on purpose and says nothing about how often each situation occurs.

## Per-case results

Same fixed rules for every case: the record formats and version 2 reading instructions from the
readability rehearsal, with no case-specific change. "Record" is the Opus tokens of the record or records
alone. "Pack" is the complete older-memory section: header, provenance line, reading instructions and the
records.

| Case | Type | Game | Decision | Earlier action(s) | Frames | Board differing from current | A record / pack | B record / pack | A pack fits 512 / 1,024 / 2,048 | B pack fits 512 / 1,024 / 2,048 | B gives earlier board as | All frames rebuilt A / B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D01 | level/reset | ls20 | 82 | 10 | 1 | 43% | 870 / 1,229 | 871 / 1,335 | no / no / yes | no / no / yes | full board (fallback) | yes / yes |
| D02 | level/reset | ka59 | 33 | 5 | 1 | 86% | 550 / 909 | 551 / 1,015 | no / yes / yes | no / yes / yes | full board (fallback) | yes / yes |
| D03 | level/reset | tn36 | 92 | 59 | 1 | 1% | 1,094 / 1,453 | 158 / 622 | no / no / yes | no / yes / yes | differences from current | yes / yes |
| D04 | level/reset | tn36 | 76 | 29 | 1 | 1% | 1,094 / 1,453 | 184 / 648 | no / no / yes | no / yes / yes | differences from current | yes / yes |
| D05 | delayed | lf52 | 85 | 46 | 3 | 4% | 2,532 / 2,891 | 1,124 / 1,588 | no / no / no | no / no / yes | differences from current | yes / yes |
| D06 | delayed | bp35 | 75 | 60 | 5 | 35% | 3,505 / 3,864 | 1,842 / 2,306 | no / no / no | no / no / no | differences from current | yes / yes |
| D07 | delayed | vc33 | 97 | 86 | 44 | 22% | 2,307 / 2,666 | 2,215 / 2,679 | no / no / no | no / no / no | differences from current | yes / yes |
| D08 | delayed | cd82 | 27 | 18 | 15 | 1% | 1,443 / 1,802 | 1,015 / 1,479 | no / no / yes | no / no / yes | differences from current | yes / yes |
| D09 | conflicting | ka59 | 97 | 82, 83 | 1, 1 | 2%, 2% | 1,878 / 2,241 | 450 / 918 | no / no / no | no / yes / yes | differences from current | yes / yes |
| D10 | conflicting | vc33 | 43 | 25, 32 | 1, 1 | 7%, 5% | 2,062 / 2,425 | 792 / 1,260 | no / no / no | no / no / yes | differences from current | yes / yes |
| D11 | conflicting | cd82 | 92 | 53, 68 | 1, 1 | 10%, 8% | 3,038 / 3,401 | 1,538 / 2,006 | no / no / no | no / no / yes | differences from current | yes / yes |
| D12 | conflicting | ka59 | 95 | 73, 86 | 1, 1 | 1%, 2% | 1,832 / 2,195 | 500 / 968 | no / no / no | no / yes / yes | differences from current | yes / yes |
| D13 | spatial | ls20 | 59 | 43 | 1 | 2% | 1,284 / 1,643 | 244 / 708 | no / no / yes | no / yes / yes | differences from current | yes / yes |
| D14 | spatial | cd82 | 25 | 15 | 1 | 7% | 1,050 / 1,409 | 782 / 1,246 | no / no / yes | no / no / yes | differences from current | yes / yes |
| D15 | spatial | vc33 | 66 | 54 | 1 | 10% | 672 / 1,031 | 280 / 744 | no / no / yes | no / yes / yes | differences from current | yes / yes |
| D16 | spatial | ka59 | 81 | 56 | 1 | 3% | 960 / 1,319 | 294 / 758 | no / no / yes | no / yes / yes | differences from current | yes / yes |
| D17 | ordinary | tn36 | 96 | 86 | 1 | 1% | 1,094 / 1,453 | 194 / 658 | no / no / yes | no / yes / yes | differences from current | yes / yes |
| D18 | ordinary | ls20 | 49 | 35 | 1 | 2% | 1,348 / 1,707 | 280 / 744 | no / no / yes | no / yes / yes | differences from current | yes / yes |
| D19 | ordinary | cd82 | 85 | 48 | 1 | 9% | 1,436 / 1,795 | 794 / 1,258 | no / no / yes | no / no / yes | differences from current | yes / yes |
| D20 | ordinary | vc33 | 72 | 63 | 1 | 7% | 696 / 1,055 | 326 / 790 | no / no / yes | no / yes / yes | differences from current | yes / yes |

- Board differing from current: share of the 4,096 cells where the board before the earlier action
  differs from the decision's current board.
- Every original frame was rebuilt from both texts in all 24 records (decoded and compared cell by cell).
- The rendered packs are in `packs/`; `results.json` has every number and the pack hashes.

**Individual record fit against complete pack fit:**

| | 512 | 1,024 | 2,048 |
|---|---|---|---|
| A: each record alone (24 records) | 0 | 10 | 21 |
| A: complete pack (20 cases) | 0 | 1 | 13 |
| B: each record alone (24 records) | 13 | 21 | 23 |
| B: complete pack (20 cases) | 0 | 11 | 18 |

The gap is the instructions and, in the four conflicting cases, the second record. A fits no two-record
case at any budget; B fits all four at 2,048 and two at 1,024.

Complete packs within 1,024 / 2,048, by type:

| Type | A | B |
|---|---|---|
| Level/reset | 1 / 4 | 3 / 4 |
| Delayed | 0 / 1 | 0 / 2 |
| Conflicting | 0 / 0 | 2 / 4 |
| Spatial | 0 / 4 | 3 / 4 |
| Ordinary | 0 / 4 | 3 / 4 |

## Scorer limits

Description is `Q-key-v1` (current board plus the last two responses). A pair is the description plus one
record plus 4 special tokens. Proposed limits are 768 / 2,048; the tested alternative is 4,096 / 8,192.

| Case | Reference board | Description, scorer tokens | Within 768 | Within 4,096 | Largest pair A / B | Pairs within 2,048 (A / B) | Pairs within 8,192 (A / B) |
|---|---|---|---|---|---|---|---|
| D01 | `o82` `4edbe4b0c82b...` | 1,301 | no | yes | 1,958 / 1,958 | no / no | yes / yes |
| D02 | `o33` `de1e1f10c472...` | 1,215 | no | yes | 1,680 / 1,680 | no / no | yes / yes |
| D03 | `o92` `43b710a4c43f...` | 855 | no | yes | 1,564 / 961 | no / no | yes / yes |
| D04 | `o76` `d5bc9cb0e317...` | 853 | no | yes | 1,573 / 976 | no / no | yes / yes |
| D05 | `o85` `87292e5cccfc...` | 2,079 | no | yes | 4,042 / 2,910 | no / no | yes / yes |
| D06 | `o75` `1997f8d49fe1...` | 8,839 | no | no | 11,486 / 10,186 | no / no | no / no |
| D07 | `o97` `bb1776778cca...` | 2,517 | no | yes | 3,979 / 3,843 | no / no | yes / yes |
| D08 | `o27` `9bfb1685bb8f...` | 1,025 | no | yes | 1,957 / 1,608 | no / no | yes / yes |
| D09 | `o97` `ee2eaee3b699...` | 954 | no | yes | 1,805 / 1,126 | no / no | yes / yes |
| D10 | `o43` `75d514cec217...` | 886 | no | yes | 1,693 / 1,234 | no / no | yes / yes |
| D11 | `o92` `db20552f80a6...` | 1,734 | no | yes | 2,890 / 2,353 | no / no | yes / yes |
| D12 | `o95` `94635d9584ba...` | 922 | no | yes | 1,741 / 1,098 | no / no | yes / yes |
| D13 | `o59` `359278bf3d42...` | 1,084 | no | yes | 2,123 / 1,248 | no / no | yes / yes |
| D14 | `o25` `0d699ae67570...` | 1,050 | no | yes | 1,833 / 1,568 | no / no | yes / yes |
| D15 | `o66` `3dfe5ee2c0d9...` | 681 | yes | yes | 1,192 / 873 | yes / yes | yes / yes |
| D16 | `o81` `e07644b74cf8...` | 1,091 | no | yes | 1,896 / 1,290 | no / no | yes / yes |
| D17 | `o96` `def743761e8d...` | 1,223 | no | yes | 1,944 / 1,354 | no / no | yes / yes |
| D18 | `o49` `9f7ba26dbdad...` | 1,237 | no | yes | 2,337 / 1,432 | no / no | yes / yes |
| D19 | `o85` `c1e46c22e400...` | 3,409 | no | yes | 4,441 / 3,931 | no / no | yes / yes |
| D20 | `o72` `215c9fe4b430...` | 715 | yes | yes | 1,233 / 932 | yes / yes | yes / yes |

- The description is within 768 in 2 cases and within 4,096 in 19.
- D06 (bp35) fails both: its description is 8,839 tokens, because the last two responses are themselves
  multi-frame animations.

## Per game

| Game | Cases | A packs within 512 / 1,024 / 2,048 | B packs within 512 / 1,024 / 2,048 | Descriptions within 768 / 4,096 | Cases failing 2,048 in both |
|---|---|---|---|---|---|
| bp35 | 1 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 | D06 |
| cd82 | 4 | 0 / 0 / 3 | 0 / 0 / 4 | 0 / 4 | none |
| ka59 | 4 | 0 / 1 / 2 | 0 / 4 / 4 | 0 / 4 | none |
| lf52 | 1 | 0 / 0 / 0 | 0 / 0 / 1 | 0 / 1 | none |
| ls20 | 3 | 0 / 0 / 3 | 0 / 2 / 3 | 0 / 3 | none |
| tn36 | 3 | 0 / 0 / 3 | 0 / 3 / 3 | 0 / 3 | none |
| vc33 | 4 | 0 / 0 / 2 | 0 / 2 / 3 | 2 / 4 | D07 |

## Where each format works and fails

**A works** for a single one-frame record at 2,048 (12 of 12 such cases) and rebuilds everything. **A
fails** on every two-record case, on three of the four multi-frame cases, and at 1,024 in 19 of 20.

**B works** wherever the earlier board is from the same level: 16 of 18 such cases fit 2,048, including
all four two-record cases and D05 (lf52, 3 frames). **B fails or degrades** in three ways:

1. **Earlier level (D01, D02).** The boards differ in 43% and 86% of cells, so B's own rule prints the
   full board. The result is A's record with instructions 106 tokens longer that describe a "before vs
   current" block the record does not have and say the board is not printed. It still fits 2,048, but the
   instructions are wrong for that record.
2. **Long or large animations (D06, D07).** D06 lists 1,424 differing cells and five frames (2,306
   tokens). D07 has 44 frames (2,679). Neither format fits.
3. **Readability with many differences is untested.** The rehearsal's B record differed from the current
   board only in a counter row. D06 and D07 ask the reader to apply hundreds of changes.

## Next representation decision (proposed)

1. **Carry B forward as the working format.** It is exact, never needs more evidence tokens than A, and
   its complete pack fits in 18 cases against 13.
2. **Add one deterministic switching rule, as a new version before any further evaluation:** when B's
   earlier board falls back to a full board, render that record as A with A's instructions. On D01 and D02
   this saves 106 tokens and removes the false statement. The rule for a pack that mixes the two kinds of
   record has to be written down with it. Nothing in this report used that rule.
3. **Decide how instructions are charged.** At 512 the instructions leave 48 tokens for B's evidence. Either
   they move to the fixed shared input and stop counting against the older-memory allowance, or 512 is
   dropped as a budget. This is a protocol choice, not a format fix.
4. **Leave long animations as recorded failures for now.** Dropping intermediate frames would fit D06 and
   D07 but loses what delayed cases are about. That trade needs reviewer judgement on real delayed cases.
5. **Replace the proposed scorer limits.** 768 / 2,048 fails 18 of 20 cases; 4,096 / 8,192 fits 19.

## Not done here

- No evidence-sufficiency or CBC judgement. The earlier records were picked by rule, not because a
  reviewer found them necessary.
- No human has read these packs, and the type labels are unreviewed.
- No U, reviewer-grade or best-feasible comparison.
- No Opus generation request.

## Files

`cases_frozen.json` (the frozen cases), `results.json` (all measurements), `packs/` (40 rendered packs),
`table_*.md` (the tables above). Code: `research/complete_evidence_v1/dev_cases.py` and
`dev_format_check.py`.
