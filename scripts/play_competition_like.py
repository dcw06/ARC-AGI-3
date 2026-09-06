"""Run the Plan 8 lifecycle through a clearly labeled local/official backend."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.competition_loop import CompetitionOrchestrator
from agent.framework_adapter import LocalFrameworkAdapter, RemoteFrameworkAdapter
from agent.watchdog import DeadlineWatchdog


def quiet_logger() -> logging.Logger:
    logger = logging.getLogger("arc3-local-emulation")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("local", "official"), default="local")
    parser.add_argument("--game", help="Comma-separated opaque game IDs")
    parser.add_argument("--max-actions", type=int, default=80)
    parser.add_argument("--max-workers", type=int, default=4)
    args = parser.parse_args()

    if args.backend == "local":
        from arc_agi import Arcade, OperationMode

        arcade = Arcade(operation_mode=OperationMode.NORMAL, logger=quiet_logger())
        adapter = LocalFrameworkAdapter(arcade)
        available = tuple(item.game_id for item in arcade.get_environments())
    else:
        adapter = RemoteFrameworkAdapter(
            base_url=os.getenv("ARC_BASE_URL", "https://arcprize.org"),
            api_key=os.getenv("ARC_API_KEY", ""),
            competition_mode=False,
        )
        available = adapter.list_game_ids()

    if args.game:
        prefixes = tuple(value.strip() for value in args.game.split(",") if value.strip())
        game_ids = tuple(value for value in available if value.startswith(prefixes))
    else:
        game_ids = available
    if not game_ids:
        raise SystemExit("no matching games")

    result = CompetitionOrchestrator(
        adapter,
        game_ids,
        max_workers=args.max_workers,
        max_actions=args.max_actions,
        watchdog=DeadlineWatchdog(32_400, 600),
    ).run()
    print(f"backend={args.backend} clients={len(result.results)} finalization={result.finalization_status}")
    for item in result.results:
        print(
            f"{item.game_id} status={item.status} levels={item.levels_completed} "
            f"actions={item.acknowledged_actions} reason={item.terminal_reason}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
