"""Validate and summarize a completed causal E1 four-cell evidence record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.e1_experiment import file_sha256, validate_experiment_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "record",
        nargs="?",
        type=Path,
        default=ROOT / "reports/runs/e1-four-cell/e1-causal-four-cell-v1.json",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "config/e1_experiment_protocol.yaml",
    )
    parser.add_argument(
        "--feature-registry",
        type=Path,
        default=ROOT / "config/e1_feature_manifests.yaml",
    )
    return parser.parse_args()


def _load(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"JSON record is not an object: {path}")
    return value


def main() -> int:
    args = parse_args()
    try:
        record = _load(args.record)
        protocol = _load(args.protocol)
        feature_registry = _load(args.feature_registry)
        validate_experiment_record(record, protocol, feature_registry)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"E1_FOUR_CELL_INVALID reason={type(exc).__name__}:{exc}")
        return 1

    analysis = record["analysis"]
    print(f"E1_FOUR_CELL_VALID sha256={file_sha256(args.record)}")
    for cell, mean in analysis["cell_means"].items():
        charged = record["cells"][cell]["charged_totals"]
        print(
            f"CELL id={cell} mean={mean:.8f} "
            f"model_requests={charged['inference_requests']} "
            f"model_completions={charged['inference_completions']} "
            f"transport_failures={charged['inference_transport_failures']} "
            f"queue_failures={charged['inference_queue_failures']} "
            f"workspace_invocations={charged['workspace_invocations']} "
            f"policy_failures={charged['policy_failures']}"
        )
    selection = analysis["selection_procedure"]
    print(
        "SELECTION "
        f"procedure_mean={selection['selection_procedure_mean']:.8f} "
        f"fixed={selection['final_fixed_candidate']} "
        f"fixed_mean={selection['final_fixed_candidate_mean']:.8f}"
    )
    for name, contrast in analysis["factorial_contrasts"].items():
        print(
            f"CONTRAST name={name} effect={contrast['mean_effect']:.8f} "
            f"nonzero={contrast['nonzero_pairs']} p={contrast['two_sided_p_value']} "
            f"status={contrast['status']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
