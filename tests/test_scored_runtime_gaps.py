"""CPU-only regressions for the four ab202f3 review findings.

The four reproduction methods also run on ab202f3 (legacy process fallback).
Never authenticate, submit, call a model or access GPU devices.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import requests

from agent.action import ActionDecision
from agent.action_journal import TransactionStatus
from agent.competition_loop import CompetitionAgentLoop
from agent.framework_adapter import PreDispatchFailure, RemoteFrameworkAdapter
from agent.scored_worker import CountedClient
from agent.watchdog import DeadlineWatchdog
from tests.test_phase0 import FakeSession

ROOT = Path(__file__).resolve().parents[1]


class RuntimeGaps(unittest.TestCase):
    def test_clean_preinstall_notebook_refuses_at_approval(self):
        from scripts.build_scored_submission_v1 import build
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            build(folder/'draft', json.loads((ROOT/'notebooks/scored-baseline-one-hour-review/'
                                              'private-bindings.example.json').read_bytes()))
            cell = json.loads((folder/'draft/submission.ipynb').read_bytes())['cells'][1]['source']
            runner = folder/'bootstrap.py'
            runner.write_text(cell, encoding='utf-8')
            result = subprocess.run([sys.executable, '-I', '-S', str(runner)], capture_output=True,
                                    text=True, timeout=30, env={**os.environ,
                                    'KAGGLE_IS_COMPETITION_RERUN':'1', 'TMPDIR':tmp, 'TEMP':tmp, 'TMP':tmp})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('PermissionError: the exact scored package has not been approved', result.stderr)
            self.assertNotIn('ModuleNotFoundError', result.stderr)
            self.assertFalse(list(folder.glob('arc3-scored-source-*')))

    @unittest.skipUnless(sys.platform == 'linux', 'process-group fault injection requires Linux')
    def test_stalled_census_cannot_delay_sigkill(self):
        from research.stagnation_supervision_runtime_v2 import procfs, publisher_process
        try:
            from agent.scored_process import ModelServer
        except ModuleNotFoundError:  # the same reproduction on the unfixed commit
            ModelServer = publisher_process.ModelServer
        with tempfile.TemporaryDirectory() as tmp:
            ready = Path(tmp)/'ready'
            child = ModelServer([sys.executable, '-c',
                'import signal,time,pathlib,sys; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                'pathlib.Path(sys.argv[1]).touch(); time.sleep(30)', str(ready)], {}, Path(tmp)/'child.log', None, None)
            child.start()
            release = threading.Event()
            def stall(*args, **kwargs):
                release.wait(1.5)
                return []
            try:
                until = time.monotonic()+5
                while not ready.exists() and time.monotonic() < until:
                    time.sleep(.01)
                self.assertTrue(ready.exists())
                began = time.monotonic()
                with patch.object(publisher_process, 'group_members', side_effect=stall), \
                        patch.object(procfs.os, 'listdir', side_effect=stall):
                    receipt = child.stop(began+.2, .1, .1)
                elapsed = time.monotonic()-began
                self.assertLess(elapsed, .8, receipt)
                self.assertTrue(receipt['sigkill_sent'])
                self.assertFalse(receipt['groups_absent'])  # stalled verification is never absence
                self.assertIsNotNone(receipt['error'])
                child.process.wait(timeout=2)
            finally:
                release.set()
                try:
                    os.killpg(child.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.process.wait(timeout=2)
                child._log.close()

    def test_dripping_response_has_absolute_deadline(self):
        # Model a peer delivering bytes before each socket inactivity timeout.
        # requests' eager .post/.json blocks; the bounded streamed caller must not.
        released = threading.Event()
        response = SimpleNamespace(is_redirect=False, raise_for_status=lambda:None, close=lambda:None)
        def chunks(chunk_size):
            for _ in range(30):
                if released.wait(.02):
                    break
                yield b' '
            yield json.dumps({'choices':[{'message':{'content':'OK'}}],
                             'usage':{'prompt_tokens':1,'completion_tokens':1}}).encode()
        response.iter_content = chunks
        def eager_json():
            list(chunks(1))
            return {'choices':[{'message':{'content':'OK'}}]}
        response.json = eager_json
        class Session:
            calls = 0
            def post(self, *args, **kwargs):
                self.calls += 1
                if not kwargs.get('stream'):
                    list(chunks(1))
                return response
        session = Session()
        client = CountedClient(session=session, timeout_seconds=.1)
        CountedClient.entered, CountedClient.deadline = 0, time.monotonic()+5
        began = time.monotonic()
        try:
            with self.assertRaises((requests.Timeout, TimeoutError)):
                client.complete({'max_tokens':128})
            self.assertLess(time.monotonic()-began, .4)
            self.assertEqual(session.calls, 1)
            self.assertEqual(CountedClient.entered, 1)
            with self.assertRaises(TimeoutError):
                client.complete({'max_tokens':128})
            self.assertEqual(session.calls, 1)
            self.assertEqual(CountedClient.entered, 1)
        finally:
            released.set()

    def test_policy_return_after_cutoff_dispatches_zero_actions(self):
        self._late_policy(False)

    def test_real_http_drip_is_bounded_and_normal_response_works(self):
        from agent.scored_transport import bounded_json_post
        release = threading.Event()
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                calls.append(self.path)
                self.rfile.read(int(self.headers['Content-Length']))
                body = b'{"choices":[{"message":{"content":"OK"}}]}'
                self.send_response(200)
                self.send_header('Content-Length',str(len(body)+(30 if self.path == '/drip' else 0)))
                self.end_headers()
                try:
                    if self.path == '/drip':
                        for _ in range(30):
                            self.wfile.write(b' ')
                            self.wfile.flush()
                            if release.wait(.02):
                                break
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        with requests.Session() as session:
            try:
                base = f'http://127.0.0.1:{server.server_port}'
                value = bounded_json_post(session,base+'/ok',{},deadline=time.monotonic()+2)
                self.assertEqual(value['choices'][0]['message']['content'],'OK')
                began = time.monotonic()
                with self.assertRaises(requests.Timeout):
                    bounded_json_post(session,base+'/drip',{},deadline=began+.12)
                self.assertLess(time.monotonic()-began,.4)
                self.assertEqual(calls,['/ok','/drip'])
            finally:
                release.set()
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_fallback_after_cutoff_dispatches_zero_actions(self):
        self._late_policy(True)

    def _late_policy(self, fail):
        adapter = RemoteFrameworkAdapter(base_url='http://local', api_key='none', session_factory=FakeSession)
        adapter.open_scorecard()
        client = adapter.bootstrap('zz99-version')
        watchdog = DeadlineWatchdog(60, 10)
        class Policy:
            def propose(self, state):
                watchdog.cancel()
                if fail:
                    raise ValueError('late invalid proposal')
                return ActionDecision.simple(1)
        result = CompetitionAgentLoop(adapter, client, policy=Policy(), max_actions=1, watchdog=watchdog).run()
        self.assertEqual(result.acknowledged_actions, 0)
        self.assertEqual(client.action_requests, 0)
        self.assertEqual(result.terminal_reason, 'global_finalization_reserve')
        adapter.close_scorecard()

    def test_boundary_refuses_without_counting_or_quarantining(self):
        allowed = True
        adapter = RemoteFrameworkAdapter(base_url='http://local', api_key='none', session_factory=FakeSession,
                                         action_admission=lambda:allowed)
        adapter.open_scorecard()
        client = adapter.bootstrap('zz99-version')
        allowed = False
        with self.assertRaises(PreDispatchFailure):
            adapter.dispatch(client, ActionDecision.simple(1))
        self.assertEqual(client.action_requests, 0)
        self.assertFalse(client.quarantined)
        self.assertEqual(client.journal.snapshot()[-1].status, TransactionStatus.FAILED_PRE_DISPATCH)
        self.assertEqual(len(client.session.calls), 1)  # bootstrap only
        adapter.close_scorecard()  # finalization is not an action admission

    @unittest.skipUnless(sys.platform == 'linux', 'process ownership requires Linux')
    def test_installation_uses_bounded_owner_and_restores_factory(self):
        from agent.scored_process import ModelServer, bounded_installation_processes
        from research.stagnation_supervision_runtime_v2 import publisher_install
        original = publisher_install.ModelServer
        with tempfile.TemporaryDirectory() as tmp:
            owner = publisher_install.InstallationProcesses(.1,.1)
            try:
                with bounded_installation_processes():
                    owner.command([sys.executable,'-c','pass'], Path(tmp)/'install.log',
                                  time.monotonic()+3, dict(os.environ), 'cpu check')
                    self.assertIsInstance(owner.groups[0]['group'], ModelServer)
                    raise KeyboardInterrupt()
            except KeyboardInterrupt:
                pass
            finally:
                receipt = owner.stop(time.monotonic()+1)
            self.assertTrue(receipt['groups_absent'], receipt)
        self.assertIs(publisher_install.ModelServer, original)

    def test_uncertain_startup_never_certifies_absence(self):
        from agent.scored_process import ModelServer
        with tempfile.TemporaryDirectory() as tmp:
            child = ModelServer([],{},Path(tmp)/'log',None,None)
            child.ownership = 'uncertain'
            receipt = child.stop(time.monotonic()+1,.1,.1)
            self.assertFalse(receipt['groups_absent'])

    @unittest.skipUnless(sys.platform == 'linux', 'handled alarm requires Linux')
    def test_handled_alarm_cannot_skip_emergency_kill(self):
        from agent.scored_process import ModelServer
        with tempfile.TemporaryDirectory() as tmp:
            ready = Path(tmp)/'ready'
            child = ModelServer([sys.executable,'-c',
                'import signal,time,pathlib,sys; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                'pathlib.Path(sys.argv[1]).touch(); time.sleep(30)',str(ready)],{},Path(tmp)/'log',None,None)
            child.start()
            old = signal.getsignal(signal.SIGALRM)
            def interrupt(*args):
                raise TimeoutError('injected handled alarm')
            try:
                until = time.monotonic()+5
                while not ready.exists() and time.monotonic() < until:
                    time.sleep(.01)
                self.assertTrue(ready.exists())
                signal.signal(signal.SIGALRM,interrupt)
                signal.setitimer(signal.ITIMER_REAL,.01)
                receipt = child.stop(time.monotonic()+1,.08,.1)
                self.assertTrue(receipt['sigkill_sent'],receipt)
                child.process.wait(timeout=1)
                self.assertFalse(receipt['groups_absent'])
                self.assertTrue(receipt['interrupted'])
                self.assertFalse(child.stop(time.monotonic()+1,.08,.1)['groups_absent'])
            finally:
                signal.setitimer(signal.ITIMER_REAL,0)
                signal.signal(signal.SIGALRM,old)
                try:
                    os.killpg(child.process.pid,signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.process.wait(timeout=1)


if __name__ == '__main__':
    unittest.main()
