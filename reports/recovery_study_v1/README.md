# Recovery as a decision problem (Direction 2): start report

Written 2026-11-14 for the research plan "Beyond the Saturated Score", section 4.

**No game was played.** Almost everything here comes from saved play (our 6 November run and 100 public
replay recordings), a local simulator of one game, reading the listed papers and books, and offline
tests. The one exception is the one-decision test, run on 14 November with your go-ahead: 100 model
calls on the Claude subscription, whose replies were recorded and sent nowhere. The harness changes are
built and tested but have not been used in play.

Three independent AI reviewers checked this work and a fourth checked the fixes. Their findings changed
it; see "Reviews" below.

## What this start found

1. **Our control cannot reset.** The 6 November harness tells the model "Never reset" and rejects action 0.
   Only the controller resets, and only after a game over. The plan's control, "the model decides when to
   reset or undo", does not describe it. The study needs one more condition: the control with resetting
   allowed.
2. **At 100 actions per game there is little for recovery to act on.** 24 games stopped on an unfinished
   level. In 19 of them the agent had spent fewer actions on that level than the human baseline: the cap
   arrived first. Five games were past the baseline (tn36, su15, bp35, cd82, lf52).
3. **In the one game where the truth can be checked, the stall was not a dead end.** A simulator of bp35,
   validated against the game earlier, shows the saved position after 100 actions is 19 actions from a
   win. The agent's 21 actions on that attempt were the first 21 of a shortest solution (40). A reset
   there would cost at least 41 actions to reach the same win. In the attempts the simulator could
   follow, the agent was on or within two actions of a shortest path until one losing action, and only
   4 actions came after the level could no longer be won.
4. **The plan's stall trigger would have fired rarely.** It needs "no new state and no change to
   memory". With notes compared word for word it cannot fire at a window of 3 or more. With notes
   compared by their claims and statuses it fires 0 times at a window of 6, and 3 times in one game at 3.
5. **A signal based on actions spent is not a sign of failure.** Flagging a level when its actions reach
   the human baseline flags 10 levels in our run; 5 of them were completed anyway, within 1 to 7 more
   actions. In the two strong public runs every flagged level was completed.
6. **Replaying a known opening is reliable but saves no actions.** The same actions from the same level
   start gave the same board in 3,698 of 3,698 comparisons. Each replayed action still counts. In our
   run the agent got back in fewer actions than an exact replay would have taken (89 against 117).
7. **Where models reset freely, most actions went to attempts that failed, but the cause is unclear.**
   In the public Opus 5 run on the official standard harness, 40% of actions were in attempts the agent
   reset and 21% in attempts ended by game over. Tycho with the same model lost 4.6% in total. Those
   two runs differ in much more than reset policy.
8. **Asked or not, the model did not reset.** In the one-decision test, 10 saved positions were each
   sent with and without the recovery check, 5 times. All 100 replies were valid and none chose a
   reset. In the 50 asked replies the answer was "continue" every time. The check changed the most
   common next action at 1 position of 10.

**My reading.** The evidence does not support spending the 34 hours a pilot would take. The agent
rarely stalls in the sense the plan describes, the budget ends most levels before recovery matters, and
the one over-baseline position we can verify calls for continuing, not resetting. (That position was
flagged by the level signal only; no stall of the repeated-board kind has been verified.)

That matches the Tycho bp35 tests of 9 and 10 November, where the agent chose to restart from a position
25 actions from a win and a forced question did not change its mind
(`reports/tycho_decision_check_l4_v1/`). Those tests challenged a reset the agent wanted; this study
would prompt one. The shared lesson is that the decision is only as good as the agent's belief about
the position.

The one-decision test was the cheap way to see whether a recovery check can tell a lost position from
a live one. By the rule fixed before any reply existed, it cannot: it produced no resets at all. With
"reset allowed" and "asked" both leaving the model's choice unchanged, the pilot's treatment conditions
would start out behaving like its control. I recommend stopping Direction 2 as designed at this budget.

## The one-decision test (run 14 November)

Ten positions from the saved 6 November run: the turn at which actions on a level first reached its human
baseline. Each was rebuilt offline exactly as the controller would build it and sent twice over, once
with resetting merely allowed and once with a recovery check as well, 5 times each. No game was touched.

| Position | Actions into the game | What the saved run did next | Resets, not asked | Resets, asked | Answers when asked |
|---|---|---|---|---|---|
| lp85 level 4 | 49 | completed the level 1 action later | 0 of 5 | 0 of 5 | continue x 5 |
| ka59 level 1 | 28 | completed it 2 actions later | 0 of 5 | 0 of 5 | continue x 5 |
| sc25 level 3 | 59 | completed it 5 actions later | 0 of 5 | 0 of 5 | continue x 5 |
| vc33 level 1 | 7 | completed it 6 actions later | 0 of 5 | 0 of 5 | continue x 5 |
| tr87 level 1 | 54 | completed it 7 actions later | 0 of 5 | 0 of 5 | continue x 5 |
| bp35 level 2 | 65 | never completed it; by the simulator, 24 actions from a win | 0 of 5 | 0 of 5 | continue x 5 |
| tn36 level 1 | 32 | never completed it | 0 of 5 | 0 of 5 | continue x 5 |
| su15 level 3 | 56 | never completed it | 0 of 5 | 0 of 5 | continue x 5 |
| cd82 level 3 | 76 | never completed it | 0 of 5 | 0 of 5 | continue x 5 |
| lf52 level 2 | 89 | never completed it | 0 of 5 | 0 of 5 | continue x 5 |

- **By the rule fixed beforehand: the check does not discriminate.** The rule asked for a reset share at
  most 0.20 where continuing is known to be right (the first six rows) and at least 0.30 higher at the
  other four. Both shares are 0.00. The rule is in `decision_test/plan.json`, written before the first
  call.
- **At the six positions where continuing is right, the model was right every time**, with or without
  the check. That is not evidence of judgement: it never reset anywhere.
- **The check barely changed the next action.** The most common action was the same with and without
  the check at 9 of 10 positions.
- **The reasons it gave** were about what it could see: how much of the game's own counter was left,
  whether the board could still be changed back, and that a reset "would gain nothing". At bp35 it wrote
  "this attempt can still work", which the simulator confirms. These are the model's stated reasons, not
  a measurement of why it chose.
- **The run:** 100 calls, all answered by Opus 5.5 at effort high, none invalid, none retried, 29 minutes,
  1.32 million input and 172,000 output tokens on the subscription.

What this does and does not show:

- It shows the first decision at each position, five times. It does not show what the model would do
  after 40 more unproductive actions.
- The positions are where the level signal first fires. The pilot would start later, at action 100, where
  tn36 has spent three times its baseline and su15 and bp35 have each died two or three times. The model
  might reset there; this test did not ask.
- The model was not told the harness's 100-action cap, here or in the saved run. It counted its budget
  from the game's own counter, which usually showed plenty left.
- Reset behaviour depends on the prompt. In the Tycho tests the same model, under a prompt that says to
  prefer a reset when an attempt looks unwinnable, did reset from a winnable position. Here, told only
  that it may reset, it never did.

## Decision needed

| Option | What it does | Model calls | Time |
|---|---|---|---|
| Stop here (my recommendation) | Record Direction 2 as not worth a pilot at this budget and move to another direction | 0 | - |
| One more check | The same test at the pilot's five starting positions (action 100), with and without the check, 5 times | 50 | about 15 minutes |
| B. Live check | The five pilot games resumed on the live games, 2 new actions each, level check and replay on | 10 to 30 | about 15 minutes |
| C. First look | Five games, 100 new actions, three conditions (control, reset allowed, level check), one run each | about 1,500 | about 8.5 hours |
| D. Pilot | Five games, 100 new actions, four conditions, three runs each | about 6,000 | about 34 hours |

- **Why stop.** The plan's hypothesis is that an explicit recovery policy beats leaving recovery to the
  model. To test it the policy has to change what the model does. At ten positions it did not.
- **What "one more check" would add.** If the model also never resets at the pilot's own starting
  positions, C and D would be comparing three copies of the control. If it does reset there, the bp35
  position (19 actions from a win) tells us whether it does so where it should not.
- **What would make recovery worth studying again:** a budget large enough that levels are abandoned
  rather than cut off (the official limit is five times the baseline per level), or a way to establish
  ground truth for more games than bp35.
- B to D still use the Claude subscription path of the 6 November run (2,467 calls in 13.9 hours).
- None of B to D answers the plan's question in 4.4 (not knowing the rules, or irreversible mistakes).
  Answering it needs ground truth about positions, which exists only for bp35.

## The control, and the conditions

The 6 November configuration: Opus 5.5, effort high, hypothesis notes (up to 8), last 8 actions shown,
100 actions per game, up to 10 controller resets after game over, model forbidden to reset.

| Condition | Compared with | What changes | Switches |
|---|---|---|---|
| R0 control | - | 6 November, unchanged | none |
| R0m reset allowed | R0 | The model may send RESET from a live position. One sentence of the system text changes. | `model_may_reset` |
| R1 check, board signal | R0m | A recovery check when the board signal fires | `stall_window` |
| R1 check, level signal | R0m | A recovery check when the level signal fires | `stall_level_ratio`, `stall_level_floor` |
| R2a replay | R1 level | On the turn after any reset, the model may have the first N actions of the ended attempt repeated | plus `replay_after_reset` |
| R2b pay-back | R1 level | A reset is refused when too few actions would remain for a new attempt | plus `recovery_pricing` |
| R2 both | R1 level | R2a and R2b together | both |

Seven configurations, in `config/recovery_v1/`, plus one for the live check.

**Where this departs from the plan, and why**

- **R0m is new.** Without it, R1 against R0 would mix "may reset" with "is asked".
- **A check is a question.** It shows facts about the agent's own play and requires an answer, continue
  or reset. It shows no human baseline and no action budget: Direction 3 varies those. A later check
  shows the answer given at the previous one.
- **R1 has two signals.** The plan's (no new board, optionally with unchanged notes) and a level signal.
- **R2 is split.** The plan's R2 changes a rule and adds replay at once; run alone, the two cannot be
  told apart.
- **The pay-back rule is the harness's, not the model's.** A reset must leave at least half the level's
  human baseline in actions, the median cost of a completed level in saved play (0.46 to 0.51 of the
  baseline in three harnesses). The model is not shown the budget. In the pilot the rule binds in the
  last 13 to 41 of the 100 new actions, depending on the game. This condition also adds one line to each
  check saying what a reset gives up (the reset and the actions on the attempt).
- **Replay is offered, not automatic.** The model chooses how many actions to repeat, each returned
  board is checked, and the action that ended in game over is never offered. A harness cannot know
  which part of a failed attempt was sound.
- **Still not single-factor:** R2a shows the model the full action list of the ended attempt, which no
  other condition shows. R1 adds an answer field the other conditions do not have.
- **Undo is left to the model** in every condition. Six games offer it.

### The stall signals on saved play

| Signal | Definition |
|---|---|
| No new board | N model actions in a row whose board was already seen in this attempt, counter cells ignored |
| ... same notes | and the notes kept the same claims and statuses over those actions |
| Level actions | Actions on the level reach a multiple of its human baseline; asked again one baseline later |

Simulated on the 6 November run with the tracker the live controller uses:

| Trigger | Checks (games) | With the hindsight counter estimate | Levels checked | ... of which completed anyway | Failed attempts checked | Attempts open at the end checked |
|---|---|---|---|---|---|---|
| no new board for 2 | 76 (13) | 70 (13) | 17 | 8 | 3 of 8 | 7 of 22 |
| no new board for 3 | 41 (10) | 35 (10) | 13 | 5 | 3 of 8 | 5 of 22 |
| no new board for 4 | 27 (8) | 21 (8) | 10 | 4 | 2 of 8 | 4 of 22 |
| no new board for 6 | 13 (5) | 10 (5) | 6 | 3 | 1 of 8 | 2 of 22 |
| no new board for 8 | 8 (3) | 5 (3) | 3 | 1 | 1 of 8 | 1 of 22 |
| no new board for 10 | 4 (2) | 3 (2) | 2 | 0 | 1 of 8 | 1 of 22 |
| no new board for 2, same notes | 12 (4) | 12 (4) | 4 | 0 | 2 of 8 | 3 of 22 |
| no new board for 3, same notes | 3 (1) | 3 (1) | 1 | 0 | 1 of 8 | 0 of 22 |
| no new board for 4, same notes | 3 (1) | 3 (1) | 1 | 0 | 1 of 8 | 0 of 22 |
| no new board for 6, same notes | 0 (0) | 0 (0) | 0 | 0 | 0 of 8 | 0 of 22 |
| level actions at 0.75x human | 20 (13) | same | 17 | 12 | 4 of 8 | 3 of 22 |
| level actions at 1.00x human | 13 (10) | same | 10 | 5 | 4 of 8 | 3 of 22 |
| level actions at 1.50x human | 7 (5) | same | 5 | 1 | 2 of 8 | 3 of 22 |
| level actions at 2.00x human | 3 (2) | same | 2 | 0 | 1 of 8 | 1 of 22 |
| level actions at 1.00x human, not before 30 | 10 (7) | same | 7 | 2 | 4 of 8 | 3 of 22 |

- "Completed anyway" means the saved run went on to complete that level. A check there is a false alarm.
- **Notes.** Word for word, the notes were identical on 11 of 2,442 consecutive actions and never three
  times running. By claims and statuses they were unchanged on 1,258 (51.5%). The "same notes" rows use
  the second reading.
- **The level signal is circular for the five pilot games:** they were chosen as the games past their
  baseline, so it flags them by construction. What it adds is the false-alarm count.
- **The counter estimate matters.** Many games show a step counter, so raw boards never repeat. The
  tracker learns which cells are a counter from actions that change one or two cells. Cells that change
  twice within one attempt are treated as objects, not counters, and a line of counter cells marked in
  order is treated as a moving bar and ignored whole. A first version missed bar cells not yet reached
  and counted 2 repeats in tn36 where there are 23; two reviewers caught it, and a fourth caught two
  further faults in the repair. On the saved run it now ignores one row or column in ten games, part of
  a row in lf52, and nothing in 14 games, where the board signal may be blind.
- **Valid up to the first check only.** A real check may change what the agent does next.
- Thresholds (window 6; 1.0x with a floor of 30 actions) were picked from this same run. Every game here
  is development data for them.

The same triggers on the public runs:

| Trigger | Source | Checks (games) | Levels checked | ... of which completed anyway |
|---|---|---|---|---|
| no new board for 6 | Official standard harness, Opus 5 | 154 (12) | 20 | 10 |
| no new board for 6 | Official standard harness, GPT-6 Astra | 179 (8) | 12 | 5 |
| no new board for 6 | Provider adapter, GPT-6 Astra | 2 (1) | 1 | 1 |
| no new board for 6 | Tycho, Opus 5 | 1 (1) | 1 | 1 |
| level actions at 1.00x human | Official standard harness, Opus 5 | 86 (21) | 37 | 20 |
| level actions at 1.00x human | Official standard harness, GPT-6 Astra | 73 (18) | 29 | 15 |
| level actions at 1.00x human | Provider adapter, GPT-6 Astra | 7 (5) | 5 | 5 |
| level actions at 1.00x human | Tycho, Opus 5 | 5 (5) | 5 | 5 |

In the two weak runs about half of the flagged levels were completed anyway; in the two strong runs all were.

## Where the 100 actions went on 6 November

2,475 actions over 25 games: 1,406 in attempts that completed a level, 842 in the last attempt of games
that stopped on an unfinished level (36 of them in sc25, whose last action was a game over), 219 in
attempts ended by a game over and then reset, and 8 controller resets.

| Game | Unfinished level | Actions spent on it | Human baseline | Ratio | Game overs in the game | Longest run without a new board: during play | ... with hindsight |
|---|---|---|---|---|---|---|---|
| tn36 | 1 | 100 | 32 | 3.12 | 1 | 23 | 23 |
| su15 | 3 | 70 | 26 | 2.69 | 2 | 4 | 4 |
| bp35 | 2 | 83 | 48 | 1.73 | 3 | 3 | 3 |
| cd82 | 3 | 65 | 41 | 1.59 | 0 | 5 | 5 |
| lf52 | 2 | 92 | 81 | 1.14 | 0 | 18 | 16 |
| ar25 | 4 | 28 | 37 | 0.76 | 0 | 0 | 0 |
| dc22 | 2 | 68 | 102 | 0.67 | 0 | 7 | 7 |
| tr87 | 2 | 39 | 58 | 0.67 | 0 | 0 | 0 |
| ka59 | 2 | 70 | 109 | 0.64 | 0 | 6 | 6 |
| cn04 | 3 | 48 | 85 | 0.56 | 0 | 0 | 0 |
| s5i5 | 3 | 59 | 106 | 0.56 | 0 | 3 | 3 |
| ls20 | 3 | 40 | 73 | 0.55 | 0 | 1 | 1 |
| re86 | 3 | 44 | 86 | 0.51 | 0 | 0 | 0 |
| r11l | 6 | 23 | 49 | 0.47 | 0 | 1 | 1 |
| sc25 | 4 | 36 | 83 | 0.43 | 1 | 0 | 0 |
| sk48 | 3 | 35 | 101 | 0.35 | 0 | 2 | 2 |
| g50t | 2 | 61 | 175 | 0.35 | 0 | 1 | 1 |
| sp80 | 5 | 31 | 96 | 0.32 | 1 | 1 | 1 |
| vc33 | 5 | 27 | 131 | 0.21 | 0 | 1 | 1 |
| sb26 | 7 | 9 | 58 | 0.16 | 0 | 0 | 0 |
| m0r0 | 3 | 29 | 203 | 0.14 | 0 | 1 | 1 |
| wa30 | 3 | 5 | 183 | 0.03 | 0 | 0 | 0 |
| tu93 | 6 | 2 | 80 | 0.03 | 1 | 0 | 0 |
| lp85 | 8 | 0 | 159 | 0.00 | 0 | 0 | 0 |

- ft09 was won. sp80 spent its last action on a reset and lp85 completed a level on its last action, so
  those two had no attempt open when play stopped.
- "Actions spent on it" counts every attempt on the level and every reset.
- The last two columns differ only in when the counter cells are known. Only tn36 and lf52 show long
  runs of repeated boards. In 14 games no counter was found, so a zero there may mean "never repeated a
  board" or "a counter the estimate missed".
- Being past the baseline does not show a position was unwinnable. Only bp35 can be checked.

### bp35, checked with the simulator

`.cache/bp35_play/solver/sim.py` is a compact copy of bp35's level logic, validated action by action
against the game on 9 November. The saved level-2 attempts were run through it.

| Attempt on level 2 | In the saved run | In the simulator |
|---|---|---|
| 1 | 6 actions, game over | On a shortest path for 5 actions (35 from a win). The sixth action lost at once, as in the game. |
| 2 | 24 actions, game over | After 7 actions, 35 from a win (two more than the shortest). The eighth action is an undo; not followed further. |
| 3 | 29 actions, game over | On a shortest path for 24 actions (after 16, the one-decision test position: 24 from a win). The 25th action made the level unwinnable; the game ended four actions later. |
| 4 | 21 actions, cap reached | On a shortest path: 19 from a win. |

- The simulator has no undo, so an attempt is followed only up to its first undo.
- "Unwinnable" means no win within the game's own action bar for the attempt (63 actions on this level).
- **Where the attempts could be followed, a reset at the perfect moment would have saved 4 actions**
  (attempt 3, actions 26 to 29). The last 17 actions of attempt 2 could not be followed. The losses seen
  were single losing actions from good positions, each followed by the controller's reset. No reset
  decision was missing, and a reset at action 100 would have cost 22 more actions than playing on.
- This is one level of one game.

## What recovery looks like in saved play

Attempts are split at every level completion and every RESET. A failed attempt ended in a RESET.

| Source | Actions | Levels done | In completed attempts | In failed attempts, resets included | In the unfinished last attempt | Resets after game over | Resets chosen from a live position | Retries with at least one action that completed the level |
|---|---|---|---|---|---|---|---|---|
| Ours, 6 Nov (Opus 5.5, 100-action cap) | 2,475 | 67 | 56.8% | 9.2% | 34.0% | 8 | 0 | 1 of 7 |
| Official standard harness, Opus 5 | 10,557 | 95 | 31.0% | 60.9% | 8.1% | 57 | 311 | 14 of 367 |
| Official standard harness, GPT-6 Astra | 14,141 | 132 | 34.8% | 59.8% | 5.4% | 107 | 58 | 9 of 165 |
| Provider adapter, GPT-6 Astra | 7,085 | 183 | 94.8% | 5.2% | 0.0% | 7 | 7 | 10 of 14 |
| Tycho, Opus 5 | 6,641 | 183 | 95.4% | 4.6% | 0.0% | 6 | 11 | 13 of 17 |

| Source | In attempts ended by game over | In attempts the agent reset | Chosen resets | ... after a single action | Levels with a failed attempt | ... completed in the end | Retry actions | ... spent getting back | Cost of that path the first time |
|---|---|---|---|---|---|---|---|---|---|
| Ours, 6 Nov | 9.2% | 0.0% | 0 | 0 | 5 | 1 | 153 | 89 | 117 |
| Official standard harness, Opus 5 | 21.1% | 39.8% | 311 | 228 | 31 | 14 | 5,282 | 966 | 2,011 |
| Official standard harness, GPT-6 Astra | 26.1% | 33.7% | 58 | 0 | 23 | 9 | 7,177 | 1,986 | 2,959 |
| Provider adapter, GPT-6 Astra | 2.3% | 2.9% | 7 | 0 | 10 | 10 | 439 | 90 | 91 |
| Tycho, Opus 5 | 1.4% | 3.2% | 11 | 0 | 13 | 13 | 556 | 139 | 143 |
| Official standard harness, Opus 5, without su15 and sk48 | 23.0% | 33.4% | 52 | 0 | 27 | 12 | 4,480 | 902 | 1,643 |
| Official standard harness, GPT-6 Astra, without su15 and sk48 | 27.6% | 29.8% | 39 | 0 | 19 | 7 | 5,930 | 1,844 | 2,753 |

"Spent getting back" is the actions the next attempt took to reach the furthest point of the failed
attempt that it came back to. "Cost of that path the first time" is what an exact replay would have cost.

What this supports:

- **The 228 single-action resets are a loop in two games.** All are in su15 and sk48, and 152 of the
  single actions are ACTION7. Without those games the Opus 5 run chose 52 resets, none after one action.
  I cannot tell whether that loop was the model's choice or the harness's handling of some reply.
- **Per level, recovery worked about half the time in the weak runs** (14 of 31, 9 of 23) and every time
  in the strong ones. "14 of 367 retries" counts every repeat of the loop.
- **Failed attempts mostly end on fresh boards.** The median failed attempt had 0 or 1 actions without a
  new board at its end in every source; counting boards seen on earlier attempts as well, 0 to 2.
- **An exact replay costs at least as much as the agent's own way back** in every source: much more in
  the weak runs and in ours, about the same in the two strong ones. Replay could save model calls and
  mistakes on the way, not actions, and R2a can add actions.
- **Strong harnesses lose little to recovery**: 4.6% and 5.2% of actions.
- These are single runs on different harnesses. They describe; they do not compare policies.

## Before any run: what RESET and undo do, per game

From 572 resets and 211 testable ACTION7 uses in the 125 saved traces.

| Game | Actions offered | Resets seen | After game over | Level kept | Board equal to the level start | ACTION7 uses that could be tested | Earlier board back, counter ignored | Within 2 cells |
|---|---|---|---|---|---|---|---|---|
| ar25 | 1 2 3 4 5 6 7 | 0 | - | not seen | not seen | 3 | 0 | 1 |
| bp35 | 3 4 6 7 | 80 | 79 | 80 of 80 | 80 of 80 | 56 | 16 | 42 |
| cd82 | 1 2 3 4 5 6 | 8 | 0 | 8 of 8 | 8 of 8 | - | - | - |
| cn04 | 1 2 3 4 5 6 | 8 | 2 | 8 of 8 | 8 of 8 | - | - | - |
| dc22 | 1 2 3 4 6 | 3 | 1 | 3 of 3 | 3 of 3 | - | - | - |
| ft09 | 6 | 0 | - | not seen | not seen | - | - | - |
| g50t | 1 2 3 4 5 | 8 | 5 | 8 of 8 | 8 of 8 | - | - | - |
| ka59 | 1 2 3 4 6 | 19 | 1 | 19 of 19 | 19 of 19 | - | - | - |
| lf52 | 1 2 3 4 6 7 | 9 | 1 | 9 of 9 | 9 of 9 | 28 | 13 | 28 |
| lp85 | 6 | 0 | - | not seen | not seen | - | - | - |
| ls20 | 1 2 3 4 | 14 | 2 | 14 of 14 | 14 of 14 | - | - | - |
| m0r0 | 1 2 3 4 5 6 | 16 | 5 | 16 of 16 | 16 of 16 | - | - | - |
| r11l | 6 | 1 | 1 | 1 of 1 | 1 of 1 | - | - | - |
| re86 | 1 2 3 4 5 | 7 | 1 | 7 of 7 | 7 of 7 | - | - | - |
| s5i5 | 6 | 2 | 0 | 2 of 2 | 2 of 2 | - | - | - |
| sb26 | 5 6 7 | 0 | - | not seen | not seen | 3 | 0 | 0 |
| sc25 | 1 2 3 4 6 | 16 | 14 | 16 of 16 | 16 of 16 | - | - | - |
| sk48 | 1 2 3 4 6 7 | 116 | 1 | 116 of 116 | 116 of 116 | 61 | 48 | 58 |
| sp80 | 1 2 3 4 5 6 | 11 | 9 | 11 of 11 | 11 of 11 | - | - | - |
| su15 | 6 7 | 169 | 5 | 169 of 169 | 169 of 169 | 60 | 35 | 47 |
| tn36 | 6 | 13 | 6 | 13 of 13 | 13 of 13 | - | - | - |
| tr87 | 1 2 3 4 | 2 | 1 | 2 of 2 | 2 of 2 | - | - | - |
| tu93 | 1 2 3 4 | 48 | 48 | 48 of 48 | 48 of 48 | - | - | - |
| vc33 | 6 | 8 | 2 | 8 of 8 | 8 of 8 | - | - | - |
| wa30 | 1 2 3 4 5 | 14 | 1 | 14 of 14 | 14 of 14 | - | - | - |

- **RESET restarted the current level, exactly, every time it was seen**: 572 of 572 kept the completed
  levels and returned the level's first board cell for cell. Four games have no reset in the data.
- **Every one of those resets followed at least one action on the attempt.** The official documentation
  says a RESET with no action since the last level change restarts the whole game. That case is not in
  the data. The policy refuses a model reset before the attempt's first action, the controller checks
  again before sending, a reset that changes the level count ends the game, and the audit refuses a log
  that contains one.
- **Undo (ACTION7) is offered in six games.** In lf52 it brought the earlier board back to within two
  cells every time (28 of 28), the difference being the counter, which still advances. In bp35, sk48 and
  su15 it mostly did (42 of 56, 58 of 61, 47 of 60). In ar25 and sb26 the few uses did not, so its
  effect there is unknown. The recordings keep only the last board of each step.
- **Replay.** Whenever two attempts started from the same level-start board and shared their opening
  actions, the boards were compared step by step: 3,698 comparisons at 2,117 positions, 1,826 of them
  reached by two or more different sources, all 25 games, no difference. The evidence is thin on some
  levels (7 comparisons in all of r11l). It covers final boards only; one paper reports unseeded visual
  noise in lf52, which could break the stricter all-frames check a resume uses. Option B would show it.

## Scoring, checked against the scorer's own output

Two official scorecards (ours and a public Opus 5 one, 250 completed levels, 50 games) reproduce exactly:

- level score = min(115, 100 x (human baseline / actions on the level)^2), zero if not completed;
- game score = the smaller of weighted completion and the weighted mean of level scores, weight = level number;
- total = mean over games.

The technical report states the cap two ways; the scorer uses the one above. Consequences for recovery:

- Actions on a level include failed attempts and resets. One reset plus a replay of k actions adds 1 + k.
- **Not every wasted action costs score.** A level keeps full marks until its actions pass about 0.93 of
  the baseline, and an unfinished level scores zero however few actions it used.
- Under our 100-action cap the score is set by completion: 23.16 against 23.28 weighted completion.

## The reset decision, stated formally

Assembled from the decision-making textbooks. No book states it in this form.

- Let G(x) be the expected actions to finish the level from position x, infinite for a dead end. Let q be
  the probability that the current line is dead and W the actions wasted before that shows.
- Without a binding budget, reset and replay k actions when
  G(current) + (q / (1 - q)) x W > 1 + k + G(position after the replay).
- With B actions left, compare the chance of finishing: reset when
  F(position after the replay, B - 1 - k) > F(current, B), and never when B <= 1 + k.
- G, F and q are the agent's own beliefs. A stall signal is evidence that raises q.

At the saved bp35 position G(current) was 19 and the right-hand side at least 41. A rule of this form is
only as good as the beliefs put into it.

## Measures

All computed by `research/recovery_v1/measures.py` from the action log, with no game source.

| Measure | Definition |
|---|---|
| Attempt | Actions on one level from its first board, or from a RESET, to completion, the next RESET, or the end of play |
| Progress event | A completed level. It is the only progress signal the game gives. |
| Dead-end loss | Actions in an attempt that ended in a RESET, plus the RESET. Reported separately for game overs and chosen resets. |
| Actions after the last completed level | Everything after the final level completion. Needs no judgement. |
| Stale tail | Actions at the end of a failed attempt with no new board, counted within the attempt and within the level |
| Return point and return cost | The furthest point of the failed attempt that the next attempt came back to, the actions it took to get there, and the cost of that path the first time |
| Levels recovered | Levels with a failed attempt that were completed in the end |
| Reset count and timing | Chosen and after game over separately; attempt length and level-action ratio at each |
| Check log | Every check, its facts and the answer; a check on a level that is then completed without a reset is a false alarm |
| Replay log | Actions replayed, and any replay stopped by a board that differed |

"Dead-end loss" is the plan's name. The data cannot tell a dead end from a mistake, except in bp35.
Return cost exists only where a reset happened, so it is reported with the reset rate, never alone.

## The pilot design (options C and D)

Each game begins by repeating the first 100 saved actions of the 6 November run with no model call.
Every returned observation must match the saved one or that game is dropped. The saved replies rebuild
the agent's notes and history, so every condition faces the same position with the same memory. Then
100 new actions.

| Game | Level | Actions on it | Human baseline | Attempts | Game overs | Actions on the current attempt |
|---|---|---|---|---|---|---|
| tn36 | 1 | 100 | 32 | 2 | 1 | 38 |
| su15 | 3 | 70 | 26 | 3 | 2 | 3 |
| bp35 | 2 | 83 | 48 | 4 | 3 | 21 |
| cd82 | 3 | 65 | 41 | 1 | 0 | 65 |
| lf52 | 2 | 92 | 81 | 1 | 0 | 92 |

What it can and cannot show:

- **One starting position per game.** Repeats share the first 100 actions and the notes, so their spread
  is the spread from that position only. Results do not generalise to the game, still less to 25 games.
- **Chosen on a bad outcome.** Conditions are compared with a fresh control from the same start, never
  with the 6 November result.
- **Primary outcome: levels completed in the 100 new actions.** With five games this is descriptive.
  The useful output is behaviour: whether resets happen, when, and what follows.
- **In the level-signal conditions the first new turn carries a check in all five games**, because all
  are already past the threshold. Later checks come one baseline apart (26 to 81 actions).
- **Exposure.** All 25 games are development data here. bp35 and lf52 were also used in earlier work in
  this project. Under the split the plan cites, four of the five are held-out games; this design uses
  them for development, which that split would not allow.
- **Not in this report, though the plan lists them:** a repeat of the control to measure our own
  run-to-run spread, RHAE and list-price cost per condition, and any measure of "varies less between
  runs". They need runs.

Checked offline: under all seven configurations the controller repeats the 100 saved actions and builds
the first new request. `data/pilot_first_requests.json` holds what each condition adds to it. This shows
the controller logic works on the saved boards; it is not evidence that the live games will match.

## What is built

| Part | Where |
|---|---|
| Switches, all off by default | `research/claude_arc_v1/config.py` |
| Stall signals, pay-back rule, check and offer text | `research/claude_arc_v1/recovery.py` |
| Repeat a saved opening | `research/claude_arc_v1/resume.py` |
| Controller, prompt, reply checks, audit, adapter | `research/claude_arc_v1/run.py`, `policy.py`, `audit.py`, `arc.py`, `backends.py` |
| Tests | `tests/test_claude_arc_v1_recovery.py` (47 tests) |
| Measures, simulation, tables | `research/recovery_v1/` |
| One-decision test: requests, plan, replies, scores | `decision_test/`, `research/recovery_v1/decision_test.py` |
| Pilot configurations, `live_enabled` false | `config/recovery_v1/` |

- **With every switch off the request is the 6 November request.** A reviewer rebuilt all 2,467 saved
  requests byte for byte with the changed code. A test pins the control's system text and reply schemas
  to hashes taken from the code as committed, and another repeats saved actions of three games and
  compares the next request with the saved one.
- The pinned adapter in `agent/` accepts RESET only after game over. It is not edited; a subclass widens
  that one check for the one call.
- The one-decision test's sender refuses to run without `--send`, and refuses to overwrite its replies.
- With the default configuration, the logged configuration now lists the new switches (all off).

## Reviews

Three AI reviewers worked independently on the first version of this report: one on design and claims,
one on the code, one recomputing the numbers with its own code. None is a human review.

| Reviewer | Found | What changed |
|---|---|---|
| Numbers | All counts reproduced except: 24 games stopped on an unfinished level, not 22; the cross-source replay count depended on file order | Counts corrected; replay now reported by position |
| Numbers | Several rows of the reading record said more than the readers' notes | Rows reworded (`LITERATURE.md`) |
| Code and design, independently | The live counter estimate missed repeats while a counter bar advanced: 2 in tn36 where there are 23 | Estimate fixed; the stall count is recomputed when the estimate changes; all trigger numbers redone |
| Code and design, independently | The level check fired on four or five turns running after a resume | The next check is now one baseline after the last |
| Code | Reply fields nobody asked for were rejected, which could end a game in treatment conditions only | Dropped instead |
| Code | A resume that differed stopped the whole run; nothing detected a reset that restarted the whole game; resume could not tell a control run from any other | Each now ends that game only, or is refused before any scorecard opens |
| Design | The pay-back condition showed the model its remaining actions; the level check showed the human baseline | Both removed from what the model sees |
| Design | The first version said the stall trigger "would never have fired" and that free resetting "goes badly" | Both restated with the splits above |
| Design | The pilot cannot answer the plan's question and had no decision rule; cheaper tests exist | The one-decision test built (and since run); bp35 checked with the simulator; recommendation changed |
| Verifier of the fixes | The repaired counter estimate forgot a bar when a level restarted and could take a small moving piece or a switch for a counter | Estimate reworked: cells that change twice in an attempt are objects; a bar stays a bar; a cap on what may be ignored; numbers redone again |
| Verifier of the fixes | The live-check configuration would have refused every reset; a replay nobody offered was silently dropped; five behaviours had no test | Fixed; tests added |
| Verifier of the fixes | All report tables matched their data; eight sentences said more than the data | Sentences corrected |

Not acted on: a 2 x 2 design separating "asked" from "baseline shown" (the baseline is no longer shown).
The reworked counter estimate has not itself been reviewed.

## Limits

- **Single saved runs.** Every number above is one run of one harness. None is a rate.
- **The counter estimate is a heuristic.** It finds no counter in 14 of 25 games. Its first two versions
  were wrong, and the third has not been reviewed. Every "no new board" number depends on it.
- **Boards, not states.** Equal boards can hide different positions.
- **Ground truth exists for one level of one game.** The bp35 result rests on a simulator validated
  earlier, not on the game itself.
- **All 25 games are development data** for the thresholds and for this design.
- **The public runs differ from ours** in harness, model and budget.
- **Reading was done by AI readers**; see `LITERATURE.md` for what each read. Russell and Norvig's text
  was not available.
- **The one-decision test is 100 replies at ten positions of one saved run.** It says what Opus 5.5
  does at those positions in this prompt, not what it would do in general.
- **Nothing here has been checked by a person.**
