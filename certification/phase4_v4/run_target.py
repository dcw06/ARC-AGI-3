"""Gated development-model supervisor entrypoint. Does not submit notebooks."""
import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from certification.phase4_v4.authority import authority


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--environments', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--started', type=float, required=True)
    args = p.parse_args()
    authority()  # Before agent, engine, CUDA, or supervisor imports.
    if not 0 <= time.monotonic() - args.started < 27540:
        raise ValueError('invalid first-cell lifecycle clock')
    from certification.phase4_v4.supervisor import supervise
    command = lambda scratch: [sys.executable, str(Path(__file__).with_name('worker.py')),
        str(scratch), str(args.environments.resolve()), str(args.started)]
    result = supervise(command, args.output, started=args.started)
    from certification.phase4_v1.lifecycle import validate_freeze
    from certification.phase4_v4.evaluate import evaluate
    from certification.phase4_v2.supervisor import save
    _, rows = validate_freeze()
    evaluation = evaluate(result, rows)
    save(args.output / 'evaluation.json', evaluation)
    raise SystemExit(0 if evaluation['passed'] else 1)
