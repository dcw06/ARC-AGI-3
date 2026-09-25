"""CPU rehearsal model: scripted transport and fixture tokenizer (never used in live mode)."""
import json
import time
from types import SimpleNamespace

LATTICE = [(16, 16), (24, 16), (40, 20), (8, 40), (56, 8), (32, 48), (48, 32), (4, 4), (60, 60), (20, 50), (50, 20), (12, 28)]
FAULTS = ('none', 'model_startup', 'transport', 'slow', 'invalid_history')


def count(messages):
    return max(1, len(json.dumps(messages, sort_keys=True, separators=(',', ':'))) // 4)


class FixtureTokenizer:
    def apply_chat_template(self, messages, **_kwargs):
        return [1] * count(messages)


def scripted_answer(request, calls, fault):
    content = request['messages'][1]['content']
    if not content.startswith('{'):  # the startup canary's user message is plain text
        return json.dumps({'action': {'action_id': 6, 'action_data': {'x': 5, 'y': 5}}})
    observation = json.loads(content)['observation']
    legal = sorted(observation['legal_actions'])
    history = observation.get('action_effect_history')
    k = 0
    if history is not None:
        k = len(history['entries'])
        if history['entries'] and history['entries'][-1]['final_frame_changed'] is False:
            k += 1
        if fault == 'invalid_history' and len(history['entries']) == 2:
            return '{"action":'
    action_id = legal[k % len(legal)]
    data = {'x': LATTICE[k % 12][0], 'y': LATTICE[k % 12][1]} if action_id == 6 else {}
    return json.dumps({'action': {'action_id': action_id, 'action_data': data}})


class ScriptedTransport:
    def __init__(self, fault='none', slow_seconds=0.0):
        if fault not in FAULTS:
            raise ValueError('rehearsal fault')
        self.fault, self.calls, self.slow = fault, 0, slow_seconds

    def __call__(self, request):
        self.calls += 1
        if self.fault == 'transport' and self.calls == 6:
            raise ConnectionError('rehearsal transport failure')
        if self.fault == 'slow':
            time.sleep(self.slow)
        content = scripted_answer(request, self.calls, self.fault)
        return SimpleNamespace(content=content, prompt_tokens=count(request['messages']),
                               completion_tokens=12, finish_reason='stop')
