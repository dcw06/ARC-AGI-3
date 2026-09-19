# Closed-loop v1 R1 development results

The authorized closed-loop v1 R1 run completed on Kaggle and passed independent
replay of the archived evidence. All 15 matched game pairs completed their 20-action
episodes: 600 policy calls/actions plus the startup canary. Startup-inclusive
runtime was 1659.281 seconds (27 minutes 39 seconds),
within the 3,300-second internal deadline and 3,600-second authorized attempt.
Independent GPU/process cleanup, dependency/source removal, finalization hashes,
request/action bindings, initial-state equality, progress counters, and evidence
completeness passed. All 664 frozen source bindings still match.

The configuration is E1S-R-derived `arc_action_v12`, comparing the frozen original
system prompt (`baseline`) with `no_concrete_examples`, using the same model,
15 development games, seeds, and per-episode action cap. Each action used a fresh
observation; paired trajectories were allowed to diverge. No fallback, later reset,
inference retry, diagnostic rerun, full pilot, or production run was performed.

| Measure | Original prompt | No concrete examples |
|---|---:|---:|
| Episodes / acknowledged actions | 15 / 300 | 15 / 300 |
| Completed-level increase / wins | 0 / 0 | 0 / 0 |
| Adjacent repeated actions | 271/285 (95.1%) | 178/285 (62.5%) |
| Canonical observation changes | 173/300 | 173/300 |
| Frame changes | 169/300 | 168/300 |
| Repeats after unchanged observation | 113 | 81 |
| Clicks at example coordinate (12,34) | 210/220 clicks | 0/218 clicks |

All 15 pairs tied on completed-level increase. All episodes ended at the action
cap, with no WIN or GAME_OVER. Repeats compare the entire action, including click
coordinates, against the immediately preceding action within an episode; there
are 19 adjacent opportunities per episode. Observation/frame changes are not
evidence of level progress. Repetition fell by 32.63
percentage points, but the experiment did not demonstrate improved solving.

This is a 20-action early-progress experiment on 15 known games with one seed.
Zero progress does not establish that the prompt change can never help. Do not
promote the no-example prompt as a demonstrated solving improvement. The next
useful work is an offline inspection of retained trajectories and observations
to distinguish unproductive action selection from visual/state interpretation
problems, before proposing another separately scoped experiment. No further
compute is authorized by these results.

## Retained evidence and independent replay

- Kaggle: https://www.kaggle.com/code/daichongwei06/arc3-phase4-action-closed-loop-v1-r1 (version 1).
- Provider COMPLETE observed at 2026-09-19T12:44:05.095706+00:00; this is an observation time, not the exact finish time.
- Archive: `evidence/phase4-closed-loop-v1-r1-completed-v1.zip` (4,080,172 bytes; 1007 provider files plus log/manifest/provider observations).
- Archive SHA-256: `994dc62307777a1adf301986aa2548bb9dad84ab438963d20392736abd493f9d`.
- Independent evaluation: `reports/phase4_closed_loop_v1_evaluation.json`.
- Evidence/source/accounting receipt: `reports/phase4_closed_loop_v1_evidence_receipt.json`.
- Reproducer: `scripts/record_phase4_closed_loop_v1_result.py`, which verifies the source lock and downloaded inventory, checks the archive byte-for-byte, and replays the extracted archive using the frozen evaluator. No GPU/model execution occurs.

The initial sequential CLI download timed out at its 90-second helper limit.
A bounded parallel, read-only download fetched the complete 1,007-file manifest;
this was an artifact-transfer retry, not another compute attempt. The original
GPU-disabled review notebook and frozen evaluator were preserved.

## Attempt accounting and open gates

One attempt was consumed. Account GPU time used changed from
1450.542 to 3119.043 seconds:
an observed delta of **1668.501 seconds**.
Provider account reserved time is zero at the terminal observation.
This is not exact per-job billing. The SDK's raw `3119.43.0s` duration serialization
is malformed, and its parsed total allowance differs from the raw response;
both representations are archived. Exact billed seconds remain null. No unused
part of the local one-hour cap is released as reusable spending authority.

Phase 4 remains open: exact billing reconciliation, production one-scorecard /
110-distinct-game certification, and production `C_admit` are unresolved. This
experiment establishes no production admission capacity or new spending authority.
