# Private replay of retained Qwen actions

The owner selected viewing retained real runs first. A local interactive replay now shows Track 3 session 2's
continuation arm on four public development games. These are recorded Qwen decisions and real offline-engine
observations, not scripted or newly generated actions. This is a historical study harness, not a new scored
E1S-R production run or a claim of solving improvement.

| Item | Result |
| --- | --- |
| Games | ar25, wa30, ls20, s5i5 |
| Episodes | 4 continuation/control episodes |
| Recorded acknowledged actions | 160, 40 per game |
| Distinct retained boards | 114 |
| Controls | Play/pause, previous/next, slider, game selection, returned-frame selection, keyboard arrows |
| Display | Before/after boards, ACTION6 click markers, engine state/levels, changed-cell counts and recorded latency |
| Source integrity | All 13 run-manifest members hash/size checked before selecting the four episodes |
| Browser check | 662 checks pass, covering all 160 action labels/positions, canvas colors, episode/step controls, autoplay/pause and keyboard stepping |
| New model requests / provider calls / attempts | 0 / 0 / 0 |
| Output access | Private local HTML and verification receipts in the git-ignored replay directory |

`scripts/build_retained_game_replay.py` and its template contain no retained frames or private account bindings.
The generated viewer contains selected recorded observations/actions; keep it local. It embeds no raw model
prompts, model weights, credentials or private dataset references, and uses no external assets or network calls.
The builder refuses raw output in a non-ignored repository path. The original evidence and consumed attempts are
unchanged. The scored submission's full-job cap and all launch gates remain in force.

To regenerate a private viewer from retained Track 3 evidence, choose a **new** output filename:

```sh
python scripts/build_retained_game_replay.py --run <retained-worker-run-directory> --output <git-ignored-directory>/index.html --arm continuation
```

Open the resulting HTML in a browser, choose a game and press **Play**, or use the arrow buttons/keys. All returned
frames remain available in order; the default view selects the final returned frame. Playback intervals are viewing
controls, not measurements of inference speed. A changed board alone is not credited as progress.
