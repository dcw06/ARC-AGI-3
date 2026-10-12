# Track 3 session 2: technical summary (sanitized)

**What this is.** The sanitized technical summary of session 2. The notebook and raw outputs stay private and
account-only. Outcome endpoints are not reported here: the protocol's comparisons pool both sessions and require the
amendment-S1 self-review to be drawn, annotated and committed first (frozen protocol §7, §8).

## Attempt

| Item | Value |
|---|---|
| Attempt | `ssv1rt2-s2-6934018b…`, version 1 of the new private session-2 notebook (one push, verified) |
| Package | private r14 (public review r11, lock `ce6c7e10…`), verified in full before the push (`19a30f0`) |
| Owner decisions (October 12) | Gate 4 (reusing the session-1 notebook's version-1 Quick Save as attachment evidence only); source, launching only after that verification passed; compute for session 2, bound to the accepted session-1 evaluation `29001aa9…`; launch |
| Provider status | submitted 18:01, RUNNING 18:03, COMPLETE 18:55 UTC (no queue) |
| Hardware | one RTX PRO 6000, bound by the monitor before the worker was released |
| First-cell lifecycle | 1,533.5 s (authorized 4,800 s; internal deadline 4,500 s) |
| Installation | 204.7 s (window 450 s) |
| Model startup | 503.9 s (ceiling 900 s); model tree re-verified (20 files) |
| Monitor readiness | worker released at 206.1 s; the bounded `/proc` probes sampled throughout and the monitor completed |
| Study work | 820 s for 480 actions (about 1.7 s per step, reflections included); all 4 game groups complete |
| Model requests | 480 policy calls + 20 reflections + 1 canary = 501 (ceilings 480 / 32 / 1) |
| Game actions | 480 on the local offline engine (12 episodes × 40); 0 dispatch failures; 0 online game calls or scorecards |
| Reflections | 12 periodic and 8 triggered, all valid; none failed |
| Tokens | policy 11,994,161 prompt + 12,463 completion; reflections 26,788 prompt + 4,481 completion |
| Failure rules | none fired; the reflection interface was never stopped |
| Cleanup | process groups absent with child ownership verified; independent GPU cleanup found 0 GPU processes; scratch removed; fail-closed finalization certified with the extracted source removed |

**Platform time outside the notebook.** The notebook's own log spans about 1,550 s, but the provider reported the run
for about 52 minutes. The other ~26 minutes passed before or after the notebook ran, outside its control; their cause
is unknown (session 1 showed almost none). The provider's session limit counts that time. The margin here was about
1,670 s under the 4,800-s limit. The internal deadline counts from the first cell, so it does not protect against
platform delay.

## Independent live evaluation

| Item | Value |
|---|---|
| Technically complete / target accepted / lifecycle verified | yes / yes / yes; 0 problems |
| Evaluating checkout's review lock | verified (private r14, the same lock as session 1's re-evaluation) |
| Retained record | `reports/stagnation_supervision_runtime_v2_results/session2_evaluation.json` in the private checkout, SHA-256 `f4f0b49e67cabb7b8f1629c4e235fc353e48b9610d1cad919c368207e3664257` |

## Reproducibility finding (hashes only; no outcome was computed or inspected)

Every block-2 episode exactly replays its block-1 counterpart, for all 12 game-and-arm pairs:
- the same policy request and response at each of the 40 steps;
- the same reflection responses;
- identical reflection cost, including the triggered calls per game.

Session 1's three continuation repeats likewise replay block 1 exactly.

**Why.** The frozen design (§5) fixes game seed 0, request seed 0 and temperature 0 for both blocks, and only arm order
rotates. Each episode runs in its own context, so arm order cannot change an episode, and serving proved deterministic.
- **Run-to-run variance is zero** on this target.
- **Block 2 adds no new trajectories.** The 24 block episodes are 12 distinct trajectories, each run twice, plus three
  further copies from the repeats.

**Consequence for the pooled analysis.** The frozen analysis treats each episode as an independent cluster for the
bootstrap. Applied as written, it would count every trajectory twice and report intervals narrower than the evidence
supports.
- This finding was recorded before any outcome was computed.
- How to handle it is an owner decision, taken before the self-review and the pooled evaluation. No analysis change
  has been made.

## What follows

Next come the amendment-S1 self-review draw, the owner's annotations and their private commitment, and then the pooled
two-session evaluation. No further session or GPU run is authorized.
