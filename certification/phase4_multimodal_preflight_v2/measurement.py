"""Bounded local measurement primitives; never authorize target execution."""
import json
import math
import os
from pathlib import Path
import threading
import time

from certification.phase4_v1.lifecycle import IsolatedInference


class RequestTimeline:
    def __init__(self, origin, maximum=8800):
        self.origin = origin
        self.maximum = maximum
        self.events = []
        self.lock = threading.Lock()
        self.local = threading.local()

    def now(self):
        return time.monotonic() - self.origin

    def current_id(self):
        return self.local.request_id

    def snapshot(self):
        with self.lock:
            # Events contain only scalar values. Copy the mutable dictionaries,
            # without recursively visiting every scalar while blocking service.
            return [event.copy() for event in self.events]


class MeasuredInference(IsolatedInference):
    """Observe the same callback and executor; never rewrite policy requests."""
    def __init__(self, executor, client_id, timeline):
        super().__init__(executor, client_id)
        self.timeline = timeline

    def execute(self, **kwargs):
        timeline = self.timeline
        with timeline.lock:
            if len(timeline.events) >= timeline.maximum:
                raise ValueError('request evidence capacity exhausted')
            event = {'request_id': f'request-{len(timeline.events):05d}',
                     'client_id': self.client_id, 'submitted_seconds': timeline.now(),
                     'service_started_seconds': None, 'completed_seconds': None,
                     'returned_seconds': None, 'outcome': 'pending', 'error': None}
            timeline.events.append(event)
        callback = kwargs['callback']

        def observed():
            with timeline.lock:
                event['service_started_seconds'] = timeline.now()
            timeline.local.request_id = event['request_id']
            try:
                return callback()
            finally:
                with timeline.lock:
                    event['completed_seconds'] = timeline.now()
                del timeline.local.request_id

        try:
            result = super().execute(**{**kwargs, 'callback': observed})
        except BaseException as exc:
            with timeline.lock:
                event.update(outcome='failed', error=type(exc).__name__)
            raise
        else:
            with timeline.lock:
                event['outcome'] = 'completed'
            return result
        finally:
            with timeline.lock:
                event['returned_seconds'] = timeline.now()


def validate_telemetry(samples, start, end, uuid, *, maximum_gap=1.0):
    """Coverage is sampled evidence, not proof between observations."""
    def number(value):
        return type(value) in (int, float) and math.isfinite(value)
    if (not all(number(v) for v in (start, end, maximum_gap))
            or not 0 <= start < end or maximum_gap <= 0 or not samples or not uuid):
        raise ValueError('missing/invalid telemetry interval')
    previous = start
    for sample in samples:
        t, used = sample.get('elapsed_seconds'), sample.get('used_bytes')
        if (sample.get('uuid') != uuid or not number(t) or not previous <= t <= end
                or t - previous > maximum_gap or type(used) is not int
                or not 0 <= used <= 86 * 1024**3):
            raise ValueError('telemetry identity/resource/coverage violation')
        previous = t
    if end - previous > maximum_gap:
        raise ValueError('telemetry trailing gap')


def save_bounded(path, value, *, byte_limit):
    """Charge every retained byte plus atomic-write temporary peak.

    Caller owns an exclusive output directory and serializes all its writers.
    Never truncate, overwrite a rejected checkpoint, or follow symlinks.
    """
    path = Path(path)
    if type(byte_limit) is not int or byte_limit <= 0 or path.parent.is_symlink():
        raise ValueError('invalid evidence directory/limit')
    payload = json.dumps(value, sort_keys=True, allow_nan=False).encode()
    total = 0
    for entry in path.parent.rglob('*'):
        if entry.is_symlink():
            raise ValueError('symlink in evidence directory')
        if entry.is_file():
            total += entry.stat().st_size
    if total + len(payload) > byte_limit:
        raise ValueError('retained evidence including atomic peak exceeds limit')
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
