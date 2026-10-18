"""Seal a private, compute-refusing review package. Never contacts Kaggle."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.initial_geometry_assistance_v1.live_package import build


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--input-pin', required=True)
    parser.add_argument('--game-environment', type=Path, required=True)
    parser.add_argument('--game-pin', required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--scope-review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(ROOT, args.inputs, args.input_pin, args.game_environment, args.game_pin,
                           json.loads(args.runtime.read_bytes()), args.output, scope_review=args.scope_review)))
