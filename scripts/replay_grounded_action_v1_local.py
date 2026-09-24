"""Read-only independent replay of a Stage B local record."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.grounded_action_v1.replay import replay_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('record', type=Path)
    args = parser.parse_args()
    print(json.dumps(replay_file(args.record), sort_keys=True))


if __name__ == '__main__':
    main()
