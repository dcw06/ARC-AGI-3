"""Real local HTTP server proves redirects/status errors/disconnects never retry."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch
import hashlib
from scripts.kaggle_stagnation_supervision_v1_r6_no_retry import OneShotSession, KaggleNoRetry


class Adapter(unittest.TestCase):
    def test_http_failure_success_redirect_and_disconnect_are_single_attempt(self):
        for status in (200,302,429,503,'disconnect'):
            with self.subTest(status=status),tempfile.TemporaryDirectory() as tmp:
                calls=[]
                class Handler(BaseHTTPRequestHandler):
                    def log_message(self,*args):pass
                    def do_POST(self):
                        calls.append(self.path)
                        self.rfile.read(int(self.headers.get('Content-Length','0')))
                        if status=='disconnect':
                            self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
                        self.send_response(status)
                        self.send_header('Location','/should-never-be-followed')
                        self.send_header('Retry-After','0');self.end_headers()
                        self.wfile.write(json.dumps({'url':'https://www.kaggle.com/code/test/not-a-run'}).encode())
                    do_GET=do_POST
                server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                ledger=Path(tmp);(ledger/'submission-claim.json').write_text('{}')
                session=OneShotSession();body=b'{"synthetic":true}'
                adapter=KaggleNoRetry(session,ledger,hashlib.sha256(body).hexdigest())
                try:
                    with patch('scripts.kaggle_stagnation_supervision_v1_r6_no_retry.URL',f'http://127.0.0.1:{server.server_port}/save'),patch('scripts.kaggle_stagnation_supervision_v1_r6_no_retry.request_body',return_value=body):
                        if status==200:adapter(ledger)
                        else:
                            with self.assertRaises(Exception):adapter(ledger)
                        with self.assertRaises(PermissionError):session.post(f'http://127.0.0.1:{server.server_port}/save')
                    self.assertEqual(calls,['/save'])
                    if status!='disconnect':self.assertTrue((ledger/'provider-response.json').is_file())
                    for scheme in ('http://','https://'):
                        self.assertEqual(session.adapters[scheme].max_retries.total,0)
                finally:server.shutdown();server.server_close();thread.join()

    def test_no_claim_or_request_drift_never_sends(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Path(tmp);s=OneShotSession();adapter=KaggleNoRetry(s,ledger,'0'*64)
            with self.assertRaises(PermissionError):adapter(ledger)
            (ledger/'submission-claim.json').write_text('{}')
            with patch('scripts.kaggle_stagnation_supervision_v1_r6_no_retry.request_body',return_value=b'wrong'):
                with self.assertRaises(ValueError):adapter(ledger)
            self.assertFalse(s.used)
