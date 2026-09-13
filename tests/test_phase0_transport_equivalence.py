"""Differential pinned-client fixture through real Requests session preparation.

Only the HTTP adapter's send boundary is replaced; no network or model call.
"""
import hashlib
import importlib.util
import json
import logging
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import requests
from requests.adapters import BaseAdapter
from arcengine import GameAction
from arc_agi.models import EnvironmentInfo
import arc_agi.wrapper

from agent.action import ActionDecision
from agent.framework_adapter import RemoteFrameworkAdapter, OutcomeUnknown, PreDispatchFailure, FinalizationUnknown
from agent.state import Observation
from scripts.validate_phase0f import m0_completion_registered

ROOT = Path(__file__).resolve().parents[1]
REAL_SESSION = requests.Session


def pinned_wrapper():
    path = ROOT / "tests/fixtures/mounted_arc_agi_0_9_8/remote_wrapper.py"
    if hashlib.sha256(path.read_bytes()).hexdigest() != "ebe8fd0a5ab2d5f65600f072fb22cf1de21c347a55b8c5ef569d6d7305c520e5":
        raise ValueError("mounted wrapper source drift")
    base = Path(arc_agi.wrapper.__file__)
    if hashlib.sha256(base.read_bytes()).hexdigest() != "deaf07a628fb2e0f743366de4967110d4c06bafa21c5b61561d9ca02f31055ee":
        raise ValueError("last-response implementation drift")
    spec = importlib.util.spec_from_file_location("arc_agi.phase0_fixture_remote", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RemoteEnvironmentWrapper


class WireFixture(BaseAdapter):
    def __init__(self):
        self.calls = []
        self.sessions = []
        self.failure = None
        self.counts = {}

    def session(self):
        session = REAL_SESSION()
        session.trust_env = False
        session.mount("https://", self)
        self.sessions.append(session)
        return session

    def close(self):
        pass

    def send(self, request, **kwargs):
        payload = json.loads(request.body)
        self.calls.append((request, payload, kwargs))
        if isinstance(self.failure, Exception):
            raise self.failure
        endpoint = request.url.rsplit("/", 1)[-1]
        if endpoint == "open":
            value = {"card_id": "fixture-card"}
        elif endpoint == "close":
            value = {"total_actions": sum(self.counts.values())}
        else:
            game = payload["game_id"]
            count = self.counts.get(game, -1) + 1
            self.counts[game] = count
            value = {"game_id": game, "guid": "guid-"+game, "frame": [[[count % 10, 2], [3, 4]], [[1, 2], [3, count % 10]]],
                     "state": "NOT_FINISHED", "levels_completed": 0, "win_levels": 2,
                     "available_actions": [1, 6], "full_reset": count == 0,
                     "action_input": {"id": 0 if endpoint == "RESET" else int(endpoint[-1]), "data": {}}}
        response = requests.Response()
        response.request = request
        response.url = request.url
        response.status_code = 200
        if self.failure == "http":
            response.status_code = 503
        if self.failure == "redirect":
            response.status_code = 302
            response.headers["Location"] = "https://fixture.invalid/other"
        if self.failure == "wrong_guid":
            value["guid"] = "wrong-client"
        if self.failure == "wrong_game":
            value["game_id"] = "wrong-game"
        if self.failure == "conversion":
            value["frame"] = "invalid"
        response._content = b"not-json" if self.failure == "json" else json.dumps(value).encode()
        # Requests itself extracts and propagates this server cookie.
        headers = Message()
        headers.add_header("Set-Cookie", "AFFINITY=fixture; Path=/; Secure")
        response.raw = SimpleNamespace(_original_response=SimpleNamespace(msg=headers))
        return response


class TransportEquivalenceTests(unittest.TestCase):
    def adapter(self):
        wire = WireFixture()
        adapter = RemoteFrameworkAdapter(base_url="https://fixture.invalid", api_key="fixture-key", session_factory=wire.session)
        adapter.open_scorecard()
        return adapter, wire

    def test_mounted_success_trace_sessions_cookies_reasoning_conversion_and_last_response(self):
        wrapper = pinned_wrapper()
        official_wire = WireFixture()
        logger = logging.getLogger("phase0-differential")
        logger.disabled = True
        master = requests.cookies.RequestsCookieJar()
        master.set("AFFINITY", "fixture", domain="fixture.invalid", path="/", secure=True)
        with patch("requests.Session", official_wire.session):
            officials = [wrapper("https://fixture.invalid", EnvironmentInfo(game_id=game), "fixture-key", logger,
                                 "fixture-card", save_recording=False, master_cookie_jar=master)
                         for game in ("fixture-a", "fixture-b")]
        adapter, wire = self.adapter()
        clients = [adapter.bootstrap(game) for game in ("fixture-a", "fixture-b")]
        for official, client in zip(officials, clients):
            self.assertEqual(Observation.from_value(official.observation_space).canonical_hash, client.observation.canonical_hash)
            self.assertEqual(official._guid, client.observation.guid)
            self.assertEqual(official.observation_space.full_reset, client.observation.full_reset)
        self.assertIsNot(clients[0].session, clients[1].session)
        for index in (0, 1, 0):
            reasoning = {"note": 'quoted " unicode 雪', "client": index}
            data = {"x": 7+index, "y": 13+index}
            prior_other = clients[1-index].observation
            returned = officials[index].step(GameAction.ACTION6, data=data, reasoning=reasoning)
            observed = adapter.dispatch(clients[index], ActionDecision(6, data, wire_reasoning=reasoning))
            self.assertIs(returned, officials[index].observation_space)
            self.assertIs(observed, clients[index].observation)
            self.assertIs(prior_other, clients[1-index].observation)
            self.assertEqual(Observation.from_value(returned).canonical_hash, observed.canonical_hash)
        returned = officials[1].step(GameAction.ACTION1)
        observed = adapter.dispatch(clients[1], ActionDecision(1))
        self.assertEqual(Observation.from_value(returned).canonical_hash, observed.canonical_hash)
        candidate_calls = wire.calls[1:]  # scorecard open has a separate lifecycle fixture
        self.assertEqual(len(candidate_calls), len(official_wire.calls))
        for (old, old_payload, _), (new, new_payload, _) in zip(official_wire.calls, candidate_calls):
            self.assertEqual(old.url, new.url)
            self.assertEqual(old.body, new.body)
            self.assertEqual(old_payload, new_payload)
            for header in ("X-API-Key", "Content-Type", "Cookie"):
                self.assertEqual(old.headers[header], new.headers[header])
        self.assertEqual(clients[0].bootstrap_requests, 1)
        self.assertEqual(clients[1].bootstrap_requests, 1)
        self.assertEqual(adapter.close_scorecard()["total_actions"], 4)

    def test_mounted_failure_keeps_last_response_but_replacement_adds_quarantine(self):
        logger = logging.getLogger("phase0-differential")
        logger.disabled = True
        for fault in ("http", "json", "conversion", requests.ReadTimeout()):
            wire = WireFixture()
            with patch("requests.Session", wire.session):
                official = pinned_wrapper()("https://fixture.invalid", EnvironmentInfo(game_id="fixture-a"),
                                             "fixture-key", logger, "fixture-card", save_recording=False)
            before = official.observation_space
            wire.failure = fault
            self.assertIsNone(official.step(GameAction.ACTION1))
            self.assertIs(before, official.observation_space)
            self.assertEqual(len(wire.calls), 2)

    def test_bootstrap_identity_mismatch_cannot_be_repaired_by_second_make(self):
        adapter, wire = self.adapter()
        wire.failure = "wrong_game"
        with self.assertRaises(OutcomeUnknown):
            adapter.bootstrap("fixture-a")
        count = len(wire.calls)
        with self.assertRaises(PreDispatchFailure):
            adapter.bootstrap("fixture-a")
        self.assertEqual(len(wire.calls), count)

    def test_proven_pre_entry_serialization_failure_does_not_send_or_quarantine(self):
        adapter, wire = self.adapter()
        client = adapter.bootstrap("fixture-a")
        before = len(wire.calls)
        with patch("agent.framework_adapter.serialize_action", side_effect=ValueError("pre-entry encoding fault")):
            with self.assertRaises(PreDispatchFailure):
                adapter.dispatch(client, ActionDecision(1))
        self.assertEqual(len(wire.calls), before)
        self.assertFalse(client.quarantined)
        self.assertEqual(client.action_requests, 0)

    def test_all_post_entry_faults_preserve_last_state_and_quarantine_without_retry(self):
        for fault in (requests.ConnectTimeout(), requests.ReadTimeout(), requests.ConnectionError(),
                      "http", "redirect", "json", "conversion", "wrong_guid"):
            with self.subTest(fault=str(fault)):
                adapter, wire = self.adapter()
                client = adapter.bootstrap("fixture-a")
                before = client.observation
                count = len(wire.calls)
                wire.failure = fault
                with self.assertRaises(OutcomeUnknown):
                    adapter.dispatch(client, ActionDecision(1))
                self.assertIs(before, client.observation)
                self.assertTrue(client.quarantined)
                self.assertEqual(str(client.journal.snapshot()[-1].status), "outcome_unknown")
                self.assertEqual(len(wire.calls), count+1)
                wire.failure = None
                with self.assertRaises(OutcomeUnknown):
                    adapter.dispatch(client, ActionDecision(1))
                self.assertEqual(len(wire.calls), count+1)

    def test_preparation_exception_after_session_entry_is_conservatively_unknown(self):
        adapter, wire = self.adapter()
        client = adapter.bootstrap("fixture-a")
        count = len(wire.calls)
        with patch.object(client.session, "prepare_request", side_effect=ValueError("session preparation")):
            with self.assertRaises(OutcomeUnknown):
                adapter.dispatch(client, ActionDecision(1))
        self.assertEqual(len(wire.calls), count)
        self.assertTrue(client.quarantined)

    def test_lifecycle_post_entry_faults_no_retry(self):
        for operation in ("open", "bootstrap", "close"):
            wire = WireFixture()
            adapter = RemoteFrameworkAdapter(base_url="https://fixture.invalid", api_key="fixture-key", session_factory=wire.session)
            if operation != "open":
                adapter.open_scorecard()
            call = {"open": adapter.open_scorecard, "bootstrap": lambda: adapter.bootstrap("fixture-a"),
                    "close": adapter.close_scorecard}[operation]
            wire.failure = requests.ReadTimeout()
            with self.assertRaises(FinalizationUnknown if operation == "close" else OutcomeUnknown):
                call()
            count = len(wire.calls)
            wire.failure = None
            with self.assertRaises((RuntimeError, PreDispatchFailure)):
                call()
            self.assertEqual(len(wire.calls), count)


class M0CompletionRegressionTests(unittest.TestCase):
    def test_later_phase_does_not_erase_completed_gate(self):
        experiments = json.loads((ROOT / "config/experiment_registry.yaml").read_text())
        models = json.loads((ROOT / "config/model_manifest.yaml").read_text())
        for phase in ("phase_0f_m0_complete", "phase_2_contract_frozen_no_treatment_admitted", "phase_3"):
            self.assertTrue(m0_completion_registered({**experiments, "current_phase": phase}, models))
        self.assertFalse(m0_completion_registered({**experiments, "treatments": {}}, models))
        self.assertFalse(m0_completion_registered(experiments, {**models, "status": "pending"}))
        self.assertFalse(m0_completion_registered(experiments, {**models, "candidate_set_frozen": False}))
