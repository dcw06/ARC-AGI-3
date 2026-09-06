"""Independent deadline state shared by orchestration and workers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Event, Thread


@dataclass(slots=True)
class DeadlineWatchdog:
    hard_seconds: float
    finalization_reserve_seconds: float
    started_monotonic: float = field(default_factory=time.monotonic)
    canceled: Event = field(default_factory=Event)
    _supervisor_stop: Event = field(default_factory=Event)
    _supervisor: Thread | None = field(default=None, init=False)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started_monotonic

    @property
    def stop_admission(self) -> bool:
        return self.canceled.is_set() or self.elapsed >= self.hard_seconds - self.finalization_reserve_seconds

    @property
    def expired(self) -> bool:
        return self.elapsed >= self.hard_seconds

    def cancel(self) -> None:
        self.canceled.set()

    def start_supervisor(self, poll_seconds: float = 0.25) -> None:
        if self._supervisor is not None:
            return

        def supervise() -> None:
            while not self._supervisor_stop.wait(poll_seconds):
                if self.elapsed >= self.hard_seconds - self.finalization_reserve_seconds:
                    self.canceled.set()
                    return

        self._supervisor = Thread(target=supervise, name="arc3-deadline-watchdog", daemon=True)
        self._supervisor.start()

    def stop_supervisor(self) -> None:
        self._supervisor_stop.set()
        if self._supervisor is not None:
            self._supervisor.join(timeout=1.0)
