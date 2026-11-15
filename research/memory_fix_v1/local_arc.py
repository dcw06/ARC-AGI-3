"""bp35 on the local copy of the game, behind the interface the harness's controller expects.

The controller (research/claude_arc_v1/run.py) only needs: list_game_ids, open_scorecard, bootstrap,
dispatch, finalize_client, close_scorecard. This class provides them over the local game, so the unchanged
controller, policy and audit can play bp35 with no call to the ARC service and no scorecard.

Observations are built field for field like the live ones. `check_against_saved_run` proves it for the
100 saved actions: every observation hashes to the value the live run recorded.
"""
from types import SimpleNamespace

import numpy as np
from arcengine import GameState

from agent.action import serialize_action
from agent.framework_adapter import PreDispatchFailure
from agent.state import Observation
from research.memory_fix_v1 import bp35_local

GUID = 'local-bp35'


def observe(result):
    return Observation(bp35_local.GAME_ID, tuple(np.ascontiguousarray(f, dtype=np.uint8) for f in result.frame),
                       GameState[result.state.name], int(result.levels_completed), int(result.win_levels), GUID,
                       tuple(int(getattr(a, 'value', a)) for a in result.available_actions), bool(result.full_reset))


class LocalBp35:
    def __init__(self, allow_reset_from_live=False):
        self.allow_reset_from_live = allow_reset_from_live
        self.opened = self.closed = False
        self.actions = 0

    def list_game_ids(self):
        return (bp35_local.GAME_ID,)

    def open_scorecard(self, tags=None):
        self.opened = True
        return 'local-no-scorecard'

    def bootstrap(self, game):
        if game != bp35_local.GAME_ID:
            raise PreDispatchFailure('only bp35 is available locally')
        engine = bp35_local.game_class()()
        first = bp35_local.perform(engine, {'action_id': 0})          # the opening RESET, not a counted action
        return SimpleNamespace(game_id=game, engine=engine, observation=observe(first))

    def dispatch(self, client, decision):
        before = client.observation
        try:   # the same legality rule as the live adapter: RESET only after GAME_OVER unless the study allows more
            serialize_action(decision, game_id=client.game_id, guid=before.guid,
                             legal_actions=before.available_actions,
                             allow_level_reset=before.state is GameState.GAME_OVER or self.allow_reset_from_live)
        except Exception as exc:
            raise PreDispatchFailure(str(exc)) from exc
        result = bp35_local.perform(client.engine, {'action_id': decision.action_id,
                                                    'action_data': dict(decision.action_data)})
        self.actions += 1
        client.observation = observe(result)
        return client.observation

    def finalize_client(self, client):
        pass

    def close_scorecard(self):
        self.closed = True
        return {'card_id': 'local-no-scorecard', 'local': True, 'actions': self.actions}


def check_against_saved_run():
    """Replay the saved actions through this adapter; return the steps whose observation hash differs."""
    from agent.action import ActionDecision
    first, steps = bp35_local.saved_run()
    world = LocalBp35()
    client = world.bootstrap(bp35_local.GAME_ID)
    differs = [] if client.observation.canonical_hash == first['observation_sha256'] else [0]
    for n, (action, saved) in enumerate(steps, 1):
        after = world.dispatch(client, ActionDecision(action['action_id'], dict(action['action_data']), source='check'))
        if after.canonical_hash != saved['observation_sha256']:
            differs.append(n)
    return differs, len(steps)


if __name__ == '__main__':
    differs, total = check_against_saved_run()
    print('saved actions', total, '| observations whose hash differs from the live run:', differs or 'none')
