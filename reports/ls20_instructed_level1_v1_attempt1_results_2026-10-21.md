# ls20 level 1 with explicit rules: attempt 1

**The run was technically complete, but the agent did not complete level 1.**
With controls and puzzle rules supplied, Qwen used all 40 allowed moves and
finished with zero completed levels. Independent offline replay reproduced
every action and observation. This first-level capability gate remains unmet
for this pilot.

## Result and validation

| Measure | Result |
| --- | --- |
| Game and scope | ls20 level 1, seed 0; one exposed development-game episode |
| Model | Existing pinned Qwen3-VL-30B-A3B-Instruct-FP8 runtime |
| Hardware | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Provider status | COMPLETE, version 1; one submission, no retry |
| Independent technical evaluation | Complete; lifecycle certified |
| Level 1 passed | **No; completed-level counter remained 0** |
| Policy replies | 40/40 valid |
| Stop reason | 40-move action cap |
| Model requests | 41: one canary and 40 policy replies |
| Offline engine actions | 41: one reset and 40 moves |
| Local scorecards | One, closed |
| Online game calls and submissions | Zero |
| Runtime | 1,523.2 s, about 25 min 23 s; below the 3,300 s worker limit |
| Prompt / completion tokens | 84,791 / 842 |
| Largest native prompt | 2,386 tokens; below 8,192 |
| Longest completion | 21 tokens; policy allowance was 256 |
| Token truncation | None; all 41 generations ended normally |
| Cleanup | Verified; zero GPU processes, owned groups absent, temporary environment and source removed |

The episode stopped because it used its move allowance, rather than because it
ran out of generation tokens or reached its deadline.

## What the agent actually did

The agent repeatedly chose **right → up → left**, continuing that three-action
pattern throughout the episode. It initially moved upward through the board.
Once upward movement stopped at an obstruction, it kept moving back and forth
and attempting the same blocked direction.

| Observed behavior | Retained evidence |
| --- | --- |
| Repeated action pattern | Every move follows the same right/up/left cycle |
| Orange player-region positions | 10 distinct positions, including the initial one |
| Moves without orange-region movement | 9 of 40 |
| Lower-left reference pattern | Unchanged throughout all 40 moves |
| Level completion | No completed-level increase |

Position tracking above is deterministic analysis of the retained orange pixels,
using the known player marker for this board. These positions were **not**
supplied to the policy, and they do not measure the model's object-recognition
accuracy.

The agent received the directional control meanings, the visible object roles,
the cross-rotation rule and the pattern-matching goal. It received current and
historical images and its own executed actions. It received **no solved route,
coordinate masks or future observations**, and it could choose any of the four
directional actions.

## What this establishes

**Those instructions were insufficient for first-level completion in this
episode.** They did not prevent the repeated movement cycle. The earlier
CPU-only positive control reproduced a 16-move human solution, so the 40-move
allowance contains a known solution; that does not show the VLM could find it.

This is one instructed episode without an uninstructed comparison arm. It does
not measure how much the instructions helped or harmed, establish that the model
cannot solve ls20, or isolate perception, rule interpretation, route planning or
use of history as the cause. The compact action replies contain no explanation
of the model's choices.

A useful next diagnostic would test those abilities separately at retained
checkpoints: locating the player/cross/goal, identifying available movement, and
choosing a short route toward the required interaction. That is a proposal, not
authorization for another model run.

## Evidence and attempt status

| Binding | Value |
| --- | --- |
| Executed source commit | `086bba44c486066f6b069d876534bd535e1740d5` |
| Review lock SHA256 | `25f3a023249f5a880628069ba07ae67fda36392661a756a259b7c7ec3dea2fa3` |
| Independent evaluation SHA256 | `f7ad28579482187bdc4abf1457a966793e1c411a46104ee6bee82cb208d2ed10` |
| Evaluated run-evidence inventory SHA256 | `5a2a782d640bba82a9e570f6e7bf6925733117a18efd6e536f0f3ea8d269195f` |
| Original collected files | All 13 verified unchanged; all 11 runtime-manifest members verified |
| Independent replay | One fresh reset, all 40 moves, one closed scorecard; no model inference |
| Native-token audit | All 41 request counts reproduced using the pinned processor |
| Earlier retained files | 696 checked unchanged |
| Post-run provider writes / GPU launches | Zero / zero |

The single authorized attempt is consumed and preserved. No retry or new GPU job
was started. Raw outputs, approval records, private bindings and the visual
replay remain in the ignored local workspace; this report contains summaries
only.

[Preparation, protocol and launch checks](ls20_instructed_level1_v1_preparation_2026-10-21.md).
