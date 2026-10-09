# Track 3: two questions for the owner and reviewer

**Status.** This is an analysis with options and recommendations. It decides nothing and changes no frozen element. The
protocol v2 science stays as frozen: games, horizon, arms, no-restart rule, trigger, prompts, labels, windows, gate,
caps and stop rules. Every number below comes from CPU-only, retained, reproducible sources:
- `reports/stagnation_supervision_runtime_v2_detector_verification.json` (frozen detector, fixtures, the archived
  action-effect-history v1 play, and ls20 on the offline engine under three fixed scripted policies);
- the staged session-1 rehearsal receipt (scripted model, so its behaviour is not model evidence).

## Question 1: do the selected continuation controls support the proposed false-interruption claim?

**The claim (protocol v2 §8.3 and §8.6).**
- **Measured quantity.** Triggered-arm detector triggers at legitimate-continuation (LC) points, divided by LC points.
- **Pass condition.** The 95% upper bound must be at most 10%, with at least 60 LC points from at least 2
  continuation-appropriate games and at least 4 episodes.
- **Advancement.** This is one of the advancement conditions.

**What the frozen code already does.** `outcomes.interruptions` (R2) admits only `wa30` as a gate control and treats
`ls20` as exploratory. With one eligible game, the minimum of 2 games is unmet, so the gate returns
`not_certifiable_minimum_not_met` by construction. The staged rehearsal shows this end to end: the triggered arm had 2
interruptions in 40 wa30 LC points and was not certifiable; the descriptive all-cases rate was 6 in 108. Those are
scripted-policy numbers, used only to show the plumbing.

**Evidence about the two controls.**

| Control | What the CPU evidence shows | Supports the claim? |
|---|---|---|
| wa30 (Tier A) | Archived real play: 48/48 points LC, 1 trigger in 48 steps, and that trigger fell at an LC point (`b2-wa30-baseline@7`). The trigger is a repeated action after a 0-cell step; the block had moved 28 cells two steps earlier. The mechanical LC rule counts it as a false interruption, although a human would plausibly call it a wall bump | Partly. It is a genuine continuation-appropriate game, but it is one game, and the LC rule can label a correct stagnation trigger as a false interruption |
| ls20 (Tier B, retained with limitation) | Offline engine, 40 actions: oscillating policies (`1,2,...` and `1,2,3,4,...`) make 40/40 full frames new but only 1-2 playfield frames new (38-39 revisits). LC labels cover 40/40 points, and the detector fired **0** times. A blocked repeat (`1,1,...`) repeats the whole frame, and the detector fires (triggers at 7, 13, ..., 37). Staged rehearsal: arms that rotate actions show 32-37 of 40 points LC with 24-28 playfield revisits | No. The detector cannot see ls20 oscillation, so ls20 LC points would lower the false-interruption rate by construction. Its LC points measure the moving display, not useful continuation (the retained limitation, now quantified) |

**Why the minimum cannot be met honestly.**
- With wa30 alone the claim fails the 2-game minimum.
- Adding ls20 would meet the count but with points that cannot show the property in question. Under oscillation, a
  near-zero ls20 rate is guaranteed by display-driven novelty.
- 60 LC points from about 4 wa30 episodes would be heavily correlated, and the protocol already says mechanical labels on a
  few episodes do not establish harm.

**Options for the owner.**
1. **Keep the frozen design (no change).**
   - The gate is reported as *not certifiable*, with the wa30-only point estimate, both intervals and the descriptive
     all-cases rate, and with the ls20 display/oscillation report alongside.
   - Triggered cannot advance under §8.6, so the expected default result, *inconclusive*, holds.
   - Cost: none. Claim strength: none on false interruptions.
2. **Narrow the claim (protocol amendment, wording only).**
   - Replace the gate with a descriptive "wa30-only false-interruption estimate" and drop it from the advancement rule.
   - Cost: amendment review. This changes §8.6, so it is not runtime work.
3. **Add a second qualified control (protocol amendment plus a new CPU probe).**
   - Probe the remaining written candidates (`tr87`, `g50t`) under a display-robust criterion fixed before probing. For
     example, require novelty above a frozen display region, or a declared region in transition_evidence_v2.
   - Admit a control only if it qualifies.
   - Cost: a new pre-registered probe and selection decision, and a source review. It stays exposed-development evidence.
4. **Human adjudication of LC triggers (protocol amendment).**
   - The blinded auditor adjudicates every triggered-arm trigger at an LC point, not a sample, before unblinding.
   - This addresses the wa30 wall-bump mislabel. It changes the gate from mechanical to adjudicated.

**Recommendation (not a decision).**
- Run under option 1, and report the false-interruption result as not certifiable.
- If the owner wants a certifiable claim later, pre-register option 3, and option 4 if wanted, as a separate amendment
  before any run that would use it.
- Do not count ls20 toward the gate under any option without a display-robust qualification. The retention decision
  allows its reporting, not its certification.

## Question 2: the reflection's placement and the auditor's role

**Placement as frozen and implemented (protocol v2 §2.1; `closed_loop/contract.py`, `bridge.py`, `supervision.py`).**
- **Where it goes.** A validated reflection is rendered into a fixed four-field block under the top-level
  `model_generated_suggestion` key, beside the `observation` in the same JSON user message. It is never placed inside the
  observation.
- **Label.** "MODEL-GENERATED SUGGESTION (a hypothesis from a reviewer model, not an observation)".
- **Lifetime.** 10 policy requests. Only a later valid reflection replaces it; reset, level change or a terminal state
  clears it. The limit is 1,600 characters.
- **Same template in both reflection arms.** One sentence in the shared system prompt describes the block in every arm.
- **Tested equivalence.** `strip_suggestion(request)` equals the continuation request.
- **Token audit.** The policy maximum is 26,010 prompt tokens, against a 60,000 ceiling.

The CPU verification confirms the placement mechanics:
- No reflection at a terminal state, at a reset or level change, after action index 29, or with an unobserved state.
- Failed and `length`-finished reflections are charged and invalid and deliver nothing.
- Only a later valid reflection delivers.
- Every decision is causal (prefix replays over all 152 fixture trajectories).

**Observations relevant to the owner's choice.**
1. **Lifetime equals the recovery window.**
   - A triggered reflection is issued at the opportunity step and is therefore shown throughout the window t+1..t+10.
     Periodic reflections (after actions 10, 20 and 30) fall in windows only by chance.
   - That is the intended timing contrast. It also means behavioural recovery in the triggered arm partly measures
     *following the suggested distinguishing test*. The test's actions are, by construction, different from the cited
     pattern, so taking one is an exit.
   - The protocol does not separate "exit by following the suggestion" from "exit by other means".
2. **Placement in the user message.**
   - The block shares the message with the factual observation. The label and the system-prompt sentence mark it as a
     hypothesis, but the model reads both together.
   - The control-interface probes showed that this model is strongly sensitive to prompt structure (v1 reference
     validity 36.7%; v2 with a shared explicit contract 100%). Placement is therefore consequential. This runtime
     successor deliberately does not adopt the probes' output template or computed control metadata.
3. **Equal budget is not equal cost.** The arms share caps, but realised calls and tokens differ (§8.4). The staged
   rehearsal, with a scripted model, already shows this: periodic 12 calls / 16,164 tokens, triggered 9 / 10,844.

**Placement options (each is an amendment except the first).**
- **P1.** Keep as frozen.
- **P2.** Keep the placement, and add a descriptive secondary measure: the share of exits whose exit action equals the
  suggestion's first test action, per arm.
- **P3.** Shorten the lifetime to fewer requests than the window, to reduce the coupling.
- **P4.** Move the block to its own labelled user message.

**Recommendation (not a decision).** P1 for this study, adding P2 only if the owner pre-registers it before the run as
descriptive. P3 and P4 change the treatment and belong in a successor protocol.

**The auditor (protocol v2 §7; open question §13 Q4).**
- **Role as written.** A teammate who did not design the detector audits 60 seeded, stratified decision points (20 per
  label). They see frames and actions only, blind to arm, trigger and outcome. If more than 20% of non-unclear points
  disagree, the gate becomes "not certifiable: reference labels unreliable".
- **Not yet chosen:** who the auditor is, which games the strata draw from, and whether the audit happens before
  outcomes are computed.

**What the evidence implies.**
- **ls20 LC points.** Under oscillation, ls20 LC points are display-driven. An auditor looking at frames would likely
  call many of them stagnant. If the LC stratum includes ls20, disagreement will probably exceed 20% and invalidate the
  labels for reasons already known.
- **wa30 wall bumps.** The wa30 wall-bump case is an LC point a human may call stagnant.
- **Blinding.** Frames from reflection arms can reveal the arm, for example through test-action patterns, so blinding to
  arm is imperfect.

**Options for the auditor's role.**
- **A1.** Label-quality auditor only, as written. The strata draw from gate-eligible games only (wa30 for LC, ar25 for
  ST), with ls20 audited and reported separately as descriptive.
- **A2.** As A1, plus full adjudication of LC triggers (this is Question 1, option 4).
- **A3.** As A1, plus a quality check of delivered reflections for leakage and solution claims. This affects no outcome.
- **For every option.** Fix the auditor's name, the sample seed and the strata before the run. Audit before comparative
  outcomes are computed.

**Recommendation (not a decision).** A1, with A3 as an optional secondary check. The auditor and the strata must be named
in a pre-run record by the owner. This analysis does not name anyone.
