"""Retain Linux CPU regression results and reproduce both frozen review snapshots. No external operations."""
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
    if sys.platform != 'linux':
        raise SystemExit('Linux required for process groups and complete CPU fixture installation checks')
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    suite = unittest.defaultTestLoader.loadTestsFromNames(SUITES + ['tests.test_control_interface_action_selection_v1'])
    folder = ROOT / 'reports/control_interface_action_selection_v1'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'cpu_checks.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(suite)
    snapshots = {'smoke_r10': reproduce(smoke, 'direct-publisher-smoke-v1-review-r10'),
                 'research_r1': reproduce(research, 'control-interface-action-selection-v1-review-r1')}
    lock = ROOT / 'notebooks/control-interface-action-selection-v1-review-r1/review-source-lock.json'
    record = {'schema': 'control_interface_action_selection_cpu_checks_v1', 'python': platform.python_version(),
        'evidence_class': 'scripted_cpu_control_checks_not_model_performance', 'gpu_used': False,
        'model_calls': 0, 'launch_authorized': False, 'review_lock_sha256': sha256(lock),
        'summary': {'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped)},
        'tests': result.records, 'snapshots_reproduce': snapshots,
        'passed': result.wasSuccessful() and all(all(r.values()) for r in snapshots.values())}
    (folder / 'cpu_checks.json').write_text(json.dumps(record, sort_keys=True, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('passed', 'summary', 'snapshots_reproduce')}, indent=1))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
