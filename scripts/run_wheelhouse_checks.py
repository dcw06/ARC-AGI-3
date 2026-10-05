"""Run the wheelhouse tooling checks and retain the evidence: source revision, command, environment, every test name
with its outcome and duration, failure text, and the offline report reproduction.

  python scripts/run_wheelhouse_checks.py --out reports/wheelhouse_tooling_checks_<revision>.json

Run it from a clean checkout of the revision under review. No network, wheel download, installation or GPU use.
"""
import argparse
import datetime
import json
import platform
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # so `python scripts/run_wheelhouse_checks.py` can import tests.*
SUITES = ['tests.test_wheelhouse_metadata', 'tests.test_wheelhouse_offline_install', 'tests.test_wheelhouse_licenses',
          'tests.test_wheelhouse_review3', 'tests.test_wheelhouse_review4', 'tests.test_wheelhouse_review5',
          'tests.test_wheelhouse_review6', 'tests.test_wheelhouse_review7']


class Recorder(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records, self._start = [], {}

    def startTest(self, test):
        self._start[test.id()] = time.monotonic()
        super().startTest(test)

    def _record(self, test, outcome, detail=None):
        self.records.append({'test': test.id(), 'outcome': outcome,
                             'seconds': round(time.monotonic() - self._start.get(test.id(), time.monotonic()), 3),
                             **({'detail': detail} if detail else {})})

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, 'pass')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, 'fail', self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test, 'error', self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test, 'skip', reason)


def iterate(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iterate(item)
        else:
            yield item


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out')
    parser.add_argument('--list', action='store_true', help='load the suites and print the test count only')
    args = parser.parse_args(argv)
    if args.list:
        suite = unittest.defaultTestLoader.loadTestsFromNames(SUITES)
        broken = [t.id() for t in iterate(suite) if t.id().startswith('unittest.loader._FailedTest')]
        print(json.dumps({'tests': suite.countTestCases(), 'import_failures': broken}))
        return 1 if broken else 0
    if not args.out:
        parser.error('--out is required unless --list is given')
    started = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    t0 = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromNames(SUITES)
    with open(Path(args.out).with_suffix('.log'), 'w', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Recorder).run(suite)
    check = subprocess.run([sys.executable, 'scripts/check_wheelhouse_metadata.py', 'analyze', '--check'], cwd=ROOT,
                           capture_output=True, text=True)
    evidence = {
        'source_revision': git('rev-parse', 'HEAD'), 'working_tree_clean': git('status', '--porcelain') == '',
        'command': ' '.join([Path(sys.executable).name, 'scripts/run_wheelhouse_checks.py', '--out', args.out]),
        'started': started, 'seconds': round(time.monotonic() - t0, 1),
        'environment': {'python': platform.python_version(), 'platform': platform.platform()},
        'suites': SUITES,
        'summary': {'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                    'skipped': len(result.skipped), 'passed': result.wasSuccessful()},
        'offline_report_reproduction': {'exit': check.returncode, 'output': check.stdout.strip()},
        'tests': sorted(result.records, key=lambda r: r['test']),
    }
    Path(args.out).write_text(json.dumps(evidence, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'source_revision': evidence['source_revision'], **evidence['summary'],
                      'reports_reproduce': check.returncode == 0}))
    return 0 if result.wasSuccessful() and check.returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
