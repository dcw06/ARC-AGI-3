"""CPU-only reproduction of the automatic arm from retained native/SAM evidence."""
import argparse
import json
import os
from pathlib import Path
import socket
import sys

os.environ.update(CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void', HF_HUB_OFFLINE='1',
                  TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', MPLBACKEND='Agg')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.initial_geometry_assistance_v1.automatic_replay import replay_comparison, sha
from research.initial_geometry_assistance_v1.geometry import canonical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control-root', type=Path, required=True)
    parser.add_argument('--molmopoint-checkpoint', type=Path, required=True)
    parser.add_argument('--sam-acquisition', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('preserve previous artifacts')
    def no_network(*a, **kw):
        raise PermissionError('automatic evidence replay: network forbidden')
    socket.socket.connect = socket.create_connection = no_network
    comparison = replay_comparison(args.control_root, args.molmopoint_checkpoint, args.sam_acquisition)
    raw = canonical(comparison)
    with args.output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'automatic_artifact_sha256': sha(raw), 'totals': comparison['totals'],
                      'model_generations': 0, 'GPU_jobs': 0, 'raw_SAM_masks_reconstructed': True,
                      'native_pointing_deployment_and_lifecycle_replayed': True}))


if __name__ == '__main__':
    main()
