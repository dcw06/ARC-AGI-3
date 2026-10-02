"""Read-only overall Track 3 replay; defaults to the complete frozen live session."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from research.stagnation_supervision_v1.closed_loop.bridge import session_spec
    from research.stagnation_supervision_v1.closed_loop.runner import protocol
    from research.stagnation_supervision_v1.closed_loop.target_evaluate import evaluate_target
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--session', required=True, choices=('1', '2'))
    parser.add_argument('--mode', choices=('live', 'rehearsal'), default='live')
    parser.add_argument('--rehearsal-internal-seconds', type=int)
    parser.add_argument('--rehearsal-group')
    parser.add_argument('--rehearsal-actions', type=int)
    args = parser.parse_args()
    spec = session_spec(protocol(), args.session)
    if args.mode == 'live' and any(x is not None for x in (
            args.rehearsal_internal_seconds, args.rehearsal_group, args.rehearsal_actions)):
        parser.error('rehearsal overrides cannot be used for live acceptance')
    if args.mode == 'rehearsal':
        if not args.rehearsal_internal_seconds:
            parser.error('explicit rehearsal budget required')
        if args.rehearsal_group:
            spec = {**spec, 'schedule': [r for r in spec['schedule'] if r['pair_id'] == args.rehearsal_group]}
            if not spec['schedule']:
                parser.error('unknown rehearsal group')
        if args.rehearsal_actions is not None:
            if not 1 <= args.rehearsal_actions <= spec['limits']['actions_per_episode']:
                parser.error('rehearsal horizon')
            spec = {**spec, 'limits': {**spec['limits'], 'actions_per_episode': args.rehearsal_actions}}
    result = evaluate_target(args.output, spec, mode=args.mode, session=args.session,
                             internal_seconds=args.rehearsal_internal_seconds)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['technically_complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
