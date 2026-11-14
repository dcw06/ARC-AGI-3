# arc-skill on a Claude subscription (third harness)

Set up 2026-11-10. One run so far: bp35 levels 1 to 4 (see "First run").

## What this is

- Harness: [arc-skill](https://github.com/pbshgthm/arc-skill) at commit `aebfe39`, a skill for the
  official Claude Code CLI: 129 lines of instructions plus a command-line tool (`arc`) that the model
  drives. The model must attach a prediction to every action; the tool grades it.
- Model: Claude Opus 5 (`claude-opus-5`) at effort `high`, through the signed-in Claude subscription.
  The paid API is not used.
- Play is on the local engine from a local game cache, the same game versions as the baseline.

## Baseline already published

The author's run (Claude Code + arc-skill + Opus 5) has a public scorecard:
<https://arcprize.org/scorecards/24ddb219-987e-464f-9050-6398a29cf5ac>, saved as
`../arc_agi3_loss_audit/data/arc_skill_opus5_scorecard.json`.

| | |
|---|---|
| Games / levels | 25 of 25 / 183 of 183 |
| Actions / resets | 7,645 / 18 (resets in 8 games) |
| Tycho + Opus 5, same games | 6,641 actions |
| bp35 | 482 actions, 4 resets; per level 18, 54, 36, 28, 31, 73, 54, 106, 82 |

The scorecard lists actions for every level, so one game or one level of a new run can be compared
without replaying the other 24 games. It is a replay of locally played runs, published by the author
and not verified by ARC Prize. The author does not state the effort level or how the 25 games were
launched.

## Use

```
scripts/run_arc_skill.sh check                 # login, model and permission check (about 7 short model calls)
scripts/run_arc_skill.sh play bp35 r1          # interactive, in your terminal
scripts/run_arc_skill.sh auto bp35 r1          # unattended; log in ~/Desktop/arc-skill-work/logs/
scripts/arc_skill_compare.py bp35-r1           # per-level actions against the baseline
```

Running `play` or `auto` again with the same game and tag continues that run. `ARC_SKILL_MODEL` and
`ARC_SKILL_EFFORT` override the model and effort (for example `claude-opus-5-5`).

Every model call counts against the plan's usage limits; how much one game uses is not yet measured.
Turn off "usage credits" in claude.ai Settings > Usage before a long run if paid credits must not be
spent when the limit is reached.

## Where things are

| Path | Content |
|---|---|
| `~/Desktop/arc-skill-work/skill-master/` | pinned copy of the skill (`ARC_SKILL_COMMIT` beside it) |
| `~/Desktop/arc-skill-work/runs/<game>-<tag>/` | one project folder per run: its own skill copy, `.arc/` game state, notes |
| `~/Desktop/arc-skill-work/settings/`, `logs/` | per-run permission rules; unattended transcripts |
| `~/.cache/arc-skill/arcade/` | game cache: ar25, bp35, lf52, ls20, vc33 so far; others download on first use |
| `.cache/arc_skill/venv`, `.cache/arc_skill/src` | Python 3.14 with `arc-agi==0.9.9`; the cloned repository |

The work folder is outside this repository on purpose: Claude Code keys its memory to the git
repository, and this project's memory notes contain bp35 solutions.

## How a run is kept cold

- Each run has its own folder, so replicates cannot read each other's notes.
- User-level Claude settings are not loaded and auto memory is off. Your user settings would otherwise
  set a different model, effort `xhigh`, and allow reading everything under `/Users/dcw06`.
- The environment is rebuilt from scratch: no `ANTHROPIC_*` variable and no ARC key reach the session.
- Reading the game cache, this repository, other sessions' files and the web is denied by rule.

These are permission rules, not an operating-system sandbox. The skill's `arc python` command runs
model-written Python with your user permissions, so a model that ignored the skill's "never inspect the
game's source" rule could still open the cached game file. Tycho runs its code in Docker; this does not.

## Differences from the author's setup

- Effort is set to `high` explicitly (Claude Code's documented default for Opus 5).
- Auto memory, web search and web fetch are off.
- `play` sends the README's exact prompt, `solve ARC-AGI-3 game <id>`. `auto` adds two sentences:
  call the launcher by its literal path, and the current directory is the run directory. Unattended
  sessions cannot approve prompts, and a command written as `"$ARC" ...` cannot be pre-approved.

## Setup check (2026-11-10)

`scripts/run_arc_skill.sh check` reported: model `claude-opus-5`; `apiKeySource` `none` (subscription
login); skill found; `arc --help`, `arc start ls20`, one graded action and `python3` ran; reading the
game cache and the `"$ARC"` form were denied, as intended.

## First run: bp35 levels 1 to 4 (2026-11-10)

`ARC_SKILL_STOP_LEVELS=4 scripts/run_arc_skill.sh auto bp35 l4-r1`, Opus 5, effort `high`, unattended.
One run; the published baseline is also one run.

| Level | This run | Published baseline | Human | Notes |
|---|---|---|---|---|
| 1 | 19 | 18 | 21 | |
| 2 | 74 | 54 | 48 | two deaths, two resets |
| 3 | 34 | 36 | 44 | |
| 4 | 23 | 28 | 38 | no deaths or resets |
| 1 to 4 | 150 | 136 | 151 | 1.10x the baseline |

- Level 4 did not reproduce the baseline's 28: this run took 23. Tycho with Opus 5.5 took 19 or 23 from
  its level-4 checkpoint (`../tycho_decision_check_l4_v1/`); the optimum is 19.
- Levels 1 and 3 are within two actions of the baseline. Level 2 is 20 over, all of it from two deaths.
- So the same harness and model do not return the same counts run to run. With one run on each side, a
  difference of a few actions on a clean level, or of tens on a level with deaths, is not evidence.
- About 45 minutes of wall time, 306 model messages, roughly 52 million cached input tokens, no context
  compaction. The share of the plan limit it used was not visible from here.

**One intervention.** After the first death the agent tried undo (ACTION7) while the game was over. The
local game process then answered every command, including reset, with "environment returned no
frames". The agent identified the fix (restart the process; the harness replays the action journal),
but the permission rules refused `kill`, and it spent about five minutes reading the harness code. I
stopped the process by hand; the agent restarted it, replayed 25 actions, reset and continued. No
failed command was counted as an action. The run was therefore not fully hands-off. Stop switches
(`ARC_SKILL_STOP_LEVELS`, `ARC_SKILL_MAX_ACTIONS`, `ARC_SKILL_MAX_MINUTES`) were added to `auto` for
this run; they act from outside the session and do not change the prompt.

## Action caps for a 25-game run

`action_caps.json` lists, per game, the baseline count, the Tycho and Strands Opus 5 counts, the human
reference and a proposed cap for `ARC_SKILL_MAX_ACTIONS`.

- Rule: cap = the larger of 2 x baseline and baseline + 150, rounded up to 10. Caps total 15,730
  against a baseline of 7,645.
- Evidence: across the three published Opus 5 runs (arc-skill, Tycho, Strands) the highest count for a
  game is at most 1.77 x the arc-skill count. Every cap is at least 1.30 x the highest of the three.
- The cap is a guard against a runaway game, not a budget: a game cut off by its cap has no count for
  its remaining levels.

## Notes on the skill itself

- Its instructions name the usual meaning of each action and tell the model to "finish first". It is
  not a hint-free prompt like the Strands one used for PRO-LONG here.
- The repository has no licence file. It is used here unmodified and is not redistributed.
- I read the tool's code before running it: no network calls of its own (the `arc-agi` package downloads
  games), a local socket to one background game process per run, and no deletion outside the run folder.
