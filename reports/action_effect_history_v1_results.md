# Action-effect history v1: live results

Attempt `aeh1-4c75150a156640fcad105a770ce81119`, run from review r3 (lock
`0f870a1a…e386`), on Kaggle version 1 with a single RTX Pro 6000. The run
evidence manifest has SHA-256 `c57fd8c7…b9d3`. The full independent evaluation
is in `reports/action_effect_history_v1_live_evaluation.json`. The raw output is
archived in `evidence/action-effect-history-v1-complete.zip`, locked by
`reports/action_effect_history_v1_archive.json`.

## Frozen results

| Result | Value |
|---|---|
| Technically complete | **yes**: lifecycle, cleanup, canary, evidence integrity and semantic replay all pass |
| Schedule | all 6 pairs and 12 episodes complete; 144 policy calls, 144 dispatches |
| Behaviour result | **inconclusive** |
| Solving result | **no demonstrated solving improvement** (0 levels in every episode) |
| Reliability | identical by arm: 0 invalid outputs, 0 dispatch failures, 0 interruptions, 0 closure failures |
| Wall time | model startup 403 s; supervisor 735 s; first cell 737 s, against a 3,300 s internal limit |
| Account GPU time | 747.6 s used (Kaggle quota counter, 13,547.4 s before to 14,295.0 s after), of 3,600 s authorized; exact billed seconds are not reported by the provider |

| Pair | Class | Baseline repeats / opportunities | History repeats / opportunities |
|---|---|---|---|
| b1-ar25 | not reduced | 3 / 11 | 3 / 11 |
| b1-s5i5 | ineligible (no baseline repeats) | 0 / 0 | 0 / 0 |
| b1-wa30 | ineligible (no baseline repeats) | 0 / 0 | 0 / 1 |
| b2-wa30 | reduced | 1 / 1 | 0 / 1 |
| b2-s5i5 | ineligible (no baseline repeats) | 0 / 0 | 0 / 0 |
| b2-ar25 | not reduced | 3 / 11 | 3 / 11 |

Pooled immediate-repeat rate: baseline 7/23 (0.304), history 6/24 (0.250).
Only three pairs were eligible, and the one *reduced* pair rests on a single
opportunity. The frozen rule therefore gives *inconclusive*. That is the
result; the observations below are exploratory and do not replace it.

## Exploratory observations (post hoc, not frozen outcomes)

1. **s5i5 counter confound.** Every s5i5 action changes one or two cells on the
   bottom row (row 63, starting at column 63 and moving left one step at a
   time). The same cells change whether the model clicks (11,10), (3,10) or
   (13,10). This looks like a per-action step counter, not a response to the
   click. The effect record correctly reports a changed frame, so the
   no-change repeat metric can never apply. The history field shows the model
   "changed 1 cell" after each click. The history arm then clicked (11,10) all
   12 times, while the baseline tried four positions.
2. **ar25: the history arm changed action type but still did nothing
   effective.** Every ACTION6 click changed 0 cells in both arms. After
   no-change steps, the history arm alternated ACTION6 with ACTION7, which also
   changed 0 cells. Same-type repeats after no change fell from 8 to 0 per
   episode, while exact repeats stayed at 3 of 11. Neither arm tried
   ACTION1–4, which the offline diagnosis showed change 109 cells.
3. **wa30: the history arm swept the action set.** It cycled ACTION1→5
   deterministically, using 5 distinct actions against the baseline's 3.
   ACTION5 changed only a single corner cell (row 63), which again looks like a
   counter.
4. **The model service was not deterministic at temperature 0.** The two wa30
   baseline episodes sent byte-identical first requests (request SHA-256
   `53d5fc65…2181`) and received different responses. ar25 baseline actions
   also differed between blocks. Both history arms reproduced exactly between
   blocks. The second wa30 history episode's mean latency was 0.23 s against
   about 1.4 s elsewhere, which fits prefix-cache reuse. Block 2 is therefore
   not a strict replication of block 1, and the baseline has non-zero
   run-to-run variance that this design cannot estimate.

## Implications for the next step (proposals only, nothing authorized)

- Change detection should separate a persistent HUD or counter region from the
  playfield before an effect counts as "the action did something". For
  example, cells that change identically under every action of an episode
  could be masked. That is a records and fixtures change, testable offline
  against s5i5 and wa30 frames.
- The ar25 behaviour suggests history alone does not steer the model towards
  untried action *types*. A bounded follow-up could test an explicit
  "untried actions" summary, but only as a separately frozen intervention.
- Before any further live comparison, the repeat measurements should
  establish the model's run-to-run variance, for example by running
  byte-identical requests with prefix caching disabled. Otherwise
  single-opportunity differences cannot be interpreted.
