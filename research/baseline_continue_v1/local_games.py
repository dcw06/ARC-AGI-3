"""Any locally stored public game behind the interface the harness's controller expects.

The same idea as research/memory_fix_v1/local_arc.py (bp35 only), for any game whose file is in the local
game cache. The controller (research/claude_arc_v1/run.py) only needs: list_game_ids, open_scorecard,
bootstrap, dispatch, finalize_client, close_scorecard. No ARC service is called and no scorecard exists.

Observations are built field for field like the live ones. Whether a local game really is the game the
saved run played is checked by continue_run.py `check`: every saved action must return an observation
that hashes to the value the live run recorded.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from arcengine import ActionInput, GameAction, GameState

from agent.action import serialize_action
from agent.framework_adapter import PreDispatchFailure
from agent.state import Observation

# Game files as downloaded by the official arc-agi toolkit: <name>/<version>/<name>.py
GAMES_DIR = Path.home() / '.cache/arc-skill/arcade/environment_files'


def game_file(game_id):
    name, version = game_id.split('-', 1)
    return GAMES_DIR / name / version / (name + '.py')


def game_class(game_id):
    name = game_id.split('-', 1)[0]
    spec = importlib.util.spec_from_loader('local_game_' + name, loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(game_file(game_id).read_text(encoding='utf-8'), module.__dict__)
    return getattr(module, name.capitalize())


def perform(engine, action_id, action_data):
    data = dict(action_data or {}) if action_id == 6 else {}
    return engine.perform_action(ActionInput(id=GameAction.from_id(action_id), data=data), raw=True)


def observe(game_id, result, full_reset=None):
    return Observation(game_id, tuple(np.ascontiguousarray(f, dtype=np.uint8) for f in result.frame),
                       GameState[result.state.name], int(result.levels_completed), int(result.win_levels),
                       'local-' + game_id.split('-', 1)[0],
                       tuple(int(getattr(a, 'value', a)) for a in result.available_actions),
                       bool(result.full_reset) if full_reset is None else full_reset)


class LocalGames:
    def __init__(self, game_ids):
        self.game_ids = tuple(game_ids)
        missing = [g for g in self.game_ids if not game_file(g).is_file()]
        if missing:
            raise ValueError('no local game file for: ' + ', '.join(missing))
        self.opened = self.closed = False
        self.actions = 0

    def list_game_ids(self):
        return self.game_ids

    def open_scorecard(self, tags=None):
        self.opened = True
        return 'local-no-scorecard'

    def bootstrap(self, game):
        if game not in self.game_ids:
            raise PreDispatchFailure('not available locally: ' + game)
        engine = game_class(game)()
        first = perform(engine, 0, {})          # the opening RESET, not a counted action
        # The live service reports full_reset false on a game's first board; the local engine says true.
        # The flag is shown to the model on its first turn, so it is set as the live run had it.
        return SimpleNamespace(game_id=game, engine=engine, observation=observe(game, first, full_reset=False))

    def dispatch(self, client, decision):
        before = client.observation
        try:   # the same legality rule as the live adapter: RESET only after GAME_OVER
            serialize_action(decision, game_id=client.game_id, guid=before.guid,
                             legal_actions=before.available_actions,
                             allow_level_reset=before.state is GameState.GAME_OVER)
        except Exception as exc:
            raise PreDispatchFailure(str(exc)) from exc
        result = perform(client.engine, decision.action_id, decision.action_data)
        self.actions += 1
        client.observation = observe(client.game_id, result)
        return client.observation

    def finalize_client(self, client):
        pass

    def close_scorecard(self):
        self.closed = True
        return {'card_id': 'local-no-scorecard', 'local': True, 'actions': self.actions}
