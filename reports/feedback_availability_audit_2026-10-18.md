# Retained feedback audit — October 18, 2026

**The clearest failures already had recent visual feedback available.** In both
ft09 and sc25 arms, every action left the full observation unchanged. On each
of the following 23 decisions, the agent repeated the same click with the
earlier before/after images and action already in its prompt: **92 decisions**
across these four episodes.

The next question should be **whether an explicit factual summary helps the
agent use feedback it already receives**. This audit cannot prove that the
model attended to or understood the images, or explain why it repeated actions.

## Method

The audit checks the externally pinned independent evaluation of
[r5 attempt 3](initial_geometry_r5_attempt3_results_2026-10-18.md), its whole-run
evidence digest, reviewed source lock and input hashes. All 288 policy requests
are reconstructed from their initial observation, supplied geometry, current
observation and preceding transitions.

Each decision uses only earlier completed transitions. Its actual prompt shows
the last two transitions as action records and before/after images. The outcome
after the audited decision is stored separately and never treated as information
available before the action. Full action identity includes click coordinates.
All changed pixels are preserved, including possible UI updates. Full
observations also include legal actions, game state and level count. No human
solution, game-rule interpretation or hidden engine state is used.

## Results

Each cell lists **automatic / reviewed** counts, with 24 decisions per episode.
The first decision cannot have prior action feedback.

| Game | Consecutive identical-action repeats | Earlier unchanged-grid outcome of chosen action visible | Same, with earlier pre-observation identical to current observation | Older unchanged outcome exists, but none visible in the recent window |
|---|---:|---:|---:|---:|
| ls20 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| s5i5 | 23 / 23 | 0 / 0 | 0 / 0 | 0 / 0 |
| cd82 | 23 / 23 | 16 / 16 | 8 / 8 | 6 / 6 |
| ft09 | 23 / 23 | 23 / 23 | 23 / 23 | 0 / 0 |
| ka59 | 20 / 23 | 14 / 16 | 7 / 8 | 5 / 6 |
| sc25 | 23 / 23 | 23 / 23 | 23 / 23 | 0 / 0 |
| **Total** | **227** | **154** | **123** | **23** |

The last column concerns a previous outcome for the same full action. It does
not assert an identical earlier observation or that the old effect transfers
to the current state. It counts only decisions with no visible unchanged
example for that action, even if an older example exists.

| Additional observation | Reading |
|---|---|
| 132/288 actions left both the grid and recorded full observation unchanged | Describes observed effects, not hidden-state equality or permanent ineffectiveness |
| 154 decisions repeated an action with an unchanged-grid example visible | Missing history alone cannot explain these repeats |
| 123 also matched an identical earlier pre-observation | Stronger observational match, not a hidden-state certificate |
| 23 had an older unchanged example but none visible | Longer memory might help these cases; usefulness remains untested |
| Both ls20 episodes followed a three-action cycle throughout | Each repeated action fell outside the two-transition window; every action changed pixels, so this is not an exact no-change loop |
| s5i5 repeated one click but every action changed pixels | Pixel novelty alone does not establish useful learning or progress |

Counts are retrospective descriptions, not independent samples or prospective
policy tests. Repetition can be necessary. Neither all repeats nor all visual
changes can be classified as failures or successes from these measurements.
First-level completion remains 0/6 in each arm.

## Revised next comparison

Hold reviewed starting geometry, model, controls, screenshots, output contract
and action budget fixed. Compare the existing recent-history interface with
the **same information plus deterministic summaries of the same last two
transitions**: full action, changed-cell count/region, observation-field changes
and observational equality. Add no older transitions in this first comparison.

This tests explicit presentation separately from extending memory. Supply all
recent outcomes before the choice; do not construct input using the future
chosen action or its outcome. Do not label a control useless, infer object
functions, declare UI-only change or identify the objective. Abstention stays
allowed. Additional reflection calls and hard repetition bans are separate
interventions, not part of this proposed comparison.

Completion stays primary. Repetition, target coverage and token cost are
diagnostics; variety alone is not success. Longer factual memory can be tested
separately, particularly for omitted-history cases. The frozen interface,
evaluator, token limits and exact package review remain preparation tasks.

## Reproduction and privacy

Producer: `scripts/audit_feedback_availability_v1.py`; logic:
`research/feedback_availability_v1.py`. Nine synthetic tests pass: truncation,
coordinate identity, future-evidence exclusion, rewritten request hashes,
full-observation distinctions and short cycles. No sealed r5 source changed.

| Record | SHA256 |
|---|---|
| Pinned independent evaluation | `a20a50032a357bd6042bcdf4c6bd40b05c4f260eef697f9d2cab867c8327e9a4` |
| Original evaluated evidence digest, rechecked | `c82fa21225031c35a53404186675be682b5b989becb3a64543b5f6b1b4c9e496` |
| Detailed private audit | `9cdfb6fb05f9fad39fc0a4f1b7f26bdd18fc018f6902d8f26e2dc89cb8b07255` |

Detailed decisions and six private before/after examples are in the main
workspace's `.cache/github-review/feedback-availability-2026-10-18/audit-r1/`
(`audit.json`, `summary.json`, `index.html`). Only aggregates are published.
Zero new model requests, game actions, provider writes or GPU jobs were used.
All previous attempts remain consumed and preserved.
