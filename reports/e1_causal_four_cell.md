# E1 four-cell version 5 report

Date: 2026-09-11

Status: complete and valid as descriptive shared-resource evidence; sparse/tied
and provisional. It is not sufficient for a causal factorial claim. This report
does not claim that representation F or safe operations improved score.

## Design and evidence

The experiment executed the frozen 2x2 design over representation R/F and
harness E1S/E1C. All four cells used the same Qwen3-VL-30B-A3B-Instruct-FP8
artifact and revision, vLLM 0.19.0, non-thinking mode, 15 development games,
per-game environment/model seeds, five folds, one-transition visible
compaction, and the eight-worker `minimum_fair_v1` queue. R exposed only the
latest final frame and no raw or derived intermediate-frame evidence. F exposed
R plus the registered E0F features derived from bounded intermediate-frame
sequences; raw intermediate frames were not directly model-visible.

Each cell was a separate complete 15-game workload, but its eight game clients
shared one inference queue. The four treatment workloads ran once in fixed order
E1S-R, E1S-F, E1C-R, E1C-F. Consequently the correct mode is
`shared_resource_whole_run`, the randomization and uncertainty unit is a paired
complete-workload run block, and version 5 contains only one non-counterbalanced
block. The per-game calculations below are retained as diagnostics and cannot
be resampled as independent inferential units.

Kaggle kernel version 5 completed on an NVIDIA RTX PRO 6000. The canonical JSON
is `reports/e1_results/e1-causal-four-cell-v5.json`, SHA-256
`f186192705e061734bf7bb93dd64f2afbe2f5538eaf828a04a123fca9515eb9d`.
The downloaded kernel and server logs have SHA-256
`e1cda188b0a675cfde7b1d24439098e7fbcf66a0d74bc01f55da8bcf700ac3da`
and `d98a174119cd1c4fb10097a0bb428925a7ea408700a6edcb3c9dc7db41fac078`.

Every cell had acknowledged scorecard finalization. All model requests
completed, with zero transport failures, zero queue failures, and zero parser
repairs. The model artifact, GPU, package binding, completion canary, game
order, seeds, folds, request ceilings, workspace ceilings, and queue bounds all
passed independent local recomputation.

## Cell results

| Cell | Mean official RHAE % | Requests/completions | Workspace calls | Policy failures | Elapsed seconds |
|---|---:|---:|---:|---:|---:|
| E1S-R | 0.0 | 1049/1049 | 0 | 162 | 1330.74 |
| E1S-F | 0.0 | 1078/1078 | 0 | 36 | 3989.65 |
| E1C-R | 0.0 | 2452/2452 | 2381 | 1012 | 1549.80 |
| E1C-F | 0.0 | 1092/1092 | 355 | 362 | 4314.94 |

All 60 game-cell scores were zero. Missing, crash, and timeout outcomes were
charged as the frozen zero value; no score was silently excluded.

## Diagnostic factorial decompositions

| Contrast | Mean effect | Nonzero game pairs | Exact two-sided p | Status |
|---|---:|---:|---:|---|
| Representation F minus R | 0.0 | 0 | unavailable | Provisional |
| Safe operations C minus S | 0.0 | 0 | unavailable | Provisional |
| Difference-in-differences interaction | 0.0 | 0 | unavailable | Provisional |

All decompositions are zero. Independently of that tie, game-level sign flips
are not valid inference for this shared-resource execution. No factorial
acceptance or null-effect claim is supported.

## Selection and operational interpretation

The cross-fitted selection-procedure diagnostic is 0.0. Every fold selected
E1S-R by the frozen tie-break order; the final fixed E1 candidate is therefore
E1S-R with descriptive development mean 0.0 and status `Provisional primary`.
This E1-internal diagnostic selection is not a causal estimate. It is now the
Phase 1 `Provisional primary` under the frozen tie-break, without an acceptance
or superiority claim.

The complete experiment took 11,346.80 seconds, below the 27,540-second
(7.65-hour) operational envelope. Model readiness took 137.11 seconds. Peak
VRAM was 77,538,000,896 bytes and peak RAM was 14,462,169,088 bytes. The
completion canary passed before the first scorecard.

## Corrective whole-run design

`config/e1_whole_run_protocol.yaml` freezes two paired complete-workload blocks
with exactly reversed treatment order. Every one of the eight treatment runs
starts a fresh vLLM process, inference queue, Arcade/session set, and policy
state, so prefix-cache and process state cannot cross treatments. Factorial
uncertainty is computed only across paired whole-run blocks; per-game values
remain diagnostic. The projected duration is 23,330.02 seconds, leaving
4,209.98 seconds inside the 27,540-second envelope. Execution is pending.
