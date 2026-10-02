"""CPU fake model server for rehearsals (never used in live mode; no model, no GPU).

Requests go through the derived service contract unchanged (`live.service.HistoryModelService`: startup canary,
per-request contract validation for both arms, tokenizer admission and call ceiling). Only the tokenizer and the
transport are stand-ins: a fixture tokenizer (character count / 4, identical on both sides so the token audit passes)
and scripted completions. Scripted outputs exercise plumbing; they say nothing about how a model behaves.
"""
import json
from types import SimpleNamespace

from research.feedback_action_v1 import adapter as AD, evidence as E

LATTICE = [(16, 16), (24, 16), (40, 20), (8, 40), (56, 8), (32, 48), (48, 32), (4, 4), (60, 60), (20, 50), (50, 20),
           (12, 28)]
MODES = ('normal', 'always_invalid', 'truncated_candidate', 'repeat')


def count(messages):
    return max(1, len(json.dumps(messages, sort_keys=True, separators=(',', ':'))) // 4)


class FixtureTokenizer:
    def apply_chat_template(self, messages, **_kwargs):
        return [1] * count(messages)


def scripted_content(request, call, mode, truncate=False, invalid=False):
    """(content, finish_reason) for one request. `call` counts policy calls from 1 (the canary is call 0).
    `truncate`: in mode truncated_candidate, the transport allows one truncation (at the candidate's second decision).
    `invalid`: this call returns unparseable output (the transport's `invalid_calls`)."""
    from research.feedback_action_v1.live.policy import arm_of
    content = request['messages'][1]['content']
    if not content.startswith('{'):  # the startup canary's user message is plain text
        return json.dumps({'action': {'action_id': 6, 'action_data': {'x': 5, 'y': 5}}}), 'stop'
    payload = json.loads(content)
    observation, arm = payload['observation'], arm_of(request)
    if mode == 'always_invalid' or invalid:
        return '{"action":', 'stop'
    if truncate and arm == 'candidate' and len(observation[E.FIELD]['entries']) == 1:
        return '{"hypothesis_test": {"hypothesis": "', 'length'
    legal, view = sorted(observation['legal_actions']), observation[E.FIELD]
    entries = view['entries']
    k = 0 if mode == 'repeat' else len(entries) + (1 if entries and entries[-1]['visual_effect'] == 'no_observed_change'
                                                   else 0)
    action_id = legal[k % len(legal)]
    action = {'action_id': action_id,
              'action_data': {'x': LATTICE[k % 12][0], 'y': LATTICE[k % 12][1]} if action_id == 6 else {}}
    if arm == 'baseline':
        return json.dumps({'action': action}), 'stop'
    carried = payload[AD.PREVIOUS_FIELD]
    supporting, conflicting, status = [], [], 'new'
    if entries:
        last = entries[-1]
        same = 'same_state_as_now' if last['from_state'] == view['current_state'] else 'different_state_from_now'
        cites = [{'ref': last['ref'], 'claim': last['visual_effect']}, {'ref': last['ref'], 'claim': same}]
        if (carried.get('available') and carried['about'] == last['ref']
                and carried['prediction']['visual_effect'] != last['visual_effect']):
            conflicting, status = cites, 'revised'
        else:
            supporting, status = cites, 'retained' if carried.get('available') else 'new'
    block = {'hypothesis': f'ACTION{action_id} changes the frame', 'status': status, 'supporting': supporting,
             'conflicting': conflicting,
             'prediction': {'visual_effect': 'final_frame_differs', 'level_completed': False,
                            'changed_region_xyxy': None},
             'if_different': f'ACTION{action_id} may be blocked or ineffective in this state'}
    return json.dumps({'hypothesis_test': block, 'action': action}), 'stop'


class ScriptedTransport:
    def __init__(self, mode='normal', invalid_calls=()):
        if mode not in MODES:
            raise ValueError('rehearsal mode')
        self.mode, self.calls, self.truncated = mode, -1, False  # the canary is call 0
        self.invalid_calls = frozenset(invalid_calls)  # policy-call numbers (from 1) that return invalid output

    def __call__(self, request):
        self.calls += 1
        content, finish = scripted_content(request, self.calls, self.mode,
                                           truncate=self.mode == 'truncated_candidate' and not self.truncated,
                                           invalid=self.calls in self.invalid_calls)
        self.truncated = self.truncated or finish == 'length'
        completion = request['max_tokens'] if finish == 'length' else min(request['max_tokens'],
                                                                           max(1, len(content) // 4))
        return SimpleNamespace(content=content, prompt_tokens=count(request['messages']),
                               completion_tokens=completion, finish_reason=finish)


class FakeServer:
    """The runner-facing service: the derived contract, a passed canary, scripted completions."""

    def __init__(self, mode='normal', invalid_calls=()):
        from research.feedback_action_v1.live.service import HistoryModelService
        self.transport = ScriptedTransport(mode, invalid_calls)
        self.service = HistoryModelService(None, self.transport, tokenizer=FixtureTokenizer(), check_versions=False)
        self.service.startup_canary()

    def complete(self, request):
        result, audit = self.service.complete(request)
        return {'content': result.content, 'tokenizer_prompt_tokens': audit['tokenizer_prompt_tokens'],
                'server_prompt_tokens': audit['server_prompt_tokens'],
                'server_completion_tokens': audit['server_completion_tokens'], 'finish_reason': audit['finish_reason']}
