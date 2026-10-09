"""Run the Track 1 CPU suites and retain per-test results (no model, no GPU, no provider, no approval).

    python scripts/run_feedback_action_v1_checks.py --label dev-env [--suites ...]

Writes reports/feedback_action_v1/cpu_checks_<label>.json and .log. The interpreter and the rehearsal environment
(FA1_REHEARSAL_* variables) are recorded, so a run on the installed successor interpreters is distinguishable from a
run in the development environment.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SUITES = ['tests.test_feedback_action_v1', 'tests.test_feedback_action_v1_denominators',
          'tests.test_feedback_action_v1_dispatch', 'tests.test_feedback_action_v1_live',
          'tests.test_feedback_action_v1_migration', 'tests.test_feedback_action_v1_token_audit',
          'tests.test_feedback_action_v1_successor', 'tests.test_feedback_action_v1_live_evaluation',
          'tests.test_feedback_action_v1_connected', 'tests.test_feedback_action_v1_http_path',
          'tests.test_transition_evidence_v2']


class Recorder(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records, self._began = [], {}

    def startTest(self, test):
        self._began[test.id()] = time.monotonic()
        super().startTest(test)

    def _record(self, test, outcome, detail=None):
        self.records.append({'test': test.id(), 'outcome': outcome,
                             'seconds': round(time.monotonic() - self._began.get(test.id(), time.monotonic()), 2),
                             **({'detail': detail[-600:]} if detail else {})})

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, 'passed')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, 'failed', self.failures[-1][1])

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test, 'error', self.errors[-1][1])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test, 'skipped', reason)

    def addSubTest(self, test, subtest, outcome):
        super().addSubTest(test, subtest, outcome)
        if outcome is not None:
            self._record(subtest, 'failed' if issubclass(outcome[0], test.failureException) else 'error',
                         self._exc_info_to_string(outcome, test))


def versions(names):
    found = {}
    for name in names:
        try:
            found[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            found[name] = None
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--label', required=True)
    parser.add_argument('--suites', nargs='*', default=SUITES)
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise SystemExit('Linux required for process-group, fcntl and subreaper controls')
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    environment = {k: v for k, v in sorted(os.environ.items()) if k.startswith('FA1_')}  # before tests set any
    folder = ROOT / 'reports/feedback_action_v1'
    folder.mkdir(parents=True, exist_ok=True)
    tests = unittest.defaultTestLoader.loadTestsFromNames(args.suites)
    begun = time.monotonic()
    with (folder / f'cpu_checks_{args.label}.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(tests)
    record = {'schema': 'feedback_action_v1_cpu_checks_v1', 'label': args.label, 'suites': args.suites,
              'python': platform.python_version(), 'executable': sys.executable,
              'packages': versions(('arc-agi', 'arcengine', 'numpy', 'transformers', 'tokenizers', 'xgrammar',
                                    'vllm', 'torch')),
              'rehearsal_environment': environment,
              'evidence_class': 'scripted_cpu_checks_not_model_performance', 'gpu_used': False, 'model_calls': 0,
              'provider_calls': 0, 'launch_authorized': False,
              'summary': {'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                          'skipped': len(result.skipped), 'seconds': round(time.monotonic() - begun, 1)},
              'tests': result.records, 'passed': result.wasSuccessful()}
    (folder / f'cpu_checks_{args.label}.json').write_text(json.dumps(record, indent=1, sort_keys=True) + '\n',
                                                         encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('label', 'passed', 'summary')}, indent=1))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
