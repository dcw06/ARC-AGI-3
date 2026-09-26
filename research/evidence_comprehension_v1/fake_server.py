"""CPU rehearsal stand-in for vLLM's OpenAI-compatible server (never used in live mode; not target evidence).

It serves the endpoints the live path uses (`/v1/models`, `/v1/chat/completions`, `/metrics`) with
vLLM 0.19.0's metric names, so rehearsals exercise the real HTTP transport, total-deadline
cancellation and metrics verification. A running request watches its socket and aborts on client
disconnect, as vLLM's `with_cancellation` does, unless the `no_abort` fault is set.

Answers are scripted from the frozen keys: mostly correct, with deterministic wrong, invalid and
pass-2-divergent answers so scoring, agreement and invalid-pair handling are exercised.
"""
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import select
import socket
import threading
import time

FAULTS = ('none', 'prefix_cache_enabled', 'hang_once', 'no_abort', 'http_error')
HANG_AT = 7  # the questionnaire call (1-based, after the canary) that hangs or fails under a fault
STUCK_SECONDS = 600


def count_tokens(messages):
    """Must equal the rehearsal fixture tokenizer (research.action_effect_history_v1.rehearsal.count)."""
    return max(1, len(json.dumps(messages, sort_keys=True, separators=(',', ':'))) // 4)


def request_sha(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()


class ScriptedAnswers:
    """Maps each frozen request to its probe; answers by a fixed rule (rehearsal only)."""

    def __init__(self):
        from research.evidence_comprehension_v1.probes import build_request, load_frozen
        frozen, _ = load_frozen()
        contexts = {c['context_id']: c for c in frozen['contexts']}
        self.by_sha = {request_sha(build_request(contexts[p['context_id']], p)): p for p in frozen['probes']}
        self.seen = {}

    def __call__(self, request):
        user = request['messages'][1]['content']
        if not user.startswith('{'):  # the startup canary
            return json.dumps({'action': {'action_id': 6, 'action_data': {'x': 5, 'y': 5}}})
        probe = self.by_sha.get(request_sha(request))
        if probe is None:
            return '{"answer":"not_in_probe_set"}'
        occurrence = self.seen[probe['probe_id']] = self.seen.get(probe['probe_id'], 0) + 1
        bucket = int(hashlib.sha256(probe['probe_id'].encode()).hexdigest(), 16) % 100
        if bucket < 3:
            return 'not json'
        wrong = bucket < 9 or (occurrence == 2 and bucket < 12)
        return json.dumps({'answer': self.wrong(probe) if wrong else probe['key']})

    @staticmethod
    def wrong(probe):
        family, key = probe['family'], probe['key']
        if family in ('available_actions', 'coordinate_actions'):
            return sorted(set(key) ^ {7})
        if family == 'tried_unchanged':
            return key[1:] if key else [{'action_id': 1, 'action_data': {}}]
        if family == 'recall_action':
            return 'not_shown' if key != 'not_shown' else {'action_id': 1, 'action_data': {}}
        return 'dispatch_failed' if key != 'dispatch_failed' else 'outcome_unknown'


class FakeVLLM:
    def __init__(self, *, fault='none', latency_seconds=0.0, answers=None):
        if fault not in FAULTS:
            raise ValueError('fake server fault')
        self.fault, self.latency = fault, latency_seconds
        self.answers = answers or ScriptedAnswers()
        self.lock = threading.Lock()
        self.running = self.waiting = 0
        self.counters = {'prompt_tokens': 0, 'generation_tokens': 0, 'prefix_queries': 0, 'prefix_hits': 0,
                         'success_stop': 0, 'success_length': 0, 'success_abort': 0}
        self.completions = 0
        self.log = []  # (event, detail) for rehearsal assertions
        fake = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *_):
                pass

            def reply(self, status, raw, kind='application/json'):
                self.send_response(status)
                self.send_header('Content-Type', kind)
                self.send_header('Content-Length', str(len(raw)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                if self.path == '/v1/models':
                    return self.reply(200, b'{"data":[{"id":"rehearsal"}]}')
                if self.path == '/metrics':
                    return self.reply(200, fake.metrics().encode(), 'text/plain')
                self.reply(404, b'{}')

            def do_POST(self):
                if self.path != '/v1/chat/completions':
                    return self.reply(404, b'{}')
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fake.handle(self, request)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.base_url = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def metrics(self):
        c = self.counters
        with self.lock:
            lines = [
                '# HELP vllm:num_requests_running Number of requests in model execution batches.',
                f'vllm:num_requests_running{{engine="0",model_name="rehearsal"}} {self.running}',
                f'vllm:num_requests_waiting{{engine="0",model_name="rehearsal"}} {self.waiting}',
                f'vllm:prompt_tokens_total{{engine="0",model_name="rehearsal"}} {c["prompt_tokens"]}',
                f'vllm:generation_tokens_total{{engine="0",model_name="rehearsal"}} {c["generation_tokens"]}',
                f'vllm:prefix_cache_queries_total{{engine="0",model_name="rehearsal"}} {c["prefix_queries"]}',
                f'vllm:prefix_cache_hits_total{{engine="0",model_name="rehearsal"}} {c["prefix_hits"]}',
                f'vllm:request_success_total{{engine="0",finished_reason="stop",model_name="rehearsal"}} {c["success_stop"]}',
                f'vllm:request_success_total{{engine="0",finished_reason="length",model_name="rehearsal"}} {c["success_length"]}',
                f'vllm:request_success_total{{engine="0",finished_reason="abort",model_name="rehearsal"}} {c["success_abort"]}',
            ]
        return '\n'.join(lines) + '\n'

    @staticmethod
    def disconnected(connection):
        readable, _, _ = select.select([connection], [], [], 0)
        if not readable:
            return False
        try:
            return connection.recv(1, socket.MSG_PEEK) == b''
        except OSError:
            return True

    def handle(self, handler, request):
        is_canary = not request['messages'][1]['content'].startswith('{')
        with self.lock:
            if not is_canary:
                self.completions += 1
            number = self.completions
            self.running += 1
        tokens = count_tokens(request['messages'])
        hang = not is_canary and number == HANG_AT and self.fault in ('hang_once', 'no_abort')
        if not is_canary and number == HANG_AT and self.fault == 'http_error':
            with self.lock:
                self.running -= 1
            return handler.reply(500, b'{"error":"rehearsal server failure"}')
        until = time.monotonic() + (STUCK_SECONDS if hang else self.latency)
        while time.monotonic() < until:
            if self.disconnected(handler.connection):
                if self.fault == 'no_abort' and hang:
                    self.log.append(('disconnect_ignored', number))
                    time.sleep(STUCK_SECONDS)  # keeps counting as running: cancellation did not reach the engine
                    return
                with self.lock:
                    self.running -= 1
                    self.counters['success_abort'] += 1
                self.log.append(('aborted', number))
                return
            time.sleep(0.01)
        content = self.answers(request)
        completion = max(1, len(content) // 4)
        with self.lock:
            self.running -= 1
            self.counters['prompt_tokens'] += tokens
            self.counters['generation_tokens'] += completion
            self.counters['success_stop'] += 1
            if self.fault == 'prefix_cache_enabled':
                self.counters['prefix_queries'] += tokens
        body = {'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': content}}],
                'usage': {'prompt_tokens': tokens, 'completion_tokens': completion}}
        try:
            handler.reply(200, json.dumps(body).encode())
        except OSError:
            pass
