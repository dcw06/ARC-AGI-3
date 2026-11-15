# Remembering a game over: bp35 level 2

Written 2026-11-15. One game, one level, saved positions only. No live game was played. 86 model calls
were made on the Claude subscription; each reply's action was then played on a local copy of the game.

## The problem, as the saved run shows it

On 6 November the agent died three times on bp35 level 2, each time by rising into a spike (a purple tile
with a yellow-white-yellow underside). It was not short of a rule. After each death it wrote one, and
each time the rule then wore away:

| | Right after the death | About 20 actions later | Then |
|---|---|---|---|
| Death 1 (action 23) | "The f objects with b0b at the bottom are hazards: rising into them causes GAME_OVER." Status: supported | Action 33: downgraded to tentative. Action 36: gone. Action 42: "hazards or goals. Their role is unknown." | Action 48: moved under a spike. Death 2. |
| Death 2 (action 48) | "The f tiles with b0b bottoms are downward spikes. If the piece rises to directly beneath one, it dies." Status: supported | Action 73: tentative, "would probably hit that spike". Action 78: "contact with the spike either ends the game or just stops the piece" | Action 78: opened the tile under a spike. Death 3. |
| Death 3 (action 78) | "Rising in column x19 sends the piece into the f spike at x20-22 y7-11, which ends the game." Status: supported | Action 97: tentative again | The run stopped at action 100 |

- **The rule fades when its evidence leaves the input.** The agent sees its last 8 actions. Death 1 left
  that window at action 32; the rule was downgraded at action 33. The agent's eight notes are rewritten
  every turn, and a claim it can no longer check against anything gets weakened, then dropped.
- **The third lesson is about one place**, column x19, not about spikes. That is the "only remembers to
  take a different path" you pointed out.
- By the bp35 simulator, each death was a single losing action from a position that could still be won.

## The fix

Three switches in the harness, all off by default. With them off, the requests are the 6 November ones.

| Switch | What it does |
|---|---|
| `game_over_lessons` | On the turn after a game over, the agent must write a lesson in two parts: `rule` (what causes a game over, as a general rule about the objects) and `applies_when` (how to tell, on any board, before acting, that an action would end the same way). It is told to write both so they hold anywhere in the game, and not to describe a route. The controller keeps the lessons, outside the eight rewritable notes, and shows them in every later request of the game. |
| `lesson_check` | While lessons exist, every reply must test its chosen action against them: name any lesson that could apply and say what on the board shows the action is safe. |
| `pin_game_overs` | The controller keeps the current level's game-over actions in every later request, each with the board before and the board after. This keeps the evidence, not a summary of it. |

The first two are aimed at your goal: a death should teach something that applies to similar cases, and
the agent should apply it. The third is the plain "do not let the evidence scroll away" version.

## The test

It goes back to the two turns where the saved run died again and asks what the agent does there.

- **Positions:** before action 48 (one earlier death) and before action 78 (two earlier deaths).
- **Five inputs:** the request as sent on 6 November; the same plus ordinary earlier actions with their
  boards (a control for added length); plus the earlier deaths' boards; plus the lessons; plus the
  lessons and the required check.
- **Where the lessons came from:** not from me. Stage 1 went back to the turn after each earlier death
  and asked the model for the lesson, as the fixed harness would have. Three replies each; the first
  valid one was used, a rule fixed beforehand.
- **8 replies per input and position**, inputs interleaved. Every reply was accepted by the controller's
  own check.
- **Outcome:** each reply's action was played on the local copy of bp35 from that exact position. That
  copy reproduces all 100 saved actions frame for frame.
- **Rule fixed before sending** (`death_test/plan.json`): an input "works at these positions" if its share
  of fatal actions is at least 0.30 below both the unchanged request and the irrelevant control.

### The lessons the model wrote (stage 1)

After death 1:

> **rule:** The player piece rises automatically through open a tiles until a solid tile stops it. If its
> column leads into an f object with b0 along its bottom edge (a spike-like hazard), the piece is
> destroyed and the game ends.
> **applies_when:** Before you clear an e tile above the piece or move it sideways into a new column, trace
> that column upward. If you would pass only through a tiles (or tiles about to be cleared) before
> reaching an f/b0 object, with no e tile or other blocker in between, the action is fatal.

After death 2:

> **rule:** An f tile with a b0b bottom edge is a lethal spike. If the rising piece comes to rest anywhere
> directly beneath one, the piece is destroyed, even if a thin 5 gap row lies between them. Only a full
> solid tile (an intact e tile or a wide 5 background block) in between keeps it safe.
> **applies_when:** Before you clear an e tile or move the piece sideways, find where the piece would rise
> to in that column. If nothing solid except the 1-row 5 gap stands between that resting spot and an
> f/b0 tile above, the action is fatal.

All six stage-1 replies were general in this way: none named a place or a route.

### Result

Replies whose action ended in game over on the local game:

| Input | Before action 48 (one earlier death) | Before action 78 (two earlier deaths) | Both |
|---|---|---|---|
| As sent on 6 November | 8 of 8 | 4 of 8 | 12 of 16 |
| Plus irrelevant earlier boards | 8 of 8 | 4 of 8 | 12 of 16 |
| Plus the earlier deaths' boards | 4 of 8 | 0 of 8 | 4 of 16 |
| Plus the lessons | 6 of 8 | 0 of 8 | 6 of 16 |
| Plus the lessons and the check | 5 of 8 | 0 of 8 | 5 of 16 |

By the rule fixed beforehand, all three kinds of memory work at these positions. Extra boards that say
nothing about a death change nothing, so the effect is not from a longer prompt.

What the table hides:

- **After two deaths the repeat stopped completely**: 0 of 24 fatal with any memory, 8 of 16 without.
- **After one death it only halved.** With the lesson, the agent did apply it. In all eight replies with
  the check it named the spike lesson and reasoned about the column it was moving into. In five it then
  concluded the move was safe, because a one-row strip of background lay between the open column and the
  spike: "row 24 at x25-29 is still background 5, which should stop the piece before it reaches the
  hazard". That strip does not protect. The first death had not shown that case; the second did, and the
  second lesson says so ("even if a thin 5 gap row lies between them").
- **So the lesson carried over to a similar case and was wrong at its edge.** The agent generalised from
  "cleared the tile under a spike" to "moved sideways under a spike", which is the transfer you asked
  for. What it could not know from one death was exactly how close is too close.
- **The three kinds of memory cannot be told apart here.** 4, 6 and 5 of 16 are within what 8 replies per
  cell can vary by. The boards did a little better at the edge case, perhaps because a board keeps
  details a summary leaves out; this test cannot confirm that.
- **Memory made it think longer.** Median output per reply: 1,548 tokens unchanged, 2,048 with irrelevant
  boards, 2,689 with lessons, 3,263 with the check, 4,542 with the deaths' boards.

## What this does and does not show

- It shows the next action at two positions of one level of one game, 8 times per input.
- **It does not show the level then gets solved.** Avoiding the spike is not the same as finding the way
  up. By the simulator, the attempt at the second position was already lost four actions earlier, so no
  action there could have won it.
- **The positions come from a run without the fix.** With the fix on from the first death, the notes and
  the play after it would have been different.
- The lessons are one sample each. The other two samples per death were similar.
- Whether a lesson carries to a later level, where spikes appear again, is not tested.
- The lesson and the pinned boards together were not tested.
- Nobody has reviewed this test or the code behind it, and no person has checked the result.

## In progress: playing level 2 from its start

Started 15 November: two runs with unchanged memory and two with lessons and the check, each beginning at
the first board of level 2 with the saved notes and playing on the local game until level 2 is solved or
100 new actions are used. The plan was written before the first call (`level2_run/plan.json`). No results
are in this file yet.

## What was run

| | Calls | Time | Tokens in / out |
|---|---|---|---|
| Stage 1: lessons | 6 | about 4 minutes | not totalled |
| Stage 2: the test | 80, none invalid, none retried | 43 minutes | 1.47 million / 243,000 |

All calls were answered by Opus 5.5 at effort high on the subscription path.

## Files

- Code: `research/claude_arc_v1/policy.py` and `config.py` (the three switches),
  `research/memory_fix_v1/death_test.py` (the test), `research/memory_fix_v1/bp35_local.py` (the local game).
- Tests: `tests/test_claude_arc_v1_recovery.py`, classes `PinnedGameOvers` and `GameOverLessons`.
- `death_test/`: `lessons.json` and `lessons_replies.jsonl` (stage 1), `requests.json` and `manifest.json`
  (the 10 frozen requests), `plan.json` (the rule, written before sending), `replies.jsonl`,
  `replies_scored.jsonl` (each action with what the local game did), `scores.json`.
