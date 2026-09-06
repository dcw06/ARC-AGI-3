# ARC Prize 2026 — Plan 8 implementation

This repository implements the transaction-safe Phase 0 foundation described
by `docs/ARC-AGI-3_Project_Plan_8.md`.

This is a starter kit for the [ARC Prize 2026 — ARC-AGI-3](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)
competition. Production uses a multi-file agent package and a dedicated
lifecycle adapter; `agent/my_agent.py` is compatibility-only.

No Docker. No `submission.json` to hand-write. No copy-pasting between your
editor and a notebook.

---

## What you need before you start

- **uv** (`make setup` uses it to download a project-local Python 3.12)
- **git** (to clone the official agent framework)
- **An ARC-AGI API key** from [the ARC Prize platform](https://arcprize.org/platform)
  to unlock all public development games
- **A Kaggle account** with the competition rules accepted
  ([accept here](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules))

That's it. No GPU required for the starter agent.

---

## Quick start

```bash
# 1.  From this project directory, create your local ARC configuration.
cp .env.example .env
# Edit .env and add your ARC_API_KEY.

# 2.  Drop your Kaggle API token (kaggle.com → Settings → Create New Token)
#     into the project-local .kaggle/ folder (NOT your home directory)
mkdir -p .kaggle && echo "KGAT_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" > .kaggle/access_token
chmod 600 .kaggle/access_token

# 3.  One-time setup: project-local Python 3.12, venv, dependencies, framework
make setup

# 4. Validate the transaction, configuration, and packaging gates.
make validate-phase0

# 5. Run the Plan 8 adapter locally.
make play-competition-like GAME=ls20 STEPS=20

# 6.  Push it to Kaggle as a submission notebook
make submit

# 7.  Watch the run
make status

# 8.  When status shows "complete", open the notebook on kaggle.com,
#     find your kernel, click "Submit to Competition" in the top
#     right, and pick `submission.parquet` from the Output File
#     dropdown. Treat it as the current one-per-day scored allowance and
#     revalidate that allowance in your account before use.
```

That's the entire loop. Steps 4–7 are what you'll repeat as you iterate;
step 8 is the deliberate moment when you spend a daily submission.

---

## Production architecture

The production entry point is `agent/production_main.py`. Immutable actions,
journaling, lifecycle dispatch, bounded state, scheduling, and watchdog logic
are separate modules under `agent/`. `agent/my_agent.py` only supports legacy
upstream smoke tests and is not the Kaggle execution path.

```python
class MyAgent(Agent):
    def is_done(self, frames, latest_frame) -> bool:
        """Return True when your agent wants to stop playing."""
        ...

    def choose_action(self, frames, latest_frame) -> GameAction:
        """Look at the game state and return the next action."""
        ...
```

The starter version picks random actions — a baseline that proves your whole
pipeline works end-to-end. Replace the body of `choose_action` with your
strategy. Everything else (Kaggle plumbing, submission file format, game
orchestration) is handled for you.

---

## What happens when you run `make submit`

The competition is a *code* competition: you submit a notebook, Kaggle runs it
twice.

```diagram
   make submit
       │
       ▼
   ┌─────────────────────────────────────┐
   │  Kaggle Phase A: Save & Run All     │
   │  ─ Runs your notebook in their      │
   │    real environment                 │
   │  ─ Validates that your code         │
   │    executes without errors          │
   │  ─ make status shows "complete"     │
   └─────────────────┬───────────────────┘
                     │
                     │  You click "Submit to Competition"
                     │  on the kernel page
                     ▼
   ┌─────────────────────────────────────┐
   │  Kaggle Phase B: Competition Rerun  │
   │  ─ Your agent actually plays the    │
   │    hidden game set                  │
   │  ─ Your leaderboard score appears   │
   └─────────────────────────────────────┘
```

`make submit` builds and uploads the notebook (Phase A). After
`make status` reports `complete`, open the kernel on kaggle.com and click
**"Submit to Competition"** to enter Phase B and get a leaderboard score.

> **The current observed allowance is one scored submission per day**, so it pays to be
> confident before you submit: get `make play-local` passing, then submit.

> **Heads up:** Before your first `make submit`, open
> [`notebooks/kernel-metadata.json`](notebooks/kernel-metadata.json) and
> replace `REPLACE_WITH_YOUR_USERNAME` with your Kaggle handle. The Makefile
> will refuse to push until you do.

### Choosing an accelerator

The notebook is generated with the competition **RTX 6000** profile by default.
To change it, open
[`scripts/build_notebook.py`](scripts/build_notebook.py) and edit **one
line** near the top:

```python
ACCELERATOR = "rtx6000"  # one of: cpu, t4, p100, rtx6000
```

Then re-run `make submit`. That's it — both the notebook metadata and
[`notebooks/kernel-metadata.json`](notebooks/kernel-metadata.json) get
updated automatically.

| Value | Hardware | When to use |
|---|---|---|
| `"cpu"` | No GPU | Deterministic fallback or other non-ML agent |
| `"t4"` | Nvidia T4 ×2 | Small models, fast iteration |
| `"p100"` | Nvidia P100 | Single big-memory GPU |
| `"rtx6000"` | Nvidia RTX 6000 (`g4-standard-48`) | **Default.** Target competition profile |

RTX 6000 is reserved for ARC-AGI-3 notebooks only — don't use it for early
iteration. All accelerated Kaggle sessions have internet disabled, which is
already the default in this kit.

---

## All the commands

| Command | What it does |
|---|---|
| `make setup` | One-time install: Python venv, `arc-agi`, `kaggle` CLI, clones the framework |
| `make play-local` | Runs your agent against every game in the dataset, locally |
| `make play-local GAME=ls20` | Same, but only one game (faster while debugging) |
| `make verify-local` | 30-second smoke test on two games |
| `make play-competition-like GAME=ls20` | Run through the Plan 8 adapter |
| `make test` | Run transaction, adapter, loop, and scheduler tests |
| `make validate-phase0` | Validate locally provable Phase 0 gates |
| `make list-games` | Print every game id available |
| `make pull-sample` | Download the official sample agent for reference |
| `make notebook` | Build the Kaggle notebook from your agent (no push) |
| `make submit` | Build the notebook **and** push it to Kaggle |
| `make status` | Check the status of your most recent Kaggle run |
| `make clean` | Remove the venv, downloads, and generated notebook |

---

## Why this setup, instead of editing in the Kaggle notebook?

Three reasons:

1. **Iteration speed.** Editing in your normal IDE, then `make play-local`,
   gives you a real-game-engine feedback loop in seconds. The Kaggle editor's
   loop is *minutes* per change.
2. **No environment surprises.** The local `arc-agi` PyPI package hosts the
   same game engine the Kaggle gateway runs. If it works locally, it works on
   Kaggle.
3. **Your code stays in git.** Notebooks are awful for diffs and code review.
   Here your real work lives in [`agent/my_agent.py`](agent/my_agent.py); the
   notebook is just an auto-generated deployment artifact.

---

## Project layout

```
.
├── agent/
│   └── my_agent.py             ★ The file you edit
├── scripts/
│   ├── play_local.py           Runs your agent against real games
│   ├── build_notebook.py       Packages your agent into a Kaggle notebook
│   └── slim_framework.py       Trims framework deps so install is light
├── notebooks/
│   ├── kernel-metadata.json    Edit once: your Kaggle username
│   └── submission.ipynb        Auto-generated, never edit by hand
├── vendor/                     Cloned framework (gitignored)
├── .venv/                      Python 3.12 venv (gitignored)
├── .kaggle/                    Your project-local Kaggle token (gitignored)
└── Makefile
```

---

## Troubleshooting

**`make setup` cannot download Python or packages**
Check that `uv` is installed and that the machine can reach Python's package
indexes and GitHub. All downloaded runtimes and caches stay inside this project.

**`make submit` says "edit kernel-metadata.json"**
You haven't replaced `REPLACE_WITH_YOUR_USERNAME` in
[`notebooks/kernel-metadata.json`](notebooks/kernel-metadata.json) yet.

**`make submit` says `401 Unauthorized`**
Your Kaggle token is missing or invalid. Generate a fresh one from your
[Kaggle Settings page](https://www.kaggle.com/settings) and overwrite
`.kaggle/access_token`.

**`make play-local` says "Could not create environment"**
Your machine couldn't reach the ARC-AGI API to download the game source on
first run. Check your internet, then try again — once downloaded, games are
cached in `environment_files/` and you're fully offline.

**My local score is 0.0**
That is expected for the Phase 0 deterministic fallback. Model and policy
screening begins in M0/Phase 1.

---

## Where to go next

- Read the [ARC-AGI-3 docs](https://docs.arcprize.org/) to understand the
  benchmark.
- `make pull-sample` to study Kaggle's reference agent (the same one
  currently sitting on the leaderboard).
- The competition's [discussion forum](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion)
  for community Q&A.

Good luck. Looking forward to seeing what you build.
