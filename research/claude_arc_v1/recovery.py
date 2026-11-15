"""Recovery study: stall signals, the reset rule, and what the model is shown.

Nothing here talks to a game or a model. Every feature is off unless the configuration turns it on, so
the November 6 control behaves exactly as before.

Signals, computed from returned boards and public counters only:

  no new board    consecutive model actions on this attempt whose resulting board was already seen in the
                  attempt, step-counter cells ignored. Optionally also requires that the agent's notes
                  kept the same claims and statuses over those actions.
  level actions   actions spent on the current level (every attempt and every RESET) as a multiple of
                  that level's public human baseline.

A recovery check is due when an enabled signal reaches its threshold. A check resets nothing: it puts
the facts in front of the model and asks it to decide.
"""
import hashlib

import numpy as np

RESET_ALLOWED = (
    'You may reset (action 0, empty action_data): it restarts the current level from its first board, keeps '
    'completed levels, and counts as one action. It is refused before your first action on an attempt. ')
REPLAY_NOTE = (' When evidence.replay_offer is present you have just been reset. Set replay to N to have the '
               'controller repeat the first N actions of the ended attempt for you, or to 0 to play on yourself. '
               'Each repeated action counts as an action, every returned board is checked against the one '
               'recorded before, and repetition stops at the first difference. When replay is above 0 your own '
               'action is not sent that turn. Without a replay_offer, leave replay out.')
# No level check within this many model actions of any other check.
MIN_GAP = 3
# A new attempt needs room to finish. In saved play the median completed level took about half its human
# baseline (0.46 to 0.51 across three harnesses), so a reset that leaves less than that is refused.
PAYBACK_SHARE = 0.5


class WholeGameReset(ValueError):
    """A RESET changed the number of completed levels. Ends that game."""


class CounterMask:
    """Cells that look like a step counter, estimated as play goes on.

    A counter cell changes once per attempt, and its neighbours follow in order. So:
      - a cell is marked when it changed in an action that changed at most `tick` cells in total;
      - a marked cell that changes a second time within one attempt belongs to an object (a piece moving
        back and forth, a switch) and is never ignored;
      - a row or column with three or more marked cells that are not objects is ignored across their span,
        because a counter also ticks during actions that change other things;
      - if those cells were marked in order along the line and the line holds no object cell, it is read
        as a bar that moves one way and the whole line is ignored from then on: the cells behind the
        first mark ticked during larger actions, and the cells ahead are ticks still to come.
    Single marked cells are not ignored. If more than MAX_LINES lines' worth of cells would be ignored the
    estimate is not trusted and nothing is ignored.

    This is a heuristic. It finds nothing when a counter never ticks alone, and equal keys do not prove
    equal positions.
    """
    MAX_LINES = 4

    def __init__(self, tick=2):
        self.tick, self.mask, self.marks = tick, None, 0
        self.order = self.objects = self.changed = None
        self.bars = set()                      # lines read as a moving bar: (0, row) or (1, column)

    def restart(self):
        """A new attempt begins (RESET or level change): a counter may run again from its start."""
        if self.changed is not None:
            self.changed[:] = False

    def update(self, before, after):
        """Learn from one ordinary action. Returns True when the set of ignored cells changed."""
        before, after = np.asarray(before), np.asarray(after)
        if before.shape != after.shape or before.ndim != 2:
            return False
        if self.order is None or self.order.shape != before.shape:
            self.order = np.zeros(before.shape, dtype=np.int64)   # 0 = unmarked, else when it was marked
            self.objects = np.zeros(before.shape, dtype=bool)
            self.changed = np.zeros(before.shape, dtype=bool)
            self.mask = np.zeros(before.shape, dtype=bool)
            self.bars = set()
        diff = before != after
        again = diff & self.changed & (self.order > 0) & ~self.objects
        self.changed |= diff
        fresh = diff & (self.order == 0)
        marking = 0 < int(diff.sum()) <= self.tick and fresh.any()
        if not again.any() and not marking:
            return False
        self.objects |= again
        if marking:
            self.marks += 1
            self.order[fresh] = self.marks
        previous, self.mask = self.mask, self._widen()
        return not np.array_equal(previous, self.mask)

    def _widen(self):
        counter = (self.order > 0) & ~self.objects
        wide = np.zeros(counter.shape, dtype=bool)
        spans = wide.copy()
        for axis, (cells, order, objects, out, plain) in enumerate((
                (counter, self.order, self.objects, wide, spans),
                (counter.T, self.order.T, self.objects.T, wide.T, spans.T))):
            for i, line in enumerate(cells):
                hit = np.flatnonzero(line)
                if objects[i].any():
                    self.bars.discard((axis, i))
                if hit.size < 3:
                    continue
                steps = np.diff(order[i][hit])
                if not objects[i].any() and steps.any() and ((steps >= 0).all() or (steps <= 0).all()):
                    self.bars.add((axis, i))
                plain[i, hit[0]:hit[-1] + 1] = True
                out[i, hit[0]:hit[-1] + 1] = True
                if (axis, i) in self.bars:
                    out[i, :] = True
        limit = self.MAX_LINES * max(counter.shape)
        for candidate in (wide, spans):
            if int(candidate.sum()) <= limit:
                return candidate
        return np.zeros(counter.shape, dtype=bool)

    def key(self, frame):
        frame = np.asarray(frame)
        if self.mask is not None and frame.shape == self.mask.shape:
            frame = frame.copy()
            frame[self.mask] = 0
        return hashlib.sha1(repr(frame.shape).encode() + frame.tobytes()).hexdigest()

    @property
    def cells(self):
        return 0 if self.mask is None else int(self.mask.sum())


def notes_signature(hypotheses):
    """What counts as the agent's memory for 'no change': which claims it holds and their status, not wording."""
    return tuple(sorted((h['id'], h['status']) for h in hypotheses))


class Tracker:
    """What the controller knows about the current level and attempt. One per game."""

    def __init__(self, first_board, tick=2):
        self.counter = CounterMask(tick)
        self.level = 0
        self.level_actions = 0       # on the current level: every attempt, RESETs included
        self.level_game_overs = 0
        self.level_resets = 0
        self.next_level_check = None  # level-action count at which the next level check is due
        self.attempt = []            # the current attempt: {'transition_id', 'action', 'after_sha256', 'state'}
        self.ended_attempt = []      # the attempt the last RESET ended, same shape
        self.boards = [np.asarray(first_board)]   # boards of the current attempt, its first board first
        self.chosen = []             # for each board after the first: was the action the model's own?
        self.keys = {self.counter.key(first_board)}   # the boards' keys under the current counter estimate
        self.stale = 0               # consecutive model actions without a new board
        self.notes_stale = 0         # consecutive model actions with the same notes signature
        self.since_check = MIN_GAP   # model actions since the last recovery check
        self.last_answer = None      # the model's answer to the last check on this level
        self._notes = None

    def record(self, transition_id, decision, before, after, *, by_model, notes=None):
        """Account for one acknowledged action. Returns facts for the evidence log."""
        action = {'action_id': decision.action_id, 'action_data': dict(decision.action_data)}
        new_level = after.levels_completed != before.levels_completed
        new = None
        if decision.action_id == 0:
            self.level_actions += 1
            self.level_resets += 1
            self.ended_attempt, self.attempt = self.attempt, []
            self._restart(after.latest_frame)
        else:
            # The counter is learned from ordinary actions only: a level change or a game over redraws it.
            ordinary = not new_level and after.state.name == 'NOT_FINISHED'
            changed = ordinary and self.counter.update(before.latest_frame, after.latest_frame)
            key = self.counter.key(after.latest_frame)
            self.level_actions += 1
            self.attempt.append({'transition_id': transition_id, 'action': action,
                                 'after_sha256': after.canonical_hash, 'state': after.state.name})
            self.boards.append(np.asarray(after.latest_frame))
            self.chosen.append(bool(by_model))
            self.level_game_overs += after.state.name == 'GAME_OVER'
            if changed:
                # The estimate moved: judge the whole attempt again, so a counter found late still counts
                # the repeats that came before it was found.
                new = self._recount() or new_level
            else:
                new = bool(new_level or key not in self.keys)
                self.keys.add(key)
                if by_model:
                    self.stale = 0 if new else self.stale + 1
            if by_model:
                self.since_check += 1
                signature = None if notes is None else notes_signature(notes)
                self.notes_stale = self.notes_stale + 1 if signature == self._notes else 0
                self._notes = signature
        if new_level:
            self.level = after.levels_completed
            self.level_actions = self.level_game_overs = self.level_resets = 0
            self.next_level_check = self.last_answer = None
            self.attempt, self.ended_attempt = [], []
            self._restart(after.latest_frame)
            self.since_check = 0
        return {'new_board': None if new is None else bool(new), 'stale': self.stale,
                'notes_stale': self.notes_stale, 'level': self.level, 'level_actions': self.level_actions,
                'attempt_actions': len(self.attempt), 'counter_cells': self.counter.cells}

    def _restart(self, board):
        self.counter.restart()
        self.boards, self.chosen, self.stale = [np.asarray(board)], [], 0
        self.keys = {self.counter.key(board)}

    def _recount(self):
        """Recompute the keys and the stale count for the attempt under the current counter estimate.

        Returns whether the newest board is new."""
        keys = [self.counter.key(board) for board in self.boards]
        seen, stale, new = {keys[0]}, 0, True
        for key, by_model in zip(keys[1:], self.chosen):
            new = key not in seen
            seen.add(key)
            if by_model:
                stale = 0 if new else stale + 1
        self.keys, self.stale = seen, stale
        return new

    def due(self, config, baseline=None):
        """Reasons a recovery check is due now. Never due before an attempt's first action."""
        if not self.attempt:
            return []
        reasons = []
        window = config.stall_window
        if (window and self.stale >= window and self.since_check >= window
                and (not config.stall_same_notes or self.notes_stale >= window)):
            reasons.append('no_new_board')
        if config.stall_level_ratio and baseline and self.since_check >= MIN_GAP:
            first = max(config.stall_level_ratio * baseline, config.stall_level_floor)
            if self.level_actions >= (first if self.next_level_check is None else self.next_level_check):
                reasons.append('level_actions')
        return reasons

    def checked(self, reasons, answer=None, baseline=None):
        """A check was made. The next level check comes one further baseline of actions after this one."""
        self.since_check = 0
        if 'level_actions' in reasons:
            self.next_level_check = self.level_actions + max(1, baseline or 1)
        if answer is not None:
            self.last_answer = {'at_actions_on_this_level': self.level_actions, **answer}

    def replay_limit(self, at_most=None):
        """How many of the ended attempt's actions may be repeated: never its fatal last action."""
        if self.attempt or not self.ended_attempt:
            return 0
        fatal = self.ended_attempt[-1]['state'] == 'GAME_OVER'
        limit = len(self.ended_attempt) - fatal
        return limit if at_most is None else max(0, min(limit, at_most))

    def offer(self, at_most=None):
        """The ended attempt, as shown to the model on the turn after a reset."""
        limit = self.replay_limit(at_most)
        if not limit:
            return None
        rows = [[n, item['transition_id'], item['action']['action_id']] + (
                    [item['action']['action_data']['x'], item['action']['action_data']['y']]
                    if item['action']['action_id'] == 6 else [])
                for n, item in enumerate(self.ended_attempt[:limit], 1)]
        return {'ended_attempt': rows, 'columns': 'n, transition_id, action_id, then x, y for ACTION6',
                'largest_replay': limit,
                'ended_by': 'GAME_OVER' if self.ended_attempt[-1]['state'] == 'GAME_OVER' else 'RESET'}


def baseline_for(config, game, level):
    values = config.level_baselines.get(game.split('-')[0]) if config.level_baselines else None
    return values[level] if values and 0 <= level < len(values) else None


def can_pay_back(actions_left, baseline=None):
    """May a reset be sent with this many actions left, this one included?

    The reset takes one. What remains must cover a new attempt: PAYBACK_SHARE of the level's human
    baseline when that is known, otherwise at least one action.
    """
    need = max(1, int(np.ceil(PAYBACK_SHARE * baseline))) if baseline else 1
    return actions_left - 1 >= need


def check_block(tracker, reasons, config):
    """The facts put in front of the model when a recovery check is due.

    Only facts about the agent's own play: no human baseline and no action budget, which other studies
    in the plan vary by themselves.
    """
    block = {'why': reasons,
             'actions_on_this_level': tracker.level_actions,
             'actions_on_this_attempt': len(tracker.attempt),
             'your_actions_in_a_row_without_a_new_board': tracker.stale,
             'game_overs_on_this_level': tracker.level_game_overs,
             'resets_on_this_level': tracker.level_resets,
             'ask': 'Decide whether this attempt can still complete the level. Answer in recovery: choice '
                    '"continue" or "reset", and in reason the observation that decides it. To reset, also '
                    'choose action 0.'}
    if tracker.last_answer:
        block['your_answer_at_the_last_check'] = tracker.last_answer
    if config.recovery_pricing:
        block['a_reset_would_cost'] = {'the_reset': 1, 'actions_on_this_attempt_given_up': len(tracker.attempt)}
    return block
