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
