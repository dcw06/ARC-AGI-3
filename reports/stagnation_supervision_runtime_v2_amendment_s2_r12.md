# Track 3 amendment S2: package r12 verified and the self-review sample drawn (sanitized)

**Status.** This is a GPU-disabled, offline record, and it authorises no run. Both sessions are complete and accepted,
and no further session or GPU run is authorized. Outcomes stay withheld until the self-review is annotated and
committed.

**What changed (amendment S2, frozen protocol §14a).** Block 2 replayed block 1 exactly, so on October 12 the owner
decided:
- **Self-review.** It draws from distinct trajectories only.
- **Pooled evaluation.** The frozen pooled analysis is reported as written, labelled as overstating precision. The
  same quantities over distinct trajectories (`pooled_distinct`) form the interpretive headline.
- **The §8.6 verdict** stays the frozen one.

The code is in `5d536ae`, with nine regressions in `tests/test_ssv_runtime_v2_amendment_s2.py`.

| Item | Value |
|---|---|
| Public review snapshot r12 | `notebooks/stagnation-supervision-v1-runtime-v2-review-r12/`, lock `519adcb2de4e7726a688a74274f0d250461f4d57272f5d43202646d1627acdfc`. Payload bindings identical to r11 (154); review documents differ only in the five S2 files (frozen protocol text, `pooled.py`, `selfreview.py` and their two scripts) |
| Private review snapshot r15 | lock `319977e0ad4288d1a0468ae1b84dd069f9f6766d9405404ac279e95c8e80ce17`; differs from public r12 only in the runtime protocol's four private bindings; payload bindings equal private r14, the package both sessions ran |

## Verification (CPU; read-only; no provider call)

| Check | Result |
|---|---|
| CPU suite r16 (`..._local_checks_r16.json`, CPython 3.12.3, commit `bcf4a8f`) | 313 tests (160 historical, 153 runtime v2, including the S2 regressions and the end-to-end pooled rehearsal), 0 failures, errors or skips; all seven receipt checks pass |
| Public review check r12 | passed |
| Private review check r15 | passed |
| Session 1 re-evaluated under private r15 | technically complete and accepted, 0 problems; identical to the r14 record apart from the evaluating lock; SHA-256 `cb178c6c…` |
| Session 2 re-evaluated under private r15 | technically complete and accepted, 0 problems; identical to the r14 record apart from the evaluating lock; SHA-256 `fd1de670…` |
| Session-2 execution lock | binds the r14 session-1 record (`29001aa9…`), which the r15 re-evaluation equals apart from the lock; the pooled evaluation checks this chain |

The staged rehearsals were not rerun: the payload bindings are identical to r11's, which passed them.

## Self-review sample (amendment S1, drawn under S2)

- **Draw.** Seed `stagnation-v1-selfreview`, by the committed script from the decision-point lists only; no
  arm-level summary was computed.
- **Exclusions.** 12 exact block-2 duplicates; the exclusions are bound in the sample.
- **Size.** 103 items. Strata with fewer candidates than their quota were taken whole, and the shortfall is
  recorded.
- **Binding.** Sample digest `1d46ed5717185ba00f1b6e7f75ea4dd77eb0dc54306f75dda6dcce0c1cfee4ad`. The sample and the
  empty annotation template stay private.

Next, the sample is annotated, and the annotations are committed privately and hashed. Only then is the pooled
evaluation run.
