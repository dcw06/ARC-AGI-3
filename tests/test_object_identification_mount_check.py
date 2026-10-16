import hashlib
from pathlib import Path
import tempfile
import unittest
from research.object_identification_v1.mount_check import verify_files

class ByteProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'a.bin').write_bytes(b'original')
        self.rows = [{'name': 'a.bin', 'bytes': 8, 'sha256': hashlib.sha256(b'original').hexdigest()}]

    def test_exact_bytes_pass_and_same_size_mutation_fails(self):
        self.assertEqual(verify_files(self.root, self.rows, lambda: None)['files_checked'], 1)
        (self.root/'a.bin').write_bytes(b'mutated!')
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            verify_files(self.root, self.rows, lambda: None)

    def test_extra_files_and_traversal_are_rejected(self):
        (self.root/'extra').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            verify_files(self.root, self.rows, lambda: None)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            verify_files(self.root, [dict(self.rows[0], name='../a.bin')], lambda: None)

    def test_final_deadline_check_is_required(self):
        calls = []
        verify_files(self.root, self.rows, lambda: calls.append(True))
        remaining = len(calls)
        def check():
            nonlocal remaining
            remaining -= 1
            if not remaining:
                raise TimeoutError('late finalization')
        with self.assertRaises(TimeoutError):
            verify_files(self.root, self.rows, check)

if __name__ == '__main__':
    unittest.main()
