# ls20 level 1 with supplied rules and an evidence memory

**Question:** with the instructed pilot's supplied controls and rules, can the
existing Qwen VLM complete exposed ls20 level 1 within 40 moves when every request
also carries a computed evidence-memory block?

This is one exposed development-game pilot. The instructed pilot's attempt 1 used
the same model, settings, board, instructions and move cap without the block, and
completed no level in 40 moves. That run is a descriptive reference, not a
concurrent control: one episode cannot attribute a difference to the block.

| Item | Frozen choice |
| --- | --- |
| Model | Qwen3-VL-30B-A3B-Instruct-FP8, existing pinned runtime |
| Game | `ls20-9607627b`, seed 0, first level only |
| Request | The instructed pilot's request, byte for byte, plus one text item inserted third |
| Evidence block | Rebuilt each step by `research/ls20_discovery_mac` (commit `f4bf522`) from the initial board and observed transitions |
| Block contents | Current same-colour region proposals, the last six transitions' changed-cell counts and moved regions, per-action tallies, and the current run of moves with no moved region |
| Excluded information | Solved route, object labels or roles, coordinate masks, future observations and replay answers |
| Success | Engine completed-level counter rises from 0 to at least 1, confirmed by independent replay |
| Stop | First completed level, game over, 40 moves, invalid answer or deadline |

A moved region is the memory's tentative match between consecutive frames in which
both copies contain changed cells. It is not a verified object, role or cause. On
ls20 the player's two colour parts appear as two regions, so one move can add two
displacement counts. The block is a pure function of the observed history, so the
independent evaluator rebuilds every request exactly. Rebuilding the memory each
step costs up to a few CPU seconds per request inside the admission window.

The lifecycle, package, operator and evaluator are derived from the instructed
pilot: `python scripts/derive_ls20_memory_evidence_v1.py --check` checks the eleven
derived files against their pinned parents. `tests/test_ls20_memory_evidence_policy_v1.py`
covers the block; the derived `tests/test_ls20_memory_evidence_v1.py` covers the
episode, inputs, worker and replay contracts. Neither makes model or provider calls.

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
