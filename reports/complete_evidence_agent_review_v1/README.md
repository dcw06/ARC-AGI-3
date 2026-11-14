# Two-role agent review of the 12 frozen cases

Run 2026-11-14. B version 2, 2,048-token allowance, case selection unchanged. No Opus generation request
was made; training stays paused. The reviewers were AI agents on this session's subagent model, not
people and not Opus. Because the two roles are different, this does not measure agreement between
reviewers, and it does not count towards R1.

**Result.** The packs are readable, but they mostly do not hold the evidence that matters.

- **Reading:** the pack reader recovered every checked fact in all 12 packs: 197 of 197 checks against
  the original frames, including 97 of 97 cell probes.
- **Evidence exists:** the history reviewer found older evidence for 59 of 60 uncertainties (35 "yes",
  24 "partly", 1 "no"). These are one agent's judgements; see "How far to trust this".
- **Selection is the failure:** in 0 of 12 cases does the pack hold a complete sufficient set of records
  for any uncertainty. In 8 cases the pack's record was not cited for any uncertainty at all. In 4 it was
  cited as one piece of a larger set.
- **Fit:** 10 of 12 packs fit 2,048; D06 and D07 stay delivery failures.

So no case yet has all three properties with one and the same pack. For 20 uncertainties across 10
cases, the history reviewer named a sufficient set that does fit 2,048 as a B version 2 pack. Those are
the candidates, pending a reading check of those packs.

## How it was run

- **Frozen first.** `frozen_inputs.json` records the 12 cases, the pack hashes (identical to the format
  check) and the decision-input hashes.
- **Role 1, evidence needed:** one fresh agent per case. Step 1 gave it only the decision-time input; it
  saved its uncertainties. That file was copied and locked, and only then were the history files placed
  in its folder: an index of every past action, per-frame change lists, board text and pictures. It never
  received a pack, a type label or the other role's answers. "No useful older evidence found" was allowed.
- **Role 2, pack reader:** four fresh agents, three cases each, no two cases from the same game. Each
  received only the decision-time input, a picture of the current board, the pack and cell-probe
  questions. No history. Code was prohibited; pictures were allowed, and none of the four opened them.
- **Locked before comparison.** All 36 submissions were copied read-only before any was compared
  (`submissions/`, hashes in `submissions_manifest.json`).
- **Sealed key.** Probe answers and per-frame counts were computed from the original frames before any
  agent started (`sealed/key_from_frames.json`).

## Comparison table

One row per case. The uncertainty shown is the highest-ranked one that the pack's record bears on, or
the reviewer's first-ranked uncertainty when the pack bears on none. "Per reviewer 1" marks a judgement
that was not independently verified and should be read as uncertain.

| Case | Important uncertainty | Older evidence exists? | Pack fits? | Required facts recovered correctly? | Failure reason |
|---|---|---|---|---|---|
| D01 ls20 | What completes a level | Partly, per reviewer 1. Actions 15 and 60 are confirmed level-completing actions | Yes, 1,274 | No. Pack read correctly (13/13), but its record (action 10) is not among the needed observations | Selection: record not relevant. The sets named for this uncertainty are 3,073 to 4,068 tokens, over the allowance |
| D02 ka59 | What event completed level 1 | Yes. Action 30 is confirmed as the level-completing action | Yes, 954 | Partly. Record 5 was read correctly (13/13) and matches reviewer 1's account of it, but it is a supporting record; action 30 is missing | Selection: incomplete set. Action 30 alone fits (1,971) |
| D04 tn36 | What moves the colour-b piece | Yes, per reviewer 1 | Yes, 674 | No. Pack read correctly (13/13); record 29 not cited for any uncertainty | Selection: record not relevant. A named set (60, 74) fits at 1,946 |
| D05 lf52 | What ended level 1 | Partly, per reviewer 1. Action 8 confirmed as level-completing | Yes, 1,614 | No. Pack read correctly (15/15); record 46 not cited | Selection: record not relevant. The sets for this uncertainty are 7,515 tokens or more |
| D06 bp35 | What the 1,276-cell change at the last action was | Yes, but the evidence is the recent action itself, whose frames the decision-time input does not list | No, 2,332 | No. Pack read correctly (18/18); record 60 not cited | Delivery and selection. No set named for any uncertainty in this case fits (3,690 to 43,428) |
| D07 vc33 | What clicking the colour-c segment did, and would do again | Partly, per reviewer 1 | No, 2,705 | Partly. Record 86 was read correctly (18/18) and matches reviewer 1's account; it needs action 69 beside it | Delivery: over 2,048. Incomplete set (86 with 69 is 3,398) |
| D10 vc33 | What the unclicked colour-9 blocks do | Partly, per reviewer 1 | Yes, 1,292 | Partly. Records 25 and 32 were read correctly (22/22) and match; the set also needs action 22 | Selection: incomplete set. Another named set (9, 10) fits at 1,172 |
| D11 cd82 | What ACTION1 to ACTION4 each do | Yes, per reviewer 1 | Yes, 2,038 | No. Pack read correctly (24/24); records 53 and 68 not cited | Selection: record not relevant. Sets for this uncertainty are about 4,800 tokens |
| D12 ka59 | What ACTION1 to ACTION4 change | Yes, per reviewer 1 | Yes, 1,000 | No. Pack read correctly (22/22); records 73 and 86 not cited | Selection: record not relevant. A named set fits at 1,622 |
| D14 cd82 | What completes the level | Partly, per reviewer 1; no sufficient set named. No level had been completed yet | Yes, 1,272 | No. Pack read correctly (13/13); record 15 not cited | Selection, and the need is not a memory problem: the history does not contain the answer |
| D15 vc33 | What the untested colour-9 blocks do | Partly, per reviewer 1 | Yes, 770 | Partly. Record 54 was read correctly (13/13) and matches; the named set is 46, 47, 55 | Selection: incomplete set. That set fits at 1,582 |
| D16 ka59 | What completed level 1 | Yes. Action 30 confirmed as level-completing | Yes, 784 | No. Pack read correctly (13/13); record 56 not cited | Selection: record not relevant. Sets for this uncertainty are 2,531 and 2,601, just over the allowance |

All 60 uncertainties, the cited actions, the sufficient sets and their rendered sizes are in
`comparison.json`.

## What was verified against the recordings

- **Role 2, mechanically:** action, frame count, cells differing in each stated frame, cells differing in
  the last frame, level completed, and 97 cell-colour probes. All 197 correct. The readers' prose was read
  but not scored item by item.
- **Role 1, mechanically:** every cited action exists at or before its decision. For uncertainties about
  what completed a level, the cited actions include the true level-completing action in every case where
  one exists.
- **Role 1, spot-checked by hand:** eight specific observations across five cases were compared with the
  frames (D10 action 38; D15 action 53; D04 actions 10 and 61; D02 actions 20 and 21; D12 actions 75 and
  78). All eight match.
- **Where the roles overlap:** in D02, D07, D10 and D15 the two roles described the same record
  independently, and both descriptions match the frames.
- **Not verified:** whether each uncertainty really is important, whether a named set is truly
  sufficient, and whether "partly" should be "yes" or "no". Those are judgements by one agent.

## Candidates for the next diagnostic

Uncertainties where reviewer 1 answered "yes" and named a sufficient set whose B version 2 pack fits
2,048. None of these packs has been read by anyone yet, so "understood from the supplied pack" is still
open for them.

| Case | Game | Uncertainty | Reviewer 1 summary of the uncertainty | Smallest sufficient group named (older actions) | B version 2 pack, tokens |
|---|---|---|---|---|---|
| D01 | ls20 | U5 | What the colour-b ring at x20-22, y31-33 (b on all eight outer cells, 3 in the centre at (21,32... | 72, 73 | 1,110 |
| D02 | ka59 | U1 | What board event made levels_completed go from 0 to 1 earlier in the game: which cells or shape... | 30 | 1,971 |
| D02 | ka59 | U2 | Why, at t33, the top row of the moved 3x3 shape (cells x42-44, y51) was drawn in colour 0 inste... | 20, 21 | 1,917 |
| D02 | ka59 | U4 | What ACTION1, ACTION2 and ACTION3 each do to the board: which cells change, in which direction ... | 3, 5, 31 | 1,951 |
| D02 | ka59 | U5 | What ACTION6 does when a given cell is clicked, and in particular what distinguishes the 3x3 sh... | 22, 23 | 1,492 |
| D04 | tn36 | U1 | What, if anything, makes the colour-b piece at x=30-33, y=13-16 (solid on rows 13-15, with a tw... | 60, 74 | 1,946 |
| D04 | tn36 | U3 | What happens when the colour-9 disc at x=32-40, y=51-59 is clicked? It is joined to the control... | 67, 74 | 1,812 |
| D04 | tn36 | U4 | What is the row-1 bar (x=1-61) counting, and what happens when its colour-9 part (now x=1-47) i... | 23, 61, 62 | 1,063 |
| D05 | lf52 | U2 | What do ACTION1, ACTION2 and ACTION3 do to the b/c square (b border x=36-41, y=50-55; c interio... | 80 | 659 |
| D07 | vc33 | U5 | What do the two colour-0 lines at x=30-37 on y=12 and y=18 mean, and why is the segment on the ... | 78, 79 | 1,514 |
| D10 | vc33 | U1 | What board condition completed levels 1 and 2? In particular, does it have to do with the row o... | 13 | 1,005 |
| D11 | cd82 | U4 | What ACTION5 does.... | 36 | 1,611 |
| D11 | cd82 | U5 | Whether the colour-c area at x27-36,y39-43 is a separate object lying over the lower half of th... | 89 | 1,733 |
| D12 | ka59 | U1 | What does each of ACTION1, ACTION2, ACTION3 and ACTION4 change on the board, and which object d... | 57, 58, 68, 72 | 1,622 |
| D12 | ka59 | U2 | What does the centre colour (0 versus 4) of an e block mean, and which cells respond to an ACTI... | 75, 78, 79 | 1,152 |
| D15 | vc33 | U1 | What board condition completes a level? In particular: does the 4/b shape (colour 4 at x=35-36 ... | 45 | 1,843 |
| D15 | vc33 | U3 | Would another ACTION6 at x=40 y=62 again raise the colour-0 area in x=30-41 (and the 4/b shape)... | 53 | 856 |
| D16 | ka59 | U2 | What do ACTION2, ACTION3 and ACTION4 do to the e block at x6-11, y33-38: which direction does e... | 40, 46, 47 | 1,578 |
| D16 | ka59 | U3 | Were the three e shapes with colour-4 centres (the 3x6 one at x30-32, y30-35 with 4 at x31, y32... | 31 | 924 |
| D16 | ka59 | U4 | What does ACTION6 (click a cell x,y) do, and which cells respond to a click: the e block at x6-... | 77, 78, 79 | 1,196 |

Four of these concern the very action the saved agent took next, which makes the outcome checkable
against the recording:

| Case | The agent's next action | Uncertainty | Set | Tokens |
|---|---|---|---|---|
| D10 vc33 | Click at x=24, y=56 | What that click does when the source side holds little colour 0 (U3, "partly": first half settled) | 38 | 758 |
| D11 cd82 | ACTION5 | What ACTION5 does (U4) | 36 | 1,611 |
| D04 tn36 | Click on the colour-9 disc | What clicking the disc does (U3) | 67, 74 | 1,812 |
| D15 vc33 | Click at x=10, y=62 | What the untested colour-9 blocks do (U2, "partly") | 46, 47, 55 | 1,582 |

Recommended order: render those set packs, repeat the pack-reading check on them, and take the ones
that are read correctly into the controlled actor-benefit test. D06 and D14 need diagnosis first: D06
has no set that fits, and D14's main need is not in the history.

One more finding for diagnosis: in D06 the decision-time input itself withholds the frames of the most
recent action, because its change list is too long to print. The first-ranked uncertainty there is about
that action. That is a gap in the recent-history format, not in older memory.

## How far to trust this

- **Agents, one per role.** Each judgement of importance and sufficiency comes from a single AI agent.
  A second reviewer might list different uncertainties.
- **Compliance is self-reported**, checked only against recorded tool counts. Each agent said it opened
  nothing outside its folder and ran no code.
- **Coverage was partial.** Reviewers read the index in full and opened 4 to 18 pictures each. Search was
  not available to them, so two read the change lists only in part (D06 by line ranges, D11 only the
  first 60 lines). "No evidence found" is therefore weaker than "evidence found".
- **One disclosure.** The D01 reviewer said the ls20 layout resembled a publicly previewed game and that
  it did not use that knowledge. The D01 pack reader recognised the name "ls20".
- **The probes are mine.** I added cell probes so reading could be scored against frames. They were
  chosen by a seeded rule from the frames before the agents ran.
- **Cost.** About 1.8 million subagent tokens on the subscription for the 16 agents.

## Files

`frozen_inputs.json`, `materials/` (what each role received), `forms/`, `submissions/` (36 locked files),
`submissions_manifest.json`, `sealed/key_from_frames.json`, `role2_scores.json`, `comparison.json`,
`table_candidates.md`. Code: `agent_review_prep.py`, `agent_review_score.py`, `agent_review_compare.py`.
