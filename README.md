# ARC Prize 2026 — Plan 8 implementation

This repository implements the transaction-safe ARC-AGI-3 agent and experiment
program described by `docs/ARC-AGI-3_Project_Plan_8.md`.

Phase 0 and the Phase 0F/M0 evidence-and-model-viability milestone are complete.
Plan 8 is active. Phase 1 implementation, experiment parameters, target-RTX
profiling, and the September 10 control availability/license decisions are
complete. Version 5 is valid descriptive four-cell evidence, and E1S-R is now
the runnable `Provisional primary` with E0 fallback. The updated shared-resource
audit still requires the frozen counterbalanced whole-run follow-up, while
ineligible published reproductions remain explicitly unavailable. The E0 public
score of 0.08 is a pipeline-validation baseline, not a competitiveness claim.

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
#     dropdown. Treat it as the current signed-in two-per-day allowance and
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

The production agent still picks deterministic legal fallback actions — a
baseline that proves the pipeline works end-to-end. Model-driven policies are
added through the production policy interface in `agent/competition_loop.py`;
the compatibility `choose_action` method above is not the production extension
point. Kaggle plumbing, submission format, and orchestration remain separate.

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

> **The current signed-in allowance is two scored submissions per day**, so it pays to be
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
| `make validate-phase0f` | Validate the evidence, representation, and M0 foundation |
| `make validate-m0-exit` | Validate all target profiles and the provisional model selection |
| `make validate-phase1` | Validate Phase 1 implementation/parameter closure and report external exit blocks |
| `make e1-q3vl30-notebook` | Build the unscored four-cell mixed E1 RTX profile |
| `make e1-q3vl30-push` | Upload that private profile on RTX PRO 6000; does not submit a score |
| `make e1-q3vl30-status` | Check the private E1 profiling run |
| `make e1-q3vl30-output` | Download its completed profile evidence into the ignored run directory |
| `make e1-four-cell-notebook` | Build the counterbalanced whole-run E1 notebook |
| `make e1-four-cell-push` | Run the private two-block whole-run experiment on RTX PRO 6000; does not submit a score |
| `make e1-four-cell-status` | Check the private whole-run experiment |
| `make e1-four-cell-output` | Download its result and per-treatment server logs |
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
2. **Early environment-parity checks.** The pinned local toolkit exercises the
   same documented contract and production transport, while the mounted runtime
   audit still fails closed if Kaggle differs.
3. **Your code stays in git.** Notebooks are awful for diffs and code review.
   The production implementation lives under [`agent/`](agent/); the notebook
   is an auto-generated deployment artifact.

---

## Project layout

```
.
├── agent/
│   ├── production_main.py      Kaggle production entry point
│   ├── competition_loop.py     Bounded game and all-game orchestration
│   ├── e1_policy.py            Stateless E1S/E1C policy and local model transport
│   ├── safe_operations.py      Spawn-isolated bounded E1C operations
│   ├── evidence.py             T0-T3 evidence retention
│   └── representation.py       Raw R and engineered F bundles
├── config/                     Versioned contracts and experiment registries
├── evaluation/                 Scoring, M0 profiles, and Phase 1 selection estimands
├── scripts/
│   ├── play_competition_like.py Runs the production lifecycle locally
│   ├── build_notebook.py       Packages your agent into a Kaggle notebook
│   └── validate_m0_exit.py     Enforces the Phase 0F/M0 exit gate
├── notebooks/
│   ├── kernel-metadata.json    Production Kaggle metadata
│   └── m0-*/                   Frozen target-RTX profiling notebooks
├── reports/                    Phase status and immutable profile records
├── tests/                      Phase 0, Phase 0F/M0, and Phase 1 tests
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
That is expected while production still uses the deterministic fallback. M0
established model viability; model-policy behavior is evaluated in Phase 1.

---

## Where to go next

- Read the [ARC-AGI-3 docs](https://docs.arcprize.org/) to understand the
  benchmark.
- `make pull-sample` to study Kaggle's reference agent (the same one
  currently sitting on the leaderboard).
- The competition's [discussion forum](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion)
  for community Q&A.

Good luck. Looking forward to seeing what you build.
