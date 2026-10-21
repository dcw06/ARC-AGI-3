# ls20: left three times, then up three times

**Question:** Can the existing Qwen VLM execute an explicitly supplied six-move
instruction and move the player accordingly?

The whole instruction is repeated unchanged on every request:
**left, left, left, up, up, up**. Control meanings are supplied: action 3 is left
and action 1 is up. The model receives the initial/current images, two recent
transitions and its executed-action history. The runner does not supply a
step-specific answer, correct mistakes, replay a scripted action instead of the
model's reply, or extend the episode to recover from deviations.

All four legal directional actions remain available. A wrong but legal action
is executed and retained. The run stops after six moves, an invalid reply, a
terminal game state or a deadline. There is no seventh move or automatic retry.

| Measure | Rule |
| --- | --- |
| Command following | Exactly six actions: `3, 3, 3, 1, 1, 1` |
| Execution match | Correct actions plus every replayed after-state matching its separately frozen reference hash |
| Technical validity | Exact request/token audit, fresh engine replay and certified lifecycle |
| Level completion | Reported separately; these six moves are not a complete solution |

The reference state hashes are bound by `live_protocol.json`. Reference images,
demonstration logs and coordinate masks are absent from the inference inputs.
The model sees the explicitly requested route, not future frames.

This is a sequence-following and control-execution probe. It does not establish
autonomous route planning, rule discovery or first-level solving. Because all
six actions are supplied, a model could pass without reading the images; passing
would not establish object recognition or visual grounding. Previous runs and
their source files remain unchanged.

The same pinned Qwen runtime, immutable image, wheel checks and bounded lifecycle
are retained. Proposed ceilings: one RTX PRO 6000, requested session timeout
3,600 s, worker 3,300 s, seven generations/model HTTP requests (one canary and
six policy replies), seven offline actions including the initial reset, and one
local scorecard. Policy replies allow at most 256 new tokens; the canary allows
16. No online game calls, submissions or retries; private account-only access,
internet and TPU off. Provider overhead may extend total time beyond one hour.

The review notebook refuses without fresh lock-bound source/use approval and
compute authorization. Preparation and CPU-scripted controls grant no launch
authority. Check derivation with `python scripts/derive_ls20_six_move_v1.py
--check`; exercise the new contracts with `python -m unittest
tests.test_ls20_six_move_v1`.
