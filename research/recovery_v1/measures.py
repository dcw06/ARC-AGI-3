"""Recovery measures computed from a trace (see traces.py). No game source, no model calls.

Definitions used throughout:

attempt       A run of actions on one level that starts at the level's first board or just after a RESET,
              and ends when the level is completed, when a RESET is sent, or when the trace ends.
              Outcomes: completed / game_over (a RESET followed GAME_OVER) / abandoned (a RESET was sent
              from a live position) / open (trace ended, level unfinished) / game_over_final.
board key     Level index plus a hash of the last returned board with step-counter cells blanked
              (counter_mask). Two equal keys do not prove equal hidden state.
new board     An action whose resulting key was not seen earlier. "In the attempt" compares with this
              attempt only; "in the level" compares with every earlier visit to the level.
dead-end loss For a failed attempt: its actions plus the RESET that ended it (the strict reading, where
              only a completed level counts as progress). `stale_tail` is the part after the attempt's
              last new board, which is what a stall detector could at best have saved.
return cost   For the attempt B that follows a failed attempt A on the same level: the furthest point of A
              that B came back to (`regained_at`, counted in actions from A's start), and how many actions
              B needed to get there (`regain_cost`). `known_ground` is B's leading actions that only
              revisit boards already seen on this level.
"""
import hashlib
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claude_arc_v1 import recovery  # noqa: E402


def counter_mask(trace, tick=2):
    """Cells that look like a step counter, judged with hindsight from the whole trace.

    The rule is the live controller's (claude_arc_v1.recovery.CounterMask), applied to every action of the
    trace before any board is compared. A live run only knows what it has seen so far.
    """
    counter = recovery.CounterMask(tick)
    before, level = trace['initial'], 0
    for step in trace['steps']:
        if step['a'] == 'RESET' or step['lc'] != level:
            counter.restart()          # a new attempt: the counter may run again
        elif step['state'] == 'NOT_FINISHED':
            counter.update(before, step['frame'])
        before, level = step['frame'], step['lc']
    return counter.mask if counter.mask is not None else np.zeros(trace['initial'].shape, dtype=bool)


def board_key(frame, level, mask=None):
    if mask is not None and frame.shape == mask.shape:
        frame = frame.copy()
        frame[mask] = 0
    return (level, hashlib.sha1(frame.tobytes()).hexdigest()[:16])


def keys(trace, mask=None):
    """[key of the first board] + [key after each step]."""
    out = [board_key(trace['initial'], 0, mask)]
    out += [board_key(step['frame'], step['lc'], mask) for step in trace['steps']]
    return out


def attempts(trace):
    """Split a trace into attempts. Indices are positions in trace['steps']."""
    steps, out = trace['steps'], []
    level, first = 0, 0
    for i, step in enumerate(steps):
        if step['a'] == 'RESET':
            died = i > 0 and steps[i - 1]['state'] == 'GAME_OVER'
            out.append({'level': level, 'first': first, 'last': i - 1, 'n': i - first,
                        'outcome': 'game_over' if died else 'abandoned', 'reset': i,
                        'reset_by': step['by'], 'full_reset': bool(step['full_reset']),
                        'level_after_reset': step['lc']})
            level, first = step['lc'], i + 1
        elif step['lc'] > level or step['state'] == 'WIN':
            out.append({'level': level, 'first': first, 'last': i, 'n': i - first + 1,
                        'outcome': 'completed', 'reset': None})
            level, first = step['lc'], i + 1
    if first < len(steps):
        final = 'game_over_final' if steps[-1]['state'] == 'GAME_OVER' else 'open'
        out.append({'level': level, 'first': first, 'last': len(steps) - 1, 'n': len(steps) - first,
                    'outcome': final, 'reset': None})
    return out


def annotate(trace, mask):
    """attempts(trace) with the novelty, dead-end and return measures filled in."""
    k = keys(trace, mask)  # k[i + 1] is the key after step i; k[first] is an attempt's starting key
    steps, rows = trace['steps'], attempts(trace)
    seen_level = {}        # level -> keys seen on that level so far
    for row in rows:
        level_seen = seen_level.setdefault(row['level'], set())
        known_before = set(level_seen)
        attempt_seen = {k[row['first']]}
        level_seen.add(k[row['first']])
        new_attempt, new_level = [], []
        for i in range(row['first'], row['last'] + 1):
            key = k[i + 1]
            new_attempt.append(key not in attempt_seen)
            new_level.append(key not in level_seen)
            attempt_seen.add(key)
            level_seen.add(key)
        row['new_in_attempt'] = int(sum(new_attempt))
        row['new_in_level'] = int(sum(new_level))
        row['stale_tail'] = _trailing_false(new_attempt)
        row['stale_tail_level'] = _trailing_false(new_level)
        row['longest_stale_run'] = _longest_false(new_attempt)
        row['after_game_over'] = sum(1 for i in range(row['first'] + 1, row['last'] + 1)
                                     if steps[i - 1]['state'] == 'GAME_OVER')
        row['known_ground'] = _leading(k[i + 1] in known_before for i in range(row['first'], row['last'] + 1))
        row['_keys'] = [k[row['first']]] + [k[i + 1] for i in range(row['first'], row['last'] + 1)]
        row['_actions'] = [(steps[i]['a'], steps[i]['x'], steps[i]['y'])
                           for i in range(row['first'], row['last'] + 1)]
        if row['outcome'] in ('game_over', 'abandoned'):
            row['dead_end_loss'] = row['n'] + 1      # the attempt and the RESET that ended it
    for a, b in zip(rows, rows[1:]):
        if a['outcome'] not in ('game_over', 'abandoned'):
            continue
        if b['level'] != a['level']:
            # A full reset sent the agent back: the cost of regaining the level is counted separately.
            a['next_same_level'] = False
            continue
        a['next_same_level'] = True
        b['follows_failed'] = True
        b['common_prefix'] = _leading(x == y for x, y in zip(a['_actions'], b['_actions']))
        where = {key: j for j, key in reversed(list(enumerate(b['_keys'])))}  # first position in B
        regained = max((i for i, key in enumerate(a['_keys']) if key in where), default=0)
        b['regained_at'] = regained
        b['regain_cost'] = where.get(a['_keys'][regained], 0)
        b['start_matches'] = a['_keys'][0] == b['_keys'][0]
    return rows


def _trailing_false(flags):
    n = 0
    for flag in reversed(flags):
        if flag:
            break
        n += 1
    return n


def _longest_false(flags):
    best = run = 0
    for flag in flags:
        run = 0 if flag else run + 1
        best = max(best, run)
    return best


def _leading(flags):
    n = 0
    for flag in flags:
        if not flag:
            break
        n += 1
    return n


def reset_facts(trace, mask=None):
    """One row per RESET step: what it was sent from and what the game returned."""
    steps, rows = trace['steps'], []
    level_start = {0: trace['initial']}      # level -> first board seen on it
    level = 0
    for i, step in enumerate(steps):
        before = trace['initial'] if i == 0 else steps[i - 1]['frame']
        if step['a'] == 'RESET':
            start = level_start.get(step['lc'])
            rows.append({
                'step': i, 'by': step['by'], 'from_state': steps[i - 1]['state'] if i else 'NOT_FINISHED',
                'previous_was_reset': i > 0 and steps[i - 1]['a'] == 'RESET',
                'level_before': level, 'level_after': step['lc'], 'full_reset_flag': bool(step['full_reset']),
                'state_after': step['state'],
                'equals_level_start': None if start is None else bool(np.array_equal(step['frame'], start)),
                'equals_level_start_ignoring_counter': None if start is None or mask is None else
                    board_key(step['frame'], 0, mask) == board_key(start, 0, mask),
                'cells_differing_from_level_start': None if start is None else int((step['frame'] != start).sum()),
                'board_unchanged_by_reset': bool(np.array_equal(step['frame'], before))})
        if step['lc'] != level:
            level = step['lc']
            level_start.setdefault(level, step['frame'])
    return rows


def undo_facts(trace, mask=None):
    """One row per ACTION7 step: did the board return to what it was before the action being undone?

    The action being undone is tracked with a stack, so a second ACTION7 in a row is compared with the
    board two actions further back. The stack is emptied by a RESET and by a level change. The public
    recordings keep only the last board of each step, so this compares final boards.
    """
    steps, rows = trace['steps'], []
    boards = [trace['initial']] + [s['frame'] for s in steps]   # boards[i] is the board before step i
    stack, level = [], 0
    for i, step in enumerate(steps):
        if step['a'] == 'RESET' or step['lc'] != level:
            stack, level = [], step['lc']
            continue
        if step['a'] != 'ACTION7':
            stack.append(i)                                      # boards[i] is what an undo should bring back
            continue
        row = {'step': i, 'changed_board': not np.array_equal(step['frame'], boards[i]),
               'in_a_row': bool(i and steps[i - 1]['a'] == 'ACTION7'), 'had_target': bool(stack)}
        if stack:
            undone = stack.pop()
            target = boards[undone]
            row['undone_action_changed_board'] = not np.array_equal(boards[undone + 1], target)
            row['restored_exact'] = bool(np.array_equal(step['frame'], target))
            row['restored_ignoring_counter'] = (None if mask is None else
                                                board_key(step['frame'], 0, mask) == board_key(target, 0, mask))
            row['cells_differing_from_target'] = int((step['frame'] != target).sum())
        rows.append(row)
    return rows
