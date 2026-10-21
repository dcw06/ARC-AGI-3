# ls20 level-1 instructed VLM pilot: preparation

**Status: implemented and CPU-validated; no GPU attempt authorized or submitted.**

The user chose **controls and rules explained; the agent plans the actions**.
This test asks whether the existing Qwen VLM can complete ls20's first level with
that help. It does not test rule discovery or compare improvement against a
baseline.

## What the agent receives

The private, frozen instruction text explains the directional controls, the
player and interaction features, the rotation rule, and the pattern-matching
goal. It also tells the agent to check observed movement and revise blocked
moves. The agent receives the initial board, the current board and at most two
observed before/after transitions, rendered at 448 × 448 without overlays.

It must choose every move. The live payload contains no solved action sequence,
object-coordinate masks, future observations or demonstration log. There is no
fixed pair of candidate actions: any of the four directional actions is allowed.

Only an engine completed-level counter increase counts as success. The runner
stops immediately after that increase and never dispatches a next-level move.
The independent audit reconstructs the requests and replays all actions against
the pinned offline engine.

## Checks completed

| Check | Result |
| --- | --- |
| New episode/replay tests | 13 passed |
| Linux suite, including those 13 tests and inherited lifecycle regressions | **169 passed; zero failures, errors or skips** |
| Derived lifecycle/package files | All five match their pinned parents |
| Private package rebuild | Byte-identical |
| Input inventory | Starting board, frozen instructions and manifest only |
| Review notebook without optional packages | Refuses before installation or file creation |
| Launch build without authority | Refuses; no reservation or claim created |
| SDK serialization | Exact private RTX PRO 6000/image/attachments request checks pass; no request sent |
| Read-only Kaggle readiness | Account, quota, unused notebook target, dataset versions/inventories, private model access and game wheels pass |
| Actual GPU allocation | Not yet checked; runtime must refuse a different accelerator |

### Real-engine software positive control

A private CPU-only helper supplied the user's retained demonstration moves to
the actual HTTP client/worker path. This was scripted software validation,
**not VLM inference or evidence that the agent can solve the level**.

| Positive-control check | Result |
| --- | --- |
| Retained human transitions reproduced | All 16, with exact before/after observations |
| First level completion | Confirmed by the engine; stopped before another move |
| HTTP requests | 17: one canary and 16 scripted answers |
| Independent fresh-engine replay | One reset, 16 moves, one closed local scorecard |
| Largest audited native prompt, including a decision-40 history check | 2,386 tokens; below 8,192 |
| Fresh game environment | All 31 wheels installed offline with required hashes |
| Complete CPU review lifecycle | 262.8 s; owned processes absent and temporary environment removed |
| Neural generations, GPU jobs, provider writes | Zero |

The reference route is retained privately and excluded from the live payload.
Raw human logs, scoped-use records, model bindings and CPU receipts remain in
the ignored private workspace.

## Final private package

| Binding | SHA256 |
| --- | --- |
| Review lock | `25f3a023249f5a880628069ba07ae67fda36392661a756a259b7c7ec3dea2fa3` |
| Review notebook | `088c110d096b70882e4857fbbebd4ad29a9ebaa1a8388c7ae8c2f1cd573899f6` |
| Inference-input manifest | `db4d01f9a5092fb8dbd8250a0156753d1a6ce49d22ca0f5578d046764ea6913c` |
| Instructions | `e7c2f9f31b1e4b77b56807d845afc6d0bc0325f56cb5986197e54eb09b6f26d1` |
| CPU source archive | `09adb447f8d0d94b1d0f83d6bc9c8bb7467ba33cc0c70fd706959248a6a2f347` |

The lock binds 64 review source files and 55 execution source files. The runtime
uses the previously pinned Qwen model-copy, immutable image and dependencies.
Every mounted publisher wheel must still be hash-verified before installation;
the prior byte receipt is historical evidence, not a replacement for that check.

## Proposed launch scope — approval still required

| Resource | Ceiling |
| --- | --- |
| GPU | Exactly one RTX PRO 6000 |
| Requested session timeout / worker limit | 3,600 / 3,300 s; provider overhead can extend total time |
| New-work cutoff / cleanup reserve | 3,000 / 300 s |
| Model generations and counted HTTP requests | 41: one canary plus at most 40 policy replies |
| New tokens | 256 per policy reply; 16 for the canary |
| Offline actions | 41: one initial reset and at most 40 moves |
| Local scorecards | One |
| Online game calls or submissions | Zero |
| Attempts / automatic retries | One / zero |
| Access and network | Private, account-only; internet and TPU off |

Fresh lock-bound source/use approval and compute authorization are still needed.
After approval, a fresh read-only preflight must pass before a single-use
reservation/claim and one submission. Previous attempts remain preserved. A
changed package, failed gate or different accelerator must stop the launch.

Implementation: [runner and protocol](../research/ls20_instruction_v1/README.md).
