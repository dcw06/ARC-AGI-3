"""Default is a no-network plan. Live flags deliberately separate paid, online and competition consent."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import sys
import time
import uuid

from .config import Config


def validate_live(config, *, execute, confirm_paid, confirm_online, confirm_competition, environ):
    if not execute:
        return
    if not config.live_enabled or not confirm_online:
        raise PermissionError('set live_enabled and explicitly confirm online ARC operations')
    if os.name != 'posix':
        raise PermissionError('live worker ownership protection requires POSIX; use WSL on Windows')
    if config.backend == 'anthropic' and (not confirm_paid or config.spend_limit_usd <= 0 or not environ.get('ANTHROPIC_API_KEY')):
        raise PermissionError('paid API consent, positive spending cap and ANTHROPIC_API_KEY are required')
    if not environ.get('ARC_API_KEY'):
        raise PermissionError('ARC_API_KEY is required; anonymous key acquisition is disabled')
    if config.mode == 'competition' and not confirm_competition:
        raise PermissionError('competition initialization needs separate explicit consent')
    if any(c in environ.get('ARC_API_KEY', '') + environ.get('ANTHROPIC_API_KEY', '') for c in '\r\n'):
        raise ValueError('invalid credential format')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/claude_arc_v1.example.json')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--confirm-paid-api', action='store_true')
    parser.add_argument('--confirm-online-arc', action='store_true')
    parser.add_argument('--confirm-competition', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    config = Config.load(args.config)
    validate_live(config, execute=args.execute, confirm_paid=args.confirm_paid_api, confirm_online=args.confirm_online_arc,
                  confirm_competition=args.confirm_competition, environ=os.environ)
    if not args.execute:
        print(json.dumps({'status': 'plan_only_no_network', 'config': config.public(),
            'model_http_request_ceiling': config.max_model_calls * 2,
            'competition_note': 'entire live inventory, one scorecard, one initialization per environment',
            'billing_note': 'client reservation is not a provider-enforced billing limit; set provider account limits too'}))
        return 0
    # Import SDK-dependent code only after authorization checks; never load .env implicitly.
    from .backends import APIBackend, Budget
    from .arc import make_adapter
    from .run import Evidence, evaluate
    if importlib.metadata.version('arc-agi') != '0.9.9':
        raise ValueError('this adapter path is pinned to arc-agi 0.9.9; review a migration before upgrading')
    output = args.output or Path('.cache/claude_arc_runs') / uuid.uuid4().hex
    root = Path(__file__).resolve().parents[2]
    resolved = output.resolve()
    private = (root / '.cache/claude_arc_runs').resolve()
    if not resolved.is_relative_to(private) or resolved == private:
        raise ValueError('output must be a fresh child of .cache/claude_arc_runs (private and git-ignored)')
    started = time.monotonic()
    evidence = Evidence(resolved)
    sources = list((root / 'agent').glob('*.py')) + list(Path(__file__).parent.glob('*.py'))
    evidence.write('source_bindings', sha256={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(sources)}, config_sha256=hashlib.sha256(Path(args.config).read_bytes()).hexdigest(),
                    packages={p: importlib.metadata.version(p) for p in ('arc-agi', 'arcengine', 'numpy', 'requests')})
    budget = Budget(config)
    remaining = lambda: config.run_seconds - (time.monotonic() - started)
    backend = APIBackend(config, budget, timeout=lambda: min(config.request_timeout_seconds, remaining() - config.cleanup_seconds))
    adapter = make_adapter(config, os.environ['ARC_API_KEY'], remaining)
    def interrupted(signum, frame):
        raise KeyboardInterrupt()
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        result = evaluate(config, backend, adapter, evidence, started_at=started)
    finally:
        signal.signal(signal.SIGTERM, previous)
        evidence.close()
    print(json.dumps({'status': 'complete' if result['full_lifecycle_complete'] else 'failed_or_incomplete',
                      'output': str(resolved), 'scorecard_url': result['scorecard_url'], 'budget': result['budget']}))
    return 0 if result['full_lifecycle_complete'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, PermissionError) as exc:
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        sys.exit(2)
