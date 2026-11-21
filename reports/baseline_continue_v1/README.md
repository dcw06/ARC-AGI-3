# Continuing the 6 November run past 100 actions (thin harness, Opus 5.5)

Batch 1 ran 2026-11-14 23:37 to 2026-11-15 08:09 PST. Results are at the end.

## What this is

The 6 November run (`research/claude_arc_v1`, Claude Opus 5.5, effort high, Claude subscription) stopped
every game at 100 actions. To get a baseline of how many actions the same agent needs per game, chosen
games are played on from their 101st action up to the per-game caps in
`../arc_skill_opus5_v1/action_caps_astra.json`.

First batch (the user's choice, 2026-11-14):

| Game | After 100 actions on 6 Nov | Cap | New actions |
|---|---|---|---|
| ar25 | 3 of 8 levels | 300 | 200 |
| bp35 | 1 of 9 levels, 3 resets used | 500 | 400 |
| cn04 | 2 of 6 levels | 250 | 150 |
| dc22 | 1 of 6 levels | 550 | 450 |
| g50t | 1 of 7 levels | 500 | 400 |

1,600 new actions. cd82 (cap 100, already reached) and ft09 (solved in 75) are skipped.

## How a game is continued

1. Its 100 saved actions are repeated on a local copy of the game with no model call. Every returned
   observation must hash to the one saved on 6 November, or the game is not played.
2. The saved replies are fed back to the policy, which rebuilds the agent's history and notes.
3. From action 101 the unchanged controller, policy and backend play, with the control settings of
   `config/claude_arc_v1.opus55_competition.json`. Games run one after another; nothing carries over
   between games.

There is no ARC scorecard: play is local. Counts come from each run's event log
(`.cache/claude_arc_runs/baseline-continue-<game>-<stamp>/`), which holds all actions, the first 100 included.

Code: `research/baseline_continue_v1/` (`local_games.py`, `continue_run.py`). It adds files only; the
harness in `research/claude_arc_v1/` is not edited.

## Is it the 6 November harness?

Checked before any model call (`continue_run.py check`, no cost):

- **Code.** The 31 files the 6 November run recorded equal commit `38f41e9`. Six harness files have
  changed since (switches added by later studies, all off here). With the control config, today's code
  produces the same system prompt and output schema as the 6 November code, byte for byte.
- **Requests.** For each of the five games, the request built at every one of the 100 saved turns (97
  for bp35, where three actions were controller resets) is identical to the request sent on 6 November.
  The controller's own resume path gives the identical request at action 100.
- **Games.** All 500 saved observations are reproduced by the local game files (same versions).
- **Environment.** Claude Code CLI 2.1.318 and package versions are the same as on 6 November. 150
  harness tests pass.

- **During the run.** At 23:40 PST, three minutes after the launch, other work began editing
  `config.py` and `policy.py` on disk. The batch is one process that loaded its code at 23:37:26, so it
  keeps the verified code for all five games. The `source_bindings` event of the ar25 log records that
  code; the same event in the later games' logs records the files on disk when each game began and may
  differ. `verify_requests.py` settles it from the logs alone: it rebuilds the agent's state with the
  code committed in `38f41e9` and compares every request the run sent. First check, 17 live requests of
  ar25: all identical. Repeated on all five logs after the batch: all 1,387 identical.

One adjustment was needed: the local engine reports `full_reset: true` on a game's first board, the live
service `false`. The flag is shown to the model on its first turn, so the local adapter sets it as the
live run had it.

## Limits to keep in mind

- **Reset allowance.** The harness ends a game at a game over once 10 level resets are used. That rule
  was sized for 100 actions and is kept, because the instruction was the original harness. bp35 has
  already used 3; if it dies 7 more times it stops before its cap, with `stop_reason: game_over`.
- **One run per game**, continued from one saved opening. It is a baseline, not a distribution.
- **Not a rerun of the first 100.** Those are the 6 November actions, replayed.
- **If a game is cut short** (plan limit, sleep, interruption), the batch stops and later games are not
  started. A stopped game cannot yet be continued again from where it stopped: the resume code refuses a
  log that was itself resumed. A merged log would be needed.

## Results (batch 1, ended 2026-11-15 08:09 PST)

8 hours 32 minutes, 1,387 model calls (22 s per call on average), no retries, no sleep, every game's
log passes the harness audit. `verify_requests.py` on all five logs: all 1,387 live requests are
identical to what the code committed in `38f41e9` builds.

| Game | Actions | Cap | Stopped by | Levels completed | At action 100 | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| ar25 | 300 | 300 | cap | 6 of 8 | 3 | 17, 14, 41, 41, 28, 115 | level 7, 44 actions |
| bp35 | 299 | 500 | reset limit | 2 of 9 | 1 | 17, 203 | level 3, 79 actions |
| cn04 | 250 | 250 | cap | 3 of 6 | 2 | 19, 33, 50 | level 4, 148 actions |
| dc22 | 550 | 550 | cap | 4 of 6 | 1 | 32, 125, 59, 123 | level 5, 211 actions |
| g50t | 500 | 500 | cap | 2 of 7 | 1 | 39, 122 | level 3, 339 actions |

- **No game was finished within its cap.** 17 of the 36 levels are completed, against 8 at action 100.
- **bp35 stopped 201 actions short of its cap**: 7 game overs on level 2 and 4 on level 3 used the
  harness's 10 level resets.
- **In each game one level absorbed most of the budget**: ar25 level 6 (115), bp35 level 2 (203), cn04
  level 4 (148, not completed), dc22 level 5 (211, not completed), g50t level 3 (339, not completed).

Actions on the levels this run completed, against the same levels in the reference runs:

| Game | Levels | This run | arc-skill + Opus 5 | Astra (adapter, high) | Human reference |
|---|---|---|---|---|---|
| ar25 | 1 to 6 | 256 | 176 | 171 | 442 |
| bp35 | 1 to 2 | 220 | 72 | 55 | 69 |
| cn04 | 1 to 3 | 102 | 76 | 68 | 168 |
| dc22 | 1 to 4 | 339 | 193 | 174 | 326 |
| g50t | 1 to 2 | 161 | 123 | 55 | 253 |

One run per game. The caps are the reference runs' totals rounded up, so reaching a cap unfinished means
this agent needs more actions than those runs did for the whole game.

Per-level counts with game overs and resets: `.cache/claude_arc_runs/baseline-continue-20261115T073726Z.json`.

## Results (ka59, 2026-11-15 09:39 to 10:34 PST)

Run on its own at the user's request, same procedure. The free check passed on the harness files as they
were on disk after the other session's edits (every saved board and request identical to 6 November).
54.9 minutes, 249 model calls, no retries, audit passes; all 249 live requests identical to the `38f41e9` code.

| Game | Actions | Cap | Stopped by | Levels completed | At action 100 | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| ka59 | 350 | 350 | cap | 3 of 7 | 1 | 30, 190, 77 | level 4, 53 actions |

Levels 1 to 3 took 297 actions here, against 108 for arc-skill + Opus 5, 109 for Astra and 188 for the
human reference. Level 2 alone took 190 actions with one game over.

Batch file: `.cache/claude_arc_runs/baseline-continue-20261115T173937Z.json`.

## Results (lf52 and ls20, 2026-11-15 10:49 to 15:30 PST)

Run in sequence at the user's request, same procedure; the free check passed for both before launch.
4 hours 41 minutes, 1,095 model calls, no retries, both logs pass the audit; all 1,095 live requests
identical to the `38f41e9` code.

| Game | Actions | Cap | Stopped by | Levels completed | At action 100 | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| lf52 | 800 | 800 | cap | 3 of 10 | 1 | 8, 710, 49 | level 4, 33 actions |
| ls20 | 500 | 500 | cap | 2 of 7 | 2 | 15, 45 | level 3, 440 actions |

- lf52 spent 710 actions and two game overs on level 2 before clearing it, then cleared level 3 in 49.
  Levels 1 to 3: 767 actions here, against 109 for arc-skill + Opus 5, 91 for Astra, 173 human.
- ls20 gained no level: 440 actions and three game overs on level 3 without clearing it (arc-skill 69,
  Astra 41, human 73). Its two completed levels took 60 actions, fewer than arc-skill (134), Astra (119)
  and the human reference (145).

Batch file: `.cache/claude_arc_runs/baseline-continue-20261115T184915Z.json`.

## Results (batch of 2026-11-15 22:35 to 2026-11-16 06:18 PST)

7 hours 43 minutes, 1,218 model calls, no retries, no sleep, all six logs pass the audit; all 1,218 live
requests identical to the `38f41e9` code (bp35 checked against its merged log).

| Game | Actions | Cap | Stopped by | Levels completed | Before this batch | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| bp35 | 500 | 500 | cap | 3 of 9 | 2 (at 299) | 17, 203, 137 | level 4, 143 actions |
| m0r0 | 250 | 250 | cap | 2 of 6 | 2 | 15, 56 | level 3, 179 actions |
| re86 | 650 | 650 | cap | 6 of 8 | 2 | 20, 36, 47, 42, 151, 77 | level 7, 277 actions |
| s5i5 | 300 | 300 | cap | 6 of 8 | 2 | 13, 28, 80, 31, 28, 36 | level 7, 84 actions |
| sb26 | 127 | 150 | **solved** | 8 of 8 | 6 | 9, 15, 16, 15, 17, 19, 17, 19 | |
| sc25 | 200 | 200 | cap | 3 of 6 | 3 | 22, 5, 37 | level 4, 136 actions |

- **sb26 is the first continued game to be solved**: 127 actions, against 124 for both arc-skill + Opus 5
  and Astra, and 213 for the human reference.
- bp35 used 17 level resets in all (7 game overs on level 2, 5 on level 3, 5 so far on level 4).
- m0r0 and sc25 gained no level: 179 and 136 actions on their open level.
- re86 and s5i5 each gained four levels and then stalled on level 7.

Actions on the levels this run completed, against the same levels in the reference runs:

| Game | Levels | This run | arc-skill + Opus 5 | Astra (adapter, high) | Human reference |
|---|---|---|---|---|---|
| bp35 | 1 to 3 | 357 | 108 | 89 | 113 |
| m0r0 | 1 to 2 | 71 | 50 | 38 | 141 |
| re86 | 1 to 6 | 373 | 292 | 278 | 590 |
| s5i5 | 1 to 6 | 216 | 170 | 163 | 469 |
| sb26 | 1 to 8 | 127 | 124 | 124 | 213 |
| sc25 | 1 to 3 | 64 | 51 | 42 | 74 |

## Results (batch of 2026-11-16 12:00 to 18:37 PST: sk48, sp80, su15, tn36)

6 hours 36 minutes, 846 model calls, no retries, all four logs pass the audit; all 846 live requests
identical to the `38f41e9` code. Calls were slower than in earlier batches (sk48 averaged 32 s).

| Game | Actions | Cap | Stopped by | Levels completed | At action 100 | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| sk48 | 500 | 500 | cap | 3 of 8 | 2 | 22, 43, 125 | level 4, 310 actions |
| sp80 | 250 | 250 | cap | 4 of 6 | 4 | 6, 8, 10, 45 | level 5, 181 actions |
| su15 | 150 | 150 | cap | 4 of 9 | 2 | 9, 21, 99, 14 | level 5, 7 actions |
| tn36 | 350 | 350 | cap | 4 of 7 | 0 | 122, 44, 29, 106 | level 5, 49 actions |

- tn36 had no level at action 100; it cleared level 1 at action 122 and three more after that.
- su15 gained two levels in 50 new actions and was stopped by its cap seven actions into level 5.
- sk48 gained one level and then spent 310 actions on level 4; sp80 gained none in 181 actions on level 5.

Actions on the levels this run completed, against the same levels in the reference runs:

| Game | Levels | This run | arc-skill + Opus 5 | Astra (adapter, high) | Human reference |
|---|---|---|---|---|---|
| sk48 | 1 to 3 | 190 | 136 | 82 | 339 |
| sp80 | 1 to 4 | 69 | 58 | 54 | 270 |
| su15 | 1 to 4 | 143 | 64 | 43 | 205 |
| tn36 | 1 to 4 | 301 | 70 | 45 | 170 |

## Results (batch of 2026-11-16 19:34 to 23:04 PST: tr87, tu93, vc33)

3 hours 30 minutes, 298 model calls, no retries, all three logs pass the audit; all 298 live requests
identical to the `38f41e9` code. wa30 was left out at the user's request (usage limit). tr87's calls
averaged 71 s.

| Game | Actions | Cap | Stopped by | Levels completed | At action 100 | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| tr87 | 200 | 200 | cap | 1 of 6 | 1 | 61 | level 2, 139 actions |
| tu93 | 209 | 250 | reset limit | 5 of 9 | 5 | 18, 15, 19, 17, 29 | level 6, 111 actions |
| vc33 | 200 | 200 | cap | 6 of 7 | 4 | 13, 8, 24, 28, 47, 72 | level 7, 8 actions |

- tu93 stopped 41 actions short of its cap: ten game overs on level 6 used the harness's 10 level resets
  (one had been used on level 2). It can be extended the way bp35 was.
- vc33 gained two levels and was stopped by its cap eight actions into its last level.
- tr87 gained no level in 139 actions on level 2.

Actions on the levels this run completed, against the same levels in the reference runs:

| Game | Levels | This run | arc-skill + Opus 5 | Astra (adapter, high) | Human reference |
|---|---|---|---|---|---|
| tr87 | 1 | 61 | 26 | 20 | 54 |
| tu93 | 1 to 5 | 98 | 111 | 94 | 234 |
| vc33 | 1 to 6 | 192 | 144 | 131 | 295 |

## All continued games so far

| Game | Actions | Cap | Levels completed | At action 100 |
|---|---|---|---|---|
| ar25 | 300 | 300 | 6 of 8 | 3 |
| bp35 | 500 | 500 | 3 of 9 (reset allowance raised to 50 after action 299) | 1 |
| cn04 | 250 | 250 | 3 of 6 | 2 |
| dc22 | 550 | 550 | 4 of 6 | 1 |
| g50t | 500 | 500 | 2 of 7 | 1 |
| ka59 | 350 | 350 | 3 of 7 | 1 |
| lf52 | 800 | 800 | 3 of 10 | 1 |
| ls20 | 500 | 500 | 2 of 7 | 2 |
| m0r0 | 250 | 250 | 2 of 6 | 2 |
| re86 | 650 | 650 | 6 of 8 | 2 |
| s5i5 | 300 | 300 | 6 of 8 | 2 |
| sb26 | 127 | 150 | 8 of 8, solved | 6 |
| sc25 | 200 | 200 | 3 of 6 | 3 |
| sk48 | 500 | 500 | 3 of 8 | 2 |
| sp80 | 250 | 250 | 4 of 6 | 4 |
| su15 | 150 | 150 | 4 of 9 | 2 |
| tn36 | 350 | 350 | 4 of 7 | 0 |
| tr87 | 200 | 200 | 1 of 6 | 1 |
| tu93 | 250 | 250 | 5 of 9 (reset allowance raised to 50 after action 209) | 5 |
| vc33 | 200 | 200 | 6 of 7 | 4 |
| wa30 | 850 | 850 | 4 of 9 | 2 |

Twenty-one games, 8,027 actions in total (5,927 new), 82 of 157 levels completed against 47 at action
100. One game solved within its cap (sb26). Not continued: cd82, lp85 and r11l (already at their cap of
100 on 6 November: 2 of 6, 7 of 8 and 5 of 6 levels) and ft09 (solved in 75). With those four, the 25
games hold 8,402 actions and 102 of 183 levels (67 on 6 November). Every game with actions left under
the caps has now been continued.

## Results (wa30, 2026-11-16 23:13 to 2026-11-17 02:50 PST)

3 hours 37 minutes, 745 model calls (17 s per call), no retries, the log passes the audit; all 745 live
requests identical to the `38f41e9` code. Batch file `.cache/claude_arc_runs/baseline-continue-20261117T071350Z.json`.

| Game | Actions | Cap | Stopped by | Levels completed | At action 100 | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| wa30 | 850 | 850 | cap | 4 of 9 | 2 | 36, 59, 187, 462 | level 5, 106 actions |

- Level 4 took 462 actions and 4 game overs, more than half the budget; level 3 took 187 and 1 game over.
  5 level resets used in all.
- Levels 1 to 4 in this run: 744 actions, against 277 for arc-skill + Opus 5, 211 for Astra (adapter,
  high) and 471 for the human reference.

## tu93 extended to its cap (2026-11-16 23:17 to 23:36 PST)

At the user's request, tu93 was continued from action 209 to its cap of 250 the way bp35 was: reset
allowance 50 for this game only, continuing from a merged log
(`merged-from-baseline-continue-tu93-20261117T033356Z.jsonl`). It ran alongside wa30 as its own process.
Free check before launch: all 209 saved boards and all 199 requests reproduced. 37 model calls, audit
passes, all 37 live requests identical to the `38f41e9` code.

Result: 250 of 250 actions, still 5 of 9 levels. Level 6 was not cleared in 152 actions and 13 game
overs; 14 level resets used in all. Batch file `.cache/claude_arc_runs/baseline-continue-20261117T071722Z.json`.

## Second round: caps at the human count (started 2026-11-19)

On 2026-11-18 the user asked for a baseline that allows more actions, kept close to the human
baseline. New caps, `action_caps_human.json`: the human reference count for the whole game (the sum of
the per-level baseline actions the ARC scorecard reports), rounded up to the next 50. Total 17,500
against 8,450; up to 9,050 new actions in 22 games. ft09 and sb26 are solved and unchanged; tn36 gets
nothing more, since its 350 actions already exceed its human count of 317.

Each game continues from where its last run stopped (`--extend`, a merged log of its whole earlier
play; cd82, lp85 and r11l continue from the 6 November log). The level-reset allowance is 50 for every
game in this round (`--resets 50`), so that no game stops short of its cap; it changes no request.
`continue_run.py` gained `--caps <file>`, and `--resets` now applies to every game of a command.

Batch 1 (ar25, bp35, cd82, cn04, dc22; 2,000 new actions), started 2026-11-19 00:00 PST on the
signed-in subscription, batch file `.cache/claude_arc_runs/baseline-continue-20261119T080027Z.json`.
Free check before launch: all five games' saved boards (300, 500, 100, 250, 550 actions) and every
saved request reproduced exactly.

Result of batch 1 (ended 2026-11-19 12:28 PST; 12 h 27 min, 1,631 model calls, 27 s per call, no
retries, all five logs pass the audit; all 1,631 live requests identical to the `38f41e9` code):

| Game | Actions | Cap | Stopped by | Levels completed | Before this round | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| ar25 | 393 | 750 | solved | 8 of 8 | 6 | 17, 14, 41, 41, 28, 115, 56, 81 | none |
| bp35 | 700 | 700 | cap | 4 of 9 | 3 | 17, 203, 137, 305 | level 5, 38 actions |
| cd82 | 200 | 200 | cap | 2 of 6 | 2 | 28, 7 | level 3, 165 actions |
| cn04 | 800 | 800 | cap | 4 of 6 | 3 | 19, 33, 50, 203 | level 5, 495 actions |
| dc22 | 1,250 | 1,250 | cap | 4 of 6 | 4 | 32, 125, 59, 123 | level 5, 911 actions |

- ar25 is solved (393 actions; arc-skill + Opus 5 260, Astra 257, human 748). Third game solved after
  ft09 and sb26.
- 1,643 new actions gained 4 levels (ar25 two, bp35 one, cn04 one). cd82 and dc22 gained none: dc22
  spent all 700 new actions on level 5, which has now taken 911 actions and 4 game overs (human 324,
  arc-skill 154, Astra 119); cn04's level 5 has taken 495 (human 208, arc-skill 72, Astra 68); cd82's
  level 3 has taken 165 (human 41, arc-skill 18, Astra 17).
- bp35 level 4 took 305 actions and 9 game overs; 22 level resets used in all.

Batch 2 (g50t, ka59, lf52, lp85, ls20; 1,950 new actions), started 2026-11-19 11:59 PST on the user's
second Claude subscription (`ARC_CLAUDE_TOKEN_FILE`, at the user's request), alongside the end of
batch 1; batch file `.cache/claude_arc_runs/baseline-continue-20261119T195939Z.json`. Free check before
launch: all five games' saved boards (500, 350, 800, 100, 500 actions) and every saved request
reproduced exactly. The log records the token file's name with every call. The account does not
change any request; the model and CLI are the same. At about 15:23 to 15:28 PST the lid was closed and
the Mac slept; the run paused and one model call (ka59) was retried.

At about 19:47 PST the computer was shut down by accident while ls20 was in play (action 649 of 800).
The process was killed, so that run has no summary and its batch entry was completed by hand from the
event log (`stop_reason: computer_shut_down`; the file before the edit is kept beside it with the
suffix `.before-shutdown-note`). The log ends cleanly after action 649: 147 of its 148 model calls were
answered, the last was in flight and no action had been sent for it. ls20 was continued from that log
at 20:15 PST, again on the second subscription (`--extend` on the interrupted folder; batch file
`.cache/claude_arc_runs/baseline-continue-20261120T041553Z.json`). Free check before the relaunch: all
649 saved boards and every saved request reproduced exactly, and the request the controller builds for
action 650 equals the one that was in flight. macOS (26.6.2) and the CLI (2.1.318) are unchanged after
the restart.

Result of batch 2 (g50t, ka59, lf52, lp85: 11:59 to 19:14 PST, 1,368 model calls, one retry, all four
logs pass the audit; ls20 up to the shutdown: 147 answered calls; every compared request of the five
logs is identical to the `38f41e9` code):

| Game | Actions | Cap | Stopped by | Levels completed | Before this round | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| g50t | 900 | 900 | cap | 2 of 7 | 2 | 39, 122 | level 3, 739 actions |
| ka59 | 750 | 750 | cap | 3 of 7 | 3 | 30, 190, 77 | level 4, 453 actions |
| lf52 | 1,350 | 1,350 | cap | 4 of 10 | 3 | 8, 710, 49, 537 | level 5, 46 actions |
| lp85 | 124 | 400 | solved | 8 of 8 | 7 | 7, 10, 16, 17, 18, 24, 8, 24 | none |
| ls20 | 800 | 800 | cap (in two runs, see above) | 2 of 7 | 2 | 15, 45 | level 3, 740 actions |

- lp85 is solved (124 actions; arc-skill + Opus 5 93, Astra 94, human 388). Fourth game solved after
  ft09, sb26 and ar25.
- lf52 gained one level: level 4 took 537 actions (human 71, arc-skill 54, Astra 56).
- g50t and ka59 gained none. g50t's level 3 has taken 739 actions and 5 game overs (human 179,
  arc-skill 92, Astra 64); ka59's level 4 has taken 453 and 3 game overs (human 51, arc-skill 45,
  Astra 41).
- ls20's continuation after the shutdown ended at the cap at 20:49 PST (151 actions, 150 model calls,
  33 min, no retries, log passes the audit, every request identical to the `38f41e9` code). ls20
  gained no level: level 3 has taken 740 actions and 6 game overs (human 73, arc-skill 69, Astra 41).
- Batch 2 in all: 1,674 new actions gained 2 levels (lf52 one, lp85 one).

State of round 2 after batches 1 to 3 (2026-11-19 20:50 PST; 11 of the 22 games with new actions
played, m0r0 only to 950 of 1,150): 12,419 actions over the 25 games, 108 of 183 levels, 4 games
solved (ft09, sb26, ar25, lp85). 4,017 new actions in this round gained 6 levels. `replay_scorecard.py
expect` (offline, ARC's scoring rule applied to the recorded actions) gives an expected card score of
39.62, against the official 36.29 after round 1; no new scorecard has been sent.

Batches 4 and 5 (all remaining games except wa30; 3,400 new actions, split evenly between the user's
two subscriptions at the user's request), both started 2026-11-19 21:39 PST and running side by side:

- Batch 4, signed-in subscription: m0r0 (200), r11l (150), re86 (650), sc25 (150), sp80 (300),
  su15 (250); 1,700 new actions; batch file `.cache/claude_arc_runs/baseline-continue-20261120T053929Z.json`.
- Batch 5, second subscription (`ARC_CLAUDE_TOKEN_FILE`): s5i5 (350), sk48 (600), tr87 (250),
  tu93 (250), vc33 (250); 1,700 new actions; batch file
  `.cache/claude_arc_runs/baseline-continue-20261120T053933Z.json`.

The games are not in table order because no split in table order gives 1,700 each. Free check before
launch: the saved boards and every saved request of all eleven games reproduced exactly (950, 100,
650, 200, 250, 150 and 300, 500, 200, 250, 200 actions). wa30 (1,000 new actions) is left for later.

Result of batch 4 (ended 2026-11-20 07:27 PST; 9 h 48 min, 1,586 model calls, no retries, all six logs
pass the audit; all 1,586 live requests identical to the `38f41e9` code):

| Game | Actions | Cap | Stopped by | Levels completed | Before this round | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| m0r0 | 1,150 | 1,150 | cap | 2 of 6 | 2 | 15, 56 | level 3, 1,079 actions |
| r11l | 159 | 250 | solved | 6 of 6 | 5 | 4, 11, 17, 15, 30, 82 | none |
| re86 | 1,300 | 1,300 | cap | 6 of 8 | 6 | 20, 36, 47, 42, 151, 77 | level 7, 927 actions |
| sc25 | 350 | 350 | cap | 3 of 6 | 3 | 22, 5, 37 | level 4, 286 actions |
| sp80 | 550 | 550 | cap | 4 of 6 | 4 | 6, 8, 10, 45 | level 5, 481 actions |
| su15 | 400 | 400 | cap | 7 of 9 | 4 | 9, 21, 99, 14, 80, 12, 10 | level 8, 155 actions |

- r11l is solved (159 actions, human 233). su15 gained three levels (5, 6 and 7 in 80, 12 and 10
  actions). 1,609 new actions gained 4 levels.
- m0r0, re86, sc25 and sp80 gained none; each spent all its new actions on one level (m0r0 level 3:
  1,079 actions and 7 game overs; re86 level 7: 927 and 3; sc25 level 4: 286 and 6; sp80 level 5: 481
  and 11).

Batch 5 stopped early at 2026-11-20 07:07 PST: tr87's call for action 320 exceeded the harness's
240-second deadline three times in a row (first try and both retries), which ends the game with
`TransportFailure`; tu93 and vc33 had not started. It was not a usage limit: no call was refused, the
two calls before it took 13 and 14 s, and the other subscription's batch ran on without an error.
tr87's calls were slow throughout (median 28 s, mean 66 s, a dozen above 200 s; actions 261 and 273
had also timed out and succeeded on a retry), while sk48 on the same account had a median of 25 s and
no failure. The deadline and the retry count are the 6 November settings and were not changed.

Result of batch 5 up to the stop (903 model calls answered, 5 retried; all three logs pass the audit;
every compared request identical to the `38f41e9` code):

| Game | Actions | Cap | Stopped by | Levels completed | Before this round | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| s5i5 | 486 | 650 | solved | 8 of 8 | 6 | 13, 28, 80, 31, 28, 36, 104, 166 | none |
| sk48 | 1,100 | 1,100 | cap | 4 of 8 | 3 | 22, 43, 125, 361 | level 5, 549 actions |
| tr87 | 319 | 450 | three timed-out calls | 2 of 6 | 1 | 61, 224 | level 3, 34 actions |

The three unfinished games were relaunched at 07:10 PST on the second subscription, tr87 last so that
a repeat of the timeout cannot hold up the other two: tu93 (250), vc33 (250), tr87 (131 left, from
its interrupted log); batch file `.cache/claude_arc_runs/baseline-continue-20261120T151023Z.json`.
Free check before the relaunch: saved boards and requests of all three reproduced exactly.

Final result of batch 5, both parts (relaunch ended 2026-11-20 13:35 PST; one more tr87 call timed
out and succeeded on its retry; all logs pass the audit; every compared request identical to the
`38f41e9` code):

| Game | Actions | Cap | Stopped by | Levels completed | Before this round | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|
| s5i5 | 486 | 650 | solved | 8 of 8 | 6 | 13, 28, 80, 31, 28, 36, 104, 166 | none |
| sk48 | 1,100 | 1,100 | cap | 4 of 8 | 3 | 22, 43, 125, 361 | level 5, 549 actions |
| tr87 | 450 | 450 | cap (in two runs) | 4 of 6 | 1 | 61, 224, 52, 52 | level 5, 61 actions |
| tu93 | 500 | 500 | cap | 8 of 9 | 5 | 18, 15, 19, 17, 29, 268, 14, 36 | level 9, 84 actions |
| vc33 | 446 | 450 | solved | 7 of 7 | 6 | 13, 8, 24, 28, 47, 72, 254 | none |

- s5i5 (486 actions, human 638) and vc33 (446, human 447) are solved. 1,532 new actions gained 10
  levels (s5i5 two, sk48 one, tr87 three, tu93 three, vc33 one).
- tu93's level 6 took 268 actions and 19 game overs; 24 level resets used in all.

State of round 2 after batches 1 to 5 (2026-11-20 13:36 PST; every game but wa30 is at its cap or
solved): 15,560 actions over the 25 games, 122 of 183 levels, 7 games solved (ft09, sb26, ar25, lp85,
r11l, s5i5, vc33). 7,158 new actions in this round gained 20 levels. `replay_scorecard.py expect`
(offline) gives an expected card score of 45.12, against the official 36.29 after round 1; no new
scorecard has been sent. wa30 (850 of 1,850 played) is the only game left.

Batch 6 (wa30, limited to 150 new actions at the user's request: `--budget 150`, so it stops at action
1,000 of 1,850 unless solved first), started 2026-11-20 14:30 PST on the signed-in subscription; batch
file `.cache/claude_arc_runs/baseline-continue-20261120T223057Z.json`. Free check before launch: all
850 saved boards and every saved request reproduced exactly.

Result of batch 6 (ended 2026-11-20 15:08 PST; 38 min, 150 model calls, no retries, log passes the
audit; all 150 live requests identical to the `38f41e9` code):

| Game | Actions | Cap in this batch | Table cap | Stopped by | Levels completed | Before this round | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|---|
| wa30 | 1,000 | 1,000 | 1,850 | the 150-action limit | 6 of 9 | 4 | 36, 59, 187, 462, 110, 70 | level 7, 76 actions |

- wa30 gained two levels: level 5 in 110 actions (human 368, arc-skill 110, Astra 111) and level 6 in
  70 (human 68, arc-skill 59, Astra 46). No game over in the 150 actions. 850 actions are left under
  its table cap.
- State after batch 6: 15,710 actions over the 25 games, 124 of 183 levels, 7 games solved; offline
  expected card score 46.13 (wa30's game score 14.45 to 39.81); no new scorecard has been sent.

Batch 7 (wa30, 300 more new actions at the user's request: `--budget 300`, so it stops at action
1,300 of 1,850 unless solved first), started 2026-11-20 15:13 PST on the signed-in subscription; batch
file `.cache/claude_arc_runs/baseline-continue-20261120T231341Z.json`. Free check before launch: all
1,000 saved boards and every saved request reproduced exactly.

Result of batch 7 (ended 2026-11-20 16:43 PST; 89 min, 299 model calls, no retries, log passes the
audit; all 299 live requests identical to the `38f41e9` code):

| Game | Actions | Cap in this batch | Table cap | Stopped by | Levels completed | Before this batch | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|---|
| wa30 | 1,300 | 1,300 | 1,850 | the 300-action limit | 7 of 9 | 6 | 36, 59, 187, 462, 110, 70, 244 | level 8, 132 actions |

- wa30 gained one level: level 7 in 244 actions and one game over (human 79, arc-skill 80, Astra 45).
  Level 8 is open after 132 actions (human 442, arc-skill 145, Astra 108). 550 actions are left under
  its table cap.
- State after batch 7: 16,010 actions over the 25 games, 125 of 183 levels, 7 games solved; offline
  expected card score 46.20 (wa30's game score 39.81 to 41.44). The second official scorecard below
  does not include these 300 actions.

Batch 8 (wa30, its last 550 actions, to the table cap of 1,850), started 2026-11-20 17:03 PST on the
signed-in subscription. The user asked that a sleep of the computer should not interrupt it. A
sleeping computer runs nothing, so the run pauses during a sleep and resumes on wake; what can end it
is the call in flight timing out three times in a row (as tr87 did). `keep_going.py` (new) covers
that: it starts `continue_run.py run wa30` and, if that stops short of the target, waits 5 minutes and
starts it again from the last saved action after the free check; it gives up after 4 starts in a row
that add no action. Each start is the ordinary command; no request changes. Log
`.cache/claude_arc_runs/baseline-continue-round2-h.log`; first batch file
`.cache/claude_arc_runs/baseline-continue-20261121T010328Z.json`.

Result of batch 8 (ended 2026-11-20 21:50 PST; 287 min on the clock, of which about 92 min the
computer was asleep; 546 model calls, no retries, log passes the audit; all 546 live requests identical
to the `38f41e9` code):

| Game | Actions | Cap in this batch | Table cap | Stopped by | Levels completed | Before this batch | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|---|
| wa30 | 1,850 | 1,850 | 1,850 | action cap | 7 of 9 | 7 | 36, 59, 187, 462, 110, 70, 244 | level 8, 682 actions |

- No new level. Level 8 is open after 682 actions and 4 game overs (human 442, arc-skill 145, Astra
  108).
- The lid was closed four times (17:59 for 30 s, 18:23 to 19:29, 19:37 for 40 s, 19:59 to 20:25). The
  run paused each time and went on by itself on wake: one start, no timeout, `keep_going.py` never had
  to restart it. The computer was on battery throughout.
- **Round 2 is complete.** State: 16,560 actions over the 25 games (cap total 17,500), 125 of 183
  levels, 7 games solved (ft09, sb26, ar25, lp85, r11l, s5i5, vc33); offline expected card score 46.20.
  The second official scorecard below counts wa30 at 1,000 actions (game score 39.81, now 41.44), so it
  shows 46.13.

### Offline checks on the caps (2026-11-20, `cap_check.py`, no model call)

Asked by the user: would the caps be better changed? A cut is a prefix of the saved play, so these
numbers are exact for rules that stop a game earlier; they say nothing about play past the cap.

| Every game cut at this share of its cap | Actions | Levels | Card score |
|---|---|---|---|
| 25% | 4,376 | 72 | 22.80 |
| 50% | 8,674 | 98 | 35.36 |
| 75% | 12,748 | 117 | 43.38 |
| 100% | 16,560 | 125 | 46.20 |

| Same caps, and a game ends when its open level has used k times the human count | Actions | Levels | Card score |
|---|---|---|---|
| k = 2 | 8,428 | 97 | 39.54 |
| k = 3 | 10,359 | 99 | 40.29 |
| k = 5 | 14,832 | 121 | 45.92 |
| k = 8 | 15,626 | 121 | 45.92 |

- The last quarter of the budget bought 2.8 points; the second quarter bought 12.6.
- 7,940 of the 16,560 actions were spent on the level still open when a game stopped.
- A limit of 3 times per level costs 6 points and 26 levels: slow levels still unlock later ones.
  A limit of 5 times saves about 1,700 actions for 0.3 points.
- Six games reached the cap soon after a new level began, with at most 1.6 times that level's human
  count used on it: lf52 (0.2), tu93 (0.8), tr87 (0.9), bp35 (1.2), wa30 (1.5), tn36 (1.6). Their last
  level was cut short, not failed. What more actions would gain there cannot be measured offline.
- Not the same test as the official Opus 5 run (ARC Prize's standard harness, 40.67, 95 levels, 10,557
  actions): another model (Opus 5), another harness (one growing conversation per game), another stop
  rule. In that run 15 of 19 unsolved games ended at exactly 5 times the human count on the open level
  (13 of 14 for GPT-6 Astra on the same harness), so the harness appears to end a game there and to
  have no cap on the game total; this is inferred from the recordings, not read from ARC's code. Four
  Opus 5 games (cn04, dc22, re86, sp80) ended earlier for a reason not known. Under that rule our score
  would be at least 45.92, because the rule would let most of our unsolved games play past our cap.
- Decision: caps unchanged. The rule was fixed before the results, and the baseline is for comparing
  later harness changes under one budget.

### Second official scorecard by replay (2026-11-20 15:31 to 16:20 PST)

At the user's request, made while batch 7 was playing. Scorecard:
https://arcprize.org/scorecards/82bd80c9-3b07-43e7-9c11-f7aff912dd35 (competition mode, same tags as
the first replay). It covers the state after batch 6: wa30 is taken from its last finished run (1,000
actions); the actions batch 7 was playing are not in it. `replay_scorecard.py` gained `--finished-only`
for this (leaves out the log of a game still in play; without it `send` refuses while a continuation
runs).

- Before sending: `expect` 46.1330; `dry` matched all 15,710 recorded actions against the local game
  copies; `inventory` found all 25 recorded game versions on offer.
- All 15,710 recorded actions of the 25 games were sent, and every observation the service returned
  hashed to the recorded one. No game stopped early, no transport error. 49 minutes.
- Official score at close: **46.13** (46.1330), 124 of 183 levels, 15,710 actions, 7 games completed
  (ft09, sb26, ar25, lp85, r11l, s5i5, vc33). First replay (round 1): 36.29, 102 levels, 8,402
  actions, 2 games. 6 November: 23.16, 67 levels, 2,475 actions, 1 game.
- All 25 official game scores equal the scores predicted offline.
- Manifest: `.cache/claude_arc_runs/baseline-replay-send-20261120T233113Z/manifest.json`, copied to
  `data/scorecard_replay_manifest_2.json`; `data/recorded_actions_2.json` holds the 15,710 actions
  of this scorecard in the format of `data/recorded_actions.json`.

Batch 3 (m0r0, r11l, re86, s5i5, sc25 in that order, limited to 700 new actions in total at the
user's request: `--budget 700`), started 2026-11-19 15:35 PST on the signed-in subscription, alongside
batch 2; batch file `.cache/claude_arc_runs/baseline-continue-20261119T233503Z.json`. m0r0 alone has
900 new actions under its cap, so unless it is solved first it uses the whole limit and stops at
action 950 of 1,150; the later games start only if actions are left. Free check before launch: all
five games' saved boards (250, 100, 650, 300, 200 actions) and every saved request reproduced exactly.
`continue_run.py` gained `--budget <n>`.

Result of batch 3 (ended 2026-11-19 19:11 PST; 3 h 37 min, 696 model calls, no retries, log passes the
audit; all 696 live requests identical to the `38f41e9` code):

| Game | Actions | Cap in this batch | Table cap | Stopped by | Levels completed | Before this round | Actions per completed level | Open level when stopped |
|---|---|---|---|---|---|---|---|---|
| m0r0 | 950 | 950 | 1,150 | the 700-action limit | 2 of 6 | 2 | 15, 56 | level 3, 879 actions |

- m0r0 gained no level: all 700 new actions went to level 3, which has now taken 879 actions and 5
  level resets (human 203, arc-skill 61, Astra 82).
- The limit was used up by m0r0, so r11l, re86, s5i5 and sc25 did not start. m0r0 has 200 actions left
  under its table cap of 1,150.

## Official scorecard by replay (prepared 2026-11-16, to run when wa30 ends)

The user asked for one scorecard covering all 25 games. `replay_scorecard.py` sends every recorded action
to the ARC service in one competition-mode scorecard, tagged `replay-of-recorded-actions`, with no model
call. After each action the returned observation must hash to the recorded one; a game stops at the first
difference (competition mode allows one start per game).

Checked offline before any live call:

- `expect`: ARC's scoring rule, read off the 6 November scorecard, reproduces all 25 of its game scores.
  A completed level scores 100 (H / A) squared, capped at 115; levels are weighted 1, 2, 3, ...; a game
  cannot score more than the weight share of its completed levels; the card is the mean over 25 games.
- `dry`: the whole replay against the local game copies: every recorded action of all 25 games matched.
- `inventory` (read-only call): the service still offers all 25 recorded game versions.

Expected card score with wa30 still in progress: 35.98, against 23.16 on 6 November.

### Result (live replay, 2026-11-17 02:52 to 03:11 PST)

Scorecard: https://arcprize.org/scorecards/6b134146-d820-4c44-a122-3f5c43e208b6 (competition mode, tags
`claude-arc-v1`, `hypotheses`, `competition`, `replay-of-recorded-actions`, `baseline-continue-v1`).

- All 8,402 recorded actions of the 25 games were sent, and every observation the service returned
  hashed to the recorded one. No game stopped early, no transport error. 19 minutes.
- Official score at close: **36.29** (36.2889), 102 of 183 levels, 8,402 actions, 2 games completed
  (ft09, sb26). The 6 November card: 23.16, 67 levels, 2,475 actions, 1 game completed.
- The score predicted offline before sending was 36.2889; all 25 official game scores equal the
  predicted ones (largest difference 1e-14).
- Saved: `.cache/claude_arc_runs/baseline-replay-send-20261117T105215Z/` (`manifest.json` with the
  service's closing result, `replay.jsonl`).
- In this folder (the run logs themselves are too large for the repository and stay in `.cache`):
  `data/scorecard_replay_manifest.json` is a copy of that manifest (the service's closing result with
  per-level actions for every game, and the predicted scores); `data/recorded_actions.json` holds
  every one of the 8,402 actions in the order played, with the number of completed levels after each,
  taken from the logs by `replay_scorecard.recorded()`.

| Game | Actions | Levels | Score | 6 Nov actions | 6 Nov levels | 6 Nov score |
|---|---|---|---|---|---|---|
| ar25 | 300 | 6 of 8 | 58.33 | 100 | 3 | 16.67 |
| bp35 | 500 | 3 of 9 | 3.49 | 100 | 1 | 2.22 |
| cd82 | 100 | 2 of 6 | 14.29 | 100 | 2 | 14.29 |
| cn04 | 250 | 3 of 6 | 28.57 | 100 | 2 | 14.29 |
| dc22 | 550 | 4 of 6 | 40.34 | 100 | 1 | 4.76 |
| ft09 | 75 | 6 of 6 | 100.00 | 75 | 6 | 100.00 |
| g50t | 500 | 2 of 7 | 10.71 | 100 | 1 | 3.57 |
| ka59 | 350 | 3 of 7 | 10.16 | 100 | 1 | 3.11 |
| lf52 | 800 | 3 of 10 | 8.41 | 100 | 1 | 1.82 |
| lp85 | 100 | 7 of 8 | 77.78 | 100 | 7 | 77.78 |
| ls20 | 500 | 2 of 7 | 10.71 | 100 | 2 | 10.71 |
| m0r0 | 250 | 2 of 6 | 14.29 | 100 | 2 | 14.29 |
| r11l | 100 | 5 of 6 | 71.43 | 100 | 5 | 71.43 |
| re86 | 650 | 6 of 8 | 58.33 | 100 | 2 | 8.33 |
| s5i5 | 300 | 6 of 8 | 58.33 | 100 | 2 | 8.33 |
| sb26 | 127 | 8 of 8 | 100.00 | 100 | 6 | 58.33 |
| sc25 | 200 | 3 of 6 | 27.11 | 100 | 3 | 27.11 |
| sk48 | 500 | 3 of 8 | 15.02 | 100 | 2 | 8.33 |
| sp80 | 250 | 4 of 6 | 47.62 | 100 | 4 | 47.62 |
| su15 | 150 | 4 of 9 | 18.35 | 100 | 2 | 6.67 |
| tn36 | 350 | 4 of 7 | 19.11 | 100 | 0 | 0.00 |
| tr87 | 200 | 1 of 6 | 3.73 | 100 | 1 | 3.73 |
| tu93 | 250 | 5 of 9 | 33.33 | 100 | 5 | 33.33 |
| vc33 | 200 | 6 of 7 | 63.31 | 100 | 4 | 35.71 |
| wa30 | 850 | 4 of 9 | 14.45 | 100 | 2 | 6.67 |

What the card is: the actions were chosen by the model during the 6 November run and its local
continuation; this card only replays them, so it is an official record of that play, not a second
independent run. bp35 and tu93 were played with a reset allowance of 50 after their first stop.
