"""Review the exact Stage B reservation package without provider access."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from research.grounded_action_v1 import authority
from scripts import phase4_grounded_action_v1_package as package

ROOT = Path(__file__).resolve().parents[1]


def fixture(root):
    lock = json.loads((ROOT / authority.REVIEW).read_bytes())
    names = set(lock['bindings']) | {authority.REVIEW}
    names |= {str(Path(authority.REVIEW).parent / name) for name in lock['artifacts']}
    for name in names:
        source, target = ROOT / name, root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return hashlib.sha256((root / authority.REVIEW).read_bytes()).hexdigest()


class Backend:
    def __init__(self, remaining=7200):
        self.remaining = remaining
        self.pushes = 0

    def quota(self):
        return {'total_time_allowed': self.remaining, 'time_used': 0,
                'time_reserved': 0}

    def push(self, _folder):
        self.pushes += 1
        return SimpleNamespace(url='https://www.kaggle.com/code/fixture/stage-b',
                               version_number=1, error=None)


class PackageTests(unittest.TestCase):
    def test_separate_authority_exact_package_and_one_use_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            lock_hash = fixture(root)
            with self.assertRaises((OSError, PermissionError)):
                package.reserve(root)
            with self.assertRaises((OSError, PermissionError)):
                package.record_approval(root, 'compute', 'separate fixture compute', lock_hash)
            package.record_approval(root, 'source', 'explicit fixture source', lock_hash)
            with self.assertRaises(FileExistsError):
                package.record_approval(root, 'source', 'second source', lock_hash)
            with self.assertRaises((OSError, PermissionError)):
                package.reserve(root)
            package.record_approval(root, 'compute', 'separate fixture compute', lock_hash)
            execution = package.reserve(root)
            with self.assertRaises(PermissionError):
                package.reserve(root)
            lock = package.package(root)
            self.assertEqual(lock['attempt_id'], execution['attempt_id'])
            self.assertEqual(package.verify(root), lock)
            metadata = json.loads((root / package.PACKAGE / 'kernel-metadata.json').read_bytes())
            self.assertTrue(metadata['enable_gpu'])
            self.assertFalse(metadata['enable_internet'])
            book = json.loads((root / package.PACKAGE / 'profile.ipynb').read_bytes())
            code = book['cells'][1]['source']
            self.assertIn('authority_payload=', code)
            sentinel = '    from scripts.phase4_grounded_action_v1_launch import run\n'
            self.assertEqual(code.count(sentinel), 1)
            probe = code.replace(sentinel,
                '    from research.grounded_action_v1.authority import require as packaged_require\n'
                f'    assert packaged_require(source)["attempt_id"] == {execution["attempt_id"]!r}\n'
                '    raise SystemExit(0)\n')
            check = root / 'package-gate-probe.py'
            check.write_text(probe)
            result = subprocess.run([sys.executable, '-I', str(check)], cwd=root,
                                    env=dict(os.environ, TMPDIR=str(root), TMP=str(root), TEMP=str(root)),
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr[-1000:])
            with self.assertRaises(PermissionError):
                package.launch(root, Backend(remaining=3599))
            self.assertFalse((root / package.CLAIM).exists())
            backend = Backend()
            receipt = package.launch(root, backend)
            self.assertEqual(backend.pushes, 1)
            self.assertEqual(receipt['status'], 'provider_response_received')
            self.assertFalse(receipt['automatic_retry_authorized'])
            self.assertEqual(json.loads((root / authority.RESERVATION).read_bytes())['status'],
                             'consumed')
            with self.assertRaises(PermissionError):
                package.launch(root, backend)
            self.assertEqual(backend.pushes, 1)

    def test_drifted_or_consumed_authority_never_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            lock_hash = fixture(root)
            package.record_approval(root, 'source', 'explicit fixture source', lock_hash)
            package.record_approval(root, 'compute', 'separate fixture compute', lock_hash)
            package.reserve(root)
            source_file = root / 'research/grounded_action_v1/contract.py'
            original = source_file.read_bytes()
            source_file.write_bytes(original + b'\n')
            with self.assertRaises((PermissionError, ValueError)):
                package.materialize(root)
            source_file.write_bytes(original)
            package.package(root)
            notebook = root / package.PACKAGE / 'profile.ipynb'
            notebook.write_bytes(notebook.read_bytes() + b'\n')
            with self.assertRaises(PermissionError):
                package.verify(root)
            reservation = root / authority.RESERVATION
            value = json.loads(reservation.read_bytes())
            value['status'] = 'consumed'
            reservation.write_text(json.dumps(value))
            with self.assertRaises(PermissionError):
                package.materialize(root)


if __name__ == '__main__':
    unittest.main()
