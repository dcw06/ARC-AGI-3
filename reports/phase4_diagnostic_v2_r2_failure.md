# Diagnostic v2 R2: evaluator rounding failure

Kaggle version 1 reported ERROR, observed 2026-09-19 06:32:00 UTC. The
notebook finished its failure/cleanup path after 820.074 seconds (13m 40s).
This was an evaluator arithmetic failure after successful model work.

All 45 requests completed with retained responses and token audits; the startup
canary passed with 46 prompt tokens and 29 completion tokens. Offline installation
passed in 138.351 seconds. Model startup took 657.349 seconds. The diagnostic
request window ran from 797.5437325989999 to 817.539367565 seconds, about 20 seconds.

The worker stored cutoff `(began + 1200) - origin` as 1997.5437325990001.
The evaluator computed `(began - origin) + 1200` as 1997.543732599.
Their difference, 2.2737367544323206e-13 seconds, triggered the strict upper-bound
check. The original evaluator replay produces exactly `request window`.
The entry wrapper then propagated failure and finalization correctly retained a
failed notebook receipt. No original receipts or frozen source files were changed.

## Cleanup and evidence

The supervisor recorded verified process cleanup, scratch removal, monitored GPU
cleanup and independent GPU cleanup. The independent probe found zero remaining
processes and absent owned groups. Dependency trees and notebook source were
removed. The retained monitor has 2,562 samples; its coverage passes both replay
evaluators. The failed output is archived as
`evidence/phase4-diagnostic-v2-r2-failed-v1.zip`, hash-bound by the v3 review lock.

## Offline correction and validation

`certification/phase4_diagnostic_v3/evaluate.py` is an offline-only revision of the
v2 evaluator. Only the reconstructed 1,200-second duration limit permits a fixed
four-ULP representation allowance based on the configured 3,300-second budget
plus 1,200 seconds (about 3.64e-12 seconds). Actual completion must remain strictly
before cutoff; the absolute cleanup-reserve boundary remains strict. Nonfinite,
boolean and negative times are rejected. No runtime deadline or GPU source was
changed, and no new launch package or compute authority was created.

Three regression tests pass, including archived-evidence replay and negative
cases for real duration overrun, absolute reserve overrun, completion at/after
cutoff, invalid times, missing cleanup, incomplete inventory and token mismatch.
The v3 offline replay passes all evaluator checks. Source/dependency/evidence
hashes are frozen in `reports/phase4_diagnostic_v3_review_lock.json`; the replay
is `reports/phase4_diagnostic_v3_replay.json`.

The historical Kaggle job and notebook finalization receipt remain failed.
The new verdict is acceptance of retained evidence by a revised offline evaluator,
not a retroactive successful notebook execution or production certification.

## Three-arm observations

Each arm covered the same 15 initial game observations, 11 with clicks legal.
Each arm produced three clicks. Baseline used (12,34) twice; relocated examples
used (47,9) twice; no-concrete-examples used neither example coordinate.
Both modified arms changed three actions relative to baseline, with no action-type
switches. These paired initial-decision results support prompt-example sensitivity
in this small sample, not improved solving, trajectory performance or capacity.

## Accounting and next gate

The one-attempt claim remains consumed and automatic retries remain prohibited.
The terminal account snapshot reports no reserved GPU time. Its parsed account
usage increased from zero to 829.088 seconds (about 13m 49s), but the SDK's raw
quota serialization contains malformed/discrepant duration strings. These are
account-level observations, not an exact per-job bill. Exact billing reconciliation
remains open; no reusable GPU credit or new authorization is inferred.

Review the offline correction and paired responses before any further experiment.
No GPU rerun is needed for this correction. Production one-scorecard/110-distinct-game
certification, production C_admit and solving effectiveness remain unresolved.
