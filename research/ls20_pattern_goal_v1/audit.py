"""Rebuild plans and model requests, replay actual actions, compare every event."""
import math
from research.initial_geometry_assistance_v1.geometry import digest
from .controller import run_episode


def audit_episode(initial, retained, replay_factory, *, assessment=None, action_cap=40, model_enabled=None):
    """Content validation only; process/provider lifecycle requires separate proof."""
    emitted = []
    requests = [e for e in retained if e['kind'] == 'model_request']
    replies = [e for e in retained if e['kind'] == 'model_response']
    if model_enabled is None: model_enabled = bool(requests)
    if type(model_enabled) is not bool or (requests and not model_enabled):
        raise ValueError('declared model-callback scope differs')
    if len(replies) > len(requests): raise ValueError('model response lacks a request')
    stops = [e for e in retained if e['kind'] == 'admission_stop']
    if len(stops) > 1: raise ValueError('multiple deadline stops')
    if stops:
        stop = stops[0]
        if (set(stop) != {'kind', 'check_index', 'overrun_seconds'} or
                type(stop['check_index']) is not int or stop['check_index'] < 1 or
                type(stop['overrun_seconds']) not in (int, float) or
                not math.isfinite(stop['overrun_seconds']) or not 0 <= stop['overrun_seconds'] < 300):
            raise ValueError('deadline-stop receipt differs')
    position = checks = 0

    def now():
        nonlocal checks
        checks += 1
        return stops[0]['overrun_seconds'] if stops and checks == stops[0]['check_index'] else -1

    def complete(body):
        nonlocal position
        if position >= len(replies): raise ValueError('missing model reply in replay')
        request, response = requests[position], replies[position]
        if (request['index'] != position or response['index'] != position or
                response['purpose'] != request['purpose'] or digest(body) != request['request_sha256'] or
                digest(body) != digest(request['body'])):
            raise ValueError('reconstructed model request differs')
        position += 1
        return response['text']

    result = run_episode(initial, replay_factory(), emitted.append, assessment=assessment,
                         complete=complete if model_enabled else None, deadline=0, now=now, action_cap=action_cap)
    if digest(emitted) != digest(retained) or position != len(replies):
        raise ValueError('Pattern matches, DFS plans, model calls, actions or outcome differ from independent replay')
    return dict(content_replay_verified=True, result=result, model_replies_reused=len(replies),
                new_model_generations=0, lifecycle_certified=False,
                qualification='Independent observation/action/planner replay; not live GPU certification.')
