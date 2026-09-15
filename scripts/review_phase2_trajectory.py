"""Describe retained trajectories after verification; no new policy or game access."""
import argparse
import base64
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.phase2_reproduction import compare_runs


def describe(bundle):
    frames = {}
    for digest, value in bundle["retained_frames"].items():
        frames[digest] = np.frombuffer(base64.b64decode(value["payload_base64"], validate=True), dtype=np.uint8).reshape(value["shape"])
    actions, coordinates = Counter(), Counter()
    changed_counts = Counter()
    longest = streak = 0
    previous = None
    for record in bundle["records"]:
        decision = record["proposal_or_fallback"]["executed_decision"]
        action = json.dumps([decision["action_id"], decision["action_data"]], sort_keys=True)
        actions[action] += 1
        streak = streak + 1 if action == previous else 1
        longest = max(longest, streak)
        previous = action
        if record["post"]:
            before = frames[record["pre"]["frame_content_sha256"]]
            after = frames[record["post"]["frame_content_sha256"]]
            indices = np.argwhere(before != after)
            changed_counts[len(indices)] += 1
            coordinates.update(map(tuple, indices.tolist()))
    return {"run_id":bundle["run_id"], "action_counts":dict(actions),
            "longest_identical_action_streak":longest,
            "changed_cell_count_histogram":dict(changed_counts),
            "changed_coordinates_row_column":[{"row":int(r),"column":int(c),"count":count}
                for (r,c),count in sorted(coordinates.items())],
            "interpretation_scope":"post_hoc_descriptive_no_new_success_threshold_or_treatment_admission"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    lock = json.loads((directory / "execution-lock.json").read_text())
    if lock != json.loads((ROOT / "notebooks/phase2-cd82/execution-lock.json").read_text()):
        raise ValueError("downloaded lock does not match frozen lock")
    execution = json.loads((directory / "execution.json").read_text())
    if execution["status"] != "complete":
        raise ValueError("incomplete execution")
    paths = [(directory / name).resolve() for name in execution["runs"]]
    if any(not path.is_relative_to(directory) for path in paths):
        raise ValueError("run path escapes directory")
    report = compare_runs(ROOT,paths,lock)
    report["descriptive_review"] = [describe(json.loads(path.read_text())["bundle"]) for path in paths]
    print(json.dumps(report,indent=2,sort_keys=True))


if __name__ == "__main__":
    main()
