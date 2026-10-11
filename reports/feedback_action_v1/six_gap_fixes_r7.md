# Track 1: six prelaunch review gaps repaired

The six findings at `edc9566` are repaired. This is CPU verification and a new review package, with no GPU launch,
Kaggle upload, approval, reservation or launch claim. The scientific design and frozen protocol, including A1,
are unchanged. The original failed attempt remains consumed; session 2 remains unauthorized.

| Finding | Repair | Retained regression |
| --- | --- | --- |
| Supervisor startup ownership | Guard the entire spawn/logging/monitor lifecycle; defer handled signals through PID registration; kill and reap owned groups and retain an interruption receipt. Uncertain ownership cannot claim group absence. | Real children interrupted before assignment, before group registration and at logging-thread startup; exceptional spawn with uncertain ownership. |
| Late lifecycle finalization | Charge dependency removal, evidence writes and extracted-source removal to the lifecycle. Check the deadline after the certification write; an overrun retains a failed receipt, with emergency cleanup still possible. | Controlled 59.9 ? 60.1 s evidence write across a 60 s ceiling; source removal crossing the same ceiling. |
| Incomplete independent request replay | Independently reconstruct the entire frozen request, packed observations, legal actions, recent history, evidence window and carried statement from retained transitions. The contract and reconstruction code are mandatory review documents. | Rehashed system prompt, model, schema, role, grid, legal-action and history mutations are rejected. |
| Trusted terminal labels and counters | Derive terminal/cap reasons, final states, pair completion and call/action/token totals from retained events. An incomplete session cannot permit session 2. | Forged win label, final state, pair status and four zeroed aggregate counters are rejected. |
| Canary token bounds | Independently require positive strict integers, exact prompt-token parity and the frozen prompt, completion and context limits. | Completion 129/0/true/negative/float, matching negative or excessive prompt counts, and boolean tokenizer counts are rejected. |
| Stale pooled evaluations | Bind evaluations to canonical run/spec/gate hashes and recompute evaluations before pooling, including metrics and the reviewed checkout. | Altered response paired with its old evaluation and forged evaluation metrics are rejected. |

## Baseline reproduction

A fresh `git archive edc9566` received only `tests/test_feedback_action_v1_review_gaps.py` from the fixed source.
All 11 test methods failed: 29 failed assertions/subtests, one error, no skips. The error is the old `run()` lacking
the new source-cleanup hook; the separate late-write test independently reproduces its passing-over-deadline bug.
The startup tests terminate and reap their reproduction children in their own finalizers, including on baseline.
The replay and pooling fixtures are synthetic/scripted development evidence, not real model results.

The baseline receipt, log and commit/test-file provenance are retained under `reports/feedback_action_v1/`:
`cpu_checks_six-gap-baseline-edc9566.{json,log}` and `six_gap_baseline.json`.

## Review snapshots

| Snapshot | Review-lock SHA-256 | Status |
| --- | --- | --- |
| Public r7 | `62df709c59d42b8da2b68a5bc8d7f4d17e764db3d63109a2ea78ea9b9433d359` | GPU-disabled; public placeholders retained; review check refuses before GPU use; connected extracted-payload rehearsal technically complete. |
| Separate private successor r8 | Recorded in the private handoff | Same account/model bindings and immutable image; exact attachments checked locally; GPU-disabled; no authority records; review check and launch packaging refuse. |

Public r1?r6 and all earlier private copies are preserved. The private successor carries only the three existing
runtime bindings. Its 23 retained licence texts were checked by hash. Scope-evidence reuse and use-assessment drafts
are rebound for review with acceptance flags false and permission outcomes blank. Historical acceptance is
provenance only. The review metadata retains the package's review-template ID; the actual notebook ID is bound
inside runtime.json and is substituted only when authorized launch packaging is allowed.

The frozen protocol text SHA-256 remains
`c489bdc68e5e557def4183c5f0a963d827090f0f54e2e8c5ca41d59b7c14935c`.
Both derivations reproduce: 11 harness files and 4 runtime files; 8 controller files and one reused function remain
verbatim. The pinned image is unchanged. No further replacement or retry is added.

## CPU verification

The Linux runs hide CUDA devices and use an isolated network namespace with loopback only. They use the retained
installed game interpreter and pinned model interpreter; model responses are scripted. They establish no fresh
GPU compatibility or provider allocation claim.

| Check | Result |
| --- | --- |
| Distinct tests, after named focused follow-ups | **200 passed; 0 failures/errors/skips unresolved** |
| First full Linux suite, retained unchanged | 200 tests; 3 failures and 1 error from stale r6 assertions; 3 environment-dependent skips. All seven results have explicit successful follow-ups. |
| Updated r7 snapshot class | 7 passed, no failures/errors/skips; byte-identical rebuild and r1?r6 history hashes verified. |
| Linux derivation/provenance follow-ups with Git object access | 2 passed, no failures/errors/skips. |
| Pinned model interpreter HTTP/grammar path | 1 passed, no failures/errors/skips; every committed form exercised. |
| New six-gap regression group | All 11 methods pass, including all mutation subcases; baseline fails as recorded above. |
| Connected lifecycle fault matrix | All 10 faults pass cleanup/evidence assertions; both normal blocks and admission cutoff pass. |
| Public r7 extracted-payload rehearsal | Technically complete; pinned tokenizer and grammar checked; source removed; no lifecycle errors. |
| Public r7 and private r8 review checks | Refuse before GPU use; no temporary files left. |
| Private r8 source/image/attachment check and rebuild | Only runtime.json differs from public r7; review documents identical; all source hashes and 23 retained licence hashes match; byte-identical rebuild. |

The first full-suite pass used the old r6 snapshot assertions. Those assertions were updated to r7 with r6 added to
the retained-history hashes, and their class was rerun. Two Git-object checks initially skipped because the Windows
worktree Git pointer could not be read; both passed after pointing the process at the shared object database.
The HTTP/grammar test skipped in the game interpreter and passed separately in the pinned model interpreter.
Original and follow-up receipts are retained rather than overwritten. The consolidated record uses the newest
result for each distinct test and names every input receipt.

## Remaining launch gates

Review this exact new private package and its scoped evidence; obtain fresh source approval and compute authorization
bound to its lock, followed by an unconsumed single-use reservation/claim and a fresh read-only provider preflight.
A1 allows only the one replacement session-1 attempt: one RTX PRO 6000, at most 3,600 seconds, 193 generation
requests including the canary, 144 offline game actions, zero online game calls/scorecards and no automatic retries.
CPU checks cannot confirm current provider attachments, available quota or the accelerator ultimately allocated.
The separate R2 redistribution review is not substituted for the direct-publisher scope assessment.
