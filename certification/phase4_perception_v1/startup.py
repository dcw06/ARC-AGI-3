"""Bounded, flushed startup diagnostics retained by the supervisor's log pipe."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
import time

MODEL_STARTUP_SECONDS = 900


def marker(stage, event, **fields):
    print(json.dumps({'startup': {'stage': stage, 'event': event,
        'utc': datetime.now(timezone.utc).isoformat(), 'monotonic': time.monotonic(),
        'pid': os.getpid(), **fields}}, sort_keys=True), flush=True)


@contextmanager
def stage(name):
    marker(name, 'begin')
    try:
        yield
    except BaseException as exc:
        marker(name, 'error', error_type=type(exc).__name__)
        raise
    else:
        marker(name, 'end')


def check_startup_deadline(elapsed, ready, limit=MODEL_STARTUP_SECONDS):
    if not ready and elapsed > limit:
        raise TimeoutError('model startup ceiling')
