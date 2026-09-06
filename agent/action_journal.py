"""Bounded in-memory write-ahead journals for live transactions."""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, replace
from enum import StrEnum
from threading import RLock
from types import MappingProxyType
from typing import Any, Mapping


class TransactionKind(StrEnum):
    SCORECARD_OPEN = "scorecard_open"
    BOOTSTRAP_RESET = "bootstrap_reset"
    ACTION = "action"
    SCORECARD_CLOSE = "scorecard_close"


class TransactionStatus(StrEnum):
    PREPARED = "prepared"
    FAILED_PRE_DISPATCH = "failed_pre_dispatch"
    DISPATCHED = "dispatched"
    ACKNOWLEDGED = "acknowledged"
    OUTCOME_UNKNOWN = "outcome_unknown"
    FINALIZATION_UNKNOWN = "finalization_unknown"


TERMINAL = frozenset(
    {
        TransactionStatus.FAILED_PRE_DISPATCH,
        TransactionStatus.ACKNOWLEDGED,
        TransactionStatus.OUTCOME_UNKNOWN,
        TransactionStatus.FINALIZATION_UNKNOWN,
    }
)


@dataclass(frozen=True, slots=True)
class JournalEntry:
    transaction_id: str
    sequence: int
    kind: TransactionKind
    status: TransactionStatus
    created_monotonic: float
    updated_monotonic: float
    prepared_fields: Mapping[str, Any]
    fields: Mapping[str, Any]


class JournalTransitionError(RuntimeError):
    pass


class LiveTransactionJournal:
    """Linearizable bounded T0 journal.

    The newest terminal entries are retained for diagnostics. A non-terminal
    entry is never evicted.
    """

    def __init__(self, namespace: str, capacity: int = 256) -> None:
        if capacity < 4:
            raise ValueError("journal capacity must be at least four")
        self.namespace = namespace
        self.capacity = capacity
        self._entries: deque[JournalEntry] = deque()
        self._by_id: dict[str, JournalEntry] = {}
        self._sequence = 0
        self._lock = RLock()

    def prepare(self, kind: TransactionKind, **fields: Any) -> JournalEntry:
        with self._lock:
            self._evict_terminal_if_needed()
            if len(self._entries) >= self.capacity:
                raise JournalTransitionError("T0 journal is full; dispatch denied")
            self._sequence += 1
            now = time.monotonic()
            transaction_id = f"{kind.value}:{self.namespace}:{self._sequence}:{uuid.uuid4().hex[:12]}"
            initial_fields = MappingProxyType(dict(fields))
            entry = JournalEntry(
                transaction_id=transaction_id,
                sequence=self._sequence,
                kind=kind,
                status=TransactionStatus.PREPARED,
                created_monotonic=now,
                updated_monotonic=now,
                prepared_fields=initial_fields,
                fields=initial_fields,
            )
            self._entries.append(entry)
            self._by_id[transaction_id] = entry
            return entry

    def mark_dispatched(self, transaction_id: str) -> JournalEntry:
        return self._transition(transaction_id, TransactionStatus.DISPATCHED, {TransactionStatus.PREPARED})

    def mark_acknowledged(self, transaction_id: str, **fields: Any) -> JournalEntry:
        return self._transition(transaction_id, TransactionStatus.ACKNOWLEDGED, {TransactionStatus.DISPATCHED}, **fields)

    def mark_failed_pre_dispatch(self, transaction_id: str, reason: str) -> JournalEntry:
        return self._transition(
            transaction_id,
            TransactionStatus.FAILED_PRE_DISPATCH,
            {TransactionStatus.PREPARED},
            failure_reason=reason,
        )

    def mark_outcome_unknown(self, transaction_id: str, reason: str) -> JournalEntry:
        return self._transition(
            transaction_id,
            TransactionStatus.OUTCOME_UNKNOWN,
            {TransactionStatus.DISPATCHED},
            failure_reason=reason,
        )

    def mark_finalization_unknown(self, transaction_id: str, reason: str) -> JournalEntry:
        return self._transition(
            transaction_id,
            TransactionStatus.FINALIZATION_UNKNOWN,
            {TransactionStatus.DISPATCHED},
            failure_reason=reason,
        )

    def get(self, transaction_id: str) -> JournalEntry:
        with self._lock:
            return self._by_id[transaction_id]

    def snapshot(self) -> tuple[JournalEntry, ...]:
        with self._lock:
            return tuple(self._entries)

    def _transition(
        self,
        transaction_id: str,
        target: TransactionStatus,
        allowed: set[TransactionStatus],
        **extra: Any,
    ) -> JournalEntry:
        with self._lock:
            current = self._by_id[transaction_id]
            if current.status not in allowed:
                raise JournalTransitionError(f"invalid transition {current.status} -> {target}")
            merged = dict(current.fields)
            merged.update(extra)
            changed = replace(
                current,
                status=target,
                updated_monotonic=time.monotonic(),
                fields=MappingProxyType(merged),
            )
            for index, item in enumerate(self._entries):
                if item.transaction_id == transaction_id:
                    self._entries[index] = changed
                    break
            self._by_id[transaction_id] = changed
            return changed

    def _evict_terminal_if_needed(self) -> None:
        while len(self._entries) >= self.capacity:
            removable = next((item for item in self._entries if item.status in TERMINAL), None)
            if removable is None:
                return
            self._entries.remove(removable)
            self._by_id.pop(removable.transaction_id, None)
