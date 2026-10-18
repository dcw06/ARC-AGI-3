"""Connected transport and lifecycle fault checks; no neural inference or GPU."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from certification.direct_publisher_smoke_v1.accounting import Clock, Ledger
from certification.direct_publisher_smoke_v1.client import Client, RequestFailed
from research.initial_geometry_assistance_v1.live_evaluation import audit_transport
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.live_package import check_notebook, normalized, EMPTY_LOCK
from research.initial_geometry_assistance_v1.geometry import canonical, digest
from research.initial_geometry_assistance_v1.live_resources import Processes, environment
from research.initial_geometry_assistance_v1.live_runtime import SCOPE, check_authority, finalize
from research.initial_geometry_assistance_v1.live_worker import DurableLedger, canary, request_plan
from research.initial_geometry_assistance_v1.model_io import validate_reply


def reply(body):
    return {'model': body['model'], 'choices': [{'message': {'role': 'assistant', 'content': 'ok'},
                                               'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 5, 'completion_tokens': 1, 'total_tokens': 6}}


class Watch:
    def __init__(self):
        self.pids = []
    def register(self, group):
        self.pids.append(group.pgid)
        return len(self.pids)-1
    def clear(self, slot, receipt):
        if not receipt['groups_absent']:
            raise ValueError('uncertain')
        self.pids[slot] = 0


class LiveChecks(unittest.TestCase):
    @staticmethod
    def synthetic_authority(pin):
        proofs = {kind: {'kind': kind, 'approved': True, 'review_lock_sha256': pin, 'scope': SCOPE,
                         'account': 'daichongwei06', 'owner_statement': 'SYNTHETIC UNIT TEST ONLY; NOT REAL APPROVAL'}
                  for kind in ('source_approval', 'use_permission', 'compute_authorization')}
        return {'review_lock_sha256': pin, 'scope': SCOPE, 'account': 'daichongwei06', 'proofs': proofs,
                **{kind: digest(record) for kind, record in proofs.items()},
                'attempt_id': 'unit-test', 'reservation': 'unit-test', 'claim': 'unit-test'}

    def test_approval_evidence_must_bind_exact_scope_and_lock(self):
        pin = 'a'*64
        value = self.synthetic_authority(pin)
        check_authority(value, pin)
        with self.assertRaises(PermissionError):
            check_authority(value, 'b'*64)
        value['proofs']['compute_authorization']['scope'] = {**SCOPE, 'generations': 300}
        with self.assertRaises(PermissionError):
            check_authority(value, pin)

    def test_notebook_seal_allows_only_authority_literal(self):
        pin = 'a'*64
        book = {'cells': [{'cell_type': 'code', 'id': 'launch-authority', 'source': 'AUTHORITY = None\n',
                            'outputs': [], 'execution_count': None},
                           {'cell_type': 'markdown', 'id': 'scope', 'source': 'scope'},
                           {'cell_type': 'code', 'id': 'runner', 'source': 'REVIEW_LOCK_SHA256 = '+repr(pin)+'\nprint(1)',
                            'outputs': [], 'execution_count': None}]}
        lock = {'notebook_template_sha256': hashlib.sha256(canonical(normalized(book))).hexdigest()}
        check_notebook(book, lock, pin, live=False)
        active = deepcopy(book)
        active['cells'][0]['source'] = 'AUTHORITY = '+repr(self.synthetic_authority(pin))+'\n'
        check_notebook(active, lock, pin, live=True)
        active['cells'][2]['source'] += '\nprint(2)'
        with self.assertRaises(ValueError):
            check_notebook(active, lock, pin, live=True)
        book['cells'][0]['source'] += 'print(99)\n'
        with self.assertRaises((ValueError, SyntaxError)):
            check_notebook(book, lock, pin, live=False)

    def test_saved_provider_image_privacy_and_sources_are_bound(self):
        from research.initial_geometry_assistance_v1.live_operator import validate_saved
        pin = 'a'*64
        book = {'cells': [{'cell_type': 'code', 'id': 'launch-authority',
                            'source': 'AUTHORITY = '+repr(self.synthetic_authority(pin))+'\n',
                            'outputs': [], 'execution_count': None},
                           {'cell_type': 'markdown', 'id': 'scope', 'source': 'scope'},
                           {'cell_type': 'code', 'id': 'runner', 'source': 'REVIEW_LOCK_SHA256 = '+repr(pin)+'\nprint(1)',
                            'outputs': [], 'execution_count': None}]}
        expected = {'slug': 'daichongwei06/unit-test', 'is_private': True, 'enable_gpu': True,
                    'enable_tpu': False, 'enable_internet': False, 'machine_shape': 'NvidiaRtxPro6000',
                    'docker_image': 'pinned-image', 'dataset_data_sources': ['a/wheels/1', 'a/model/1'],
                    'competition_data_sources': ['competition'], 'kernel_data_sources': [], 'model_data_sources': []}
        metadata = {k: v for k, v in expected.items() if k != 'slug'}
        metadata.update(ref=expected['slug'], current_version_number=2)
        lock = {'save_fields': expected, 'notebook_template_sha256': hashlib.sha256(canonical(normalized(book))).hexdigest()}
        snapshot = {'metadata': metadata, 'source': book}
        validate_saved(snapshot, lock, pin, 2)
        for key, value in [('is_private', False), ('docker_image', 'changed'), ('machine_shape', 'T4'),
                           ('enable_internet', True), ('dataset_data_sources', ['a/other/1'])]:
            with self.subTest(key=key):
                bad = deepcopy(snapshot)
                bad['metadata'][key] = value
                with self.assertRaises(ValueError):
                    validate_saved(bad, lock, pin, 2)

    def test_no_authority_never_passes(self):
        for value in (None, {}, {'source_approval': 'yes'}):
            with self.assertRaises(PermissionError):
                check_authority(value, 'a'*64)

    def test_model_reply_bounds_independent(self):
        body = canary()
        self.assertEqual(validate_reply(body, reply(body), 5), 'ok')
        mutations = [('prompt_tokens', True), ('prompt_tokens', -5), ('completion_tokens', True),
                     ('completion_tokens', 0), ('completion_tokens', 17), ('total_tokens', 0)]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                bad = reply(body)
                bad['usage'][key] = value
                with self.assertRaises(ValueError):
                    validate_reply(body, bad, 5)
        with self.assertRaises(ValueError):
            validate_reply(body, reply(body), 6)

    def test_request_schedule_counts_once(self):
        cases = [{'case_id': str(i), 'order': ['automatic', 'reviewed']} for i in range(6)]
        plan = request_plan(cases)
        self.assertEqual(len(plan), 289)
        clock = Clock({'internal_seconds': 3300, 'admission_cutoff_seconds': 3000}, time.monotonic())
        calls = []
        ledger = DurableLedger(plan, clock, calls.append)
        ledger.admit('canary')
        with self.assertRaises(RuntimeError):
            ledger.admit('canary')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['kind'], 'HTTP_admission')
        self.assertEqual(calls[0]['request_kind'], 'canary')

    def test_late_admission_record_does_not_send(self):
        clock = Clock({'internal_seconds': 3300, 'admission_cutoff_seconds': 3000}, 0, now=lambda: 2999)
        def slow_record(value):
            clock.now = lambda: 3000
        ledger = DurableLedger(request_plan([]), clock, slow_record)
        with self.assertRaises(TimeoutError):
            ledger.admit('canary')

    def test_trickled_http_response_has_absolute_deadline(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                received.append(True)
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200)
                self.send_header('Content-Length', '1000')
                self.end_headers()
                try:
                    for i in range(1000):
                        self.wfile.write(b'x')
                        self.wfile.flush()
                        time.sleep(0.01)
                except (OSError, ConnectionError):
                    pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            clock = Clock({'internal_seconds': 3300, 'admission_cutoff_seconds': 3000}, time.monotonic())
            plan = request_plan([])
            plan[0]['timeout_seconds'] = 0.08
            ledger = Ledger(plan, 1, clock)
            client = Client('127.0.0.1', server.server_port, ledger, clock, canary()['model'])
            begin = time.monotonic()
            with self.assertRaises(RequestFailed):
                client.call('canary', canary())
            self.assertLess(time.monotonic()-begin, 0.5)
            self.assertEqual(len(ledger.entries), 1)
            self.assertEqual(received, [True])
        finally:
            server.shutdown()
            server.server_close()

    def test_transport_replay_rejects_modified_prompt_and_usage(self):
        body = canary()
        events = [{'kind': 'HTTP_request', 'id': 'canary', 'body': body, 'native_prompt_tokens': 5},
                  {'kind': 'HTTP_admission', 'id': 'canary', 'sequence': 1, 'method': 'POST',
                   'path': '/v1/chat/completions', 'issued_at': 1, 'request_kind': 'canary'},
                  {'kind': 'HTTP_response', 'id': 'canary', 'status': 200, 'raw': json.dumps(reply(body))}]
        self.assertEqual(len(audit_transport(events, {'canary': body}, token_audit=lambda b: 5)[0]), 1)
        bad = deepcopy(events)
        bad[0]['body']['messages'][0]['content'] = 'Changed'
        with self.assertRaises(ValueError):
            audit_transport(bad, {'canary': body})
        with self.assertRaises(ValueError):
            audit_transport(events, {'canary': body}, token_audit=lambda b: 6)

    def test_driver_environment_retains_loader_but_no_credentials(self):
        env = environment({'LD_LIBRARY_PATH': '/usr/local/nvidia/lib64:/opt/lib', 'KAGGLE_API_TOKEN': 'secret'})
        self.assertEqual(env['LD_LIBRARY_PATH'], '/usr/local/nvidia/lib64:/opt/lib')
        self.assertNotIn('KAGGLE_API_TOKEN', env)
        self.assertEqual(env['MPLBACKEND'], 'Agg')

    def test_final_write_overrun_cannot_return(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            moment = [59.9]
            def late_write(path, value):
                write_new(path, value)
                moment[0] = 60.1
            with self.assertRaises(TimeoutError):
                finalize(output, {'started_monotonic': 0, 'error': None}, deadline=60,
                         now=lambda: moment[0], writer=late_write)
            self.assertFalse(json.loads((output/'provisional-result.json').read_bytes())['lifecycle_finalized'])
            self.assertFalse((output/'return-witness.json').exists())

    def test_interrupted_witness_and_return_marker_cannot_return(self):
        for stop in ('return-witness.json', 'marker'):
            with self.subTest(stop=stop), tempfile.TemporaryDirectory() as folder:
                def writer(path, value):
                    write_new(path, value)
                    if path.name == stop:
                        raise KeyboardInterrupt()
                def emit(*args, **kwargs):
                    if stop == 'marker':
                        raise KeyboardInterrupt()
                with self.assertRaises(KeyboardInterrupt):
                    finalize(Path(folder), {'started_monotonic': 0, 'error': None}, deadline=60,
                             now=lambda: 59, writer=writer, emit=emit)

    def test_actual_handled_interrupt_before_popen_assignment_is_owned(self):
        self._interrupt_spawn('Popen')

    def test_actual_handled_interrupt_before_group_registration_is_owned(self):
        self._interrupt_spawn('getpgid')

    def _interrupt_spawn(self, boundary):
        if sys.platform != 'linux':
            self.skipTest('requires real Linux process groups')
        watch, log = Watch(), None
        resources = Processes(watch)
        previous = signal.signal(signal.SIGINT, lambda s, f: (_ for _ in ()).throw(KeyboardInterrupt()))
        with tempfile.TemporaryDirectory() as folder:
            real = getattr(subprocess if boundary == 'Popen' else os, boundary)
            def interrupted(*args, **kwargs):
                result = real(*args, **kwargs)
                os.kill(os.getpid(), signal.SIGINT)
                return result
            try:
                target = 'certification.direct_publisher_smoke_v1.server.' + ('subprocess.Popen' if boundary == 'Popen' else 'os.getpgid')
                with patch(target, side_effect=interrupted), self.assertRaises(KeyboardInterrupt):
                    resources.spawn([sys.executable, '-c', 'import time; time.sleep(30)'], Path(folder)/'child.log',
                                    environment(), 'interrupt reproduction')
                self.assertEqual(len(watch.pids), 1)
                self.assertGreater(watch.pids[0], 0)
            finally:
                receipt = resources.stop(time.monotonic()+3)
                signal.signal(signal.SIGINT, previous)
            self.assertTrue(receipt['groups_absent'])
            self.assertEqual(watch.pids, [0])

    def test_uncertain_spawn_is_never_absent(self):
        resources = Processes(Watch())
        with tempfile.TemporaryDirectory() as folder:
            with patch('certification.direct_publisher_smoke_v1.server.subprocess.Popen', side_effect=KeyboardInterrupt()):
                with self.assertRaises(KeyboardInterrupt):
                    resources.spawn(['unused'], Path(folder)/'child.log', environment(), 'uncertain')
            self.assertFalse(resources.stop(time.monotonic()+2)['groups_absent'])

    def test_stalled_cleanup_cannot_swallow_hard_deadline(self):
        if sys.platform != 'linux':
            self.skipTest('requires Linux process watchdog')
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            script = folder/'watchdog_reproduction.py'
            script.write_text('''import os,sys,time
from pathlib import Path
from research.initial_geometry_assistance_v1.live_resources import HardDeadline,Processes,environment
if __name__ == '__main__':
    watchdog = HardDeadline(time.monotonic()+0.8)
    watchdog.start()
    resources = Processes(watchdog)
    child = resources.spawn([sys.executable,'-c','import time; time.sleep(30)'],Path(sys.argv[1])/'child.log',environment(),'child')
    (Path(sys.argv[1])/'pid').write_text(str(child['group'].pgid))
    child['group']._group_alive = lambda: time.sleep(20)
    resources.stop(time.monotonic()+0.1)
''')
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
            begin = time.monotonic()
            process = subprocess.Popen([sys.executable, str(script), str(folder)], env=env)
            try:
                self.assertEqual(process.wait(timeout=5), -signal.SIGKILL)
                self.assertLess(time.monotonic()-begin, 3)
                pid = int((folder/'pid').read_text())
                for i in range(20):
                    stat = Path('/proc')/str(pid)/'stat'
                    if not stat.exists() or stat.read_text().rsplit(')', 1)[1].split()[0] == 'Z':
                        break
                    time.sleep(0.05)
                else:
                    self.fail('watchdog left child running')
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                if (folder/'pid').exists():
                    try:
                        os.killpg(int((folder/'pid').read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass


if __name__ == '__main__':
    unittest.main()
