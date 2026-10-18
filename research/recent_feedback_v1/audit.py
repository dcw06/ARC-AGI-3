"""Check summary arithmetic and replay the unchanged baseline event contract."""
from copy import deepcopy
import json

from research.initial_geometry_assistance_v1.audit import audit_episode as baseline_audit
from research.initial_geometry_assistance_v1.geometry import digest
from .interface import NOTE, SUMMARY_BYTE_LIMIT, VARIANTS, displayed_history


def baseline_request(body, variant):
    if variant not in VARIANTS:
        raise ValueError('unknown feedback variant')
    base = deepcopy(body)
    if variant == 'recent_raw':
        displayed_history(base)
        return base
    part = base['messages'][1]['content'].pop()
    if set(part) != {'type', 'text'} or part['type'] != 'text' or len(part['text'].encode()) > SUMMARY_BYTE_LIMIT:
        raise ValueError('summary text contract')
    summary = json.loads(part['text'])
    step, current, records = displayed_history(base)
    rows = []
    # Independent arithmetic: count differences by row and column, rather than
    # trusting a producer count/bounding box or reconstructing with its helper.
    for info, before, after in records:
        row_counts = [sum(a != b for a, b in zip(left, right)) for left, right in zip(before, after)]
        ys = [y for y, count in enumerate(row_counts) if count]
        xs = [x for x in range(64) if any(before[y][x] != after[y][x] for y in range(64))]
        rows.append(dict(info, changed_cell_count=sum(row_counts),
                         changed_bbox_xyxy_inclusive=[min(xs), min(ys), max(xs), max(ys)] if xs else None,
                         before_grid_equals_current=before == current, after_grid_equals_current=after == current))
    expected = {'schema': 'recent_feedback_summary_v1', 'decision_step': step, 'qualification': NOTE,
                'transitions': rows}
    canonical = json.dumps(expected, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if part['text'] != canonical:
        raise ValueError('summary differs from independently checked displayed evidence')
    return base


def audit_episode(case, variant, events, *, model, cap=24, replay_engine=None):
    if variant not in VARIANTS:
        raise ValueError('unknown feedback variant')
    baseline = deepcopy(events)
    for event in baseline:
        if event['kind'] in ('bootstrap_intent', 'summary'):
            if event['arm'] != variant:
                raise ValueError('episode variant binding differs')
            event['arm'] = 'reviewed'
        if event['kind'] == 'request':
            if event['request_sha256'] != digest(event['body']):
                raise ValueError('variant request hash differs')
            event['body'] = baseline_request(event['body'], variant)
            event['request_sha256'] = digest(event['body'])
    result = baseline_audit(case, 'reviewed', baseline, model=model, cap=cap, replay_engine=replay_engine)
    result.update(arm=variant, summary_independently_verified=variant == 'recent_summary',
                  qualification='Content replay only; not neural inference or live lifecycle certification.')
    return result
