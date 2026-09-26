# Evidence comprehension v1: runner and review package r2

**Status:** GPU-disabled review snapshot. Authorized seconds are zero. There has been no
reservation, upload or model call. This package is for an independent review. Source approval and
a separate compute authorization would follow only after that review.

The protocol is `reports/evidence_comprehension_v1_protocol.md` (revision 5). Package r1 (`0b0e453`,
lock `866bffdb…354e`) is preserved in `notebooks/evidence-comprehension-v1-review-r1/`.

## Changes in r2 (review of package r1)

Each finding was first reproduced on r1's code, then fixed with regressions:

| Finding | On r1's code | Fix and regressions |
|---|---|---|
| Call validation accepted impossible metadata | These mutations produced no call errors: both prompt counts −1; completion −5; completion and finish reason missing; finish `length`; a call from 3,290 s to 3,350 s | Independent validation of token bounds, finish reason, cache counters, host timing and ordered in-bound timestamps against the frozen limits. Truncated (`length`) responses are always scored invalid. Twelve re-hashed mutation regressions, all rejected with the evidence still verifying. |
| Idle and metrics checks did not enforce a total deadline | A 1.0 s idle window returned success after 1.45 s | Absolute deadlines across inference, teardown, each metrics read, idle verification, the post-answer cache check and the bridge reply; late observations are rejected. New regressions: a slow reader, trickling metrics, and the caller's deadline overriding the timeout. New rehearsal faults (slow abort, late abort, trickling metrics, late reply) on the connected path. |
| Cache verification trusted a flag | `prefix_caching_disabled_verified: true` was accepted alongside 999 queries and 999 hits | The verdict is recomputed from counters for the canary and every answered call. The cancellation verdict is recomputed from its measurements and timings. Regressions: forged server record, forged per-call counters, a stale prompt counter, and forged cancellation receipts. |

## What the review of r3 asked the rehearsal to show, and where it is shown

| Requirement | Where it is shown |
|---|---|
| Prefix caching is disabled in the running server | Connected rehearsals: server evidence checked after the canary and after every answer; a caching-enabled server is refused before any question (`test_prefix_caching_enabled_is_refused_before_any_question`) |
| Timeouts cancel server-side work, not just the wait, within an enforced time | A hung call reaches the 2 s rehearsal deadline; the fake server logs the abort; the host observes the server idle and keeps a cancellation receipt (`test_timeout_cancels_server_side_work`). A server that ignores the disconnect fails idle verification and stops the run (`test_server_that_ignores_cancellation_stops_the_run`). A slow abort inside the window is verified. A late abort, a trickling metrics endpoint and a late bridge reply each stop the run within the per-call bound (`test_slow_abort_within_the_window_is_verified`, `test_late_abort_trickling_metrics_and_late_replies_stop_within_the_bound`). |
| Interruptions keep evidence and report an incomplete gate | Deadline interruption in gate pass 1 and in gate pass 2, on the connected path. Evidence verifies, the gate is `incomplete`, and the last call returns before the cutoff (`test_deadline_interruption_in_each_gate_pass`). |
| Cleanup, logging and storage failures stay bounded | HTTP failure, storage exhaustion, cancellation, monitor exit, model startup failure and log flood each fail within seconds. Process groups and scratch are cleaned, and partial evidence stays verifiable where any was written (`test_failures_are_bounded_cleaned_and_keep_honest_evidence`). A SIGTERM-ignoring child is removed (`test_surviving_child_is_cleaned_up`). |
| The evaluator reconstructs scores from retained responses | Editing one retained response changes the evaluator's score by exactly one. Forged request hashes, out-of-order calls and broken token parity are rejected, and nothing is scored from them. A run missing its second-pass calls is `incomplete` (`test_normal_run_and_scores_come_only_from_retained_responses`). |
| Missing evidence cannot pass the gate | Pass-identified analysis regressions (zero passes, one pass, empty passes, interrupted passes, a single missing answer), plus the truncated connected run above. |

## Live path

The live path reuses the reviewed action-effect-history lifecycle: the launcher, the first-cell
supervisor, externally owned worker and monitor process groups, the gated release, the bridge and
the atomic evidence with a hash manifest. The experiment-specific pieces are:

- **`transport.py`**
  - a total-deadline HTTP transport that shuts the connection down on expiry;
  - a Prometheus metrics reader;
  - idle verification;
  - the positive check that prefix caching is disabled.
- **`service.py`**
  - serves only requests whose hash is in the frozen probe set, and at most 1,308 of them;
  - a single canary, with caching verified off after it and after every answer;
  - a cancellation receipt after every timeout, or a refusal of every later call if the server does
    not go idle.
- **`host.py`:** the pinned vLLM server with exactly one derived flag change
  (`--no-enable-prefix-caching`), with the derived argv retained.
- **`worker.py`:** validates the host's server evidence before any question, then runs the
  questionnaire on the shared first-cell clock.
- **`runner.py`**
  - follows the schedule module's order and admission rule;
  - writes one atomic file per call;
  - never scores anything.
- **`scripts/evaluate_evidence_comprehension_v1.py`**
  - lifecycle checks against the frozen limits;
  - server evidence;
  - binding of every call to the frozen order and requests;
  - cancellation receipts for every timeout;
  - scoring of the retained responses only, analysed by identified pass.

Rehearsal mode runs the same code, with the CPU fake server over real local HTTP, the fixture
tokenizer, an injected GPU identity, a 2 s call timeout and a 3 s idle window. It requires
`ECV_REHEARSAL=1` and no visible GPU.

## Known intermittent result

While preparing r2, the connected suite ran three times. One run had a single failing test out of 10;
the other two passed all 10, as did the final full check (67 tests). That run's report kept only
counts, so the failing test was not identified. The run was noticeably slower (814 s against 604 s),
which suggests a timing-sensitive assertion under load, but that is not established. The check now
records each failure's test name and traceback in `reports/evidence_comprehension_v1_rehearsal_results.json`,
so any recurrence is identifiable.

## What the local evidence cannot show

- **Real behaviour of vLLM 0.19.0 on the target GPU.** Whether the abort actually lands, and how
  fast the metrics return to idle, can only be observed live. The live run checks both itself and
  stops if either fails. The fake server imitates the documented behaviour; it is not evidence of it.
- **Runtime of the cache-disabled workload.** It is unmeasured. The budget scenarios are planning
  figures, and the runner's admission control, not the estimate, protects the cleanup reserve.
- **Model answers.** The fake server's answers are scripted, so the rehearsal labels are not results.

## How to verify

```sh
python -m scripts.check_evidence_comprehension_v1          # every local suite; rewrites the rehearsal results
python scripts/review_evidence_comprehension_v1_notebook.py --folder notebooks/evidence-comprehension-v1-review-r2
```

The review script does four things:
1. Checks every binding and the metadata (private, offline, GPU off).
2. Executes the frozen notebook cell and requires a `PermissionError` before installation, with no
   extracted source left behind.
3. Executes the same cell with only `MODE` switched to rehearsal. The full connected questionnaire
   must pass the independent evaluator.
4. Runs the actual snapshot through approval, reservation and packaging, and checks the packaged
   authority gate.
