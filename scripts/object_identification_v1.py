"""Prepare/verify/score private visual probes; never launches a model or a job."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.object_identification_v1.probe import evaluate, prepare, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('prepare')
    build.add_argument('--snapshot', type=Path, required=True)
    build.add_argument('--output', type=Path, required=True)
    check = commands.add_parser('verify')
    check.add_argument('--bundle', type=Path, required=True)
    score = commands.add_parser('score')
    score.add_argument('--bundle', type=Path, required=True)
    score.add_argument('--responses', type=Path, required=True)
    score.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.snapshot, args.output)
    elif args.command == 'verify':
        lock = verify(args.bundle)
        result = {'verified': True, 'cases': len(lock['case_ids']), 'model_calls': 0}
    else:
        result = evaluate(args.bundle, args.responses)
        # Exclusive creation preserves every earlier evaluation.
        from scripts.serve_manual_strategy_worksheet import canonical, private_directory
        private_directory(args.output.parent)
        with args.output.open('xb') as stream:
            stream.write(canonical(result))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
