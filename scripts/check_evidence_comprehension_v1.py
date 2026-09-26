"""Run every local suite for the questionnaire and record the rehearsal results (no model calls, no GPU)."""
import json
from pathlib import Path
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUITES = {'probe_set_keys_scoring_and_analysis': 'tests.test_evidence_comprehension_v1',
          'schedule_admission_and_interrupted_gate': 'tests.test_evidence_comprehension_v1_schedule',
          'transport_cancellation_and_cache_metrics': 'tests.test_evidence_comprehension_v1_transport',
          'connected_path_rehearsals': 'tests.test_evidence_comprehension_v1_connected'}


def main():
    results = {}
    for label, name in SUITES.items():
        begun = time.monotonic()
        outcome = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName(name))
        results[label] = {'module': name, 'tests_run': outcome.testsRun, 'failures': len(outcome.failures),
                          'errors': len(outcome.errors), 'passed': outcome.wasSuccessful(),
                          'seconds': round(time.monotonic() - begun, 1)}
    report = {'scope': 'local CPU rehearsals only; CPU fake of the model server with scripted answers; '
                       'no model calls or GPU runs',
              'suites': results, 'all_passed': all(r['passed'] for r in results.values()),
              'covers': ['frozen probe set, dual keys, full-schema validation, pass-identified analysis',
                         'missing passes or answers are incomplete, never success',
                         'admission timing validation; per-call bound; interrupted gate in both passes (simulated)',
                         'total-deadline transport; server-side abort on disconnect verified from server metrics',
                         'server that ignores cancellation stops the run',
                         'prefix caching verified disabled from server metrics; enabled caching refused before questions',
                         'connected launcher->supervisor->worker->host->HTTP server->runner->evaluator',
                         'deadline interruption during gate pass 1 and gate pass 2 with the cleanup reserve untouched',
                         'model startup failure, HTTP failure, monitor exit, cancellation, storage exhaustion, '
                         'log flood, SIGTERM-ignoring child: bounded, cleaned up, honest partial evidence',
                         'evaluator scores only retained responses; forged hashes, order and token parity rejected',
                         'instrumentation leaves requests and answers unchanged'],
              'token_audit': 'reports/evidence_comprehension_v1_token_audit.json', 'model_calls': 0, 'gpu_runs': 0}
    (ROOT / 'reports/evidence_comprehension_v1_rehearsal_results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=1))
    if not report['all_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
