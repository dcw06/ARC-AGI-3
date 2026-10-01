# Stagnation supervision v1: detector benchmark and frozen trigger (Track 3, milestones A–C)

Synthetic, CPU only. No model ran, nothing ran on a GPU, and no real-game or holdout data was used. Code:
`research/stagnation_supervision_v1/`. Tests: `tests/test_stagnation_supervision_v1*.py`.
Transition evidence comes from `research/transition_evidence_v1`, which this work reads and does not modify.

**Question.** Does an intervention triggered by evidence of stagnation help more than ordinary continuation, or
more than reflection at fixed intervals under the same budget? This report covers only the first step: a
mechanical detector, its frozen trigger, and its held-out precision and recall on labelled synthetic
trajectories. It does not test whether intervening helps. "No progress detected" never means "progress is
impossible": a trigger is a prompt to reconsider, not a verdict.

## 1. Benchmark (`fixtures.py`)

- **Families.** 19 families of scripted trajectories in a seeded grid world, emitted as raw transitions in the
  `transition_evidence_v1` format. Every record passes `transition.validate`.
- **Labels.** Labels come from the construction, which knows the hidden state, and the detector never sees them.
  One rule applies everywhere: a step is *stagnant* if it repeats a (hidden state, action) whose outcome the
  agent has already observed, and the construction guarantees the repeat moves nothing towards progress. A first
  probe, a move into a new state, a repeat that advances a hidden quantity, required backtracking, and replaying
  a route after a reset are all *productive*.
- **Positive families (10, each contains stagnant steps):**
  - `repeated_click_no_effect` (the cd82 pattern)
  - `rotating_clicks_no_effect`
  - `toggle_two_cycle`
  - `move_square_cycle`
  - `counter_only_repeat` (the s5i5 pattern: only a step counter changes)
  - `loop_under_step_counter`
  - `walk_into_wall`
  - `no_effect_with_dispatch_gaps` (failed and unknown dispatches interleaved)
  - `loop_then_escape`
  - `loop_escape_into_loop`
- **Hard negatives (9, productive throughout):**

  | Family | What it tests |
  |---|---|
  | `move_to_destination` | Repeated movement needed to reach a destination |
  | `incremental_click_effect` | Repeated clicks with incremental effects |
  | `backtracking_required` | Backtracking the layout requires |
  | `delayed_effect` | An effect that appears only after several repeats |
  | `counter_with_static_playfield` | A counter changes while the playfield stays the same |
  | `productive_exploration_no_completion` | Exploration with no level completion |
  | `varied_click_painting` | Many small effects at different positions |
  | `dispatch_retry_productive` | Retrying after a failed dispatch |
  | `reset_then_replay` | Replaying a route after a reset |

- **Ambiguous by design.** Before the payoff, `delayed_effect` looks like `repeated_click_no_effect`, and
  `counter_with_static_playfield` and `incremental_click_effect` look like `counter_only_repeat`. On these
  pairs, any threshold trades recall against false interventions.
- **Partitions.**

  | Partition | Seed | Trajectories | Positive / hard negative |
  |---|---|---|---|
  | development | `ws3-stagnation-fixtures-development` | 76 (4 per family) | 40 / 36 |
  | evaluation | `ws3-stagnation-fixtures-evaluation` | 76 (4 per family) | 40 / 36 |

  A whole trajectory stays in one partition. Half the trajectories carry an agent-side prediction stream
  (provisional format: `{action_index, expects_change}`).
- **Unit of analysis.** The trajectory. Steps from one trajectory are never treated as independent samples.

## 2. Detector (`detector.py`)

The detector is mechanical and causal: a test checks that its output at step t is unchanged when later records
are removed. Its inputs are:
- pre-action frame fingerprints;
- the exact dispatched action;
- the measured visual effect;
- environment-reported progress and segment boundaries;
- optionally, prediction outcomes.

It has six candidate signals:

| Signal | Fires when |
|---|---|
| `repeat_no_effect` | The same (pre-frame, action) is acknowledged k times with no lasting observed change |
| `state_action_recurrence` | The same (pre-frame, action) is acknowledged k times, whatever its effect |
| `tiny_effect_repeat` | The identical action is repeated k times in a row, each time changing at most 4 cells |
| `novelty_stall` | Among the last w observed transitions, at most n reached a frame new to the segment |
| `prediction_failures` | k consecutive scored predictions failed |
| `no_progress_horizon` | k observed transitions pass without a confirmed progress signal |

Evidence rules (all tested):
- A failed dispatch is never evidence of no effect. It neither extends nor breaks a pattern.
- An unknown outcome or a missing observation adds nothing and breaks streaks.
- An `indeterminate` effect is never counted as no change.
- A reset or level change starts a new segment and clears all statistics.
- A visible change is never treated as progress.
- Decisions do not change when colours are consistently relabelled.

Every firing cites its evidence as action indices.

## 3. Frozen trigger (`thresholds.py`, `trigger_spec.json`)

The selection objective was fixed before selection ran:
- **Constraint:** at most 10% of development trajectories receive a trigger at a productive step.
- **Then, in order:** maximise recall (positive trajectories with a trigger at a stagnant step); fewest
  false-intervention trajectories; highest precision; lowest latency; fewest signals; largest thresholds.

Selection used the development partition only. The tests check that it refuses evaluation fixtures.
- It searched 9,600 candidates.
- The cooldown (6 actions) and the "tiny effect" size (4 cells) were fixed beforehand and were not tuned.
- Three reference detectors were declared with the grid, before any evaluation run: `repeat_no_effect_only_k3`
  (a naive no-effect streak detector), `no_progress_horizon_only_10`, and `periodic_every_6` (a fixed schedule).
- The spec was committed (0aa9958) before the evaluation partition was first scored.

**Selected:** `state_action_recurrence = 2` and `tiny_effect_repeat = 10`. All other signals are off.

In words: trigger on the first exact repeat of a (frame, action) pair within a segment, or on 10 identical
actions in a row with tiny effects.

**Development (for transparency, not a result):**
- recall 36/40;
- precision 60/65;
- false-intervention trajectories 4/76, all `delayed_effect`;
- mean latency 0.92 actions.

**One correction before freezing.** A fixture bug surfaced in the development errors: `rotating_clicks_no_effect`
could sample the same cell twice, so a "first round" step was actually a repeat. It was fixed, and selection was
rerun on development before the spec was frozen. No evaluation data was looked at.

## 4. Held-out evaluation (`evaluate.py`, `evaluation_results.json`)

| Detector | Recall (trajectories) | Precision (triggers) | Trajectories with a false intervention | Hard negatives with a false intervention | Mean latency (actions) |
|---|---|---|---|---|---|
| **selected (frozen)** | **36/40 (0.90)** | **61/66 (0.92)** | **4/76** | **4/36** | **0.92** |
| repeat_no_effect_only_k3 | 20/40 (0.50) | 26/30 (0.87) | 4/76 | 4/36 | 2.6 |
| no_progress_horizon_only_10 | 24/40 (0.60) | 33/55 (0.60) | 15/76 | 11/36 | 5.96 |
| periodic_every_6 | 39/40 (0.975) | 58/112 (0.52) | 40/76 | 32/36 | 2.67 |

Wilson 95% intervals for the selected detector (trajectory level):
- recall: 0.77–0.96;
- false-intervention rate: 0.02–0.13.

These intervals understate the uncertainty. Trajectories within a family are near-replicates, so the effective
sample is closer to 19 families than to 76 trajectories.

**All retained errors of the frozen detector** (`evaluation_results.json`, `errors`):
- **False interventions, 5 triggers in 4 trajectories.**
  - Where: `eva-delayed_effect-0..3` at action 1, and `eva-delayed_effect-3` again at action 7 (the release step).
  - Why: the first exact repeat of a no-change action is indistinguishable from a no-effect loop until the
    delayed effect appears.
  - This is the designed cost of `state_action_recurrence = 2`. If delayed effects are common in real games,
    k = 2 is too aggressive.
- **Missed positives, 4 trajectories.** `eva-counter_only_repeat-2`, `-3` and `eva-loop_under_step_counter-1`,
  `-3`.
  - Why: a per-action step counter makes every frame unique, so exact fingerprints never repeat.
- **The counter case is effectively a blind spot.** The four counter trajectories that were "detected" were
  caught only incidentally, at latency 8:
  - `counter_only_repeat-0` and `-1` by a 10-step streak;
  - `loop_under_step_counter-0` and `-2` because the synthetic counter wrapped around.
- **All other trajectories.** The other 32 positive trajectories were detected at latency 0–1. No hard negative
  other than `delayed_effect` received a trigger. That includes:
  - movement to a destination;
  - incremental clicks;
  - backtracking;
  - a counter with a static playfield;
  - long exploration without completion;
  - failed-dispatch retries;
  - replay after a reset.

**Reading the references.**
- **Periodic schedule.** It finds almost every loop eventually (39/40), but about half its triggers land on
  productive steps (54/112), and 32/36 hard negatives are interrupted. This is the false-alarm cost that
  triggered reflection is meant to avoid.
- **Pure no-progress horizon.** It is both late and noisy.
- **Naive no-effect streak.** It misses every loop in which something visibly changes: toggles, movement cycles
  and counters.

## 5. Limits (what this benchmark cannot show)

- **Synthetic data.** The families, their proportions and their lengths were chosen by us. Precision depends on
  how often real games contain delayed effects or step counters, and that rate is unknown. The real s5i5 counter
  (`reports/action_effect_history_v1_results.md`) is exactly the blind spot measured here.
- **Labels and families share one author.** They are not independent of the detector designer. The evaluation
  partition guards against threshold overfitting, not against family-design bias.
- **Exact fingerprints.** Exact fingerprints are defeated by any action-independent display change. A fix needs a
  HUD/counter separation field, which is a dependency (see the protocol draft). It should not be guessed from
  pixels inside this detector.
- **No claim about outcomes.** The benchmark measures whether triggers land on stagnant steps. It says nothing
  about whether an intervention helps.

## 6. Bounded intervention and CPU rehearsals (milestone C)

See `reports/stagnation_supervision_v1_protocol_draft.md` §2–3 for the interface and policy. The rehearsal tests
use scripted supervisor outputs only. They cover:
- repeated triggers with cooldown and a cap on interventions;
- token-budget exhaustion;
- invalid and over-long outputs, outputs citing unshown evidence, outputs mentioning environment source or game
  identifiers, solution claims, over-long test plans, and test actions that break the `arc_action_v12`
  argument rules;
- call exceptions and a scripted supervisor that runs out of outputs (each charged and retained);
- triggers from failed dispatches alone (none happen);
- deferral when the current state was not observed;
- resets clearing the detector but not the episode limits;
- arms differing only in timing;
- agreement between the evaluated trigger stream and the rehearsed calls on every development trajectory.

## 7. Tests

| Module | Tests | Result |
|---|---|---|
| `tests.test_stagnation_supervision_v1` | 18 | pass |
| `tests.test_stagnation_supervision_v1_intervention` | 25 | pass |
| `tests.test_stagnation_supervision_v1_evaluation` | 3 | pass |
| `tests.test_transition_evidence_v1` (the contract, unchanged) | 16 | pass |

Regenerate the outputs with:
- `python -m research.stagnation_supervision_v1.thresholds` (development only);
- `python -m research.stagnation_supervision_v1.evaluate`.

The tests check that both reproduce exactly.
