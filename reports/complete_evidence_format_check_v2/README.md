# B version 2, the rerendered 20 cases, the staged review packet and the exposure ledger

Prepared 2026-11-14. Protocol revision 11. No Opus generation request was made. Training and the full
G2 batch stay paused. The first format check (`../complete_evidence_format_check_v1/`) is unchanged.

**Result.** B now states its starting-board mode in every record, and the contradictory wording is gone.
Under the same rule for all 20 cases it rebuilds every frame, fits 2,048 tokens in 18 cases and 1,024 in
11. The bp35 description that failed the scorer limit now fits under a lossless rule, but bp35 as a game
is still not supported: 8 of 20 sampled bp35 decisions remain over the limit.

Decisions in force for this representation:

| Setting | Value |
|---|---|
| Working format | B version 2 (`M-ref-v2`), with an explicit full-board mode |
| Older-memory allowance | 2,048 tokens working, 1,024 secondary; instructions, headers and provenance counted inside it |
| 512 tokens | Retired as an active budget; kept as a recorded feasibility failure (0 of 20 packs in A, B version 1 and B version 2) |
| Scorer limits | 4,096 description / 8,192 pair, provisional |

Phase 1 still needs evidence sufficiency, human agreement, actor benefit and ranking headroom. This
package shows encoding and size only.

## 1. B version 2

Code: `m_ref2` and `pack_b2` in `research/complete_evidence_v1/formats_v2.py`. B version 1 is untouched.

- Every record carries a line `start board: from current` or `start board: full`.
- The rule that picks the mode is unchanged: whichever writes the earlier board in less text.
- The instructions contain one paragraph per mode and include only the modes present in the pack. The
  sentence "does not print its board before the action" now appears only beside `from current`.
- A pack names the reference board in its header only when some record uses it.
- **Mixed packs** carry both paragraphs, each tied to its own marker. None of the 20 cases is mixed, so
  one mixed pack was built to exercise that path: ls20 decision 82 with records 10 (full) and 61 (from
  current), 1,719 tokens, both records rebuilt exactly (`packs/constructed_mixed_ls20_d82_B2.txt`). It is
  not one of the 20 cases.

Instruction and header overhead, in Opus tokens: 484 for a from-current record (488 for two), 398 for a
full-board record. B version 1 was 464 in both modes; A was 359.

## 2. The 20 cases, rerendered

Same frozen cases, same rule for each, no case-specific repair. Tokens are Opus estimates from the
counting endpoint, logged with their payloads. "Record" is the record or records alone; "Pack" is the
complete older-memory section.

| Case | Type | Game | Decision | Earlier action(s) | Frames | Start board | Record | Pack B v2 | Pack B v1 | Pack A | Fits 2,048 | Fits 1,024 | 512 (retired) | All frames rebuilt | Pack sha256 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D01 | level/reset | ls20 | 82 | 10 | 1 | full | 876 | 1,274 | 1,335 | 1,229 | yes | no | no | yes | `9ba25a7dbeac` |
| D02 | level/reset | ka59 | 33 | 5 | 1 | full | 556 | 954 | 1,015 | 909 | yes | yes | no | yes | `59c06d4e920d` |
| D03 | level/reset | tn36 | 92 | 59 | 1 | from current | 164 | 648 | 622 | 1,453 | yes | yes | no | yes | `e7702949357f` |
| D04 | level/reset | tn36 | 76 | 29 | 1 | from current | 190 | 674 | 648 | 1,453 | yes | yes | no | yes | `ed8751e38211` |
| D05 | delayed | lf52 | 85 | 46 | 3 | from current | 1,130 | 1,614 | 1,588 | 2,891 | yes | no | no | yes | `06e32b46e4fe` |
| D06 | delayed | bp35 | 75 | 60 | 5 | from current | 1,848 | 2,332 | 2,306 | 3,864 | no | no | no | yes | `9d071052474d` |
| D07 | delayed | vc33 | 97 | 86 | 44 | from current | 2,221 | 2,705 | 2,679 | 2,666 | no | no | no | yes | `6d0927a3fc70` |
| D08 | delayed | cd82 | 27 | 18 | 15 | from current | 1,021 | 1,505 | 1,479 | 1,802 | yes | no | no | yes | `32ab7b900e87` |
| D09 | conflicting | ka59 | 97 | 82, 83 | 1, 1 | from current | 462 | 950 | 918 | 2,241 | yes | yes | no | yes | `533ced749f12` |
| D10 | conflicting | vc33 | 43 | 25, 32 | 1, 1 | from current | 804 | 1,292 | 1,260 | 2,425 | yes | no | no | yes | `ecde202145c5` |
| D11 | conflicting | cd82 | 92 | 53, 68 | 1, 1 | from current | 1,550 | 2,038 | 2,006 | 3,401 | yes | no | no | yes | `79da9ce47ae1` |
| D12 | conflicting | ka59 | 95 | 73, 86 | 1, 1 | from current | 512 | 1,000 | 968 | 2,195 | yes | yes | no | yes | `2939f52e283d` |
| D13 | spatial | ls20 | 59 | 43 | 1 | from current | 250 | 734 | 708 | 1,643 | yes | yes | no | yes | `5feb4da287c4` |
| D14 | spatial | cd82 | 25 | 15 | 1 | from current | 788 | 1,272 | 1,246 | 1,409 | yes | no | no | yes | `e7c167b8e068` |
| D15 | spatial | vc33 | 66 | 54 | 1 | from current | 286 | 770 | 744 | 1,031 | yes | yes | no | yes | `c0f714f3514f` |
| D16 | spatial | ka59 | 81 | 56 | 1 | from current | 300 | 784 | 758 | 1,319 | yes | yes | no | yes | `673c83fbb4d0` |
| D17 | ordinary | tn36 | 96 | 86 | 1 | from current | 200 | 684 | 658 | 1,453 | yes | yes | no | yes | `fdd438651fa4` |
| D18 | ordinary | ls20 | 49 | 35 | 1 | from current | 286 | 770 | 744 | 1,707 | yes | yes | no | yes | `e9c9b127c262` |
| D19 | ordinary | cd82 | 85 | 48 | 1 | from current | 800 | 1,284 | 1,258 | 1,795 | yes | no | no | yes | `396d85bc6b42` |
| D20 | ordinary | vc33 | 72 | 63 | 1 | from current | 332 | 816 | 790 | 1,055 | yes | yes | no | yes | `e86cbc93697b` |

| Complete pack fits | 2,048 | 1,024 | 512 (retired) |
|---|---|---|---|
| B version 2 | 18 of 20 | 11 of 20 | 0 of 20 |
| B version 1 | 18 of 20 | 11 of 20 | 0 of 20 |
| A | 13 of 20 | 1 of 20 | 0 of 20 |

- **Every original frame was rebuilt** from the B version 2 text in all 24 records.
- **Full-board mode (D01, D02):** packs are 61 tokens smaller than in version 1 and no longer misdescribe
  themselves. They are 45 tokens larger than A's.
- **From-current mode (18 cases):** packs are 26 tokens larger than in version 1 (32 with two records),
  the cost of stating the mode.
- **Still over 2,048:** D06 (bp35, 5 frames, 2,332) and D07 (vc33, 44 frames, 2,705). Both keep every
  intermediate frame and stay recorded as failures.
- **Tight:** D11 is 10 tokens under 2,048.

Per game:

| Game | Cases | Packs within 2,048 | Packs within 1,024 | Cases over 2,048 |
|---|---|---|---|---|
| bp35 | 1 | 0 | 0 | D06 |
| cd82 | 4 | 4 | 0 | none |
| ka59 | 4 | 4 | 4 | none |
| lf52 | 1 | 1 | 0 | none |
| ls20 | 3 | 3 | 2 | none |
| tn36 | 3 | 3 | 3 | none |
| vc33 | 4 | 3 | 2 | D07 |

Full hashes are in `results.json`; hashes of the other package files are in `MANIFEST.json`.

## 3. Scorer limits and the description

The description must fit 4,096 tokens and each description-record pair 8,192. Two description rules
were measured side by side:

- **Original** (`Q-key-v1`): current board, then the last two responses as changes.
- **Shift rule** (`Q-key-v2`, new, separately versioned): the same, but a frame may be written against the
  board before, the previous frame or the current board, and against any of them moved by up to 8 cells.
  Runs of identical frames are written once. It is exact: every recent frame decoded back correctly.

| Case | Reference board | Description, original rule | Description, shift rule | Shift used | Rebuilds recent frames | Within 4,096 (original / shift) | All pairs within 8,192 (original / shift) |
|---|---|---|---|---|---|---|---|
| D01 | `o82` `4edbe4b0c82b` | 1,301 | 1,250 | no | yes | yes / yes | yes / yes |
| D02 | `o33` `de1e1f10c472` | 1,215 | 1,162 | no | yes | yes / yes | yes / yes |
| D03 | `o92` `43b710a4c43f` | 855 | 836 | no | yes | yes / yes | yes / yes |
| D04 | `o76` `d5bc9cb0e317` | 853 | 833 | no | yes | yes / yes | yes / yes |
| D05 | `o85` `87292e5cccfc` | 2,079 | 1,789 | no | yes | yes / yes | yes / yes |
| D06 | `o75` `1997f8d49fe1` | 8,839 | 3,574 | yes | yes | no / yes | no / yes |
| D07 | `o97` `bb1776778cca` | 2,517 | 2,341 | no | yes | yes / yes | yes / yes |
| D08 | `o27` `9bfb1685bb8f` | 1,025 | 860 | no | yes | yes / yes | yes / yes |
| D09 | `o97` `ee2eaee3b699` | 954 | 910 | no | yes | yes / yes | yes / yes |
| D10 | `o43` `75d514cec217` | 886 | 844 | no | yes | yes / yes | yes / yes |
| D11 | `o92` `db20552f80a6` | 1,734 | 1,517 | no | yes | yes / yes | yes / yes |
| D12 | `o95` `94635d9584ba` | 922 | 900 | no | yes | yes / yes | yes / yes |
| D13 | `o59` `359278bf3d42` | 1,084 | 1,048 | no | yes | yes / yes | yes / yes |
| D14 | `o25` `0d699ae67570` | 1,050 | 869 | no | yes | yes / yes | yes / yes |
| D15 | `o66` `3dfe5ee2c0d9` | 681 | 635 | no | yes | yes / yes | yes / yes |
| D16 | `o81` `e07644b74cf8` | 1,091 | 1,033 | no | yes | yes / yes | yes / yes |
| D17 | `o96` `def743761e8d` | 1,223 | 1,186 | no | yes | yes / yes | yes / yes |
| D18 | `o49` `9f7ba26dbdad` | 1,237 | 1,196 | no | yes | yes / yes | yes / yes |
| D19 | `o85` `c1e46c22e400` | 3,409 | 3,344 | no | yes | yes / yes | yes / yes |
| D20 | `o72` `215c9fe4b430` | 715 | 672 | no | yes | yes / yes | yes / yes |

On the 20 cases the shift rule brings the bp35 description from 8,839 to 3,574 tokens, so all 20
descriptions and all pairs fit.

**Across games it does not close the problem.** On 500 decisions, 20 per game:

| | Original rule | Shift rule |
|---|---|---|
| Descriptions within 4,096 | 479 of 500 | 489 of 500 |
| Largest description | 48,315 | 11,659 |
| Rebuilds every recent frame | not checked | yes, all 500 |

- Decisions still over the limit: bp35 8; r11l 1; sb26 1; tr87 1.
- bp35 is the pattern: after a long scrolling response, the two recent responses alone exceed the limit.
  The isolated sb26, tr87 and r11l cases follow responses of 23 to 328 frames.

**Scope limit, stated plainly.** With these limits the scorer cannot be given a complete description for
8 of 20 sampled bp35 decisions, nor for a few decisions after very long animations in other games. Those
decisions count as size failures. Nothing is cut to make them fit, and G1 is not passed for them. Unless a
later versioned rule supports them, results must be reported as excluding such decisions, with the count
of exclusions.

The shift rule has not been read by any person or model. It changes only the scorer's description, not
the records and not Opus's input.

## 4. Staged review packet

`review_packet/` holds the protocol's full-history subset: 12 of the 20 cases, three per contrasting
type from three different games each, chosen by seed. `review_packet/README.md` has the rules.

- **Subset:** D01, D02, D04, D05, D06, D07, D10, D11, D12, D14, D15, D16. It was chosen after pack sizes were known and before any scorer
  or reviewer output. It includes both over-allowance cases.
- **Order enforced by folders:** stage 1 is the decision-time input only; stage 2 is every past action
  up to the decision, as pictures, with nothing marking what was selected; stage 3 is the rendered pack;
  stage 4 is the type label.
- **What each reviewer records:** the important questions (stage 1); the observations and sufficient
  groups needed to answer them, with their status (stage 2); which of those survive in the pack and can
  be read there (stage 3); whether the assigned type is meaningful (stage 4).
- **Forms:** four templates in `review_packet/forms/`. Each stage is saved before the next is opened, and
  first submissions are kept unchanged.
- "The pack's record does not matter for any question" is a possible and reportable answer.

Nobody has reviewed anything yet. AI agents can rehearse the procedure; they do not satisfy R1.

## 5. Exposure ledger

`exposure_ledger.json` lists, per game, exactly which records and decisions have been sampled or
inspected. **No game is wholly untouched.**

- Applies to all 25 games: every record was formatted and token-counted in Phase 1, every board was
  compared in the repeat audits, and per-game outcome totals were published.
- The published `records.csv` holds, for every record of every game, the action, frame count, level and
  number of changed cells. Those are outcome-derived values. They have been used only in aggregate.
- 7 development games carry the development cases and all content-level inspection.
- 18 games are **format-exposed**: 8 token-counted records and 20 sampled decisions each, and nothing
  inspected by content.

| Game | Tier | Token-count sample (records) | Scorer sample (decisions / records) | Development cases | Other specific exposure |
|---|---|---|---|---|---|
| ar25 | format-exposed | 8 | 20 / 71 | none | none |
| bp35 | development | 8 | 20 / 72 | D06 | 5 items |
| cd82 | development | 8 | 20 / 71 | D08, D11, D14, D19 | 1 item |
| cn04 | format-exposed | 8 | 20 / 63 | none | none |
| dc22 | format-exposed | 8 | 20 / 67 | none | none |
| ft09 | format-exposed | 8 | 20 / 50 | none | none |
| g50t | format-exposed | 8 | 20 / 72 | none | none |
| ka59 | development | 8 | 20 / 60 | D02, D09, D12, D16 | 1 item |
| lf52 | development | 8 | 20 / 68 | D05 | 3 items |
| lp85 | format-exposed | 8 | 20 / 64 | none | none |
| ls20 | development | 8 | 20 / 74 | D01, D13, D18 | 2 items |
| m0r0 | format-exposed | 8 | 20 / 70 | none | none |
| r11l | format-exposed | 8 | 20 / 66 | none | 1 item |
| re86 | format-exposed | 8 | 20 / 66 | none | none |
| s5i5 | format-exposed | 8 | 20 / 69 | none | none |
| sb26 | format-exposed | 8 | 20 / 73 | none | 1 item |
| sc25 | format-exposed | 8 | 20 / 58 | none | none |
| sk48 | format-exposed | 8 | 20 / 65 | none | none |
| sp80 | format-exposed | 8 | 20 / 64 | none | none |
| su15 | format-exposed | 8 | 20 / 63 | none | none |
| tn36 | development | 8 | 20 / 60 | D03, D04, D17 | 3 items |
| tr87 | format-exposed | 8 | 20 / 74 | none | 1 item |
| tu93 | format-exposed | 8 | 20 / 66 | none | none |
| vc33 | development | 8 | 20 / 67 | D07, D10, D15, D20 | 1 item |
| wa30 | format-exposed | 8 | 20 / 70 | none | none |

The 18 format-exposed games can still supply reserved prediction cases if the target answers stay
concealed and unused, and if the cases avoid the sampled records and decisions in the ledger. That is
weaker than untouched evaluation games and should be reported as such.

## Not done

- No evidence-sufficiency or CBC judgement, and no human review.
- No U, reviewer-grade or best-feasible comparison.
- B version 2 and the shift rule have not been read by any person or by Opus. The rehearsal that passed
  used B version 1 on one tn36 example.
- No Opus generation request.

## Files

`results.json`, `packs/` (20 packs and one constructed mixed pack), `table_*.md`, `q_key2_cross_game.json`,
`constructed_mixed_pack.json`, `exposure_ledger.json`, `MANIFEST.json`, `review_packet/`.
Code: `formats_v2.py` (`m_ref2`, `pack_b2`, `q_key2`), `dev_format_check_v2.py`, `q_key2_check.py`,
`review_packet.py`, `exposure_ledger.py`.
