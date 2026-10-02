"""Run the final Track 3 CPU suite and bind its receipt to the tested source and tests."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'reports/stagnation_supervision_v1_local_checks_r4.json'


def source_bindings():
    from scripts.build_stagnation_supervision_v1_review_r4 import inventory
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in inventory()}


def test_bindings():
    names = list((ROOT / 'tests').glob('test_stagnation_supervision_v1*.py'))
    names += [Path(__file__), ROOT / 'scripts/build_stagnation_supervision_v1_review_r4.py',
              ROOT / 'scripts/review_stagnation_supervision_v1_notebook_r4.py']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(names)}


def check():
    value = json.loads(OUT.read_bytes())
    if (value.get('status') != 'passed_cpu_scope' or value.get('failures') != 0 or value.get('errors') != 0
            or value.get('tested_source_bindings') != source_bindings()
            or value.get('test_and_review_script_bindings') != test_bindings()):
        raise ValueError('CPU test receipt or tested source drift')
    return value


def run():
    if OUT.exists():
        raise FileExistsError('final test receipt is write-once; use --check or a new revision')
    sources, tests = source_bindings(), test_bindings()
    started = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), 'test_stagnation_supervision_v1*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if sources != source_bindings() or tests != test_bindings():
        raise ValueError('tested source changed while the suite ran')
    if not result.wasSuccessful():
        raise RuntimeError(f'CPU suite failed: {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors')
    value = {'version': 'stagnation_supervision_v1_local_checks_r4', 'status': 'passed_cpu_scope',
             'command': "python -m scripts.check_stagnation_supervision_v1_review_r4",
             'tests_run': result.testsRun, 'failures': 0, 'errors': 0, 'skipped': len(result.skipped),
             'elapsed_seconds': round(time.monotonic() - started, 3), 'python_version': sys.version.split()[0],
             'packages': {n: importlib.metadata.version(n) for n in ('arcengine', 'arc-agi', 'numpy')},
             'tested_source_bindings': sources, 'test_and_review_script_bindings': tests,
             'scope': 'offline engine, scripted model transport, real process/RSS/scratch probes, injected GPU telemetry',
             'gpu_runs': 0, 'real_model_calls': 0, 'compute_authorized_seconds': 0,
             'earlier_rehearsal_note': 'Earlier 142- and 150-test runs each exposed a narrow slow-deadline assertion. Retained evidence demonstrated both valid cutoff outcomes: deadline_exceeded/run deadline enforced and technical_failure/model transport. The final test accepts only those pairs with an external-cutoff receipt, actual calls and verified cleanup.'}
    with OUT.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='read-only receipt/source verification')
    args = parser.parse_args()
    value = check() if args.check else run()
    print(json.dumps({k: value[k] for k in ('status', 'tests_run', 'failures', 'errors', 'elapsed_seconds')}))
