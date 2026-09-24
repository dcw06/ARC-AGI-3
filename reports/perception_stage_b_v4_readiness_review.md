# Stage B R4 readiness and target-boundary review

Status: **GPU disabled, review-only, no source approval, compute authorization,
reservation, or target attempt.** R1–R3 snapshots remain historical.

The game-side `connect_ready` now independently verifies the exact frozen
ACTION6 canary request and its SHA-256, the complete bounded response body and
its hash/byte count, a legal action, matching positive tokenizer/server prompt
counts, completion count within 128, `finish_reason="stop"`, exact expected
artifact identity, and startup at or below 900 seconds. Mutation tests reject
each missing or changed field, including a fabricated 64-character hash and a
901-second startup. Admission remains closed on rejection.

A new Stage B-only authority module binds a future launch review lock, separate
source and compute approvals, an execution lock, and one 3,600-second
reservation. It rejects missing, drifted, and consumed records before a runtime
claim. The future launch review lock does **not** exist in this revision, so
real authority cannot pass. The host, monitor, worker, and supervisor check
this gate before model import, subprocess creation, or GPU probing.

The source now includes a pinned-host entrypoint, an isolated-interpreter game
worker, real GPU probe adapter, monitor loop with durable first-sample
readiness, and independent GPU cleanup verdict. The trajectory runner can
write through the historical shared bounded evidence store. CPU tests exercise
the resource and monitor seams with injected telemetry; they are not target GPU
evidence. The existing external CPU rehearsal still proves bridge and process
group cleanup with scripted responses.

**Remaining before a launch review:** connect these components in a Stage B
external *live* supervisor. It must gate and claim before installation, launch
distinct pinned game/model interpreters under owned process groups, supervise
the real monitor through success and every failure, bound all logs and
trajectory evidence, enforce first-cell 3,300-second and 3,000-second
admission deadlines with a 300-second cleanup reserve, verify groups and GPU
processes independently, and retain a failure receipt even if readiness never
appears. Independently test startup failure, cancellation, evidence exhaustion,
deadlines, and cleanup failure. Re-audit exact target requests and unpack and
inspect a **new launch package** before requesting source approval or separate
compute authorization. The R4 notebook is only a GPU-disabled source snapshot.

The proposed 3,600-second attempt remains unauthorized. This is a two-action
per-arm development study; equal visible initial observations do not prove
hidden-state equality, and a zero-level result would not establish a general
solving limit or complete Phase 4.
