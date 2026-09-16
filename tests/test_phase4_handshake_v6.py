import json
from pathlib import Path
import tempfile
import unittest

from certification.phase4_v6.handshake import read_local_ready


class HandshakeTests(unittest.TestCase):
    def test_exact_identity_required(self):
        good = dict(kind='local_cpu_monitor_ready', nonce='fresh', worker_pid=123, monitor_pid=456)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ready.json'
            path.write_text(json.dumps(good))
            self.assertEqual(read_local_ready(path, nonce='fresh', worker_pid=123, monitor_pid=456), good)
            for delta in ({'nonce': 'stale'}, {'worker_pid': 1}, {'monitor_pid': 1},
                          {'kind': 'gpu_ready'}, {'extra': True}):
                path.write_text(json.dumps({**good, **delta}))
                with self.assertRaises(ValueError):
                    read_local_ready(path, nonce='fresh', worker_pid=123, monitor_pid=456)

    def test_bad_json_oversize_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ready.json'
            for data in ('broken', 'x' * 4097):
                path.write_text(data)
                with self.assertRaises(ValueError):
                    read_local_ready(path, nonce='n', worker_pid=123, monitor_pid=456)
            link = Path(folder) / 'link.json'
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                read_local_ready(link, nonce='n', worker_pid=123, monitor_pid=456)
