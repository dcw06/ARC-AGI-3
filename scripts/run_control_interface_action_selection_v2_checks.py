"""Retain Linux CPU checks and reproduce historical and successor snapshots. No external operations."""
import json
import os
import platform
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_direct_publisher_smoke_checks import Recorder, SUITES
from scripts.run_control_interface_action_selection_checks import reproduce
from certification.direct_publisher_smoke_v1 import notebook as smoke
from research.control_interface_action_selection_v1 import notebook as baseline
from research.control_interface_action_selection_v2 import notebook as successor
from research.control_interface_action_selection_v2.binding import sha256


def main():
    if sys.platform != 'linux':
        raise SystemExit('Linux required for process-group and CPU fixture controls')
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    suites = SUITES + ['tests.test_control_interface_action_selection_v1',
                      'tests.test_control_interface_action_selection_v2',
                      'tests.test_control_interface_action_selection_v2_contract']
    tests = unittest.defaultTestLoader.loadTestsFromNames(suites)
    folder = ROOT / 'reports/control_interface_action_selection_v2'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'cpu_checks.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(tests)
    snapshots = {label: reproduce(module, name) for label, module, name in (
        ('smoke_r10', smoke, 'direct-publisher-smoke-v1-review-r10'),
        ('baseline_v1_r2', baseline, 'control-interface-action-selection-v1-review-r2'),
        ('successor_v2_r1', successor, 'control-interface-action-selection-v2-review-r1'))}
    record = {'schema': 'control_interface_action_selection_v2_cpu_checks', 'python': platform.python_version(),
        'evidence_class': 'scripted_cpu_control_checks_not_model_performance', 'gpu_used': False,
        'model_calls': 0, 'provider_calls': 0, 'launch_authorized': False, 'review_revision': 1,
        'review_lock_sha256': sha256(ROOT / 'notebooks/control-interface-action-selection-v2-review-r1/review-source-lock.json'),
        'summary': {'run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped)},
        'tests': result.records, 'snapshots_reproduce': snapshots,
        'passed': result.wasSuccessful() and all(all(r.values()) for r in snapshots.values())}
    (folder / 'cpu_checks.json').write_bytes((json.dumps(record, sort_keys=True, indent=1) + '\n').encode())
    print(json.dumps({k: record[k] for k in ('passed', 'summary', 'snapshots_reproduce')}, indent=1))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
