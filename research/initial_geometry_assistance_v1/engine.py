"""Lazy imports keep preparation usable before the pinned game install."""
from pathlib import Path

from .policy import check_observation


class OfflineEngine:
    def __init__(self, game_id, games, recordings):
        from arc_agi import Arcade, OperationMode
        from agent.framework_adapter import LocalFrameworkAdapter
        self.game_id = game_id
        self.client = None
        self.card = None
        self.closed = False
        self.adapter = LocalFrameworkAdapter(
            Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(Path(games)),
                   recordings_dir=str(Path(recordings))), seed_by_game={game_id: 0})

    @staticmethod
    def snapshot(obs):
        return check_observation({'grid': obs.latest_frame.tolist(), 'state': obs.state.value,
                                  'levels_completed': obs.levels_completed,
                                  'legal_actions': sorted(a for a in obs.available_actions if 1 <= a <= 7)})

    def bootstrap(self):
        self.card = self.adapter.open_scorecard(tags=['initial-geometry-development-offline'])
        self.client = self.adapter.bootstrap(self.game_id)
        return self.snapshot(self.client.observation)

    def dispatch(self, action):
        from agent.action import ActionDecision
        obs = self.adapter.dispatch(self.client, ActionDecision(**action, source='initial_geometry_shared_policy_v1'))
        return self.snapshot(obs)

    def close(self):
        if self.closed:
            raise ValueError('duplicate engine close')
        self.closed = True
        if self.client is not None:
            self.adapter.finalize_client(self.client)
        receipt = self.adapter.close_scorecard() if self.card is not None else None
        return {'closed': True, 'local_scorecard_opened': self.card is not None,
                'local_scorecard_closed': receipt is not None, 'online_calls': 0}
