# Evidence comprehension v1: investigation of the intermittent connected-suite failure

**Status:** cause identified from retained evidence as a race in one rehearsal's design, not a defect
in deadline enforcement, cancellation, cleanup or evidence integrity. No remediation has been applied
yet; see "Next steps". GPU authorization is on hold.

## The three outcomes

All three runs used the same `research/` and `tests/` sources: exactly those committed in `c6f9982`.
The working tree was uncommitted during the runs, based on `0b0e453`. Between runs only the check
script changed (it gained a `problems` field after run B), plus the review guide and the status
report. Host load was not recorded for any run.

The host was WSL2 (kernel 6.18.33.2-microsoft-standard), with 8 CPUs and 8 GB of memory, recorded
the same day after run C.

| | Run A | Run B | Run C |
|---|---|---|---|
| Command | `powershell -File scripts/wsl-python.ps1 -m scripts.check_evidence_comprehension_v1` (stdout to a scratch log; stderr not retained) | `.venv/bin/python -m unittest -v tests.test_evidence_comprehension_v1_connected` (in WSL) | `.venv/bin/python -m scripts.check_evidence_comprehension_v1` (in WSL) |
| Ended (Windows clock, EDT) | 2026-09-26 13:49:57 | 14:10:24 | 14:21:46 |
| Durations | suites 16.8 s / 3.7 s / 20.3 s / **813.6 s** connected | 726.0 s | 17.9 s / 3.7 s / 20.3 s / 603.5 s connected |
| Result | connected: 10 tests, **1 failure** | 10 of 10 passed | all 67 passed |
| Failed test recorded by the runner | **not recorded** (only counts were kept) | — | — |

The WSL wall clock stepped forward by about 37,430 s (about 10 h 24 min) **during run A**. Run A's
rehearsal directories are timed 03:12:43–03:16:55 and then 13:40:58–13:48:30 on the WSL clock. The
Windows clock did not step. Nothing on the live path reads the wall clock: every deadline and elapsed
time is `time.monotonic()`, which I checked with a search.

## Identifying the failure after the fact

The runner did not record which test failed, so at the time its identity was unknown. It has since
been identified from run A's retained evidence. The rehearsal harness keeps every evidence directory,
and all 18 of run A's survive. Three lines of evidence support the identification:

1. **Replay.** Run A's 18 retained outputs were fed, in execution order, through the **unmodified**
   connected tests, with `run_fault` substituted so each test received run A's own evidence. The
   result was exactly one failure:
   `test_failures_are_bounded_cleaned_and_keep_honest_evidence`, subtest `fault='monitor_exit'`, at
   `assertEqual(value['run_evidence']['verified'], evidence)`, with `False != True`. Every other test
   and subtest passed, including all the mutation checks. That matches the "10 tests, 1 failure" run
   A reported.
2. **Direct check.** All 17 other rehearsals in run A satisfy every cleanup, bound and evaluator
   assertion made of them.
3. **Timelines.** File write times, relative to the rehearsal's first file:

| Rehearsal | Monitor ready | Model host started | Canary | Run evidence | Monitor lost | Questions answered |
|---|---|---|---|---|---|---|
| Run B `monitor_exit` (passed) | 2.14 s | 2.57 s | 3.37 s | present | about 5.1 s | 43 |
| Run C `monitor_exit` (passed) | 1.53 s | 1.83 s | 2.41 s | present | about 4.6 s | 104 |
| Run A `monitor_exit` (failed) | 1.76 s | 2.11 s | **never** | **absent** | before the canary | 0 |

### Reproducing the identification

All three runs' rehearsal evidence is preserved in
`evidence/evidence-comprehension-v1-intermittent-runs.tar.xz`. It holds 26,062 files in a 2.0 MB
archive, SHA-256 `643c8846…c406`. The lock, with every member's hash and the directory-to-run
mapping, is `reports/evidence_comprehension_v1_intermittent_runs_archive.json`. Each run's 18
directories were verified to show the connected suite's exact fault sequence before archiving.

```sh
python scripts/replay_evidence_comprehension_v1_run_a.py --run run_a   # 10 tests, 1 failure: monitor_exit
python scripts/replay_evidence_comprehension_v1_run_a.py --run run_b   # control: 10 tests, 0 failures
python scripts/replay_evidence_comprehension_v1_run_a.py --run run_c   # control: 10 tests, 0 failures
```

Replaying runs B and C gives 0 failures, with every rehearsal consumed. So the replay harness
reproduces each run's outcome rather than introducing failures of its own.

## Mechanism

The `monitor_exit` fault makes the monitor call `os._exit` **3 s after the monitor starts**, whatever
the worker is doing. The test assumed the worker would already be answering questions by then, and
normally it is, by one to two seconds. In run A the model host had not completed its canary when the
monitor died. The rehearsal took 9.5 s of monotonic time, against about 5.4 s in the passing runs.
That fits the VM stall implied by the wall-clock resynchronisation in the same rehearsal, but the
stall is an inference, not a measurement.

## What the failure does and does not affect

Run A's `monitor_exit` rehearsal behaved correctly on every property that matters:

| Property | Run A evidence |
|---|---|
| Deadline enforcement | Ended in 9.5 s; never approached the admission cutoff or the reserve |
| Cancellation | Not involved: no question was ever sent |
| Cleanup | Supervisor process groups verified gone; first-cell cleanup with no errors; scratch removed; GPU cleanup verified |
| Evidence integrity | No run evidence was written. The evaluator reported it as unverified (manifest missing), the gate as `incomplete`, and the lifecycle as failed. Nothing was scored. |

**Classification:** the rehearsal design contains a race, and the test asserted an outcome that
depends on who wins it. The system under test did not misbehave.

## Diagnostics added

`scripts/check_evidence_comprehension_v1.py` now writes a diagnostics record for every run under
`reports/evidence_comprehension_v1_diagnostics/`. For every test and subtest it keeps:
- the name, wall-clock and monotonic start and end, and duration;
- the outcome and full traceback;
- the load average before and after;
- a flag when the wall clock steps relative to the monotonic clock.

For each run it also keeps the host details, the git commit and dirty paths, and the exact command.
Each connected rehearsal adds its test, fault, evidence directory, receipts, supervisor return code,
first-cell cleanup, host status, worker result or failure, and evaluation summary. Evidence
directories are never deleted.

The recorder was confirmed with an intentional failure. `--self-test` runs a suite containing a
passing test, a failing assertion, an error, a failing subtest, and a failure after recording a
rehearsal. It then verifies that each is retained with its outcome, traceback and timing, and that
the rehearsal is linked to its test. The output is in `reports/evidence_comprehension_v1_diagnostics/self-test.json`.

## Follow-up after the review of `adf3b9d`

1. **Recorder defect (fixed).** A `setUpClass` error reaches the result without `startTest`. The
   recorder crashed with a `TypeError`, masking the original exception, and the saved report
   contained only the earlier suite with `all_passed: true`. Reproduced on `adf3b9d`'s recorder.
   - Class, module and suite fixture errors are now kept as their own records.
   - A runner exception is kept with its traceback, and later suites still run.
   - An interrupted run saves an incomplete record before re-raising.
   - Success requires every requested suite to have completed and passed.
   - Five regressions are in `tests/test_evidence_comprehension_v1_diagnostics.py`, and the
     self-test now also includes a `setUpClass` failure after a passing suite (11 checks, all pass).
2. **Deterministic monitor-loss rehearsals (done).**
   - `monitor_exit` now uses a bounded readiness handshake: the monitor exits once the worker's run
     evidence and first retained call exist. If they do not appear within 120 s, it exits anyway and
     leaves `monitor/handshake-timeout.json`, so a slow start stays visible instead of silently
     changing the case.
   - A separate `monitor_exit_before_ready` fault makes the monitor exit before publishing readiness,
     so the supervisor never releases the worker and missing study evidence is guaranteed.
3. **A second race, surfaced by the handshake (fixed).** The first run of the updated test failed.
   From its retained evidence, `monitor_exit` stopped with reason `transport_failure` after 4 calls;
   the second run recorded `canceled` after 6. When the supervisor cancels while a call is in
   flight, the host's bridge refuses or drops that call, and the runner filed it as a transport
   failure.
   - **What it was:** a **labelling defect in the runner**, reproduced on `adf3b9d`'s runner. It did
     not affect deadlines, cleanup or evidence integrity: that run was bounded, fully cleaned, and
     its evidence verified.
   - **The fix:** a call that fails while the cancel file exists is now recorded as `canceled`, and
     the run stops with reason `canceled`. The evaluator accepts that status.
   - **Regressions:** deterministic. An in-flight call during cancellation is labelled `canceled`,
     and a genuine transport failure is still labelled `transport_failure`.

The replay tool now refuses to run unless the connected tests match the version the archived runs
executed (`adf3b9d`), because later revisions add rehearsal cases.

4. **Nested runs cleared the outer logging (fixed; review of `b7e84bc`).** `run_suites` removed
   `ECV_DIAGNOSTICS_LOG` unconditionally on exit, and the recorder's `stopTest` removed
   `ECV_CURRENT_TEST`. The diagnostics suite calls `run_suites` inside the full check, so every
   connected rehearsal after it went unrecorded, silently. Reproduced on `b7e84bc`'s recorder:
   `(None, None)` after the nested runs, and no outer rehearsals recorded. Both variables are now
   saved and restored, including on exceptions. The regression runs nested diagnostics (one normal,
   one interrupted) followed by a rehearsal-recording test, and requires the outer record to keep
   that rehearsal. The first repeat series, which had started on `b7e84bc`, was stopped before any
   run completed.

## Series 2 results (predeclared: 5 sequential full checks on `b74b177`, code identical to `ff02ddc`)

All five runs executed with no reruns. Each run's diagnostics record and rehearsal log are in
`reports/evidence_comprehension_v1_diagnostics/series2-repeat-N.*`, and the driver log is
`series2-driver.log`. Every run recorded all 19 connected rehearsals, each linked to its test.

| Run | Monotonic duration | Result | Rehearsals recorded | Wall-clock jumps flagged (s) |
|---|---|---|---|---|
| 1 | 793 s | all 76 pass | 19 of 19 | 726, 650, 227 |
| 2 | 683 s | all 76 pass | 19 of 19 | 414, 190 (and −2) |
| 3 | 759 s | all 76 pass | 19 of 19 | 103, 215, 14,394, 1,124 |
| 4 | 710 s | **1 error** | 19 of 19 | 301, **41,244** |
| 5 | 677 s | all 76 pass | 19 of 19 | none |

**Result: 4 of 5 passed.** The series spanned about 17.5 hours of wall time but only about 60 minutes of
monotonic time. The flagged jumps indicate the WSL VM was repeatedly paused, most likely by the
Windows host sleeping. That is an inference from the clocks; host sleep was not observed directly.

### Run 4's error

- **Where:** `test_late_abort_trickling_metrics_and_late_replies_stop_within_the_bound`, subtest
  `late_abort`. The test's assertions up to line 320 passed: the study failed as intended, it stopped
  with `transport_failure`, the gate was `incomplete`, there were no call errors, and the last call
  was within its bound. It then raised `FileNotFoundError` reading `worker/cancellations.json`.
- **What the retained evidence shows** (`~/ecv-rehearsal-tests/tmpl1ad9swe`):
  - The run stopped on **call 0**, not at the hung 7th call.
  - The error was `bridge admission closed`, raised on the worker side: the host received **0**
    questionnaire calls.
  - The call's start and return stamps are 10.35 s apart on the monotonic clock, just over the 10 s
    rehearsal bound, with no work in between.
  - The rehearsal took 33 s against about 11 s normally.
  - The same test carries a 41,244 s wall-clock jump.
- **Mechanism (inferred):** a VM pause. On resume, the guest's monotonic clock advanced past the
  call's per-call deadline, so the worker's proxy correctly refused to send an already-expired call.
- **Effect on the system:**
  - **Deadline enforcement:** correct. An expired call was not sent.
  - **Cancellation:** not reached.
  - **Cleanup:** complete. All groups were verified gone, and scratch and GPU cleanup were verified.
  - **Evidence integrity:** the evidence verifies, and the gate was reported `incomplete`.
- **Defect found:** the stop reason is `transport_failure`, but the cause was the call's own deadline
  expiring before dispatch. This is a labelling defect of the same kind as the in-flight cancellation
  case. It was not fixed in the tested commit.
- **Test assumption:** the test assumes the run reaches the hung call. A pause that consumes a call's
  bound before dispatch breaks that assumption.

No threshold or assertion has been relaxed.

### Remediation (reviewer's decision: relabel only; no third series)

- **The relabel.** A call that fails after its own per-call deadline has passed, with no cancellation
  present, is now recorded as `deadline_expired`, and the run stops with that reason. Cancellation
  keeps precedence. A failure within the bound stays `transport_failure`.
- **The evaluator.** It accepts the status only when the label is true: the call must span its whole
  per-call bound.
- **The `late_reply` fault.** Its reply is rejected at the bound, so it is now correctly labelled
  `deadline_expired`, and its connected-test expectation is updated to match.
- **Regressions.** Deterministic, using an injected clock:
  - a clock jump past the bound gives `deadline_expired`;
  - a failure within the bound stays `transport_failure`;
  - cancellation takes precedence;
  - the evaluator rejects an untrue `deadline_expired` label.
- **Reproduced first:** on the series-2 code (`ff02ddc`), the run-4 scenario was labelled
  `transport_failure`.
- **Not changed.** The `late_abort` test still assumes the run reaches the hung call. A VM pause that
  consumes a call's bound before dispatch can still make it fail, now with stop reason
  `deadline_expired`. That remains an **unresolved residual risk** on this host. No controlled series
  with host sleep prevented has been run, so pause-induced failures have not been separated from any
  other cause. Accepting that risk is an explicit decision for the reviewer, and it has not been
  recorded here as accepted. A pause on the live target would be handled the same conservative way.

## Next steps

1. **Predeclared repeats.** Five sequential full-check runs on the resulting commit, with the
   diagnostics recorder, on an otherwise idle machine with nothing else running from this session.
   Every run is reported, with no reruns. Any failure is investigated before launch.
2. **Freeze package r3.** The check script, the review guide, `monitor.py`, `runner.py`,
   `schedule.py` and `supervisor.py` are hash-bound, so approval must be of r3.
