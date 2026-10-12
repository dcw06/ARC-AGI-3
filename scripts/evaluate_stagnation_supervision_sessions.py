"""Two-session pooled evaluation for Track 3 (frozen protocol v2; CPU only; read-only; no model or GPU).

    python scripts/evaluate_stagnation_supervision_sessions.py --session1 OUT1 --record1 S1.json \
        --session2 OUT2 --record2 S2.json --session2-execution EXECUTION.json \
        --annotations ANNOTATIONS.json --annotations-sha256 HEX

Each record is the retained output of scripts/evaluate_stagnation_supervision_runtime_v2.py for that session; both
are recomputed and must match. Comparisons are computed only after the amendment-S1 self-review annotations verify.
When --record1 is a re-evaluation under a later review lock, --session1-launch-record supplies the session-1
evaluation the session-2 execution lock binds; the two must be equal apart from the evaluating lock (amendment S2).
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from research.stagnation_supervision_runtime_v2.pooled import evaluate_sessions
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for s in ('1', '2'):
        parser.add_argument(f'--session{s}', required=True, type=Path)
        parser.add_argument(f'--record{s}', required=True, type=Path)
    parser.add_argument('--session2-execution', type=Path)
    parser.add_argument('--annotations', required=True, type=Path)
    parser.add_argument('--annotations-sha256', required=True)
    parser.add_argument('--annotations-commitment', required=True, type=Path,
                        help='private receipt of the prior immutable annotation/sample Git commit')
    parser.add_argument('--session1-launch-record', type=Path,
                        help='the session-1 evaluation bound by the session-2 execution lock, if --record1 is a re-evaluation')
    args = parser.parse_args()
    result = evaluate_sessions({'1': args.session1, '2': args.session2}, {'1': args.record1, '2': args.record2},
                               annotations=args.annotations, annotations_sha256=args.annotations_sha256,
                               session2_execution=args.session2_execution,
                               annotations_commitment=args.annotations_commitment,
                               session1_launch_record=args.session1_launch_record)
    print(json.dumps(result, indent=1, allow_nan=False, default=str))
    return 0 if result['pooled'] is not None else 1


if __name__ == '__main__':
    raise SystemExit(main())
