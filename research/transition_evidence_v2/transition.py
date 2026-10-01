"""Transition records, version 2 (draft, not frozen): version 1 records plus identity, context, available actions
and an optional masked view.

A version 2 record is built by version 1's `build` and then extended. Nothing version 1 computes is recomputed or
changed here, so `to_v1(build(raw, mask))` equals `transition_evidence_v1.transition.build(raw)` exactly (tested).

Input is version 1's raw evidence. Observations may also carry `available_actions` (a list of action ids), as the
environment reports them; when an observation omits it, the field is `absent`, never assumed.

A mask is {'id': str, 'frame_shape': [height, width], 'rects_xyxy': [[x0, y0, x1, y1], ...] (inclusive grid
cells, frame read as grid[y][x]), 'provenance': {'kind': 'declared' | 'detected_online', 'source': str,
'basis': str}}. The masked view repeats version 1's measurements over the cells outside the mask; changes inside
the mask are counted separately. A mask applies only to frames of its declared shape.
"""
import copy

from research.transition_evidence_v1 import transition as T1
from research.transition_evidence_v2 import vocabulary as V

ADDED = ('context', 'masked')  # top-level blocks version 2 adds; identity gains `record_id`


def record_id(identity):
    return f"{identity['episode_id']}#{identity['action_index']}"


def mask_problems(mask):
    """[] for a well-formed mask, else the reasons it is malformed."""
    if not isinstance(mask, dict) or set(mask) != {'id', 'frame_shape', 'rects_xyxy', 'provenance'}:
        return ['a mask has exactly id, frame_shape, rects_xyxy and provenance']
    problems = []
    if not isinstance(mask['id'], str) or not mask['id']:
        problems.append('mask id must be a non-empty string')
    shape = mask['frame_shape']
    if not (isinstance(shape, list) and len(shape) == 2 and all(type(v) is int and v > 0 for v in shape)):
        return problems + ['frame_shape must be [height, width] of positive integers']
    height, width = shape
    rects = mask['rects_xyxy']
    if not isinstance(rects, list) or not rects:
        problems.append('rects_xyxy must be a non-empty list')
    else:
        for r in rects:
            if not (isinstance(r, list) and len(r) == 4 and all(type(v) is int for v in r)
                    and 0 <= r[0] <= r[2] < width and 0 <= r[1] <= r[3] < height):
                problems.append(f'rectangle {r!r} is not inside a {height}x{width} frame')
    p = mask['provenance']
    if not (isinstance(p, dict) and set(p) == {'kind', 'source', 'basis'} and p['kind'] in V.MASK_PROVENANCE
            and all(isinstance(p[k], str) and p[k] for k in ('source', 'basis'))):
        problems.append('provenance needs kind (declared or detected_online), source and basis')
    return problems


def _inside(mask, x, y):
    return any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in mask['rects_xyxy'])


def _split(reference, frame, mask):
    """(outside, inside) changed-cell counts, or None when the frames differ in shape or the mask does not apply."""
    if T1.shape(reference) != T1.shape(frame) or T1.shape(frame) != mask['frame_shape']:
        return None
    cells = T1.compare(reference, frame)[1]
    inside = sum(1 for x, y in cells if _inside(mask, x, y))
    return len(cells) - inside, inside


def _masked(raw, record, mask):
    """The masked view for one record. Mirrors version 1's `measure` rules on the cells outside the mask."""
    if mask is None:
        return {'status': 'unavailable', 'reason': 'no mask was supplied'}
    view = {'mask': copy.deepcopy(mask)}
    availability = record['observations']['availability']
    if record['dispatch']['status'] != V.ACKNOWLEDGED or availability['status'] == V.MISSING:
        return {'status': 'unavailable', 'reason': availability['reason'], **view}
    pre = raw['before']['frames'][-1]
    if T1.shape(pre) != mask['frame_shape']:
        return {'status': 'unavailable', 'reason': 'the mask does not apply to a pre-action frame of this shape', **view}
    frames = []
    for row, grid in zip(record['measurements']['frames'], raw['outcome']['after']['frames']):
        if not row['valid']:
            frames.append({'index': row['index'], 'valid': False})
            continue
        split = _split(pre, grid, mask)
        if split is None:  # a shape change: the frame differs, but outside/inside counts are undefined
            frames.append({'index': row['index'], 'valid': True, 'differs_outside': V.measured(True),
                           'changed_outside': V.unavailable('the frame differs in shape; the mask does not apply'),
                           'changed_inside': V.unavailable('the frame differs in shape; the mask does not apply')})
        else:
            frames.append({'index': row['index'], 'valid': True, 'differs_outside': V.measured(split[0] > 0),
                           'changed_outside': V.measured(split[0]), 'changed_inside': V.measured(split[1])})
    valid = [f for f in frames if f['valid']]
    if any(f['differs_outside']['value'] for f in valid):
        any_outside = V.measured(True)
    elif availability['status'] == V.PARTIAL:
        any_outside = V.unavailable('no valid returned frame differs outside the mask, but some frames are invalid')
    else:
        any_outside = V.measured(False)
    final = frames[-1]
    final_equals = (V.measured(not final['differs_outside']['value']) if final['valid']
                    else V.unavailable('the final returned frame is invalid'))
    if final_equals['status'] != 'measured':
        visual = {'status': V.INDETERMINATE, 'reason': final_equals['reason']}
    elif not final_equals['value']:
        visual = {'status': V.FINAL_FRAME_DIFFERS, 'reason': 'the final returned frame differs outside the mask'}
    elif any_outside['status'] == 'measured' and any_outside['value']:
        visual = {'status': V.CHANGED_THEN_RETURNED,
                  'reason': 'an earlier frame differed outside the mask; the final frame equals the pre-action frame there'}
    elif any_outside['status'] == 'measured':
        visual = {'status': V.NO_OBSERVED_CHANGE,
                  'reason': 'no returned frame differs outside the mask; changes inside the mask are set aside, not denied'}
    else:
        visual = {'status': V.INDETERMINATE, 'reason': any_outside['reason']}
    inside_counts = [f['changed_inside'] for f in valid]
    if any(c['status'] == 'measured' and c['value'] > 0 for c in inside_counts):
        mask_changed = V.measured(True)
    elif all(c['status'] == 'measured' for c in inside_counts) and availability['status'] == V.COMPLETE:
        mask_changed = V.measured(False)
    else:
        mask_changed = V.unavailable('some returned frames are invalid or differ in shape')
    return {'status': 'measured', **view, 'frames': frames, 'any_returned_frame_differs_outside': any_outside,
            'final_frame_equals_pre_outside': final_equals, 'visual_effect_outside': visual,
            'mask_region_changed': mask_changed}


def _actions(observation):
    actions = observation.get('available_actions')
    if actions is None:
        return V.absent('the producer did not retain available actions')
    return V.measured(sorted(copy.deepcopy(actions)))


def extend(raw, record, mask=None):
    """Add the version 2 blocks to a version 1 record built from `raw` (the record is not otherwise changed)."""
    problems = mask_problems(mask) if mask is not None else []
    if problems:
        raise ValueError('malformed mask: ' + '; '.join(problems))
    record = copy.deepcopy(record)
    record['version'] = V.VERSION
    record['identity']['record_id'] = record_id(record['identity'])
    before = raw['before']
    record['context'] = {'levels_completed_before': V.measured(before['levels_completed']),
                         'state_before': V.measured(before.get('state')),
                         'available_actions_before': _actions(before)}
    if record['dispatch']['status'] == V.ACKNOWLEDGED:
        record['environment']['reported']['available_actions_after'] = _actions(raw['outcome']['after'])
    record['masked'] = _masked(raw, record, mask)
    return record


def build(raw, mask=None):
    return extend(raw, T1.build(raw), mask)


def history(raws, masks=None):
    """Version 1 history (segments, continuity) extended per record. `masks` is None, one mask for every record, or a
    list with one mask (or None) per raw transition."""
    per = masks if isinstance(masks, list) else [masks] * len(raws)
    if len(per) != len(raws):
        raise ValueError('one mask per transition')
    return [extend(raw, record, mask) for raw, record, mask in zip(raws, T1.history(raws), per)]


def to_v1(record):
    """The version 1 record contained in a version 2 record."""
    record = copy.deepcopy(record)
    record['version'] = V.V1_VERSION
    del record['identity']['record_id']
    for key in ADDED:
        del record[key]
    if record['environment'].get('reported'):
        del record['environment']['reported']['available_actions_after']
    return record


def model_statement(transition_identity, kind, content, source):
    """A model's claim about a transition, kept apart from measurements, citing the transition by record_id."""
    statement = T1.model_statement(transition_identity, kind, content, source)
    statement['version'] = V.VERSION
    statement['about_record_id'] = record_id(transition_identity)
    return statement


def validate(record):
    """Version 1's checks on the contained record, plus the version 2 rules."""
    problems = T1.validate(to_v1(record))
    if record.get('version') != V.VERSION:
        problems.append('not a version 2 record')
    if record['identity'].get('record_id') != record_id(record['identity']):
        problems.append('record_id does not match episode_id and action_index')
    m = record['masked']
    if m['status'] == 'measured':
        problems += ['mask: ' + p for p in mask_problems(m['mask'])]
        if record['dispatch']['status'] != V.ACKNOWLEDGED:
            problems.append('a masked measurement exists for an action whose result was not observed')
        visual = m['visual_effect_outside']['status']
        if visual not in V.VISUAL:
            problems.append('masked visual effect outside the vocabulary')
        if visual == V.NO_OBSERVED_CHANGE and m['any_returned_frame_differs_outside'] != V.measured(False):
            problems.append('masked no_observed_change without a measured absence of change outside the mask')
        if (record['measurements']['visual_effect']['status'] == V.NO_OBSERVED_CHANGE
                and visual != V.NO_OBSERVED_CHANGE):
            problems.append('a mask cannot create a change that the unmasked frames do not show')
    elif m['status'] != 'unavailable' or not m.get('reason'):
        problems.append('masked view: untyped or unexplained')
    return problems
