# Evidence comprehension v1: predeclared repeat runs

Declared before any run of this series starts, in the commit that adds this revision of the file.
That commit is the code under test.

## Series history

- **Series 1, on `b7e84bc`: aborted.** It was stopped at 2026-09-26T23:57:57Z, during repeat-1,
  before any run had completed. Review of `b7e84bc` found that a nested `run_suites` (the
  diagnostics suite runs inside the full check) cleared `ECV_DIAGNOSTICS_LOG` and `ECV_CURRENT_TEST`.
  The connected suite, which runs later, would therefore have recorded no rehearsals. The series'
  driver log is retained as `reports/evidence_comprehension_v1_diagnostics/aborted-series-b7e84bc.log`.
- **Series 2: this plan.** It runs on the commit that fixes the restoration and adds its regression.

## Plan

- **Number of runs: 5.** Every run is executed and reported, whatever the earlier outcomes. There
  are no reruns, and no run is stopped or discarded early for being red or green.
- **What each run is:** the full local check, meaning all five suites including the connected-path
  rehearsals, via

  ```sh
  .venv/bin/python -m scripts.check_evidence_comprehension_v1 --run-id series2-repeat-N --label "series 2, predeclared repeat N of 5"
  ```

  in WSL, for N = 1…5.
- **Order and conditions:** strictly sequential, one run at a time, started by a single driver
  script that records each run's start and end on both clocks. Nothing else is run from this session
  while the runs are in progress. Host details, load before and after every test, and wall-clock step
  flags are recorded by the check itself.
- **Retention:** each run's diagnostics record (`reports/evidence_comprehension_v1_diagnostics/series2-repeat-N.json`
  and `.rehearsals.jsonl`) is committed, and every rehearsal evidence directory is kept.
- **Completeness check on every run:** the record must list all 19 connected-suite rehearsals (the
  18 earlier ones plus `monitor_exit_before_ready`), each linked to the test that ran it. The
  diagnostics suite's nested runs write to their own temporary logs, so they add nothing here. A run
  that finished but recorded fewer is a diagnostics failure and is investigated like any other
  failure.

## Decision rules, fixed in advance

- **All five pass:** the result is reported as "5 of 5 passed". That does not prove the absence of
  intermittent failures; it bounds how often they occur on this host. Package r3 is then frozen and
  submitted for independent review.
- **Any failure:** it is investigated from its retained diagnostics and evidence **before** any GPU
  launch. The investigation must decide whether the failure affects deadline enforcement,
  cancellation, cleanup or evidence integrity, or is confined to a test assertion. No threshold or
  assertion is relaxed without that evidence. The remaining runs still complete and are reported.
- **The original run-A failure:** it is reported as "cause identified; the rehearsal race it depended
  on has been removed", never as "fixed" on the strength of these runs alone. The earlier finding
  stands on its own evidence.
