"""Pinned lifecycle adapter and the only production environment-call boundary."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

import requests
from arcengine import GameState
from requests.adapters import HTTPAdapter
from requests.cookies import RequestsCookieJar
from urllib3.util.retry import Retry

from .action import ActionDecision, ActionValidationError, serialize_action, wire_json_bytes
from .action_journal import LiveTransactionJournal, TransactionKind
from .state import Observation


class OutcomeUnknown(RuntimeError):
    """Transport was entered but no trustworthy resulting state is available."""


class PreDispatchFailure(RuntimeError):
    """Failure was proven to occur before transport entry."""


class FinalizationUnknown(RuntimeError):
    """Scorecard close may have reached the backend."""


class AdapterClient(Protocol):
    game_id: str
    observation: Observation
    journal: LiveTransactionJournal


def _session_without_retries() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=0, connect=0, read=0, redirect=0, status=0)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


@dataclass(slots=True)
class RemoteClient:
    game_id: str
    observation: Observation
    session: requests.Session
    journal: LiveTransactionJournal
    bootstrap_requests: int = 1
    action_requests: int = 0
    quarantined: bool = False
    closed: bool = False


@dataclass(slots=True)
class LocalClient:
    game_id: str
    observation: Observation
    environment: Any
    journal: LiveTransactionJournal
    bootstrap_requests: int = 1
    action_requests: int = 0
    quarantined: bool = False
    closed: bool = False


class RemoteFrameworkAdapter:
    """Direct gateway adapter matching the pinned arc-agi 0.9.9 wire contract."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        competition_mode: bool = True,
        timeout_seconds: float = 10.0,
        session_factory: Any = _session_without_retries,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.competition_mode = competition_mode
        self.timeout_seconds = timeout_seconds
        self._session_factory = session_factory
        self._master_session = session_factory()
        self._master_cookie_jar = RequestsCookieJar()
        self._cookie_lock = threading.Lock()
        self.lifecycle_journal = LiveTransactionJournal("lifecycle", capacity=128)
        self.scorecard_id: str | None = None
        self._opened = False
        self._closed = False
        self._made_games: set[str] = set()

    @property
    def headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Accept": "application/json"}

    def list_game_ids(self) -> tuple[str, ...]:
        response = self._master_session.get(
            f"{self.base_url}/api/games",
            headers=self.headers,
            timeout=self.timeout_seconds,
            allow_redirects=False,
        )
        if response.is_redirect:
            raise RuntimeError("game inventory redirected")
        response.raise_for_status()
        values = response.json()
        return tuple(str(item["game_id"]) for item in values)

    def open_scorecard(self, tags: list[str] | None = None) -> str:
        if self._opened:
            raise RuntimeError("scorecard open already attempted")
        self._opened = True
        payload: dict[str, Any] = {"tags": tags or ["plan8-e0"]}
        if self.competition_mode:
            payload["competition_mode"] = True
        encoded = self._encode(payload)
        entry = self.lifecycle_journal.prepare(
            TransactionKind.SCORECARD_OPEN,
            payload_sha256=encoded[1],
        )
        try:
            response = self._post_once(
                self._master_session,
                "/api/scorecard/open",
                payload,
                entry.transaction_id,
                payload_bytes=encoded[0],
            )
            card_id = str(response.json()["card_id"])
            if not card_id:
                raise ValueError("empty card id")
        except Exception as exc:
            self.lifecycle_journal.mark_outcome_unknown(entry.transaction_id, type(exc).__name__)
            self._master_session.close()
            raise OutcomeUnknown("scorecard open outcome is unknown") from exc
        self.lifecycle_journal.mark_acknowledged(entry.transaction_id, card_id=card_id)
        self.scorecard_id = card_id
        return card_id

    def bootstrap(self, game_id: str) -> RemoteClient:
        if not self.scorecard_id:
            raise PreDispatchFailure("scorecard is not open")
        if game_id in self._made_games:
            raise PreDispatchFailure("environment make/bootstrap already attempted")
        self._made_games.add(game_id)
        payload = {"card_id": self.scorecard_id, "game_id": game_id}
        encoded = self._encode(payload)
        journal = LiveTransactionJournal(game_id, capacity=256)
        entry = journal.prepare(
            TransactionKind.BOOTSTRAP_RESET,
            requested_game_id=game_id,
            scorecard_id=self.scorecard_id,
            payload_sha256=encoded[1],
        )
        session = self._session_factory()
        try:
            response = self._post_once(
                session,
                "/api/cmd/RESET",
                payload,
                entry.transaction_id,
                journal=journal,
                payload_bytes=encoded[0],
            )
            observation = Observation.from_value(response.json())
            if observation.game_id and observation.game_id != game_id:
                raise ValueError("bootstrap returned a different game id")
        except Exception as exc:
            journal.mark_outcome_unknown(entry.transaction_id, type(exc).__name__)
            session.close()
            raise OutcomeUnknown(f"bootstrap outcome unknown for {game_id}") from exc
        journal.mark_acknowledged(
            entry.transaction_id,
            guid=observation.guid,
            observation_hash=observation.canonical_hash,
            legal_actions=list(observation.available_actions),
        )
        return RemoteClient(game_id, observation, session, journal)

    def dispatch(self, client: RemoteClient, decision: ActionDecision) -> Observation:
        if client.quarantined:
            raise OutcomeUnknown("client is quarantined")
        try:
            serialized = serialize_action(
                decision,
                game_id=client.game_id,
                guid=client.observation.guid,
                legal_actions=client.observation.available_actions,
                allow_level_reset=client.observation.state is GameState.GAME_OVER,
            )
        except Exception as exc:
            raise PreDispatchFailure(str(exc)) from exc
        entry = client.journal.prepare(
            TransactionKind.ACTION,
            decision_id=decision.decision_id,
            action_id=decision.action_id,
            pre_state_hash=client.observation.canonical_hash,
            legal_actions=list(client.observation.available_actions),
            payload_sha256=serialized.payload_sha256,
        )
        try:
            response = self._post_once(
                client.session,
                f"/api/cmd/{serialized.endpoint}",
                dict(serialized.payload),
                entry.transaction_id,
                journal=client.journal,
                payload_bytes=serialized.payload_bytes,
            )
            observation = Observation.from_value(response.json())
            if observation.guid != client.observation.guid:
                raise ValueError("response guid does not match client session")
        except Exception as exc:
            client.action_requests += 1
            client.quarantined = True
            client.journal.mark_outcome_unknown(entry.transaction_id, type(exc).__name__)
            raise OutcomeUnknown(f"action outcome unknown for {client.game_id}") from exc
        client.action_requests += 1
        client.journal.mark_acknowledged(
            entry.transaction_id,
            post_state_hash=observation.canonical_hash,
        )
        client.observation = observation
        return observation

    def close_scorecard(self) -> dict[str, Any]:
        if not self.scorecard_id:
            raise PreDispatchFailure("no scorecard to close")
        if self._closed:
            raise RuntimeError("scorecard close already attempted")
        self._closed = True
        payload = {"card_id": self.scorecard_id}
        encoded = self._encode(payload)
        entry = self.lifecycle_journal.prepare(
            TransactionKind.SCORECARD_CLOSE,
            card_id=self.scorecard_id,
            payload_sha256=encoded[1],
        )
        try:
            response = self._post_once(
                self._master_session,
                "/api/scorecard/close",
                payload,
                entry.transaction_id,
                payload_bytes=encoded[0],
            )
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("close response is not an object")
        except Exception as exc:
            self.lifecycle_journal.mark_finalization_unknown(entry.transaction_id, type(exc).__name__)
            self._master_session.close()
            raise FinalizationUnknown("scorecard close outcome is unknown") from exc
        self.lifecycle_journal.mark_acknowledged(entry.transaction_id)
        self._master_session.close()
        return result

    @staticmethod
    def finalize_client(client: RemoteClient) -> None:
        if not client.closed:
            client.closed = True
            client.session.close()

    def _post_once(
        self,
        session: requests.Session,
        path: str,
        payload: dict[str, Any],
        transaction_id: str,
        *,
        journal: LiveTransactionJournal | None = None,
        payload_bytes: bytes | None = None,
    ) -> requests.Response:
        target_journal = journal or self.lifecycle_journal
        target_journal.mark_dispatched(transaction_id)
        with self._cookie_lock:
            session.cookies.update(self._master_cookie_jar)
        body = payload_bytes if payload_bytes is not None else wire_json_bytes(payload)
        response = session.post(
            f"{self.base_url}{path}",
            data=body,
            headers={**self.headers, "Content-Type": "application/json"},
            timeout=self.timeout_seconds,
            allow_redirects=False,
        )
        with self._cookie_lock:
            self._master_cookie_jar.update(session.cookies)
        if response.is_redirect:
            raise requests.TooManyRedirects("redirect disabled for live transaction")
        response.raise_for_status()
        return response

    @staticmethod
    def _encode(payload: dict[str, Any]) -> tuple[bytes, str]:
        import hashlib

        raw = wire_json_bytes(payload)
        return raw, hashlib.sha256(raw).hexdigest()


class LocalFrameworkAdapter:
    """Instrumented local emulation; never labeled as Kaggle authority."""

    def __init__(self, arcade: Any, *, seed_by_game: Mapping[str, int] | None = None) -> None:
        self.arcade = arcade
        self.seed_by_game = dict(seed_by_game or {})
        if any(
            not isinstance(game_id, str)
            or not game_id
            or isinstance(seed, bool)
            or not isinstance(seed, int)
            for game_id, seed in self.seed_by_game.items()
        ):
            raise ValueError("local game seeds must map non-empty IDs to integers")
        self.lifecycle_journal = LiveTransactionJournal("local-lifecycle", capacity=128)
        self.scorecard_id: str | None = None
        self._made_games: set[str] = set()
        self._closed = False

    def list_game_ids(self) -> tuple[str, ...]:
        return tuple(str(item.game_id) for item in self.arcade.get_environments())

    def open_scorecard(self, tags: list[str] | None = None) -> str:
        entry = self.lifecycle_journal.prepare(TransactionKind.SCORECARD_OPEN)
        self.lifecycle_journal.mark_dispatched(entry.transaction_id)
        try:
            self.scorecard_id = str(self.arcade.open_scorecard(tags=tags or ["plan8-e0-local"]))
        except Exception as exc:
            self.lifecycle_journal.mark_outcome_unknown(entry.transaction_id, type(exc).__name__)
            raise OutcomeUnknown("local scorecard open failed") from exc
        self.lifecycle_journal.mark_acknowledged(entry.transaction_id, card_id=self.scorecard_id)
        return self.scorecard_id

    def bootstrap(self, game_id: str) -> LocalClient:
        if not self.scorecard_id or game_id in self._made_games:
            raise PreDispatchFailure("invalid or duplicate local bootstrap")
        self._made_games.add(game_id)
        journal = LiveTransactionJournal(game_id, capacity=256)
        entry = journal.prepare(TransactionKind.BOOTSTRAP_RESET, requested_game_id=game_id, scorecard_id=self.scorecard_id)
        journal.mark_dispatched(entry.transaction_id)
        try:
            make_kwargs: dict[str, Any] = {
                "scorecard_id": self.scorecard_id,
                "save_recording": False,
            }
            if game_id in self.seed_by_game:
                make_kwargs["seed"] = self.seed_by_game[game_id]
            environment = self.arcade.make(game_id, **make_kwargs)
            if environment is None or environment.observation_space is None:
                raise ValueError("make returned no initial observation")
            observation = Observation.from_value(environment.observation_space)
        except Exception as exc:
            journal.mark_outcome_unknown(entry.transaction_id, type(exc).__name__)
            raise OutcomeUnknown(f"local bootstrap failed for {game_id}") from exc
        journal.mark_acknowledged(entry.transaction_id, guid=observation.guid, observation_hash=observation.canonical_hash)
        return LocalClient(game_id, observation, environment, journal)

    def dispatch(self, client: LocalClient, decision: ActionDecision) -> Observation:
        if client.quarantined:
            raise OutcomeUnknown("client is quarantined")
        try:
            serialized = serialize_action(
                decision,
                game_id=client.game_id,
                guid=client.observation.guid,
                legal_actions=client.observation.available_actions,
                allow_level_reset=client.observation.state is GameState.GAME_OVER,
            )
        except ActionValidationError as exc:
            raise PreDispatchFailure(str(exc)) from exc
        entry = client.journal.prepare(
            TransactionKind.ACTION,
            decision_id=decision.decision_id,
            action_id=decision.action_id,
            pre_state_hash=client.observation.canonical_hash,
            payload_sha256=serialized.payload_sha256,
        )
        client.journal.mark_dispatched(entry.transaction_id)
        try:
            from arcengine import GameAction

            raw = client.environment.step(
                GameAction.from_id(decision.action_id),
                data=dict(decision.action_data),
                reasoning=dict(decision.wire_reasoning) or None,
            )
            if raw is None:
                raise ValueError("local wrapper returned no observation")
            observation = Observation.from_value(raw)
        except Exception as exc:
            client.action_requests += 1
            client.quarantined = True
            client.journal.mark_outcome_unknown(entry.transaction_id, type(exc).__name__)
            raise OutcomeUnknown(f"local action outcome unknown for {client.game_id}") from exc
        client.action_requests += 1
        client.journal.mark_acknowledged(entry.transaction_id, post_state_hash=observation.canonical_hash)
        client.observation = observation
        return observation

    def close_scorecard(self) -> dict[str, Any]:
        if not self.scorecard_id or self._closed:
            raise PreDispatchFailure("invalid local close")
        self._closed = True
        entry = self.lifecycle_journal.prepare(TransactionKind.SCORECARD_CLOSE, card_id=self.scorecard_id)
        self.lifecycle_journal.mark_dispatched(entry.transaction_id)
        try:
            result = self.arcade.close_scorecard(self.scorecard_id)
        except Exception as exc:
            self.lifecycle_journal.mark_finalization_unknown(entry.transaction_id, type(exc).__name__)
            raise FinalizationUnknown("local scorecard close failed") from exc
        self.lifecycle_journal.mark_acknowledged(entry.transaction_id)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return {"result": result}

    @staticmethod
    def finalize_client(client: LocalClient) -> None:
        client.closed = True
