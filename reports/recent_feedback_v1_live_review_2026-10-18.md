# Recent-feedback paired gameplay: live package review

This prospective pilot compares the unchanged recent-image interface with an
explicit deterministic summary of those same displayed transitions. Both arms
receive the same owner-reviewed starting geometry. It tests feedback presentation,
not independent object discovery or a longer memory window.

| Frozen setting | Value |
| --- | --- |
| Starts and order | Six retained development starts; three raw-first and three summary-first pairs |
| Model | Same pinned Qwen3-VL-30B-A3B-Instruct-FP8 checkpoint and runtime as the completed baseline |
| Episode budget | 24 policy calls/actions per episode; 12 episodes |
| Summary | Last two displayed transitions only; at most 4,096 UTF-8 bytes; no roles, rules, recommendations or action bans |
| Prompt/output limits | At most 8,192 native prompt tokens, checked before HTTP admission; at most 256 new policy tokens |
| Compute scope | One RTX PRO 6000; requested session timeout 3,600 s; worker 3,300 s; admission cutoff 3,000 s |
| Request/action ceilings | 289 generations including canary; 300 HTTP requests; 300 offline actions including 12 resets; 12 local scorecards |
| Access and external effects | Private account-only; internet/TPU off; zero online game calls and scoreboard submissions; no retries |

The live protocol freezes the exact case inventory, geometry, order, resource
ceilings and metric denominators before any generation. Primary results are
paired first-level completion within 24 actions. Secondary results describe
repeated full actions after unchanged displayed grids, context strata, action
diversity and prediction coverage/accuracy. Grid equality does not establish
hidden-state equality, and diversity is not solving.

## Exact package and checks

Private review r2 lock SHA256:
`fd778424ce3ab9994a4608e020a9f9b0a5b7aaa8721e695e83f8c75ceedd9bc9`.

| Review area | Result |
| --- | --- |
| Runtime derivation | Four modules reproducibly derived from exact hash-verified, unchanged baseline r5 source |
| Sealing | Fresh-process rebuild is byte-identical; 104 payload members; 393,980-byte review notebook; all reviewed source files present and hash-bound |
| Bootstrap | Standard-library-only imports verified in an isolated pre-install interpreter; no-authority notebook refuses before setup |
| Negative fixtures | 14 checks reject altered order, geometry, grids, seeds, game identity, rehashed wrong board, source, image, attachments, privacy, TPU/internet, timeout and accelerator |
| Extracted-package tests | 88 passed, zero failures/errors/skips, including Linux process ownership and deadline faults |
| Final full Linux group | 110 passed, zero failures/errors/skips; 12.99 s |
| Full-cap connected rehearsal | 289 scripted HTTP completions; 12 real offline game episodes and 12 independent engine replays; 288 play dispatches and 12 resets |
| Rehearsal accounting | Replay separately adds 288 dispatches and 12 resets; 24 local scorecards including replay; zero neural inference or GPU jobs |
| Pinned native token check | Transformers 4.57.6 independently rechecks all 289 requests with exact count agreement; maximum 4,816 prompt tokens |
| Rehearsal lifecycle | 357.54 s including fresh offline game installation, playback, replay and extracted tests; process groups absent; temporary interpreter removed |
| Provider preflight | Read-only account, quota, target absence, dataset versions/privacy, model/wheel inventories and 31 competition game wheels passed; actual allocated GPU still requires runtime verification |
| Earlier attempts | Three consumed baseline attempts preserved; 112 retained attempt/evidence files hash-checked; baseline r5 source and review lock unchanged |

The first local review build omitted the connected-rehearsal script because a
preparation helper imported the builder before regenerating it. Its CPU check
failed before gameplay. That build and failure remain retained. R2 was built and
rebuilt in separate fresh processes and explicitly checks every reviewed source
against the embedded payload.

The first concurrent full Linux test group had one watchdog total-time assertion
failure (4.14 s against 3 s); the process was killed. The isolated regression
passed in 1.74 s. Both observations are retained. The final full-group rerun
passed all 110 tests in 12.99 s with no skips; its receipt is bound before any
authorization/reservation is used.

## Interpretation and launch controls

CPU replies are scripted and do not demonstrate neural gameplay performance,
current CUDA compatibility or future trajectory token counts. Every live prompt
is audited before admission; mounted bytes and actual GPU identity are verified
again inside the job. An overrun, interruption or uncertain ownership fails the
attempt. Evidence finalization and source/interpreter removal remain inside the
bounded lifecycle. Independent native-token checks, game replay, a version-bound
provider COMPLETE receipt and the exact return marker are required afterward.

The owner explicitly requested comprehensive review and one submission under
the preceding unchanged ceilings. The operator must bind that delegated approval
to this exact lock, protocol and retained scoped-use evidence, rerun fresh
read-only preflight, and consume a new single-use reservation before one send.
It must stop on drift, refusal or network uncertainty. This does not imply that
the owner personally inspected a newly generated hash. Allocation, mounting,
setup and GPU release can extend total provider time beyond one hour, as previously
accepted. No prior reservation or attempt is reused.

## Submission record

After this review, one fresh reservation was consumed and exactly one provider
save-and-run call created private version 1. Fresh preflight passed all seven
checks, with no rejected attachments or provider error. A read-only pull verified
the exact authorized notebook, private settings, pinned image, requested RTX PRO
6000 and sources. Kaggle reported RUNNING at collection of the submission receipt.
All 112 retained earlier-attempt files still matched their hashes. There was no
automatic retry.

This is a submission-status record, not a completed experiment or a claim that
the requested GPU was already observed by the runtime. Raw approvals, reservation,
request, provider response and saved-source receipts remain private. Collection,
independent native-token checking, engine replay and provider lifecycle validation
are required after the run finishes.
