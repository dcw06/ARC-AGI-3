"""Regressions for the review of c239f26: unsafe work directories, unbound manifests, slow response headers."""
import hashlib
import json
import shutil
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from scripts import check_wheelhouse_metadata as W
from scripts import check_wheelhouse_offline_install as O
from scripts import download_wheelhouse as D
from scripts import extract_wheelhouse_licenses as X

ROOT = Path(__file__).resolve().parents[1]


def tampered_manifest(folder):
    """The approved manifest with one artifact hash changed and its stored digest left untouched."""
    manifest = json.loads(O.MANIFEST.read_text(encoding='utf-8'))
    manifest['artifacts'][0]['sha256'] = '0' * 64
    path = folder / 'manifest.json'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    return path


class UnsafeWorkDirectory(unittest.TestCase):
    """Finding 1: the installer never recursively clears a user-supplied directory."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.wheels = self.tmp / 'wheels'
        self.wheels.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def refused(self, parent):
        with mock.patch.object(O.shutil, 'rmtree', side_effect=AssertionError('rmtree reached')), \
                mock.patch.object(O.tempfile, 'mkdtemp', side_effect=AssertionError('mkdtemp reached')):
            with self.assertRaises(SystemExit):
                O.main(['--wheels', str(self.wheels), '--workdir-parent', str(parent), '--allow-network'])

    def test_root_home_repository_and_ancestors_are_refused_before_any_change(self):
        for parent in ('/', str(Path.home()), str(ROOT), str(ROOT / 'reports'), str(ROOT.parent)):
            self.refused(parent)

    def test_overlapping_wheel_paths_are_refused(self):
        inside = self.wheels / 'sub'
        inside.mkdir()
        for parent in (self.wheels, inside, self.tmp):
            self.refused(parent)

    def test_a_fresh_child_is_created_and_nothing_else_is_touched(self):
        parent = self.tmp / 'parent'
        parent.mkdir()
        keep = parent / 'precious.txt'
        keep.write_text('must survive')
        evidence = self.tmp / 'evidence'
        with mock.patch.object(O, 'network_reachable', return_value=False), \
                mock.patch.object(O, 'verify_wheels', return_value=['broken.whl']), \
                mock.patch.object(O, 'RESULT', self.tmp / 'result.json'), \
                mock.patch.object(O, 'EVIDENCE', evidence):
            self.assertEqual(O.main(['--wheels', str(self.wheels), '--workdir-parent', str(parent)]), 1)
        children = [p for p in parent.iterdir() if p.is_dir()]
        self.assertEqual(len(children), 1)
        self.assertTrue(children[0].name.startswith('install-check-'))
        self.assertEqual(keep.read_text(), 'must survive')
        result = json.loads((self.tmp / 'result.json').read_text())
        self.assertEqual(result['work_directory'], str(children[0]))

    def test_removal_is_confined_to_the_exclusive_directory(self):
        work = self.tmp / 'work'
        work.mkdir()
        with self.assertRaises(O.CheckError):
            O.remove_inside(work, self.tmp)
        with self.assertRaises(O.CheckError):
            O.remove_inside(work, work)
        (work / 'venv').mkdir()
        O.remove_inside(work, work / 'venv')
        self.assertFalse((work / 'venv').exists())


class ManifestBinding(unittest.TestCase):
    """Finding 2: the installer and the licence extractor recompute the approved manifest's digest."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_approved_manifest_still_validates(self):
        manifest = D.load_manifest(O.MANIFEST, D.APPROVED_MANIFEST_SHA256)
        self.assertEqual(manifest['artifact_count'], 174)

    def test_installer_refuses_a_tampered_manifest_before_any_filesystem_change(self):
        bad = tampered_manifest(self.tmp)
        parent = self.tmp / 'parent'
        parent.mkdir()
        with mock.patch.object(O, 'MANIFEST', bad), \
                mock.patch.object(O.tempfile, 'mkdtemp', side_effect=AssertionError('mkdtemp reached')):
            with self.assertRaises(SystemExit):
                O.main(['--wheels', str(self.tmp / 'w'), '--workdir-parent', str(parent), '--allow-network'])
        self.assertEqual(list(parent.iterdir()), [])

    def test_licence_extractor_refuses_a_tampered_manifest(self):
        bad = tampered_manifest(self.tmp)
        with mock.patch.object(X, 'MANIFEST', bad), \
                mock.patch.object(X, 'extract', side_effect=AssertionError('extract reached')):
            with self.assertRaises(SystemExit):
                X.main(['--wheels', str(self.tmp / 'w'), '--texts', str(self.tmp / 't')])

    def test_licence_texts_may_not_overlap_the_wheels(self):
        with mock.patch.object(X, 'extract', side_effect=AssertionError('extract reached')):
            with self.assertRaises(SystemExit):
                X.main(['--wheels', str(self.tmp), '--texts', str(self.tmp / 'inside')])


class SlowHeaderServer:
    """A real local HTTP server that trickles its status line and headers one byte at a time."""

    def __init__(self, delay=0.05, total=4.0):
        self.sock = socket.socket()
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.delay, self.total = delay, total
        self.client_gone_at = None
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        conn, _ = self.sock.accept()
        conn.recv(65536)
        payload = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nX-Slow: ' + b'a' * 200 + b'\r\n\r\nbody'
        deadline = time.monotonic() + self.total
        try:
            for byte in payload:
                if time.monotonic() > deadline:
                    break
                conn.sendall(bytes([byte]))
                time.sleep(self.delay)
        except OSError:
            self.client_gone_at = time.monotonic()
        finally:
            conn.close()
            self.sock.close()


class SlowHeaders(unittest.TestCase):
    """Finding 3: a total deadline interrupts response headers that trickle in."""

    def test_metadata_client_returns_at_the_deadline_and_cancels_the_socket(self):
        server = SlowHeaderServer()
        url = f'http://127.0.0.1:{server.port}/simple/demo/'
        client = W.Client(budget=5, total_deadline=0.15, operation_timeout=5.0)
        start = time.monotonic()
        with mock.patch.object(W, 'check_url', lambda u: None):
            with self.assertRaises(W.DeadlineExceeded) as raised:
                client.get(url, 10_000)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 0.15 + 0.35, elapsed)
        self.assertIn('worker stopped: True', str(raised.exception))
        server.thread.join(3)
        self.assertIsNotNone(server.client_gone_at, 'the server never saw the connection closed')
        self.assertLess(server.client_gone_at - start, 1.5)

    def test_downloader_returns_at_the_deadline_and_leaves_no_partial_file(self):
        server = SlowHeaderServer()
        tmp = Path(tempfile.mkdtemp())
        try:
            artifact = {'filename': 'demo-1.0-py3-none-any.whl', 'size': 4, 'sha256': hashlib.sha256(b'body').hexdigest(),
                        'url': f'http://127.0.0.1:{server.port}/demo-1.0-py3-none-any.whl'}
            dl = D.Downloader(tmp, sleep=lambda s: None)
            start = time.monotonic()
            with mock.patch.object(D, '_artifact_url_ok', lambda url, name: True), \
                    mock.patch.object(D, 'BASE_DEADLINE', 0.15), mock.patch.object(D, 'MIN_RATE', 10 ** 12):
                result = dl.fetch(artifact)
            elapsed = time.monotonic() - start
            self.assertEqual(result['status'], 'failed')
            self.assertIn('deadline', result['reason'])
            self.assertLess(elapsed, 0.15 + 0.35, elapsed)
            server.thread.join(3)
            self.assertIsNotNone(server.client_gone_at)
            time.sleep(0.2)
            self.assertEqual(list((tmp / '.partial').glob('*')), [])
            self.assertFalse((tmp / artifact['filename']).exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_fast_local_response_still_completes(self):
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        sock.listen(1)
        port = sock.getsockname()[1]

        def serve():
            conn, _ = sock.accept()
            conn.recv(65536)
            conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok')
            conn.close()
            sock.close()
        threading.Thread(target=serve, daemon=True).start()
        client = W.Client(budget=5, total_deadline=5.0, operation_timeout=2.0)
        with mock.patch.object(W, 'check_url', lambda u: None):
            body, _ = client.get(f'http://127.0.0.1:{port}/x', 100)
        self.assertEqual(body, b'ok')


if __name__ == '__main__':
    unittest.main()
