"""Transition records, version 2 (draft, not frozen): version 1 records plus identity, context, available actions
and an optional masked view.

A version 2 record is built by version 1's `build` and then extended. Nothing version 1 computes is recomputed or
changed here, so `to_v1(build(raw, mask))` equals `transition_evidence_v1.transition.build(raw)` exactly (tested).

Input is version 1's raw evidence. Observations may also carry `available_actions` (a list of action ids), as the
environment reports them; when an observation omits it, the field is `absent`, never assumed.

A mask is {'id': str, 'frame_shape': [height, width], 'rects_xyxy': [[x0, y0, x1, y1], ...] (inclusive grid
cells, frame read as grid[y][x]), 'provenance': {'kind': 'declared' | 'detected_online', 'source': str,
'basis': str}}. The masked view repeats version 1's measurements over the cells outside the declared region; changes
inside the region are counted separately. A mask applies only to frames of its declared shape. It never touches
dispatch, environment events, progress or available actions: those are reported whether or not a mask is supplied.

Two checks: `validate(record)` checks one record's structure and internal consistency; `verify(record, raw, mask)`
rebuilds the record from its raw evidence and requires an exact match, which also catches a consistent forgery.
"""
import copy

from research.transition_evidence_v1 import transition as T1
from research.transition_evidence_v2 import vocabulary as V

ADDED = ('context', 'masked')  # top-level blocks version 2 adds; identity gains `record_id`
REPORTED_ADDED = ('available_actions_after', 'available_actions_changed')
OUTSIDE = 'the declared region'


def record_id(identity):
    return f"{identity['episode_id']}#{identity['action_index']}"


def _int(value):
    return type(value) is int


def mask_problems(mask):
    """[] for a well-formed mask, else the reasons it is malformed."""
    if not isinstance(mask, dict) or set(mask) != {'id', 'frame_shape', 'rects_xyxy', 'provenance'}:
        return ['a mask has exactly id, frame_shape, rects_xyxy and provenance']
    problems = []
    if not isinstance(mask['id'], str) or not mask['id']:
        problems.append('mask id must be a non-empty string')
    shape = mask['frame_shape']
    if not (isinstance(shape, list) and len(shape) == 2 and all(_int(v) and v > 0 for v in shape)):
        return problems + ['frame_shape must be [height, width] of positive integers']
    height, width = shape
    rects = mask['rects_xyxy']
    if not isinstance(rects, list) or not rects:
        problems.append('rects_xyxy must be a non-empty list')
    else:
        for r in rects:
            if not (isinstance(r, list) and len(r) == 4 and all(_int(v) for v in r)
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


def _summary(frames, availability):
    """The masked summary from per-frame entries, by version 1's `measure` rules. Used to build and to validate."""
    valid = [f for f in frames if f['valid']]
    if any(f['differs_outside']['value'] for f in valid):
        any_outside = V.measured(True)
    elif availability == V.PARTIAL:
        any_outside = V.unavailable(f'no valid returned frame differs outside {OUTSIDE}, but some frames are invalid')
    else:
        any_outside = V.measured(False)
    final = frames[-1]
    final_equals = (V.measured(not final['differs_outside']['value']) if final['valid']
                    else V.unavailable('the final returned frame is invalid'))
    if final_equals['status'] != 'measured':
        visual = {'status': V.INDETERMINATE, 'reason': final_equals['reason']}
    elif not final_equals['value']:
        visual = {'status': V.FINAL_FRAME_DIFFERS, 'reason': f'the final returned frame differs outside {OUTSIDE}'}
    elif any_outside['status'] == 'measured' and any_outside['value']:
        visual = {'status': V.CHANGED_THEN_RETURNED,
                  'reason': f'an earlier frame differed outside {OUTSIDE}; the final frame equals the pre-action frame there'}
    elif any_outside['status'] == 'measured':
        visual = {'status': V.NO_OBSERVED_CHANGE,
                  'reason': f'no observed change outside {OUTSIDE}; changes inside it are set aside, not denied, and '
                            'this does not establish that the action had no effect'}
    else:
        visual = {'status': V.INDETERMINATE, 'reason': any_outside['reason']}
    inside = [f['changed_inside'] for f in valid]
    if any(c['status'] == 'measured' and c['value'] > 0 for c in inside):
        region_changed = V.measured(True)
    elif all(c['status'] == 'measured' for c in inside) and availability == V.COMPLETE:
        region_changed = V.measured(False)
    else:
        region_changed = V.unavailable('some returned frames are invalid or differ in shape')
    return {'any_returned_frame_differs_outside': any_outside, 'final_frame_equals_pre_outside': final_equals,
            'visual_effect_outside': visual, 'mask_region_changed': region_changed}


def _masked(raw, record, mask):
    """The masked view for one record."""
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
            why = 'the frame differs in shape; the mask does not apply'
            frames.append({'index': row['index'], 'valid': True, 'differs_outside': V.measured(True),
                           'changed_outside': V.unavailable(why), 'changed_inside': V.unavailable(why)})
        else:
            frames.append({'index': row['index'], 'valid': True, 'differs_outside': V.measured(split[0] > 0),
                           'changed_outside': V.measured(split[0]), 'changed_inside': V.measured(split[1])})
    return {'status': 'measured', **view, 'frames': frames, **_summary(frames, availability['status'])}


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
        reported = record['environment']['reported']
        reported['available_actions_after'] = after = _actions(raw['outcome']['after'])
        before_actions = record['context']['available_actions_before']
        reported['available_actions_changed'] = (
            V.measured(after['value'] != before_actions['value'])
            if after['status'] == before_actions['status'] == 'measured'
            else V.unavailable('available actions were not retained on both sides of the action'))
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
    record['identity'].pop('record_id', None)
    for key in ADDED:
        record.pop(key, None)
    for key in REPORTED_ADDED:
        (record['environment'].get('reported') or {}).pop(key, None)
    return record


def model_statement(transition_identity, kind, content, source):
    """A model's claim about a transition, kept apart from measurements, citing the transition by record_id."""
    statement = T1.model_statement(transition_identity, kind, content, source)
    statement['version'] = V.VERSION
    statement['about_record_id'] = record_id(transition_identity)
    return statement


def _typed(value, check, name):
    """Problems with one typed field: measured with a value passing `check`, or unavailable/absent with a reason."""
    if not isinstance(value, dict) or value.get('status') not in ('measured', 'unavailable', 'absent'):
        return [f'{name}: untyped']
    if value['status'] == 'measured':
        return [] if set(value) == {'status', 'value'} and check(value['value']) else [f'{name}: malformed value']
    return [] if set(value) == {'status', 'reason'} and isinstance(value['reason'], str) and value['reason'] else [
        f'{name}: {value["status"]} without a reason']


def _action_list(value):
    return (isinstance(value, list) and all(_int(a) and a >= 0 for a in value) and value == sorted(set(value)))


def _count(value):
    return _int(value) and value >= 0


def _context_problems(record):
    context = record.get('context')
    if not isinstance(context, dict) or set(context) != {'levels_completed_before', 'state_before',
                                                         'available_actions_before'}:
        return ['context: missing or malformed']
    problems = _typed(context['levels_completed_before'], _count, 'context.levels_completed_before')
    problems += _typed(context['state_before'], lambda v: v is None or isinstance(v, str), 'context.state_before')
    problems += _typed(context['available_actions_before'], _action_list, 'context.available_actions_before')
    if context['levels_completed_before']['status'] != 'measured':
        problems.append('context.levels_completed_before: the pre-action observation always reports a level')
    reported = record['environment'].get('reported')
    if record['dispatch']['status'] != V.ACKNOWLEDGED:
        if reported is not None:
            problems.append('environment.reported exists for an action whose result was not observed')
        return problems
    if not isinstance(reported, dict) or not set(REPORTED_ADDED) <= set(reported):
        return problems + ['environment.reported: available actions missing']
    after = reported['available_actions_after']
    problems += _typed(after, _action_list, 'available_actions_after')
    problems += _typed(reported['available_actions_changed'], lambda v: type(v) is bool, 'available_actions_changed')
    before = context['available_actions_before']
    if not problems and after['status'] == before['status'] == 'measured':
        if reported['available_actions_changed'] != V.measured(after['value'] != before['value']):
            problems.append('available_actions_changed contradicts the reported actions')
    elif not problems and reported['available_actions_changed']['status'] == 'measured':
        problems.append('available_actions_changed measured without actions on both sides')
    if not problems and reported.get('levels_completed_before') != context['levels_completed_before']['value']:
        problems.append('context level contradicts the reported level before the action')
    return problems


def _masked_problems(record):
    m = record.get('masked')
    if not isinstance(m, dict):
        return ['masked view: missing']
    if m.get('status') == 'unavailable':
        ok = isinstance(m.get('reason'), str) and m['reason'] and set(m) <= {'status', 'reason', 'mask'}
        return [] if ok else ['masked view: unavailable without a reason, or with measurements']
    if m.get('status') != 'measured':
        return ['masked view: untyped']
    expected = {'status', 'mask', 'frames', 'any_returned_frame_differs_outside', 'final_frame_equals_pre_outside',
                'visual_effect_outside', 'mask_region_changed'}
    if set(m) != expected:
        return ['masked view: fields differ from the schema']
    problems = ['mask: ' + p for p in mask_problems(m['mask'])]
    if problems:
        return problems
    if record['dispatch']['status'] != V.ACKNOWLEDGED or record['observations']['availability']['status'] in (
            V.MISSING, V.NOT_APPLICABLE):
        return ['a masked measurement exists for an action whose result was not observed']
    if m['mask']['frame_shape'] != record['observations']['pre_frame_shape']:
        problems.append('the mask is declared for another frame shape than the pre-action frame')
    v1_frames = record['measurements']['frames']
    if not isinstance(m['frames'], list) or len(m['frames']) != len(v1_frames):
        return problems + ['masked frames do not correspond one-to-one to the returned frames']
    for mine, full in zip(m['frames'], v1_frames):
        where = f'masked frame {full["index"]}'
        if not isinstance(mine, dict) or mine.get('index') != full['index'] or mine.get('valid') != full['valid']:
            problems.append(f'{where}: index or validity differs from the returned frame')
            continue
        if not full['valid']:
            if set(mine) != {'index', 'valid'}:
                problems.append(f'{where}: an invalid frame carries measurements')
            continue
        if set(mine) != {'index', 'valid', 'differs_outside', 'changed_outside', 'changed_inside'}:
            problems.append(f'{where}: fields differ from the schema')
            continue
        full_count = full['vs_pre']['changed_cells']
        out, ins = mine['changed_outside'], mine['changed_inside']
        if full['vs_pre']['comparability'] == V.COMPARABLE:
            if not (_typed(out, _count, where) == [] and _typed(ins, _count, where) == []
                    and out['status'] == ins['status'] == 'measured'):
                problems.append(f'{where}: counts must be measured non-negative integers')
                continue
            if out['value'] + ins['value'] != full_count['value']:
                problems.append(f'{where}: outside plus inside differs from the full-frame changed count')
            if mine['differs_outside'] != V.measured(out['value'] > 0):
                problems.append(f'{where}: differs_outside contradicts the outside count')
        else:
            if out['status'] != 'unavailable' or ins['status'] != 'unavailable' or mine['differs_outside'] != V.measured(True):
                problems.append(f'{where}: a frame of another shape differs, with undefined counts')
    if problems:
        return problems
    summary = _summary(m['frames'], record['observations']['availability']['status'])
    for key, value in summary.items():
        if m[key] != value:
            problems.append(f'{key} contradicts the masked frames')
    if (record['measurements']['visual_effect']['status'] == V.NO_OBSERVED_CHANGE
            and m['visual_effect_outside']['status'] != V.NO_OBSERVED_CHANGE):
        problems.append('a mask cannot create a change that the unmasked frames do not show')
    return problems


def validate(record):
    """Version 1's checks on the contained record, plus the version 2 structure and consistency rules."""
    if not isinstance(record, dict) or not all(k in record for k in ('identity', 'dispatch', 'environment', *ADDED)):
        return ['not a version 2 record: a block is missing']
    problems = T1.validate(to_v1(record))
    if record.get('version') != V.VERSION:
        problems.append('not a version 2 record')
    if record['identity'].get('record_id') != record_id(record['identity']):
        problems.append('record_id does not match episode_id and action_index')
    return problems + _context_problems(record) + _masked_problems(record)


def verify(record, raw, mask=None):
    """Problems unless a single `record` (built by `build`, without history fields) is exactly what `raw` builds."""
    return [] if build(raw, mask) == record else ['the record differs from what its raw evidence builds']


def verify_history(records, raws, masks=None):
    """Problems unless `records` are exactly what `history(raws, masks)` builds, segments and continuity included."""
    rebuilt = history(raws, masks)
    if len(rebuilt) != len(records):
        return ['the number of records differs from the raw transitions']
    return [f'record {r["identity"].get("record_id")}: differs from what its raw evidence builds'
            for r, expected in zip(records, rebuilt) if r != expected]
