"""CPU-only subprocess fixture for the Stage B ownership/bridge rehearsal."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from certification.phase4_integrated_v2.bridge import ModelProxy
from .bridge_service import BridgeService, ProxyService
from .engine import DevelopmentAdapter, restore_game_mount, verified_game_mount
from .local import ScriptedService, run
from .replay import replay_file
from .target_host import serve_host


class FixtureTokens:
    def apply_chat_template(self, *_args, **_kwargs):
        return [1] * 10


def fixture_factory(retain, _deadline):
    scripted = ScriptedService()

    def transport(request):
        answer = scripted.complete(request)
        return SimpleNamespace(content=answer['content'], prompt_tokens=10,
                               completion_tokens=16, finish_reason=answer['finish_reason'])

    service = BridgeService('fixture-only', transport, tokenizer=FixtureTokens(), retain_canary=retain)
    service.artifact = {'fixture': 'cpu_only_no_model'}
    return service, SimpleNamespace(close=lambda: None)


def host(args):
    with patch('research.grounded_action_v1.model_service.verify'), \
            patch('research.grounded_action_v1.model_service.importlib.metadata.version',
                  side_effect=lambda name: {'transformers': '4.57.6', 'tokenizers': '0.22.2',
                                            'jinja2': '3.1.6'}[name]):
        factory = (lambda *_: (_ for _ in ()).throw(TimeoutError('injected model startup')))
        if args.fault != 'startup':
            factory = fixture_factory
        result = serve_host(args.scratch / 'model.sock', args.data_root / 'host-evidence', args.scratch / 'cancel',
                            deadline=args.deadline, service_factory=factory,
                            evidence_limit=512 if args.fault == 'evidence' else 4 * 1024**2)
    raise SystemExit(0 if result['status'] == 'stopped' else 1)


def worker(args):
    args.scratch.mkdir(parents=True, exist_ok=True)
    if args.fault == 'cancel':
        (args.scratch / 'cancel').touch()
    command = [sys.executable, '-m', 'research.grounded_action_v1.target_fixture', 'host',
               '--output', str(args.output), '--data-root', str(args.data_root), '--scratch', str(args.scratch),
               '--deadline', str(args.deadline), '--fault', args.fault]
    model = subprocess.Popen(command)  # Inherit the externally owned worker PGID.
    try:
        until = min(args.deadline, time.monotonic() + 5)
        while not (args.scratch / 'model.sock').exists():
            if model.poll() is not None:
                raise RuntimeError('fixture host failed before ready')
            if time.monotonic() >= until:
                raise TimeoutError('fixture host ready timeout')
            time.sleep(.02)
        proxy = ModelProxy(args.scratch, 'fixture-only', args.deadline, args.scratch / 'cancel')
        ProxyService(proxy).connect_ready(expected_artifact={'fixture': 'cpu_only_no_model'})
        with tempfile.TemporaryDirectory(prefix='stage-b-cpu-games-', dir=args.scratch) as temp:
            root = Path(temp)
            games = verified_game_mount(restore_game_mount(root / 'restored'), root / 'staged')
            record = args.data_root / 'record.json'
            result = run(record, ProxyService(proxy),
                         lambda arm: DevelopmentAdapter(arm, games, root / 'recordings'),
                         deadline_seconds=max(.01, args.deadline - time.monotonic()),
                         kind='offline_development_engine')
            if result['status'] != 'complete':
                raise RuntimeError('fixture study failed: ' + str(result['error']))
            replay_file(record)
    finally:
        (args.scratch / 'cancel').touch(exist_ok=True)
        model.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=('host', 'worker'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--deadline', type=float, required=True)
    parser.add_argument('--fault', choices=('none', 'startup', 'cancel', 'evidence'), default='none')
    args = parser.parse_args()
    if os.environ.get('CUDA_VISIBLE_DEVICES') not in ('', None):
        raise RuntimeError('CPU fixture refuses visible GPU')
    try:
        (host if args.role == 'host' else worker)(args)
    except Exception as exc:
        path = args.data_root / ('fixture-' + args.role + '-failure.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'error': type(exc).__name__ + ': ' + str(exc)[:256]}))
        raise


if __name__ == '__main__':
    main()
