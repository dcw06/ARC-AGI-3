"""Verify mounted model and tokenize frozen requests offline; never launch a model."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase4_runner import TargetServiceBackend


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True)
    args = parser.parse_args()
    backend = TargetServiceBackend()
    backend.primary = replace(backend.primary, model_path=args.model_path)
    print(json.dumps(backend.preflight(), indent=2, sort_keys=True))
