"""The real bp35 game logic, run locally, for checking what an action does at a saved position.

The game file was downloaded on 9 November (.cache/bp35_play/game/, game id bp35-0a0ad940, the version the
6 November run played). `replay` sends a list of saved actions to a fresh local game and can check every
returned frame against the saved run. Nothing here calls a model or the ARC service.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
from arcengine import ActionInput, GameAction

ROOT = Path(__file__).resolve().parents[2]
GAME_DIR = ROOT / '.cache/bp35_play/game'
SAVED = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
GAME_ID = 'bp35-0a0ad940'


def game_class():
    spec = importlib.util.spec_from_loader('bp35_local_copy', loader=None)
    module = importlib.util.module_from_spec(spec)
    exec((GAME_DIR / 'bp35.py').read_text(encoding='utf-8'), module.__dict__)
    return module.Bp35


def perform(game, action):
    data = dict(action.get('action_data') or {}) if action['action_id'] == 6 else {}
    return game.perform_action(ActionInput(id=GameAction.from_id(action['action_id']), data=data), raw=True)


def saved_run():
    """(first observation, [(action, observation after)]) for bp35 in the saved 6 November run."""
    first, steps = None, []
    with SAVED.open() as handle:
        for line in handle:
            if GAME_ID not in line or ('"kind":"transition"' not in line and '"kind":"initial_observation"' not in line):
                continue
            event = json.loads(line)
            if event.get('game_id') != GAME_ID:
                continue
            if event['kind'] == 'initial_observation':
                first = event['observation']
            else:
                steps.append((event['action'], event['after']))
    return first, steps


def same(result, observation):
    frames = [np.asarray(f) for f in result.frame]
    saved = [np.asarray(f) for f in observation['frames']]
    return (len(frames) == len(saved) and all(np.array_equal(a, b) for a, b in zip(frames, saved))
            and result.state.name == observation['state']
            and int(result.levels_completed) == observation['levels_completed'])


def replay(actions, check=None):
    """A fresh local game after `actions`. With `check` (saved observations) every step must match."""
    game = game_class()()
    opened = perform(game, {'action_id': 0})
    result, mismatches = opened, []
    for n, action in enumerate(actions):
        result = perform(game, action)
        if check is not None and not same(result, check[n]):
            mismatches.append(n + 1)
    return game, result, mismatches


if __name__ == '__main__':
    first, steps = saved_run()
    game, result, mismatches = replay([a for a, _ in steps], [o for _, o in steps])
    opened = perform(game_class()(), {'action_id': 0})
    print('saved actions', len(steps), 'opening board equal', same(opened, first),
          'steps that differ from the saved run', mismatches or 'none')
