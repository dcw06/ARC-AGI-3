"""Adapt the frozen bounded continuation without changing its lifecycle code."""
from copy import deepcopy
import time

from research.feedback_probe_v1.continuation import continuation as original_continuation
from research.initial_geometry_assistance_v1.geometry import digest
from .interface import VARIANTS, policy_request


def continuation(checkpoint, variant, engine, complete, sink, *, model, deadline, now=time.monotonic):
    if variant not in VARIANTS:
        try:
            raise ValueError('unknown summary-probe condition')
        finally:
            engine.close()

    def emit(event):
        event = deepcopy(event)
        if event['kind'] in ('bootstrap_intent', 'summary'):
            if event['variant'] != 'baseline':
                raise ValueError('unexpected underlying continuation variant')
            event['variant'] = variant
        if event['kind'] == 'request':
            event['body'] = policy_request(event['body'], variant)
            event['request_sha256'] = digest(event['body'])
        sink(event)

    def request(body):
        transformed = policy_request(body, variant)
        # The transformation itself is lifecycle work. A slow decoder must
        # not forward a request after the caller's absolute deadline.
        if now() >= deadline:
            raise TimeoutError('summary transformation exhausted admission')
        return complete(transformed)

    result = original_continuation(checkpoint, 'baseline', engine,
        request, emit,
        model=model, deadline=deadline, now=now)
    return dict(result, variant=variant)
