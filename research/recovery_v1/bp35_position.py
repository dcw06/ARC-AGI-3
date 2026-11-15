"""Were the saved bp35 level-2 positions of the November 6 run still winnable? Local simulator, no game, no model.

bp35 is the one game with a simulator on this machine (.cache/bp35_play/solver/sim.py, a compact copy of
the level logic that was validated action by action against the game on 9 November). The saved actions are
run through it and a breadth-first search gives the fewest actions to a win from a position, within the
in-game action bar. Attempts that contain an undo are only run up to it: the simulator has no undo.

Usage (project environment): bp35_position.py <out.json>
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.cache/bp35_play/solver'))
sys.path.insert(0, str(ROOT / 'research'))
from sim import Level, WIN, LOSE  # noqa: E402
from recovery_v1 import measures as M, traces  # noqa: E402

BAR = 63            # the in-game action bar on levels 1 to 6: an attempt ends when it runs out
RED = 'lrpkmzabbfa'  # the block that flips gravity; without it the level only moves one way


def to_sim(step):
    return {'ACTION3': ('L',), 'ACTION4': ('R',)}.get(step['a']) or ('C', step['x'], step['y'])


def fewest_to_win(level, state, budget, cap=6_000_000):
    one_way = not any(name == RED for _, name in level.start[5])

    def key(st):
        P, g, C, w, moff, blocks = st
        if one_way:     # blocks behind the player can never matter again (same reduction as solve.py)
            blocks = frozenset(b for b in blocks if b[0][1] <= P[1])
        return (P, g, C, w & 1, moff, blocks)
    seen, frontier = {key(state)}, [state]
    for depth in range(1, budget + 1):
        following = []
        for st in frontier:
            for action in level.actions(st):
                after, outcome = level.step(st, action)
                if outcome == LOSE:
                    continue
                if outcome == WIN:
                    return {'fewest_actions_to_win': depth, 'states_searched': len(seen)}
                k = key(after)
                if k not in seen:
                    seen.add(k)
                    following.append(after)
        frontier = following
        if not frontier:
            return {'fewest_actions_to_win': None, 'note': 'no win reachable', 'states_searched': len(seen)}
        if len(seen) > cap:
            return {'fewest_actions_to_win': None, 'note': 'search stopped at its cap: undecided',
                    'states_searched': len(seen)}
    return {'fewest_actions_to_win': None, 'note': 'no win within the action bar', 'states_searched': len(seen)}


def main(out_path):
    trace = traces.load_events()['bp35-0a0ad940']
    level = Level(2)
    attempts = [a for a in M.attempts(trace) if a['level'] == 1]
    rows, began = [], time.time()
    for number, attempt in enumerate(attempts, 1):
        steps = trace['steps'][attempt['first']:attempt['last'] + 1]
        undo = next((i for i, s in enumerate(steps) if s['a'] == 'ACTION7'), None)
        usable = steps if undo is None else steps[:undo]
        state, states, outcomes = level.start, [level.start], []
        for step in usable:
            state, outcome = level.step(state, to_sim(step))
            outcomes.append(outcome)
            states.append(state)
            if outcome:
                break
        row = {'attempt': number, 'actions_in_saved_run': attempt['n'], 'ended_in_saved_run': attempt['outcome'],
               'actions_simulated': len(outcomes), 'first_undo_at_action': None if undo is None else undo + 1,
               'simulated_end': outcomes[-1] if outcomes and outcomes[-1] else 'still alive'}
        # Where to ask: just before a fatal action, at the end of what could be simulated, and for the
        # third attempt at the position used in the one-decision test (65 actions into the game).
        ask = {len(outcomes) - 1} if outcomes and outcomes[-1] == LOSE else {len(outcomes)}
        if attempt['first'] <= 65 <= attempt['last'] + 1 and 65 - attempt['first'] <= len(outcomes):
            ask.add(65 - attempt['first'])
        found = {n: fewest_to_win(level, states[n], BAR - n) for n in sorted(ask)}
        last = max(found)
        if found[last]['fewest_actions_to_win'] is None and not found[last]['note'].startswith('search stopped'):
            # The attempt was already lost at the last point checked. Find the action that lost it: once a
            # position cannot be won it stays that way, so a bisection is enough.
            good = max((n for n, r in found.items() if r['fewest_actions_to_win'] is not None), default=0)
            bad = last
            while bad - good > 1:
                middle = (good + bad) // 2
                found[middle] = fewest_to_win(level, states[middle], BAR - middle)
                good, bad = (middle, bad) if found[middle]['fewest_actions_to_win'] is not None else (good, middle)
            row['lost_by_action_of_this_attempt'] = bad
            row['actions_from_then_to_its_end'] = attempt['n'] - bad + 1
        row['positions'] = [{'after_actions_of_this_attempt': n, 'after_actions_of_the_game': attempt['first'] + n,
                             **found[n]} for n in sorted(found)]
        rows.append(row)
        print(json.dumps(row), round(time.time() - began), 's', flush=True)
    Path(out_path).write_text(json.dumps({'level': 2, 'shortest_solution': 40, 'attempts': rows}, indent=1) + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
