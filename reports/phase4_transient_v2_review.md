# Transient-frame v2 authorization and launch review

Status: pending explicit user source approval and separate compute authorization.
No authority has been recorded, no reservation made, and no GPU run launched.

This revision preserves transient v1 R3 and its deliberate live-execution rejection.
R3 review lock SHA-256 is
`7cf4378b3e4674b6c74ddac119ab4ce8d637272bf2b109b88ebb1605fa0be943`.
The new namespace is `certification/phase4_transient_v2`; the review notebook is
`notebooks/phase4-transient-v2-review-r1`, private, offline, and GPU-disabled.

## Experiment and limits

The selection rules, no-example prompt, model, games, paired seeds, action budget,
tokenizer binding, response retention, independent trajectory evaluation, and
cleanup requirements are inherited unchanged from transient v1 R3, except for
revision identity. The only experimental difference remains the transient-frame
field. Six episodes on ft09, three matched pairs, at most 20 actions each: 120
policy calls plus one startup canary. No coordinate history, fallback, reset, or
retry is added. This is an exploratory early-progress comparison using an
E1S-R-derived `arc_action_v12` policy, not established solving improvement.

Proposed compute authority is exactly one startup-inclusive 3,600-second attempt
on one RTX PRO 6000. The internal lifecycle cap is 3,300 seconds; workload stops
by 3,000 seconds with 300 seconds reserved for cleanup. Existing installation,
startup, workload, memory, payload, context, and evidence ceilings remain in force.
No full pilot, holdout run, scored submission, or production certification is
authorized. Production one-scorecard/110-distinct-game certification, production
`C_admit`, and exact billing remain open.

## Review-to-launch binding

`scripts/phase4_transient_v2_launch.py` records two separate explicit decisions.
Both bind the exact review-lock hash. Compute approval also binds the source
approval bytes and exact integer limits. Approval text is recorded by the operator
from the user's decision; these local records are not cryptographic signatures.

Reservation exclusively creates one attempt identifier and binds the execution
lock and both approvals. Deterministic packaging adds only authority sidecars,
the reviewed wrapper injection, launch description, and required GPU metadata.
Validation reconstructs exact package bytes; changing content and merely updating
its hash does not bypass comparison. Missing, mismatched, consumed, or reused
records fail before upload. Quota must be finite, nonnegative, and sufficient.

An exclusive, fsynced launch claim consumes the attempt before the sole provider
upload call. Provider exceptions or ambiguous responses never restore authority.
A partial reservation/package/prelaunch failure is fail-closed and needs manual
review. The notebook also exclusively writes a runtime-consumed marker outside
its temporary source tree before installation. The supported launcher prevents
repeat uploads; the runtime marker prevents replay in the same working directory.
These local controls cannot prevent someone manually uploading a copied notebook
to a fresh provider session. Such replay is outside this authorization.

## Validation and completion requirements

Local tests cover missing and mismatched approvals/reservations, consumed states,
source/package tampering, invalid quota, one upload, unknown provider outcome,
runtime marker reuse, and the inherited selection/trajectory failure cases.
Package review compiles all embedded Python, verifies every binding, and executes
the unapproved notebook to confirm rejection before installation with temporary
source removal. A temporary copy with synthetic approvals verifies deterministic
launch packaging without provider access; those approvals are never project
authority. Machine-readable review results are recorded separately after freeze.

After real approval and one launch, download retained evidence, independently
replay v2 trajectories and lifecycle/cleanup checks, archive and hash the result,
and reconcile observed usage against the 3,600-second reservation. Account quota
deltas are estimates; exact billed usage remains unknown unless provider evidence
establishes it. A successful infrastructure run does not complete Phase 4 or
justify promoting the treatment.
