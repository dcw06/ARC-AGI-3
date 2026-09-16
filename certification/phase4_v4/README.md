# v4 — shared-model development integration, review only

This revision adds the real shared-service path to the v3 terminal-aware
development lifecycle. It preserves v1 preparation, the v2 failed run and the v3
local pass. It has **zero authorized compute** and `execution_ready=false`.

## Implemented

- One frozen model service shared by the eight-worker inference queue and 110
  development clients; no changes to E1S-R policy prompts or proposal limits.
- Local-only model artifact/tokenizer loading and model-tree verification.
- Exact, untruncated chat-template tokenization for each real trajectory request;
  context overflow, missing server usage and prompt-token disagreement fail.
- One audited startup canary. Canary transport failure is surfaced without
  being retried by the readiness health-check loop.
- External startup/lifecycle deadlines, RAM/scratch monitoring, exclusive GPU
  UUID binding, retained device telemetry and whole-process-group cleanup checks.
- Final worker checkpoint retention after process termination, with errors
  taking precedence over completion flags.
- Independent evaluator requiring all client/action/finalization evidence plus
  model artifact binding, canary, token-count parity and GPU resource evidence.
- A standard-library-only readiness/approval/reservation gate before dependency
  installation, hardware queries or model startup. The old prescreen ledger is
  not reused, and its retained eight hours provide no credit.

`notebooks/phase4-lifecycle-v4-review/profile.ipynb` is a **review artifact**, not
an approved runnable GPU experiment. Its metadata is private, internet-disabled
and GPU-disabled. Its embedded ledger authorizes zero seconds, so execution stops
at the pre-install gate. It was built locally; nothing was uploaded or launched.
`review-source-lock.json` binds the packaged source, but is not an approved target
execution lock. The builder deliberately does not produce an approved build.

## Validation and limits of evidence

All 10 new unit/integration tests passed, including dynamically audited token
counts, context overflow, missing/mismatched server usage, pre-install rejection
under `python -S`, negative evaluator mutations and mocked GPU supervisor paths.
A combined **34-test sandbox-safe suite** passed. The previously passing real
process-table supervisor tests were not rerun in that combined suite: the
approval service rejected escalation because its usage limit was reached.
Do not describe this as a new 43-test full-suite pass.

GPU telemetry/model responses in these tests are mocked. No actual model has
been loaded for v4, no VRAM result measured and no target performance claim made.
The notebook source compiles and its embedded gate has been checked without
third-party site packages. See `reports/phase4_v4_review_status.json` for hashes.

## Still required before any launch

1. Focused review and fault testing of the real-model worker, external supervisor,
   notebook-level supervision, evidence retention limits and evaluator. The
   absence of a test failure is not a claim that all seams are covered.
2. Clean target-compatible offline installation/import validation, including
   the separately mounted frozen vLLM wheelhouse. The environment-only package's
   earlier resolver dry run is not that validation.
3. A prospective real-trajectory capacity measurement design. Current bounded
   prompt samples are not representative capacity evidence; request durations
   must not be summed as if concurrent service were sequential. `C_nominal` and
   `C_admit` remain null until actual, properly scoped model measurements exist.
4. Approved full execution inventory, an approved notebook build, independent
   allowance verification and a new explicit one-attempt eight-hour reservation.

The evaluator can assess development-model lifecycle evidence, but deliberately
does not close Phase 4 or certify production. This remains 110 clients repeating
15 development games, with separate scorecards and single-episode terminal-loss
handling. Production reset behavior and one scorecard across 110 distinct games
remain separate gates. H1/H2 and advanced scheduling are untouched.

## Local review commands

```sh
.venv/bin/python -m unittest tests.test_phase4_model_integration -q
```

The review builder uses exclusive output creation to preserve the generated
artifact. Do not overwrite it or flip readiness/approval fields to bypass review.
