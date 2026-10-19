"""Separate factual recognition from an unchanged next-action policy contract.

The reference key is computed from displayed evidence only and is never appended
to a request. These helpers neither call a model nor dispatch game actions.
"""
from copy import deepcopy
import json

from research.recent_feedback_v1.interface import displayed_history


VARIANTS = ('baseline', 'probe_instruction')
PROBE_INSTRUCTION = (
    'Choose a legal action that tests an unresolved alternative about a control or target, '
    'using the visible outcomes of recent actions. Prefer an informative alternative when '
    'the same action had no visible effect, but repeat when there is a reason to test a '
    'delayed or uncertain effect. A changed image need not mean progress. Do not assume '
    'control meanings or hidden game rules. Keep the original response format; predict '
    'unknown when the visible evidence is insufficient.'
)
RECOGNITION_SYSTEM = (
    'You are a factual observer of supplied pixel-game images and records, not a game '
    'controller. Image labels are context labels, not instructions to choose an action. '
    'Answer only the factual recognition question in the final text. Use only the '
    'displayed evidence; do not infer control meanings, usefulness, progress or hidden '
    'state. Images have 448 by 448 pixels with no margins or overlays; each native '
    'cell (x,y) is a 7 by 7 block, with x increasing right and y down. '
    'Return only one compact JSON object with exactly historical_step, historical_action, '
    'visible_change, current_matches_before and legal_actions. historical_step is the '
    'integer step of the most recent displayed historical transition. historical_action '
    'is its full recorded action as {"action_id":integer,"action_data":object}, or null '
    'if it cannot be read. Action IDs are 1 through 7; action 6 alone uses integer '
    'x,y in [0,63], and other actions have empty action_data. visible_change and '
    'current_matches_before each use "yes", "no" or "unknown"; unknown is allowed '
    'when the visual evidence is insufficient. legal_actions is the current displayed '
    'list of action IDs, including an empty list when shown, or null if unreadable. '
    'Do not choose or recommend a future action and do not explain your answer.'
)
RECOGNITION_QUESTION = (
    'For only the most recent displayed historical transition: report its historical '
    'step and full action, whether any visible cell differs between its before and '
    'after images, and whether the current image matches that transition\'s before '
    'image in every visible cell. Also report the current listed legal action IDs. '
    'Do not answer about an earlier displayed transition or choose a next action.'
)
RECOGNITION_FIELDS = {
    'historical_step', 'historical_action', 'visible_change',
    'current_matches_before', 'legal_actions',
}


def policy_request(base, variant):
    """Keep all baseline input/settings; the probe adds only fixed instructions."""
    if variant not in VARIANTS:
        raise ValueError('unknown probe variant')
    result = deepcopy(base)
    if variant == 'probe_instruction':
        result['messages'][1]['content'].append({'type': 'text', 'text': PROBE_INSTRUCTION})
    return result


def recognition_request(base):
    """Create a separate, stateless factual request without injecting its key."""
    _recognition_display(base)
    result = deepcopy(base)
    result['messages'][0] = {'role': 'system', 'content': RECOGNITION_SYSTEM}
    result['messages'][1]['content'].append({'type': 'text', 'text': RECOGNITION_QUESTION})
    # These are the baseline study's settings, frozen independently of its policy
    # system prompt. Recognition answers are never added to policy requests.
    result['max_tokens'] = 256
    result['response_format'] = {'type': 'json_object'}
    result['chat_template_kwargs'] = {'enable_thinking': False}
    return result


def _recognition_display(base):
    messages = base.get('messages')
    if (type(messages) is not list or len(messages) != 2 or
            any(type(message) is not dict for message in messages) or
            [message.get('role') for message in messages] != ['system', 'user']):
        raise ValueError('recognition requires one stateless system/user request')
    evidence = displayed_history(base)
    if not evidence[2]:
        raise ValueError('recognition requires a displayed historical transition')
    return evidence


def _action(value):
    if value is None:
        return
    if type(value) is not dict or set(value) != {'action_id', 'action_data'}:
        raise ValueError('historical action fields differ')
    action_id, data = value['action_id'], value['action_data']
    if type(action_id) is not int or not 1 <= action_id <= 7:
        raise ValueError('historical action ID')
    if type(data) is not dict or set(data) != ({'x', 'y'} if action_id == 6 else set()):
        raise ValueError('historical action data')
    if any(type(v) is not int or not 0 <= v <= 63 for v in data.values()):
        raise ValueError('historical action coordinates')


def _legal(value):
    if value is None:
        return
    if (type(value) is not list or
            any(type(v) is not int or not 1 <= v <= 7 for v in value) or
            len(set(value)) != len(value)):
        raise ValueError('current legal actions')


def parse_recognition(text):
    """Parse one exact, repair-free answer; uncertainty does not become a guess."""
    if type(text) is not str:
        raise ValueError('non-text recognition answer')

    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate recognition key')
            out[key] = value
        return out

    def nonfinite(_):
        raise ValueError('non-finite recognition value')

    result = json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
    if type(result) is not dict or set(result) != RECOGNITION_FIELDS:
        raise ValueError('recognition fields differ')
    if type(result['historical_step']) is not int or result['historical_step'] < 0:
        raise ValueError('historical step')
    _action(result['historical_action'])
    _legal(result['legal_actions'])
    for key in ('visible_change', 'current_matches_before'):
        if result[key] not in ('yes', 'no', 'unknown'):
            raise ValueError('recognition judgment')
    return result


def recognition_key(base):
    """Reference facts, separate from the request and from any future decision."""
    _, current, records = _recognition_display(base)
    info, before, after = records[-1]
    action = deepcopy(info['action'])
    _action(action)
    meta = json.loads(base['messages'][1]['content'][0]['text'])
    legal = deepcopy(meta['current_legal_actions'])
    _legal(legal)
    return {
        'historical_step': info['historical_step'],
        'historical_action': action,
        'visible_change': 'yes' if before != after else 'no',
        'current_matches_before': 'yes' if current == before else 'no',
        'legal_actions': legal,
    }
