# Track 3 stagnation supervision v1: results (sanitized)

**Verdict: inconclusive.** The frozen §8.6 rule could not return anything else, because the false-interruption gate
is not certifiable with one qualified control game (§8.3). Beyond the rule, the evidence does not show that
detector-triggered reflection helps the agent leave loops:
- **Recovery.** Across 15 recovery opportunities in distinct trajectories, there were two recoveries, one in each
  reflection arm. The self-review judged the triggered arm's recovery to be an artefact of a display counter.
- **Levels.** No arm completed a level in any game.

**Scope.** These are development games with prior model exposure and one model (Qwen3-VL-30B-A3B FP8, temperature 0,
seed 0). The results are not real-game or generalisation evidence. The notebook, raw outputs, self-review sample and
annotations stay private. This summary is sanitized.

## What ran

| Session | Content | Status |
|---|---|---|
| 1 (attempt 3; attempts 1-2 failed before readiness) | block 1 (4 games × 3 arms) + 3 continuation repeats, 600 actions | technically complete, accepted |
| 2 | block 2 (4 games × 3 arms), 480 actions | technically complete, accepted |

**Amendment S2** was decided on October 12, 2026, before any outcome was inspected. The trigger was that block 2
replayed block 1 exactly: the same requests, responses and reflections. Serving was deterministic, so the 24 block
episodes are 12 distinct trajectories, and the 3 repeats are further copies.
- **Headline.** The distinct-trajectory analysis is the interpretive headline.
- **Frozen analysis.** It is reported as written, but it overstates precision.

The pooled evaluation passed every binding check:
- both session records were recomputed under private lock r15;
- the session-2 execution lock binds the launch-time session-1 record, which equals the r15 re-evaluation apart from
  the lock;
- the self-review annotations were committed privately (`de1abfe4…`) before the comparison.

The retained private record is `pooled_evaluation.json`, SHA-256 `47fd9d07…`.

## Primary endpoint: behavioural recovery (ar25, wa30, ls20)

The headline below counts distinct trajectories, one episode per game and arm. Rate = recovered / (recovered +
not recovered).

| Arm | Episodes | Opportunities | Recovered / decided | Rate | Wilson 95% | Episode bootstrap 95% |
|---|---|---|---|---|---|---|
| continuation | 3 | 4 | 0 / 4 | 0.00 | 0.00–0.49 | 0.00–0.00 |
| periodic | 3 | 6 | 1 / 6 | 0.17 | 0.03–0.56 | 0.00–1.00 |
| triggered | 3 | 5 | 1 / 5 | 0.20 | 0.04–0.62 | 0.00–0.50 |

**Point differences (descriptive).** Triggered − continuation +0.20; triggered − periodic +0.03; periodic −
continuation +0.17.

Each nonzero rate rests on a single event. Every interval spans most of the range, and with one trajectory per game
and arm the intervals reflect variation between games only. **Horizon censoring.** Detector firings too late for a
full recovery window: continuation 7, periodic 10, triggered 6.

**By game** (distinct trajectories):

| Game | continuation | periodic | triggered |
|---|---|---|---|
| ar25 (stagnation case) | 0 / 3 | 0 / 3 | 0 / 3 |
| wa30 | 0 / 1 | 0 / 2 | 1 / 2 |
| ls20 (exploratory) | no opportunity | 1 / 1 | no opportunity |
| s5i5 (declared blind spot; never pooled) | 0 / 1 | 0 / 1 | 0 / 1 |

**The two recoveries, as the self-review saw them:**
- **Periodic, ls20, genuine.** After 14 consecutive blocked presses, the agent moved onto a marked tile, which changed
  a status icon, and then on to new positions. The exit action was the first action of the reflection's suggested test.
- **Triggered, wa30, an artefact.** The "exit" was the same blocked press as before. It stopped matching the stalled
  pattern only because wa30's move counter had changed the frame fingerprint. The agent then reached one new position
  and settled into a two-position up/down oscillation.

**Frozen analysis (24 episodes, labelled as overstating precision).** The same rates appear with doubled counts:
0/8, 2/12 and 2/10. Each copy counts as an independent episode, so the intervals are narrower than the evidence
supports. The §8.6 conditions came out as follows:

| Condition | Result | Note |
|---|---|---|
| Against periodic in the stagnation case, both blocks | false | ar25 is 0/3 in every arm |
| Against continuation | true | |
| False interruptions within cap | false | not certifiable |
| No regressions | true | |
| Beyond repeat-episode variance | true | trivially: the variance is zero because decoding is deterministic |

## Secondary measures

| Measure | Result |
|---|---|
| Completed levels | 0 in every arm and game |
| False interruptions (triggered arm, wa30 only, provisional gate) | 2 of 36 LC points (5.6%), Wilson upper 18.1%; **not certifiable** (one qualified control game; minimum not met) |
| Suggestion following (§8.1, descriptive) | periodic: the one recovered exit equalled the suggested test's first action; triggered: it did not |
| Reliability | 0 failed or unknown dispatches; 0 invalid policy outputs; 0 invalid or failed reflections (9 periodic, 6 triggered in distinct primary-game trajectories) |
| Cost (both sessions) | 1,080 policy calls, 40 reflections, 2 canaries; reflection tokens per session 26,788 prompt + 4,481 completion; the triggered arm used about 0.64 of the periodic arm's reflection tokens |
| Reproducibility | every block-2 episode and every repeat replayed its original exactly; run-to-run variance zero |

## Self-review (amendment S1, drawn under S2; descriptive only)

**Annotator.** Claude, the AI agent that designed and operated the study, by owner decision. The review is unblinded
and not independent; it does not certify labels, and labels were not changed.

**Sample.** 103 items. The quotas were short wherever the distinct trajectories had fewer candidates: gate-eligible
IND, ls20 IND, reflections and recoveries.

| Stratum | Answers |
|---|---|
| Labels, gate-eligible (wa30 LC, ar25 ST, IND) | 41 agree, 4 disagree, 1 unclear: disagreement 8.9% (below the descriptive 20% line) |
| Labels, ls20 | 39 agree, 0 disagree, 1 unclear |
| Reflections, periodic (9) | cites available evidence 7 yes / 2 unclear; turns uncertainty into fact 2 yes; test can distinguish explanations 5 yes / 2 no / 2 unclear |
| Reflections, triggered (6) | cites available evidence 6 yes; turns uncertainty into fact 0; test can distinguish explanations 4 yes / 1 no / 1 unclear |
| Recoveries (2) | more than a changed action: 1 yes, 1 no |

**What the review found:**
- **wa30 has display-driven novelty too.** Its bottom-row move counter makes frames "new" while the player oscillates
  between two positions. All four label disagreements are wa30 LC points of this kind, and so is the triggered arm's
  only recovery. Until now the protocol recorded this limitation for ls20 only.
  - It inflates wa30's LC counts, which are the denominator of the false-interruption measure.
  - It lets an unchanged blocked action count as a loop exit.
- **ar25 was stuck from the first action in every arm.** None of its 40 steps changed a cell in any arm.
  - Every action was a click: 3 distinct coordinates in continuation, 4 in periodic and 7 in triggered.
  - The reflections described the stall correctly, but every test they proposed was another click. No policy step or
    reflection tried any of the six other available actions.
- **Reflection quality.** Reflections mostly cited real evidence. Two periodic reflections stated over-general rules
  that their own cited records contradicted. Several proposed tests repeated the stuck behaviour or tested what the
  evidence had already settled.

## What this does and does not show

- **Does not show** that detector-triggered reflection improves loop recovery over periodic reflection or no
  reflection. The one triggered recovery is an artefact, and the counts are single events.
- **Does not show** that it harms. The false-interruption measure is not certifiable, and it is distorted by wa30's
  counter.
- **Does show,** for this model and these games:
  - the runtime, supervision and evaluation chain works end to end under its limits;
  - reflections are cheap and reliable (no invalid outputs);
  - neither reflection arm turned stalled play into level progress;
  - deterministic serving makes repeated blocks uninformative.

**Not authorized here; each would need a new protocol.** Any follow-up would need:
- detector, label and recovery rules that mask display regions (move counters, timers);
- variation that produces distinct trajectories (for example, different game seeds rather than repeated blocks);
- more than one qualified continuation control.
