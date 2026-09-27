"""Continuous synthetic trajectories for evidence comprehension v2 (frozen generation rules and seeds).

A trajectory is a sequence of events from one starting frame. Each event records its action, its kind,
the frame it started from and the levels completed before it; an acknowledged event also records every
returned frame, the levels completed after it and whether the game reported a full reset. Rules (asserted
here and re-checked by `independent.py`):
- an acknowledged event's final returned frame is the next event's starting frame;
- a failed dispatch leaves the frame unchanged;
- after an unknown outcome the next frame may or may not differ (nothing was observed);
- `level_up` returns a new level's frame and increments levels_completed;
- `reset` returns the current level's starting frame, which may equal the frame before it.

Records are built by the real record code (research/action_effect_v1/records.py) and shown through the
live history field (research/action_effect_history_v1/contract.py), which shows only the current segment:
entries before the latest reset or level change are never shown.

The templates target the v1 findings (coordinate availability, previously ineffective actions, transient
changes) and the boundary cases: unavailable ACTION6 with clicks in history, neighbouring click
coordinates, absent history, failed dispatch, unknown outcome, transient change, reset and level change.
Nothing here recommends an action or encodes game rules.
"""
import copy
import hashlib
import json
import random

from research.action_effect_history_v1.contract import history_field
from research.action_effect_v1.records import EffectHistory, effect_record

KINDS = ('no_change', 'final_change', 'transient', 'dispatch_failed', 'outcome_unknown', 'level_up', 'reset')
ACKNOWLEDGED = ('no_change', 'final_change', 'transient', 'level_up', 'reset')
WIN_LEVELS = 8
LEGAL_WITH_6 = ([1, 2, 3, 4, 5, 6, 7], [6], [1, 2, 3, 4, 6], [6, 7], [2, 4, 5, 6], [1, 3, 6])
LEGAL_WITHOUT_6 = ([1, 2, 3, 4, 5, 7], [1, 2, 3, 4, 5], [1, 3, 5, 7], [1, 2, 3, 4], [5, 7], [2, 7])


# ------------------------------------------------------------------ frames

def encode_frame(grid):
    return f'{len(grid)}x{len(grid[0])}:' + ''.join('0123456789abcdef'[v] for row in grid for v in row)


def decode_frame(text):
    size, cells = text.split(':')
    h, w = map(int, size.split('x'))
    return [[int(cells[y * w + x], 16) for x in range(w)] for y in range(h)]


def mutate(rng, grid):
    """A deterministic local change: one rectangle recoloured (every cell in it differs)."""
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    rh, rw = rng.randint(1, 5), rng.randint(1, 6)
    y0, x0 = rng.randrange(h - rh + 1), rng.randrange(w - rw + 1)
    colour = rng.randrange(16)
    for y in range(y0, y0 + rh):
        for x in range(x0, x0 + rw):
            out[y][x] = colour if colour != grid[y][x] else (colour + 1) % 16
    return out


def new_level(rng, grid):
    out = grid
    for _ in range(6):
        out = mutate(rng, out)
    return out


# ------------------------------------------------------------------ events

def run(rng, base, steps, levels=0):
    """Continuous events from (action, kind) steps, starting with `levels` levels completed."""
    current, level_start, events = base, base, []
    for action, kind in steps:
        if kind not in KINDS:
            raise ValueError(kind)
        event = {'action': copy.deepcopy(action), 'kind': kind, 'pre': encode_frame(current), 'levels_before': levels}
        returned = None
        if kind == 'no_change':
            returned = [current] * rng.randint(1, 2)
        elif kind == 'final_change':
            frames = [mutate(rng, current) for _ in range(rng.randint(1, 2))]
            current = frames[-1]
            returned = frames
        elif kind == 'transient':
            returned = [mutate(rng, current) for _ in range(rng.randint(1, 2))] + [current]
        elif kind == 'level_up':
            current = level_start = new_level(rng, current)
            levels += 1
            returned = [current]
        elif kind == 'reset':
            current = level_start
            returned = [current]
        elif kind == 'outcome_unknown' and rng.random() < 0.5:
            current = mutate(rng, current)  # the game may have changed; nothing was observed
        if returned is not None:
            event.update(returned=[encode_frame(f) for f in returned], levels_after=levels,
                         full_reset=kind == 'reset')
        events.append(event)
    return {'events': events, 'final': encode_frame(current), 'levels_completed': levels}


def continuity_errors(trajectory):
    errors = []
    events = trajectory['events']
    for i, event in enumerate(events):
        following = events[i + 1]['pre'] if i + 1 < len(events) else trajectory['final']
        if 'returned' in event and event['returned'][-1] != following:
            errors.append(f'{trajectory["context_id"]}: event {i} final frame is not the next starting frame')
        if event['kind'] == 'dispatch_failed' and event['pre'] != following:
            errors.append(f'{trajectory["context_id"]}: failed dispatch {i} changed the frame')
    return errors


def history_of(trajectory):
    history = EffectHistory(limit=64)
    for event in trajectory['events']:
        pre = {'frames': [decode_frame(event['pre'])], 'levels_completed': event['levels_before']}
        if event['kind'] == 'dispatch_failed':
            outcome = {'status': 'dispatch_failed', 'error': 'request rejected before acknowledgement'}
        elif event['kind'] == 'outcome_unknown':
            outcome = {'status': 'outcome_unknown', 'reason': 'response timeout after send'}
        else:
            outcome = {'status': 'acknowledged', 'post': {
                'frames': [decode_frame(f) for f in event['returned']], 'levels_completed': event['levels_after'],
                'full_reset': event['full_reset'], 'state': 'NOT_FINISHED'}}
        history.append(effect_record(pre, event['action'], outcome))
    return history


def observation(trajectory):
    """The live observation format without grids (the v1 gate format), with the live history field."""
    events = trajectory['events']
    return {'legal_actions': list(trajectory['legal_actions']), 'levels_completed': trajectory['levels_completed'],
            'win_levels': WIN_LEVELS, 'state': 'NOT_FINISHED',
            'recent_actions': [events[-1]['action']['action_id']] if events else [],
            'action_effect_history': history_field(history_of(trajectory))}


# ------------------------------------------------------------------ templates

def click(x, y):
    return {'action_id': 6, 'action_data': {'x': x, 'y': y}}


def simple(ident):
    return {'action_id': ident, 'action_data': {}}


def pick(rng, legal):
    """A clicked cell (whether or not ACTION6 is legal now), a legal simple action, or occasionally an id that
    is not currently legal: history can contain actions that are no longer available."""
    if rng.random() < 0.35:
        return click(rng.randrange(64), rng.randrange(64))
    simple_legal = [i for i in legal if i != 6]
    other = [i for i in (1, 2, 3, 4, 5, 7) if i not in legal]
    if not simple_legal or (other and rng.random() < 0.1):
        return simple(rng.choice(other or [1, 2, 3, 4, 5, 7]))
    return simple(rng.choice(simple_legal))


def neighbour(rng, action):
    data = action['action_data']
    axis = rng.choice(('x', 'y'))
    step = rng.choice((-1, 1)) if 0 < data[axis] < 63 else (1 if data[axis] == 0 else -1)
    return click(**dict(data, **{axis: data[axis] + step}))


def mixed_kinds(rng, n, weights=None):
    weights = weights or {'no_change': 4, 'final_change': 2, 'transient': 3, 'dispatch_failed': 2,
                          'outcome_unknown': 2}
    pool = [k for k, w in weights.items() for _ in range(w)]
    return [rng.choice(pool) for _ in range(n)]


def with_repeats(rng, legal, n, repeat=0.3):
    actions = []
    for _ in range(n):
        actions.append(copy.deepcopy(rng.choice(actions)) if actions and rng.random() < repeat else pick(rng, legal))
    return actions


def t_mixed(rng, legal):
    n = rng.randint(1, 6)
    return list(zip(with_repeats(rng, legal, n), mixed_kinds(rng, n)))


def t_near_miss(rng, legal):
    first = click(rng.randrange(64), rng.randrange(64))
    actions = [first]
    for _ in range(rng.randint(2, 4)):
        roll = rng.random()
        actions.append(copy.deepcopy(first) if roll < 0.35 else neighbour(rng, first) if roll < 0.8 else pick(rng, legal))
    return list(zip(actions, mixed_kinds(rng, len(actions), {'no_change': 3, 'final_change': 1, 'transient': 2,
                                                                'dispatch_failed': 1, 'outcome_unknown': 1})))


def t_transient(rng, legal):
    n = rng.randint(3, 5)
    kinds = mixed_kinds(rng, n, {'no_change': 3, 'transient': 3, 'final_change': 1, 'dispatch_failed': 1})
    for i in rng.sample(range(n), 2):
        kinds[i] = 'transient'
    return list(zip(with_repeats(rng, legal, n, 0.4), kinds))


def t_failed_unknown(rng, legal):
    n = rng.randint(3, 5)
    kinds = mixed_kinds(rng, n, {'no_change': 3, 'transient': 1, 'dispatch_failed': 2, 'outcome_unknown': 2})
    a, b = rng.sample(range(n), 2)
    kinds[a], kinds[b] = 'dispatch_failed', 'outcome_unknown'
    return list(zip(with_repeats(rng, legal, n, 0.45), kinds))


def t_same_frame_repeats(rng, legal):
    n = rng.randint(3, 6)
    kinds = mixed_kinds(rng, n, {'no_change': 5, 'transient': 2, 'dispatch_failed': 1, 'final_change': 1})
    return list(zip(with_repeats(rng, legal, n, 0.5), kinds))


def t_stale_unchanged(rng, legal):
    """Unchanged entries, then a final change or an unknown outcome, then more: only the later ones are on the
    frame that is still current."""
    before, after = rng.randint(1, 2), rng.randint(0, 2)
    unchanged = {'no_change': 3, 'transient': 2, 'dispatch_failed': 1}
    kinds = (mixed_kinds(rng, before, unchanged) + [rng.choice(('final_change', 'final_change', 'outcome_unknown'))]
             + mixed_kinds(rng, after, unchanged))
    return list(zip(with_repeats(rng, legal, len(kinds), 0.5), kinds))


def _boundary(rng, legal, kind):
    before, after = rng.randint(1, 4), rng.randint(0, 3)
    actions = with_repeats(rng, legal, before + 1 + after, 0.4)
    kinds = mixed_kinds(rng, before) + [kind] + mixed_kinds(rng, after)
    return list(zip(actions, kinds))


def t_level_boundary(rng, legal):
    return _boundary(rng, legal, 'level_up')


def t_reset_boundary(rng, legal):
    return _boundary(rng, legal, 'reset')


def t_long(rng, legal):
    n = rng.randint(6, 9)
    return list(zip(with_repeats(rng, legal, n, 0.35), mixed_kinds(rng, n)))


def t_empty(rng, legal):
    return []


TEMPLATES = (('mixed', t_mixed), ('near_miss_clicks', t_near_miss), ('transient', t_transient),
             ('failed_and_unknown', t_failed_unknown), ('same_frame_repeats', t_same_frame_repeats),
             ('stale_unchanged', t_stale_unchanged),
             ('level_boundary', t_level_boundary), ('reset_boundary', t_reset_boundary),
             ('long_with_omitted', t_long), ('empty_history', t_empty))
PARTITIONS = {'development': ('evidence-comprehension-v2-development', 3),
              'withheld': ('evidence-comprehension-v2-withheld', 12)}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def contexts(base, partition, seen):
    """Seeded trajectories for one partition: `per_template` instances of every template, alternating legal sets
    with and without ACTION6, starting at a random level. A draw whose observation equals one already generated
    (in any partition; `seen` holds their canonical forms and is updated) is redrawn, so no question is asked
    twice and no withheld question reappears in the development partition."""
    seed, per_template = PARTITIONS[partition]
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    result = []
    for name, template in TEMPLATES:
        for i in range(per_template):
            context_id = f'{partition[:3]}-{name}-{i:02d}'
            while True:
                legal = rng.choice(LEGAL_WITH_6 if len(result) % 2 == 0 else LEGAL_WITHOUT_6)
                trajectory = {'context_id': context_id, 'partition': partition, 'template': name,
                              'legal_actions': list(legal),
                              **run(rng, base, template(rng, legal), levels=rng.randrange(WIN_LEVELS - 2))}
                shown = _canonical(observation(trajectory))
                if shown not in seen:
                    break
            seen.add(shown)
            errors = continuity_errors(trajectory)
            if errors:
                raise ValueError(errors[0])
            result.append(trajectory)
    return result
