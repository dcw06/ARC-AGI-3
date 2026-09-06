from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import requests
from arcengine import GameAction, GameState

from agent.action import ActionDecision, ActionValidationError, DisplayPoint, serialize_action
from agent.action_journal import LiveTransactionJournal, JournalTransitionError, TransactionKind, TransactionStatus
from agent.competition_loop import CompetitionAgentLoop, CompetitionOrchestrator
from agent.controller import DeterministicFallback
from agent.framework_adapter import OutcomeUnknown, RemoteFrameworkAdapter
from agent.output_policy import OutputPolicyError, enforce_retained_allowlist
from agent.scheduler import FairInferenceQueue
from agent.state import Observation
from agent.watchdog import DeadlineWatchdog


def frame(*, state: str = "NOT_FINISHED", levels: int = 0, actions: list[int] | None = None) -> dict:
    return {
        "game_id": "zz99-version",
        "frame": [[[0, 1], [1, 0]]],
        "state": state,
        "levels_completed": levels,
        "win_levels": 2,
        "guid": "guid-1",
        "full_reset": False,
        "available_actions": actions if actions is not None else [1, 6],
    }


class FakeResponse:
    def __init__(self, value: object, status: int = 200, redirect: bool = False) -> None:
        self.value = value
        self.status_code = status
        self.is_redirect = redirect

    def json(self):
        return self.value

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code), response=self)


class FakeSession:
    def __init__(self) -> None:
        self.cookies = requests.cookies.RequestsCookieJar()
        self.calls: list[tuple[str, str, dict]] = []
        self.fail_action = False

    def mount(self, *_args) -> None:
        pass

    def get(self, url: str, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return FakeResponse([{"game_id": "zz99-version", "title": "not retained"}])

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if url.endswith("/scorecard/open"):
            return FakeResponse({"card_id": "card-1"})
        if url.endswith("/cmd/RESET"):
            return FakeResponse(frame())
        if "/cmd/ACTION" in url:
            if self.fail_action:
                raise requests.Timeout("ambiguous")
            return FakeResponse(frame(levels=1))
        if url.endswith("/scorecard/close"):
            return FakeResponse({"score": 0.0})
        raise AssertionError(url)


class ActionTests(unittest.TestCase):
    def test_action_is_immutable_and_request_local(self) -> None:
        decision = ActionDecision.click(DisplayPoint(3, 7))
        serialized = serialize_action(
            decision,
            game_id="zz99-version",
            guid="guid-1",
            legal_actions=[GameAction.ACTION6],
        )
        self.assertEqual(dict(serialized.payload)["x"], 3)
        with self.assertRaises(TypeError):
            decision.action_data["x"] = 9  # type: ignore[index]

    def test_illegal_and_bad_coordinates_fail_before_dispatch(self) -> None:
        with self.assertRaises(ActionValidationError):
            DisplayPoint(64, 0)
        with self.assertRaises(ActionValidationError):
            serialize_action(
                ActionDecision.simple(GameAction.ACTION5),
                game_id="zz99-version",
                guid="guid-1",
                legal_actions=[GameAction.ACTION1],
            )

    def test_reasoning_byte_limit_checks_server_parsed_value(self) -> None:
        decision = ActionDecision.simple(GameAction.ACTION1, wire_reasoning={"x": "a" * 100})
        with self.assertRaises(ActionValidationError):
            serialize_action(decision, game_id="g", guid="u", legal_actions=[1], reasoning_limit_bytes=20)


class JournalTests(unittest.TestCase):
    def test_valid_sequence_and_no_retry_transition(self) -> None:
        journal = LiveTransactionJournal("test")
        entry = journal.prepare(TransactionKind.ACTION, payload_sha256="x")
        journal.mark_dispatched(entry.transaction_id)
        terminal = journal.mark_outcome_unknown(entry.transaction_id, "timeout")
        self.assertEqual(terminal.status, TransactionStatus.OUTCOME_UNKNOWN)
        with self.assertRaises(JournalTransitionError):
            journal.mark_dispatched(entry.transaction_id)


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sessions: list[FakeSession] = []

        def factory() -> FakeSession:
            value = FakeSession()
            self.sessions.append(value)
            return value

        self.adapter = RemoteFrameworkAdapter(base_url="http://gateway", api_key="key", session_factory=factory)

    def test_one_open_bootstrap_action_and_close(self) -> None:
        self.adapter.open_scorecard()
        client = self.adapter.bootstrap("zz99-version")
        next_observation = self.adapter.dispatch(client, ActionDecision.simple(GameAction.ACTION1))
        self.assertEqual(next_observation.levels_completed, 1)
        self.adapter.close_scorecard()
        calls = [call for session in self.sessions for call in session.calls if call[0] == "POST"]
        self.assertEqual(sum(url.endswith("/cmd/RESET") for _, url, _ in calls), 1)
        self.assertEqual(sum("/cmd/ACTION1" in url for _, url, _ in calls), 1)
        self.assertTrue(all(call[2]["allow_redirects"] is False for call in calls))

    def test_ambiguous_action_quarantines_without_retry(self) -> None:
        self.adapter.open_scorecard()
        client = self.adapter.bootstrap("zz99-version")
        client.session.fail_action = True
        with self.assertRaises(OutcomeUnknown):
            self.adapter.dispatch(client, ActionDecision.simple(GameAction.ACTION1))
        with self.assertRaises(OutcomeUnknown):
            self.adapter.dispatch(client, ActionDecision.simple(GameAction.ACTION1))
        action_calls = [call for call in client.session.calls if "/cmd/ACTION1" in call[1]]
        self.assertEqual(len(action_calls), 1)
        self.assertEqual(client.journal.snapshot()[-1].status, TransactionStatus.OUTCOME_UNKNOWN)

    def test_request_payloads_do_not_cross_clients(self) -> None:
        self.adapter.open_scorecard()
        first = self.adapter.bootstrap("zz99-version")
        # A second adapter isolates the duplicate fake game used by this fixture.
        other_sessions: list[FakeSession] = []
        second_adapter = RemoteFrameworkAdapter(
            base_url="http://gateway",
            api_key="key",
            session_factory=lambda: other_sessions.append(FakeSession()) or other_sessions[-1],
        )
        second_adapter.open_scorecard()
        second = second_adapter.bootstrap("zz99-version")
        self.adapter.dispatch(first, ActionDecision.click(DisplayPoint(1, 2)))
        second_adapter.dispatch(second, ActionDecision.click(DisplayPoint(9, 10)))
        first_payload = [call[2]["json"] for call in first.session.calls if "/cmd/ACTION6" in call[1]][0]
        second_payload = [call[2]["json"] for call in second.session.calls if "/cmd/ACTION6" in call[1]][0]
        self.assertEqual((first_payload["x"], first_payload["y"]), (1, 2))
        self.assertEqual((second_payload["x"], second_payload["y"]), (9, 10))

    def test_bootstrap_journal_has_no_fabricated_prestate(self) -> None:
        self.adapter.open_scorecard()
        client = self.adapter.bootstrap("zz99-version")
        bootstrap = client.journal.snapshot()[0]
        self.assertNotIn("pre_state_hash", bootstrap.prepared_fields)
        self.assertNotIn("guid", bootstrap.prepared_fields)
        self.assertEqual(bootstrap.fields["guid"], "guid-1")
        self.assertEqual(bootstrap.status, TransactionStatus.ACKNOWLEDGED)


class FakeLoopAdapter:
    def dispatch(self, client, _decision):
        client.calls += 1
        client.observation = Observation(
            game_id=client.observation.game_id,
            layers=client.observation.layers,
            state=GameState.NOT_FINISHED,
            levels_completed=0,
            win_levels=2,
            guid=client.observation.guid,
            available_actions=(1,),
        )
        return client.observation


class FakeClient:
    def __init__(self) -> None:
        self.game_id = "opaque-runtime-id"
        self.observation = Observation.from_value(frame(actions=[1]))
        self.calls = 0


class LoopTests(unittest.TestCase):
    def test_exact_action_cap_and_bounded_state(self) -> None:
        client = FakeClient()
        loop = CompetitionAgentLoop(FakeLoopAdapter(), client, max_actions=3)
        result = loop.run()
        self.assertEqual(result.acknowledged_actions, 3)
        self.assertEqual(client.calls, 3)
        self.assertFalse(hasattr(loop, "frames"))

    def test_fallback_is_session_deterministic(self) -> None:
        state1 = type("S", (), {"observation": Observation.from_value(frame(actions=[1, 2, 6]))})()
        state2 = type("S", (), {"observation": Observation.from_value(frame(actions=[1, 2, 6]))})()
        self.assertEqual(DeterministicFallback().propose(state1).action_id, DeterministicFallback().propose(state2).action_id)

    def test_three_independent_traces_are_deterministic(self) -> None:
        traces = []
        for suffix in range(3):
            obs = Observation(
                game_id="opaque",
                layers=Observation.from_value(frame()).layers,
                state=GameState.NOT_FINISHED,
                levels_completed=0,
                win_levels=2,
                guid=f"different-guid-{suffix}",
                available_actions=(1, 2, 6),
            )
            state = SimpleNamespace(observation=obs)
            policy = DeterministicFallback()
            trace = []
            for _ in range(12):
                decision = policy.propose(state)
                trace.append((decision.action_id, tuple(sorted(decision.action_data.items()))))
            traces.append(trace)
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(traces[1], traces[2])


class SchedulerTests(unittest.TestCase):
    def test_110_client_queue_is_bounded_and_services_all(self) -> None:
        scheduler = FairInferenceQueue(maxsize=110)
        for index in range(110):
            scheduler.submit(f"client-{index}", 0, str(index), lambda index=index: index)
        self.assertEqual(scheduler.max_observed_size, 110)
        outputs = []
        while scheduler.size:
            serviced = scheduler.service_one()
            self.assertIsNotNone(serviced)
            outputs.append(serviced[1])
        self.assertEqual(outputs, list(range(110)))

    def test_independent_watchdog_stops_admission(self) -> None:
        watchdog = DeadlineWatchdog(hard_seconds=0.05, finalization_reserve_seconds=0.02)
        watchdog.start_supervisor(poll_seconds=0.002)
        deadline = time.monotonic() + 0.2
        while not watchdog.stop_admission and time.monotonic() < deadline:
            time.sleep(0.002)
        watchdog.stop_supervisor()
        self.assertTrue(watchdog.stop_admission)


class SyntheticAdapter:
    def __init__(self) -> None:
        self.open_count = 0
        self.close_count = 0
        self.bootstrap_count: dict[str, int] = {}

    def open_scorecard(self, tags=None):
        self.open_count += 1
        return "card"

    def bootstrap(self, game_id):
        self.bootstrap_count[game_id] = self.bootstrap_count.get(game_id, 0) + 1
        obs = Observation(
            game_id=game_id,
            layers=Observation.from_value(frame()).layers,
            state=GameState.NOT_FINISHED,
            levels_completed=0,
            win_levels=1,
            guid=f"guid-{game_id}",
            available_actions=(1,),
        )
        return SimpleNamespace(game_id=game_id, observation=obs, calls=0)

    def dispatch(self, client, _decision):
        client.calls += 1
        client.observation = Observation(
            game_id=client.game_id,
            layers=client.observation.layers,
            state=GameState.WIN,
            levels_completed=1,
            win_levels=1,
            guid=client.observation.guid,
            available_actions=(1,),
        )
        return client.observation

    def close_scorecard(self):
        self.close_count += 1
        return {"score": 0}


class OrchestrationTests(unittest.TestCase):
    def test_110_clients_one_scorecard_one_make_each(self) -> None:
        adapter = SyntheticAdapter()
        ids = [f"opaque-{index}" for index in range(110)]
        result = CompetitionOrchestrator(adapter, ids, max_workers=8, max_actions=2).run()
        self.assertEqual(len(result.results), 110)
        self.assertTrue(all(item.levels_completed == 1 for item in result.results))
        self.assertEqual(adapter.open_count, 1)
        self.assertEqual(adapter.close_count, 1)
        self.assertEqual(set(adapter.bootstrap_count.values()), {1})


class OutputPolicyTests(unittest.TestCase):
    def test_allowlist_removes_only_scoped_unapproved_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "working"
            root.mkdir()
            (root / "submission.parquet").write_bytes(b"ok")
            (root / "logs.log").write_text("hidden")
            (root / "recording").mkdir()
            (root / "recording" / "frame.json").write_text("hidden")
            removed = enforce_retained_allowlist(root)
            self.assertEqual(removed, ("logs.log", "recording"))
            self.assertEqual([item.name for item in root.iterdir()], ["submission.parquet"])

    def test_allowlist_rejects_broad_root(self) -> None:
        with self.assertRaises(OutputPolicyError):
            enforce_retained_allowlist("/")


class ConfigurationTests(unittest.TestCase):
    def test_all_registries_are_json_compatible_and_versioned(self) -> None:
        root = Path(__file__).resolve().parents[1] / "config"
        for path in root.iterdir():
            if path.suffix in {".yaml", ".json", ".lock"}:
                value = json.loads(path.read_text())
                self.assertEqual(value["schema_version"], 1, path.name)


if __name__ == "__main__":
    unittest.main()
