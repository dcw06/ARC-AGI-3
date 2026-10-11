# Track 1 (feedback_action_v1): results of the two-session evaluation

**What this is.** The sanitized results of the frozen protocol's two-session evaluation
(`live_evaluation.evaluate_sessions`, frozen protocol §9), run once over both technically complete sessions on
October 11, 2026. Aggregates only; the notebooks and raw outputs stay private and account-only.

**Answer to the research question** ("Does structured hypothesis testing improve action selection?"): **not shown on
these three exposed development games.** There is no solving claim, the action-selection rule is inconclusive, and
the candidate's predictions were never accurate.

## Sessions

| Session | Attempt | Lifecycle | Model requests | Offline game actions | Technical status |
|---|---|---|---|---|---|
| 1 | attempt 1 `fa1-s1-8c598909…`: consumed during installation, no study data; replacement `fa1-s1r-d1bc3d6b…` (amendment A1) | 820.6 s | 145 (ceiling 193) | 144 (ceiling 144) | technically complete; permits session 2 |
| 2 | `fa1-s2-c1264812…` (one attempt, no replacement) | 862.2 s | 145 (ceiling 193) | 144 (ceiling 144) | technically complete |

Both ran on one RTX PRO 6000, bound before study execution. In each, all six episodes reached the 24-action cap, no
F-rule fired, free text stayed within `ascii_only` (gate A), and all 72 carried statements were reconstructed with 0
mismatches. The live independent evaluation verified the reviewed checkout (private lock `23cb7142…`) for both.
Two-session evaluation (private): SHA-256 `3e45a3d95142e967086d70e8487d34cc85bd829338c907cf23eb12b7569d4887`.

## Solving (§9.2): no solving claim

Levels completed, per game, block and arm:

| Game | Block 1 baseline / candidate | Block 2 baseline / candidate |
|---|---|---|
| s5i5 (coordinate-only) | 0 / 0 | 0 / 0 |
| ls20 (directional) | 0 / 0 | 0 / 0 |
| sk48 (mixed) | 0 / 0 | 0 / 0 |

Neither arm completed a level in 24 actions. A solving improvement needed more levels than the baseline in at least
two games, in both blocks.

## Action selection (§9.3, exploratory): inconclusive

| Failure-inclusive rate | s5i5 baseline / candidate | ls20 baseline / candidate | sk48 baseline / candidate |
|---|---|---|---|
| Untested action type chosen | undefined | 0.316 / 0.125 | 0.042 / 0.042 |
| Repeat after no change | undefined (0 opportunities by construction) | undefined | 1.000 / 1.000 |
| Invalid action | 0 / 0 | 0 / 0 | 0 / 0 |

- A behavioural improvement needed a defined rate that differs in at least two games, in the same direction in both
  blocks. Only ls20 differs, and there the candidate chose untested action types **less** often.
- In sk48 both arms repeated the same no-change action 23 times in 24 (exact repeats in the same state), and none of
  those repeats was followed by a visible change or a level.

## Candidate process measures (descriptive, §9.5)

| Measure | s5i5 | ls20 | sk48 |
|---|---|---|---|
| Prediction accuracy | 0.000 | 0.000 | 0.000 |
| Revision after a falsified prediction | 0.478 | 0.000 | 0.000 |
| Citation supply | 1.000 | 1.000 | 1.000 |
| Unsupported citations | 0.000 | 0.100 | 0.000 |
| Invalid procedure block | 0.000 | 0.000 | 0.000 |

The candidate always supplied citations and they were almost always mechanically supported, but none of its
predictions of the next frames was accurate. A better process measure would not by itself show better action
selection (§2.1).

## Exploratory advancement thresholds (§9.4): met

- Invalid actions: candidate 0 of 144, baseline 0 of 144 (threshold: candidate ≤ baseline + 0.05).
- Unsupported citations: 12 of 504 (2.4%), with citation supply 138 of 138 (threshold ≤ 20%, at least 10 citations).

These gate only whether an ablation or a larger study is worth proposing. They are not evidence of reliable
grounding, and with no outcome difference they do not by themselves argue for one.

## Cost per arm (each session; identical in both)

| Arm | Calls | Prompt tokens | Completion tokens | Call seconds (total) |
|---|---|---|---|---|
| Baseline | 72 | 1,818,859 | 1,801 | 114 |
| Candidate | 72 | 1,848,502 | 15,643 | 229 |

## Important limit: the two blocks were identical

Session 2 reproduced session 1 exactly. In every game and arm the actions and the raw model responses are identical.
Each episode starts from environment seed 0 and decodes at temperature 0 with model seed 0 and prefix caching off, so
the run is deterministic, and the block order does not matter.
- The second block is therefore a determinism check, not an independent replicate. The §9.3 conditions "in the same
  direction in both blocks" and "the arm difference exceeding that arm's block-1/block-2 difference" carry no
  information about run-to-run variance here: the block difference is zero by construction.
- The results describe one deterministic trajectory per game and arm: 72 decisions per arm, on three exposed
  development games. They are not evidence about other games, other seeds, or competition performance (§1).
- The candidate is a bundled treatment (procedure, hypothesis block, carried statements, a 5× completion allowance);
  no component can be isolated (§2.1).

A future study of this question needs independent replicates, for example different environment seeds or games,
rather than a repeated deterministic block.
