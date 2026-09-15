"""Inspect exact E1S-R request fixtures without loading a model or an environment."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase4_workload import build_workload


if __name__ == "__main__":
    workload = build_workload()
    print(json.dumps({key: value for key, value in workload.items()
                      if key not in {"fixtures", "assignments"}}, indent=2))
    print(json.dumps([{key: value for key, value in row.items() if key != "request"}
                      for row in workload["fixtures"]], indent=2))
