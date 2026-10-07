"""SCRIPTED STUB for CPU rehearsals only: a stdlib HTTP server imitating the vLLM OpenAI endpoints the smoke test
uses. It loads no model and touches no GPU; every response is scripted. Behaviours exercise the failure paths."""
import argparse
import json
import os
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BEHAVIOURS = ('normal', 'never_ready', 'exit_early', 'slow_completion', 'stay_busy', 'ignore_sigterm',
              'child_ignores_sigterm', 'wrong_model')
STATE = {'running': 0, 'lock': threading.Lock(), 'aborted': 0}


def answer(body):
    text = json.dumps(body.get('messages', []))
    if 'image_url' in text:
        return 'Red'
    if 'How many numbered lines' in text:
        return '120'
    if 'single word: ok' in text:
        return 'ok'
    return 'READY'


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    behaviour = 'normal'
    served = 'stub'

    def log_message(self, fmt, *args):
        print('stub:', fmt % args, flush=True)

    def _send(self, status, payload, content_type='application/json'):
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/health':
            self._send(200, b'', 'text/plain')
        elif self.path == '/v1/models':
            name = 'some-other-model' if self.behaviour == 'wrong_model' else self.served
            self._send(200, {'object': 'list', 'data': [{'id': name, 'object': 'model'}]})
        elif self.path == '/metrics':
            running = STATE['running'] + (1 if self.behaviour == 'stay_busy' else 0)
            text = (f'# scripted stub metrics\nvllm:num_requests_running{{model_name="{self.served}"}} {running}.0\n'
                    f'vllm:num_requests_waiting{{model_name="{self.served}"}} 0.0\n')
            self._send(200, text.encode(), 'text/plain')
        else:
            self._send(404, {'error': 'not found'})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        if self.path != '/v1/chat/completions':
            return self._send(404, {'error': 'not found'})
        if self.behaviour == 'slow_completion':
            time.sleep(3600)
        if body.get('stream'):
            return self._stream(body)
        content = answer(body)
        self._send(200, {'model': self.served, 'choices': [{'index': 0, 'message': {'role': 'assistant',
                   'content': content}, 'finish_reason': 'stop'}],
                   'usage': {'prompt_tokens': 10 + len(json.dumps(body)) // 4, 'completion_tokens': 1}})

    def _stream(self, body):
        with STATE['lock']:
            STATE['running'] += 1
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            for i in range(1, body.get('max_tokens', 16) + 1):
                chunk = {'model': self.served, 'choices': [{'index': 0, 'delta': {'content': f'{i} '}}]}
                self.wfile.write(f'data: {json.dumps(chunk)}\n\n'.encode())
                self.wfile.flush()
                time.sleep(0.05)
            self.wfile.write(b'data: [DONE]\n\n')
        except (BrokenPipeError, ConnectionResetError):
            STATE['aborted'] += 1  # the client cancelled: stop generating, as vLLM aborts the request
        finally:
            with STATE['lock']:
                STATE['running'] -= 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--served', required=True)
    parser.add_argument('--behaviour', choices=BEHAVIOURS, default='normal')
    parser.add_argument('--startup-delay', type=float, default=0.5)
    args = parser.parse_args()
    print(f'SCRIPTED STUB (no model, no GPU) behaviour={args.behaviour}', flush=True)
    if args.behaviour == 'exit_early':
        raise SystemExit(3)
    if args.behaviour in ('ignore_sigterm', 'child_ignores_sigterm'):
        if args.behaviour == 'child_ignores_sigterm' and os.fork() == 0:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            time.sleep(3600)
            os._exit(0)
        signal.signal(signal.SIGTERM, signal.SIG_IGN if args.behaviour == 'ignore_sigterm' else signal.SIG_DFL)
    if args.behaviour == 'never_ready':
        time.sleep(3600)
    time.sleep(args.startup_delay)
    Handler.behaviour, Handler.served = args.behaviour, args.served
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
