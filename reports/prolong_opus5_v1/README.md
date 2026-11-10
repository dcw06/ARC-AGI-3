# PRO-LONG on a Claude subscription (second harness)

Set up 2026-11-09. First run (bp35, Opus 5) started the same day; see "Run log".

## What this is

- Harness: [PRO-LONG](https://github.com/alexisfox7/PRO-LONG) (MIT), Claude Code backend, at the
  commit in `.cache/prolong/arc-agi-3/UPSTREAM_COMMIT`. It runs the official Claude Code CLI inside a
  Docker container and signs in with a subscription token, so usage counts against the plan.
- Prompt: replaced with the hint-free prompt from the
  [Strands fork](https://github.com/strands-labs/benchmark-harnesses/tree/main/arc-agi-3-agent)
  (Apache-2.0). PRO-LONG's original prompt names the actions and colours and mentions players,
  walls, goals and step budgets; it is kept next to the new one as `prompts_prolong_original.py.txt`.
- Installed in `.cache/prolong/arc-agi-3/` (git-ignored). Launcher: `scripts/run_prolong.sh`.

## Evidence behind the choice

The Strands fork of PRO-LONG with Opus 5 has an official scorecard:
<https://arcprize.org/scorecards/8a10b024-3560-448f-ac31-becc48affe5b>

| Check | Result |
|---|---|
| Score on the scorecard | 99.949 (reported as 99.95) |
| Games won / levels | 25 of 25 / 183 of 183, competition mode |
| Actions / resets | 8,841 / 70 |
| Score recomputed from per-level actions | 99.94919, matches; 0 per-game mismatches |
| Only game below 100 | wa30, 98.73 |
| bp35 | 530 actions, 11 resets |
| Model | Stated by the authors and the scorecard tag `prolong_strands_opus5_ablation_nopriors`; the scorecard itself does not record a model |

That run used Amazon Bedrock and the Strands agent loop, not the Claude Code CLI. This setup
(PRO-LONG's Claude Code backend + Opus 5 + the hint-free prompt) has no published result.

## One-time setup: the subscription token

Run these yourself in a terminal (the token is a credential):

```
claude setup-token
scripts/set_token.sh        # paste the token when asked; it checks the format and saves it
```

## Use

```
scripts/run_prolong.sh check            # no model call
scripts/run_prolong.sh smoke            # one tiny model call; confirms the plan serves the model
GAMES=bp35 scripts/run_prolong.sh run opus5-bp35-a
```

Overrides: `MODEL` (default `claude-opus-5`), `EFFORT` (`high`), `GAMES` (`bp35`, comma-separated),
`MAX_ACTIONS` (1000 per game), `MODE` (`online`).

Results: `.cache/prolong/arc-agi-3/evaluation_results/<timestamp>_swarm_prolong_agent__<name>/`
with `scorecard.json`, `summary.txt` and one folder per game (`logs.txt`, `logs_agent.txt`).

## Things to know before a long run

- When the plan's usage limit is hit, the harness sleeps until the reset and then continues.
  An ARC scorecard can close after a long idle period, so a run that sleeps may lose its scorecard.
- Each turn is an agent loop of roughly ten model calls. One game at a time is the sensible start.
- The agent's container can reach only `anthropic.com` and `claude.ai`, through an allowlist proxy.

## Run log

### opus5-bp35-a (in progress when this was written, 2026-11-09 18:31 PST)

bp35, Opus 5, high effort, hint-free prompt, up to 1,000 actions, on the subscription.
Scorecard: <https://arcprize.org/scorecards/90586038-8b64-49ca-8845-73537a6b5eb3>

| Level | This run | Tycho + Opus 5 | Strands + Opus 5 | Human baseline |
|---|---|---|---|---|
| 1 | 26 | 17 | 24 | 21 |
| 2 | 48 (one death) | 47 | 52 | 48 |
| 3 | 34 | 35 | 42 | 44 |

Snapshot: 113 actions, 30 agent turns, 65 minutes, on level 4. Level 3 was cleared in one
attempt at the proven minimum of 34 actions. Final numbers are not in yet.

## Notes from setting it up

- The installed `prolong-swarm` command could not import the package on this Mac (the editable
  install's `.pth` file carries the macOS hidden flag, which Python 3.12 skips). The launcher
  starts it with `python -m prolong_agent.agent.swarm` from the harness folder instead.
- The harness log's `total_cost` is overstated on the Claude Code backend: Claude Code reports a
  running total for the resumed session each turn and the harness adds those up. The last turn's
  own `$` figure is the session total (about $23 notional at the snapshot above).
- A subscription token starts with `sk-ant-oat`. The launcher refuses anything else before making
  a call; `scripts/set_token.sh` checks the paste before saving it.
- To rebuild: copy `research/arc-agi-3` from PRO-LONG at the recorded commit into
  `.cache/prolong/arc-agi-3`, create a Python 3.12 environment there and `pip install -e .`,
  build the two Docker images from its `docker/` folder, and replace
  `prolong_agent/agent/prompts.py` with the Strands version.
