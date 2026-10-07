"""Run retained descendant regressions against a separate source checkout.

Example (Linux, CPU only):
  python scripts/reproduce_direct_publisher_install_timeout.py \
      --source-root /tmp/baseline-500caa6 --expect vulnerable --out /tmp/baseline.json

The current regression fixture is imported with the target checkout's controller.
Its teardown explicitly terminates/reaps leaked fixture children on the baseline.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['test_installation_timeout_descendant_is_reaped_before_cleanup_verified',
         'test_import_timeout_descendant_is_reaped_before_cleanup_verified']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--expect', required=True, choices=['vulnerable', 'fixed'])
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    target = args.source_root.resolve()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=target, text=True).strip()
    clean = not subprocess.check_output(['git', 'status', '--porcelain'], cwd=target, text=True).strip()
    sys.path.insert(0, str(target))
    path = ROOT / 'tests/test_direct_publisher_smoke_install_lifecycle.py'
    spec = importlib.util.spec_from_file_location('installation_timeout_regressions', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for controller in (module.I, module.R, module.S):
        if not Path(controller.__file__).resolve().is_relative_to(target):
            raise RuntimeError('regression imported a controller outside the target checkout')
    observations = []

    class RetainedReproduction(module.InstallationDescendants):
        def execute(self, *a, **kw):
            result = super().execute(*a, **kw)
            pids = [int(p.read_text()) for p in self.base.glob('*.pid')]
            observations.append({'test': self._testMethodName, 'passed': result['passed'],
                                 'failed_stage': result['failed_stage'], 'error': result['error'],
                                 'cleanup_verified': result['cleanup_verified'], 'cleanup': result['cleanup'],
                                 'fixture_pids': pids,
                                 'pids_present_when_cleanup_reported': [p for p in pids if Path(f'/proc/{p}').exists()]})
            return result

    suite = unittest.TestSuite(RetainedReproduction(name) for name in NAMES)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.with_suffix('.log').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    remaining = [p for observation in observations for p in observation['fixture_pids']
                 if Path(f'/proc/{p}').exists()]
    expected = (len(result.failures) == 2 and not result.errors and not result.skipped
                and len(observations) == 2 and all(o['pids_present_when_cleanup_reported']
                                                 and o['cleanup_verified'] for o in observations)) \
        if args.expect == 'vulnerable' else result.wasSuccessful() and not result.skipped
    report = {'schema': 'direct_publisher_install_timeout_reproduction_v1', 'source_revision': revision,
              'working_tree_clean_before_checks': clean, 'python': platform.python_version(),
              'regression_fixture_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'controller_install_sha256': hashlib.sha256(Path(module.I.__file__).read_bytes()).hexdigest(),
              'evidence_class': 'scripted_cpu_regressions', 'expected': args.expect,
              'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'observations': observations, 'fixture_pids_present_after_teardown': remaining,
              'as_expected': bool(expected and not remaining), 'gpu_launched': False}
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('source_revision', 'expected', 'tests_run', 'failures', 'errors',
                                           'fixture_pids_present_after_teardown', 'as_expected')}, indent=2))
    return 0 if report['as_expected'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
