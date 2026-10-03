# Track 3 R6: reservation versus execution authority

R5's reservation-only records incorrectly passed its live gate. Do not submit
its reserved notebook. R5 and its consumed/unused history are preserved, not
rewritten. The original session-1 reservation remains unused and unchanged:
`ssv1-r5-session1-reservation-001`, 5,400 provider seconds / 5,100 internal seconds.
No second reservation is created for this repair. Session 2 remains unauthorized.

## Executable boundary

The R6 GPU-disabled review notebook derives from the verified R4 payload with
only authority.py replaced. The complete authority overlay is retained in
scripts/stagnation_supervision_v1_authority_r6_template.py and hash-bound in the
package review. Model, prompts, requests, policy, telemetry, budgets, evaluator
and cleanup bytes are unchanged. Historical R4/R5 packages remain reproducible.

validate_reservation accepts only the four exact original session-1 authority
records, whose SHA-256 hashes are embedded in R6. It confirms a reserved state
and reservation-only compute scope. It grants no execution permission.

require (used before installation, model access and GPU probes) additionally
requires fresh R6 source approval and a distinct launch approval. The latter
must explicitly say submit_and_execute_one_attempt and submission_authorized=true,
with the exact new source-review hash, successor source-approval hash, original
compute/execution/reservation hashes, original attempt ID, session 1, maximum
one submission and zero automatic retries. Missing, reservation-only or mismatched
launch authority is rejected. Runtime claims are still exclusive and durable.
The new approval explicitly carries the existing budget forward; it does not
invent another reservation or silently reuse the R5 source approval for R6.

The R6 assembler requires both new approvals before making a GPU-enabled package.
The review notebook remains GPU-disabled with no approvals. Actual committed R5
reservation bytes are used in regressions: reservation validation succeeds while
require, assembly and the notebook live entrypoint refuse. Synthetic positive
approvals exist only in temporary test directories.

## One-use submission boundary

scripts/submit_stagnation_supervision_v1_r6_once.py reconstructs the authorized
package, checks exact artifact bytes, then exclusively creates and fsyncs
submission-claim.json in the original reservation ledger directory before
invoking the supplied transport once. A preexisting claim blocks invocation even
if no result receipt exists. Exceptions including cancellation retain an unknown
outcome receipt and never remove the claim. Successful return also consumes the
attempt pending provider reconciliation. Neither outcome permits automatic retry.
The original reservation records/ledger are historical; the append-only claim
and result are authoritative for later submission status. Reservation-only
records fail before claim creation or transport.

This is a local serialization mechanism, not a distributed provider lock. A
future submission must use the canonical ledger and one reviewed provider adapter
that itself makes no retries. This repair does not supply or invoke a network
adapter, upload anything, book Kaggle capacity or execute a GPU run. Copying an
old package or using the Kaggle CLI directly bypasses this submission workflow
and is not authorized. The R5 reserved notebook is explicitly superseded.

## Review

Run `python -m scripts.review_stagnation_supervision_v1_authorization_r6` in the
existing Linux development environment. It checks the exact runtime overlay,
authority mutations, actual reservation-only notebook rejection, exclusive runtime
claims, and submission success/timeout/preexisting-claim/missing-launch cases.
Submission tests use a synthetic transport and temporary ledgers. They test the
actual assembler unmocked first, then reuse its verified reconstruction for the
fault matrix. The unpacked notebook also performs the existing CPU three-arm
rehearsal with independent trajectory/lifecycle evaluation and cleanup.

R4's runtime evidence and tokenizer audit remain unchanged. Real GPU timing is
unmeasured. ls20 remains exploratory and cannot supply the missing second
qualified continuation control; false-interruption certification remains blocked.

After review, request R6 source approval and a separate explicit launch decision
bound to the new source hash and original reservation. Nothing in this repair or
its prior reservation approval authorizes submission. No new reservation needed.
