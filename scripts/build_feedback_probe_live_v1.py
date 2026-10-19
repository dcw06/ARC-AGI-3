"""Build a private GPU-refusing review package locally; no provider operations."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.feedback_probe_v1.live_contract import prepare_inputs
from research.feedback_probe_v1.live_package import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('prepared', 'inputs', 'game-environment', 'runtime', 'scope-review', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--cpu-pin', required=True)
    parser.add_argument('--game-pin', required=True)
    args = parser.parse_args()
    pin = prepare_inputs(args.prepared, args.cpu_pin, ROOT, args.inputs)
    runtime = json.loads(args.runtime.read_bytes())
    runtime['input_manifest_sha256'] = pin
    result = build(ROOT, args.inputs, pin, args.game_environment, args.game_pin,
                   runtime, args.output, scope_review=args.scope_review)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
