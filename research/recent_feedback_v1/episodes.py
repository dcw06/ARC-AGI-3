"""Adapt the existing CPU episode path without modifying the sealed r5 source."""
from copy import deepcopy

from research.initial_geometry_assistance_v1.episodes import episode as baseline_episode
from research.initial_geometry_assistance_v1.geometry import digest
from .interface import VARIANTS, request_for_variant


def episode(case, variant, engine, complete, sink, **kwargs):
    """Only reviewed geometry is supplied. Callers must supervise all callbacks.

    Both the request journal and callback receive the identical derived request.
    No additional generation, action override, repair or retry is performed.
    """
    if variant not in VARIANTS:
        raise ValueError('unknown feedback variant')

    def journal(event):
        event = deepcopy(event)
        if event['kind'] in ('bootstrap_intent', 'summary'):
            event['arm'] = variant
        if event['kind'] == 'request':
            event['body'] = request_for_variant(event['body'], variant)
            event['request_sha256'] = digest(event['body'])
        sink(event)

    result = baseline_episode(case, 'reviewed', engine,
                              lambda body: complete(request_for_variant(body, variant)), journal, **kwargs)
    return dict(result, arm=variant)
