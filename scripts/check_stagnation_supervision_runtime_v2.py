"""Run the full Track 3 CPU suite (historical R4 suite, R5-R7 suites and the runtime v2 suite) plus the read-only
historical receipt checks, and bind a write-once receipt to the tested sources and tests. Linux CPU only.

    python -m scripts.check_stagnation_supervision_runtime_v2            # run and write the receipt (write-once)
    python -m scripts.check_stagnation_supervision_runtime_v2 --check    # verify the receipt still binds the tree
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'reports/stagnation_supervision_runtime_v2_local_checks_r1.json'
PATTERNS = ('test_stagnation_supervision_v1*.py', 'test_ssv_*.py')
HISTORICAL_CHECKS = (
    [sys.executable, '-m', 'scripts.derive_stagnation_supervision_v1', '--check'],
    [sys.executable, '-m', 'scripts.check_stagnation_supervision_v1_review_r4', '--check'],
    [sys.executable, '-m', 'scripts.verify_stagnation_supervision_v1_audit_inputs_r3', '--check'],
    [sys.executable, '-m', 'scripts.verify_stagnation_supervision_runtime_v2_detector', '--check'],
    [sys.executable, '-m', 'scripts.report_stagnation_supervision_runtime_v2_diff', '--check'],
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_bindings():
    from research.stagnation_supervision_runtime_v2.closure import closure
    names = set(closure(ROOT)['files'])
    names |= {p.relative_to(ROOT).as_posix() for p in (ROOT / 'research/stagnation_supervision_runtime_v2').glob('*')
              if p.is_file()}
    return {n: sha(ROOT / n) for n in sorted(names)}


def test_bindings():
    names = sorted({p for pattern in PATTERNS for p in (ROOT / 'tests').glob(pattern)})
    names += [ROOT / 'tests/ssv_runtime_v2_fixtures.py', Path(__file__)]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in names}


def check():
    value = json.loads(OUT.read_bytes())
    if (value.get('status') != 'passed_cpu_scope' or value['failures'] or value['errors']
            or value.get('tested_source_bindings') != source_bindings() or value.get('test_bindings') != test_bindings()):
        raise ValueError('CPU receipt or tested source drift')
    return value


def run():
    if OUT.exists():
        raise FileExistsError('write-once receipt exists: ' + str(OUT))
    sources, tests = source_bindings(), test_bindings()
    started = time.monotonic()
    historical = []
    for argv in HISTORICAL_CHECKS:
        value = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=1800)
        historical.append({'command': ' '.join(argv[1:]), 'returncode': value.returncode,
                           'tail': (value.stdout.strip().splitlines() or [''])[-1][:300]})
    suites = {}
    totals = {'tests_run': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
    for pattern in PATTERNS:
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern, top_level_dir=str(ROOT))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        suites[pattern] = {'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                           'skipped': len(result.skipped),
                           'failed': [str(t) for t, _ in result.failures + result.errors][:20]}
        for key in totals:
            totals[key] += suites[pattern][key]
    if sources != source_bindings() or tests != test_bindings():
        raise ValueError('tested source changed while the suite ran')
    passed = not totals['failures'] and not totals['errors'] and all(h['returncode'] == 0 for h in historical)
    value = {'version': 'stagnation_supervision_runtime_v2_local_checks_r1',
             'status': 'passed_cpu_scope' if passed else 'failed', **totals, 'suites': suites,
             'historical_and_receipt_checks': historical, 'elapsed_seconds': round(time.monotonic() - started, 3),
             'python_version': sys.version.split()[0],
             'packages': {n: importlib.metadata.version(n) for n in ('arcengine', 'arc-agi', 'numpy')},
             'tested_source_bindings': sources, 'test_bindings': tests,
             'scope': ('offline engine, scripted model transport, real process/RSS/scratch probes, injected GPU '
                       'telemetry, synthetic authority trees in temporary directories'),
             'gpu_runs': 0, 'real_model_calls': 0, 'provider_calls': 0, 'compute_authorized_seconds': 0,
             'not_covered_here': ['scripts.derive_stagnation_supervision_runtime_v2 --check (needs git objects; run on '
                                  'the Windows checkout)', 'staged real-interpreter rehearsals (separate receipts)']}
    with OUT.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=1, sort_keys=True)
        stream.write('\n')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    value = check() if args.check else run()
    print(json.dumps({k: value[k] for k in ('status', 'tests_run', 'failures', 'errors', 'skipped', 'elapsed_seconds')}))
    sys.exit(0 if value['status'] == 'passed_cpu_scope' else 1)
