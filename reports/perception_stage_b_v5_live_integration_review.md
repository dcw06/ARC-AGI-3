# Stage B R5 live-supervisor source review

Status: **GPU disabled; no launch approval, compute authorization, reservation,
or target attempt.** R1-R4 notebooks and locks remain historical.

R5 connects the gated first-cell entrypoint to the split model/game install,
the real-monitor handshake, the externally owned game-worker group, bounded
logs, the shared evidence store, and independent process/GPU cleanup. The
supervisor consumes or verifies the one-use runtime claim before target work.
It retains an outer verdict and GPU cleanup receipt on monitored failures.
The game worker now writes its cancellation marker through the evidence store,
so subsequent writes remain inside the shared 128 MiB inventory.

The local CPU failure rehearsal starts real, isolated process groups with a
sleeping worker and a monitor that exits before readiness. It verifies that
the worker is never released, both groups are reaped, scratch is removed,
and the failure and cleanup evidence remain. The absent-authority test rejects
both target entrypoints before output, subprocess creation, or GPU query.
These injected checks do not establish real target startup or successful game
execution.

The R5 notebook is a hash-locked **source snapshot**, not a target launch
notebook. It does not contain a launch cell, does not enable GPU, and cannot
satisfy the separate Stage B authority gate. The proposed 3,600-second
reservation remains unauthorized.

Before launch review: exercise cancellation after monitor readiness, startup
failure, evidence exhaustion, deadline expiry, and cleanup failure through the
connected supervisor; independently inspect the exact target install and
runtime package, including real-monitor/GPU visibility; re-audit exact policy
and sealed-audit requests against the pinned tokenizer; then build and inspect
a new launch notebook whose source lock binds the executable and budget.
Source approval and a fresh compute authorization must follow that review.

The study remains a two-action-per-arm development case. Equal visible
initial observations do not prove hidden-state equality, and zero completed
levels would provide little evidence about broader solving ability or Phase 4
certification.
