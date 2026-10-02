# Stagnation supervision v1: comparison protocol v1 (REVIEWABLE DRAFT, not frozen)

**Status.** This is a draft for review. It authorises nothing: no GPU time, no Kaggle run, no model inference, no
upload, and no holdout or withheld-partition access. It replaces nothing:
`reports/stagnation_supervision_v1_protocol_draft.md` stays as history. Freezing needs a review, a lock and an
explicit approval.

Inputs:
- the frozen trigger (`research/stagnation_supervision_v1/trigger_spec.json`);
- the synthetic benchmark (`reports/stagnation_supervision_v1_detector_results.md`);
- the CPU archive diagnostic (`reports/stagnation_supervision_v1_archive_diagnostic.md`).

## 1. Research question

**Does intervention at detected stagnation improve recovery, compared with ordinary continuation and with equally
budgeted periodic reflection?**

**Recovery.** After a reflection call, the agent leaves the detected loop, meaning it takes a (state, action) pair
not yet tried in the segment. It then obtains a confirmed progress signal (`levels_completed` increase or WIN)
before the detector fires again. Escaping into another loop is not recovery.

**Two comparisons:**
- Triggered vs periodic isolates **timing** at matched reflection cost.
- Triggered vs continuation measures the value of reflecting at all.

Beating continuation alone does not show value beyond spending more model calls.

## 2. Arms

Every arm shares:
- the policy model and serving configuration (as in action-effect-history v1: Qwen3-VL-30B-A3B FP8, vLLM 0.19.0,
  temperature 0, request seed 0, `max_tokens` 128, thinking disabled, `arc_action_v12` actions);
- the episode length;
- the transition_evidence_v2 records, unmasked;
- the frozen detector, which runs as an observer in every arm.

| Arm | When the reflection request is sent | Limits (identical in both reflection arms) |
|---|---|---|
| continuation | never | none (no reflection) |
| periodic | after every 10th action (P = 40 ÷ cap 4) | cooldown 6 actions; cap 4 per episode (valid, invalid and failed calls all count); supervisor-token ceiling 8,000 per episode; postponed when the current state was not observed; no retries |
| triggered | when the frozen detector fires (`state_action_recurrence = 2`, `tiny_effect_repeat = 10`) | same as periodic |

- **One request template.** Both reflection arms use `intervention.PROMPT`, the same four-field output, and the
  same validation, including the `arc_action_v12` argument rules.
- **Legal test actions** come from the reported available actions (transition_evidence_v2).
- **The arm label** never appears in the prompt.

**What the agent receives.** Only the rendered, validated fields reach the policy, as one extra block of text in the
next policy request. An invalid output delivers nothing. Exactly how the block is placed in the policy prompt must
be specified and frozen before review.

**View.** The unmasked view only. The step-counter blind spot (s5i5) is a known limitation. A masked fingerprint
would be a separately versioned experiment.

## 3. Cases

**Eligible games.** Only the development partition of `config/holdout_ledger.yaml` (15 games):

> ar25, cd82, ft09, g50t, ka59, lf52, ls20, s5i5, sc25, sk48, sp80, su15, tr87, vc33, wa30

H1 and H2 are excluded and are never opened. All 15 development games have prior model exposure, so every case is a
development case, not independent validation.

**Selection rule.** It was written before naming any game. It uses only the CPU archive diagnostic's mechanical
statistics: per game, over all archived acknowledged steps of action-effect-history v1, with zero model calls added.

**Tier A: games with archived observer evidence.**

| Group | Qualifies when (per game, pooled over its archived episodes) |
|---|---|
| Stagnation case | ≥ 90% of acknowledged steps show `no_observed_change`, **and** the frozen detector fired in every archived episode |
| Continuation-appropriate case | ≥ 75% of acknowledged steps reach a final frame new to their episode, **and** the median changed-cell count per step is > 4 (larger than the detector's tiny-effect size, so a step counter does not qualify) |
| Declared blind-spot case | Fits neither group, but ≥ 90% of steps change 1–4 cells (a per-action display change). It is run and reported separately, and excluded from the primary comparison and from the false-interruption denominator. |

**Tier B: a second continuation-appropriate game.** It is needed so the false-interruption cap rests on more than
one game.
- **Candidates,** in this fixed order: ls20, tr87, g50t. This is the no-coordinate replacement order already frozen
  for action-effect-history v1.
- **Rule.** Take the first candidate whose CPU scripted probe meets the continuation-appropriate criterion. The probe
  is the existing offline dispatch path with 12 fixed scripted legal actions, as in
  `reports/action_effect_history_v1_environment_check.json`; it uses no model.
- **Status.** This probe has not been run. The game is named only after it runs, and before any model run.

**Applying Tier A to the archive.**

| Game | Acknowledged steps | `no_observed_change` | Median changed cells | New final frames | Detector fired in episodes | Group |
|---|---|---|---|---|---|---|
| ar25 | 48 | 48 (100%) | 0 | 0 | 4 / 4 | **stagnation case** (design-informed: ar25 informed this intervention) |
| wa30 | 48 | 3 (6%) | 32 | 44 (92%) | 1 / 4 | **continuation-appropriate case** |
| s5i5 | 48 | 0 | 1 | 48 (100%) | 2 / 4 | **declared blind-spot case** |

**Resulting cases:** ar25 (stagnation), wa30 (continuation), the Tier B game (continuation, pending its probe) and
s5i5 (blind spot, reported separately).
- **Game seed** is 0 for every case, as in action-effect-history v1.
- **Replacement** happens only for technical incompatibility found by the CPU dispatch check, using the frozen
  replacement orders. A game is never replaced for an outcome-based reason.

## 4. Exclusions

- **Holdouts.** H1 and H2 games are never opened, listed for play or used for selection. No withheld partition is
  touched.
- **Games without archived evidence or a passing Tier B probe** are not eligible for this pilot.
- **From the primary comparison:** s5i5 (blind-spot case, reported separately).
- **From outcome metrics:** an episode that ends on a technical failure (lifecycle, closure, or a dispatch failure
  streak under §9). It is retained and reported, and its pair is marked not admitted. A game–block pair is admitted
  only if all three arms complete.
- **No reruns or substitutions after results are seen.** No threshold, cap, period or label rule changes after
  review.

## 5. Seeds and order

- **Fixed seeds.** Game seed 0; request seed 0; temperature 0.
- **Prefix caching off.** Action-effect-history v1 observed run-to-run differences with byte-identical first
  requests and suspected cache reuse.
- **Blocks.** 2 blocks. Within each game, arm order follows a rotation: block 1 runs continuation, periodic,
  triggered; block 2 runs periodic, triggered, continuation.
- **Repeat episode.** One byte-identical repeat of the block-1 continuation episode per primary game, to estimate
  run-to-run variance. A difference between arms smaller than the repeat difference is not interpreted.
- **Bootstrap seed.** The fixed string `stagnation-supervision-v1-protocol-v1`.

## 6. Horizons

- **Episode length: 40 actions,** provisional and subject to the budget in §10–11. An episode also stops at WIN or
  GAME_OVER, with no reset or restart.
- **Recovery horizon:** 10 actions after a reflection call, for both "leave" and "progress". The result is also
  reported to the end of the episode.
- **Within the 40 actions:** the cooldown of 6 and the cap of 4 allow up to 4 calls per reflection-arm episode.

## 7. Reference labels (frozen before results; assigned by rule, not by judgement)

A frozen script labels every observed decision point, meaning after an acknowledged and observed step t, in every
arm. It uses records only and is written and tested on synthetic fixtures before the run. Labels never use
detector output, arm or outcome.

| Label | Rule |
|---|---|
| **LC** (legitimate-continuation opportunity) | At least one of the last 3 acknowledged steps of the segment, up to and including t, changed more than 4 cells and reached a final frame new to the segment |
| **ST** (stagnation point) | Not LC, and each of the last 3 acknowledged steps of the segment changed at most 4 cells (0 included) |
| **IND** (indeterminate) | Neither LC nor ST, including the first two steps of a segment. Excluded from both denominators and counted. |

**Blind human audit.**
- **Sample.** A seeded, stratified random sample of 60 decision points: 20 from each label.
- **Reviewer.** Someone who does not know the arm, the trigger or the outcome, and who labels from the frames and
  actions alone as continue, stagnant or unclear.
- **Reporting.** Agreement with the rule is reported. The rule labels govern.
- **Consequence.** If the auditor disagrees with the rule on more than 20% of non-unclear points, the
  false-interruption cap is reported as "not certifiable: reference labels unreliable".

## 8. Metrics and denominators

| Metric | Numerator | Denominator | Unit |
|---|---|---|---|
| **False-interruption rate** (cap, §8.1) | Triggered-arm detector triggers at LC points (also reported for calls actually made) | LC points in the triggered arm | decision points, cluster-bootstrapped by episode |
| Periodic interruption rate (reference) | Periodic calls at LC points | LC points in the periodic arm | as above |
| Detector precision | Triggers at ST points (triggers at IND points reported separately) | All triggers | triggers |
| Detector recall | Stagnation runs (at least 3 consecutive ST points) containing a trigger | Stagnation runs, in the **continuation arm**, where the detector is an untouched observer | runs |
| Recovery (primary) | Calls followed within 10 actions by leaving the loop and then a confirmed progress signal before the detector fires again | Calls made, per arm | calls; reported per episode |
| Loop exit | Calls followed by leaving (`supervision.escapes`); result in {progress, another_detected_loop, no_progress_before_end, did_not_leave} | Calls made | calls |
| Actions to leave | Actions from a call to the first untried (state, action) pair | Calls that left | calls |
| Time in detected loops | Decision points between a detector firing and leaving | Observed decision points | per episode, every arm |
| Completed levels | `levels_completed` increases | Episodes | episodes |
| Cost | Reflection calls, charged tokens (serving tokenizer counts), latency; their share of the episode ceiling | Episodes | episodes |
| Reliability | Invalid outputs; failed calls; failed and unknown dispatches; cancellations; episodes ended by budget | Calls; dispatches; episodes respectively | as stated |

**The unit of analysis is the episode.** Decision points within an episode are never treated as independent.
Intervals are computed by episode-cluster bootstrap (10,000 resamples, fixed seed), with Wilson intervals shown as
a naive reference.

### 8.1 The 10% false-interruption cap (provisional acceptance ceiling)

- **Rate.** The rate is the share of LC points in the triggered arm that received a detector trigger. The LC
  definition (§7) is the frozen denominator.
- **Certification.** The cap is **certified** only if the upper end of the 95% interval is ≤ 10%, taking the larger
  of the cluster-bootstrap upper bound and the Wilson upper bound.
- **Minimum evidence.** The cap **cannot be certified** with fewer than 60 LC points in the triggered arm, from at
  least 2 continuation-appropriate games and at least 4 episodes. At 60 points, 0 false interruptions gives a
  Wilson upper bound of 6.0% and 2 give 11.4%, so the minimum makes the cap meaningful only with very few false
  interruptions.
- **Results reported in every case:** the point estimate, both intervals, the counts, and the per-game split.
- **What the cap is.** It is an acceptance ceiling for using the trigger, not a hypothesis test. Failing it is
  reported as "exceeds the provisional cap". Missing the minimum is reported as "not certifiable".

### 8.2 Advancement (draft)

Triggered reflection advances only if **all** of the following hold:
- **Recovery against periodic:** more recovery per episode than periodic in both blocks for the stagnation case,
  with realised reflection tokens ≤ periodic's.
- **Recovery against continuation:** more recovery than continuation.
- **False interruptions:** the cap is certified, and the triggered false-interruption rate is ≤ periodic's.
- **No regressions:** completed levels, invalid-output rate and failure rates are no worse than either other arm.
- **Beyond variance:** the differences exceed the repeat-episode variance.

Otherwise the result is **inconclusive**. Given 0 completed levels to date, a recovery effect is unlikely to be
measurable at this scale. The proposal accepts that "inconclusive" is the expected default.

## 9. Failure rules (fixed before the run)

- **Interface failure.** If invalid reflection outputs exceed 50% after the first 10 reflection calls, stop the
  reflection arms and report. The interface is then the finding.
- **Dispatch failures.** If failed plus unknown dispatches exceed 10% of dispatches, stop and report.
- **Nothing to intervene on.** If the stagnation case's block-1 continuation episode shows zero detector firings,
  stop: there would be nothing to intervene on. The archive fired in 4 of 4 ar25 episodes.
- **Wall time.** Stop at the internal wall-time limit, keeping the startup and teardown margins of earlier runs.
- **Charging.** Every call, including invalid, failed and cancelled calls, is charged. The supervisor-token ceiling
  is never exceeded. No automatic reruns.
- **Evidence integrity.** Lifecycle, cleanup, canary and archive checks follow the established run-evidence
  procedure. A technically incomplete run reports no outcome result.

## 10. Runtime estimate (estimates from measured rates, labelled as such)

**Measured inputs:**

| Source | Measurement |
|---|---|
| action-effect-history v1 | Model startup 403 s |
| action-effect-history v1 | Supervisor time 735 s for 144 policy steps, about 5.1 s per step all-in (model call, dispatch, evidence) |
| action-effect-history v1 | Mean policy-call latency 1.2–1.6 s; one prefix-cached episode at 0.24 s, excluded |
| action-effect-history v1 | About 24,400 prompt tokens and about 30 completion tokens per policy call |
| evidence-comprehension v3 | Installation 141 s |
| evidence-comprehension v3 | Model startup 819 s, so startup varies 2× between runs |
| evidence-comprehension v3 | 0.104 s mean per short-answer call, with about 740 prompt tokens per call and prefix caching off |
| Rehearsal requests (`stagnation_supervision_v1`) | 2,775–4,764 characters, about 700–1,200 tokens at the declared 4 characters per token |

**Unmeasured.** Reflection-call decode time, for up to about 400 output tokens, is not measured. **Estimate:** 2–8 s
per call.

**Design size:**
- **Episodes:** 4 games × 3 arms × 2 blocks = 24, plus 3 repeat episodes (one per primary game), giving 27 episodes
  of at most 40 actions and at most 1,080 policy steps.
- **Reflection calls:** at most 4 per reflection-arm episode × 16 = 64.

**Estimated GPU time:**

| Component | Estimate |
|---|---|
| Policy steps: 1,080 × 5.1 s | ≈ 5,500 s |
| Reflections: 64 × 2–8 s | ≈ 130–510 s |
| Startup and installation: 544–960 s per run | ≈ 1,100–1,900 s over 2 runs |
| **Total** | **≈ 6,700–7,900 s** |

**Splitting.** A single cell may not fit under per-cell limits, so the design is planned as **two runs, one per
block** (about 3,400–4,000 s each).

**Episode token use (estimate):**
- **Policy prompts:** about 980k tokens per episode (40 × 24.4k), as in action-effect-history v1.
- **Reflection:** at most 8,000 supervisor tokens per episode, which fits 4 calls of about 1,200 input plus 400
  output tokens.

**The 40-action horizon is provisional.** If a pre-run timing check measures more than 5.1 s per step all-in, the
horizon is reduced before freezing, never after results.

## 11. Proposed budget (proposal only; nothing authorised)

| Step | GPU | Status |
|---|---|---|
| CPU work | none | Tier B scripted probe and reference-label script with synthetic tests; must finish before review |
| Main runs | **9,000 GPU-seconds (2.5 h)** across **at most two runs** | About 15% above the upper estimate. One attempt each, no automatic reruns, stop rules as in §9 |

**Accounting.** The exact billed time is unknown from the provider. The account counter is recorded before and after
each run, as in earlier runs.

## 12. Known limitations

- **The step-counter blind spot.** Under the unmasked view, s5i5-like step bars make every frame unique.
  `state_action_recurrence` cannot fire there; only a 10-action identical streak can.
- **Small, exposed, design-informed sample.** One stagnation game, which informed the design, and two
  continuation games, all with prior model exposure. No generalisation claim is possible.
- **Mechanical labels.** LC and ST labels are mechanical proxies: a new frame is not progress, and few changed
  cells is not stagnation. The audit measures, but does not remove, this gap.
- **Few level completions.** Recovery requires a confirmed progress signal. With 0 completed levels to date, the
  primary metric may be all zeros. That would be reported as such, and it would not show that supervision cannot
  help.

## Open questions for review

1. **Tier B probe.** Approve running it on CPU, which needs the offline engine. Alternatively, accept a pilot with
   one continuation game; the cap would then be "not certifiable" by construction.
2. **Prompt placement.** How should the rendered reflection be placed in the policy prompt? This affects only the
   reflection arms and must be frozen.
3. **Run size.** Is a two-run split (one per block) acceptable, or should the horizon shrink to fit one run?
4. **Audit reviewer.** Who is the blind auditor, and is 60 sampled points enough?
5. **Episode length.** Should GAME_OVER episodes keep "no restart", as in action-effect-history v1, even though
   that shortens some episodes below 40 actions?
