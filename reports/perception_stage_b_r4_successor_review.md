# Stage B successor R4 source review

The first authorized Stage B GPU attempt failed during first-cell import,
before dependency installation. Its frozen R2 notebook omitted
`reports/phase4_torch_wheel_inspection.json`. The prior R2 approval,
reservation, and upload claim remain consumed. See
`reports/perception_stage_b_r1_failure_and_r3_review.md` for the provider
record and download verification.

R4 preserves historical R1-R3 review notebooks and the submitted R2 package.
It adds the missing frozen report to its embedded source and gives any future
attempt distinct source/compute approval records, execution lock, reservation,
launch claim, and notebook ID. The active authority scope is
`phase4-grounded-action-stage-b-live-r2`; the proposed limits remain one
3,600-second provider reservation, 3,300-second internal deadline, at most
12 study calls plus one canary, two development episodes, and no retry.

The GPU-disabled R4 notebook independently verified **1,043 source
bindings**. A subprocess imported the split-install module and torch-wheel
contract from the **unpacked notebook source** without a checkout fallback.
Eight focused CPU tests passed for packaged import, absent/mismatched/consumed
authority, and one-use package behavior. The review notebook rejected
unapproved execution. R4 review lock SHA-256:
`ffe00a09b72d3019f6816d69e293b2d51d353b16a43330f3ab3a437afd9d33`.

R4 is **not approved, reserved, packaged for GPU, or uploaded**. A new
explicit R4 source approval and separate compute authorization are required
before reservation. Then the exact materialized package and quota must be
reviewed before one submission. The prior approval cannot carry over.
