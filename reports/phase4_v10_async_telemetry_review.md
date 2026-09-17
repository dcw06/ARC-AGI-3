# V10 asynchronous telemetry repair

Implements the fix specified in the v9 failure report. Sampling submits measurements to a single bounded writer thread instead of waiting for filesystem persistence. No sample is dropped or downsampled. The writer batches available records while retaining their order and uses the existing lossless chunk format and evidence budget.

The pending queue includes in-flight samples and is limited to 32 samples, five seconds of pending age, and 8,192 encoded bytes per item. Writer exceptions, overflow, excess age, or final drain timeout fail the attempt. The one-second maximum sampling gap and all GPU/RAM/scratch limits remain unchanged. This separates filesystem waits from sampling; it does not guarantee immunity from CPU scheduling, Python thread contention, slow probes, or persistent storage overload.

Readiness is published only after a durable initial checkpoint. The writer holds that checkpoint until the supervisor acknowledges its validation, preventing a concurrent chunk/manifest update during the readiness read. Sampling continues into the bounded queue during this handshake. Final monitor success requires every queued sample to be persisted within the remaining lifecycle deadline. Independent GPU cleanup from v9 remains in place and cannot restore lost monitoring coverage.

Persistence timings now distinguish encoding/compression, chunk writes, manifest writes, evidence-lock wait, inventory scan, write/flush, fsync and replacement. Recent writer timings and queue state are available in failure context; final writer statistics are retained with monitor results. OS-level stalls can still delay a failure receipt, so the existing external process/deadline supervisor remains necessary.

Validation: 20 asynchronous/staging/bridge/review tests passed in 15.842 seconds, plus eight inherited monitor-diagnostics/independent-cleanup tests in 1.248 seconds. The 1.42-second delayed-write test retained every sample while sampling gaps remained below one second. Tests cover queue overflow, pending age, writer failure, drain timeout and immutable readiness checkpoint acknowledgement.

The complete native-Linux CPU-only pilot passed: 110 clients, 7,722 requests, 83.853 seconds, request/action invariance and cleanup verified. It uses scripted completions and injected GPU telemetry; it is not target model or capacity evidence. Portable local evidence: `evidence/phase4-v10-local-review.zip`, SHA-256 `4b5d9d191f814edac997c3cd418930166dd883405ac0642b2adabe99c42428a4`.

Source review lock SHA-256: `7e4411c9c697c78d6d030fc719e6bdfa8f1a0aba2cd6227609b4801b33de6047`. The review notebook remains GPU-disabled; the separate launch package embeds the fresh authority sidecars. Historical v7–v9 source bindings were verified unchanged.

The user explicitly authorized one GPU launch after the repair. Attempt `p4-v10-pilot-20260917T153958Z` has its own 28,800-second reservation, 27,540-second internal deadline, and no automatic retry. Target validation and final usage reconciliation remain outstanding until the provider run terminates and its outputs are evaluated.
