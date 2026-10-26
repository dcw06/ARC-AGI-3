# ls20 level 1 with supplied rules and an evidence memory: preparation

**CPU preparation complete; awaiting owner review.** No model inference, GPU job,
upload, reservation or approval has occurred. Nothing launches until the owner
approves this exact package.

*Revised October 26 after an independent package review.* The first version of this
report (commit `7ca39e1`) described a superseded package, review lock `8a5e2321…`.
That package predated the colour legend and the review fixes below, and its Kaggle
readiness result applied only to it. Every binding and number here is for the
current lock.

The pilot reruns the instructed ls20 level-1 test with one addition. Every request
is the instructed pilot's request, byte for byte, plus one text block rebuilt by the
M1 evidence memory (`research/ls20_discovery_mac`, commit `f4bf522`) from the
initial board and the observed transitions. The instructed pilot's attempt 1 used
the same model, settings, board, instructions and 40-move cap without the block,
and completed no level. That run is pinned in the protocol as a descriptive
reference, not a concurrent control. [Design, caveats and limits](../research/ls20_memory_evidence_v1/README.md).

| Information | Source |
| --- | --- |
| Control meanings, visible object roles (player, white cross, reference and destination patterns), rotation rule, goal | The instructed pilot's instructions, unchanged |
| Every current same-colour region with colour ID and x/y ranges | Block |
| Last six moves: changed-cell counts, moved regions with post-move positions and displacements | Block |
| Per-action tallies and the latest run of moves with no moved region | Block |
| Colour-ID-to-RGB legend used to draw the images, and the meaning of each field | Block |
| Solved route, object masks, future frames, replay answers | Not supplied |

The block adds no object labels or roles. On real ls20 frames an up move reports
the player's two colour parts each moving `dy = -5`.

## Package review

A multi-agent review covered the evidence block, the design and claims, the derived
lifecycle code, the private package and bindings, the CPU checks, live-run risks
and privacy. Each finding was then challenged by two independent verifiers. It found
no blocker. Changes made in response:

| Finding | Change |
| --- | --- |
| Colour IDs had no legend linking them to the image colours | Block carries `rendered_palette`, as the k=4 pilot's prompt did |
| Field meanings were not stated in the block | Block note defines post-move positions, displacements, `[dx, dy, count]` and the streak |
| `changed_cells` and `any_change` count the move-budget bar, so they are non-zero on blocked moves | Stated in the block note, README and protocol; `region_moved` is the informative tally |
| Protocol and README misdescribed what is supplied (no legend or streak; "no roles", although the instructions name them) | Rewritten; the protocol now pins the instructed attempt by commit, review lock and evaluation hash |
| No descriptive measures fixed in advance | Protocol lists them: moves used, moves without player movement, longest run of identical actions without movement, distinct player positions, first reference-pattern change and invalid replies, each beside the instructed attempt's value |
| The synthetic move-40 prompt understated realistic prompt size | The CPU review now rebuilds all 40 requests of the instructed attempt's real moves and records their token counts |
| No record of which helper code produced each check run | Per-stage helper provenance records (`stage-r4` retroactively, `stage-r5` at derivation) |
| This report described a superseded package | Revised |

Two follow-up reviews were cut short by a usage limit: the launch operator for this
study and post-run collection and evaluation. Neither code path exists for this
study yet. Both will be derived and reviewed before any launch. One review note
applies to them: the published-source check must name this study's branch, and the
prior-attempt preservation check must cover every earlier attempt.

## Validation of the current package

| Check | Result |
| --- | --- |
| New and derived contract tests | 20 pass on Windows (Python 3.11) |
| Owned offline Linux suite | 220 pass; no failures, errors or skips |
| Derived sources | Eleven files match their pinned instructed-pilot parents |
| Real-engine CPU positive control | Scripted 16-move human route completes level 1 through the new requests; engine counter confirms; independent replay agrees (1 reset, 16 moves, 1 close) |
| Evidence block | Present in every policy request |
| Instructed attempt's 40 real moves, rebuilt | Every request equals the retained instructed request once the block is removed; native prompts 2,027 to 3,890 tokens against the 8,192 cap |
| Exact package | Byte-identical rebuild; 73 review sources and 63 execution sources hash-bound; memory module inside the closure |
| Inference inputs | Board, instructions and manifest only; no route or reference files |
| Refusals | Review notebook refuses before installation; launch without authority refused |
| CPU lifecycle | 314 s; network isolated; owned processes absent; temporary environment removed |
| Read-only Kaggle readiness, current lock | Account, quota, unused target, dataset versions, private model access, inventories and game wheels pass; zero writes |
| Model inference / GPU jobs / provider writes | Zero / zero / zero |

The CPU replies were a scripted human route, and the scripted server ignores request
content. These checks therefore establish software behaviour, request construction
and token budgets, not model performance. The block-bearing prompt has not been run
through the real model.

Four earlier CPU review stages are retained privately. Stage 1 failed: a protocol file
read by the instructed pilot's tests was missing from the CPU source archive (218 of
219 tests passed). Stage 2 passed the suite and the real-engine episode, then stopped
at the helper's synthetic move-40 prompt, which paired a current board with a
different history end; the policy correctly refused it. Stage 3 passed but was
superseded by the colour legend. Stage 4 passed but was superseded by the review fixes.

## Disclosures

- The unchanged instructions tell the model that no object-coordinate masks are
  supplied. The block lists region positions, not masks or labels; the wording is
  kept so the request stays identical to the instructed pilot's.
- The no-movement streak stays at 1 in an alternating pattern such as the
  instructed attempt's; the per-action tally would have shown "up" tried 13 times
  and moving 4.
- The first (canary) request used about 23 s of its 30 s HTTP timeout in earlier live
  runs. That inherited limit is unchanged; a slower start would consume the single
  attempt before any move.
- Rebuilding the memory each step costs a few CPU seconds per request, inside the
  3,000 s admission window.

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
earlier attempts. Before a submission: the launch and collection code for this study
must be derived and reviewed, then lock-bound source, use and compute approval, a
fresh preflight and a single-use reservation and claim.

| Binding | SHA256 or commit |
| --- | --- |
| Source commit | `c9d48d4` |
| Private review lock | `e4c14554bf22a8af2ecc82acdff89782ff26307a804cff164509666f4a1dd840` |
| Input manifest | `5204d2afa0c4827f3b4cab666806bf32b78788d918dc98c0b82a14626a069485` |
| Review notebook | `f781fbe8496b36fc13857d218b32860f498fda8cfe1055a8ec63287fe3ed1653` |
| CPU source archive | `156aaacbc4622241581cdf0cdf8c862601c4e81b19622d0f625cc72a658a915b` |
| Protocol | `0924c06e2827e9e69a2fb46b85a6743248667b86de552c3b336f09332f7e261d` |

Private inputs, runtime bindings and CPU evidence remain git-ignored.
