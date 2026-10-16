"""Explicit preflight/dry-check/launch commands. Importing this file never launches."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.object_identification_v1 import operations as G
from research.object_identification_v1.kaggle_operator import Backend, serialize
from research.object_identification_v1.operator import Operator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight', 'dry-check', 'launch'))
    for name in ('package', 'approval', 'authorization', 'operator-lock'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--review-lock', required=True)
    parser.add_argument('--preflight', type=Path)
    parser.add_argument('--token-file', type=Path, default=Path.home()/'.kaggle/access_token')
    args = parser.parse_args()
    op = Operator(args.package, args.approval, args.authorization, args.review_lock, ROOT, args.operator_lock)
    op.verify_local()
    if args.mode == 'dry-check':
        G.require(args.preflight is not None, 'passed preflight path required')
        book, _, body = op.prepare(args.preflight, serialize)
        print(json.dumps({'SDK_wire_body_validated': True, 'preflight_bound': True,
                          'reservation_consumed': False, 'provider_calls': 0,
                          'notebook_bytes': len(G.canonical(book)), 'serialized_field_count': len(body)}))
        return
    backend = Backend(op, args.token_file, allow_save=args.mode == 'launch')
    try:
        if args.mode == 'preflight':
            path = op.preflight(backend)
        else:
            G.require(args.preflight is not None, 'passed preflight path required')
            path = op.launch(backend, args.preflight, serialize)
        print(json.dumps({'receipt': str(path), 'status': G.load(path)['status']}, indent=2))
        return 0 if G.load(path)['status'] in ('passed', 'submitted_once_saved_package_verified') else 1
    finally:
        backend.close()


if __name__ == '__main__':
    sys.exit(main())
