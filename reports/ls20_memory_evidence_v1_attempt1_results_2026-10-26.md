# ls20 evidence-memory pilot: attempt 1 results

**Technically complete and independently validated. The agent did not complete
level 1.** With the instructed pilot's controls and rules plus a computed
evidence-memory block in every request, Qwen used all 40 moves and finished with
zero completed levels. The block reported accurately that one action kept failing,
and the agent kept choosing it.

## Pre-registered descriptive measures

Each measure is fixed in the protocol and reported beside the instructed attempt,
which used the same model, settings, board, instructions and cap without the block.
That attempt ran earlier; it is a reference, not a concurrent control.

| Measure | Evidence memory | Instructed attempt |
| --- | --- | --- |
| Moves used / stop reason | 40 / action cap | 40 / action cap |
| Level 1 completed | No | No |
| Moves without player movement | 9 | 9 |
| Longest run of identical actions without movement | 1 | 1 |
| Distinct player positions, including the start | 8 | 10 |
| First move changing the reference pattern (cross contact) | None | None |
| Invalid replies | 0 | 0 |
| Prompt / completion tokens | 144,798 / 842 | 84,791 / 842 |
| Largest native prompt | 3,895 tokens | 2,386 tokens |

Player positions use the instructed results analysis unchanged: the ten orange
marker cells located on the retained frames. They were not supplied to the model.

## What the agent did

After four opening moves (right, up, left, down), the agent repeated
**right → up → down** for the rest of the episode. Up and down moved the player
every time; right moved it 4 times in 13 and was blocked at moves 14, 17, 20, …, 38.
The instructed attempt also cycled with period three (right → up → left) and was
blocked on the same move indices, with up as the blocked action.

| Action | Taken | Player moved |
| --- | --- | --- |
| Up | 13 | 13 |
| Down | 13 | 13 |
| Right | 13 | 4 |
| Left | 1 | 1 |

The block made this visible. In the final request its per-action tally read: right
taken 13 times, a region moved 4 times; up and down moved every time. The agent still
chose right every third move. It also predicted no visible change for 33 of 40 moves,
although every move changed at least the move-budget bar.

## What this establishes

**Adding the evidence block did not change the outcome or the failure pattern in
this episode.** Accurate, explicit tallies of blocked moves did not stop the agent
from repeating a blocked action.

This is one exposed episode against an earlier reference run. It cannot attribute
the different cycle or the two fewer distinct positions to the block, and it does
not show whether the model read the block, misread it, or ignored it. It does not
establish that the model cannot solve ls20, or isolate perception, rule use or
planning. No discovery, generalization or standalone solving claim follows.

## Runtime and independent validation

| Check or resource | Observed result |
| --- | --- |
| Provider status | COMPLETE, version 1; one submission, no retry |
| Allocated GPU | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Recorded lifecycle | 809.4 s, below the 3,300 s worker limit |
| Model generations / counted model HTTP requests | 41 / 41 ceiling: one canary and 40 policy replies |
| Largest completion / finish reasons | 21 tokens; all generations stopped normally |
| Offline actions | 41 / 41 ceiling: one reset and 40 moves; one local scorecard, closed |
| Online game calls / scorecards / submissions | Zero |
| GPU cleanup | Verified; zero GPU processes; owned groups absent; temporary environment and source removed |
| Evidence collection | 13 files, 3,133,595 bytes, hashes checked; provider source unchanged during collection |
| Native prompt counts | All 41 independently re-counted and matched |
| Independent replay | Every request, including each evidence block, rebuilt from the exact prelaunch archive; 40 moves replayed on a fresh offline engine (1 reset, 40 moves, 1 close) |
| Independent evaluation | Technically complete; lifecycle certified; network isolated; 78 s |

The first independent evaluation run stopped before any replay or scoring: its helper,
derived from the k=4 study, passed that study's input folder name instead of this
package's. A corrected helper changed only that path and wrote to a separate folder.
The first run's records, including a matching native-token re-count, are retained.

| Binding | SHA256 or commit |
| --- | --- |
| Executed source commit | `5c5f1e55071894f087deaba63af23a38d8d8d5f3` |
| Private review lock | `e4c14554bf22a8af2ecc82acdff89782ff26307a804cff164509666f4a1dd840` |
| Input manifest | `5204d2afa0c4827f3b4cab666806bf32b78788d918dc98c0b82a14626a069485` |
| Independent evaluation | `62512ec4db53690c3d67682ed90f39d842a48c6530859b325d710e7e5e28aea5` |
| Evaluated run evidence inventory | `c0968919a5adabdd49ce895ffc225cef878b81b09856fa59318333a558c74271` |

Private raw outputs, provider evidence, approvals and CPU replay remain git-ignored.
Only sanitized results are published. The one attempt is consumed and preserved; no
retry or additional GPU run was launched or authorized.
