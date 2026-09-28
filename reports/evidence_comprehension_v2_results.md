# Evidence comprehension v2: live results

Attempt `ecv2-65759c16cf1648a19f8bf0128a070826`, from review package r1 (lock `de9642c6…82a3`), on Kaggle
(version 1, one RTX Pro 6000). The protocol is `reports/evidence_comprehension_v2_protocol.md` (revision 2).
- **Independent evaluation:** `reports/evidence_comprehension_v2_live_evaluation.json`.
- **Archive:** `evidence/evidence-comprehension-v2-live.tar.xz` (43 files, SHA-256 `58517d20…188c`), locked by
  `reports/evidence_comprehension_v2_live_archive.json`. Replaying it reproduces the evaluation exactly.
- **Download manifest:** `reports/evidence_comprehension_v2_download.json` (34 provider files).

## Technical result

| Check | Result |
|---|---|
| Technically complete (independent evaluator, live mode) | **yes**: lifecycle passed, run evidence verified, no call errors |
| Calls | 8,004 of 8,004 answered; 0 timed out, 0 invalid, 0 truncated |
| Prefix caching | Off. The server processed 4,967,063 prompt tokens (the audited 4,967,024 plus the canary) with 0 prefix-cache queries and 0 hits. |
| Two-pass agreement (withheld) | Every answer identical between the passes, in every family and condition |
| Time | Installation 114 s; model startup 402 s; questions 837 s (mean 0.094 s per call, slowest 0.72 s). First cell 1,358 s, against the 3,000 s admission cutoff and the 1,823 s planning estimate. |
| GPU accounting | Exact billed time: **unknown**. The account counter rose from 926.26 s (prelaunch) to 2,293.652 s (`reports/evidence_comprehension_v2_postrun_provider.json`), a rise of 1,367.39 s. That is an account-counter observation, not a billed amount. The attempt is consumed; unused authorization is not reusable. |

## Decision (frozen rules, withheld partition, both-correct)

| Track | Verdict | Promoted? |
|---|---|---|
| Control availability | **`improved_below_criterion`** | No |
| History reading | **`improved_below_criterion`** | No |

"Complete" means every withheld question was answered in both passes. It says nothing about whether
comprehension passed. The labels describe this diagnostic's criterion under these prompts and
representations, not general comprehension.

### Control track

| Family | Role | Baseline | Candidate (intersect instruction) | Paired: improved / regressed; difference [95% CI] |
|---|---|---|---|---|
| legal_actions | component | 0.958 (criterion_met) | 0.992 (criterion_met) | +4 / −0; +0.033 [0.008, 0.067] |
| action6_legal | component | 0.975 (criterion_met) | 0.992 (criterion_met) | +2 / −0; +0.017 [0.000, 0.042] |
| coordinate_rule | component | 1.000 (not_diagnostic, as designed) | 1.000 | — |
| **legal_coordinate_actions** | **target** | **0.517 (below_accuracy_floor)** | **0.883 (inconclusive)** | **+44 / −0; +0.367 [0.283, 0.458]** |

- **The baseline reproduces v1's failure on fresh cases.** All 58 errors answered `[6]` when ACTION6 was not
  legal.
- **The components are fine.** The model knows which ids are legal (0.958), whether 6 is legal (0.975), and
  that only ACTION6 takes coordinates (1.000). The failure is in intersecting them.
- **The instruction fixed 44 of the 58 errors, with no regressions.** Every one of the 14 remaining errors is
  the same case: ACTION6 not legal, but present in the history, even though the instruction names that case.
  This association is **consistent with interference from the history**. It is not established as the cause:
  this experiment did not vary the history independently, so establishing it would need a matched comparison
  that removes or alters ACTION6 in the history while holding everything else fixed.
- **Why it is not promoted.** The target's 0.883 falls short of the 0.90 criterion (its shortcut-disagreement
  accuracy is 1.00), so the verdict is `improved_below_criterion`.

### History track

| Family | Role | Baseline | Candidate (normalized records) | Paired: improved / regressed; difference [95% CI] |
|---|---|---|---|---|
| step_action_match | component | 0.925 (criterion_met) | 0.950 (criterion_met) | +9 / −4; +0.025 [−0.010, 0.060] |
| dispatch_status | component | 0.983 (criterion_met) | 0.975 (criterion_met) | +1 / −2; −0.008 [−0.042, 0.017] |
| any_change | component | 0.775 (inconclusive; 0.21 where the shortcut is wrong) | 0.942 (criterion_met; 1.00) | +27 / −7; +0.167 [0.083, 0.250] |
| final_equals_pre | component | 0.817 (inconclusive) | 0.925 (criterion_met) | +15 / −2; +0.108 [0.042, 0.175] |
| frame_since_step | component | 0.442 (below floor) | 0.450 (below floor) | +10 / −9; +0.008 [−0.067, 0.075] |
| qualifying_steps | component | 0.408 (below floor) | 0.417 (below floor) | +11 / −10; +0.008 [−0.067, 0.083] |
| **tried_unchanged** | **target** | **0.533 (below floor)** | **0.525 (below floor)** | +11 / −12; −0.008 [−0.083, 0.067] |
| **outcome_class** | **target** | **0.819 (inconclusive)** | **0.895 (inconclusive)** | +24 / −11; **+0.076 [0.006, 0.150]** |
| **observed_effect** | **target** | **0.762 (inconclusive)** | **0.866 (inconclusive)** | +21 / −4; **+0.104 [0.047, 0.162]** |

**Where reading breaks.** The decomposition separates two levels:

1. **Reading one entry.** The model reads exact actions, including neighbouring clicks, and dispatch status
   well under both representations.
   - Under the baseline records, it misses **transient changes**: `any_change` is 0.21 on the questions where
     "final frame only" is wrong.
   - The normalized records fix that. `any_change` rises to 1.00 there, and `final_equals_pre` meets the
     criterion. `outcome_class` and `observed_effect` improve with intervals above zero.
   - Transient cases still cause most of the remaining target errors. Under the candidate, 7 of 18
     `outcome_class` errors read changed-then-returned as final_frame_changed, and 10 of 22 `observed_effect`
     errors read it as no change.
2. **Combining entries.** Deciding whether the frame is still current (`frame_since_step`), which entries
   qualify (`qualifying_steps`) and the deduplicated set (`tried_unchanged`) all stay **below the floor under
   both representations**, with no paired change.
   - In `frame_since_step`, the most common error is `changed_at_least_once` for steps that are not shown, or
     that stayed the same.
   - In `qualifying_steps`, the model often lists steps when none qualify.
   - In `tried_unchanged`, it both omits and adds actions (candidate: 21 omit only, 32 add only, 4 both).

**Why it is not promoted.** The history candidate improves `outcome_class` and `observed_effect` with lower
bounds above zero, and no family regresses beyond the tolerance. But no target meets the criterion, and
`tried_unchanged` is unchanged at the floor, so the verdict is `improved_below_criterion`. The absence of a
detected regression is not a demonstration of non-inferiority.

## Descriptive partitions (not part of the decision)

| Partition | Family | Baseline | Candidate |
|---|---|---|---|
| development (30 contexts) | legal_coordinate_actions | 16/30 | 26/30 |
| development | tried_unchanged | 15/30 | 14/30 |
| development | outcome_class | 33/46 | 42/46 |
| development | observed_effect | 38/42 | 36/42 |
| transfer (6 archived v1 contexts, previously exposed) | legal_coordinate_actions | 4/6 | 6/6 |
| transfer | tried_unchanged | 4/6 | 5/6 |
| transfer | outcome_class | 11/11 | 11/11 |
| transfer | observed_effect | 9/10 | 10/10 |

These are single-pass and small, and they point the same way as the withheld result.

## How the result is used (protocol §10, frozen)

Both tracks are `improved_below_criterion`. So the frozen next step is to **investigate that track's evidence
representation or the model's capability before adding planning.** Neither candidate is promoted, and no
action-selection experiment follows from this result.

The error patterns suggest targets. These are hypotheses for a new, separately protocolled diagnostic, not
conclusions:
- **Control.** The remaining failures occur when ACTION6 is in the history but not legal. That is consistent
  with history interference, which is a hypothesis; a matched history-removal or alteration comparison would
  test it. Candidates to test:
  - presenting available actions with their argument requirements already joined;
  - placing the intersection rule in the question.
- **History, per-entry.** Transient changes remain the main error even with explicit phrases.
- **History, multi-entry.** The still-current rule is not applied, under either representation. This is where
  a separately labelled, tool-computed arm (for example, per-entry "still current" status) would test whether
  offloading the computation helps. Its success would support a tool-assisted agent, not unaided
  comprehension.

Scope: synthetic development trajectories and a scripted question set only. This says nothing about
generalization or solving.
