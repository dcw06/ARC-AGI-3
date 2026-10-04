"""Unit checks of scripts/check_wheelhouse_offline_install.py (no installation is performed here)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import check_wheelhouse_offline_install as O

ROOT = Path(__file__).resolve().parents[1]


class Lock(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(O.MANIFEST.read_text(encoding='utf-8'))

    def test_lock_pins_every_artifact_by_version_and_hash(self):
        lines = O.lock_lines(self.manifest)
        self.assertEqual(len(lines), 174)
        torch = next(l for l in lines if l.startswith('torch=='))
        sha = next(a['sha256'] for a in self.manifest['artifacts'] if a['filename'].startswith('torch-2.10.0-3-'))
        self.assertEqual(torch, f'torch==2.10.0 --hash=sha256:{sha}')
        self.assertTrue(all(' --hash=sha256:' in l for l in lines))

    def test_the_approved_manifest_is_the_one_bound(self):
        self.assertEqual(self.manifest['manifest_sha256'], O.EXPECTED_MANIFEST)

    def test_install_command_is_offline_and_hash_pinned(self):
        cmd = O.install_command('/v/bin/python', Path('/w'), Path('/l'))
        for flag in ('--no-index', '--no-cache-dir', '--require-hashes', '--only-binary=:all:'):
            self.assertIn(flag, cmd)
        self.assertNotIn('--index-url', cmd)
        self.assertNotIn('--extra-index-url', cmd)

    def test_clean_environment_has_no_user_config_or_network_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = O.clean_env(Path(tmp))
        self.assertEqual(env['PIP_CONFIG_FILE'], '/dev/null')
        self.assertEqual(env['PYTHONNOUSERSITE'], '1')
        self.assertNotIn('PIP_INDEX_URL', env)
        self.assertNotIn('http_proxy', {k.lower() for k in env})


class Refusals(unittest.TestCase):
    def test_refuses_paths_inside_the_repository(self):
        with self.assertRaises(SystemExit):
            O.main(['--wheels', str(ROOT / 'reports'), '--workdir-parent', '/tmp', '--allow-network'])

    def test_refuses_when_the_network_is_reachable(self):
        with mock.patch.object(O, 'network_reachable', return_value=True):
            with self.assertRaises(SystemExit):
                O.main(['--wheels', '/tmp/w', '--workdir-parent', '/tmp'])

    def test_wheel_verification_detects_bad_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = b'abc'
            manifest = {'artifacts': [{'filename': 'a-1.0-py3-none-any.whl', 'size': 3,
                                       'sha256': hashlib.sha256(body).hexdigest()},
                                      {'filename': 'b-1.0-py3-none-any.whl', 'size': 3, 'sha256': '0' * 64}]}
            (Path(tmp) / 'a-1.0-py3-none-any.whl').write_bytes(body)
            (Path(tmp) / 'b-1.0-py3-none-any.whl').write_bytes(body)
            self.assertEqual(O.verify_wheels(manifest, Path(tmp)), ['b-1.0-py3-none-any.whl'])


class Freeze(unittest.TestCase):
    def test_freeze_comparison(self):
        manifest = {'artifacts': [{'filename': 'Foo_Bar-1.0-py3-none-any.whl'},
                                  {'filename': 'torch-2.10.0-3-cp312-cp312-manylinux_2_28_x86_64.whl'}]}
        ok = O.compare_freeze('foo-bar==1.0\ntorch==2.10.0\npip==24.0\n', manifest)
        self.assertEqual((ok['missing'], ok['version_mismatch'], ok['extra'], ok['pip']), ([], [], [], '24.0'))
        bad = O.compare_freeze('foo-bar==1.1\nsurprise==9\n', manifest)
        self.assertEqual(bad['missing'], ['torch'])
        self.assertEqual(bad['version_mismatch'], ['foo-bar'])
        self.assertEqual(bad['extra'], ['surprise'])


if __name__ == '__main__':
    unittest.main()
