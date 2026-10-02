# Stagnation supervision v1: comparison protocol v2 (REVIEWABLE DRAFT, not frozen)

**Status.**
- **Draft.** This is a draft for review. It authorises nothing: no GPU time, no Kaggle run, no model inference, no
  upload, no reservation, and no holdout or withheld-partition access.
- **Earlier versions.** v1 (`reports/stagnation_supervision_v1_protocol_v1.md`) and the earlier draft stay as history.
- **This revision** applies the review of v1 (b1df75c).
- **Runtime estimates are not an authorization ceiling.** A ceiling exists only in a future signed compute
  authorization.
- **Prior exposure limits real-game claims.** All development games have prior model exposure.

| Record | Location |
|---|---|
| Frozen trigger | `research/stagnation_supervision_v1/trigger_spec.json` (unchanged) |
| Archive diagnostic | `reports/stagnation_supervision_v1_archive_diagnostic.md` |
| Tier B probe | `reports/stagnation_supervision_v1_tier_b_probe.json` |
| Post-hoc Tier B inspection | `reports/stagnation_supervision_v1_tier_b_inspection.json` |
| Outcome evaluator | `research/stagnation_supervision_v1/outcomes.py` |
| GPU-disabled closed loop | `research/stagnation_supervision_v1/closed_loop/`, derived by `scripts/derive_stagnation_supervision_v1.py` |

## Changes from v1

| Review item | v2 |
|---|---|
| The outcome was defined per reflection call, so it could not be measured in continuation | Outcomes are defined on **detector-defined opportunities**. The frozen detector observes every arm, and every opportunity is assessed over a common subsequent action window (§8). |
| Equal caps do not make equal cost | Realised reflection calls, tokens and latency are reported per arm. Periodic and triggered are **equal-budget**, not equal-cost (§8.4). |
| "New state reached" can be satisfied by a moving counter | The primary behavioural endpoint is **behavioural recovery**: exit from the cited repetition pattern, followed by a predeclared quiet period without recurrence, inside a fixed window. New states and new (state, action) pairs are reported separately. Level completion is the separate solving endpoint (§8.1). |
| Tier B probe | Approved and run. ls20 met the frozen criterion. A post-hoc inspection qualifies that result (§3). |
| Reflection delivery | A labelled model-generated suggestion block, separate from the observation, with the same placement, lifetime and size limit in both reflection arms. It is cleared at reset, level change or terminal state. No reflection is issued when fewer actions remain than the recovery window (§2.1). |
| Audit and cap | A blinded audit by a teammate who did not design the detector. 60 points is an initial label-quality audit, not certification. The 10% ceiling stays as a provisional benchmark gate (§8.3). |
| Horizon and sessions | 40 actions, two sessions. Timing was recomputed from measured rates (§10). |
| GAME_OVER | No restart; restarting would be a different intervention (§6). |

## 1. Research question

**Does intervention at detected stagnation improve recovery, compared with ordinary continuation and with equally
budgeted periodic reflection?**
- **Recovery** means behavioural recovery (§8.1), measured identically in all three arms.
- **Level completion** is the solving endpoint and is reported separately.
- **Triggered vs periodic** isolates timing at equal budget.
- **Triggered vs continuation** measures the value of reflecting at all.

## 2. Arms

Shared by every arm, unchanged from action-effect-history v1's common baseline:
- the policy model and serving settings: Qwen3-VL-30B-A3B FP8, vLLM 0.19.0, temperature 0, request seed 0,
  `max_tokens` 128, thinking disabled;
- the `arc_action_v12` action contract;
- the observation payload and response schema;
- one shared system prompt, to which one sentence describing the suggestion block is added in all arms;
- transition_evidence_v2 records, unmasked;
- the frozen detector, running as an observer.

| Arm | Reflection request | Policy limits (identical for periodic and triggered) |
|---|---|---|
| continuation | never | none |
| periodic | after every 10th action | cooldown 6 actions; cap 4 per episode (valid, invalid and failed all count); supervisor-token ceiling 8,000 per episode; postponed while the state is unobserved; no reflection when fewer than 10 actions remain; no retries |
| triggered | when the frozen detector fires (`state_action_recurrence = 2`, `tiny_effect_repeat = 10`) | same as periodic |

- **Reflection request.** Both reflection arms use one template (`intervention.PROMPT`) and one four-field output,
  validated against `arc_action_v12` with legal ids taken from the reported available actions. The arm label never
  appears in the prompt.
- **Reflection call settings.** The reflection call uses the same model, temperature 0, seed 0, `max_tokens` 400, a
  fixed system message, and no thinking.

### 2.1 Suggestion delivery (implemented; identical in both reflection arms)

**Placement.**
- A validated reflection becomes the top-level field `model_generated_suggestion`, beside the observation and never
  inside it.
- It carries a fixed label: "MODEL-GENERATED SUGGESTION (a hypothesis from a reviewer model, not an observation)".
- It contains the rendered four fields and its lifetime.
- The observation payload is byte-identical to continuation's. `strip_suggestion(request)` equals the continuation
  request (tested).

**Lifetime.**
- The block is shown with the next 10 policy requests.
- It is replaced only by a later valid reflection. An invalid or failed reflection delivers nothing and leaves the
  current block in place.
- The size limit is 1,600 characters.

**Clearing.** The block is cleared at a reported reset, level change or terminal state (tested for all three).

**Minimum remaining actions.** No reflection is issued when fewer than 10 actions remain, which is the recovery
window. Every reflection can therefore be evaluated over a full window (tested: no call after action index 29 of
40).

**Continuation** never carries a block. A request that tries is refused.

**No reflection at a terminal state or segment boundary.** This follows the review of 463cea3.
- **At a terminal state** (WIN or GAME_OVER), play has ended and no recovery window can follow. The terminal
  transition and the detector output are still recorded. The decision is logged as `suppressed_terminal_state`, with
  0 remaining actions.
- **At a reset or level change,** the detector's evidence belongs to the segment that just ended. The decision is
  logged as `suppressed_segment_boundary`.
- **Remaining actions** are computed from actual play, not the nominal horizon. The runner passes 0 after a terminal
  state, or after a non-acknowledged dispatch, which also stops the episode.
- **Tests.** Termination, reset and level change are tested at a scheduled periodic call and at a trigger firing in
  both reflection arms.
- **Effect on rehearsal.** On the synthetic rehearsal, exactly 8 of 3,384 decisions changed, each at a level
  completion or reset. The other 3,376 are byte-identical to before.

**Reflection completion semantics.**
- **Validity.** A reflection is valid only if the service reports `finish_reason` exactly `stop`.
- **Anything else** (`length`, missing or null, or any other value) makes it an invalid reflection. It is charged,
  its request and raw output are retained, it counts toward the cap, and it delivers no new suggestion. An existing
  suggestion keeps its lifetime unchanged.
- **Token audit.** A token-count mismatch remains a technical failure.
- **Tests** cover `length`, a missing value and an unknown value.

## 3. Cases (development partition only)

**Eligible games.** The development partition of `config/holdout_ledger.yaml` (15 games), verified in code. H1 and
H2 are never opened. The offline game archive contains only development games (checked).

**Selection rule.** v1's rule, stated before naming games, unchanged:

| Tier | Group | Game | Basis |
|---|---|---|---|
| A | stagnation case | ar25 | Archive: 100% `no_observed_change`; fired in 4/4 episodes. Design-informed. |
| A | continuation-appropriate case | wa30 | Archive: 92% new final frames; median 32 changed cells. |
| A | declared blind-spot case | s5i5 | Archive: every step changes 1–2 step-bar cells. Run and reported separately. |
| B | continuation-appropriate case | **ls20, pending review** | CPU probe (below) |

**Tier B probe** (approved; CPU only; offline engine; no model).
- **Provenance.** The definition was committed (0a8ef61) before the run, and the result is write-once (ce2beb2).
- **Candidates** in the written order: ls20, tr87, g50t. Probing stopped at the first that qualified.

| Candidate | Probed | Observed steps | New final frames | Median changed cells | Terminal | Result |
|---|---|---|---|---|---|---|
| ls20-9607627b | yes | 12 | 12 (100%) | 52 | none | **qualifies** under the frozen criterion |
| tr87-cd924810 | no (stopped at the first qualifier) | | | | | |
| g50t-5849a774 | no (stopped at the first qualifier) | | | | | |

**Post-hoc inspection.** It was written after the probe, is descriptive and changes nothing (792453e).
- **Finding.** Every ls20 probe step changed 2 cells in the bottom rows. In 10 of 12 steps, the frame above the
  bottom rows had already been seen in the episode. The scripted rotation (1, 2, 3, 4) moved the playfield back and
  forth, and a per-step display made every full frame new.
- **Why the criterion missed it.** The criterion's median of more than 4 cells did not exclude this, because the
  oscillating block contributes 50 cells.
- **What it means.** Under this probe, ls20's qualification rests on the same kind of moving-display novelty the
  review warned about.
- **The rule result stands as recorded.** No second policy or candidate was run.
- **Decision needed (§13, question 1):** keep ls20 as written, or adopt an amended criterion and probe tr87, then
  g50t. An amended criterion would be a new, separately committed definition, not a reinterpretation.
- **If ls20 is excluded** and no replacement is approved, the false-interruption gate is "not certifiable" by
  construction, because it needs at least 2 continuation games.

**Game seed** is 0. Initial canonical hashes are frozen in `closed_loop/protocol.json`; the ar25, s5i5 and wa30
hashes reproduce action-effect-history v1's. Replacement happens only for technical incompatibility.

**Prior exposure.** Every development game has prior model exposure, and ar25 informed the design. Results are
development evidence about these games and this model. They are not real-game or generalisation claims.

## 4. Exclusions

- **Holdouts.** H1 and H2 are never opened, listed or used for selection.
- **Primary comparison.** s5i5 is the declared blind-spot case; it is run and reported separately.
- **Technical failures.** An episode ending on a technical failure is retained and reported. Its game group is "not
  admitted" for outcome comparison.
- **No outcome-based changes.** No outcome-based reruns, substitutions or threshold, label, cap or window changes
  after review.

## 5. Seeds and order

- **Fixed seeds.** Game seed 0, request seed 0, temperature 0.
- **Prefix caching off.** It is a settings item for the future host.
- **Blocks.** Two blocks. Within each game, arm order rotates: block 1 runs continuation, periodic, triggered; block
  2 runs periodic, triggered, continuation.
- **Repeat episodes.** One byte-identical continuation repeat per primary game in block 1, to estimate run-to-run
  variance.
- **Bootstrap seed.** `stagnation-supervision-v1-protocol-v2`.

## 6. Horizons

- **Episode length: 40 actions,** provisional. Episodes are not shortened to fit one session if that would remove
  the post-intervention window.
- **Terminal states.** Play stops at WIN or GAME_OVER with no restart.
- **Recovery window:** 10 actions. **Quiet period:** 5 actions. **Latest exit:** 5 actions after the opportunity
  opens.
- **Reflections** are possible only through action index 29.

## 7. Reference labels (frozen rule; implemented in `outcomes.labels`)

| Label | Rule |
|---|---|
| **LC** (legitimate-continuation opportunity) | At least one of the last 3 acknowledged steps in the segment changed more than 4 cells into a final frame new to the segment |
| **ST** | Not LC, and each of the last 3 acknowledged steps changed at most 4 cells |
| **IND** | Neither (excluded from both denominators) |
| **UNOBSERVED** | The step's result was not observed |

Labels never use detector output, arm or outcome. A counter alone is never LC (tested).

**Blinded audit.**
- **Auditor.** A teammate who did not design the detector.
- **Sample.** A seeded, stratified sample of 60 decision points, 20 per label.
- **Method.** The auditor sees the frames and actions only, without arm, trigger or outcome, and labels each point
  continue, stagnant or unclear.
- **Status.** This is an initial label-quality audit, not strong certification.
- **Consequence.** If more than 20% of non-unclear points disagree with the rule, the gate is reported as "not
  certifiable: reference labels unreliable".

## 8. Metrics and denominators

**The unit is the episode.** Decision points are never treated as independent. Intervals use episode-cluster
bootstrap (10,000 resamples, fixed seed), with Wilson intervals as a naive reference.

### 8.1 Primary behavioural endpoint: behavioural recovery (`outcomes.opportunities`)

**Opportunity.** The first detector firing at step t, cooldown ignored, with all 10 window actions inside the
40-action horizon.
- It is identified identically in every arm by the observer detector.
- Windows never overlap; the next opportunity can open only after the window closes.
- Firings too late for a full window are counted as `censored_horizon`.

**Pattern.** What the firing cited:
- for `state_action_recurrence`: the exact (pre-frame, action) pairs in its evidence;
- for `tiny_effect_repeat`: the identical action with effects of at most 4 cells.

**Assessment over window t+1 .. t+10:**

| Status | Meaning |
|---|---|
| `recovered` | The exit is the first acknowledged, observed step that is not an instance of the pattern. It must happen by t+5, and the next 5 actions must contain no detector firing and no instance of the pattern. |
| `not_recovered` | All needed steps were observed, and the agent did not recover. This includes escaping into another loop and a late exit. |
| `indeterminate` | An unknown outcome or missing observation intervenes. A failed dispatch is skipped. |
| `censored_terminal` | The episode ends, or a reset starts a new segment, before recovery is decided. |

**Primary rate.** `recovered` ÷ (`recovered` + `not_recovered`), per arm, by episode-cluster bootstrap. Opportunities,
statuses and censoring counts are always reported.

**Secondary measures.** Actions to exit, new frames in the window, new (state, action) pairs in the window, and
level completion inside the window. A moving counter can make every frame new without recovery (tested).

### 8.2 Solving endpoint

**Completed levels** per episode and arm, from `levels_completed` increases. With 0 completed levels to date, a
difference is not expected at this scale.

### 8.3 Provisional false-interruption gate (10%)

| Element | Definition |
|---|---|
| Rate | Triggered-arm detector triggers at LC points ÷ LC points in the triggered arm. Reflection calls actually made at LC points are reported too. |
| Reference | The periodic arm's rate, computed the same way |
| Within the provisional ceiling | The 95% upper bound, taking the larger of the Wilson and episode-cluster bootstrap bounds, is at most 10% |
| Minimum evidence | At least 60 LC points from at least 2 continuation-appropriate games and at least 4 episodes; otherwise "not certifiable" |
| Always reported | Point estimate, both intervals, counts, per-game split |

**What the gate cannot show.** It is a provisional benchmark gate. Mechanical novelty labels and a few correlated
episodes do not establish that an interruption is genuinely harmful.

### 8.4 Realised cost (`outcomes.realised_cost`)

Per arm:
- reflection calls: valid, invalid and failed;
- charged input and output tokens, using serving-tokenizer counts in a live run;
- latency, and the triggered-to-periodic token ratio.

The two reflection arms are **equal-budget** (same cap, cooldown, token ceiling and lifetime), **not automatically
equal-cost**. Any comparison states the realised cost of each arm.

### 8.5 Reliability

Rates are given per call, dispatch and episode:
- invalid reflections and failed reflections;
- failed and unknown dispatches;
- token-audit failures (each is a technical failure);
- cancellations and interruptions.

### 8.6 Advancement (draft)

Triggered advances only if **all** of the following hold:
- **Against periodic:** a higher behavioural-recovery rate than periodic in both blocks for the stagnation case,
  with realised reflection cost reported.
- **Against continuation:** a higher rate than continuation.
- **False interruptions:** the false-interruption gate is within the provisional ceiling with minimum evidence met,
  and the triggered rate is at most the periodic rate.
- **No regressions:** completed levels, invalid and failure rates are no worse than either other arm.
- **Beyond variance:** the difference exceeds the repeat-episode variance.

Otherwise the result is **inconclusive**, which is the expected default.

## 9. Failure rules (fixed before any run)

- **Interface failure.** Invalid reflections above 50% after the first 10 reflection calls stop the reflection arms.
- **Dispatch failures.** Failed plus unknown dispatches above 10% stop the run.
- **Nothing to intervene on.** Zero detector firings in the stagnation case's block-1 continuation episode stop the
  run.
- **Token audit.** A reflection or policy token-audit mismatch is a technical failure (tested). A reflection that
  did not finish with `stop` is an invalid reflection, not a technical failure (§2.1).
- **Admission and wall time.** The admission cutoff and internal wall time are enforced, with the cleanup reserve
  kept.
- **Charging.** Every call is charged; no automatic retries.
- **Evidence integrity.** A technically incomplete run reports no outcome result.

## 10. Runtime (recomputed; estimates, labelled as such)

**Measured inputs:**

| Source | Measurement |
|---|---|
| action-effect-history v1 (live) | 735 s supervisor time for 144 policy steps, 5.1 s per step all-in, with 12-step episodes |
| action-effect-history v1 (live) | Policy-call latency 1.2–1.6 s |
| action-effect-history v1 (live) | Model startup 403 s |
| action-effect-history v1 (live) | About 24,400 prompt tokens per policy call |
| evidence-comprehension v3 (live) | Startup 819 s, so startup varies 2× between runs |
| evidence-comprehension v3 (live) | Installation 141 s |
| This pass, CPU rehearsal (this workstation, offline engine, fake server) | About 0.40 s per step overhead, of which about 0.31 s is evidence persistence, at 40-action episodes |
| This pass, CPU rehearsal | Persistence rewrites the growing episode file, so its cost per step rises with episode length |
| This pass, CPU rehearsal | Before a fix in this pass, history rebuilding cost about 7.9 s per step; that cost is now removed |
| Rehearsal reflection requests | About 700–1,200 tokens at the declared 4 characters per token |

**Unmeasured.** Reflection decode time, estimated at 2–8 s per call.

**Per-step estimate: 5.1–6.1 s.** The upper figure adds an assumed 1 s for longer-episode persistence on the target
CPU. A pre-run timing check on the target must confirm it before freezing.

| | Session 1 (block 1 + repeats) | Session 2 (block 2) |
|---|---|---|
| Episodes | 15 (12 + 3 repeats) | 12 |
| Policy steps (at most) | 600 | 480 |
| Reflection calls (at most) | 32 | 32 |
| Policy steps × 5.1–6.1 s | 3,060–3,660 s | 2,448–2,928 s |
| Reflections × 2–8 s | 64–256 s | 64–256 s |
| Startup and installation | 544–960 s | 544–960 s |
| Cleanup reserve | 300 s | 300 s |
| **Estimated session time** | **≈ 3,970–5,180 s** | **≈ 3,360–4,440 s** |

These are estimates, not authorization ceilings.

## 11. Package and sessions (proposal; nothing authorised)

**There are two sessions, one per block,** each a separate package run with its own startup, canary and cleanup.

| | Session 1 | Session 2 |
|---|---|---|
| Content | block 1 (4 game groups × 3 arms) plus 3 continuation repeats | block 2 (4 game groups × 3 arms) |
| Session count | 1 of 2 | 2 of 2 |
| Maximum reservation (proposal) | 5,400 s | 4,800 s |
| Admission cutoff | A game group (up to 3 episodes) is admitted only if at least 800 s remain before the internal deadline; otherwise it and all later groups are recorded "not admitted" | same, 800 s |
| Cleanup reserve | 300 s, kept after the internal deadline for client, scorecard and process cleanup | 300 s |
| Retry policy | **No retry allowance is approved.** No automatic retries of calls, episodes, groups or sessions. A failed or interrupted session is reported as such and is not rerun without a new, separate approval. | same |

**Totals.**
- **Proposed reservation:** 10,200 GPU-seconds across both sessions. This is a proposal only.
- **Estimated use:** about 7,330–9,620 s. It is an estimate, not an authorization ceiling.
- **Accounting:** the account counter is recorded before and after each session, because the exact billed time is
  unknown from the provider.

## 12. What remains before an exact source and package lock

1. **Tier B decision.** Keep ls20, or approve an amended criterion and a new probe of tr87, then g50t.
2. **Live host and process stack.** Derive the host, worker, supervisor, monitor, resources, launch, package, review
   and notebook files from action-effect-history v1 by the same counted-substitution pattern.
   - The model host must serve and audit reflection requests (`max_tokens` 400, no response format) beside policy
     requests.
   - Its call ceilings come from `closed_loop/protocol.json` (1,080 policy, 64 reflection).
3. **Tokenizer counts.** Replace the 4-characters-per-token admission estimate with serving-tokenizer counts for
   reflection admission in live mode.
4. **Live evaluator.** An independent evaluator that rebuilds transition_evidence_v2 records from run evidence and
   computes §8 with `outcomes.py`, with a replay test. It also needs the audit sampling script.
5. **Pre-run timing check** on the target CPU for per-step overhead at 40 actions. If it exceeds 6.1 s per step, the
   reservations above are recomputed before freezing. The horizon is not cut.
6. **Review of placement and limits.** The suggestion-block placement, label and lifetime, the reflection request
   settings, and the window and quiet lengths (10/5).
7. **Governance.** A named auditor, then source approval, compute authorization and reservation records, by humans.
8. **Package build.** A fresh-checkout package build and the review lock.

## 13. Open questions

1. **Tier B.** Accept ls20 despite the post-hoc finding, or approve an amended, separately committed criterion? For
   example, "novelty must persist when the cells changed on every step are ignored". Such a criterion uses a
   per-episode description, not a detector mask.
2. **Two sessions.** Is the split with the stated reservations acceptable, or should one longer session be
   requested?
3. **Window lengths.** Are 10 actions (window) and 5 (quiet period) acceptable for behavioural recovery, given the
   40-action horizon and the last reflection at action 29?
4. **Auditor.** Who is the blinded auditor?
5. **Repeat episodes.** Is one continuation repeat per primary game enough for the variance check?
