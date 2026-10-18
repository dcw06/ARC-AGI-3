"""Lazy imports keep preparation usable before the pinned game install."""
import hashlib
import json
from pathlib import Path

from .policy import check_observation


def verify_game_environment(root, receipt_sha256, *, wheels=None, check=lambda: None):
    """Check the game environment against an independently supplied receipt hash."""
    root = Path(root)
    wheels = Path(wheels) if wheels is not None else root/'wheels'
    check()
    raw = (root/'receipt.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt_sha256:
        raise ValueError('game environment receipt differs')
    receipt = json.loads(raw)
    lock = hashlib.sha256((root/'game_requirements.lock').read_bytes()).hexdigest()
    if lock != receipt['requirements_sha256']:
        raise ValueError('game requirements lock differs')
    members = receipt['verified_members']
    expected_wheels = {name.split('/', 1)[1] for name in members if name.startswith('wheels/')}
    if wheels.is_symlink() or not wheels.is_dir() or {p.name for p in wheels.iterdir()} != expected_wheels:
        raise ValueError('game wheel inventory differs')
    for name, info in members.items():
        parts = Path(name).parts
        if (not parts or Path(name).is_absolute() or '..' in parts or '\\' in name or ':' in name or
                parts[0] not in ('wheels', 'environment_files') or
                (parts[0] == 'wheels' and len(parts) != 2)):
            raise ValueError('unsafe game environment member')
        path = wheels/parts[1] if parts[0] == 'wheels' else root/name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
            raise ValueError('unsafe game environment file')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                check()
                digest.update(block)
        check()
        if digest.hexdigest() != info['sha256'] or path.stat().st_size != info['bytes']:
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
