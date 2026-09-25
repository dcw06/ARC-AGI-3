"""Deterministic change-detection and action-effect fixtures.

Pre-action frames come from the committed ar25 development observation; post-action frames are
deterministic transformations of it (or small synthetic grids). They are perception and record
tests, not playable environments. Reference labels are computed mechanically by
records.effect_record; tests re-check them with an independent implementation. No case contains
a model interpretation, and none reveals the offline counterfactual probes. Action ids
are arbitrary labels chosen not to mirror any game's observed behaviour.
"""
import copy
import json
from pathlib import Path

from research.action_effect_v1.records import effect_record, EffectHistory

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name('fixtures.json')
BACKGROUND = 9


def base():
    value = json.loads((ROOT / 'reports/integrated_case_v1/initial_observation.json').read_bytes())
    return value['frames'][-1]


def reference_cells(object_id):
    reference = json.loads((ROOT / 'reports/integrated_case_v1/geometry_reference.json').read_bytes())
    return [tuple(c) for c in next(o for o in reference['objects'] if o['id'] == object_id)['cells']]


def observation(frames, levels=0, state='NOT_FINISHED', full_reset=False):
    return {'frames': frames, 'levels_completed': levels, 'state': state, 'full_reset': full_reset}


def moved(grid, object_id, dx, dy):
    out = copy.deepcopy(grid)
    cells = reference_cells(object_id)
    for x, y in cells:
        out[y][x] = BACKGROUND
    for x, y in cells:
        out[y + dy][x + dx] = grid[y][x]
    return out


def removed(grid, object_id):
    out = copy.deepcopy(grid)
    for x, y in reference_cells(object_id):
        out[y][x] = BACKGROUND
    return out


def recoloured(grid, object_id, old, new):
    out = copy.deepcopy(grid)
    for x, y in reference_cells(object_id):
        if out[y][x] == old:
            out[y][x] = new
    return out


def click(x, y):
    return {'action_id': 6, 'action_data': {'x': x, 'y': y}}


def plain(action_id):
    return {'action_id': action_id, 'action_data': {}}


def single_cases():
    g = base()
    ack = lambda frames, **kw: {'status': 'acknowledged', 'post': observation(frames, **kw)}
    return [
        ('same_type_coordinates_a', 'Same action type, first coordinates; identical frames',
         observation([g]), click(16, 16), ack([g])),
        ('same_type_coordinates_b', 'Same action type, different coordinates; identical frames',
         observation([g]), click(40, 20), ack([g])),
        ('identical_frames', 'Non-click action returning an identical frame',
         observation([g]), plain(2), ack([g])),
        ('movement', 'Object A translated one cell right',
         observation([g]), plain(7), ack([moved(g, 'A', 1, 0)])),
        ('disappearance', 'Object B removed (set to background)',
         observation([g]), plain(5), ack([removed(g, 'B')])),
        ('colour_only', 'Object A colour 5 changed to 8; shape and markings unchanged',
         observation([g]), plain(5), ack([recoloured(g, 'A', 5, 8)])),
        ('intermediate_return', 'First returned frame changes, final frame equals the pre-action frame',
         observation([g]), plain(7), ack([moved(g, 'A', 1, 0), copy.deepcopy(g)])),
        ('level_counter_only', 'Level counter increases while every pixel is unchanged',
         observation([g]), plain(5), ack([g], levels=1)),
        ('dimension_change', 'Returned frame has different dimensions',
         observation([g]), plain(5), ack([[[BACKGROUND] * 32 for _ in range(32)]])),
        ('dispatch_failed', 'Request rejected before reaching the game; must not become a no-op',
         observation([g]), click(16, 16), {'status': 'dispatch_failed', 'error': 'HTTP 503 before acknowledgement'}),
        ('outcome_unknown', 'Request sent but no result observed (timeout); must not become a no-op',
         observation([g]), plain(1), {'status': 'outcome_unknown', 'reason': 'response timeout after send'}),
    ]


def history_sequence():
    """Resets and level transitions: segment boundaries and failed dispatches kept distinct."""
    g = base()
    next_level = [[BACKGROUND] * 64 for _ in range(64)]
    for y in range(10, 14):
        for x in range(10, 14):
            next_level[y][x] = 3
    steps = [
        (observation([g]), plain(7), {'status': 'acknowledged', 'post': observation([moved(g, 'A', 1, 0)])}),
        (observation([moved(g, 'A', 1, 0)]), click(16, 16),
         {'status': 'acknowledged', 'post': observation([moved(g, 'A', 1, 0)])}),
        (observation([moved(g, 'A', 1, 0)]), click(16, 16), {'status': 'dispatch_failed', 'error': 'connection reset'}),
        (observation([moved(g, 'A', 1, 0)]), plain(2),
         {'status': 'acknowledged', 'post': observation([next_level], levels=1)}),
        (observation([next_level], levels=1), plain(3),
         {'status': 'acknowledged', 'post': observation([next_level], levels=1)}),
        (observation([next_level], levels=1), plain(4),
         {'status': 'acknowledged', 'post': observation([g], levels=0, full_reset=True)}),
        (observation([g]), click(20, 16), {'status': 'acknowledged', 'post': observation([g])}),
    ]
    history = EffectHistory(limit=5)
    entries = [history.append(effect_record(pre, action, outcome)) for pre, action, outcome in steps]
    return {'steps': [{'pre': pre, 'action': action, 'outcome': outcome} for pre, action, outcome in steps],
            'entries': entries, 'view': history.view()}


def generate():
    cases = [{'case_id': cid, 'description': text, 'pre': pre, 'action': action, 'outcome': outcome,
              'reference_record': effect_record(pre, action, outcome)}
             for cid, text, pre, action, outcome in single_cases()]
    return {'version': 'action_effect_fixtures_v1',
            'scope': 'Deterministic record and change-detection fixtures from the ar25 development frame. '
                     'Perception and record tests, not playable environments; labels are mechanical. Action ids are arbitrary labels, not derived from any game behaviour.',
            'cases': cases, 'history_sequence': history_sequence()}


def render():
    return json.dumps(generate(), separators=(',', ':'), sort_keys=True) + '\n'
