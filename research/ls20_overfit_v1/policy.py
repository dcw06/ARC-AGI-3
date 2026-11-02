"""Demonstration memorization; no model inference or inferred game rules."""
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import re

from research.initial_geometry_assistance_v1.geometry import check_grid, digest
from research.initial_geometry_assistance_v1.policy import check_observation

GAME_ID = 'ls20-9607627b'
SCHEMA = 'ls20_overfit_v1'
MAX_MOVES = 256
QUALIFICATION = (
    'Memorized human demonstration on ls20-9607627b, seed 0, first three levels only. '
    'Exact observation matching includes the visible time bar. This is not a general learned policy.'
)


def _sha(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('invalid SHA256')
    return value


def _action(value):
    if (type(value) is not dict or set(value) != {'action_id', 'action_data'} or
            type(value['action_id']) is not int or value['action_id'] not in (1, 2, 3, 4) or
            type(value['action_data']) is not dict or value['action_data']):
        raise ValueError('expected one directional action with empty data')
    return value


def _snapshot(value):
    check_observation(value)
    if value['legal_actions'] != sorted(value['legal_actions']):
        raise ValueError('legal actions must use the engine snapshot ordering')
    return value


def _raw_snapshot(value):
    expected = {'game_id', 'state', 'levels_completed', 'win_levels',
                'available_actions', 'frames', 'canonical_hash'}
    if type(value) is not dict or set(value) != expected or value['game_id'] != GAME_ID:
        raise ValueError('demonstration observation contract differs')
    if type(value['win_levels']) is not int or value['win_levels'] != 7:
        raise ValueError('demonstration winning-level count differs')
    _sha(value['canonical_hash'])
    if type(value['frames']) is not list or not value['frames']:
        raise ValueError('demonstration has no visible frame')
    for frame in value['frames']:
        check_grid(frame)
    actions = value['available_actions']
    if (type(actions) is not list or any(type(a) is not int for a in actions) or
            len(set(actions)) != len(actions)):
        raise ValueError('demonstration legal actions differ')
    return _snapshot({'grid': value['frames'][-1], 'state': value['state'],
                      'levels_completed': value['levels_completed'],
                      'legal_actions': sorted(actions)})


def _utc(value):
    if type(value) is not str:
        raise ValueError('demonstration timestamp is not text')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('invalid demonstration timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError('demonstration timestamp must be UTC')
    return parsed


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def _not_finite(_):
    raise ValueError('non-finite JSON value')


def compile_demo(path, expected_sha256):
    """Extract the first uninterrupted three-level success; leave the source untouched."""
    _sha(expected_sha256)
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('human demonstration SHA256 differs')
    rows = [json.loads(line, object_pairs_hook=_pairs, parse_constant=_not_finite)
            for line in raw.decode('utf-8').splitlines()]
    if not rows or type(rows[0]) is not dict:
        raise ValueError('missing demonstration session')
    header = rows[0]
    if (header.get('type') != 'session_start' or header.get('schema') != 'public_game_manual_v1' or
            header.get('game_id') != GAME_ID or type(header.get('seed')) is not int or
            header['seed'] != 0 or header.get('actor') != 'human_manual' or
            header.get('source') != 'offline_public_development_engine'):
        raise ValueError('demonstration game, seed or origin differs')
    _utc(header.get('utc'))
    previous = header.get('initial_observation')
    initial = _raw_snapshot(previous)
    if initial['levels_completed'] != 0 or initial['state'] != 'NOT_FINISHED':
        raise ValueError('demonstration does not start at level one')
    steps, boundaries, request_ids = [], [], set()
    last_boundary = 0
    for index in range(MAX_MOVES):
        position = 2 * index + 1
        if position + 1 >= len(rows):
            raise ValueError('demonstration ends before three levels are complete')
        entered, acknowledged = rows[position:position + 2]
        if (type(entered) is not dict or type(acknowledged) is not dict or
                entered.get('type') != 'action_entered' or
                acknowledged.get('type') != 'action_acknowledged'):
            raise ValueError('demonstration action and acknowledgement pairing differs')
        for event in (entered, acknowledged):
            if type(event.get('sequence')) is not int or event['sequence'] != index + 1:
                raise ValueError('demonstration sequence differs')
        request_id = entered.get('request_id')
        if (type(request_id) is not str or not request_id or request_id in request_ids or
                acknowledged.get('request_id') != request_id):
            raise ValueError('demonstration request pairing differs')
        request_ids.add(request_id)
        # The retained demo has two wall-clock reversals. Sequence numbers,
        # request pairing and the exact observation chain establish event order.
        _utc(entered.get('utc'))
        _utc(acknowledged.get('utc'))
        seconds = acknowledged.get('seconds')
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('demonstration acknowledgement duration differs')
        before, after = _raw_snapshot(entered.get('before')), _raw_snapshot(acknowledged.get('after'))
        if entered['before'] != previous or before['state'] != 'NOT_FINISHED':
            raise ValueError('demonstration observation chain differs')
        action = _action(entered.get('action'))
        if action['action_id'] not in before['legal_actions']:
            raise ValueError('demonstration action is not legal')
        old_level, new_level = before['levels_completed'], after['levels_completed']
        if not old_level <= new_level <= old_level + 1 or after['state'] == 'GAME_OVER':
            raise ValueError('demonstration level progression differs')
        if after['state'] != 'NOT_FINISHED' and new_level < 3:
            raise ValueError('demonstration terminates before level three')
        steps.append({'index': index, 'action': deepcopy(action),
                      'before_sha256': digest(before), 'after_sha256': digest(after),
                      'before_levels': old_level, 'after_levels': new_level})
        if new_level > old_level:
            boundaries.append({'level': new_level, 'after_moves': index + 1,
                               'moves': index + 1 - last_boundary})
            last_boundary = index + 1
        if new_level == 3:
            program = {'schema': SCHEMA, 'game_id': GAME_ID, 'seed': 0, 'goal_levels': 3,
                       'source_demo_sha256': expected_sha256, 'initial_observation': deepcopy(initial),
                       'steps': steps, 'level_boundaries': boundaries, 'qualification': QUALIFICATION}
            OverfitPolicy(program)
            return program
        previous = acknowledged['after']
    raise ValueError('three-level demonstration exceeds the 256-move cap')


class OverfitPolicy:
    """Acknowledge every observed transition before selecting the next memorized action."""

    def __init__(self, program):
        self._program = deepcopy(program)
        p = self._program
        fields = {'schema', 'game_id', 'seed', 'goal_levels', 'source_demo_sha256',
                  'initial_observation', 'steps', 'level_boundaries', 'qualification'}
        if (type(p) is not dict or set(p) != fields or p['schema'] != SCHEMA or
                p['game_id'] != GAME_ID or type(p['seed']) is not int or p['seed'] != 0 or
                type(p['goal_levels']) is not int or p['goal_levels'] != 3 or
                p['qualification'] != QUALIFICATION):
            raise ValueError('overfit program contract differs')
        _sha(p['source_demo_sha256'])
        initial = _snapshot(p['initial_observation'])
        if initial['state'] != 'NOT_FINISHED' or initial['levels_completed'] != 0:
            raise ValueError('overfit program initial observation differs')
        if type(p['steps']) is not list or not 1 <= len(p['steps']) <= MAX_MOVES:
            raise ValueError('overfit program move cap differs')
        previous_hash, level, boundary = digest(initial), 0, 0
        boundaries = []
        for index, step in enumerate(p['steps']):
            if (type(step) is not dict or set(step) != {'index', 'action', 'before_sha256',
                    'after_sha256', 'before_levels', 'after_levels'} or
                    type(step['index']) is not int or step['index'] != index or
                    type(step['before_levels']) is not int or step['before_levels'] != level or
                    type(step['after_levels']) is not int or
                    not level <= step['after_levels'] <= min(3, level + 1) or level == 3):
                raise ValueError('overfit program step or level chain differs')
            _action(step['action'])
            if _sha(step['before_sha256']) != previous_hash:
                raise ValueError('overfit program observation hash chain differs')
            previous_hash = _sha(step['after_sha256'])
            if step['after_levels'] != level:
                boundaries.append({'level': step['after_levels'], 'after_moves': index + 1,
                                   'moves': index + 1 - boundary})
                boundary = index + 1
            level = step['after_levels']
        # Canonical JSON distinguishes true from 1, unlike Python dict equality.
        if (level != 3 or type(p['level_boundaries']) is not list or
                any(type(item) is not dict or set(item) != {'level', 'after_moves', 'moves'} or
                    any(type(value) is not int for value in item.values())
                    for item in p['level_boundaries']) or
                digest(p['level_boundaries']) != digest(boundaries)):
            raise ValueError('overfit program completion boundaries differ')
        self._cursor, self._pending, self._failed = 0, None, False

    @property
    def cursor(self):
        return self._cursor

    @property
    def completed(self):
        return not self._failed and self._cursor == len(self._program['steps'])

    def _refuse(self, message):
        self._failed = True
        raise ValueError(message)

    def select(self, game_id, observation):
        if self._failed:
            raise ValueError('overfit policy previously failed')
        if self.completed:
            raise StopIteration('first three levels complete')
        if self._pending is not None:
            raise ValueError('previous action acknowledgement is still pending')
        try:
            current = _snapshot(observation)
            step = self._program['steps'][self._cursor]
            if (game_id != GAME_ID or current['state'] != 'NOT_FINISHED' or
                    current['levels_completed'] != step['before_levels'] or
                    digest(current) != step['before_sha256'] or
                    step['action']['action_id'] not in current['legal_actions']):
                self._refuse('current observation, game or action differs from the demonstration')
        except (TypeError, KeyError, ValueError):
            self._failed = True
            raise
        self._pending = deepcopy(step['action'])
        return deepcopy(self._pending)

    def acknowledge(self, action, after):
        if self._failed:
            raise ValueError('overfit policy previously failed')
        if self._pending is None:
            self._refuse('no action is awaiting acknowledgement')
        try:
            _action(action)
            current = _snapshot(after)
            step = self._program['steps'][self._cursor]
            if (action != self._pending or digest(current) != step['after_sha256'] or
                    current['levels_completed'] != step['after_levels'] or
                    current['state'] == 'GAME_OVER' or
                    (current['state'] != 'NOT_FINISHED' and current['levels_completed'] < 3)):
                self._refuse('acknowledged action or observation differs from the demonstration')
        except (TypeError, KeyError, ValueError):
            self._failed = True
            raise
        self._cursor += 1
        self._pending = None
