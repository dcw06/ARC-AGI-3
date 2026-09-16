# Phase 4 local scheduler and fault matrix — September 15, 2026

Status: expanded local baseline checks passed. This is not target-GPU batching,
full-load fault certification, or Phase 4 completion. No runtime source, frozen
protocol, notebook, scheduler selection or compute authority changed.

## Coverage

| Requirement | Local evidence | Remaining target gate |
| --- | --- | --- |
| Priority units and fairness | FIFO sequence wins over identity, state payload and generation; 110 waiting requests precede later arrivals | Model-backed full-workload queue telemetry |
| Aging | 299.999/300/300.001-second boundary; expired head skipped; stale generations and canceled clients isolated | Measured tail age under real trajectory load |
| Worker topology and admission waves | 1, 2 and 8 workers each serve 110 distinct results exactly once, overlap reaches but never exceeds configured workers, threads terminate | Actual vLLM batching efficiency, prompt-length mix and selected eight-worker GPU throughput |
| Model faults | Timeout/disconnect surface without queue retry; subsequent request succeeds; actual offline ls20 uses legal fallback and closes its scorecard | Integrated target model crash/timeout and recovery evidence |
| Storage faults | Injected ENOSPC/read-only exceptions propagate; finalization attempted once, unknown receipt cannot pass; fake-service scratch-limit and storage faults exercised | Actual target filesystem/evidence retention failure behavior |
| Workspace faults | E1S-R rejects an operation response, never constructs a tool workspace, and uses legal fallback | No workspace-tool execution is authorized for E1S-R; do not substitute E1C tests as parent evidence |
| Cancellation | Existing queue timeout/staleness tests, cancellation after completion before actual dispatch, and fake-service hang/finalization-hang termination | Integrated GPU full-game cancellation and remote finalization |
| Startup/resource monitoring | Fake-service startup/inference/finalization failures, missing monitor and resource-limit failures; preflight and retained-checkpoint regressions | Clean offline install and target supervisor review remain required |

Concurrency tests use event barriers and exact result/count assertions, not speed
thresholds. FIFO dequeue priority does not imply concurrent completion order.
Admission waves are not GPU batches. Storage exceptions are injected, not a real
disk-full experiment. CPU service tests do not prove an uncooperative CUDA worker
is terminated. Existing prescreen GPU cleanup evidence remains separately scoped.

## Verification

- 9 new tests in `tests/test_phase4_scheduler_fault_matrix.py`.
- 54 tests passed together: scheduler fault matrix, phase4, lifecycle, model
  integration, terminal, preflight, and launch review modules.
- 5 process-level tests in `tests.test_phase4_runner` passed separately with
  approved process-table access (5.693 seconds). The first sandbox run failed
  because resource monitoring was denied; it is not counted as a pass.
- Historical v3 snapshot verification passed, including preserved source locks.
- No GPU inference, upload, reservation, budget release or advanced policy.

Reproduce the main local suite:

```sh
MPLCONFIGDIR="$PWD/.cache/matplotlib" XDG_CACHE_HOME="$PWD/.cache" .venv/bin/python -m unittest tests.test_phase4_scheduler_fault_matrix tests.test_phase4 tests.test_phase4_lifecycle tests.test_phase4_model_integration tests.test_phase4_terminal tests.test_phase4_preflight tests.test_phase4_launch_review -q
```

Run `tests.test_phase4_runner` separately in an environment permitting process
inspection. Do not mock away resource monitoring to claim process-level coverage.
