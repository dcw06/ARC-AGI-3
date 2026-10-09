"""SCRIPTED CPU STUB for the Track 2 successor rehearsals only: never live, loads no model, touches no GPU.

One server process for everything the verified lifecycle and the study phase send:
- the verified stub's /health, /v1/models, startup and inference answers and streamed cancellation probe
  (certification/direct_publisher_smoke_v1/rehearsal_stub.py, reused unchanged by subclassing);
- for the frozen Stage 1 requests of one session, the Track 2 rehearsal's scripted answers (ScriptedAnswers from
  research/evidence_memory_v1/run/fake_server.py, over that session's frozen set): mostly the key, with deterministic
  invalid, truncated, wrong and repeat-divergent answers;
- vLLM 0.19's metric names on /metrics: running/waiting gauges, prompt-token and prefix-cache counters and aborts.
  A study request watches its socket and aborts on client disconnect, as vLLM's `with_cancellation` does.
Prompt tokens of study requests are the session token audit's pinned-tokenizer counts, so token parity is exercised
exactly as in a live run. Every fault below is rehearsal-only and keyed to study call HANG_AT where it applies.
"""
import argparse
import hashlib
import json
from pathlib import Path
import select
import socket
import sys
import threading
import time
from http.server import ThreadingHTTPServer

# none: the scripted buckets; clean_answers: every answer the key (full-history truth); package_reader: an exact
# reader of the package (protocol.oracle_read's answer from the probe's package-relative truth), so the pooled analysis
# reproduces the availability ceilings of protocol v2 section 8; the rest inject one failure (clean answers otherwise).
FAULTS = ('none', 'clean_answers', 'package_reader', 'invalid_repeat', 'hang_once', 'no_abort', 'http_error',
          'token_mismatch', 'prefix_cache_enabled', 'prefix_cache_late', 'slow')
HANG_AT = 7  # the study call (1-based) that hangs or fails under a fault, as in the reviewed fake server
STUCK_SECONDS = 600
STATE = {'lock': threading.Lock(), 'study_calls': 0, 'running': 0, 'prompt_tokens': 0, 'generation_tokens': 0,
         'prefix_queries': 0, 'aborted': 0}


def load_session(root, package):
    from research.evidence_memory_v1.run import fake_server as T2
    from research.evidence_memory_v1.run.probes import build_request
    folder = Path(root) / package
    frozen = json.loads((folder / 'probes.json').read_bytes())
    audit = json.loads((folder / 'token-audit.json').read_bytes())
    counts = {row['request_sha256']: row['prompt_tokens'] for row in audit['requests']}

    class SessionAnswers(T2.ScriptedAnswers):
        def __init__(self):  # the reviewed answers over this session's frozen set (not run/probes.json)
            contexts = {c['context_id']: c for c in frozen['contexts']}
            self.by_sha = {T2.request_sha(build_request(contexts[p['context_id']], p)): p for p in frozen['probes']}
            self.pass_1_calls = len(frozen['schedule'][0]['probe_ids'])
            self.seen = {}
            self.clean = False
    return SessionAnswers(), counts, T2.TRUNCATED, T2.request_sha


def disconnected(connection):
    readable, _, _ = select.select([connection], [], [], 0)
    if not readable:
        return False
    try:
        return connection.recv(1, socket.MSG_PEEK) == b''
    except OSError:
        return True


def make_handler(base, answers, counts, truncated, request_sha, fault, latency):
    answers.clean = fault != 'none'  # every other fault is isolated from the scripted answer buckets

    def counted(prompt):
        with STATE['lock']:
            STATE['prompt_tokens'] += prompt
            if fault == 'prefix_cache_enabled' or (fault == 'prefix_cache_late' and STATE['study_calls'] >= HANG_AT):
                STATE['prefix_queries'] += prompt

    class Handler(base.Handler):
        def _send(self, status, payload, content_type='application/json'):
            try:
                super()._send(status, payload, content_type)
            except (BrokenPipeError, ConnectionResetError):
                pass  # the client already cancelled

        def do_GET(self):
            if self.path != '/metrics':
                return super().do_GET()
            with STATE['lock'], base.STATE['lock']:
                running = STATE['running'] + base.STATE['running']
                values = dict(STATE)
            labels = f'engine="0",model_name="{self.served}"'
            text = ''.join(f'{name}{{{labels}}} {value}\n' for name, value in (
                ('vllm:num_requests_running', running), ('vllm:num_requests_waiting', 0),
                ('vllm:prompt_tokens_total', values['prompt_tokens']),
                ('vllm:generation_tokens_total', values['generation_tokens']),
                ('vllm:prefix_cache_queries_total', values['prefix_queries']),
                ('vllm:prefix_cache_hits_total', 0)))
            text += (f'vllm:request_success_total{{engine="0",finished_reason="abort",model_name="{self.served}"}} '
                     f"{values['aborted']}\n")
            self._send(200, ('# scripted stub metrics\n' + text).encode(), 'text/plain')

        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}'
            body = json.loads(raw)
            if self.path != '/v1/chat/completions':
                return self._send(404, {'error': 'not found'})
            if body.get('stream'):
                counted(10 + len(raw) // 4)
                return self._stream(body)
            if request_sha(body) not in answers.by_sha:
                counted(10 + len(raw) // 4)  # startup canary, inference and cancellation probes
                return self._send(200, {'model': self.served, 'choices': [{'index': 0, 'message': {
                    'role': 'assistant', 'content': base.answer(body)}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 10 + len(raw) // 4, 'completion_tokens': 1}})
            self.study(body)

        def study(self, body):
            sha = request_sha(body)
            with STATE['lock']:
                STATE['study_calls'] += 1
                number = STATE['study_calls']
                STATE['running'] += 1
            hang = number == HANG_AT and fault in ('hang_once', 'no_abort')
            if fault == 'http_error' and number == HANG_AT:
                with STATE['lock']:
                    STATE['running'] -= 1
                return self._send(500, {'error': 'rehearsal server failure'})
            until = time.monotonic() + (STUCK_SECONDS if hang else latency if fault == 'slow' else 0.0)
            while time.monotonic() < until:
                if disconnected(self.connection):
                    if fault == 'no_abort' and hang:
                        time.sleep(STUCK_SECONDS)  # still running: the cancellation never reached the engine
                        return
                    with STATE['lock']:
                        STATE['running'] -= 1
                        STATE['aborted'] += 1
                    return
                time.sleep(0.005)
            probe = answers.by_sha[sha]
            content = answers(body)
            if fault == 'package_reader':
                package = probe['package']
                content = json.dumps({'values': package} if probe['kind'] == 'recall' else
                                     {'choice': package[0] if package else probe['question']['candidates'][0]})
            if fault == 'invalid_repeat' and number > answers.pass_1_calls and int(
                    hashlib.sha256(probe['probe_id'].encode()).hexdigest(), 16) % 100 < 10:
                content = 'not json'  # only repeat-pass calls (after every pass-1 call): pass 1 stays clean
            finish, completion = 'stop', max(1, len(content) // 4)
            if content.startswith(truncated):
                content, finish, completion = content[len(truncated):], 'length', body['max_tokens']
            prompt = counts[sha] + (1 if fault == 'token_mismatch' and number == HANG_AT else 0)
            counted(prompt)
            with STATE['lock']:
                STATE['running'] -= 1
                STATE['generation_tokens'] += completion
            self._send(200, {'model': self.served, 'choices': [{'index': 0, 'message': {
                'role': 'assistant', 'content': content}, 'finish_reason': finish}],
                'usage': {'prompt_tokens': prompt, 'completion_tokens': completion}})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--served', required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--package', required=True)
    parser.add_argument('--fault', choices=FAULTS, default='none')
    parser.add_argument('--latency', type=float, default=0.0)
    args = parser.parse_args()
    sys.path.insert(0, str(args.root))
    from certification.direct_publisher_smoke_v1 import rehearsal_stub as base
    answers, counts, truncated, request_sha = load_session(args.root, args.package)
    print(f'SCRIPTED CPU STUB: no model, no GPU; fault={args.fault}; enable_prefix_caching=False', flush=True)
    handler = make_handler(base, answers, counts, truncated, request_sha, args.fault, args.latency)
    handler.served, handler.behaviour = args.served, 'normal'
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer(('127.0.0.1', args.port), handler).serve_forever()


if __name__ == '__main__':
    main()
