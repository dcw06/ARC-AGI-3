"""Kaggle entry point with bounded, non-game-specific console output."""

from __future__ import annotations

import os
from importlib.metadata import version

from .competition_loop import CompetitionOrchestrator
from .framework_adapter import RemoteFrameworkAdapter
from .watchdog import DeadlineWatchdog


def main() -> int:
    print("ARC3_RUN_START", flush=True)
    try:
        if version("arc-agi") != "0.9.9" or version("arcengine") != "0.9.3":
            print("ARC3_RUNTIME_INCOMPATIBLE", flush=True)
            return 3
        adapter = RemoteFrameworkAdapter(
            base_url=os.getenv("ARC_BASE_URL", "http://gateway:8001"),
            api_key=os.getenv("ARC_API_KEY", "test-key-123"),
            competition_mode=True,
        )
        game_ids = adapter.list_game_ids()
        watchdog = DeadlineWatchdog(hard_seconds=32_400, finalization_reserve_seconds=600)
        result = CompetitionOrchestrator(
            adapter,
            game_ids,
            max_workers=int(os.getenv("ARC_MAX_CLIENTS", "8")),
            max_actions=int(os.getenv("ARC_MAX_ACTIONS", "80")),
            watchdog=watchdog,
        ).run()
        completed = sum(item.status == "complete" for item in result.results)
        print(
            f"ARC3_RUN_END clients={len(result.results)} completed={completed} finalization={result.finalization_status}",
            flush=True,
        )
        return 0 if result.finalization_status == "acknowledged" else 2
    except Exception:
        print("ARC3_RUN_FAILED phase=startup_or_inventory", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
