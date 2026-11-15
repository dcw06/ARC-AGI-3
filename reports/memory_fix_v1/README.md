# Remembering a game over: bp35 level 2

Written 2026-11-15. One game, one level, all on a local copy of the game; no live game was played.
Two tests on the Claude subscription: 86 model calls at saved positions (each reply's action was then
played on the local game), then 243 calls in four runs of level 2 from its start.

**Short version.** The agent already wrote a rule after each death; the rule then wore away. With the fix,
a death produces a general lesson that stays in every later request and must be checked before every
action. At the two saved positions where the 6 November run died again, memory cut fatal replies from 12
of 16 to 4 to 6 of 16. Played from the start of level 2, all four runs solved the level, with and without
the fix, so there is no result on solving. Neither run with the fix died a second time; one of the two
runs without it died three times, the same way each time. Counted by turn, the unchanged agent took the
fatal action at 2 of the 20 turns where one was available after its first death, and the fixed agent at
0 of 9. That is too few to call an effect.

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

### What the position test does and does not show

- It shows the next action at two positions of one level of one game, 8 times per input.
- **It does not show the level then gets solved.** Avoiding the spike is not the same as finding the way
  up. By the simulator, the attempt at the second position was already lost four actions earlier, so no
  action there could have won it. The runs in the next section play the level through.
- **The positions come from a run without the fix.** With the fix on from the first death, the notes and
  the play after it would have been different. The runs in the next section have the fix on from the start.
- The lessons are one sample each. The other two samples per death were similar.
- Whether a lesson carries to a later level, where spikes appear again, is not tested.
- The lesson and the pinned boards together were not tested.
- Nobody has reviewed either test or the code behind them, and no person has checked the results.

## Playing level 2 from its start

Four runs on the local game, 15 November. Each began at the first board of level 2 with the notes the
6 November run had at that point (its 17 level-1 actions were repeated with no model call, and every board
matched the saved one). Each then played with its own choices until level 2 was solved or 100 new actions
were used. Two runs had the 6 November harness unchanged; two had `game_over_lessons` and `lesson_check`
on. The plan and its reading rule were written before the first call (`level2_run/plan.json`).

| Run | Memory | Level 2 solved | Actions on level 2 | Game overs | at level-2 action | Model calls | Output tokens | Minutes |
|---|---|---|---|---|---|---|---|---|
| control-1 | unchanged | yes | 44 | 1 | 3 | 43 | 75,000 | 12.6 |
| control-2 | unchanged | yes | 87 | 3 | 6, 13, 46 | 84 | 173,000 | 29.6 |
| lessons-1 | lessons and check | yes | 57 | 1 | 10 | 56 | 147,000 | 25.0 |
| lessons-2 | lessons and check | yes | 61 | 1 | 6 | 60 | 175,000 | 29.4 |

Actions count every action on the level, including the reset after each game over. For scale: the human
baseline for this level is 48 actions, the shortest solution the simulator finds is 40, and the
6 November run used 83 without solving it. No reply was sent back by the controller in any run, and all
four logs pass the harness's own audit.

**By the rule fixed beforehand, there is no result on solving the level:** all four runs solved it. Two
runs per arm cannot separate the arms from chance, and 57 and 61 actions sit between 44 and 87.

### Did a death repeat?

This is the question the fix was built for. It is a secondary measure in the plan, and whether two deaths
have "the same cause" is my reading of the boards.

- **With the fix: no second death in either run**, over the 46 and 54 actions that followed the first one.
- **Without it: one run never died again, the other died three times, the same way each time.** In all
  three of control-2's deaths the piece came to rest directly under a spike with only a one-row strip of
  background between them: by opening the tile above it (action 6), by stepping sideways into an open
  column (action 13), and by opening the tile above it again (action 46).

Control-2 shows the 6 November failure again. Its notes, by level-2 action:

| Action | What the notes said |
|---|---|
| 8, first turn after death 1 | "The f/b0 spike shapes are deadly." Status: supported |
| 10 | "The f/b0 spike shapes, or something above x37-53, are deadly." |
| 11 and 12 | "The cause may be the open a-column reaching off the top of the map, or spike shapes." |
| 13, death 2 | "Rising at x37-41 ended the game, possibly because the open a-column runs off the top of the map." No note mentions spikes. Plan: step into the open column, "the 5 cells at x25-29 in row 24 should stop it there" |
| 15, first turn after death 2 | "The f cells with b0 tips ... are spikes, and a piece that rises into them dies." Status: supported |
| 16 to 42 | "The f/b0 spikes kill a piece that rises against them." Status: supported on every turn |
| 43 to 45 | No note states that spikes kill; the notes are about the route. Action 45: "then solid 5 at y18 that shields it from the spikes" |
| 46, death 3 | "it stops under the spike. It may not die there, because the spike is separated by a 5 border row." |

- **The first rule was rewritten into a wrong one within five turns.** The view had scrolled and the
  spikes were off the screen, so the agent no longer saw what its rule was about and replaced it with a
  guess. The fatal action was still in its eight-action history, without its boards.
- **The second rule lasted 28 turns and still did not prevent death 3.** It was dropped at action 43,
  after the piece had passed safely through a gap between spikes, and the agent died three turns later.
  It still treated spikes as a danger then. What it got wrong was whether a one-row strip of background
  protects, which is exactly what death 2 had shown. The note written after death 2 kept "spikes kill"
  and not that detail.

### What the fixed agent did

Both lessons were written on the turn after the first death, and both are general. Neither names a
place or a route:

> **lessons-1, rule:** The piece falls upward. When the tile above it is opened (e clicked into a), it
> rises through every open a tile until a solid tile (e block or dotted wall) stops it. If the first
> non-open tile it reaches in that column is an f/b0 spike tile, the game ends.
> **applies_when:** Before clicking an e tile directly above the piece, or moving the piece under an open
> column, look upward in that column (scroll the board if needed). If spikes come before any e or wall
> tile, that action will end the game. Clear a different column, or move sideways first.

> **lessons-2, rule:** The piece rises through open space until it is blocked. If the first thing above
> it in its 5-wide column is an f block with a b0b underside (a downward spike), the piece runs into it
> and the game ends. Removing the last e tile between the piece and a spike is fatal.
> **applies_when:** Before clicking an e tile, or before moving the piece sideways under open space, scan
> the piece's column straight up. If there are no e tiles left between the piece and an f/b0b block after
> the action, the action will end the game.

- **Both cover the sideways step**, the "similar case" of the goal, from a death that happened by opening
  a tile.
- **The check was written on every later turn**: 46 of 46 in lessons-1 and 54 of 54 in lessons-2. In 39
  and 49 of them the agent said the lesson applied and gave what on the board made the action safe, for
  example: "the column above the piece (x19-23) has e tiles at y25-35 and an f spike at x20-22, y7-11.
  Clearing both e tiles would be fatal, so I'm moving sideways instead of clicking."
- **It cost output, not actions.** Median output per call was 1,237 and 1,466 tokens unchanged, 1,768 and
  2,141 with the fix.

### How often was a game over one action away?

"No second death" needs a denominator. For every turn where the agent chose an action, each possible
action was tried on a copy of the local game at that exact position: both moves, the undo, and a click on
every tile.

| Run | Turns after the first game over | of which one action would have ended the game | Fatal action taken |
|---|---|---|---|
| control-1 | 40 | 4 | 0 |
| control-2 | 78 | 16 | 2 |
| lessons-1 | 46 | 4 | 0 |
| lessons-2 | 54 | 5 | 0 |

- **Unchanged: 2 of 20 such turns ended in the fatal action. With the fix: 0 of 9.** That is no evidence
  of a difference.
- At every one of these turns exactly one action was fatal (one tile to click, or once one move), among
  many the agent could take. Most were not close calls: the agent had no reason to act there.

### What the runs do and do not show

- **They do not show the fix makes the agent solve the level, or solve it in fewer actions.** The unchanged
  agent solved it twice, once in 44 actions, fewer than either fixed run.
- **They are consistent with the fix stopping repeat deaths, and too few to show it.** One unchanged run
  in two repeated a death; zero fixed runs in two did. Counted by turn it is 2 of 20 against 0 of 9. A
  difference that size happens by chance often.
- The unchanged agent did better here than on 6 November (83 actions, three deaths, not solved), from the
  same board, notes and request. That alone shows how far single runs of this level vary.
- One level of one game. Whether a lesson helps on a later level, where spikes return, is not tested.
- The pinned game-over boards (`pin_game_overs`) were not part of these runs.

## What was run

| | Calls | Time | Tokens in / out |
|---|---|---|---|
| Stage 1: lessons | 6 | about 4 minutes | not totalled |
| Stage 2: the test | 80, none invalid, none retried | 43 minutes | 1.47 million / 243,000 |
| Level 2 from its start: four runs | 243, none sent back | 97 minutes of run time, two runs at a time | 3.74 million / 570,000 |

All calls were answered by Opus 5.5 at effort high on the subscription path.

## Files

- Code: `research/claude_arc_v1/policy.py` and `config.py` (the three switches),
  `research/memory_fix_v1/death_test.py` (the position test), `research/memory_fix_v1/bp35_local.py` (the
  local game), `local_arc.py` (the local game behind the harness's controller), `continue_bp35.py` (the
  level-2 runs), `level2_results.py` (their numbers).
- Tests: `tests/test_claude_arc_v1_recovery.py`, classes `PinnedGameOvers` and `GameOverLessons`.
- `death_test/`: `lessons.json` and `lessons_replies.jsonl` (stage 1), `requests.json` and `manifest.json`
  (the 10 frozen requests), `plan.json` (the rule, written before sending), `replies.jsonl`,
  `replies_scored.jsonl` (each action with what the local game did), `scores.json`.
- `level2_run/`: `plan.json` (written before the first call), `results.json` (per run and per turn: the
  action, the notes' status, the check, the lesson, and whether a game over was one action away),
  `replay.html` (all four runs action by action, built by `research/memory_fix_v1/replay_page.py`). The
  full run logs are in `.cache/claude_arc_runs/bp35-l2-*-20261115T014800Z/`, which is not in git.
