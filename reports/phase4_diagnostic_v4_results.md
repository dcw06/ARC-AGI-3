# Diagnostic v4 R1 passed

Kaggle version 1 reported COMPLETE, observed 2026-09-19 09:28:45 UTC.
The notebook and independent archived-evidence replay both passed. All 45
diagnostic requests and the startup canary completed. Startup-inclusive final
runtime was 612.344 seconds (10m 12s), within the 3,300-second internal deadline
and requested 3,600-second provider timeout. Model startup took 462.160 seconds;
the 45-call diagnostic window took 19.944 seconds.

The 1,821 retained monitor samples pass coverage validation. Monitored and
independent GPU cleanup, process-group termination, scratch removal, dependency
removal and source removal passed. The independent GPU probe found zero remaining
processes. Local replay verified the source lock, notebook artifacts, telemetry
chunk hashes, response/token audits, target comparison, and final receipt hashes
for evaluation and dependency cleanup.

## Example-coordinate result

All 45 actions exactly match the previous v2 R2 diagnostic. Each arm covers the
same 15 initial development observations, with clicks legal in 11. Each arm
produced three clicks; all other actions were unchanged across arms.

| Game | Original examples | Relocated examples | No concrete examples |
| --- | --- | --- | --- |
| ft09-0d8bbf25 | (12,34) | (47,9) | (32,16) |
| vc33-5430563c | (12,34) | (47,9) | (59,25) |
| s5i5-18d95033 | (12,12) | (10,10) | (11,10) |

For the first two games the output follows the injected example coordinates in
both runs. This supports reproducible prompt-example copying for those initial
decisions. The diagnostic does not prove all clicks are copied, that selected
coordinates are useful, or that removing examples improves level completion.
It executes no game actions and observes no resulting transitions or levels.
Repeating the same cases is evidence of reproducibility, not additional game coverage.

## Retention and accounting

Archive: `evidence/phase4-diagnostic-v4-r1-passed-v1.zip` (2,101,637 bytes).
SHA-256: `9b7a4dd9f71e4288760abe7fc19c78e28f0dd565e0ff8177e08f35175825483a`.
Source/evidence bindings are in `reports/phase4_diagnostic_v4_evidence_lock.json`;
local verdict and per-game comparisons are in `reports/phase4_diagnostic_v4_evaluation.json`.
Replay locally with the configured Linux environment:

```bash
python -m scripts.replay_phase4_diagnostic_v4
```

Account usage increased from 829.088 to 1,450.542 seconds, an observed delta of
621.454 seconds (10m 21s), and account reserved time is zero at the terminal
observation. This is not exact per-job billing. The raw SDK quota serialization
has duration inconsistencies; both raw and parsed observations are retained in
`reports/phase4_diagnostic_v4_usage_reconciliation.json`. Exact billing remains open.
The one-attempt claim is consumed; no retry or additional compute is authorized.

The next solving investigation should separately test action selection without
concrete examples against actual game transitions. This report does not authorize
that experiment. No full pilot, advanced scheduling, production C_admit or
one-scorecard/110-distinct-game certification is justified by this diagnostic alone.
