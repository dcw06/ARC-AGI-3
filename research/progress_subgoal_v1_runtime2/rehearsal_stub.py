# Derived from research/control_interface_action_selection_v2/rehearsal_stub.py (5a21dd3) by scripts/build_progress_subgoal_v1_runtime2.py; edit the derivation.
"""Local HTTP fixture, not a model. Exercises the complete bounded controller on CPU.

Questionnaire requests (strict json_schema response format) get scripted answers: `scripted` applies the reviewed
rehearsal rule of research.progress_subgoal_v1.fake_server.ScriptedAnswers (mostly correct; deterministic wrong,
invalid, truncated and pass-2-divergent answers), `oracle` answers every key. Prompt-token usage is the frozen offline
token audit's count for that request, so the controller's parity check is exercised. Faults act on questionnaire
call FAULT_AT (0-based) and, for consecutive timeouts, the call after it."""
import argparse
import json
from pathlib import Path
import threading
import time
from http.server import ThreadingHTTPServer
from certification.direct_publisher_smoke_v1 import rehearsal_stub as base

FAULT_AT = 7
HANG_SECONDS = 60
LOCK = threading.Lock()


class Handler(base.Handler):
    questionnaire_fault = 'none'
    policy = 'scripted'
    latency = 0.0
    answers = tokens = keys = None
    calls = 0
    busy = False

    def do_GET(self):
        if self.path == '/metrics' and Handler.busy:  # not_idle: the hung request is still reported running
            text = (f'vllm:num_requests_running{{model_name="{self.served}"}} 1.0\n'
                    f'vllm:num_requests_waiting{{model_name="{self.served}"}} 0.0\n')
            return self._send(200, text.encode(), 'text/plain')
        return super().do_GET()

    def do_POST(self):
        from research.progress_subgoal_v1.fake_server import TRUNCATED, request_sha
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        if self.path != '/v1/chat/completions':
            return self._send(404, {'error': 'not found'})
        if body.get('stream'):
            return self._stream(body)
        questionnaire = (body.get('response_format') or {}).get('type') == 'json_schema'
        content, finish, usage = base.answer(body), 'stop', {'prompt_tokens': 100, 'completion_tokens': 1}
        if questionnaire:
            with LOCK:
                n = Handler.calls
                Handler.calls += 1
            fault = self.questionnaire_fault
            if self.latency:
                time.sleep(self.latency)
            hang = ((fault in ('timeout_once', 'not_idle') and n == FAULT_AT)
                    or (fault == 'consecutive_timeouts' and n in (FAULT_AT, FAULT_AT + 1)))
            if hang:
                if fault == 'not_idle':
                    Handler.busy = True
                time.sleep(HANG_SECONDS)
                return None  # the client has closed the connection
            if fault == 'http_error' and n == FAULT_AT:
                return self._send(500, {'error': 'scripted server error'})
            digest = request_sha(body)
            content = (json.dumps({'answer': self.keys[digest]}) if self.policy == 'oracle'
                       else self.answers(body))
            completion = max(1, min(31, len(content) // 3))
            if content.startswith(TRUNCATED):
                content, finish, completion = content[len(TRUNCATED):], 'length', 32
            usage = {'prompt_tokens': self.tokens[digest] + (1 if fault == 'token_mismatch' and n == FAULT_AT else 0),
                     'completion_tokens': completion}
        self._send(200, {'model': self.served, 'choices': [{'index': 0,
            'message': {'role': 'assistant', 'content': content}, 'finish_reason': finish}],
            'usage': usage})


def prepare(root):
    """Scripted answers and the frozen token audit's prompt-token count for every scheduled request."""
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1.fake_server import ScriptedAnswers
    from research.progress_subgoal_v1_runtime2 import questionnaire as QN
    frozen, _, rows = QN.scheduled(root)
    audit = QN.token_audit(root)
    probes = {p['probe_id']: p for p in frozen['probes']}
    tokens, keys = {}, {}
    for n, (_, _, _, probe_id, request) in enumerate(rows):
        digest = request_hash(request)
        tokens[digest] = audit['prompt_tokens'][n]
        keys[digest] = probes[probe_id]['key']
    return ScriptedAnswers(), tokens, keys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--served', required=True)
    parser.add_argument('--questionnaire-fault', choices=('none', 'timeout_once', 'consecutive_timeouts', 'not_idle',
                                                          'http_error', 'token_mismatch', 'admission_cutoff'),
                        default='none')
    parser.add_argument('--policy', choices=('scripted', 'oracle'), default='scripted')
    parser.add_argument('--latency', type=float, default=0.0)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    Handler.answers, Handler.tokens, Handler.keys = prepare(args.root)
    print('SCRIPTED CPU STUB: no model, no GPU; enable_prefix_caching=False', flush=True)
    Handler.served, Handler.questionnaire_fault = args.served, args.questionnaire_fault
    Handler.policy, Handler.latency = args.policy, args.latency
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
