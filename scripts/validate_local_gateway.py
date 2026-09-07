"""Exercise the production adapter against the pinned toolkit's real REST app."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import replace
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arc_agi import Arcade, OperationMode
from arc_agi.server import create_app
from arcengine import GameAction, GameState
from flask import jsonify, request
from werkzeug.serving import make_server

from agent.action import ActionDecision, DisplayPoint
from agent.framework_adapter import RemoteFrameworkAdapter


def main() -> int:
    if not (ROOT / "environment_files" / "ls20" / "9607627b" / "metadata.json").exists():
        print("LOCAL_GATEWAY_EQUIVALENCE_FAILED fixture_missing")
        return 2

    old_reset = os.environ.get("ONLY_RESET_LEVELS")
    os.environ["ONLY_RESET_LEVELS"] = "true"
    logging.disable(logging.CRITICAL)
    server = None
    try:
        logger = logging.getLogger("phase0-gateway")
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
        arcade = Arcade(operation_mode=OperationMode.OFFLINE, logger=logger)

        def add_cookie(response, _api_key):
            response.set_cookie("ARC_AFFINITY", "phase0")
            return response

        app, _ = create_app(
            arcade,
            competition_mode=True,
            save_all_recordings=False,
            include_frame_data=True,
            add_cookie=add_cookie,
        )

        @app.before_request
        def require_affinity_after_open():
            if request.path.startswith("/api/cmd/") and request.cookies.get("ARC_AFFINITY") != "phase0":
                return jsonify({"error": "missing affinity"}), 409
            return None

        server = make_server("127.0.0.1", 0, app)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        adapter = RemoteFrameworkAdapter(
            base_url=f"http://127.0.0.1:{server.server_port}",
            api_key="phase0-fixture",
            competition_mode=True,
        )
        game_ids = adapter.list_game_ids()
        assert game_ids
        card_id = adapter.open_scorecard(tags=["agent", "phase0-fixture"])
        client = adapter.bootstrap(game_ids[0])

        scorecard = arcade.scorecard_manager.get_scorecard(card_id, "phase0-fixture")
        assert scorecard is not None
        card = scorecard.get_card(client.observation.game_id)
        assert (card.actions[0], card.resets[0]) == (0, 0)

        # RESET is lifecycle-legal after GAME_OVER even when omitted from the
        # normal action list. Altering this local view does not affect the server.
        client.observation = replace(client.observation, state=GameState.GAME_OVER)
        adapter.dispatch(client, ActionDecision.simple(GameAction.RESET, decision_id="fixture-reset"))
        assert (card.actions[0], card.resets[0]) == (1, 1)

        action_id = next(value for value in client.observation.available_actions if value != 0)
        if action_id == GameAction.ACTION6.value:
            decision = ActionDecision.click(DisplayPoint(0, 0), decision_id="fixture-action")
        else:
            decision = ActionDecision.simple(action_id, decision_id="fixture-action")
        adapter.dispatch(client, decision)
        assert (card.actions[0], card.resets[0]) == (2, 1)
        assert client.bootstrap_requests == 1
        assert client.action_requests == 2
        assert all(item.status.value == "acknowledged" for item in client.journal.snapshot())

        closed = adapter.close_scorecard()
        assert closed["total_actions"] >= 2
        print("LOCAL_GATEWAY_EQUIVALENCE_PASSED")
        return 0
    except Exception:
        print("LOCAL_GATEWAY_EQUIVALENCE_FAILED invariant")
        return 1
    finally:
        if server is not None:
            server.shutdown()
        logging.disable(logging.NOTSET)
        if old_reset is None:
            os.environ.pop("ONLY_RESET_LEVELS", None)
        else:
            os.environ["ONLY_RESET_LEVELS"] = old_reset


if __name__ == "__main__":
    raise SystemExit(main())
