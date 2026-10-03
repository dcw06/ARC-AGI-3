# Current update: user stopped the attempt

Kaggle now reports `CANCEL_ACKNOWLEDGED` after the user's manual stop.
The provider acknowledges cancellation; this is not independent evidence of
GPU-process cleanup or exact billing. The submission claim remains consumed,
with no retry or replacement reservation. No valid study result was established.
The missing wheelhouse attachment remains unresolved.

The following submission-time report is retained as historical context.

# R6 session 1: submitted once; required attachment rejected

The user's latest instruction explicitly approved R6 source and one session-1
submission. The existing reservation ssv1-r5-session1-reservation-001 was reused;
no new reservation was created. R5 was not submitted. This Codex primary agent
was the designated operator, using the canonical existing ledger in this worktree.

## Local review and approval

The adapter uses the installed official Kaggle SDK request schema, but bypasses
its transport. One requests.Session with total/connect/read/status/redirect/other
retries set to zero sends exactly one SaveKernel POST; redirects are disabled and
a second send is refused. Connect/read timeouts are 30/120 seconds. Responses
are bounded to 256 KiB and retained before interpretation. Credentials remain
local and are neither embedded in the notebook nor recorded in evidence.

Two local tests passed, exercising real loopback HTTP success, redirect, 429,
503 and disconnect responses, duplicate-send refusal, missing-claim and request-
hash rejection. Final package extraction verified the actual R6 authority gate
without invoking the live notebook entrypoint. The exact wire notebook, privacy,
GPU, internet-disabled flags, RTX PRO 6000 shape and 5,400-second provider timeout
were checked. Source/test/launcher hashes and installed versions are retained in
r6-prelaunch.json. The approved runtime source hash remains
365572597cc972268dc0cb7b52d5b10ea2b5f4f31ea22bbbaf77285d2272bd03.

## Provider result and limitation

The durable one-use submission claim was fsynced before the HTTP POST. Kaggle
returned HTTP 200, notebook version 1, kernel ID 136847605, and URL:
https://www.kaggle.com/code/daichongwei06/arc3-stagnation-supervision-v1-authorization-r6

However, invalidDatasetSources contains driessmit1/arc3-vllm-h100-wheelhouse-v3.
The latest pulled metadata confirms there are no dataset attachments; competition
and model attachments remain. The adapter's transport-return receipt is not
technical acceptance of the study. This is an invalid required attachment and
no valid study result or model readiness has been established.

Latest status queries report RUNNING. An initial query using versionLabel "1"
returned 404; the latest-version query succeeds. Raw read-only responses were
retained (some initial receipts contain gzip-compressed response bytes). No
SaveKernel retry occurred. A bounded logs request returned HTTP 400.

Cancellation could not be issued safely: the available status/metadata responses
do not provide the kernel_session_id required by the installed CancelKernelSession
API, and neither the kernel ID nor version number was substituted for that ID.
If still running, stop the attempt through the notebook's Kaggle interface.
The frozen notebook should fail at the missing-wheelhouse check before model
installation; this is an expectation, not an observed cleanup result.

The reservation is now consumed for submission. Preserve the append-only claim
and provider evidence; do not reuse the original reserve-only ledger event as
permission for another attempt. Exact billing and terminal cleanup remain
unverified. Real GPU timing and the second qualified continuation control remain
unresolved; this cannot certify the false-interruption gate or complete Phase 4.
