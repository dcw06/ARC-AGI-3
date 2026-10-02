"""Synthetic diagnostic fixtures for progress_subgoal_v1 (DRAFT; development material only).

Each fixture is a short sequence of raw transitions in the transition_evidence_v1 input format (transition.build),
optionally with a subgoal verification record adopted at its start. Frames are small synthetic grids; no action id
or rectangle has a game meaning. Three disjoint rectangles R1..R3 are named only by coordinates in questions.

Expected facts are kept per transition from the construction itself (which rectangles it painted, in which returned
frame, whether the subgoal target colour is in place, what the environment reported). They are not computed from
frames. Construction knowledge that is not observable (e.g. an unobserved action that changed the game underneath)
is stored under `unobservable` and never enters a key (tested by flipping it).

Families (spec Milestones A-C):
- progress interpretation: counter-only change; animation and reversion; object movement without known usefulness;
  explicit completion; failure and unknown outcomes; multiple plausible explanations for one transition;
- causal restraint: possibly autonomous change; simultaneous changes; repeated intervention; insufficient evidence;
- subgoal verification: achieved without progress; achieved then a level completes; invalidated; budget exhausted;
  pending; unobserved.

Partitions: `development` (small, for prompt and rehearsal work) and `coverage_dryrun` (a larger development-only
build used to check that the generator can meet the coverage floors; it is never to be asked to a model). The
evaluation partition does not exist yet: its seed is to be drawn and recorded only at the protocol freeze.
"""
import copy
import hashlib
import random

from research.progress_subgoal_v1 import subgoal as S

VERSION = 'progress_subgoal_v1_fixtures'
PARTITIONS = {'development': ('progress-subgoal-v1-development', 2),
              'coverage_dryrun': ('progress-subgoal-v1-coverage-dryrun', 30)}
SOURCE = 'synthetic_fixture'
REGIONS = ('R1', 'R2', 'R3')
REASON = 'A uniformly coloured target rectangle might be part of a level goal (untested).'


def recolour(grid, xywh, colour):
    out = copy.deepcopy(grid)
    x0, y0, w, h = xywh
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            out[y][x] = colour
    return out


class Builder:
    def __init__(self, rng):
        self.rng = rng
        h, w = rng.randint(8, 11), rng.randint(8, 11)
        bg = rng.randrange(16)
        self.frame = [[bg] * w for _ in range(h)]
        for _ in range(rng.randint(3, 6)):
            self.frame[rng.randrange(h)][rng.randrange(w)] = rng.choice([c for c in range(16) if c != bg])
        self.regions = self._allocate(h, w)
        ids = rng.sample([1, 2, 3, 4, 5, 6, 7], 3)
        self.A, self.B, self.C = (self._action(i, h, w) for i in ids)
        self.paint = {r: None for r in REGIONS}  # uniform colour the construction put in each rectangle
        self.levels, self.state = 0, 'NOT_FINISHED'
        self.raws, self.facts = [], []
        self.subgoal, self.target = None, None
        self.auto_since = set()  # rectangles changed between observations since the last transition
        self.leaves_observed = True  # whether the last transition left an observed frame

    def _action(self, action_id, h, w):
        if action_id == 6:
            return {'action_id': 6, 'action_data': {'x': self.rng.randrange(w), 'y': self.rng.randrange(h)}}
        return {'action_id': action_id, 'action_data': {}}

    def _allocate(self, h, w):
        while True:
            rects = []
            for name in REGIONS:
                rw = self.rng.randint(2, 3) if name == 'R1' else self.rng.randint(1, 3)
                rh = self.rng.randint(1, 2)
                rects.append([self.rng.randrange(w - rw + 1), self.rng.randrange(h - rh + 1), rw, rh])
            if all(not _overlap(a, b) for i, a in enumerate(rects) for b in rects[i + 1:]):
                return dict(zip(REGIONS, rects))

    def fresh(self, region, avoid=()):
        """A colour absent from every cell of the rectangle (so painting changes every cell), not in `avoid`."""
        x0, y0, w, h = self.regions[region]
        present = {self.frame[y][x] for y in range(y0, y0 + h) for x in range(x0, x0 + w)}
        return self.rng.choice([c for c in range(16) if c not in present and c not in avoid])

    def _avoid(self, region):
        return (self.target,) if self.target is not None and region == 'R1' else ()

    def colours(self, regions, hit_target=False):
        return {r: (self.target if hit_target and r == 'R1' else self.fresh(r, self._avoid(r))) for r in regions}

    def setup_block(self):
        """Before any transition: a one-cell block at R1's top-left, distinct from its right neighbour."""
        x, y = self.regions['R1'][:2]
        self.frame[y][x] = self.rng.choice([c for c in range(16) if c != self.frame[y][x + 1]
                                            and c != self.target])

    def adopt(self, budget, invalidation=('attempts',)):
        target = self.fresh('R1')
        self.target = target
        inv = []
        if 'attempts' in invalidation:
            inv.append({'kind': 'no_region_change_after_attempts', 'action': copy.deepcopy(self.A),
                        'region_xywh': list(self.regions['R1']), 'attempts': 2,
                        'text': 'two observed attempts of this action each leave the target rectangle unchanged'})
        if 'game_over' in invalidation:
            inv.append({'kind': 'state_reported', 'state': 'GAME_OVER', 'text': 'the environment reports GAME_OVER'})
        self.subgoal = S.subgoal_record(self.regions['R1'], target, budget, inv, REASON)

    def _met(self):
        return self.target is not None and self.paint['R1'] == self.target

    def _observation(self, frame, **changes):
        value = {'frames': [copy.deepcopy(frame)], 'levels_completed': self.levels, 'state': self.state,
                 'full_reset': False}
        value.update(changes)
        return value

    def _add(self, action, outcome, fact, leaves_observed, unobservable=None):
        n = len(self.raws)
        gap = ({r: 'cannot_tell' for r in REGIONS} if n and not self.leaves_observed else
               {r: ('yes' if r in self.auto_since else 'no') for r in REGIONS} if n else None)
        self.raws.append({'identity': {'episode_id': None, 'action_index': n}, 'before': self._before,
                          'proposal': None, 'dispatched': copy.deepcopy(action), 'outcome': outcome,
                          'environment_source': SOURCE})
        self.facts.append({'dispatched': copy.deepcopy(action), 'gap': gap, 'target_met_before': self._met_before,
                           'progress': 'unknown', 'state_after': None, 'target_met_final': None,
                           'unobserved_final': False, **fact, 'unobservable': unobservable or {}})
        self.auto_since = set()
        self.leaves_observed = leaves_observed

    def _start(self):
        self._before = self._observation(self.frame)
        self._met_before = self._met()

    # ---- transitions; each updates the construction state exactly as the environment would

    def act(self, action, paint=(), hit_target=False, transient=False, levels=0, state=None, move=False):
        self._start()
        pre = copy.deepcopy(self.frame)
        new, changed = copy.deepcopy(pre), set()
        new_paint = dict(self.paint)
        for region, colour in self.colours(paint, hit_target).items():
            new = recolour(new, self.regions[region], colour)
            new_paint[region] = colour
            changed.add(region)
        if move:
            x, y = self.regions['R1'][:2]
            new[y][x], new[y][x + 1] = new[y][x + 1], new[y][x]
            new_paint['R1'] = None
            changed.add('R1')
        if not transient:
            self.frame, self.paint = new, new_paint
        self.levels += levels
        self.state = state or self.state
        frames = [new, pre] if transient else [new]
        visual = ('no_observed_change' if not changed else 'changed_then_returned' if transient else 'final_frame_differs')
        after = {**self._observation(self.frame), 'frames': copy.deepcopy(frames)}
        self._add(action, {'status': 'acknowledged', 'after': after},
                  {'dispatch': 'acknowledged', 'visual': visual,
                   'region': {r: 'yes' if r in changed else 'no' for r in REGIONS},
                   'progress': 'confirmed' if levels > 0 or state == 'WIN' else 'unknown', 'state_after': self.state,
                   'target_met_final': self._met()}, True)

    def failed(self, action):
        self._start()
        self._add(action, {'status': 'failed', 'reason': 'request rejected before acknowledgement'},
                  {'dispatch': 'failed', 'visual': 'indeterminate', 'region': {r: 'cannot_tell' for r in REGIONS}}, True)

    def unknown(self, action, changed_underneath):
        self._start()
        self._add(action, {'status': 'outcome_unknown', 'reason': 'response timeout after send'},
                  {'dispatch': 'outcome_unknown', 'visual': 'indeterminate', 'unobserved_final': True,
                   'region': {r: 'cannot_tell' for r in REGIONS}}, False, {'changed_underneath': changed_underneath})
        if changed_underneath:  # the action executed and nobody saw it
            colour = self.fresh('R1', self._avoid('R1'))
            self.frame = recolour(self.frame, self.regions['R1'], colour)
            self.paint['R1'] = colour

    def missing(self, action):
        self._start()
        self._add(action, {'status': 'acknowledged', 'after': {**self._observation(self.frame), 'frames': []}},
                  {'dispatch': 'acknowledged', 'visual': 'indeterminate', 'unobserved_final': True,
                   'region': {r: 'cannot_tell' for r in REGIONS}}, False)

    def partial(self, action, paint=(), hit_target=False):
        """With paint: [changed frame, invalid frame] (no valid final frame). Without: [invalid frame, same frame]."""
        self._start()
        broken = [row[:] for row in self.frame]
        broken[0] = broken[0][:-1]  # rows of different lengths: an invalid frame
        if paint:
            for region, colour in self.colours(paint, hit_target).items():
                self.frame = recolour(self.frame, self.regions[region], colour)
                self.paint[region] = colour
            frames = [copy.deepcopy(self.frame), broken]
            fact = {'region': {r: 'yes' if r in paint else 'cannot_tell' for r in REGIONS}, 'unobserved_final': True}
        else:
            frames = [broken, copy.deepcopy(self.frame)]
            fact = {'region': {r: 'cannot_tell' for r in REGIONS}, 'target_met_final': self._met()}
        self._add(action, {'status': 'acknowledged', 'after': {**self._observation(self.frame), 'frames': frames}},
                  {'dispatch': 'acknowledged', 'visual': 'indeterminate', **fact}, bool(not paint))

    def autonomous(self, regions):
        """A change between two observations, with no action-specific evidence."""
        for region, colour in self.colours(regions).items():
            self.frame = recolour(self.frame, self.regions[region], colour)
            self.paint[region] = colour
            self.auto_since.add(region)


def _overlap(a, b):
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])


# ------------------------------------------------------------------ families: name -> (variants, recipe(builder, v))

def _counter_only(b, v):
    b.act(b.B)
    b.act(b.A, ['R1'] if v == 0 else ['R3'])


def _animation_reversion(b, v):
    b.act(b.B)
    if v < 2:  # the focus transition changes and returns
        b.act(b.A, ['R1'] if v == 0 else ['R1', 'R2'], transient=True)
    else:  # a change between observations, then a transition with no observed change
        b.autonomous(['R1'])
        b.act(b.A)


def _object_move(b, v):
    b.setup_block()
    b.act(b.B)
    b.act(b.A, move=True)


def _explicit_completion(b, v):
    b.act(b.B)
    if v == 0:
        b.act(b.A, ['R1'], levels=1)
    elif v == 1:  # progress without visible change
        b.act(b.A, levels=1)
    elif v == 2:
        b.act(b.A, ['R2'], state='WIN')
    else:  # a win without visible change
        b.act(b.A, state='WIN')


def _failure_unknown(b, v):
    b.act(b.B, ['R2'])
    [lambda: b.failed(b.A), lambda: b.unknown(b.A, b.rng.random() < 0.5), lambda: b.missing(b.A),
     lambda: b.partial(b.A, ['R1']), lambda: b.partial(b.A)][v]()


def _multiple_explanations(b, v):
    b.act(b.B)
    b.autonomous(['R1'])
    b.act(b.A, ['R1', 'R2'], levels=1 if v == 1 else 0)


def _possibly_autonomous(b, v):
    b.act(b.B)
    if v == 0:
        b.autonomous(['R1'])
        b.act(b.B)
    b.act(b.A, ['R1'])


def _simultaneous(b, v):
    b.act(b.B)
    b.act(b.A, ['R1', 'R2'] if v == 0 else ['R1', 'R2', 'R3'])


def _repeated_intervention(b, v):
    if v == 0:  # consistent trials and unchanged controls
        b.act(b.A, ['R1']), b.act(b.B), b.act(b.A, ['R1']), b.act(b.B), b.act(b.A, ['R1'])
    elif v == 1:  # consistent trials changing two rectangles at once
        b.act(b.A, ['R1', 'R2']), b.act(b.B), b.act(b.A, ['R1', 'R2'])
    elif v == 2:  # a control changes another rectangle only
        b.act(b.A, ['R1']), b.act(b.B, ['R2']), b.act(b.A, ['R1'])
    elif v == 3:  # one trial leaves the rectangle unchanged
        b.act(b.A, ['R1']), b.act(b.B), b.act(b.A), b.act(b.B), b.act(b.A, ['R1'])
    else:  # a control changes it too
        b.act(b.A, ['R1']), b.act(b.B, ['R1']), b.act(b.A, ['R1'])


def _insufficient(b, v):
    if v == 0:
        b.act(b.A, ['R1'])
    elif v == 1:  # repeated, but no control
        b.act(b.A, ['R1']), b.act(b.A, ['R1'])
    elif v == 2:  # later trials unobserved
        b.act(b.A, ['R1']), b.act(b.B), b.unknown(b.A, False), b.failed(b.A)
    else:
        b.act(b.A, ['R1']), b.act(b.B), b.missing(b.A)


def _sg_achieved(b, v):
    b.adopt(5)
    b.act(b.B)
    if v == 1:  # a transient appearance first; only a final frame or a frame before counts
        b.act(b.A, ['R1'], hit_target=True, transient=True)
    b.act(b.A, ['R1'], hit_target=True)


def _sg_achieved_then_level(b, v):
    b.adopt(5)
    b.act(b.A, ['R1'], hit_target=True)
    b.act(b.B, ['R2'], levels=1)


def _sg_invalidated(b, v):
    if v == 0:
        b.adopt(6)
        b.act(b.A), b.act(b.B, ['R2']), b.act(b.A)
    else:
        b.adopt(6, ('attempts', 'game_over'))
        b.act(b.B), b.act(b.A, ['R2']), b.act(b.C, state='GAME_OVER')


def _sg_budget(b, v):
    b.adopt(3)
    b.act(b.B, ['R2']), b.act(b.C, ['R3']), b.act(b.A, ['R1'] if v == 0 else ['R3'])


def _sg_pending(b, v):
    b.adopt(6)
    if v == 0:
        b.act(b.B), b.act(b.A, ['R2'])
    elif v == 1:  # the target appears only in an intermediate frame
        b.act(b.A, ['R1'], hit_target=True, transient=True), b.act(b.B)
    else:
        b.act(b.B), b.act(b.A, ['R1'], hit_target=True, transient=True)


def _sg_unobserved(b, v):
    b.adopt(6)
    b.act(b.B)
    [lambda: b.unknown(b.A, b.rng.random() < 0.5), lambda: b.missing(b.A),
     lambda: b.partial(b.A, ['R1'], hit_target=True)][v]()


FAMILIES = {
    'counter_only_change': (2, _counter_only),
    'animation_and_reversion': (3, _animation_reversion),
    'object_move_without_known_usefulness': (1, _object_move),
    'explicit_completion': (4, _explicit_completion),
    'failure_and_unknown_outcome': (5, _failure_unknown),
    'multiple_explanations': (2, _multiple_explanations),
    'possibly_autonomous_change': (2, _possibly_autonomous),
    'simultaneous_changes': (2, _simultaneous),
    'repeated_intervention': (5, _repeated_intervention),
    'insufficient_evidence': (4, _insufficient),
    'subgoal_achieved_without_progress': (2, _sg_achieved),
    'subgoal_achieved_then_level': (1, _sg_achieved_then_level),
    'subgoal_invalidated': (2, _sg_invalidated),
    'subgoal_budget_exhausted': (2, _sg_budget),
    'subgoal_pending': (3, _sg_pending),
    'subgoal_unobserved': (3, _sg_unobserved),
}
# Families generated more often, so that rare keys and classes reach the coverage floors.
WEIGHT = {'repeated_intervention': 2, 'animation_and_reversion': 2, 'explicit_completion': 2, 'subgoal_unobserved': 2}


def generate(partition, seed=None, count=None):
    """Fixtures of one partition. `seed`/`count` override the table (used only for the evaluation build at freeze)."""
    default_seed, default_count = PARTITIONS.get(partition, (None, None))
    seed, count = seed or default_seed, count or default_count
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    out = []
    for family, (variants, recipe) in FAMILIES.items():
        for i in range(count * WEIGHT.get(family, 1)):
            b = Builder(random.Random(rng.random()))
            recipe(b, i % variants)
            opaque = 'ps-' + hashlib.sha256(f'{seed}:{family}:{i}'.encode()).hexdigest()[:12]
            for n, raw in enumerate(b.raws):
                raw['identity'] = {'episode_id': opaque, 'action_index': n}
            out.append({'id': opaque, 'family': family, 'variant': i % variants, 'partition': partition,
                        'raws': b.raws, 'subgoal': b.subgoal, 'regions': b.regions,
                        'actions': {'A': b.A, 'B': b.B, 'C': b.C},
                        'evaluator_only': {'facts': b.facts}})
    return out
