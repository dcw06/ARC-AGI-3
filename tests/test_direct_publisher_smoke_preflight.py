"""Integrity refusals with small fixture bytes; never install or use a GPU."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from certification.direct_publisher_smoke_v1.preflight import PreflightFailed, load_inputs, verify_mounted


def sha(data):
    return hashlib.sha256(data).hexdigest()


class DirectPublisherPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'package'
        self.mount = self.root / 'mount'
        self.package.mkdir()
        self.mount.mkdir()
        self.rows = []
        lock = ''
        plain = ''
        for name in ('alpha', 'beta'):
            payload = (name + ' fixture wheel bytes').encode()
            filename = name + '-1.0-py3-none-any.whl'
            (self.mount / filename).write_bytes(payload)
            self.rows.append({'filename': filename, 'sha256': sha(payload), 'size': len(payload)})
            plain += name + '==1.0\n'
            lock += name + '==1.0 --hash=sha256:' + sha(payload) + '\n'
        (self.package / 'trusted_requirements.lock').write_bytes(lock.encode())
        self.metadata = {'README.md': b'fixture\n', 'requirements.lock': plain.encode(),
                         'SHA256SUMS': ''.join(row['sha256'] + '  ' + row['filename'] + '\n'
                                              for row in self.rows).encode()}
        for name, data in self.metadata.items():
            (self.mount / name).write_bytes(data)
        self.proposal = {'dataset': {'ref': 'fixture/source', 'version': 1}, 'wheel_count': 2,
                         'integrity_budget_seconds': 100, 'trusted_requirements_sha256': sha(lock.encode()),
                         'trusted_artifacts_sha256': sha(json.dumps(self.rows, sort_keys=True,
                                                                   separators=(',', ':')).encode()),
                         'publisher_metadata_sha256': {n: sha(d) for n, d in self.metadata.items()}}
        self.save_inputs()

    def save_inputs(self):
        (self.package / 'proposal.json').write_text(json.dumps(self.proposal))
        (self.package / 'trusted_manifest.json').write_text(json.dumps({'artifacts': self.rows}))

    def verify(self, **kwargs):
        return verify_mounted(self.mount, package=self.package, **kwargs)

    def test_nominal_integrity_never_claims_permission_or_launch(self):
        with patch('subprocess.run', side_effect=AssertionError('no subprocess permitted')):
            receipt = self.verify()
        self.assertTrue(receipt['integrity_passed'])
        self.assertEqual(receipt['wheel_bytes_verified'], 2)
        for field in ('account_attachment_verified', 'provider_attachment_version_verified',
                      'permissions_assessed', 'gpu_compatibility_established', 'launch_authorized'):
            self.assertIs(receipt[field], False)

    def test_same_size_wheel_tampering_refused(self):
        path = self.mount / self.rows[0]['filename']
        path.write_bytes(b'x' * path.stat().st_size)
        with self.assertRaisesRegex(PreflightFailed, 'wheel byte hash differs'):
            self.verify()

    def test_missing_and_extra_files_refused(self):
        for extra in (False, True):
            with self.subTest(extra=extra):
                target = self.mount / ('unlisted.whl' if extra else self.rows[0]['filename'])
                if extra:
                    target.write_bytes(b'unlisted')
                else:
                    data = target.read_bytes()
                    target.unlink()
                with self.assertRaisesRegex(PreflightFailed, 'file inventory differs'):
                    self.verify()
                if extra:
                    target.unlink()
                else:
                    target.write_bytes(data)

    def test_publisher_metadata_tampering_refused(self):
        (self.mount / 'requirements.lock').write_bytes(b'alpha==9.0\nbeta==1.0\n')
        with self.assertRaisesRegex(PreflightFailed, 'publisher metadata differs'):
            self.verify()

    def test_publisher_pin_mismatch_refused_even_when_metadata_bound(self):
        data = b'alpha==9.0\nbeta==1.0\n'
        (self.mount / 'requirements.lock').write_bytes(data)
        self.proposal['publisher_metadata_sha256']['requirements.lock'] = sha(data)
        self.save_inputs()
        with self.assertRaisesRegex(PreflightFailed, 'package/version pins differ'):
            self.verify()

    def test_trusted_lock_tampering_refused(self):
        (self.package / 'trusted_requirements.lock').write_bytes(b'alpha==1.0\n')
        with self.assertRaisesRegex(PreflightFailed, 'requirements differ'):
            self.verify()

    def test_trusted_manifest_tampering_refused(self):
        self.rows[0]['sha256'] = '0' * 64
        self.save_inputs()
        with self.assertRaisesRegex(PreflightFailed, 'inventory differs from its binding'):
            self.verify()

    def test_deadline_crossed_on_final_check_refused(self):
        calls = []
        self.verify(now=lambda: calls.append(0) or 0)
        final_call = len(calls)
        count = 0

        def now():
            nonlocal count
            count += 1
            return 100 if count == final_call else 0

        with self.assertRaisesRegex(PreflightFailed, 'deadline exceeded'):
            self.verify(now=now)
        self.assertEqual(count, final_call)

    def test_symlink_refused(self):
        target = self.mount / self.rows[0]['filename']
        saved = self.root / 'original'
        target.replace(saved)
        try:
            target.symlink_to(saved)
        except OSError:
            self.skipTest('symlinks unavailable on this platform')
        with self.assertRaisesRegex(PreflightFailed, 'symlink'):
            self.verify()

    def test_retained_production_inputs_are_consistent(self):
        proposal, rows, trusted_pins = load_inputs()
        self.assertEqual(len(rows), 174)
        self.assertEqual(len(trusted_pins), 174)
        self.assertEqual(proposal['dataset']['ref'], 'driessmit1/arc3-vllm-h100-wheelhouse-v3')


if __name__ == '__main__':
    unittest.main()
