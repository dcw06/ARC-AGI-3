# Initial-geometry gameplay: bounded live runtime and private review

The missing executable runner is implemented. Private review r4 is sealed with
lock SHA256 `e0452a412ecc0fe2be93c954547fbf88ad824272cc3f4ee36dadb75f04af6476`.
The owner approved r4's source/use and then separately authorized two fresh
single-use attempts. Both passed fresh preflight, consumed distinct claims and
made one SaveKernel call each. Both calls ended in SSL EOF without a provider
response, including attempt 2 through WSL HTTPS. Read-only reconciliation still
found no target notebook among 73 owner notebooks at 15:32:21 UTC on October 18.
No run is confirmed. Both uncertain attempts stay consumed; no automatic retry occurred.
Existing attempts and private raw evidence remain unchanged.

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

## Authorized attempt 1: transport failure

| Stage | Retained result |
|---|---|
| Owner approval | Exact message retained privately, bound to r4, its scope and the three source/use/compute records |
| Fresh preflight | Account, quota, target absence, dataset versions, inventories and account-only private model access all pass |
| Reservation / claim | Fresh, single-use; consumed before provider transport; preserved |
| Package | Original r4 unchanged outside its declared authority-data cell; SDK source, timeout, accelerator and attachment fields checked again at send time |
| SaveKernel | Exactly one send; SSL EOF (`SSLError`), no returned version or HTTP status; no automatic retry |
| Reconciliation | Read-only owner catalogue has 73 notebooks and excludes the target; status lookup raises ValueError; no confirmed Kaggle run |
| Evidence | Approval, preflight, reservation, claim, execution lock, HTTP events, failure receipt and reconciliation retained privately |

The SSL exception's urllib3 "Max retries exceeded" wording does not establish
multiple sends: the transport explicitly sets zero retries and the retained
ledger contains exactly one SaveKernel event. The connection failure does not
establish its underlying cause or prove that a server-side effect could never
appear later. The reservation is therefore not recycled.

Source and scoped-use approval remain recorded for unchanged r4. Another send
requires fresh compute authorization, a new single-use reservation and fresh
read-only reconciliation/preflight. No new authorization is inferred from this
failed attempt. No model-performance or runtime-compatibility conclusion follows.

## Separately authorized attempt 2: same transport failure

The owner said "Now you may try again." Its private record binds that exact
message to the unchanged r4 lock and inherited ceilings. Source/use records
were retained; only compute authorization and single-use attempt data were new.
Attempt 1's consumed claim and send receipt were checked and left intact.

Fresh preflight again passed all six checks, including absence of a delayed
attempt-1 notebook. The external operator used WSL Python HTTPS through the same
reviewed provider boundary; this changed no notebook source outside authority
data and introduced no automatic retry. Exactly one SaveKernel send encountered
`SSLError`. A read-only follow-up again found the target absent, and the status
lookup raised ValueError. Both sets of private receipts remain preserved.

The attempt-2 notebook is 57,967,905 bytes. Both failures occurred during its
submission, but this does not establish that payload size caused the SSL EOF.
The transport failure needs investigation before spending further attempts;
there is no confirmed model execution or performance result to analyze.
