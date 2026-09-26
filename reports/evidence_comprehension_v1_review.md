# Evidence comprehension v1: runner and review package r1

**Status:** GPU-disabled review snapshot. Authorized seconds are zero. There has been no
reservation, upload or model call. This package is for an independent review. Source approval and
a separate compute authorization would follow only after that review.

The protocol is `reports/evidence_comprehension_v1_protocol.md` (revision 4).

## What the review of r3 asked the rehearsal to show, and where it is shown

| Requirement | Where it is shown |
|---|---|
| Prefix caching is disabled in the running server | Connected rehearsals: server evidence checked after the canary and after every answer; a caching-enabled server is refused before any question (`test_prefix_caching_enabled_is_refused_before_any_question`) |
| Timeouts cancel server-side work, not just the wait | A hung call reaches the 2 s rehearsal deadline; the fake server logs the abort; the host observes the server idle and keeps a cancellation receipt (`test_timeout_cancels_server_side_work`). A server that ignores the disconnect fails idle verification and stops the run (`test_server_that_ignores_cancellation_stops_the_run`). |
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
python scripts/review_evidence_comprehension_v1_notebook.py --folder notebooks/evidence-comprehension-v1-review-r1
```

The review script does four things:
1. Checks every binding and the metadata (private, offline, GPU off).
2. Executes the frozen notebook cell and requires a `PermissionError` before installation, with no
   extracted source left behind.
3. Executes the same cell with only `MODE` switched to rehearsal. The full connected questionnaire
   must pass the independent evaluator.
4. Runs the actual snapshot through approval, reservation and packaging, and checks the packaged
   authority gate.
