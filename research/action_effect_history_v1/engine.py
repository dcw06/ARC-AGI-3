"""Offline development-engine adapter for the three frozen cases (seed 0; never a live competition game)."""
from pathlib import Path

from agent.action import ActionDecision


class DevelopmentAdapter:
    def __init__(self, game_id, arm, episode_id, games, recordings):
        from arc_agi import Arcade, OperationMode
        from agent.framework_adapter import LocalFrameworkAdapter
        self.game_id, self.arm, self.episode_id = game_id, arm, episode_id
        self.adapter = LocalFrameworkAdapter(
            Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(Path(games)),
                   recordings_dir=str(Path(recordings) / episode_id)), seed_by_game={game_id: 0})
        self.client = None
        self.card = None

    def bootstrap(self):
        self.card = self.adapter.open_scorecard(tags=['action-effect-history-v1', self.arm, self.episode_id])
        self.client = self.adapter.bootstrap(self.game_id)
        return self.client.observation

    def dispatch(self, action, before):
        if self.client is None or self.client.observation.canonical_hash != before.canonical_hash:
            raise ValueError('client/pre-observation mismatch')
        decision = ActionDecision(**action, source='action_effect_history_v1',
                                  decision_id=f'{self.episode_id}-{self.client.action_requests}')
        post = self.adapter.dispatch(self.client, decision)
        from certification.phase4_v1.lifecycle import journal_record
        return post, {'acknowledged': True, 'source': 'offline_development_engine',
                      'journal': journal_record(self.client.journal)[-1]}

    def close(self):
        errors = []
        if self.client is not None:
            try:
                self.adapter.finalize_client(self.client)
            except Exception as exc:
                errors.append(type(exc).__name__ + ': ' + str(exc)[:128])
        receipt = None
        if self.card is not None:
            try:
                receipt = self.adapter.close_scorecard()
            except Exception as exc:
                errors.append(type(exc).__name__ + ': ' + str(exc)[:128])
        return {'closed': not errors and (self.client is None or self.client.closed) and
                (self.card is None or receipt is not None), 'scorecard_id': self.card, 'errors': errors}
