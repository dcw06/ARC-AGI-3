"""Run and retain the runtime2 CPU checks (no GPU, model, provider, approval or reservation).

Groups (one record each, written to --out):
  successor   the runtime2 suites (package/gate/derivation, questionnaire stage, evaluator, science; the full HTTP
              rehearsals with PSV1R2_REHEARSALS=1);
  controller  the verified controller's own regression suites, copied unchanged from 5a21dd3 (they need a host
              Python with pip, so run this group with such an interpreter);
  snapshot    review r<N>: source bindings, artifacts and review documents verified, and a fresh rebuild of the
              notebook, metadata and lock reproduces them byte for byte.

Every record says what it is: scripted CPU control checks, never GPU, model or provider evidence.

Usage: python scripts/run_progress_subgoal_v1_runtime2_checks.py --group successor|controller|snapshot --out FILE
"""
import argparse
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
GROUPS = {
    'successor': ['tests.test_progress_subgoal_v1_runtime2', 'tests.test_progress_subgoal_v1_runtime2_questionnaire',
                  'tests.test_progress_subgoal_v1_runtime2_evaluator', 'tests.test_progress_subgoal_v1_runtime2_science',
                  'tests.test_progress_subgoal_v1_runtime2_rehearsal'],
    'controller': ['tests.test_direct_publisher_smoke', 'tests.test_direct_publisher_smoke_bootstrap',
                   'tests.test_direct_publisher_smoke_competition', 'tests.test_direct_publisher_smoke_install_lifecycle',
                   'tests.test_direct_publisher_smoke_lifecycle', 'tests.test_direct_publisher_smoke_model_dataset',
                   'tests.test_direct_publisher_smoke_model_mount', 'tests.test_direct_publisher_smoke_preflight',
                   'tests.test_direct_publisher_smoke_runtime_versions'],
}


class Recorder(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records, self.started = [], {}

    def startTest(self, test):
        self.started[test.id()] = time.monotonic()
        super().startTest(test)

    def _add(self, test, outcome, detail=None):
        began = self.started.get(test.id())
        self.records.append({'test': test.id(), 'outcome': outcome, 'detail': detail,
                             'seconds': round(time.monotonic() - began, 3) if began else None})

    def addSuccess(self, test):
        super().addSuccess(test)
        self._add(test, 'success')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._add(test, 'failure', self._exc_info_to_string(err, test)[-3000:])

    def addError(self, test, err):
        super().addError(test, err)
        self._add(test, 'error', self._exc_info_to_string(err, test)[-3000:])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._add(test, 'skipped', reason)


def run_suites(names):
    tests = unittest.defaultTestLoader.loadTestsFromNames(names)
    with tempfile.TemporaryFile('w+') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(tests)
    return {'suites': names, 'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
            'skipped': len(result.skipped), 'passed': result.wasSuccessful(), 'tests': result.records}


def snapshot(revision):
    from research.progress_subgoal_v1_runtime2.binding import check_sources, sha256
    from research.progress_subgoal_v1_runtime2.notebook import build_review
    folder = ROOT / f'notebooks/progress-subgoal-v1-runtime2-review-r{revision}'
    name = (folder / 'review-source-lock.json').relative_to(ROOT).as_posix()
    lock = check_sources(ROOT, name)
    artifacts = all(sha256(folder / n) == d for n, d in lock['artifacts'].items())
    documents = all(sha256(ROOT / n) == d for n, d in lock['review_documents'].items())
    with tempfile.TemporaryDirectory() as tmp:
        rebuilt = Path(tmp) / folder.name
        build_review(rebuilt, root=ROOT)
        reproduces = {n: (rebuilt / n).read_bytes() == (folder / n).read_bytes()
                      for n in ('profile.ipynb', 'kernel-metadata.json', 'review-source-lock.json')}
    metadata = json.loads((folder / 'kernel-metadata.json').read_bytes())
    r4 = ROOT / 'notebooks/progress-subgoal-v1-review-r4/review-source-lock.json'
    return {'review_revision': revision, 'review_lock_sha256': sha256(folder / 'review-source-lock.json'),
            'source_bindings_verified': len(lock['bindings']), 'artifacts_verified': artifacts,
            'review_documents_verified': documents, 'rebuild_reproduces': reproduces,
            'notebook_bytes': (folder / 'profile.ipynb').stat().st_size,
            'gpu_enabled': metadata['enable_gpu'], 'internet_enabled': metadata['enable_internet'],
            'private': metadata['is_private'], 'unresolved_placeholders': lock['unresolved_placeholders'],
            'superseded_r4_lock_sha256': sha256(r4),
            'passed': (artifacts and documents and all(reproduces.values()) and metadata['enable_gpu'] is False
                       and metadata['enable_internet'] is False and lock['gpu_enabled'] is False
                       and lock['gpu_launch_authorized'] is False and lock['authorized_seconds'] == 0
                       and (folder / 'profile.ipynb').stat().st_size < 900000)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('successor', 'controller', 'snapshot'), required=True)
    parser.add_argument('--revision', type=int, default=6)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise SystemExit('Linux required for process-group and CPU fixture controls')
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    began = time.time()
    body = snapshot(args.revision) if args.group == 'snapshot' else run_suites(GROUPS[args.group])
    record = {'schema': 'progress_subgoal_v1_runtime2_cpu_checks_v1', 'group': args.group,
              'evidence_class': 'scripted_cpu_control_checks_not_gpu_or_model_evidence', 'gpu_used': False,
              'model_calls': 0, 'provider_calls': 0, 'launch_authorized': False,
              'python': platform.python_version(), 'executable': sys.executable, 'platform': platform.platform(),
              'environment': {k: os.environ.get(k) for k in ('PSV1R2_REHEARSALS', 'PSV1R2_REHEARSAL_HOST_PYTHON',
                                                             'PSV1R2_BASIS', 'CUDA_VISIBLE_DEVICES')},
              'started_unix': round(began, 1), 'seconds': round(time.time() - began, 1), **body}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes((json.dumps(record, sort_keys=True, indent=1) + '\n').encode())
    print(json.dumps({k: record.get(k) for k in ('group', 'passed', 'run', 'failures', 'errors', 'skipped', 'seconds')}))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
