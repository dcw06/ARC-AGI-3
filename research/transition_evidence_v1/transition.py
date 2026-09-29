"""Transition records and exact frame measurements (Workstream 3, transition_evidence_v1).

Input is raw evidence as a producer retains it:
  {'identity': {'episode_id': str, 'action_index': int},
   'before': {'frames': [grid, ...], 'levels_completed': int, 'state': str, 'full_reset': bool},
   'proposal': {'action_id', 'action_data'} | {'unparsed': str} | None (not retained),
   'dispatched': {'action_id', 'action_data'},
   'outcome': {'status': 'acknowledged', 'after': <observation like 'before'>}
            | {'status': 'failed', 'reason': str} | {'status': 'outcome_unknown', 'reason': str},
   'environment_source': str}

Output is a record with separate dimensions (vocabulary.py). Measurements are exact and use two stated references:
- `vs_pre`: each returned frame against the pre-action frame (the last frame of `before`);
- `vs_previous`: each returned frame against the one before it (frame 0 against the pre-action frame).
Missing frames are never synthesized. An invalid returned frame is kept as invalid with its reason; it never
becomes a zero-change measurement. The record describes observations only; it contains no cause, reward or
judgement. Model statements belong in a separate record (see `model_statement`).
"""
import copy
import hashlib
import json

from research.transition_evidence_v1 import vocabulary as V

CONTRACT = 'an acknowledged action returns at least one valid frame'


def grid_problem(grid):
    """None for a valid frame (non-empty rectangular grid of integers 0..15), else the reason it is invalid."""
    if type(grid) is not list or not grid:
        return 'not a non-empty list of rows'
    if any(type(row) is not list or not row for row in grid):
        return 'a row is not a non-empty list'
    if any(len(row) != len(grid[0]) for row in grid):
        return 'rows have different lengths'
    if any(type(v) is not int or not 0 <= v <= 15 for row in grid for v in row):
        return 'a cell is not an integer 0..15'
    return None


def frame_sha256(grid):
    return hashlib.sha256(json.dumps(grid, separators=(',', ':')).encode()).hexdigest()


def shape(grid):
    return [len(grid), len(grid[0])]


def compare(reference, frame):
    """(comparability, changed cell list or None). Cells are [x, y] with the frame read as grid[y][x]."""
    if shape(reference) != shape(frame):
        return V.DIMENSIONS_DIFFER, None
    cells = [[x, y] for y, row in enumerate(frame) for x, value in enumerate(row) if value != reference[y][x]]
    return V.COMPARABLE, cells


def _comparison(reference, frame, label):
    comparability, cells = compare(reference, frame)
    if cells is None:
        return {'comparability': comparability,
                'changed_cells': V.unavailable(f'dimensions differ from {label}; a cell-by-cell count is undefined'),
                'differs': V.measured(True)}
    box = ([min(c[0] for c in cells), min(c[1] for c in cells), max(c[0] for c in cells), max(c[1] for c in cells)]
           if cells else None)
    return {'comparability': comparability, 'changed_cells': V.measured(len(cells)),
            'changed_bbox_xyxy': V.measured(box),
            'changed_mask_sha256': V.measured(hashlib.sha256(json.dumps(cells).encode()).hexdigest()),
            'differs': V.measured(bool(cells))}


def measure(pre, returned):
    """Measurements for an acknowledged action. `returned` is the raw list of returned frames."""
    frames = []
    previous = pre
    for index, grid in enumerate(returned):
        problem = grid_problem(grid)
        if problem:
            frames.append({'index': index, 'valid': False, 'reason': problem})
            previous = None  # chronology is broken: the next frame has no valid predecessor
            continue
        row = {'index': index, 'valid': True, 'shape': shape(grid), 'sha256': frame_sha256(grid),
               'vs_pre': _comparison(pre, grid, 'the pre-action frame')}
        row['vs_previous'] = (_comparison(previous, grid, 'the previous frame') if previous is not None else
                              {'comparability': V.UNAVAILABLE,
                               'changed_cells': V.unavailable('the previous returned frame is invalid'),
                               'differs': V.unavailable('the previous returned frame is invalid')})
        frames.append(row)
        previous = grid
    valid = [f for f in frames if f['valid']]
    if not frames:
        availability = {'status': V.MISSING, 'reason': 'acknowledged, but no frame was returned; ' + CONTRACT}
    elif not valid:
        availability = {'status': V.MISSING, 'reason': 'acknowledged, but every returned frame is invalid'}
    elif len(valid) < len(frames):
        availability = {'status': V.PARTIAL, 'reason': f'{len(frames) - len(valid)} of {len(frames)} returned frames invalid'}
    else:
        availability = {'status': V.COMPLETE, 'reason': CONTRACT}
    final = frames[-1] if frames else None
    if availability['status'] == V.MISSING:
        why = availability['reason']
        any_differs = final_equals = V.unavailable(why)
        visual = {'status': V.INDETERMINATE, 'reason': why}
    else:
        differs = [f['vs_pre']['differs']['value'] for f in valid]
        if any(differs):
            any_differs = V.measured(True)
        elif availability['status'] == V.PARTIAL:
            any_differs = V.unavailable('no valid returned frame differs, but some returned frames are invalid')
        else:
            any_differs = V.measured(False)
        if final['valid']:
            final_equals = V.measured(not final['vs_pre']['differs']['value'])
        else:
            final_equals = V.unavailable('the final returned frame is invalid')
        if final_equals['status'] != 'measured':
            visual = {'status': V.INDETERMINATE, 'reason': final_equals['reason']}
        elif not final_equals['value']:
            visual = {'status': V.FINAL_FRAME_DIFFERS, 'reason': 'the final returned frame differs from the pre-action frame'}
        elif any_differs['status'] == 'measured' and any_differs['value']:
            visual = {'status': V.CHANGED_THEN_RETURNED,
                      'reason': 'an earlier returned frame differed; the final returned frame equals the pre-action frame'}
        elif any_differs['status'] == 'measured':
            visual = {'status': V.NO_OBSERVED_CHANGE,
                      'reason': 'no returned frame differs from the pre-action frame; this describes the observations only'}
        else:
            visual = {'status': V.INDETERMINATE, 'reason': any_differs['reason']}
    return {'returned_frame_count': V.measured(len(frames)), 'frames': frames, 'availability': availability,
            'any_returned_frame_differs': any_differs, 'final_frame_equals_pre': final_equals, 'visual_effect': visual}


def environment(before, after, source):
    events, signals = [], []
    delta = after['levels_completed'] - before['levels_completed']
    if delta > 0:
        events.append(V.LEVEL_COMPLETED)
        signals.append('levels_completed_increased')
    elif delta < 0:
        events.append(V.LEVEL_COUNT_DECREASED)
    if after.get('state') not in (None, 'NOT_FINISHED'):
        events.append(V.TERMINAL_STATE)
        if after.get('state') == 'WIN':
            signals.append('state_WIN')
    if after.get('full_reset') is True:
        events.append(V.RESET_ACKNOWLEDGED)
    reported = {'levels_completed_before': before['levels_completed'], 'levels_completed_after': after['levels_completed'],
                'state_before': before.get('state'), 'state_after': after.get('state'),
                'full_reset_after': after.get('full_reset')}
    progress = ({'status': V.CONFIRMED, 'signals': signals, 'source': source} if signals else
                {'status': V.UNKNOWN, 'reason': 'no allowed progress signal was reported; this does not establish '
                                                'that no progress occurred', 'source': source})
    return {'events': events or [V.NONE_REPORTED], 'reported': reported, 'source': source}, progress


def build(raw):
    """One transition record from raw evidence. Raises ValueError on malformed input (not on missing evidence)."""
    before, outcome = raw['before'], raw['outcome']
    pre_problem = grid_problem(before['frames'][-1]) if before.get('frames') else 'no pre-action frame'
    if pre_problem:
        raise ValueError('the pre-action frame is required and must be valid: ' + pre_problem)
    status = outcome.get('status')
    if status not in (V.ACKNOWLEDGED, V.FAILED, V.OUTCOME_UNKNOWN):
        raise ValueError('unknown dispatch status')
    proposal = raw.get('proposal')
    record = {
        'version': V.VERSION,
        'identity': copy.deepcopy(raw['identity']),
        'action': {'proposal': (V.absent('the producer did not retain the model proposal') if proposal is None
                                else V.measured(copy.deepcopy(proposal))),
                   'dispatched': copy.deepcopy(raw['dispatched']),
                   'proposal_equals_dispatched': (V.unavailable('the proposal was not retained') if proposal is None
                                                  else V.unavailable('the proposal could not be parsed')
                                                  if 'unparsed' in proposal else V.measured(proposal == raw['dispatched']))},
        'dispatch': {'status': status, 'reason': outcome.get('reason')},
        'observations': {'before_frames_sha256': [frame_sha256(f) for f in before['frames']],
                         'pre_frame_shape': shape(before['frames'][-1])},
    }
    pre = before['frames'][-1]
    if status == V.ACKNOWLEDGED:
        after = outcome['after']
        m = measure(pre, after.get('frames') or [])
        record['observations']['availability'] = m.pop('availability')
        record['measurements'] = m
        record['environment'], record['progress'] = environment(before, after, raw.get('environment_source', 'unspecified'))
    else:
        if not isinstance(outcome.get('reason'), str) or not outcome['reason']:
            raise ValueError('a failed or unknown dispatch needs a reason')
        if status == V.FAILED:
            availability = {'status': V.NOT_APPLICABLE, 'reason': 'the dispatch failed: nothing was delivered'}
            why = 'the dispatch failed; this is not a no-op observation'
        else:
            availability = {'status': V.MISSING, 'reason': 'the action may have executed; its result was not observed'}
            why = 'the outcome is unknown; the action may have executed'
        record['observations']['availability'] = availability
        record['measurements'] = {'returned_frame_count': V.unavailable(why), 'frames': [],
                                  'any_returned_frame_differs': V.unavailable(why),
                                  'final_frame_equals_pre': V.unavailable(why),
                                  'visual_effect': {'status': V.INDETERMINATE, 'reason': why}}
        record['environment'] = {'events': [V.NOT_OBSERVED], 'reported': None, 'source': raw.get('environment_source')}
        record['progress'] = {'status': V.UNKNOWN, 'reason': why, 'source': raw.get('environment_source')}
    return record


def last_observed_frame(raw):
    """The last valid frame this transition leaves observed, or None when its result was not observed."""
    status = raw['outcome']['status']
    if status == V.FAILED:
        return raw['before']['frames'][-1]
    if status == V.OUTCOME_UNKNOWN:
        return None
    frames = raw['outcome']['after'].get('frames') or []
    return frames[-1] if frames and grid_problem(frames[-1]) is None else None


def history(raws):
    """Records with segment numbers and continuity. A segment ends after a reported reset, level-count change or
    terminal state. Continuity compares each before-frame with the last frame the previous transition left
    observed; after an unknown outcome or missing observation it is a declared gap, never assumed."""
    records, segment, previous = [], 0, None
    for raw in raws:
        record = build(raw)
        before = raw['before']['frames'][-1]
        if previous is not None and set(previous['record']['environment']['events']) & {
                V.RESET_ACKNOWLEDGED, V.LEVEL_COMPLETED, V.LEVEL_COUNT_DECREASED, V.TERMINAL_STATE}:
            segment += 1
            previous = None
        if previous is None:
            continuity = {'status': V.FIRST_IN_SEGMENT}
        elif previous['raw']['outcome']['status'] == V.OUTCOME_UNKNOWN:
            continuity = {'status': V.GAP_UNKNOWN_OUTCOME,
                          'reason': 'the previous action may have executed; its result was never observed'}
        else:
            last = last_observed_frame(previous['raw'])
            if last is None:
                continuity = {'status': V.GAP_MISSING_OBSERVATION,
                              'reason': 'the previous transition left no valid final frame'}
            else:
                same = shape(last) == shape(before) and compare(last, before)[1] == []
                continuity = {'status': V.MATCHES_PREVIOUS if same else V.DIFFERS_FROM_PREVIOUS}
        record['segment'] = segment
        record['continuity'] = continuity
        records.append(record)
        previous = {'raw': raw, 'record': record}
    return records


def model_statement(transition_identity, kind, content, source):
    """A model's claim about a transition, kept apart from measurements. It never overwrites a measured fact."""
    return {'version': V.VERSION, 'record': 'model_statement', 'about': copy.deepcopy(transition_identity),
            'kind': kind, 'content': copy.deepcopy(content), 'source': source, 'status': 'hypothesis'}


def validate(record):
    """Internal consistency of one record against the vocabulary rules. Returns a list of problems."""
    problems = []
    status = record['dispatch']['status']
    availability = record['observations']['availability']['status']
    m = record['measurements']
    visual = m['visual_effect']['status']
    if status not in V.DISPATCH or availability not in V.AVAILABILITY or visual not in V.VISUAL:
        problems.append('value outside the vocabulary')
    for name in ('any_returned_frame_differs', 'final_frame_equals_pre', 'returned_frame_count'):
        value = m[name]
        if value.get('status') not in ('measured', 'unavailable', 'absent') or (
                value['status'] != 'measured' and not value.get('reason')):
            problems.append(f'{name}: untyped or unexplained')
    if status == V.FAILED and (availability != V.NOT_APPLICABLE or visual != V.INDETERMINATE):
        problems.append('a failed dispatch was given an observation or a visual effect')
    if status == V.OUTCOME_UNKNOWN and (availability != V.MISSING or visual != V.INDETERMINATE):
        problems.append('an unknown outcome was given an observation or a visual effect')
    if availability == V.MISSING and any(v['status'] == 'measured' for v in
                                         (m['any_returned_frame_differs'], m['final_frame_equals_pre'])):
        problems.append('a missing observation produced a measured change value')
    if visual == V.NO_OBSERVED_CHANGE and (m['any_returned_frame_differs'] != V.measured(False)):
        problems.append('no_observed_change without a measured absence of change')
    if record['progress']['status'] == V.CONFIRMED and not set(record['progress'].get('signals', ())) <= set(
            V.ALLOWED_PROGRESS_SIGNALS):
        problems.append('progress confirmed by a signal that is not allowed')
    if record['progress']['status'] not in V.PROGRESS:
        problems.append('progress status outside the deterministic vocabulary')
    return problems
