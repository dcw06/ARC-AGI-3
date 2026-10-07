"""Real offline pip installs with a Python image that cannot run ensurepip.

No real publisher wheels, model, account, network or GPU are used.
The regressions also run unchanged against fe63ce1.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from certification.direct_publisher_smoke_v1 import install as I, run as R
from certification.direct_publisher_smoke_v1.binding import load_protocol
from certification.direct_publisher_smoke_v1.rehearsal import fixture_bundle


@unittest.skipUnless(sys.platform == 'linux', 'Linux installation ownership required')
class BootstrapWithoutEnsurepip(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='offline-bootstrap-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.mount, self.inputs = self.base / 'mount', self.base / 'inputs'
        fixture_bundle(self.mount, self.inputs)
        self.wrapper = self.base / 'python'
        self.wrapper.write_text(f'#!{sys.executable}\n' + f'''import os, sys
args = sys.argv[1:]
if args[:2] == ['-m', 'venv'] and '--without-pip' not in args:
    print('ensurepip unavailable in this runtime image', file=sys.stderr)
    sys.exit(1)
os.execv({sys.executable!r}, [{sys.executable!r}, *args])
''')
        self.wrapper.chmod(0o755)
        self.runtime = {'packages': {'fixturea': '1.0', 'fixtureb': '1.0'},
                        'imports': ['fixturea', 'fixtureb']}

    def install(self):
        return I.install(self.mount, self.base / 'venv', self.runtime, time.monotonic() + 30,
                         self.base / 'install.log', python=str(self.wrapper),
                         requirements=self.inputs / 'trusted_requirements.lock')

    def test_offline_hash_pinned_install_without_ensurepip(self):
        try:
            result = self.install()
        except I.InstallFailed as exc:
            self.fail(f'offline install must work without ensurepip: {exc}')
        self.assertTrue(result['passed'])
        self.assertEqual(result['versions'], self.runtime['packages'])
        venv = (self.base / 'venv').resolve()
        for imported in result['imports'].values():
            self.assertTrue(Path(imported).resolve().is_relative_to(venv))
        # No host/site pip is installed or exposed to the managed environment.
        checked = subprocess.run([result['python'], '-I', '-c',
                                  'import importlib.util; print(importlib.util.find_spec("pip"))'],
                                 capture_output=True, text=True, check=True, timeout=5)
        self.assertEqual(checked.stdout.strip(), 'None')

    def test_hash_mismatch_still_fails_without_ensurepip(self):
        wheel = self.mount / 'fixturea-1.0-py3-none-any.whl'
        wheel.write_bytes(wheel.read_bytes() + b'tampered')
        with self.assertRaisesRegex(I.InstallFailed, 'offline install exited'):
            self.install()
        self.assertIn('HASHES', (self.base / 'install.log').read_text())

    def test_live_install_failure_does_not_claim_cpu_only_gpu_cleanup(self):
        protocol = load_protocol()
        with patch.object(R.host, 'host_facts', return_value={}), \
             patch.object(R, 'verify_bundle', return_value={}), \
             patch.object(R, 'install', side_effect=I.InstallFailed('ensurepip failed')):
            result = R.run('live', protocol, self.base / 'evidence', time.monotonic(),
                           bundle=self.mount, workdir=self.base / 'work',
                           gpu_query=lambda _: self.fail('GPU stage must not run'),
                           on_environment_cleanup=lambda: {'fixture': True})
        self.assertFalse(result['passed'])
        self.assertEqual(result['failed_stage'], 'installation')
        self.assertEqual(result['ledger']['issued'], 0)
        self.assertEqual(result['cleanup']['gpu'], 'not_exercised (GPU verification stage not reached)')


if __name__ == '__main__':
    unittest.main()
