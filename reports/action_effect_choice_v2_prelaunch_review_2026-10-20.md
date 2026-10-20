# Action-effect choice v2: prelaunch review of eabb499

**Not ready for GPU submission.** The phase-explicit interface has substantial
CPU validation, but this revision contains a prospective CPU package, not a
v2 live pilot package. No new defect was reproduced in the reviewed phase/schema
implementation. The blocking gaps below concern the unimplemented live path;
passing tests for the older launcher does not certify that path for v2.

## Blocking integration gaps

| Gate | Current evidence and required completion |
| --- | --- |
| V2 execution and pilot limits | The only committed action-effect live worker imports `research.action_effect_choice_v1.flow` ([worker](../research/action_effect_choice_live_v1/live_worker.py)). Its ledger permits 33 requests, 16 resets, 68 dispatches and 16 closes. The runtime scope permits 84 offline actions including resets. The v2 format pilot instead proposes 9 requests, 4 resets, 16 dispatches and 4 closes, totaling 20 offline actions including resets. Implement and fault-test a v2 worker and scope that enforce the smaller plan before any effects. Merely changing the prompt or notebook authority would leave the wrong executable contract. |
| V2 independent evaluation | The existing [content auditor](../research/action_effect_choice_live_v1/audit.py) reconstructs v1 requests and expects eight checkpoints, sixteen conditions and the v1 ledger. It cannot certify the four-condition v2 pilot. Add independent reconstruction of both phase-specific requests, prior-answer binding, reached/unreached phase accounting and matching transport/engine totals. Format coverage must remain incomplete if any condition never reaches its second phase. |
| Exact private notebook and authority | No v2 live review notebook, source/execution lock or single-use reservation exists in the inspected successor workspace. The retained v1 lock is valid for its consumed attempt only. Build a new GPU-refusing review package binding the v2 sources/protocol, immutable runtime image, exact notebook identity, versioned attachments, mounted-byte checks, use evidence and pilot limits. Review its actual payload and launch request, then obtain fresh lock-bound approval/compute authority and reservation. |

The current v1 input verifier refuses the new CPU inputs because their manifest
contract differs. This is a useful refusal, not a reason to rename a file or
relax verification. The new live-input contract must independently reconstruct
the correct pilot subset and bind its relationship to all eight original
checkpoints. Reference branches, scripted answers and hypothetical future
request audits must stay outside the inference payload.

Current provider availability, quota and saved notebook state were **not**
queried. There is no final v2 target package against which to run that preflight.
These checks belong immediately before a later authorized launch. The intended
GPU remains exactly one RTX PRO 6000; requested session and worker deadlines
must be explicit in that future package. A session timeout does not establish a
one-hour bound on provider allocation, mounting or release overhead.

## Checks completed

| Check | Result |
| --- | --- |
| Independent Linux suite | **117 passed**, zero failures, errors or skips; includes both interface versions, worker, transport/replay evaluation, package/operator/source checks, startup interruptions, descendant cleanup and finalization/deadline faults |
| Exact-source review | 144 source files from the two pinned CPU archives match the checkout and isolated Linux snapshot; no conflicting dependency bytes |
| Derivation and CPU inputs | Three derived files match their pinned parents; the externally pinned 18-file v2 inference preparation verifies |
| Retained evidence bindings | All eight hashes listed in the preparation report match their retained files, including native grammar, token and real-engine receipts |
| Prior private package | Its original review lock, embedded payload and scoped-evidence hashes still verify against their original sources; this does not approve v2 |
| Attempt preservation | 434 completed-attempt files match the preservation inventory |
| Review lifecycle | 178 seconds within the 420-second test watchdog; subprocess groups absent, descendants reaped, temporary snapshot removed |
| Provider/model effects | Zero Kaggle calls, provider writes, neural generations or GPU launches |

Two preliminary local helper runs stopped before the test suite: one used an
incorrect local review directory, and one was interrupted during slow
Windows/WSL source traversal. They were retained separately. The completed
check used the same hash-verified source and private review metadata in a native
Linux snapshot. These were local review operations, not GPU attempts.

The reviewer verified the retained CPU receipts and their source bindings.
The prior native decoder test admitted 50 first-phase and 450 second-phase
canonical legal answers, and rejected 34 adversarial answers per phase. Its
208 request-wrapper/sampling conversions cover both phases. These results are
CPU compatibility evidence; they do not establish a neural format-compliance
rate, forecast accuracy or gameplay improvement. The GPU's actual server and
decoder path still need observation during the proposed pilot.

The retained real-engine CPU rehearsal covers all sixteen conditions with 32
scripted completions, sixteen deterministic trajectory replays and 48 fresh
reference branches. All eighty engines closed. Native processor counts cover
192 request variations, with a maximum of 5,224 prompt tokens against 8,192.
These retained checks were hash-verified in this review, rather than rerun or
represented as new model inference.

## Experimental interpretation

| Question | Review conclusion |
| --- | --- |
| Does restored game history imply a previous study decision? | No. The integer study index is independently supplied and checked against the restored prefix length. |
| Are earlier invalid replies being rescued? | No. The strict parser is reused; 2 of the 17 retained study replies remain valid and 15 remain invalid. |
| Does first-phase compliance show understanding? | No. The decoder fixes both retrospective fields to `not_applicable`; this is host-enforced procedure. |
| Does the second-phase decoder supply correct outcomes? | No. It permits all substantive retrospective enums and all forecast categories. Correctness still requires independent evidence. |
| Can the pilot compare scientific arm effects? | Its proposed purpose is format acceptance and reached-phase coverage only. No arm advantage, learning or solving claim follows. |
| Can a case be replaced after an early stop? | No. Keep scheduled denominators and missing phase coverage; do not force continuation or select a favorable replacement. |

The first two original inventory entries correctly give four conditions, eight
restored-prefix dispatches, at most eight new dispatches, four resets and four
local scorecards. The nine-request ceiling includes one startup canary. The
candidate labels and instruction arms remain unchanged; selection by inventory
ordinal does not create a held-out evaluation set.

## Review receipts and preservation

| Binding | SHA256 |
| --- | --- |
| V2 prepared inference manifest | `97d689d691d120c15d632563eb94b7dd8b3a194e02339083ffb9f10a6fcba103` |
| V2 CPU source archive | `48028ac74581782258470bd5f32f54e901e05a67b09685f1f7a91d906e2568d9` |
| Independent 117-test receipt | `5b7e8ef30b0949500095d86da92a07c8fb9f2f8e3dcf5f1a741a203491444dbf` |
| Source/preservation/retained-evidence review | `0fc35fac1e3b0196ca7f1887008e311f8aa67b168228df23d7cc89d2fcf864b3` |
| Independent review lifecycle receipt | `378aebeae4cf8643de6c7f8f989ba74c4724018983ca40e8dbe0481bf11f37b9` |

Private detailed receipts are retained under
`.cache/github-review/action-effect-choice-v2-2026-10-20/prelaunch-review-eabb499-r3/`.

No production source was changed during review. Three unrelated untracked
coordinate-grid files were left untouched. All consumed attempts and retained
v1 evidence remain preserved. No GPU job, provider upload, reservation, launch
claim or submission was made by this review.
