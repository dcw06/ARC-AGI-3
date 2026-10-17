"""Start the local human game UI: .venv/bin/python scripts/play_human.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from human_play.server import main

if __name__ == '__main__':
    main()
