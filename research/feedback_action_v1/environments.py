"""Synthetic environments with known mechanisms (synthetic diagnostics only; never real-game data).

Each environment emits raw transitions in the `transition_evidence_v1` input format, so the shared builder, the
evidence view and the evaluator run unchanged on them. Mechanisms are known so that rehearsals can be scored; the
mechanism is never shown to a policy. Action numbers have no game meaning outside this module.

Available actions: with `report_actions` set, every observation also carries `available_actions`, so version 2
records have a measured `context.available_actions_before` and `available_actions_after`. It is off by default so
the frozen decision-boundary fixtures stay byte-identical (their context reports the field as `absent`).

Fault injection: `faults` maps a dispatch index to 'failed' (rejected before execution; nothing happens) or
'outcome_unknown' (the action executes, but its result is never returned).
"""
import copy

SOURCE = 'synthetic_environment'
SIZE = 8
WALL, PLAYER, GOAL, SWITCH, LAMP_OFF, LAMP_ON, TARGET, DECOY, FLASH = 5, 3, 2, 9, 7, 8, 4, 6, 1


def blank(background=0):
    grid = [[background] * SIZE for _ in range(SIZE)]
    for i in range(SIZE):
        grid[0][i] = grid[SIZE - 1][i] = grid[i][0] = grid[i][SIZE - 1] = WALL
    return grid


class Environment:
    legal_actions = ()
    mechanism = ''
    win_levels = 1

    def __init__(self, faults=None):
        self.faults = dict(faults or {})
        self.levels, self.state, self.full_reset = 0, 'NOT_FINISHED', False
        self.dispatches = 0
        self.frame = self.level_frame()

    report_actions = False  # when True, observations carry `available_actions` (transition_evidence_v2 context)

    def observe(self):
        obs = {'frames': [copy.deepcopy(self.frame)], 'levels_completed': self.levels, 'state': self.state,
               'full_reset': self.full_reset}
        if self.report_actions:
            obs['available_actions'] = list(self.legal_actions)
        return obs

    def complete_level(self):
        self.levels += 1
        if self.levels >= self.win_levels:
            self.state = 'WIN'
        self.reset_level()

    def dispatch(self, action, proposal=None):
        """Execute one action and return the raw transition (the contract's input format)."""
        index = self.dispatches
        self.dispatches += 1
        before = self.observe()
        raw = {'identity': {'episode_id': type(self).__name__, 'action_index': index}, 'before': before,
               'proposal': copy.deepcopy(proposal if proposal is not None else action),
               'dispatched': copy.deepcopy(action), 'environment_source': SOURCE}
        fault = self.faults.get(index)
        if fault == 'failed':
            raw['outcome'] = {'status': 'failed', 'reason': 'synthetic: request rejected before acknowledgement'}
            return raw
        self.full_reset = False
        frames = self.step(action)
        if fault == 'outcome_unknown':
            raw['outcome'] = {'status': 'outcome_unknown', 'reason': 'synthetic: response lost after send'}
        else:
            raw['outcome'] = {'status': 'acknowledged', 'after': {**self.observe(), 'frames': frames}}
        return raw


class DelayedSwitch(Environment):
    """ACTION5 three times in a row completes the level; the first two presses change nothing visible.
    ACTION1 toggles a lamp and resets the hidden press count. Two levels."""
    legal_actions = (1, 5)
    mechanism = 'three consecutive ACTION5 complete the level; earlier presses are invisible; ACTION1 toggles a lamp'
    win_levels = 2

    def level_frame(self):
        grid = blank(self.levels)
        grid[6][6] = SWITCH
        grid[1][1] = LAMP_OFF
        return grid

    def reset_level(self):
        self.presses = 0
        self.frame = self.level_frame()

    def __init__(self, faults=None):
        self.presses = 0
        super().__init__(faults)

    def step(self, action):
        if action['action_id'] == 5:
            self.presses += 1
            if self.presses == 3:
                self.complete_level()
        else:
            self.presses = 0
            self.frame[1][1] = LAMP_ON if self.frame[1][1] == LAMP_OFF else LAMP_OFF
        return [copy.deepcopy(self.frame)]


class PushToGoal(Environment):
    """ACTION1-4 move a marker up, down, left, right; walls block (no observed change). Reaching the goal completes
    the level. After `move_limit` moves in one level the environment resets the level (full_reset)."""
    legal_actions = (1, 2, 3, 4)
    mechanism = 'ACTION1 up, ACTION2 down, ACTION3 left, ACTION4 right; goal completes the level; wall bumps change nothing'
    win_levels = 2
    MOVES = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
    GOALS = ((3, 1), (1, 4))

    def __init__(self, faults=None, move_limit=None):
        self.move_limit, self.moves, self.pos = move_limit, 0, (1, 1)
        super().__init__(faults)

    def level_frame(self):
        grid = blank()
        gx, gy = self.GOALS[min(self.levels, len(self.GOALS) - 1)]
        grid[gy][gx] = GOAL
        grid[self.pos[1]][self.pos[0]] = PLAYER
        return grid

    def reset_level(self):
        self.pos, self.moves = (1, 1), 0
        self.frame = self.level_frame()

    def step(self, action):
        dx, dy = self.MOVES[action['action_id']]
        x, y = self.pos[0] + dx, self.pos[1] + dy
        self.moves += 1
        if self.frame[y][x] != WALL:
            self.pos = (x, y)
            if (x, y) == self.GOALS[min(self.levels, len(self.GOALS) - 1)]:
                self.complete_level()
                return [copy.deepcopy(self.frame)]
            self.frame = self.level_frame()
        if self.move_limit is not None and self.moves >= self.move_limit:
            self.reset_level()
            self.full_reset = True
        return [copy.deepcopy(self.frame)]


class Clicker(Environment):
    """ACTION6 only. Clicking the target cell completes the level; clicking the decoy flashes it (a changed frame,
    then the original); any other cell changes nothing."""
    legal_actions = (6,)
    mechanism = 'ACTION6 on (5, 5) completes the level; on (2, 5) a flash returns to the original; elsewhere nothing'
    TARGET_XY, DECOY_XY = (5, 5), (2, 5)

    def level_frame(self):
        grid = blank()
        grid[self.TARGET_XY[1]][self.TARGET_XY[0]] = TARGET
        grid[self.DECOY_XY[1]][self.DECOY_XY[0]] = DECOY
        return grid

    def reset_level(self):
        self.frame = self.level_frame()
        self.frame[3][3] = GOAL  # the completed level looks different

    def step(self, action):
        xy = (action['action_data']['x'], action['action_data']['y'])
        if xy == self.TARGET_XY:
            self.complete_level()
            return [copy.deepcopy(self.frame)]
        if xy == self.DECOY_XY:
            flash = copy.deepcopy(self.frame)
            flash[xy[1]][xy[0]] = FLASH
            return [flash, copy.deepcopy(self.frame)]
        return [copy.deepcopy(self.frame)]


ENVIRONMENTS = {'delayed_switch': DelayedSwitch, 'push_to_goal': PushToGoal, 'clicker': Clicker}


def action(action_id, x=None, y=None):
    return {'action_id': action_id, 'action_data': {} if x is None else {'x': x, 'y': y}}
