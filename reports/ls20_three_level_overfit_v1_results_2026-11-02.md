# ls20: the fitted agent completes the first three levels

**All three requested levels passed on the real offline engine.** The new policy
was fitted to the owner's earlier successful demonstration, then executed from
a fresh level-1 start. A second fresh engine reproduced every observation and
action. Success comes from the engine's completed-level counter reaching three.

| Level | Moves | Cumulative moves | Result |
| --- | ---: | ---: | --- |
| 1 | 16 | 16 | Passed |
| 2 | 92 | 108 | Passed |
| 3 | 43 | 151 | Passed |

## What changed

The earlier DFS controller stalled in level 2. This version deliberately
memorizes the first 151 moves of the owner's successful play, retaining the
detours and timer-dependent transitions. It checks the complete board before
each move and checks the resulting observation before selecting another.
It does not issue reset actions or improvise after a mismatch.

This meets the narrow three-level objective through **demonstration imitation**.
It is not VLM weight training, autonomous rule learning, a general ls20 solver,
or evidence of transfer to another game or seed. The policy is specific to
`ls20-9607627b`, seed 0, with the retained starting observation. Exact matching
includes the yellow bar and other interface pixels.

The committed fitted policy is approximately 48 KB. It can be used without the
raw human log. The original general agent, earlier controllers, GPU attempts and
private evidence remain unchanged. No competition notebook or submission was
modified by this work.

## Verification

| Check | Result |
| --- | --- |
| Windows and Linux policy regressions | 17 tests passed on each, zero failures or skips |
| Compiled policy reproducibility | Byte-identical hash from the retained human demonstration |
| Live study | 151 directional actions; engine completed-level counter reached 3 |
| Fresh-engine reconstruction | Another 151 actions; all 309 journal events matched |
| Separate read-only audit | Checked all 151 before/action/after records, legal actions, counters and hashes |
| Per-episode reset and scorecard | One initial reset, one closed local scorecard; no in-episode reset action |
| Total engine actions | 302 directional actions plus two initial resets across study and reconstruction |
| Bounded CPU lifecycle | 73.81 seconds within 600 seconds; registered owned group absent after exit |
| Source integrity | All 30 executed repository source hashes verified |
| New model generations / GPU jobs / online calls / provider writes | 0 / 0 / 0 / 0 |
| Automatic retries | None |

The demonstration was recorded with `arc-agi 0.9.9`; this CPU environment has
`arc-agi 0.9.8`. Both use `arcengine 0.9.3`. Despite that SDK difference, every
normalized observation matched exactly, including the final frame after each
action. The check uses final board frames, not all intermediate animation frames.

One preliminary invocation refused an unfilled policy-hash argument before
creating an attempt directory or starting the engine. It performed zero game
actions. The subsequent actual study and its explicitly counted reconstruction
both passed; no failed episode was discarded or relabelled.

## Files and limits

- [Integration and reproduction guide](../research/ls20_overfit_v1/README.md)
- [Fitted policy](../research/ls20_overfit_v1/policy_seed0.json)
- [Policy implementation and compiler](../research/ls20_overfit_v1/policy.py)
- [CPU runner](../scripts/run_ls20_overfit_v1.py)
- [Regression tests](../tests/test_ls20_overfit_v1.py)
- [Aggregate engine results](ls20_three_level_overfit_v1_results_2026-11-02.json)

Raw human logs, new engine journals, process logs and private local paths remain
local. The derived policy and aggregate results contain no credentials or
provider/account records. This is a CPU-tested specialization; it has not been
deployed to Kaggle or evaluated for a competition score.

The local visual replay has 152 frames and three per-level GIFs, generated from
the new engine run. The last frame shows the next board appearing after the
third completion; the agent stops there.

| Retained binding | SHA256 |
| --- | --- |
| Source human demonstration | `5539aa3e36626bcbefa4c4b09e9435dc5b8df3d1ef552d88d141e971f1e9bb9f` |
| Fitted policy | `d70c8ff61040d49405f95ef5d56e17f1634ac51695c97e01b2f7f5a92c35b2cd` |
| Engine results | `df0f1b2bd7ac1e5392562b4d94af48fca00f3ef06b05698a85675e24abfcc1a0` |
| Study and reconstruction journal (each) | `ee102aa978c144e633641349e4b84bc2b14229d5d861cccfa6a6a457137fcc9f` |
| Executed source manifest | `c09097c74e0afba79a547fd99a0fd36ca0704533d6a8455cba2f29845ed521af` |
