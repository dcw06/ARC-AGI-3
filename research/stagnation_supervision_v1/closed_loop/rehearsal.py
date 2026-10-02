"""CPU rehearsal transport for the derived model host (hand-written; never used in live mode; no model).

`ScriptedTransport` has the interface the derived model service expects (request -> object with content,
prompt_tokens, completion_tokens, finish_reason). It answers the startup canary with a fixed legal ACTION6, and
policy and reflection requests through the fake server. `FixtureTokenizer` is action-effect-history v1's rehearsal
tokenizer, re-exported unchanged, so the service's pre-transport count equals the transport's reported count.
"""
import json
import time
from types import SimpleNamespace

from research.action_effect_history_v1.rehearsal import FixtureTokenizer, count  # noqa: F401  (re-exported unchanged)
from research.stagnation_supervision_v1.closed_loop.fake_server import FakeModelServer
from research.stagnation_supervision_v1.closed_loop.service import kind

FAULTS = ('none', 'model_startup', 'transport', 'slow', 'reflection_invalid', 'reflection_length')


class ScriptedTransport:
    def __init__(self, fault='none', slow_seconds=0.0):
        if fault not in FAULTS:
            raise ValueError('rehearsal fault')
        self.fault, self.calls, self.slow = fault, 0, slow_seconds
        self.server = FakeModelServer((fault,) if fault in ('reflection_invalid', 'reflection_length') else ())

    def __call__(self, request):
        self.calls += 1
        if self.fault == 'transport' and self.calls == 6:
            raise ConnectionError('rehearsal transport failure')
        if self.fault == 'slow':
            time.sleep(self.slow)
        user = request['messages'][1]['content']
        if kind(request) == 'policy' and not user.startswith('{'):  # the startup canary's plain-text message
            content, finish, completion = json.dumps({'action': {'action_id': 6, 'action_data': {'x': 5, 'y': 5}}}), 'stop', 12
        else:
            answer = self.server.complete(request)
            content, finish, completion = answer['content'], answer['finish_reason'], answer['server_completion_tokens']
        return SimpleNamespace(content=content, prompt_tokens=count(request['messages']), completion_tokens=completion,
                               finish_reason=finish)
