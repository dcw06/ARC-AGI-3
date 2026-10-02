"""CPU fake model server for rehearsals (hand-written; never used in live mode; no model).

Policy behaviour (scripted, deterministic): without a suggestion block it repeats one "stuck" action (ACTION6 at a
fixed cell if legal, else the lowest legal id), so the frozen detector has loops to observe. With a suggestion
block present it takes the block's first test action if legal, then rotates through the other legal actions until
the block expires or is cleared. Reflection behaviour: a valid four-field answer proposing a legal action different
from the last one shown. Faults reproduce invalid reflections, reflection transport failures and token-audit
mismatches. Token counts are a fixture count (4 characters per token), equal on both sides unless faulted.
"""
import json
import re

from research.stagnation_supervision_v1.closed_loop import bridge as B
from research.stagnation_supervision_v1.closed_loop.service import kind

FAULTS = ('reflection_invalid', 'reflection_exception', 'reflection_audit_mismatch', 'reflection_length',
          'reflection_missing_finish', 'reflection_unknown_finish')
FINISH = {'reflection_length': 'length', 'reflection_missing_finish': None, 'reflection_unknown_finish': 'tool_calls'}
STUCK_CELL = {'x': 32, 'y': 32}


def count(value):
    return max(1, len(json.dumps(value, sort_keys=True, separators=(',', ':'))) // 4)


class FakeModelServer:
    def __init__(self, faults=()):
        if set(faults) - set(FAULTS):
            raise ValueError('unknown rehearsal fault')
        self.faults = set(faults)
        self.policy_calls = self.reflection_calls = 0
        self.followed = {}  # issued_after_action -> how many requests have carried that block

    def complete(self, request):
        if kind(request) == 'reflection':
            self.reflection_calls += 1
            if 'reflection_exception' in self.faults:
                raise ConnectionError('rehearsal reflection transport failure')
            content = 'not json' if 'reflection_invalid' in self.faults else self._reflect(request)
        else:
            self.policy_calls += 1
            content = self._policy(request)
        prompt = count(request['messages'])
        reflection = kind(request) == 'reflection'
        server = prompt + 1 if 'reflection_audit_mismatch' in self.faults and reflection else prompt
        finish = 'stop'
        for fault in self.faults & set(FINISH):
            if reflection:
                finish = FINISH[fault]
        return {'content': content, 'tokenizer_prompt_tokens': prompt, 'server_prompt_tokens': server,
                'server_completion_tokens': max(1, len(content) // 4), 'finish_reason': finish}

    def _policy(self, request):
        payload = json.loads(request['messages'][1]['content'])
        legal = sorted(payload['observation']['legal_actions'])
        stuck = ({'action_id': 6, 'action_data': dict(STUCK_CELL)} if 6 in legal
                 else {'action_id': legal[0], 'action_data': {}})
        block = payload.get(B.SUGGESTION_FIELD)
        if block is None:
            action = stuck
        else:
            n = self.followed.get(block['issued_after_action'], 0)
            self.followed[block['issued_after_action']] = n + 1
            proposed = self._test_action(block['text'], legal)
            others = [a for a in legal if a != stuck['action_id']] or legal
            if n == 0 and proposed is not None:
                action = proposed
            else:
                a = others[n % len(others)]
                action = {'action_id': a, 'action_data': {'x': 8 + 8 * (n % 7), 'y': 8} if a == 6 else {}}
        return json.dumps({'action': action})

    @staticmethod
    def _test_action(text, legal):
        match = re.search(r'^Test actions: (\[.*\])$', text, re.M)
        if not match:
            return None
        actions = json.loads(match.group(1))
        first = actions[0] if actions else None
        return first if first and first['action_id'] in legal else None

    @staticmethod
    def _reflect(request):
        content = json.loads(request['messages'][1]['content'].split('Evidence:\n', 1)[1])
        shown = [e['action_index'] for e in content['evidence']]
        last = content['evidence'][-1]['action']['action_id']
        legal = [a for a in content['available_actions'] if 1 <= a <= 7]
        choice = next((a for a in legal if a != last), legal[0])
        height, width = content['frame_shape']
        action = {'action_id': choice, 'action_data': {'x': width // 4, 'y': height // 4} if choice == 6 else {}}
        return json.dumps({'observed_pattern': 'The same action repeats and the frame does not change.',
                           'evidence_refs': shown[-2:],
                           'assumption_to_reconsider': 'That repeating this action will eventually change something.',
                           'distinguishing_test': {'description': 'Take a different action once and compare frames.',
                                                   'actions': [action]}})
