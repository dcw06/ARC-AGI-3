"""Verify summary arithmetic independently, then replay the original contract."""
from copy import deepcopy

from research.feedback_probe_v1.audit import audit_continuation as original_audit
from research.feedback_probe_v1.interface import recognition_request as original_recognition
from research.initial_geometry_assistance_v1.geometry import digest
from research.recent_feedback_v1.audit import baseline_request
from .interface import VARIANTS


def audit_recognition_request(checkpoint, variant, body):
    if variant not in VARIANTS:
        raise ValueError('unknown recognition condition')
    expected = original_recognition(checkpoint['base_request'])
    if variant == 'recent_summary':
        # The independent old auditor recomputes row/column differences. It
        # does not call the producer's recent_summary() helper.
        part = deepcopy(body['messages'][1]['content'][-2])
        policy = deepcopy(checkpoint['base_request'])
        policy['messages'][1]['content'].append(part)
        base = baseline_request(policy, variant)
        if digest(base) != digest(checkpoint['base_request']):
            raise ValueError('recognition display differs')
        expected['messages'][1]['content'].insert(-1, part)
    if digest(body) != digest(expected):
        raise ValueError('full factual request differs from frozen evidence')
    return True


def audit_continuation(checkpoint, variant, events, *, model, replay_engine=None):
    try:
        if variant not in VARIANTS:
            raise ValueError('unknown continuation condition')
        normalized = deepcopy(events)
        for event in normalized:
            if event['kind'] in ('bootstrap_intent', 'summary'):
                if event.get('variant') != variant:
                    raise ValueError('condition identity changed')
                event['variant'] = 'baseline'
            if event['kind'] == 'request':
                if event.get('request_sha256') != digest(event['body']):
                    raise ValueError('request hash differs')
                event['body'] = baseline_request(event['body'], variant)
                event['request_sha256'] = digest(event['body'])
    except BaseException:
        # A replay interpreter can already exist when argument validation or
        # independent arithmetic refuses. Ownership transfers only below.
        if replay_engine is not None:
            replay_engine.close()
        raise
    result = original_audit(checkpoint, 'baseline', normalized, model=model, replay_engine=replay_engine)
    return dict(result, variant=variant,
                summary_independently_verified=variant == 'recent_summary')
