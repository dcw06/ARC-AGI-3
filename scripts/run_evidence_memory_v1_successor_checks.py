"""Retain Linux CPU checks for the Track 2 successor packages and reproduce both review snapshots.

No network, provider, model or GPU: tests use temporary fixtures, scripted servers and fixture wheels only. Run from a
fresh clone on Linux; the successor group needs an interpreter with pip (fixture venv installs) and the pinned
tokenizer files (EVIDENCE_MEMORY_TOKENIZER) for the tokenizer-dependent tests.

    python scripts/run_evidence_memory_v1_successor_checks.py --group successor --out <record.json>
    python scripts/run_evidence_memory_v1_successor_checks.py --group track2 --out <record.json>
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
GROUPS = {
    'successor': ['tests.test_evidence_memory_v1_successor', 'tests.test_evidence_memory_v1_successor_service',
                  'tests.test_evidence_memory_v1_successor_freeze', 'tests.test_evidence_memory_v1_successor_session_order',
                  'tests.test_evidence_memory_v1_successor_connected',
                  'tests.test_direct_publisher_smoke', 'tests.test_direct_publisher_smoke_lifecycle',
                  'tests.test_direct_publisher_smoke_preflight', 'tests.test_direct_publisher_smoke_install_lifecycle',
                  'tests.test_direct_publisher_smoke_bootstrap', 'tests.test_direct_publisher_smoke_runtime_versions',
                  'tests.test_direct_publisher_smoke_model_dataset', 'tests.test_direct_publisher_smoke_competition',
                  'tests.test_direct_publisher_smoke_model_mount'],
    'track2': ['tests.test_evidence_memory_v1', 'tests.test_evidence_memory_v1_harness',
               'tests.test_evidence_memory_v1_migration', 'tests.test_evidence_memory_v1_protocol',
               'tests.test_evidence_memory_v1_stage1', 'tests.test_evidence_memory_v1_run',
               'tests.test_evidence_memory_v1_final', 'tests.test_evidence_memory_v1_run_evidence',
               'tests.test_evidence_memory_v1_run_final_e2e', 'tests.test_evidence_memory_v1_run_connected',
               'tests.test_transition_evidence_v2', 'tests.test_transition_evidence_v1'],
}


class Recorder(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def startTest(self, test):
        self.started = time.monotonic()
        super().startTest(test)

    def record(self, test, outcome, detail=None):
        self.records.append({'test': test.id(), 'outcome': outcome, 'seconds': round(time.monotonic() - self.started, 3),
                             'detail': detail})

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


def reproduce(label):
    """The latest review snapshot (r2 since the protocol freeze; earlier ones are kept as history) rebuilt from this
    checkout, file by file."""
    import importlib
    from research.evidence_memory_v1.successor import plan as PL
    module = importlib.import_module(PL.SESSIONS[label]['module'] + '.notebook')
    binding = importlib.import_module(PL.SESSIONS[label]['module'] + '.binding')
    frozen = (ROOT / binding.review_lock(ROOT)).parent
    with tempfile.TemporaryDirectory() as folder:
        regenerated = Path(folder) / 'review'
        module.build_review(regenerated, root=ROOT)
        same = {n: (frozen / n).read_bytes() == (regenerated / n).read_bytes()
                for n in ('profile.ipynb', 'kernel-metadata.json', 'review-source-lock.json')}
    return {'review_revision': frozen.name.rsplit('-r', 1)[1],
            'review_lock_sha256': hashlib.sha256((frozen / 'review-source-lock.json').read_bytes()).hexdigest(), **same}


def head():
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--group', choices=sorted(GROUPS), required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise SystemExit('Linux required (process groups, POSIX run evidence, fixture installs)')
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    tests = unittest.defaultTestLoader.loadTestsFromNames(GROUPS[args.group])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with args.out.with_suffix('.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(tests)
    snapshots = {label: reproduce(label) for label in ('A', 'B')}
    record = {'schema': 'evidence_memory_v1_successor_cpu_checks_v1', 'group': args.group, 'suites': GROUPS[args.group],
              'revision': head(), 'python': platform.python_version(), 'executable': sys.executable,
              'evidence_class': 'scripted_cpu_control_checks_not_model_performance', 'gpu_used': False,
              'model_calls': 0, 'provider_calls': 0, 'launch_authorized': False,
              'tokenizer_files': 'EVIDENCE_MEMORY_TOKENIZER' if os.environ.get('EVIDENCE_MEMORY_TOKENIZER') else None,
              'seconds': round(time.monotonic() - started, 1),
              'summary': {'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                          'skipped': len(result.skipped)},
              'tests': result.records, 'snapshots_reproduce': snapshots,
              'passed': result.wasSuccessful() and all(all(v for k, v in s.items()
                                                           if k not in ('review_lock_sha256', 'review_revision'))
                                                       for s in snapshots.values())}
    args.out.write_bytes((json.dumps(record, sort_keys=True, indent=1) + '\n').encode())
    print(json.dumps({k: record[k] for k in ('passed', 'summary', 'snapshots_reproduce', 'seconds')}, indent=1))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
