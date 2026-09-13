"""Run the Plan 8 lifecycle through a clearly labeled local/official backend."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.competition_loop import CompetitionOrchestrator
from agent.diagnostics import TransitionDiagnosticRecorder
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
    parser.add_argument(
        "--diagnostics-dir",
        type=Path,
        help="Write local, content-addressed transition bundles to this directory",
    )
    args = parser.parse_args()

    if args.backend == "local":
        from arc_agi import Arcade, OperationMode

        arcade = Arcade(operation_mode=OperationMode.NORMAL, logger=quiet_logger())
        phase2 = json.loads((ROOT / "config/phase2_contract.yaml").read_text())
        frozen_seeds = {
            item["game_id"]: item["seed"]
            for item in phase2["development_game_seed_pairs"]
        }
        adapter = LocalFrameworkAdapter(arcade, seed_by_game=frozen_seeds)
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

    recorders: list[TransitionDiagnosticRecorder] = []

    def diagnostic_factory(client: object) -> TransitionDiagnosticRecorder:
        game_id = str(getattr(client, "game_id"))
        recorder = TransitionDiagnosticRecorder(
            game_id=game_id,
            treatment_id="E0-fallback",
            seed=frozen_seeds.get(game_id) if args.backend == "local" else None,
            run_id="phase2-local-diagnostic",
            capacity=max(args.max_actions, 1),
        )
        recorders.append(recorder)
        return recorder

    result = CompetitionOrchestrator(
        adapter,
        game_ids,
        max_workers=args.max_workers,
        max_actions=args.max_actions,
        watchdog=DeadlineWatchdog(32_400, 600),
        diagnostic_factory=diagnostic_factory if args.diagnostics_dir is not None else None,
    ).run()
    if args.diagnostics_dir is not None:
        args.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        for recorder in recorders:
            opaque_name = hashlib.sha256(recorder.game_id.encode()).hexdigest()[:20]
            recorder.write(args.diagnostics_dir / f"{opaque_name}.json")
        print(f"diagnostics={args.diagnostics_dir} bundles={len(recorders)}")
    print(f"backend={args.backend} clients={len(result.results)} finalization={result.finalization_status}")
    for item in result.results:
        print(
            f"{item.game_id} status={item.status} levels={item.levels_completed} "
            f"actions={item.acknowledged_actions} reason={item.terminal_reason}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
