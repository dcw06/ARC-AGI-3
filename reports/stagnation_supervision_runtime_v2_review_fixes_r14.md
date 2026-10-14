# Track 3 amendment S2: second review fix, malformed nested inputs (sanitized)

**Status.** This is an offline, CPU-only record. No GPU run, upload, reservation or launch was made or authorized.
- **Preserved.** The GPU evidence, retained session records, both earlier pooled analyses and every published report
  are untouched.
- **Outcome.** No numerical conclusion changes.

## The finding (P2) and the fix

A second review of `18455f9`, `9d25d1f`, `4421a60` and `0f0dc40` found that malformed inputs could still crash the
evaluator:
- an execution lock whose `session1_evaluation` was a list (`[1]`) raised `AttributeError`;
- a retained record containing `NaN` crashed the canonical comparison.

The fix (`a800063`; review snapshot r14, `e59e07e`):
- **Strict reader.** Every evaluation input is read by `selfreview.strict_json`, which rejects `NaN`, `Infinity`,
  `-Infinity` and numbers that overflow to infinity before any comparison. That covers the retained session records,
  the execution lock, the launch-time record, the annotations, the commitment receipt and the committed blobs. A
  rejected file is reported as "unreadable or malformed".
- **Execution binding.** The execution lock's `session1_evaluation` must be an object holding a lowercase 64-hex
  SHA-256. Anything else is reported as a validation failure.
- **Nested structure.** The annotations must be lists of objects (`validate`). The commitment receipt must be an
  object with string `commit` and `repository` fields (`verify_commitment`).

**Regressions** (`MalformedNestedInputs`). Each requires a reported failure and no pooled result. They fail on
`4421a60`: the old code crashes with `AttributeError` or on the non-finite comparison, or, for a `NaN` in the
annotations, silently produces a pooled result.
- **Execution bindings:** `[1]`, `null`, a string, `{}`, a non-string digest, a short digest, an uppercase digest and
  a list digest, each with and without a launch-time record.
- **Non-finite numbers:** `NaN`, `Infinity`, `-Infinity`, `1e999` and `-1e999` in either retained record, the
  launch-time record and the execution lock.
- **Annotations and receipts:** annotations whose items are not objects, annotations that are not an object, and a
  `NaN` in the annotations; commitment receipts that are a list, have a non-string commit or repository, or hold a
  `NaN`.
- **Direct checks** of `validate` and the strict reader.

## Verification and reproduction (CPU; private inputs read-only)

| Check | Result |
|---|---|
| CPU suite r18 (`..._local_checks_r18.json`, commit `e59e07e`) | 331 tests (160 historical, 171 runtime v2), 0 failures, errors or skips; all seven receipt checks pass |
| Public review snapshot r14 | lock `f01ee748924529414ef8eb43358d37d1bf40fadc2cd45761e103945fa7726546`; payload bindings identical to r13 (154); review documents differ only in `pooled.py` and `selfreview.py` |
| Public review check r14 | passed |
| Private review snapshot r17 | lock `f521f5cdf49b27a6564729253141a5c75d4129797086e1e064c48e8e268963d5`; differs from public r14 only in the four private bindings; payload equals private r14, the package both sessions ran |
| Both sessions re-evaluated under r17 | technically complete and accepted, 0 problems; identical to their r14 and r16 records apart from the evaluating lock |
| Corrected pooled analysis under r17 | binding checks and committed-sample equivalence pass; equal to the first corrected analysis (r16) apart from the session records' hashes; verdict inconclusive |
| Against the original analysis (`47fd9d07…`, rerun byte-identically) | 33 items identical, including every rate, interval, count, level, exclusion and the verdict; only the counts-derived limitation sentence differs, as in r16 |
| Against the independent reproduction | all 19 checks agree, including actual spend equal to the run totals |
