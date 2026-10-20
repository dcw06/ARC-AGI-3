"""Prepare the prospective phase-explicit successor; never submit or run a model."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.action_effect_choice_v2.preparation import build, verify, protocol
from research.initial_geometry_assistance_v1.live_io import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoints', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.checkpoints, args.output)
    pin = sha(args.output/'input-manifest.json')
    verify(args.output, pin)
    print(json.dumps({'passed': True, 'input_manifest_sha256': pin,
                      'inference_files': len(result['files_sha256']),
                      'format_pilot_proposal': protocol()['format_pilot'],
                      'GPU_jobs': 0, 'model_generations': 0, 'provider_writes': 0}))


if __name__ == '__main__': main()
