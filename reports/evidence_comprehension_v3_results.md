# Evidence comprehension v3: live results

Attempt `ecv3-089bf11fd38c41f88808794a134a3d56`, from review package r1 (lock `66713c62…5cfd`), on Kaggle (version 1,
one RTX Pro 6000). The protocol is `reports/evidence_comprehension_v3_protocol.md` (revision 2).

| Record | Location |
|---|---|
| Independent evaluation | `reports/evidence_comprehension_v3_live_evaluation.json` |
| Archive | `evidence/evidence-comprehension-v3-live.tar.xz`: 44 files, SHA-256 `552d5c7e…9dac`, locked by `reports/evidence_comprehension_v3_live_archive.json`. Replaying it reproduces the evaluation exactly. |
| Download manifest | `reports/evidence_comprehension_v3_download.json` (35 provider files) |
| Approval | recorded verbatim: "I approve the workstream 1's v3 run now you can run it". The disclosed residual risks were not accepted. |

## 1. Technical validity

| Check | Result |
|---|---|
| Technically complete (independent evaluator, live mode) | **yes**: lifecycle passed, run evidence verified, no call errors |
| Calls | 6,054 of 6,054 answered; 0 timed out, invalid or truncated |
| Completeness | primary (both tracks), secondary history alteration, withheld schedule and whole schedule: **all complete** |
| Prefix caching | Off. 4,472,550 prompt tokens were processed (the audited 4,472,511 plus the canary), with 0 prefix-cache queries and 0 hits. |
| Two-pass agreement (withheld) | every answer identical between the passes |
| Time | Installation 141 s; **model startup 819 s** (twice v2's 402 s); questions 701 s (mean 0.104 s per call, slowest 0.72 s); first cell 1,666 s, against the 3,000 s cutoff. This was longer than the 1,485 s measured-overhead scenario and inside the 1,854 s allowance scenario. |
| GPU accounting | Exact billed time: **unknown**. The account counter rose from 2,293.652 s to 3,969.989 s (`reports/evidence_comprehension_v3_postrun_provider.json`), a rise of 1,676.337 s. That is an account-counter observation, not a billed amount. |

## 2. Control-interface result (Track A)

**Verdict: `candidate_clear_improvement`.** The scores are both-correct over the withheld partition, original
variant only.

| Family | Role | A0 intersect instruction (reference) | A1 computed control metadata | Paired: improved / regressed; difference [95% CI] |
|---|---|---|---|---|
| legal_actions | component | 0.992 (criterion_met) | 1.000 (criterion_met) | +1 / −0; +0.008 [0.000, 0.023] |
| action6_legal | component | 1.000 (criterion_met) | 1.000 (criterion_met) | 0 / 0 |
| **legal_coordinate_actions** | **target** | **0.859 (inconclusive)** | **1.000 (criterion_met)** | **+18 / −0; +0.141 [0.086, 0.203]** |

**The reference's errors.** All 18 of A0's errors answered `[6]` when ACTION6 was not legal, and every one had
ACTION6 in the history. v2's pattern reproduced on fresh cases, at 0.859 here against v2's 0.883.

**What the candidate did.** The computed metadata removed every one of those errors and introduced none.

**How to read this.** It shows **a more usable control interface**: the metadata supplies the relationship the
question tests. It does not show that the model learned to intersect the rule and the legal set itself.

## 3. Tool-assisted history result (Track B)

**Verdict: `improved_below_criterion_tool_assisted`.**

| Family | Role | B0 normalized history (reference) | B1 tool eligibility | Paired: improved / regressed; difference [95% CI] |
|---|---|---|---|---|
| step_action_match | component | 0.977 (criterion_met) | 0.953 (criterion_met) | +0 / −3; −0.023 [−0.055, 0.000] |
| any_change | component | 0.938 (criterion_met) | 0.922 (criterion_met) | +3 / −5; −0.016 [−0.055, 0.023] |
| qualifying_steps | component | 0.367 (below floor) | 0.625 (below floor) | +34 / −1; **+0.258 [0.180, 0.336]** |
| outcome_class | component | 0.906 (inconclusive) | 0.891 (inconclusive) | +7 / −9; −0.016 [−0.078, 0.047] |
| observed_effect | component | 0.852 (inconclusive) | 0.867 (inconclusive) | +9 / −7; +0.016 [−0.047, 0.078] |
| **tried_unchanged** | **target** | **0.477 (below floor)** | **0.664 (below floor)** | **+26 / −2; +0.188 [0.117, 0.266]** |

**What the tool changed.** The tool fields lifted both the target and entry selection substantially: 26 answers
fixed against 2 broken, and 34 against 1. But `tried_unchanged` stays below the 0.70 floor.

**Where it is still limited.** Even with every entry already marked eligible or not, the model:
- selects and deduplicates badly;
- answers correctly on only 0.32 of the questions where the best shortcut is wrong.

**Observed error pattern (pass 1, `tried_unchanged` wrong answers):**

| Condition | Omitted qualifying actions only | Added non-qualifying actions only | Both | Answer contained duplicates |
|---|---|---|---|---|
| B0 | 28 | 31 | 8 | 5 |
| B1 | 15 | 25 | 3 | 1 |

The dominant remaining pattern under B1 is **including actions from entries the tool marked not eligible**. These
are observed error patterns, not claims about the model's internal mechanism.

**No family regressed beyond the tolerance.** The small negative differences on the per-entry components are
within the intervals. "No regression detected" is not a demonstration of non-inferiority.

## 4. Secondary history sensitivity (non-gating)

**The comparison.** For 60 withheld contexts, legal-coordinate questions were asked twice. The second time used a
matched synthetic counterfactual history: every ACTION6 event replaced by one legal simple action, with all
outcomes kept and every action reference kept consistent.

| Condition | Both correct | Right only with the original history | Right only with the counterfactual | Neither | Difference [95% CI] |
|---|---|---|---|---|---|
| A0 intersect instruction | 42 | 0 | **16** | 2 | +0.267 [0.167, 0.383] |
| A1 computed metadata | 60 | 0 | 0 | 0 | 0 |

**What it shows.** Under A0, removing ACTION6 from an otherwise identical history turned 16 wrong answers right,
and none the other way. This is evidence that **irrelevant action history interferes with the control answer**,
in these synthetic cases.

**What it does not show.** It does not establish that live control errors all have this cause.

**Under A1**, the answers were insensitive to the history alteration.

## 5. Limitations

- **The evidence is synthetic.** Contexts are synthetic development trajectories. The transfer group (six
  previously exposed archived observations, without grids) is descriptive and outside the gate. Nothing here
  concerns solving or full live visual observations.
- **Both passes are one sample.** They were identical, as in v1 and v2. With caching off, they measure
  repeatability, not independent samples.
- **Both positive results are assisted.** Track A is interface usability, and Track B is tool-assisted.
  Neither establishes unaided reasoning.
- **v3's withheld partition is now development material.** A follow-up tuned on these answers needs fresh
  evaluation cases.

## 6. Next step (Workstream 1, Milestone D decision table)

| Track | Outcome | Next step |
|---|---|---|
| Control | candidate clearly improves and meets the criterion | **Prepare a control-interface action-selection comparison** (Milestone E): the same observations and budget, with and without computed control metadata, changing only that component. |
| History | improvement remains below the criterion | **Diagnose the residual errors before any action-selection use.** The dominant pattern under B1 is including entries the tool marked not eligible. A follow-up would name one explanation, for example that the eligibility field is not being used for selection; an alternative, for example that deduplication of exact actions is the bottleneck; the smallest comparison that separates them; fresh evaluation cases; and a separate budget. |

Only the control interface qualifies, so no combined claim arises.
