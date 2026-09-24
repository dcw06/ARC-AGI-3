"""Run the CPU-only scripted Stage B pair and immediately replay it."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.grounded_action_v1.local import ScriptedAdapter, ScriptedService, run
from research.grounded_action_v1.replay import replay_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output, ScriptedService(), lambda arm: ScriptedAdapter(arm))
    if result['status'] != 'complete':
        raise SystemExit(result['error'])
    print(json.dumps(replay_file(args.output), sort_keys=True))


if __name__ == '__main__':
    main()
