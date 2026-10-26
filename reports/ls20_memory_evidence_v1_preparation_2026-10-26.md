# ls20 level 1 with supplied rules and an evidence memory: preparation

**CPU preparation complete; awaiting owner review.** No model inference, GPU job,
upload, reservation or approval has occurred. Nothing launches until the owner
approves this exact package.

The pilot reruns the instructed ls20 level-1 test with one addition. Every request
is the instructed pilot's request, byte for byte, plus one text block rebuilt by the
M1 evidence memory (`research/ls20_discovery_mac`, commit `f4bf522`) from the
initial board and the observed transitions. The instructed pilot's attempt 1 used
the same model, settings, board, instructions and 40-move cap without the block,
and completed no level. That run is a descriptive reference, not a concurrent
control. [Design and limits](../research/ls20_memory_evidence_v1/README.md).

| Block field | Contents |
| --- | --- |
| `current_regions` | Every same-colour connected region on the current board: colour, cell count, x and y ranges |
| `recent_transitions` | Last six moves: action, changed-cell count and moved regions with their displacement |
| `action_summary` | Per action: times taken, times anything changed, times a region moved, commonest displacements |
| `recent_steps_without_moved_region` | Current run of moves in which no region moved |

A moved region is a tentative match between consecutive frames in which both copies
contain changed cells, not a verified object or role. On real ls20 frames, an up
move reports the player's two colour parts each moving `dy = -5`. The block names no
objects and supplies no route, labels, roles or future frames.

## Validation

| Check | Result |
| --- | --- |
| New and derived contract tests | 32 pass on Windows (Python 3.11) |
| Owned offline Linux suite | 219 pass; no failures, errors or skips |
| Derived sources | Eleven files match their pinned instructed-pilot parents |
| Real-engine CPU positive control | Scripted 16-move human route completes level 1 through the new requests; engine counter confirms; independent replay agrees (1 reset, 16 moves, 1 close) |
| Evidence block | Present in every policy request |
| Native prompt tokens | Largest actual 3,446; synthetic move-40 worst case 3,347; cap 8,192 |
| Exact package | Byte-identical rebuild; 73 review sources and 63 execution sources hash-bound; memory module inside the closure |
| Inference inputs | Board, instructions and manifest only; no route or reference files |
| Refusals | Review notebook refuses before installation; launch without authority refused |
| CPU lifecycle | 324 s; network isolated; owned processes absent; temporary environment removed |
| Read-only Kaggle readiness | Account, quota, unused target, dataset versions, private model access, inventories and game wheels pass |
| Model inference / GPU jobs / provider writes | Zero / zero / zero |

The CPU replies were a scripted human route, so these checks establish software
behaviour only, not model performance. Rebuilding the memory each step costs up to
a few CPU seconds per request, inside the admission window.

Two earlier CPU review runs are retained privately as failed checks. The first
omitted a protocol file that the instructed pilot's tests read from the CPU source
archive (218 of 219 tests passed). The second passed the suite and the real-engine
episode, then stopped at the helper's synthetic move-40 prompt, which paired a
current board with a different history end. The new policy correctly refused it,
and the helper now uses the history's last board.

## Proposed one-attempt scope, not yet authorized

| Resource | Limit |
| --- | --- |
| GPU | Exactly one RTX PRO 6000 |
| Time | Requested session 3,600 s; worker 3,300 s; admission cutoff 3,000 s; cleanup reserve 300 s |
| Model requests and generations | At most 41: one canary and up to 40 policy replies |
| New tokens | Canary 16; each policy reply 256 |
| Offline engine actions | At most 41, including the one reset |
| Local scorecards | One |
| Online game calls / submissions | Zero / zero |
| Access | Private, account-only; internet and TPU off |
| Attempts / automatic retries | One / zero |

Provider overhead may extend total time beyond the requested session timeout, as in
earlier attempts. Before a submission, lock-bound source, use and compute approval,
a fresh preflight and a single-use reservation and claim are still required.

| Binding | SHA256 or commit |
| --- | --- |
| Source commit | `7bec96c` |
| Private review lock | `8a5e23219ba14ddd2d4ced66182ae27ab5537f04ef82d581f87638802fac2429` |
| Input manifest | `2aa4fed1aeea87a17643bb60a7b694a4f015ab9072564fcaf76f529e1496991a` |
| Review notebook | `a3b7e34216f956a66756edb9e0f0f60de14bf23c5a40997ce6bda6a9ad89ecef` |
| CPU source archive | `71e0a40fe201a40875530f6498aaadfbca123b193c2ce047fe91f93acaaf6156` |
| Protocol | `8af0745b9a6f3412a33c010cb4da9b3f364a4c6c3d6c86315b10ded95cbe8ea5` |

Private inputs, runtime bindings and CPU evidence remain git-ignored.
