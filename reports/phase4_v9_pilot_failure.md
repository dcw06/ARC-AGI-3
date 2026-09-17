# V9 submission and runtime failure

The first user launch succeeded: Kaggle accepted version 1 at 2026-09-17 15:21:22 UTC. A subsequent invocation encountered exclusive-creation `FileExistsError`. The start command now detects an existing launch claim or receipt, prints its recorded submission and monitoring command, and exits without another upload. Partial preparation without a claim is reported explicitly for inspection.

Kaggle subsequently reported `ERROR`. Staging and installation passed. The monitor retained an exact sampling-gap violation: 1.68481043 seconds against the unchanged one-second maximum. The preceding telemetry persistence took 1.420735037 seconds, whereas the next GPU, RSS and scratch probes took approximately 0.0112, 0.00246 and 0.000315 seconds. These measurements identify telemetry persistence as the dominant contributor to this gap; the receipt does not distinguish lock contention, directory traversal, compression or filesystem synchronization within persistence.

RSS and scratch remained below their limits. Independent post-termination GPU cleanup passed with zero remaining compute processes, and owned-process/scratch cleanup passed. The run remains failed because that cleanup cannot restore continuous monitoring coverage.

The next repair should isolate sampling from slow evidence persistence while retaining bounded, lossless evidence and failing on backlog or writer failure. Investigate persistence substage timing; do not simply relax the one-second sampling requirement. No replacement GPU attempt was submitted.

Preserved evidence and account usage reconciliation: `reports/phase4_v9_pilot_evaluation.json`. The consumed reservation remains retained; account quota changes are not exact per-run billing.
