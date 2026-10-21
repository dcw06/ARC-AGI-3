# ls20 level 1 with supplied controls and rules

**Question:** Can the existing Qwen VLM complete the first level when it is told
what the controls and puzzle rules mean, but must choose every move itself?

This is one instructed development-game pilot, not a test of discovering unknown
rules. The board and rules have already been exposed during development. There
is no uninstructed comparison arm or generalization claim.

| Item | Frozen choice |
| --- | --- |
| Model | Qwen3-VL-30B-A3B-Instruct-FP8, existing pinned runtime |
| Game | `ls20-9607627b`, seed 0, first level only |
| Images | Current board, initial board and at most two observed transitions; each 448 × 448 |
| Supplied information | Directional control meanings, visible object roles, rotation rule and completion goal |
| Agent's responsibility | Locate the pieces and corridors, plan the route, choose moves, check their effects |
| Excluded information | Solved move sequence, coordinate masks, future observations and replay answers |
| Success | Engine completed-level counter rises from 0 to at least 1, confirmed by independent replay |
| Stop | First completed level, game over, 40 moves, invalid answer or deadline |

The private inputs contain only the initial observation, the frozen instruction
text and their manifest. The public protocol pins both input identities. Updating
the prompt requires a new input manifest and review lock.

The policy can select any of the four directional actions. It receives actual
before/after observations and its own previous actions. It emits one strict JSON
action, without coordinates or a batch. There is no retry or repair of an invalid
answer, and no next-level move after completion.

`flow.py` records all requests, replies and engine transitions. `audit.py`
reconstructs the full requests and independently replays every action. The live
evaluator additionally requires the reviewed source, token audit, cleanup evidence,
finalization witness and exact version-bound Kaggle completion record. An image
that appears solved or a model's success statement cannot pass the test.

The package and lifecycle are derived from the corrected verified-feedback
runner. `python scripts/derive_ls20_instruction_v1.py --check` checks the five
derived files against their pinned parents. `python -m unittest
tests.test_ls20_instruction_v1` exercises the new episode and replay contracts
without inference or provider calls.

| Proposed live ceiling | Limit |
| --- | --- |
| GPU | Exactly one RTX PRO 6000 |
| Kaggle session timeout requested | 3,600 s; provider overhead can extend total time |
| Worker / new-work cutoff / cleanup reserve | 3,300 / 3,000 / 300 s |
| Generations and counted model HTTP requests | 41: one canary and up to 40 policy replies |
| New tokens | 256 per policy reply; 16 for the canary |
| Offline engine actions | 41: one initial reset and up to 40 moves |
| Local scorecards | One |
| Online game calls and submissions | Zero |
| Attempts / automatic retries | One / zero |
| Access | Private, account-only; internet and TPU off |

Preparation grants no compute authority. The review notebook refuses before
installation or GPU use. Source approval, scoped use, compute authorization,
fresh preflight and a single-use reservation/claim must bind the final private
review lock before a submission.
