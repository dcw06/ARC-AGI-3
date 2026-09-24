"""Offline development-engine adapter for Stage B; never a target GPU launch."""
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import zipfile

from agent.action import ActionDecision
from agent.framework_adapter import LocalFrameworkAdapter
from certification.phase4_v1.lifecycle import journal_record

GAME_ID = 'ar25-0c556536'
SEED = 0


class DevelopmentAdapter:
    def __init__(self, arm, games, recordings):
        from arc_agi import Arcade, OperationMode
        self.arm = arm
        self.adapter = LocalFrameworkAdapter(
            Arcade(operation_mode=OperationMode.OFFLINE,
                   environments_dir=str(Path(games)), recordings_dir=str(Path(recordings) / arm)),
            seed_by_game={GAME_ID: SEED})
        self.client = None
        self.card = None

    def bootstrap(self):
        self.card = self.adapter.open_scorecard(tags=['grounded-action-stage-b-development', self.arm])
        self.client = self.adapter.bootstrap(GAME_ID)
        return self.client.observation

    def dispatch(self, action, before):
        if self.client is None or self.client.observation.canonical_hash != before.canonical_hash:
            raise ValueError('development client/pre-observation mismatch')
        decision = ActionDecision(**action, source='grounded_action_stage_b',
                                  decision_id=f'{self.arm}-{self.client.action_requests}')
        post = self.adapter.dispatch(self.client, decision)
        return post, {'acknowledged': True, 'action': action, 'source': 'offline_development_engine',
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
                (self.card is None or receipt is not None),
                'source': 'offline_development_engine', 'client_closed': self.client is None or self.client.closed,
                'scorecard_closed': self.card is None or receipt is not None,
                'scorecard_id': self.card, 'scorecard_receipt': receipt,
                'lifecycle_journal': journal_record(self.adapter.lifecycle_journal),
                'client_journal': journal_record(self.client.journal) if self.client is not None else [],
                'errors': errors}


def verified_game_mount(source, destination):
    """Stage the historical manifest-bound development games, without inference."""
    from certification.phase4_closed_loop_v1.game_assets import stage_games
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / 'reports/phase4_v2_offline_package.json').read_bytes())
    return stage_games(source, destination, manifest)


def restore_game_mount(destination):
    """Restore manifest-verified game files from the committed development archive."""
    root = Path(__file__).resolve().parents[2]
    archive = root / 'evidence/phase4-v2-development-offline.zip'
    manifest = json.loads((root / 'reports/phase4_v2_offline_package.json').read_bytes())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['archive_sha256']:
        raise ValueError('development archive hash')
    destination = Path(destination)
    destination.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as bundle:
        for name, info in manifest['files'].items():
            if not name.startswith('environment_files/'):
                continue
            relative = PurePosixPath(name.removeprefix('environment_files/'))
            if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
                raise ValueError('unsafe game path')
            raw = bundle.read(name)
            if len(raw) != info['bytes'] or hashlib.sha256(raw).hexdigest() != info['sha256']:
                raise ValueError('game archive member drift: ' + name)
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    return destination
