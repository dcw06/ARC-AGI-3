"""Run every local suite for the comparison and record the rehearsal results (no model calls, no GPU)."""
import json
from pathlib import Path
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUITES = {'records_and_fixtures': 'tests.test_action_effect_v1',
          'request_contract': 'tests.test_action_effect_history_v1_contract',
          'runner_rehearsals': 'tests.test_action_effect_history_v1_runner',
          'connected_path_rehearsals': 'tests.test_action_effect_history_v1_connected',
          'negative_regressions_from_r1_review': 'tests.test_action_effect_history_v1_negative',
          'r8_evaluator_repair': 'tests.test_grounded_action_v1_r8_evaluation'}


def main():
    results = {}
    for label, name in SUITES.items():
        begun = time.monotonic()
        outcome = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName(name))
        results[label] = {'module': name, 'tests_run': outcome.testsRun, 'failures': len(outcome.failures),
                          'errors': len(outcome.errors), 'passed': outcome.wasSuccessful(),
                          'seconds': round(time.monotonic() - begun, 1)}
    report = {'scope': 'local CPU rehearsals only; scripted model; no model calls or GPU runs',
              'suites': results, 'all_passed': all(r['passed'] for r in results.values()),
              'covers': ['full schedule and replay from past observations only', 'null-denominator metrics and outcome classes',
                         'invalid output, rejected/unknown/frameless dispatch', 'transport failure and token mismatch',
                         'deadline overrun mid-pair and non-admission', 'connected launcher->supervisor->worker->host->bridge->runner',
                         'model startup failure, monitor exit, cancellation, storage exhaustion, SIGTERM-ignoring child',
                         'instrumentation leaves requests and actions unchanged', 'R8 archive replay unchanged'],
              'environment_check': 'reports/action_effect_history_v1_environment_check.json',
              'token_audit': 'reports/action_effect_history_v1_token_audit.json', 'model_calls': 0, 'gpu_runs': 0}
    (ROOT / 'reports/action_effect_history_v1_rehearsal_results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=1))
    if not report['all_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
