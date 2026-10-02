"""Labelled synthetic trajectories for the stagnation detector benchmark (Track 3, stagnation_supervision_v1).

Each fixture is one scripted trajectory in a tiny seeded grid world, emitted as raw transitions in the
transition_evidence_v1 input format (consumed read-only). Labels come from the construction, which knows the hidden
state; the detector never sees them.

Labelling rule (one rule for every family). A step is `stagnant` when it repeats a (hidden state, action) whose
outcome the agent has already observed and the construction guarantees that repeating it moves nothing towards
progress. Every other step is `productive`: a first probe (even with no visible effect), a move into a new state,
a repetition that advances a hidden quantity (a charge, an incremental fill, a delayed effect), backtracking the
layout requires, or replaying a route after a reset. Synthetic only: nothing here describes a real game.

Positive families contain stagnant steps. Hard negatives are productive throughout but look like loops to a naive
detector. Some pairs are ambiguous by design (`counter_only_repeat` vs `incremental_click_effect` and
`counter_with_static_playfield`; `repeated_click_no_effect` vs `delayed_effect`): the observations up to the payoff
are the same kind, so any threshold trades recall against false interventions. That ambiguity is the point.

Partitions: development and evaluation use different seeds; a whole trajectory always stays in one partition.
Thresholds are chosen on development only (thresholds.py).
"""
import copy
import hashlib
import json
import random

VERSION = 'stagnation_supervision_v1_fixtures'
PARTITIONS = {'development': ('ws3-stagnation-fixtures-development', 4),
              'evaluation': ('ws3-stagnation-fixtures-evaluation', 4)}
SOURCE = 'synthetic_fixture'
PRODUCTIVE, STAGNANT = 'productive', 'stagnant'
RESET = {'action_id': 0, 'action_data': {}}
INTERACT = {'action_id': 5, 'action_data': {}}


class World:
    """A seeded grid with an optional 1x1 avatar, toggled marks and up to two bars. Rows 0 and h-1 hold bars; the
    avatar stays in rows 2..h-3. Action ids 1-4 move (mapping seeded per fixture), 5 interacts, 6 clicks, 0 resets."""

    def __init__(self, rng, step_counter=False):
        self.rng = rng
        self.h, self.w = rng.randint(10, 13), rng.randint(10, 13)
        self.bg = rng.randrange(16)
        (self.avatar_colour, self.mark_colour, self.counter_colour, self.charge_colour,
         self.effect_colour, deco) = rng.sample([c for c in range(16) if c != self.bg], 6)
        self.base = [[self.bg] * self.w for _ in range(self.h)]
        for _ in range(rng.randint(1, 3)):  # static decoration, so frames are not uniform
            x, y = rng.randrange(self.w - 1), rng.randrange(2, self.h - 3)
            self.base[y][x] = deco
        self.marks = {}
        self.avatar = None
        self.visited = set()
        self.bars = {}  # name -> [cells, fill]
        if step_counter:
            self.add_bar('counter', 0, self.w - self.rng.randint(0, 2))
        self.moves = dict(zip(rng.sample([1, 2, 3, 4], 4), [(0, -1), (0, 1), (-1, 0), (1, 0)]))
        self.action_for = {d: a for a, d in self.moves.items()}
        self.levels = 0
        self.predict = rng.random() < 0.5  # half the fixtures carry an agent-side prediction stream
        self.raws, self.labels, self.notes, self.predictions = [], [], [], []

    # ---- layout

    def add_bar(self, name, row, length):
        start = self.rng.randrange(self.w - length + 1)
        self.bars[name] = [[(x, row) for x in range(start, start + length)], 0]

    def place(self, x, y):
        self.avatar = [x, y]
        self.visited.add((x, y))

    def place_with_room(self, room):
        """Place the avatar so it can move `room[d]` steps in each direction d (as far as the board allows)."""
        lo_x, hi_x = room.get((-1, 0), 0), self.w - 1 - room.get((1, 0), 0)
        lo_y, hi_y = 2 + room.get((0, -1), 0), self.h - 3 - room.get((0, 1), 0)
        self.place(self.rng.randint(lo_x, hi_x), self.rng.randint(lo_y, hi_y))

    def inside(self, x, y):
        return 0 <= x < self.w and 2 <= y <= self.h - 3

    def render(self):
        grid = copy.deepcopy(self.base)
        for (x, y), colour in self.marks.items():
            grid[y][x] = colour
        for name, (cells, fill) in self.bars.items():
            colour = self.counter_colour if name == 'counter' else self.charge_colour
            for x, y in cells[:fill]:
                grid[y][x] = colour
        if self.avatar:
            grid[self.avatar[1]][self.avatar[0]] = self.avatar_colour
        return grid

    def fill(self, name):
        cells = self.bars[name][0]
        self.bars[name][1] = (self.bars[name][1] + 1) % (len(cells) + 1)  # wraps like a display

    # ---- actions

    def click_action(self, cell=None):
        x, y = cell or (self.rng.randrange(self.w), self.rng.randrange(2, self.h - 2))
        return {'action_id': 6, 'action_data': {'x': x, 'y': y}}

    def move(self, action):
        dx, dy = self.moves[action['action_id']]
        x, y = self.avatar[0] + dx, self.avatar[1] + dy
        if self.inside(x, y):
            self.avatar = [x, y]
            self.visited.add((x, y))

    def default_effect(self, action):
        if action['action_id'] in self.moves and self.avatar:
            self.move(action)

    def observation(self, frame, **changes):
        value = {'frames': [frame], 'levels_completed': self.levels, 'state': 'NOT_FINISHED', 'full_reset': False}
        value.update(changes)
        return value

    def act(self, action, label, note, effect=None, outcome='acknowledged', level_up=False, reset_to=None):
        pre = self.render()
        raw = {'identity': {'episode_id': None, 'action_index': len(self.raws)}, 'before': self.observation(pre),
               'proposal': copy.deepcopy(action), 'dispatched': copy.deepcopy(action), 'environment_source': SOURCE}
        if outcome == 'failed':
            raw['outcome'] = {'status': 'failed', 'reason': 'request rejected before acknowledgement'}
        else:
            if reset_to is not None:
                reset_to()
            elif effect is None:
                self.default_effect(action)
            elif effect is not False:  # False: the action has no effect on the world
                effect(action)
            if 'counter' in self.bars:
                self.fill('counter')
            if outcome == 'outcome_unknown':  # the action executed; nobody saw the result
                raw['outcome'] = {'status': 'outcome_unknown', 'reason': 'response timeout after send'}
            else:
                self.levels += int(level_up)
                raw['outcome'] = {'status': 'acknowledged',
                                  'after': self.observation(self.render(), levels_completed=self.levels,
                                                            full_reset=reset_to is not None)}
        if self.predict:
            self.predictions.append({'action_index': len(self.raws), 'expects_change': True})
        self.raws.append(raw)
        self.labels.append(label)
        self.notes.append(note)

    def explore(self, n, note='explore'):
        """Up to n self-avoiding moves into unvisited cells; every one is productive."""
        done = 0
        for _ in range(n):
            options = [a for a, (dx, dy) in sorted(self.moves.items())
                       if self.inside(self.avatar[0] + dx, self.avatar[1] + dy)
                       and (self.avatar[0] + dx, self.avatar[1] + dy) not in self.visited]
            if not options:
                break
            self.act({'action_id': self.rng.choice(options), 'action_data': {}}, PRODUCTIVE, note)
            done += 1
        return done

    def toggle(self, cell):
        def effect(_):
            if cell in self.marks:
                del self.marks[cell]
            else:
                self.marks[cell] = self.mark_colour
        return effect

    def free_cell(self):
        while True:
            cell = (self.rng.randrange(self.w), self.rng.randrange(2, self.h - 2))
            if cell not in self.marks and list(cell) != self.avatar:
                return cell

    def region_change(self, _):
        x, y = self.rng.randrange(self.w - 3), self.rng.randrange(2, self.h - 5)
        for dy in range(3):
            for dx in range(3):
                self.marks[(x + dx, y + dy)] = self.effect_colour


def label_repeats(i):
    return PRODUCTIVE if i == 0 else STAGNANT


# ---- positive families (contain stagnant steps)

def repeated_click_no_effect(w):
    w.place_with_room({})
    w.explore(w.rng.randint(0, 4))
    action = w.click_action()
    for i in range(w.rng.randint(6, 10)):
        w.act(action, label_repeats(i), 'click_no_effect', effect=False)


def rotating_clicks_no_effect(w):
    cells, n = [], w.rng.randint(2, 4)
    while len(cells) < n:
        cell = w.free_cell()
        if cell not in cells:  # distinct positions, so the first round contains no repeat
            cells.append(cell)
    actions = [w.click_action(cell) for cell in cells]
    for r in range(w.rng.randint(3, 4)):
        for action in actions:
            w.act(action, PRODUCTIVE if r == 0 else STAGNANT, 'rotating_click_no_effect', effect=False)


def toggle_cycle(w, n, note='toggle_cycle'):
    """The same click toggles one cell on and off: states alternate. The first two steps are new pairs."""
    cell = w.free_cell()
    action = w.click_action(cell)
    for i in range(n):
        w.act(action, PRODUCTIVE if i < 2 else STAGNANT, note, effect=w.toggle(cell))


def toggle_two_cycle(w):
    w.place_with_room({})
    w.explore(w.rng.randint(0, 3))
    toggle_cycle(w, w.rng.randint(8, 12))


def move_square_cycle(w):
    side = w.rng.randint(1, 2)
    w.place_with_room({(1, 0): side, (0, 1): side})
    path = [(1, 0)] * side + [(0, 1)] * side + [(-1, 0)] * side + [(0, -1)] * side
    for lap in range(w.rng.randint(3, 4)):
        for d in path:
            w.act({'action_id': w.action_for[d], 'action_data': {}}, PRODUCTIVE if lap == 0 else STAGNANT, 'square_cycle')


def counter_only_repeat(w):
    """Repeated click whose only visible effect is a per-action step counter (cf. the s5i5 observation)."""
    w.place_with_room({})
    w.explore(w.rng.randint(0, 3))
    action = w.click_action()
    for i in range(w.rng.randint(6, 10)):
        w.act(action, label_repeats(i), 'click_counter_only', effect=False)


def loop_under_step_counter(w):
    w.place_with_room({})
    toggle_cycle(w, w.rng.randint(8, 12), 'toggle_cycle_with_counter')


def walk_into_wall(w):
    d = w.rng.choice(sorted(w.moves.values()))
    a = w.rng.randint(2, 5)
    w.place_with_room({d: a})
    # move the start so exactly `a` steps reach the board edge in direction d
    while w.inside(w.avatar[0] + d[0] * (a + 1), w.avatar[1] + d[1] * (a + 1)):
        w.avatar = [w.avatar[0] + d[0], w.avatar[1] + d[1]]
    w.visited = {tuple(w.avatar)}
    action = {'action_id': w.action_for[d], 'action_data': {}}
    for _ in range(a):
        w.act(action, PRODUCTIVE, 'walk')
    for i in range(w.rng.randint(4, 8)):
        w.act(action, label_repeats(i), 'push_at_edge')


def no_effect_with_dispatch_gaps(w):
    w.place_with_room({})
    w.explore(w.rng.randint(0, 2))
    action = w.click_action()
    n = w.rng.randint(7, 11)
    gaps = {w.rng.randrange(1, n): 'failed', w.rng.randrange(1, n): 'failed', w.rng.randrange(1, n): 'outcome_unknown'}
    for i in range(n):
        if i in gaps:
            w.act(action, STAGNANT, 'gap_' + gaps[i], effect=False, outcome=gaps[i])
        w.act(action, label_repeats(i), 'click_no_effect', effect=False)


def loop_then_escape(w):
    w.place_with_room({})
    toggle_cycle(w, w.rng.randint(6, 9))
    w.explore(w.rng.randint(4, 7), 'escape')


def loop_escape_into_loop(w):
    w.place_with_room({})
    toggle_cycle(w, w.rng.randint(5, 7))
    action = w.click_action()
    for i in range(w.rng.randint(6, 8)):
        w.act(action, label_repeats(i), 'second_loop_click_no_effect', effect=False)


# ---- hard negatives (productive throughout)

def straight_line(w, n_lo, n_hi):
    d = w.rng.choice(sorted(w.moves.values()))
    extent = (w.w if d[1] == 0 else w.h - 4) - 1
    n = w.rng.randint(min(n_lo, extent), min(n_hi, extent))
    w.place_with_room({d: n})
    return {'action_id': w.action_for[d], 'action_data': {}}, n


def move_to_destination(w):
    action, n = straight_line(w, 5, 10)
    finish = w.rng.random() < 0.5
    for i in range(n):
        w.act(action, PRODUCTIVE, 'move_towards_destination', level_up=finish and i == n - 1)


def incremental_click_effect(w):
    """The same click fills one more cell of a bar each time: an incremental effect that advances."""
    w.place_with_room({})
    n = w.rng.randint(5, 9)
    w.add_bar('charge', w.h - 1, n)
    action = w.click_action()
    finish = w.rng.random() < 0.5
    for i in range(n):
        w.act(action, PRODUCTIVE, 'incremental_fill', effect=lambda _: w.fill('charge'), level_up=finish and i == n - 1)


def varied_click_painting(w):
    w.place_with_room({})
    for _ in range(w.rng.randint(8, 14)):
        cell = w.free_cell()
        w.act(w.click_action(cell), PRODUCTIVE, 'paint',
              effect=lambda _, c=cell: w.marks.__setitem__(c, w.mark_colour))


def backtracking_required(w):
    dirs = sorted(w.moves.values())
    a_dir = w.rng.choice(dirs)
    b_dir = w.rng.choice([d for d in dirs if d[0] * a_dir[0] + d[1] * a_dir[1] == 0])
    a, b = w.rng.randint(3, 4), w.rng.randint(3, 4)
    w.place_with_room({a_dir: a, b_dir: b})
    back = (-a_dir[0], -a_dir[1])
    for d, n, note in ((a_dir, a, 'into_dead_end'), (back, a, 'backtrack'), (b_dir, b, 'new_route')):
        for _ in range(n):
            w.act({'action_id': w.action_for[d], 'action_data': {}}, PRODUCTIVE, note)


def delayed_effect(w):
    """The same action shows nothing for d steps (a hidden charge advances), then the playfield changes."""
    w.place_with_room({})
    action = INTERACT if w.rng.random() < 0.5 else w.click_action()
    d = w.rng.randint(3, 7)
    finish = w.rng.random() < 0.5
    for _ in range(d):
        w.act(action, PRODUCTIVE, 'hidden_charge', effect=False)
    w.act(action, PRODUCTIVE, 'delayed_release', effect=w.region_change, level_up=finish)


def counter_with_static_playfield(w):
    """A visible charge counter fills while the playfield stays unchanged, then the playfield changes."""
    w.place_with_room({})
    n = w.rng.randint(4, 8)
    w.add_bar('charge', 0, n + 1)
    action = INTERACT if w.rng.random() < 0.5 else w.click_action()
    finish = w.rng.random() < 0.5
    for _ in range(n):
        w.act(action, PRODUCTIVE, 'charge_counter', effect=lambda _: w.fill('charge'))
    w.act(action, PRODUCTIVE, 'charged_release', effect=w.region_change, level_up=finish)


def productive_exploration_no_completion(w):
    """Mostly new states, plus single no-effect probes; no progress signal within the trajectory."""
    w.place_with_room({})
    for _ in range(w.rng.randint(18, 28)):
        if w.rng.random() < 0.8 and w.explore(1):
            continue
        w.act(w.click_action(w.free_cell()), PRODUCTIVE, 'probe_once', effect=False)


def dispatch_retry_productive(w):
    action, n = straight_line(w, 5, 9)
    failures = set(w.rng.sample(range(n), 2))
    unknown = w.rng.choice([i for i in range(n) if i not in failures])
    for i in range(n):
        if i in failures:
            w.act(action, PRODUCTIVE, 'failed_then_retried', outcome='failed')
        w.act(action, PRODUCTIVE, 'move_towards_destination', outcome='outcome_unknown' if i == unknown else 'acknowledged')


def reset_then_replay(w):
    w.place_with_room({})
    start = list(w.avatar)
    route = []
    for _ in range(w.rng.randint(3, 5)):
        before = len(w.raws)
        if not w.explore(1, 'route'):
            break
        route.append(w.raws[before]['dispatched'])

    def back_to_start():
        w.avatar = list(start)
        w.marks = {}
    w.act(RESET, PRODUCTIVE, 'reset', reset_to=back_to_start)
    for action in route:
        w.act(action, PRODUCTIVE, 'replay_after_reset')


POSITIVE = {
    'repeated_click_no_effect': (repeated_click_no_effect, False),
    'rotating_clicks_no_effect': (rotating_clicks_no_effect, False),
    'toggle_two_cycle': (toggle_two_cycle, False),
    'move_square_cycle': (move_square_cycle, False),
    'counter_only_repeat': (counter_only_repeat, True),
    'loop_under_step_counter': (loop_under_step_counter, True),
    'walk_into_wall': (walk_into_wall, False),
    'no_effect_with_dispatch_gaps': (no_effect_with_dispatch_gaps, False),
    'loop_then_escape': (loop_then_escape, False),
    'loop_escape_into_loop': (loop_escape_into_loop, False),
}
HARD_NEGATIVE = {
    'move_to_destination': (move_to_destination, False),
    'incremental_click_effect': (incremental_click_effect, False),
    'varied_click_painting': (varied_click_painting, False),
    'backtracking_required': (backtracking_required, False),
    'delayed_effect': (delayed_effect, False),
    'counter_with_static_playfield': (counter_with_static_playfield, False),
    'productive_exploration_no_completion': (productive_exploration_no_completion, False),
    'dispatch_retry_productive': (dispatch_retry_productive, False),
    'reset_then_replay': (reset_then_replay, False),
}
FAMILIES = {**POSITIVE, **HARD_NEGATIVE}


def generate(partition):
    """All fixtures of one partition: {'fixtures': public evidence, 'evaluator_only': labels and notes}."""
    seed, count = PARTITIONS[partition]
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    fixtures, evaluator_only = [], {}
    for family, (make, step_counter) in FAMILIES.items():
        for i in range(count):
            fid = f'{partition[:3]}-{family}-{i}'
            w = World(random.Random(rng.random()), step_counter=step_counter)
            make(w)
            opaque = 'st-' + hashlib.sha256(fid.encode()).hexdigest()[:12]  # no family label in the evidence
            for raw in w.raws:
                raw['identity']['episode_id'] = opaque
            fixtures.append({'id': fid, 'partition': partition, 'raws': w.raws,
                             'predictions': w.predictions if w.predict else None})
            evaluator_only[fid] = {'family': family, 'positive': family in POSITIVE, 'labels': w.labels,
                                   'notes': w.notes}
    return {'version': VERSION, 'partition': partition, 'fixtures': fixtures, 'evaluator_only': evaluator_only}


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def digest(partition):
    return hashlib.sha256(encode(generate(partition))).hexdigest()
