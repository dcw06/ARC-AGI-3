"""Retain Linux CPU regressions and reproduce the current review. Preserve historical records."""
import argparse
import json
import os
import platform
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_direct_publisher_smoke_checks import Recorder, SUITES
from certification.direct_publisher_smoke_v1 import notebook as smoke
from research.control_interface_action_selection_v1 import notebook as research
from research.control_interface_action_selection_v1.binding import sha256


def reproduce(module, name):
    frozen = ROOT / 'notebooks' / name
    with tempfile.TemporaryDirectory() as folder:
        regenerated = Path(folder) / 'review'
        module.build_review(regenerated, root=ROOT)
        return {n: (frozen / n).read_bytes() == (regenerated / n).read_bytes()
                for n in ('profile.ipynb', 'kernel-metadata.json', 'review-source-lock.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-revision', type=int, default=2)
    parser.add_argument('--out', type=Path, default=ROOT / 'reports/control_interface_action_selection_v1/packaging_fix_r2_cpu_checks.json')
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise SystemExit('Linux required for process groups and complete CPU fixture installation checks')
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    suite = unittest.defaultTestLoader.loadTestsFromNames(SUITES + ['tests.test_control_interface_action_selection_v1'])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.with_suffix('.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(suite)
    snapshots = {'smoke_r10': reproduce(smoke, 'direct-publisher-smoke-v1-review-r10'),
                 f'research_r{args.review_revision}': reproduce(research, f'control-interface-action-selection-v1-review-r{args.review_revision}')}
    lock = ROOT / f'notebooks/control-interface-action-selection-v1-review-r{args.review_revision}/review-source-lock.json'
    record = {'schema': 'control_interface_action_selection_cpu_checks_v1', 'python': platform.python_version(),
        'evidence_class': 'scripted_cpu_control_checks_not_model_performance', 'gpu_used': False,
        'model_calls': 0, 'launch_authorized': False, 'review_revision': args.review_revision, 'review_lock_sha256': sha256(lock),
        'summary': {'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped)},
        'tests': result.records, 'snapshots_reproduce': snapshots,
        'passed': result.wasSuccessful() and all(all(r.values()) for r in snapshots.values())}
    args.out.write_text(json.dumps(record, sort_keys=True, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('passed', 'summary', 'snapshots_reproduce')}, indent=1))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
