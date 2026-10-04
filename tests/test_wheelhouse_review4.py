"""Regressions for the review of 2b1a5d1: result delivery bounded by the deadline; cleanup on interruption."""
import hashlib
import multiprocessing
import os
import shutil
import signal
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from scripts import check_wheelhouse_metadata as W
from scripts import download_wheelhouse as D

ALLOWANCE = 1.5  # seconds: spawn start-up plus kill and reap


# Worker targets (module level so a spawned process can import them).
def target_complete(result_path, value):
    W.deliver(result_path, ('ok', value))


def target_partial_then_stall(result_path, seconds):
    with open(result_path, 'wb') as stream:  # the start of a result written in place, never completed
        stream.write(b'\x80\x05partial-header')
        stream.flush()
    time.sleep(seconds)


def target_crash_midway(result_path):
    with open(result_path + '.partial', 'wb') as stream:
        stream.write(b'half a result')
    os._exit(3)


def target_late(result_path, seconds):
    W.deliver(result_path, ('ok', 'too late'))
    time.sleep(seconds)  # complete, but the worker has not exited by the deadline


def target_sleep(result_path, seconds):
    time.sleep(seconds)


def dead(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


def interrupt_main_after(seconds):
    main = threading.main_thread().ident
    timer = threading.Timer(seconds, lambda: signal.pthread_kill(main, signal.SIGINT))
    timer.daemon = True
    timer.start()
    return timer


class ResultDelivery(unittest.TestCase):
    def run_target(self, target, args, deadline_s):
        pids = []
        start = time.monotonic()
        try:
            return W.run_worker(target, args, time.monotonic() + deadline_s, time.monotonic, 'a test worker',
                                observer=pids), pids, time.monotonic() - start
        except BaseException as error:
            error.pids, error.elapsed = pids, time.monotonic() - start
            raise

    def test_a_complete_result_is_preserved(self):
        value, pids, _ = self.run_target(target_complete, ({'a': [1, 2]},), 10)
        self.assertEqual(value, ('ok', {'a': [1, 2]}))
        self.assertTrue(dead(pids[0]))
        self.assertEqual(multiprocessing.active_children(), [])

    def test_a_partial_result_then_stall_is_killed_at_the_deadline(self):
        with self.assertRaises(W.DeadlineExceeded) as raised:
            self.run_target(target_partial_then_stall, (30,), 1.0)
        self.assertIn('terminated: True', str(raised.exception))
        self.assertLess(raised.exception.elapsed, 1.0 + ALLOWANCE)
        self.assertTrue(dead(raised.exception.pids[0]))

    def test_a_crash_midway_is_a_controlled_failure_with_no_partial_result(self):
        with self.assertRaises(W.WorkerFailed) as raised:
            self.run_target(target_crash_midway, (), 10)
        self.assertIn('code 3', str(raised.exception))
        self.assertTrue(dead(raised.exception.pids[0]))

    def test_a_result_completed_after_the_deadline_is_rejected(self):
        with self.assertRaises(W.DeadlineExceeded):
            self.run_target(target_late, (30,), 1.0)

    def test_interrupting_the_parent_cleans_up_the_worker_first(self):
        interrupt_main_after(1.0)
        with self.assertRaises(KeyboardInterrupt) as raised:
            self.run_target(target_sleep, (60,), 30)
        self.assertLess(raised.exception.elapsed, 1.0 + ALLOWANCE)
        self.assertTrue(dead(raised.exception.pids[0]), 'the worker survived the interruption')
        self.assertEqual(multiprocessing.active_children(), [])

    def test_temporary_result_directories_are_removed(self):
        before = set(Path(tempfile.gettempdir()).glob('wheelhouse-worker-*'))
        self.run_target(target_complete, ('x',), 10)
        with self.assertRaises(W.WorkerFailed):
            self.run_target(target_crash_midway, (), 10)
        self.assertEqual(set(Path(tempfile.gettempdir()).glob('wheelhouse-worker-*')), before)


class InterruptedDownload(unittest.TestCase):
    def test_interrupted_download_publishes_nothing_and_cleans_up_after_the_worker(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            artifact = {'filename': 'demo-1.0-py3-none-any.whl', 'size': 2, 'sha256': hashlib.sha256(b'ok').hexdigest(),
                        'url': 'http://127.0.0.1:9/demo-1.0-py3-none-any.whl'}
            dl = D.Downloader(tmp, sleep=lambda s: None)
            interrupt_main_after(1.0)
            with mock.patch.object(D, '_artifact_url_ok', lambda url, name: True), \
                    mock.patch.object(D, 'BASE_DEADLINE', 30), mock.patch.object(D, 'MIN_RATE', 10 ** 12), \
                    mock.patch.dict(os.environ, {W.STALL_ENV: '60'}):
                with self.assertRaises(KeyboardInterrupt):
                    dl.fetch(artifact)
            self.assertTrue(dl.worker_pids and dead(dl.worker_pids[0]), 'the download worker survived')
            self.assertFalse((tmp / artifact['filename']).exists())
            self.assertEqual(list((tmp / '.partial').glob('*')), [])
            self.assertEqual(multiprocessing.active_children(), [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class NoConnectionAfterCancellation(unittest.TestCase):
    """Cancellation before the connection: the worker is killed and never connects (re-asserted on this design)."""

    def test_no_connection_after_a_cancelled_stalled_worker(self):
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        sock.listen(5)
        sock.settimeout(0.1)
        port, accepted = sock.getsockname()[1], []

        def serve():
            end = time.monotonic() + 3.0
            while time.monotonic() < end:
                try:
                    conn, _ = sock.accept()
                except OSError:
                    continue
                accepted.append(time.monotonic())
                conn.close()
            sock.close()
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        client = W.Client(budget=5, total_deadline=0.2, operation_timeout=5.0)
        with mock.patch.object(W, 'check_url', lambda u: None), mock.patch.dict(os.environ, {W.STALL_ENV: '1.5'}):
            with self.assertRaises(W.DeadlineExceeded):
                client.get(f'http://127.0.0.1:{port}/x', 100)
        thread.join(5)
        self.assertEqual(accepted, [])


if __name__ == '__main__':
    unittest.main()
