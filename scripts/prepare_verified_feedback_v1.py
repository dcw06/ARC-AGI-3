"""Prepare or verify CPU-only inputs; never imports a model or provider."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.verified_feedback_v1.preparation import build, verify
from research.initial_geometry_assistance_v1.live_io import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--checkpoints', type=Path)
    group.add_argument('--check-pin')
    args = parser.parse_args()
    if args.checkpoints is not None:
        build(args.checkpoints, args.output)
        pin = sha(args.output/'input-manifest.json')
    else: pin = args.check_pin
    result = verify(args.output, pin)
    print(json.dumps({'passed': True, 'input_manifest_sha256': pin, 'inference_files': len(result['files_sha256']),
                      'live_enabled': False, 'GPU_jobs': 0, 'model_generations': 0, 'provider_writes': 0}))


if __name__ == '__main__': main()
