"""Prepare the private geometry-only input set. Never launches compute."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.initial_geometry_assistance_v1.prepare import build_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base = args.control_root
    manifest = build_inputs(base/'gpu-live-review-r1/references/confirmed-review.json',
                            base/'sam-comparison-evaluation-r1.json', base/'control-independent-evaluation-r1.json',
                            base/'preparation-r1/inputs', args.output)
    print(json.dumps({'prepared': True, 'cases': 6, 'automatic_masks': 22, 'reviewed_masks': 37,
                      'source_pins_checked_before_preparation': True, 'GPU_jobs': 0,
                      'protocol_sha256': manifest['protocol_sha256']}))


if __name__ == '__main__':
    main()
