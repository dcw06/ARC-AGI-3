"""VLM judges a path color first, then plans each actual action without a route."""
import json
from certification.phase4_multimodal_preflight_v3.images import png, data_url, PALETTE
from research.initial_geometry_assistance_v1.policy import check_observation, parse_answer
from .geometry import context

MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
ACTION_CAP = 24
ASSESS_SYSTEM = (
    'Inspect the initial pixel-game image and the supplied k=4 spatial neighbor estimate. '
    'The estimate predicts hidden floor near the orange-and-blue player, not the sprite color; '
    'it is a heuristic, not a supplied correct path label. Decide independently which visible '
    'color represents a usable route to the white cross. Use null when uncertain. '
    'Return only JSON with exactly path_color_id (integer 0 through 15 or null). '
    'After exploration, compare actual before/after movement. Moving without a special event '
    'is evidence of traversability only; no effect or a blocked move is not proof of a color role. '
    'No action, explanation, route sequence or additional field.'
)
SYSTEM = (
    'Move the orange-and-blue player to the initial white cross location. Plan your own route. '
    'Controls: 1 up, 2 down, 3 left, 4 right; action_data is {}. No clicks, reset or batches. '
    'The earlier path-color judgment and k=4 floor estimate may be wrong. Inspect the current '
    'image and actual movement feedback; do not assume color alone proves traversability. '
    'Avoid repeating a blocked move. The supplied player/cross coordinates are assisted visible '
    'geometry, not hidden engine state. Images are 448x448, native cells are 7x7; x right, y down. '
    'Stop goal is reaching the cross, not solving the level or reaching the other square. '
    'In explore_colors mode, prefer a nearby uniform color region not yet tried, including '
    'regions whose traversability is uncertain. Use actual movement feedback to distinguish '
    'blocked motion from motion with no special event. Do not keep retrying a blocked direction. '
    'You have at most eight exploration moves; never assume every color is reachable. '
    'Return only compact JSON with exactly action_id (1,2,3,4), action_data ({}), '
    'predicted_visible_change (yes,no,unknown).'
)


def body(system, content):
    return dict(model=MODEL, messages=[dict(role='system', content=system), dict(role='user', content=content)],
                max_tokens=256, temperature=0, seed=0, chat_template_kwargs={'enable_thinking': False},
                response_format={'type': 'json_object'})


def image(label, grid):
    return [dict(type='text', text=label),
            dict(type='image_url', image_url={'url': data_url(png(grid, cell=7))})]


def assess_request(initial, instructions, current=None, history=None):
    check_observation(initial)
    current = initial if current is None else current
    history = [] if history is None else history
    check_observation(current)
    return body(ASSESS_SYSTEM, [dict(type='text', text=instructions), dict(type='text', text=json.dumps(
        dict(geometry_and_knn=context(initial['grid'], current['grid']),
             probes=probe_records(initial, history),
             rendered_palette={str(i): list(rgb) for i, rgb in enumerate(PALETTE)}), sort_keys=True))]
        + image('Initial board (historical):', initial['grid'])
        + image('Current board; judge the path color without an action:', current['grid']))


def probe_records(initial, history):
    records = []
    for item in history:
        before = context(initial['grid'], item['before']['grid'])
        after = context(initial['grid'], item['after']['grid'])
        region = next((r for r in before['adjacent_regions'] if r['action_id'] == item['action']['action_id']), None)
        old, new = before['current_player']['center'], after['current_player']['center']
        records.append(dict(step=item['step'], action_id=item['action']['action_id'],
            targeted_initial_region=region, displacement=[new[0]-old[0], new[1]-old[1]],
            moved=old != new, floor_estimate_after=after['current_floor_estimate']['predicted_color_id']))
    return records


def parse_assessment(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('duplicate path assessment field')
            result[key] = value
        return result
    value = json.loads(text, object_pairs_hook=pairs)
    if (type(value) is not dict or set(value) != {'path_color_id'} or
            (value['path_color_id'] is not None and
             (type(value['path_color_id']) is not int or not 0 <= value['path_color_id'] < 16))):
        raise ValueError('path assessment must be one color ID or null')
    return value


def make_request(initial, current, history, instructions, assessment, mode='navigate_to_cross'):
    check_observation(initial); check_observation(current)
    parse_assessment(json.dumps(assessment))
    if (type(instructions) is not str or not instructions.strip() or
            len(history) >= ACTION_CAP or current['legal_actions'] != [1, 2, 3, 4]):
        raise ValueError('navigation request scope differs')
    content = [dict(type='text', text=instructions), dict(type='text', text=json.dumps(dict(
        decision_index=len(history), action_cap=ACTION_CAP, path_assessment=assessment, mode=mode,
        observed_probes=probe_records(initial, history),
        geometry_and_knn=context(initial['grid'], current['grid']),
        executed_actions=[r['action'] for r in history]), sort_keys=True))]
    content += image('Initial board (historical):', initial['grid'])
    for entry in history[-2:]:
        content.append(dict(type='text', text=json.dumps({'previous_action': entry['action'], 'step': entry['step']}, sort_keys=True)))
        content += image('Previous before:', entry['before']['grid']) + image('Previous after:', entry['after']['grid'])
    content += image('Current board: choose one action toward the cross.', current['grid'])
    return body(SYSTEM, content)


def parse(text, legal):
    answer = parse_answer(text, legal)
    if answer['action_id'] not in (1, 2, 3, 4) or answer['action_data']:
        raise ValueError('directional action required')
    return answer
