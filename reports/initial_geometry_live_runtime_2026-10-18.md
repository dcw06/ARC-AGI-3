# Initial-geometry gameplay: bounded live runtime and private review

The missing executable runner is implemented. Private review r4 is sealed with
lock SHA256 `e0452a412ecc0fe2be93c954547fbf88ad824272cc3f4ee36dadb75f04af6476`.
No approval, reservation, claim, provider save or GPU run was created for this
study. Existing attempts and private raw evidence remain unchanged.

| Component | Implemented behavior |
|---|---|
| Input admission | Full retained native pointing/deployment/SAM-logit replay reproduces the automatic arm before r3 inputs; original 22 automatic and 37 reviewed objects retained |
| Shared policy | Same Qwen policy for 12 counterbalanced episodes; historical starting geometry only; fresh current screenshots; latest two transitions; no game-specific rules or semantic labels |
| Model service | Isolated pinned vLLM 0.19 / Transformers 4.57.6 interpreter, FP8 Qwen revision unchanged; six-image allowance; context 32,768; prefix caching off |
| Game service | Separate 31-wheel interpreter and six pinned public development game versions; MPLBACKEND=Agg throughout; bounded ordered RPC; offline mode only |
| Transport | Frozen one-use request IDs, durable admission before HTTP, absolute 30-second connect/header/body deadline, raw replies retained before interpretation |
| Response audit | Exact model/assistant role, native/server prompt-token equality, strict positive integer usage, completion cap and total-token consistency; invalid actions end their episode without repair |
| Process ownership | Installation/import commands and model/game worker registered as owned groups with startup signals deferred through ownership/watchdog registration; uncertain spawn cannot imply absence |
| Hard deadline | Separate process kills registered groups without a census and then terminates the notebook process at the final deadline; a swallowed one-shot cleanup alarm cannot remove this bound |
| Finalization | Process and GPU cleanup, temporary interpreter/source removal and evidence writes share the lifecycle deadline; provisional result, post-write witness, exact return marker and provider COMPLETE all required |
| Independent evaluation | Exact request/observation replay, strict transport and ledger accounting, real-engine replay, native-token audit, source/input lock and finalization/provider checks; saved provider source, image, privacy, accelerator request and attachments are checked too; no file alone certifies success |
| Launch boundary | Exact source/image/attachment/timeout SDK fields, authority-only late-binding slot, exclusive consumed reservation and send receipt before a single provider write |

| Proposed scope | Ceiling |
|---|---|
| Accelerator / attempt | One RTX PRO 6000; one fresh attempt; no automatic retries |
| Time | Requested session 3,600 s; worker 3,300 s; admission cutoff 3,000 s; 300 s cleanup reserve |
| Study work | 12 episodes, at most 24 policy actions each |
| Generations | 288 study calls plus one canary = 289 maximum |
| New tokens | 256 per study call; 16 for the canary |
| Counted HTTP | Ceiling 300; frozen one-use plan admits at most 289 POSTs; readiness uses TCP only |
| Offline actions | 288 policy dispatches plus 12 initial resets = 300 maximum |
| Scorecards | 12 local cards; zero online game calls, online cards or leaderboard submissions |
| Data handling | Private account-only notebook and raw outputs; sanitized summaries only; internet and TPU off |

The accepted time policy permits allocation, setup, mounting and GPU release
to extend total elapsed time beyond the requested session hour. Quota and a
requested machine shape do not establish actual allocation: the runtime
refuses anything other than exactly one RTX PRO 6000 before installation.

| Check | Result / limitation |
|---|---|
| Linux regressions | 70 pass; zero failures, errors or skips |
| Faults exercised | Handled interruption before Popen assignment and before group registration; uncertain spawn; trickled HTTP body; late admission; interrupted/late finalization; stalled cleanup with independent hard kill |
| Connected CPU rehearsal | 12 episodes, 25 scripted HTTP replies, 24 dispatches and 12 resets; independent replay of all 12 episodes; cleanup and temporary-environment removal verified |
| Exact sealed payload | Extracted and verified against r4, then exercised from its source and game files with another fresh offline installation and all 12 episodes/replays; 16 live-module tests pass; the pinned processor archive is an external CPU-only fixture |
| Rehearsal processor | CPU Transformers 4.57.1 in the connected Linux check; not represented as the production model stack |
| Pinned processor audit | Separate real Transformers 4.57.6 CPU audit: 24 prompts, maximum 4,609 input tokens, up to six images; manual and native counts agree |
| SDK dry check | Exact serialized source/image/attachments/private GPU request and requested timeout validated without sending |
| Review refusal | Exact review notebook stops before payload extraction, installation, GPU queries or game actions |
| Provider read-only checks | Account, quota, target absence, dataset versions, filename/size inventories and private model access with zero collaborators pass; zero provider writes |
| Actual CUDA/vLLM gameplay | Not exercised; no neural generations for this study |

The first connected CPU rehearsal uncovered a journal field collision: the
request's category overwrote the HTTP-admission event type. The independent
transport audit refused it. The corrected producer preserves both fields and
has a regression. That rehearsal is retained; the corrected connected check
passes. No GPU attempt was consumed by these local checks. A deliberately
SIGKILLed watchdog test emits Python's semaphore-recovery warning; the test
verifies that the owned child is no longer running.

Protocol r3 explicitly lists reviewed-object, supplied-mask and supplied-anchor
first-click diagnostics. Supplied geometry can guide clicks directly, so
these do not establish independent object localization. The comparison still
measures the complete starting representation, including inventory omissions,
on six exposed development states. There are no new model-performance results.

The private review contains 116 embedded files (43,469,549 bytes), the exact
notebook/runtime/settings, the historical personal-use assessment, all 23
unchanged standard wheel agreement texts and the model dataset inventory.
Historical permissions are labelled historical; they do not supply fresh
approval for this changed gameplay package. The automatic-arm provenance,
input, game receipt, protocol, source and scope-evidence hashes are bound by
the review lock. No credentials, weights or owner semantic answers are embedded.

Next: review and approve this exact lock and scoped use, authorize one attempt
within the ceilings, then create a single-use reservation/claim and rerun a
fresh read-only preflight. Stop on package drift, failed gates or a different
accelerator. This follows the bound `check_authority()` guard; it does not
replace unresolved redistribution decisions with approval labels.
