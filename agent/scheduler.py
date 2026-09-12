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
    completed: threading.Event = field(default_factory=threading.Event, compare=False)
    result: Any = field(default=None, compare=False)
    error: BaseException | None = field(default=None, compare=False)


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
                request.canceled.set()
                return request, None
            try:
                return request, request.callback()
            except BaseException as exc:
                request.error = exc
                return request, None
        finally:
            self._queue.task_done()


class InferenceQueueError(RuntimeError):
    """A queued inference did not complete within its frozen authority."""


class QueuedInferenceExecutor:
    """Shared bounded worker service around :class:`FairInferenceQueue`.

    Admission is global FIFO by the queue's monotonically assigned sequence.
    Worker count controls service concurrency without changing that admission
    order.  Callers wait only on their own immutable request record.
    """

    def __init__(
        self,
        *,
        maxsize: int = 110,
        max_age_seconds: float = 300.0,
        worker_count: int = 8,
    ) -> None:
        if worker_count < 1:
            raise ValueError("worker_count must be positive")
        self.queue = FairInferenceQueue(maxsize=maxsize, max_age_seconds=max_age_seconds)
        self._stopping = threading.Event()
        self._workers = tuple(
            threading.Thread(
                target=self._worker,
                name=f"minimum-fair-inference-{index}",
                daemon=True,
            )
            for index in range(worker_count)
        )
        for worker in self._workers:
            worker.start()

    def execute(
        self,
        *,
        client_id: str,
        generation: int,
        state_hash: str,
        callback: Callable[[], Any],
        timeout_seconds: float = 300.0,
    ) -> Any:
        if self._stopping.is_set():
            raise InferenceQueueError("inference service is closed")
        try:
            request = self.queue.submit(client_id, generation, state_hash, callback)
        except queue.Full as exc:
            raise InferenceQueueError("inference queue is full") from exc
        if not request.completed.wait(timeout_seconds):
            request.canceled.set()
            raise InferenceQueueError("inference request timed out")
        if request.error is not None:
            raise request.error
        if request.canceled.is_set():
            raise InferenceQueueError("inference request was canceled or stale")
        return request.result

    def cancel_client(self, client_id: str) -> None:
        self.queue.cancel_client(client_id)

    def close(self) -> None:
        self._stopping.set()
        for worker in self._workers:
            worker.join(timeout=1.0)

    def __enter__(self) -> "QueuedInferenceExecutor":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def _worker(self) -> None:
        while not self._stopping.is_set() or self.queue.size:
            serviced = self.queue.service_one()
            if serviced is None:
                self._stopping.wait(0.001)
                continue
            request, value = serviced
            request.result = value
            if value is None and (
                request.canceled.is_set()
                or time.monotonic() - request.submitted_monotonic > self.queue.max_age_seconds
            ):
                request.canceled.set()
            request.completed.set()
