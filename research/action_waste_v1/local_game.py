"""A public ARC game played on its local game file, behind the interface the harness's controller expects.

The controller (research/claude_arc_v1/run.py) only needs: list_game_ids, open_scorecard, bootstrap,
dispatch, finalize_client, close_scorecard. This provides them over a game file on disk, so the unchanged
controller, policy and audit can play with no call to the ARC service and no scorecard. It is
research/memory_fix_v1/local_arc.py made to work for any game whose file is on disk.

`check_against_saved_run` replays the saved 6 November actions through the adapter and compares every
observation hash with the one the live run recorded.

    local_game.py check <game id>...
"""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from arcengine import ActionInput, GameAction, GameState

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent.action import ActionDecision, serialize_action  # noqa: E402
from agent.framework_adapter import PreDispatchFailure  # noqa: E402
from agent.state import Observation  # noqa: E402

FILES = (ROOT / 'reports/runs/phase4-v2-assets/environment_files', ROOT / 'environment_files')
SAVED = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
GUID = 'local-game'


def game_file(game_id):
    prefix, version = game_id.split('-')
    for root in FILES:
        path = root / prefix / version / (prefix + '.py')
        if path.exists():
            return path
    raise FileNotFoundError('no local game file for ' + game_id)


def game_class(game_id):
    prefix = game_id.split('-')[0]
    spec = importlib.util.spec_from_loader('local_game_' + prefix, loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(game_file(game_id).read_text(encoding='utf-8'), module.__dict__)
    return getattr(module, prefix.capitalize())


def perform(engine, action):
    data = dict(action.get('action_data') or {}) if action['action_id'] == 6 else {}
    return engine.perform_action(ActionInput(id=GameAction.from_id(action['action_id']), data=data), raw=True)


def observe(game_id, result):
    return Observation(game_id, tuple(np.ascontiguousarray(f, dtype=np.uint8) for f in result.frame),
                       GameState[result.state.name], int(result.levels_completed), int(result.win_levels), GUID,
                       tuple(int(getattr(a, 'value', a)) for a in result.available_actions), bool(result.full_reset))


class LocalGame:
    def __init__(self, game_id):
        self.game_id, self.actions = game_id, 0
        game_file(game_id)      # fail now, not at the first action, if the file is missing

    def list_game_ids(self):
        return (self.game_id,)

    def open_scorecard(self, tags=None):
        return 'local-no-scorecard'

    def bootstrap(self, game):
        if game != self.game_id:
            raise PreDispatchFailure('only %s is available here' % self.game_id)
        engine = game_class(game)()
        first = perform(engine, {'action_id': 0})          # the opening RESET, not a counted action
        return SimpleNamespace(game_id=game, engine=engine, observation=observe(game, first))

    def dispatch(self, client, decision):
        before = client.observation
        try:   # the live adapter's legality rule: RESET only after GAME_OVER
            serialize_action(decision, game_id=client.game_id, guid=before.guid,
                             legal_actions=before.available_actions,
                             allow_level_reset=before.state is GameState.GAME_OVER)
        except Exception as exc:
            raise PreDispatchFailure(str(exc)) from exc
        result = perform(client.engine, {'action_id': decision.action_id, 'action_data': dict(decision.action_data)})
        self.actions += 1
        client.observation = observe(client.game_id, result)
        return client.observation

    def finalize_client(self, client):
        pass

    def close_scorecard(self):
        return {'card_id': 'local-no-scorecard', 'local': True, 'actions': self.actions}


def saved_run(game_id):
    """(first observation, [(action, observation after)]) for one game of the saved 6 November run."""
    first, steps = None, []
    with SAVED.open() as handle:
        for line in handle:
            if game_id not in line or ('"kind":"transition"' not in line and '"kind":"initial_observation"' not in line):
                continue
            event = json.loads(line)
            if event.get('game_id') != game_id:
                continue
            if event['kind'] == 'initial_observation':
                first = event['observation']
            else:
                steps.append((event['action'], event['after']))
    return first, steps


def check_against_saved_run(game_id):
    """Steps whose observation hash differs from the live run's, and how many steps were compared."""
    first, steps = saved_run(game_id)
    world = LocalGame(game_id)
    client = world.bootstrap(game_id)
    differs = [] if client.observation.canonical_hash == first['observation_sha256'] else [0]
    for n, (action, saved) in enumerate(steps, 1):
        after = world.dispatch(client, ActionDecision(action['action_id'], dict(action['action_data']), source='check'))
        if after.canonical_hash != saved['observation_sha256']:
            differs.append(n)
    return differs, len(steps)


if __name__ == '__main__':
    for name in sys.argv[2:]:
        differs, total = check_against_saved_run(name)
        print(name, 'saved actions', total, '| observations whose hash differs from the live run:', differs or 'none')
