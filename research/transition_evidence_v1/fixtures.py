"""Deterministic synthetic transition fixtures (Workstream 3, transition_evidence_v1).

Each fixture is a sequence of raw transitions, the input format of transition.build. Expected values are derived
from the construction itself: every construction step records exactly which cells it changed. They are not taken
from the comparator; the comparator and the independent reference are both checked against them.

Frames are small synthetic grids with seeded colours. No action id has a game meaning, and no region is assumed
to be a counter or a board: the "counter-only" case recolours a small region at a seeded position. Construction
parameters and expected values are evaluator-only data, stored apart from the raw evidence.

Partitions: development and evaluation use different seeds, and a whole sequence always stays in one partition.
"""
import copy
import hashlib
import json
from pathlib import Path
import random

VERSION = 'transition_evidence_v1_fixtures'
OUTPUT = Path(__file__).with_name('fixtures.json')
PARTITIONS = {'development': ('ws3-transition-fixtures-development', 2),
              'evaluation': ('ws3-transition-fixtures-evaluation', 3)}
SOURCE = 'synthetic_fixture'


class Builder:
    """Builds one sequence, tracking the expected facts of each transition from construction."""

    def __init__(self, rng):
        self.rng = rng
        h, w = rng.randint(10, 16), rng.randint(10, 16)
        self.background = rng.randrange(16)
        self.frame = [[self.background] * w for _ in range(h)]
        for _ in range(rng.randint(2, 4)):  # decoration, so frames are not uniform
            self.frame = self.recolour(self.frame, *self.rect(1, 3), self.other(self.background))[0]
        self.levels, self.state = 0, 'NOT_FINISHED'
        self.raws, self.expected, self.construction = [], [], []

    def other(self, *avoid):
        return self.rng.choice([c for c in range(16) if c not in avoid])

    def rect(self, lo, hi):
        h, w = len(self.frame), len(self.frame[0])
        rh, rw = self.rng.randint(lo, hi), self.rng.randint(lo, hi)
        return self.rng.randrange(w - rw + 1), self.rng.randrange(h - rh + 1), rw, rh

    @staticmethod
    def recolour(grid, x0, y0, w, h, colour):
        out = copy.deepcopy(grid)
        changed = set()
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if out[y][x] != colour:
                    out[y][x] = colour
                    changed.add((x, y))
        return out, changed

    def changed_frame(self, lo=1, hi=4):
        """A frame differing from the current one in a known, non-empty set of cells."""
        while True:
            x, y, w, h = self.rect(lo, hi)
            out, cells = self.recolour(self.frame, x, y, w, h, self.other())
            if cells:
                return out, cells, {'op': 'recolour_rect', 'xywh': [x, y, w, h]}

    def action(self):
        if self.rng.random() < 0.4:
            return {'action_id': 6, 'action_data': {'x': self.rng.randrange(len(self.frame[0])),
                                                    'y': self.rng.randrange(len(self.frame))}}
        return {'action_id': self.rng.choice([1, 2, 3, 4, 5, 7]), 'action_data': {}}

    def observation(self, frame=None, **changes):
        value = {'frames': [copy.deepcopy(frame or self.frame)], 'levels_completed': self.levels, 'state': self.state,
                 'full_reset': False}
        value.update(changes)
        return value

    def add(self, outcome, expected, construction, proposal='same', before=None):
        dispatched = self.action()
        if proposal == 'same' and self.rng.random() < 0.15:
            proposal = None  # the producer did not retain the model proposal
        prop = (None if proposal is None else dispatched if proposal == 'same' else
                {'action_id': (dispatched['action_id'] % 7) + 1, 'action_data': {}})
        raw = {'identity': {'episode_id': None, 'action_index': len(self.raws)},
               'before': before or self.observation(), 'proposal': prop, 'dispatched': dispatched,
               'outcome': outcome, 'environment_source': SOURCE}
        self.raws.append(raw)
        base = {'dispatch': outcome['status'], 'events': ['none_reported'], 'progress': 'unknown'}
        self.expected.append({**base, **expected, 'proposal_equals_dispatched': None if prop is None else prop == dispatched})
        self.construction.append(construction)

    # ---- transition kinds; each updates the current frame exactly as the environment would

    def no_change(self, repeats=1):
        frames = [copy.deepcopy(self.frame) for _ in range(repeats)]
        self.add({'status': 'acknowledged', 'after': {**self.observation(), 'frames': frames}},
                 {'availability': 'complete', 'visual': 'no_observed_change', 'vs_pre': [0] * repeats,
                  'vs_previous': [0] * repeats, 'any_differs': False, 'final_equals': True},
                 {'kind': 'no_change', 'repeats': repeats})

    def final_change(self, kind='final_change', lo=1, hi=4):
        new, cells, op = self.changed_frame(lo, hi)
        self.add({'status': 'acknowledged', 'after': self.observation(new)},
                 {'availability': 'complete', 'visual': 'final_frame_differs', 'vs_pre': [len(cells)],
                  'vs_previous': [len(cells)], 'any_differs': True, 'final_equals': False},
                 {'kind': kind, **op})
        self.frame = new

    def transient(self):
        mid, cells, op = self.changed_frame()
        self.add({'status': 'acknowledged', 'after': {**self.observation(), 'frames': [mid, copy.deepcopy(self.frame)]}},
                 {'availability': 'complete', 'visual': 'changed_then_returned', 'vs_pre': [len(cells), 0],
                  'vs_previous': [len(cells), len(cells)], 'any_differs': True, 'final_equals': True},
                 {'kind': 'transient', **op})

    def move_block(self):
        h, w = len(self.frame), len(self.frame[0])
        bw, bh = self.rng.randint(1, 2), self.rng.randint(1, 2)
        colour = self.other(self.background)
        clean = [[self.background] * w for _ in range(h)]
        x0, y0 = self.rng.randrange(0, w - 2 * bw - 1), self.rng.randrange(h - bh + 1)
        start = self.recolour(clean, x0, y0, bw, bh, colour)[0]
        dx = bw + self.rng.randint(0, 1)
        end = self.recolour(clean, x0 + dx, y0, bw, bh, colour)[0]
        self.frame = start  # the board holds only the block, so the moved cells are known exactly
        self.add({'status': 'acknowledged', 'after': self.observation(end)},
                 {'availability': 'complete', 'visual': 'final_frame_differs', 'vs_pre': [2 * bw * bh],
                  'vs_previous': [2 * bw * bh], 'any_differs': True, 'final_equals': False},
                 {'kind': 'board_move_without_completion', 'block_xywh': [x0, y0, bw, bh], 'dx': dx},
                 before=self.observation(start))
        self.frame = end

    def level_completed(self):
        new = [[(v + 1) % 16 for v in row] for row in self.frame]
        n = len(self.frame) * len(self.frame[0])
        self.add({'status': 'acknowledged', 'after': self.observation(new, levels_completed=self.levels + 1)},
                 {'availability': 'complete', 'visual': 'final_frame_differs', 'vs_pre': [n], 'vs_previous': [n],
                  'any_differs': True, 'final_equals': False, 'events': ['level_completed'], 'progress': 'confirmed'},
                 {'kind': 'level_completion_receipt'})
        self.frame, self.levels = new, self.levels + 1

    def terminal(self, state):
        self.add({'status': 'acknowledged', 'after': self.observation(state=state)},
                 {'availability': 'complete', 'visual': 'no_observed_change', 'vs_pre': [0], 'vs_previous': [0],
                  'any_differs': False, 'final_equals': True, 'events': ['terminal_state'],
                  'progress': 'confirmed' if state == 'WIN' else 'unknown'},
                 {'kind': 'terminal', 'state': state})
        self.state = state

    def reset(self, level_start):
        n = sum(a != b for ra, rb in zip(self.frame, level_start) for a, b in zip(ra, rb))
        self.add({'status': 'acknowledged', 'after': self.observation(level_start, full_reset=True)},
                 {'availability': 'complete', 'visual': 'final_frame_differs' if n else 'no_observed_change',
                  'vs_pre': [n], 'vs_previous': [n], 'any_differs': bool(n), 'final_equals': not n,
                  'events': ['reset_acknowledged']},
                 {'kind': 'reset'})
        self.frame = copy.deepcopy(level_start)

    def failed(self):
        self.add({'status': 'failed', 'reason': 'request rejected before acknowledgement'},
                 {'availability': 'not_applicable', 'visual': 'indeterminate', 'vs_pre': [], 'vs_previous': [],
                  'any_differs': None, 'final_equals': None, 'events': ['not_observed']},
                 {'kind': 'failed_dispatch'})

    def unknown(self, changed_underneath):
        self.add({'status': 'outcome_unknown', 'reason': 'response timeout after send'},
                 {'availability': 'missing', 'visual': 'indeterminate', 'vs_pre': [], 'vs_previous': [],
                  'any_differs': None, 'final_equals': None, 'events': ['not_observed']},
                 {'kind': 'unknown_outcome', 'changed_underneath': changed_underneath})
        if changed_underneath:  # the action did execute; nobody saw it
            self.frame = self.changed_frame()[0]

    def no_frames(self):
        self.add({'status': 'acknowledged', 'after': {**self.observation(), 'frames': []}},
                 {'availability': 'missing', 'visual': 'indeterminate', 'vs_pre': [], 'vs_previous': [],
                  'any_differs': None, 'final_equals': None},
                 {'kind': 'acknowledged_without_frames'})

    def dimensions(self):
        cropped = [row[:] for row in self.frame[:-1]]
        self.add({'status': 'acknowledged', 'after': self.observation(cropped)},
                 {'availability': 'complete', 'visual': 'final_frame_differs', 'vs_pre': [None], 'vs_previous': [None],
                  'any_differs': True, 'final_equals': False},
                 {'kind': 'dimensions_differ', 'removed_rows': 1})
        self.frame = cropped

    def partial(self, with_change):
        broken = [row[:] for row in self.frame]
        broken[0] = broken[0][:-1]  # rows of different lengths: an invalid frame
        if with_change:
            mid, cells, op = self.changed_frame()
            frames = [mid, broken, copy.deepcopy(self.frame)]
            expected = {'vs_pre': [len(cells), 'invalid', 0], 'vs_previous': [len(cells), 'invalid', 'no_valid_previous'],
                        'any_differs': True, 'final_equals': True, 'visual': 'changed_then_returned'}
        else:
            op = {}
            frames = [broken, copy.deepcopy(self.frame)]
            expected = {'vs_pre': ['invalid', 0], 'vs_previous': ['invalid', 'no_valid_previous'],
                        'any_differs': None, 'final_equals': True, 'visual': 'indeterminate'}
        self.add({'status': 'acknowledged', 'after': {**self.observation(), 'frames': frames}},
                 {'availability': 'partial', **expected}, {'kind': 'partial_observation', **op})

    def animate_between(self):
        """An automatic change between two observations, with no action-specific evidence."""
        self.frame = self.changed_frame(1, 1)[0]


def sequence_expectations(builder):
    """Segment and continuity from construction knowledge (independent of transition.history)."""
    out, segment, prior = [], 0, None
    for raw, exp, cons in zip(builder.raws, builder.expected, builder.construction):
        if prior is not None and set(prior[1]['events']) & {'reset_acknowledged', 'level_completed', 'terminal_state'}:
            segment, prior = segment + 1, None
        if prior is None:
            continuity = 'first_in_segment'
        elif prior[1]['dispatch'] == 'outcome_unknown':
            continuity = 'gap_after_unknown_outcome'
        elif prior[1]['availability'] == 'missing':
            continuity = 'gap_after_missing_observation'
        else:
            last = prior[0]['before']['frames'][-1] if prior[1]['dispatch'] == 'failed' else \
                prior[0]['outcome']['after']['frames'][-1]
            continuity = 'matches_previous_final' if last == raw['before']['frames'][-1] else 'differs_from_previous_final'
        out.append({**exp, 'segment': segment, 'continuity': continuity})
        prior = (raw, exp)
    return out


FAMILIES = {
    'identical_frames': lambda b: b.no_change(repeats=b.rng.randint(1, 3)),
    'transient_change': lambda b: b.transient(),
    'final_frame_differs': lambda b: b.final_change(),
    'counter_only_change': lambda b: b.final_change('counter_only_change', 1, 2),
    'board_move_without_completion': lambda b: b.move_block(),
    'level_completion_receipt': lambda b: b.level_completed(),
    'failed_dispatch': lambda b: (b.failed(), b.no_change()),
    'unknown_outcome': lambda b: (b.unknown(changed_underneath=b.rng.random() < 0.5), b.no_change()),
    'acknowledged_without_frames': lambda b: (b.no_frames(), b.no_change()),
    'dimensions_differ': lambda b: b.dimensions(),
    'partial_observation': lambda b: (b.partial(True), b.partial(False)),
    'reset_boundary': lambda b: _reset(b),
    'delayed_visible_event': lambda b: (b.no_change(), b.no_change(), b.no_change(), b.final_change()),
    'automatic_animation': lambda b: (b.no_change(), b.animate_between(), b.no_change(), b.animate_between(), b.no_change()),
    'terminal_game_over': lambda b: b.terminal('GAME_OVER'),
    'terminal_win': lambda b: b.terminal('WIN'),
    'proposal_differs_from_dispatch': lambda b: b.add(
        {'status': 'acknowledged', 'after': {**b.observation()}},
        {'availability': 'complete', 'visual': 'no_observed_change', 'vs_pre': [0], 'vs_previous': [0],
         'any_differs': False, 'final_equals': True}, {'kind': 'fallback_dispatch'}, proposal='differs'),
    'mixed_history': lambda b: (b.transient(), b.failed(), b.no_change(), b.unknown(False), b.final_change(),
                                b.no_frames(), b.no_change(), b.level_completed(), b.no_change()),
}


def _reset(b):
    start = copy.deepcopy(b.frame)
    b.final_change()
    b.no_change()
    b.reset(start)
    b.no_change()


def generate():
    fixtures, evaluator_only = [], {}
    for partition, (seed, count) in PARTITIONS.items():
        rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
        for family, make in FAMILIES.items():
            for i in range(count):
                fid = f'{partition[:3]}-{family}-{i}'
                b = Builder(random.Random(rng.random()))
                make(b)
                opaque = 'fx-' + hashlib.sha256(fid.encode()).hexdigest()[:12]  # no family label in raw evidence
                for n, raw in enumerate(b.raws):
                    raw['identity'] = {'episode_id': opaque, 'action_index': n}
                fixtures.append({'id': fid, 'family': family, 'partition': partition, 'raws': b.raws})
                evaluator_only[fid] = {'construction': b.construction, 'expected': sequence_expectations(b)}
    return {'version': VERSION, 'fixtures': fixtures, 'evaluator_only': evaluator_only}


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    raw = encode(generate())
    if parser.parse_args().check:
        if OUTPUT.read_bytes() != raw:
            raise SystemExit('frozen fixtures differ from a fresh generation')
        print('fixtures match:', hashlib.sha256(raw).hexdigest())
    else:
        OUTPUT.write_bytes(raw)
        print('wrote', OUTPUT.name, hashlib.sha256(raw).hexdigest(), len(raw))
