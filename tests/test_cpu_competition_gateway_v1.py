"""Scored worker integration against a controlled loopback HTTP gateway.

These are real requests/REST/SDK parsing checks, not hidden games. The server
serves synthetic 64x64 observations only. No provider, internet, model, real game
asset or new dependency is used. Gateway-generated parquet remains a separate
provider artifact; a successful worker summary does not establish its existence.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from agent.framework_adapter import RemoteFrameworkAdapter
from research.cpu_competition_v1.runtime import DeadlineSession, run
from tests.test_cpu_competition_v1 import program


GAME = 'zz99-12345678'
ROOT = Path(__file__).resolve().parents[1]


class Gateway:
    def __init__(self, *, unavailable_gets=0, lost_ack=None, rejected_post=None):
        self.unavailable_gets = unavailable_gets
        self.lost_ack = lost_ack
        self.rejected_post = rejected_post
        self.calls = []
        self.actions = 0

    def observation(self, action_index=0):
        grid = [[3] * 64 for _ in range(64)]
        grid[0][0] = action_index
        return dict(game_id=GAME, guid='synthetic-guid', frame=[grid],
                    state='GAME_OVER' if action_index >= 2 else 'NOT_FINISHED',
                    levels_completed=0, win_levels=7,
                    available_actions=[6] if action_index == 0 else [1])


@contextmanager
def server(gateway):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *_args):
            pass

        def response(self, status, value, *, cookie=None):
            body = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            if cookie is not None:
                self.send_header('Set-Cookie', cookie)
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()

        def do_GET(self):
            gateway.calls.append(dict(method='GET', path=self.path,
                                      headers=dict(self.headers), body=None))
            if self.path != '/api/games':
                return self.response(404, {'error': 'unknown synthetic route'})
            if gateway.unavailable_gets:
                gateway.unavailable_gets -= 1
                return self.response(503, {'error': 'synthetic startup pending'})
            self.response(200, [{'game_id': GAME}])

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            gateway.calls.append(dict(method='POST', path=self.path,
                                      headers=dict(self.headers), body=body))
            if self.path == gateway.lost_ack:
                # The request was accepted; its acknowledgement is deliberately lost.
                self.close_connection = True
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            if self.path == gateway.rejected_post:
                return self.response(503, {'error': 'synthetic post rejection'})
            if self.path == '/api/scorecard/open':
                return self.response(200, {'card_id': 'synthetic-card'},
                                     cookie='card_session=synthetic; Path=/')
            if self.path == '/api/cmd/RESET':
                return self.response(200, gateway.observation(),
                                     cookie='game_session=synthetic; Path=/')
            if self.path in ('/api/cmd/ACTION6', '/api/cmd/ACTION1'):
                gateway.actions += 1
                return self.response(200, gateway.observation(gateway.actions))
            if self.path == '/api/scorecard/close':
                return self.response(200, {'score': 0.0, 'source': 'synthetic'})
            self.response(404, {'error': 'unknown synthetic route'})

    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{httpd.server_port}'
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
        if thread.is_alive():
            raise RuntimeError('synthetic HTTP server did not stop')


@unittest.skipUnless(hasattr(signal, 'setitimer'), 'requires sequential POSIX HTTP deadline')
class GatewayIntegration(unittest.TestCase):
    def exercise(self, gateway, **kwargs):
        deadline = time.monotonic() + 10

        def session():
            value = DeadlineSession(deadline)
            value.trust_env = False  # Loopback cannot use a host HTTP proxy.
            return value

        with server(gateway) as base_url:
            adapter = RemoteFrameworkAdapter(base_url=base_url, api_key='synthetic-local-key',
                                             competition_mode=True, session_factory=session)
            try:
                result = run(adapter, program(), work_deadline=deadline,
                             max_actions=3, **kwargs)
            finally:
                adapter._master_session.close()
        return result

    def test_production_rest_contract_click_nonclick_cookies_and_close(self):
        gateway = Gateway()
        result = self.exercise(gateway)
        self.assertTrue(result['closed_verified'])
        self.assertEqual(result['actions_acknowledged'], 2)
        self.assertEqual([(c['method'], c['path']) for c in gateway.calls], [
            ('GET', '/api/games'), ('POST', '/api/scorecard/open'),
            ('POST', '/api/cmd/RESET'), ('POST', '/api/cmd/ACTION6'),
            ('POST', '/api/cmd/ACTION1'), ('POST', '/api/scorecard/close')])
        opened, reset, click, move, close = gateway.calls[1:]
        self.assertTrue(opened['body']['competition_mode'])
        self.assertEqual(reset['body'], {'card_id': 'synthetic-card', 'game_id': GAME})
        self.assertEqual(click['body'], {'game_id': GAME, 'guid': 'synthetic-guid', 'x': 0, 'y': 0})
        self.assertEqual(move['body'], {'game_id': GAME, 'guid': 'synthetic-guid'})
        self.assertEqual(close['body'], {'card_id': 'synthetic-card'})
        for call in gateway.calls:
            self.assertEqual(call['headers']['X-API-Key'], 'synthetic-local-key')
        self.assertIn('card_session=synthetic', reset['headers'].get('Cookie', ''))
        self.assertIn('game_session=synthetic', close['headers'].get('Cookie', ''))

    def test_readiness_retries_only_safe_get_before_any_post(self):
        gateway = Gateway(unavailable_gets=2)
        result = self.exercise(gateway, sleep=lambda _seconds: time.sleep(0.01))
        self.assertTrue(result['closed_verified'])
        self.assertEqual([c['method'] for c in gateway.calls[:3]], ['GET'] * 3)
        self.assertEqual(sum(c['path'] == '/api/scorecard/open' for c in gateway.calls), 1)
        self.assertEqual(result['actions_acknowledged'], 2)

    def test_lost_action_acknowledgement_quarantines_without_post_retry(self):
        gateway = Gateway(lost_ack='/api/cmd/ACTION6')
        result = self.exercise(gateway)
        self.assertEqual(result['ambiguous_actions'], 1)
        self.assertEqual(result['actions_admitted'], 1)
        self.assertEqual(result['actions_acknowledged'], 0)
        self.assertEqual(sum(c['path'] == '/api/cmd/ACTION6' for c in gateway.calls), 1)
        self.assertFalse(any(c['path'] == '/api/cmd/ACTION1' for c in gateway.calls))
        self.assertEqual(gateway.calls[-1]['path'], '/api/scorecard/close')
        self.assertTrue(result['closed_verified'])

    def test_post_503_is_not_treated_as_readiness_or_retried(self):
        gateway = Gateway(rejected_post='/api/scorecard/open')
        result = self.exercise(gateway)
        self.assertFalse(result['closed_verified'])
        self.assertEqual(result['error_type'], 'OutcomeUnknown')
        self.assertEqual([(c['method'], c['path']) for c in gateway.calls],
                         [('GET', '/api/games'), ('POST', '/api/scorecard/open')])

    def test_exact_scored_cli_subprocess_imports_from_frozen_root(self):
        # Execute the real runtime.py main guard. Only the destination is changed
        # to this test's loopback gateway; request/session/parser/runtime stay real.
        bootstrap = '''import runpy,sys
import agent.framework_adapter as framework
original=framework.RemoteFrameworkAdapter
endpoint=sys.argv.pop(1)
script=sys.argv.pop(1)
def local_adapter(*args,**kwargs):
    kwargs['base_url']=endpoint
    return original(*args,**kwargs)
framework.RemoteFrameworkAdapter=local_adapter
sys.argv[0]=script
runpy.run_path(script,run_name='__main__')
'''
        gateway = Gateway()
        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONNOUSERSITE='1',
                   PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg',
                   CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void',
                   KAGGLE_IS_COMPETITION_RERUN='1', NO_PROXY='127.0.0.1,localhost')
        for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
            env.pop(name, None)
        with tempfile.TemporaryDirectory() as directory:
            with server(gateway) as base_url:
                result = subprocess.run([sys.executable, '-B', '-c', bootstrap, base_url,
                    str(ROOT / 'research/cpu_competition_v1/runtime.py'),
                    '--program', str(ROOT / 'research/ls20_overfit_v1/policy_seed0.json'),
                    '--work-seconds', '10', '--final-seconds', '15'],
                    cwd=directory, env=env, capture_output=True, text=True, timeout=25)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            records = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
            summary = next(row for row in reversed(records) if 'closed_verified' in row)
            self.assertTrue(summary['closed_verified'])
            self.assertEqual(summary['actions_acknowledged'], 2)
            # A fake score response is not a submission file. Only the gateway
            # owns that artifact; notebook finalization must separately require it.
            self.assertFalse((Path(directory) / 'submission.parquet').exists())
            self.assertNotIn('submission_created', summary)
        self.assertEqual(sum(c['path'] == '/api/scorecard/close' for c in gateway.calls), 1)


if __name__ == '__main__':
    unittest.main()
