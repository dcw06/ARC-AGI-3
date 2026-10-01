# Feedback-action v1: closed-loop development experiment, protocol draft r0

**Status: draft for review.** It is not frozen and not authorized. There is no reservation, notebook, package or
model call. Nothing here approves compute. Every number below is a proposal.

## Question

When both arms receive the same accurate action-effect evidence, does a bounded structured hypothesis-testing
procedure change decisions compared with the evidence alone? The procedure is: hypothesis, supporting and
conflicting references, action, observable prediction, and what a different result would imply.

This is a bounded exploratory development comparison:
- not a generalization claim;
- not certification;
- not compute-matched.

The isolated difference and its exact cost are in `reports/feedback_action_v1_design.md` §2.

## Arms

- **Baseline:** the current observation, the legal controls, and the `transition_evidence_v1` evidence view.
- **Candidate:** the same, plus the `PROCEDURE` paragraph and the `hypothesis_test` response block.

Both arms share:
- the model, decoding settings (temperature 0, fixed seed) and action schema;
- the action validator and dispatch rule;
- the environment and observation pipeline.

A test requires `strip_procedure(candidate) == baseline` at every decision.

## Cases (selection rule written before any outcome of this design was inspected)

Only the development partition of `config/holdout_ledger.yaml` is eligible. H1, H2 and every withheld partition are
excluded and never opened. All 15 development games are already exposed, so every case is a **development case,
not independent validation**.

**Selection rule.** It is declared by control coverage and uses only the initial `available_actions` in
`reports/action_effect_history_v1_control_inventory.json` (zero actions dispatched):

1. Exclude ar25, cd82 and ft09, the subjects of earlier design work and dedicated diagnostics.
2. Form three control groups, so that each control mechanism family the procedure must reason about appears:
   - **coordinate-only:** ACTION6 present, no ACTION1–4;
   - **no coordinate action:** ACTION6 absent;
   - **mixed:** ACTION1–4 and ACTION6 both present.
3. Within each group, pick the lowest `sha256("feedback-action-v1:" + game_id)`.

| Group | Eligible (tie-break prefix) | Selected |
|---|---|---|
| coordinate-only | s5i5 `20844cd6`, su15 `47e73c3a`, vc33 `682c8345` | `s5i5-18d95033` |
| no coordinate action | ls20 `0b8ca6e9`, wa30 `98990942`, tr87 `9b7668b6`, g50t `d3f5582d` | `ls20-9607627b` |
| mixed | sk48 `05697743`, lf52 `254d6880`, sc25 `7a6b54e1`, sp80 `cf9a1935`, ka59 `f0c63aa4` | `sk48-d8078629` |

**Mechanism coverage.** This is declared from earlier retained evidence, not from game rules. s5i5 has a known
per-action counter region (AEH v1 results, observation 1). There, `no_observed_change` cannot occur unless the
counter is masked. s5i5 is kept deliberately, as the case where the repeat metric is expected to be uninformative,
and is reported as such.

**Replacement.** Replacement happens only for a technical incompatibility found by a CPU environment and dispatch
check. The replacement is the next game in the same group's tie-break order. A game is never replaced for an
outcome-based reason.

## Horizon and schedule

**Horizon: 24 dispatched actions per episode**, with up to 32 model calls (invalid outputs consume calls, not
actions).

**Why this horizon.** One prediction → feedback → revision cycle needs at least three decisions:
1. predict;
2. observe the falsification, then revise;
3. act on the revision.

With one or two segment boundaries (a reset or a level) possible, 24 actions allow several cycles per segment. That
is double AEH v1's 12, which yielded too few repeat opportunities. Level completion within 24 actions is not
expected on the evidence so far (0 levels in all earlier development runs). The horizon is chosen for the cycle,
not for solving.

**Schedule.**
- 3 cases × 2 arms × 2 blocks (seed 0 in both) = 12 episodes, up to 288 dispatched actions.
- Arm order within a block alternates by case.
- Prefix caching is off.
- Block 2 is a replication of block 1, to measure run-to-run variance. It is not an independent sample.

## Metrics (all reported per episode, per arm; nothing pooled across steps as if independent)

| Metric | Definition (independent evaluator, `research/feedback_action_v1/evaluate.py`) |
|---|---|
| Exact repeats after no observed change in the same state | Count of chosen exact actions (id plus coordinates) whose latest same-state observation in the window was `no_observed_change`, **with the number followed by a visible change or level**. Reported without equating repetition with waste. |
| Chosen-action evidence status | Distribution over `untested`, `tested_other_state`, `failed_only`, `outcome_unknown_only` and the same-state statuses |
| Prediction accuracy (candidate only) | correct / incorrect / unscoreable over mechanically checkable predictions. Descriptive, with no between-arm comparison. |
| Revision after contradiction (candidate only) | recognized / revised_not_cited / cited_not_revised / not_recognized / procedure_invalid. Descriptive. Not a success criterion: see design §6, delayed effects. |
| Invalid actions | by reason (not_json, truncated, illegal_action, …); retained, never dispatched |
| Invalid procedure blocks and unsupported citations | by reason; citations by category (`not_earlier`, `earlier_not_shown`, `wrong_claim`, `failure_read_as_no_change`) |
| Completed levels | from `levels_completed` increases or WIN only |
| Cost | actions, model calls, prompt and completion tokens (tokenizer counts in the live run), wall time, dispatch failures, unknown outcomes, interruptions |

## Outcome and advancement rules (proposal)

1. **Technical validity first.** All 12 episodes complete. The lifecycle and evidence integrity pass. The
   independent evaluator's replay matches. Otherwise the result is `technically_incomplete` and no behaviour
   claim is made.
2. **Solving.** Claim a solving improvement only from completed levels. The candidate must complete more levels
   than the baseline in at least two of three cases, in both blocks, with no case where it completes fewer.
   Otherwise the result is "no demonstrated solving improvement", whatever the behaviour metrics show.
3. **Behaviour (exploratory).** "Fewer unjustified repeats" is reported only if both blocks show the same
   direction in at least two cases, **and** the reduced repeats were ones not followed by a change. Anything else
   is `inconclusive`. Any per-case difference smaller than the baseline's block-1/block-2 difference is
   `within_run_to_run_variance`.
4. **Advancement to a larger study** needs either rule 2, or rule 3 together with:
   - candidate invalid-action rate ≤ the baseline's + 0.05;
   - unsupported-citation rate ≤ 0.20.

   The cost is reported either way.

## Proposed GPU budget and stop rules (proposal only; nothing is reserved or approved)

**Reference.** AEH v1 (144 calls, 128-token cap) used about 748 s of account GPU, including about 403 s of model
startup. ECv3's startup took 819 s.

**Estimate.**

| Item | Estimate |
|---|---|
| Startup | ≤ 900 s |
| Baseline calls | 144 × about 1.5 s |
| Candidate calls | 144 × up to about 6 s (640-token cap) |
| Total | **about 2,000 s** |

**Requested ceiling: 3,600 s** of a single session on one GPU. There are no retries for outcome reasons.

**Stop rules:**
- Stop the run without re-running if any of these happens:
  - first-cell wall time exceeds 3,000 s;
  - either arm's invalid-action rate exceeds 0.25 over its first 24 calls (technical abort; retain everything);
  - any holdout or withheld identifier appears in a request;
  - the canary or evidence integrity fails.
- A technical abort produces a report, not a silent rerun. A rerun needs a new approval.

## Before freezing (open items)

- Run the CPU environment and dispatch check on s5i5, ls20 and sk48 with 24 scripted legal actions.
- Measure tokenizer-exact token counts for both arms on recorded development observations (offline).
- Decide whether s5i5's counter region is masked: a contract change, Track-independent.
- Decide whether to add a third arm, a prediction-only arm without hypothesis and references, so that "predicting"
  is separated from "testing hypotheses".
