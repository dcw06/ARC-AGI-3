# ls20 explicit six-move VLM probe: preparation

**Prepared and CPU-validated; no new model inference or GPU launch.**

The user requested: **move left three times, then up three times**. The exact
requested action sequence is `3, 3, 3, 1, 1, 1` (left is action 3; up is action 1).

| Design | Choice |
| --- | --- |
| Model / board | Existing pinned Qwen VLM, same ls20 level-1 starting board and seed 0 |
| Whole instruction | LEFT, LEFT, LEFT, UP, UP, UP; repeated unchanged on each request |
| Model inputs | Control meanings, initial/current images, two recent transitions, executed-action history |
| Runner behavior | Dispatch the model's actual legal action, including a wrong one; no correction, forced route or per-step desired answer |
| Stop | Six moves, invalid answer, terminal game state or deadline; no seventh move |
| Command-following measure | Exactly six issued actions in the requested order |
| Execution measure | Correct commands and all six independently replayed states matching frozen reference hashes |

This tests explicit sequence following and game control execution. A model could
pass from the text alone: passing does not establish object recognition, visual
grounding, autonomous route planning or first-level solving. The six moves are
not a complete level solution. Wrong actions are retained rather than corrected
to make the test appear successful.

## Validation

| Check | Result |
| --- | --- |
| Focused new tests | 16 passed |
| Connected Linux regression suite, including those tests | 185 passed; zero failures, errors or skips |
| Derivation | All 11 files match their pinned parents; completed pilot source unchanged |
| Package rebuild | Byte-identical |
| Review notebook / missing-authority launch | Refuse before installation or creating a reservation |
| SDK serialization | Exact private RTX PRO 6000/image/attachment settings verified; no send |
| CPU software positive control | Actual HTTP client/worker executes all six scripted moves; fresh independent replay agrees |
| Native prompt maximum | 1708 tokens; below 8,192 |
| CPU cleanup | Owned groups absent and temporary environment removed |
| Read-only Kaggle readiness | Account, quota, unused target, source versions/inventories, private access and game wheels pass |
| Neural generations / GPU jobs / provider writes | Zero / zero / zero |

The CPU positive control reproduces the retained human demonstration's first six
transitions. Scripted replies are only a software check; they do not establish
that the VLM follows the instruction. Future reference frames and demonstration
logs are excluded from the live payload. Evaluation reference hashes are frozen
in the protocol. The explicitly requested route is intentionally included.

## Final private review and proposed limits

| Binding | SHA256 |
| --- | --- |
| Review lock | `3e8afbcb386f0d17e40f94d658ebcd3d52817b27af34da28b78c94678a77fdab` |
| Review notebook | `02e2ed118ab9d0ce7d9e3dda9b04362a7c5c85c9f0f8096fdd46236741e1b92d` |
| Input manifest | `7e9410bba02c9516b41d4b3daed9e3024f49d5eca6f231f9fb3b398db9342976` |
| CPU source archive | `e8268a1d59d9f9afdceac3b090c0c976fb80c61ea722634c306ecd05abed6f40` |

| Resource | Ceiling |
| --- | --- |
| Accelerator | Exactly one RTX PRO 6000 |
| Requested session timeout / worker limit | 3,600 / 3,300 s; provider overhead can extend total time |
| New-work cutoff / cleanup reserve | 3,000 / 300 s |
| Generations and counted model HTTP requests | Seven: one canary plus six policy replies |
| New tokens | 256 per policy reply; 16 for the canary |
| Offline actions / local scorecards | Seven including the reset / one |
| Online game calls or submissions | Zero |
| Attempts / automatic retries | One / zero |
| Access and network | Private, account-only; internet and TPU off |

Fresh source/use approval and compute authorization must bind this lock. A fresh
read-only preflight and single-use reservation/claim follow approval. There is no
launch authority yet, and all previous attempts remain preserved. The runtime
must refuse a different accelerator.

[Probe implementation](../research/ls20_six_move_v1/README.md).
