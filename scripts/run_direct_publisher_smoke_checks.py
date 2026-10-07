"""Retain focused CPU test results and reproduce the frozen runner review snapshot.

Run from a clean Linux checkout with core.autocrlf=false. No network/provider/GPU
work; tests use only temporary fixture evidence and scripted process controls.
"""
import argparse
import json
import platform
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from certification.direct_publisher_smoke_v1 import notebook as N
from certification.direct_publisher_smoke_v1.binding import sha256

SUITES = ['tests.test_direct_publisher_smoke', 'tests.test_direct_publisher_smoke_lifecycle',
          'tests.test_direct_publisher_smoke_preflight', 'tests.test_direct_publisher_smoke_install_lifecycle']


class Recorder(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def startTest(self, test):
        self.started = time.monotonic()
        super().startTest(test)

    def record(self, test, outcome, detail=None):
        self.records.append(dict(test=test.id(), outcome=outcome,
                                 seconds=round(time.monotonic() - self.started, 3), detail=detail))

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, 'pass')

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.record(test, 'fail', self._exc_info_to_string(error, test))

    def addError(self, test, error):
        super().addError(test, error)
        self.record(test, 'error', self._exc_info_to_string(error, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, 'skip', reason)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--review-revision', type=int, default=2)
    args = parser.parse_args()
    revision, clean = git('rev-parse', 'HEAD'), not git('status', '--porcelain')
    suite = unittest.defaultTestLoader.loadTestsFromNames(SUITES)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.with_suffix('.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(suite)
    frozen = ROOT / f'notebooks/direct-publisher-smoke-v1-review-r{args.review_revision}'
    with tempfile.TemporaryDirectory(prefix='direct-publisher-review-reproduce-') as folder:
        reproduced = Path(folder) / 'snapshot'
        N.build_review(reproduced, root=ROOT)
        matches = {name: (frozen / name).read_bytes() == (reproduced / name).read_bytes()
                   for name in ('profile.ipynb', 'kernel-metadata.json', 'review-source-lock.json')}
    report = {'schema': 'direct_publisher_smoke_cpu_checks_v1', 'source_revision': revision,
              'working_tree_clean_before_checks': clean, 'python': platform.python_version(),
              'evidence_class': 'cpu_control_checks_not_remote_wheel_or_gpu_evidence',
              'summary': {'run': result.testsRun, 'failures': len(result.failures),
                          'errors': len(result.errors), 'skipped': len(result.skipped)},
              'tests': result.records, 'review_snapshot_reproduces': matches,
              'review_lock_sha256': sha256(frozen / 'review-source-lock.json'),
              'review_revision': args.review_revision,
              'passed': result.wasSuccessful() and all(matches.values()),
              'gpu_compatibility_evidence': False, 'launch_authorized': False}
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('source_revision', 'working_tree_clean_before_checks',
                                           'summary', 'review_snapshot_reproduces', 'passed')}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
