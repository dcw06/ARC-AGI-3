"""Bounded fair request admission used before model-aware scheduling exists."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(order=True, slots=True)
class ScheduledRequest:
    sequence: int
    client_id: str = field(compare=False)
    generation: int = field(compare=False)
    state_hash: str = field(compare=False)
    callback: Callable[[], Any] = field(compare=False)
    submitted_monotonic: float = field(default_factory=time.monotonic, compare=False)
    canceled: threading.Event = field(default_factory=threading.Event, compare=False)


class FairInferenceQueue:
    """Minimal bounded FIFO service with stale/cancel rejection."""

    def __init__(self, maxsize: int = 110, max_age_seconds: float = 300.0) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        self._queue: queue.PriorityQueue[ScheduledRequest] = queue.PriorityQueue(maxsize=maxsize)
        self.max_age_seconds = max_age_seconds
        self._sequence = 0
        self._lock = threading.Lock()
        self._latest_generation: dict[str, int] = {}
        self.max_observed_size = 0
        self.max_observed_age = 0.0

    @property
    def size(self) -> int:
        return self._queue.qsize()

    def submit(self, client_id: str, generation: int, state_hash: str, callback: Callable[[], Any]) -> ScheduledRequest:
        with self._lock:
            self._sequence += 1
            self._latest_generation[client_id] = max(generation, self._latest_generation.get(client_id, generation))
            request = ScheduledRequest(self._sequence, client_id, generation, state_hash, callback)
        self._queue.put_nowait(request)
        self.max_observed_size = max(self.max_observed_size, self._queue.qsize())
        return request

    def cancel_client(self, client_id: str) -> None:
        with self._lock:
            self._latest_generation[client_id] = self._latest_generation.get(client_id, 0) + 1

    def service_one(self) -> tuple[ScheduledRequest, Any] | None:
        try:
            request = self._queue.get_nowait()
        except queue.Empty:
            return None
        age = time.monotonic() - request.submitted_monotonic
        self.max_observed_age = max(self.max_observed_age, age)
        latest = self._latest_generation.get(request.client_id, request.generation)
        try:
            if request.canceled.is_set() or request.generation != latest or age > self.max_age_seconds:
                return request, None
            return request, request.callback()
        finally:
            self._queue.task_done()
