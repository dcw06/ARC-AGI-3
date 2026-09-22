# Coordinate diagnostic v2: complete, wording threshold not met

Kaggle version 1 completed. Frozen independent replay passed with no errors,
including all 56 requests, retained response hashes, token parity, canary,
monitor coverage, deadlines, evidence bounds, and final independent cleanup.
The tokenizer-manifest repair succeeded on target. This is diagnostic evidence,
not gameplay improvement, a capacity admission result, or Phase 4 completion.

## Outcomes

| Condition | Correct | Transposed color | Other valid | Malformed / transport |
|---|---:|---:|---:|---:|
| Baseline | 15/28 (53.57%) | 3 | 10 | 0 / 0 |
| Explicit indexing | 16/28 (57.14%) | 2 | 10 | 0 / 0 |

Paired correctness: two improvements, one regression, 25 unchanged. The frozen
clarification threshold is not met: net gain is one rather than at least four,
and transpose matches fall by one rather than at least four. Only one retained
source improves and another regresses. Do not promote the wording change.

| Source | Baseline correct | Explicit correct |
|---|---:|---:|
| ar25 retained 64x64 | 1/4 | 2/4 |
| ft09 retained 64x64 | 3/4 | 3/4 |
| ls20 retained 64x64 | 2/4 | 2/4 |
| sc25 retained 64x64 | 1/4 | 0/4 |
| Synthetic 8x8 | 4/4 | 4/4 |
| Synthetic 16x16 | 2/4 | 2/4 |
| Synthetic 32x32 | 2/4 | 3/4 |

Both conditions score 7/16 on retained 64x64 boards. The predeclared size-related
lead is met: synthetic 8x8 accuracy is 100% in both conditions, exceeding retained
accuracy by 56.25 percentage points. This does not isolate size as the cause:
content, distribution, and input length also differ; there is only one synthetic
grid per size. The 16/32 results are not monotonic. Boundary accuracy pooled over
conditions is 24/28 versus interior 7/28, a descriptive lead, not a new acceptance
threshold or causal proof. Questions sharing a source are correlated.

The evidence favors investigating reliable extraction/indexing within larger raw
grids over treating coordinate-convention clarification alone as a remedy. A next
proposal should isolate one representation/grounding change and use matched
underlying grids. No new experiment or model call is authorized by these results.
Correct color reading would still not establish useful action selection.

## Evidence and reproducibility

All 23 downloaded files (3,227,382 bytes) match the download manifest. The archive
also retains provider observations and seven approval/launch/reservation receipts.
Archive: `evidence/phase4-coordinates-v2-r1-completed.zip`.
SHA-256: `afc7c4482c6d0bb37033b11101639e86d7c7f207e4426bca2e5cf1d14ba67440`.
Member hashes: `reports/phase4_coordinates_v2_completed_archive.json`.
Independent result: `reports/phase4_coordinates_v2_pilot_evaluation.json`.

Read-only replay from a checkout using the project's CPU dependency environment:

```bash
python scripts/check_phase4_coordinates_v2.py --live-manifest reports/phase4_coordinates_v2_completed_archive.json
```

No credentials, ignored downloaded files, model weights, or GPU are required.
The command verifies the frozen source/artifact lock, regenerates source-bound
cases, checks every archive member, and independently evaluates the final output.
Historical v1 source and its failed attempt remain unchanged.

## Usage and closure

One consumed attempt: `co2-a6d2e62a2d134105bb1603c67efce868`.
Provider ceiling 2,100 seconds; internal ceiling 1,980 seconds.
Notebook elapsed: 632.562242186 seconds. Model startup: 492.258276060 seconds;
request window: 7.152484869 seconds. All 56 diagnostic calls plus one canary ran;
zero environment actions, scorecards, or automatic retries.

Diagnostic tokens: 299,768 prompt and 413 completion. Canary: 46 prompt and 29
completion. Total: 299,814 prompt and 442 completion. Diagnostic service latency
median 0.078032 seconds, maximum 0.640686 seconds; these exclude model startup
and the separate 23.919922-second canary call.

Independent cleanup found zero remaining owned GPU processes and absent process
groups; scratch, dependency trees, and extracted source were removed. Account SDK
usage changed from 5,496.679 to 6,139.137 seconds (delta 642.458), with zero provider
reserved time at the terminal observation. This account-wide delta is not exact
per-attempt billing. Malformed raw duration strings and SDK/raw allowance
disagreement remain unresolved. Exact billed seconds remain null; the local
reservation stays consumed and no unused budget is reauthorized.

Production one-scorecard/110-distinct-game certification, workload-specific
admission limits, and exact accounting remain open.
