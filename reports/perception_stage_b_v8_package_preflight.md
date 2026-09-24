# Stage B R2 one-attempt package preflight

Status: **R2 source approved; separate compute authorization pending. No
reservation, launch package, upload, or GPU attempt has been created.**
The proposed source is the frozen Stage B launch
R2 notebook, review lock SHA-256
`2452a94693d37e051bc1b70092e537b316614c56d4dbcdcdc82f33d46d1ba57a`.

The new package tool requires distinct source and compute approval records,
binds both to the exact R2 review lock and compute to source, creates a fresh
one-use execution/reservation pair, and materializes a deterministic private
GPU notebook with embedded, hash-checked sidecars. It validates exact package
bytes before any provider query. The one-shot path checks account quota,
persists a launch claim before upload, consumes the reservation, and never
automatically retries an unknown provider outcome.

Two CPU-only package tests passed using synthetic approvals in a temporary
source copy and a fake provider. They verified successful sidecar extraction
and runtime authority, as well as rejection of missing, mismatched, or
consumed authority, package drift, insufficient quota, and a second launch.
The real repository's `verify` command rejected the absent Stage B approval
records before any provider call, as intended.

Read-only Kaggle GPU quota at preflight: total 108,000 seconds, used
10,687.795 seconds, reserved 0 seconds. This is account-wide availability,
not an attempt reservation or exact billing. The proposed provider reservation
is 3,600 seconds, internal limit 3,300 seconds, at most 12 study calls plus
one canary, two development episodes with two actions each, and no scored
submission or automatic retry.

The user explicitly approved the R2 source; its approval record is
`reports/perception_stage_b_live_source_approval.json`. Next: record a
separate one-attempt compute authorization; reserve once; materialize and independently inspect
the exact GPU-enabled package; then submit once if its quota and package gates
still pass. Neither the reviewed notebook nor this preflight grants launch
authority by itself.
