"""Lazy imports keep preparation usable before the pinned game install."""
import hashlib
import json
from pathlib import Path

from .policy import check_observation


def verify_game_environment(root, receipt_sha256):
    """Check the game environment against an independently supplied receipt hash."""
    root = Path(root)
    raw = (root/'receipt.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt_sha256:
        raise ValueError('game environment receipt differs')
    receipt = json.loads(raw)
    lock = hashlib.sha256((root/'game_requirements.lock').read_bytes()).hexdigest()
    if lock != receipt['requirements_sha256']:
        raise ValueError('game requirements lock differs')
    members = receipt['verified_members']
    for name, info in members.items():
        data = (root/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != info['sha256'] or len(data) != info['bytes']:
            raise ValueError('game environment differs')
    # Every game file the engine can load must be a verified member.
    games = {p.relative_to(root).as_posix() for p in (root/'environment_files').rglob('*') if p.is_file()}
    if games != {name for name in members if name.startswith('environment_files/')}:
        raise ValueError('game environment inventory differs')
    return {'game_environment_receipt_sha256': receipt_sha256, 'game_requirements_sha256': lock}


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
