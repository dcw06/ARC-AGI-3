"""Deterministic request construction and strict, repair-free action parsing."""
import json

from certification.phase4_multimodal_preflight_v3.images import data_url, png
from .geometry import check_grid, check_inventory, digest

SYSTEM = (
    'You control an unfamiliar pixel game. Try to complete its first level using visible feedback. '
    'You receive no game rules or game-specific control explanations. Only listed action IDs are legal. '
    'ACTION6 alone takes integer x,y coordinates in [0,63]; all other actions take an empty data object. '
    'Each image is exactly 448 by 448: original cell (x,y) occupies pixels [7*x,7*x+6] by [7*y,7*y+6], '
    'with x increasing right and y down. No image has margins or overlays. '
    'The supplied geometry belongs ONLY to the initial step-0 image. Objects may since have moved, '
    'changed or disappeared; do not treat its cells as current positions. The inventory can be incomplete '
    'or wrong. It supplies geometry, not control meanings or game rules. '
    'Observe the current image and recent transitions, choose one action, and predict whether the next '
    'final image will differ in any visible cell (including interface changes). Use unknown if uncertain. '
    'Return ONLY compact JSON with exactly action_id, action_data and predicted_visible_change. '
    'Example syntax: {"action_id":6,"action_data":{"x":20,"y":30},'
    '"predicted_visible_change":"unknown"}. Do not reset, explain, or output multiple actions.'
)


def check_observation(observation):
    if type(observation) is not dict or set(observation) != {'grid', 'legal_actions', 'state', 'levels_completed'}:
        raise ValueError('observation contract differs')
    check_grid(observation['grid'])
    actions = observation['legal_actions']
    if (type(actions) is not list or len(set(actions)) != len(actions) or
            any(type(v) is not int or not 1 <= v <= 7 for v in actions)):
        raise ValueError('invalid legal actions')
    if observation['state'] not in ('NOT_FINISHED', 'WIN', 'GAME_OVER'):
        raise ValueError('invalid engine state')
    if type(observation['levels_completed']) is not int or observation['levels_completed'] < 0:
        raise ValueError('invalid level counter')
    return observation


def request_for(initial, geometry, current, history, step, model):
    check_observation(initial)
    check_observation(current)
    check_inventory(geometry)
    if type(step) is not int or not 0 <= step < 24 or len(history) != step:
        raise ValueError('history/step mismatch')
    meta = {'step': step, 'current_legal_actions': current['legal_actions'],
            'current_state': current['state'], 'current_levels_completed': current['levels_completed'],
            'geometry_observed_at_step': 0, 'geometry_initial_grid_sha256': digest(initial['grid']),
            'initial_objects': geometry, 'omitted_transition_count': max(0, len(history)-2)}
    content = [{'type': 'text', 'text': json.dumps(meta, sort_keys=True, separators=(',', ':'))}]

    def image(label, grid):
        content.extend([{'type': 'text', 'text': label},
                        {'type': 'image_url', 'image_url': {'url': data_url(png(grid, cell=7))}}])

    image('Initial image, step 0 (historical):', initial['grid'])
    for old in history[-2:]:
        content.append({'type': 'text', 'text': json.dumps({
            'historical_step': old['step'], 'action': old['action'],
            'before_state': old['before']['state'], 'after_state': old['after']['state'],
            'after_levels_completed': old['after']['levels_completed']}, sort_keys=True)})
        image('Historical before:', old['before']['grid'])
        image('Historical after:', old['after']['grid'])
    image('Current image; choose the next action here:', current['grid'])
    return {'model': model, 'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': content}],
            'temperature': 0, 'seed': 0, 'max_tokens': 256,
            'response_format': {'type': 'json_object'}, 'chat_template_kwargs': {'enable_thinking': False}}


def parse_answer(text, legal_actions):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('duplicate response key')
            out[k] = v
        return out
    if type(text) is not str:
        raise ValueError('non-text answer')
    answer = json.loads(text, object_pairs_hook=pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite JSON')))
    if type(answer) is not dict or set(answer) != {'action_id', 'action_data', 'predicted_visible_change'}:
        raise ValueError('response fields differ')
    action_id, data = answer['action_id'], answer['action_data']
    if type(action_id) is not int or action_id not in legal_actions or not 1 <= action_id <= 7:
        raise ValueError('illegal action ID')
    if type(data) is not dict or set(data) != ({'x', 'y'} if action_id == 6 else set()):
        raise ValueError('action data fields differ')
    if any(type(v) is not int or not 0 <= v < 64 for v in data.values()):
        raise ValueError('invalid action coordinate')
    if answer['predicted_visible_change'] not in ('yes', 'no', 'unknown'):
        raise ValueError('invalid change prediction')
    return answer
