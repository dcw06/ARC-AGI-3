"""Deterministic action-effect records built only from previously observed information.

A record is derived from exactly three inputs: the pre-action observation, the dispatched
action, and the dispatch outcome (what the engine returned, or how the dispatch failed). It
describes what happened. It never recommends an action, classifies objects by game rules, or
contains information from counterfactual or offline probes.
"""
import hashlib
import json

VERSION = 'action_effect_record_v1'
STATUSES = ('acknowledged', 'dispatch_failed', 'outcome_unknown')
EFFECT_FIELDS = ('returned_frame_count', 'returned_frames_sha256', 'changed_cells_by_frame',
                 'dimension_changed_by_frame', 'final_frame_changed', 'any_frame_changed',
                 'returned_to_pre_frame', 'level_delta', 'reset', 'state_after')


def check_grid(grid):
    if (type(grid) is not list or not grid or type(grid[0]) is not list or not grid[0]
            or any(type(row) is not list or len(row) != len(grid[0]) for row in grid)
            or any(type(v) is not int or not 0 <= v <= 15 for row in grid for v in row)):
        raise ValueError('grid must be a non-empty rectangular list of integers 0..15')
    return grid


def frames_sha256(frames):
    for frame in frames:
        check_grid(frame)
    return hashlib.sha256(json.dumps(frames, separators=(',', ':')).encode()).hexdigest()


def changed_cells(before, after):
    """Number of cells whose value differs; None when the dimensions differ (not comparable)."""
    if len(before) != len(after) or len(before[0]) != len(after[0]):
        return None
    return sum(a != b for row_a, row_b in zip(before, after) for a, b in zip(row_a, row_b))


def check_action(action):
    if type(action) is not dict or set(action) != {'action_id', 'action_data'}:
        raise ValueError('action must have exactly action_id and action_data')
    if type(action['action_id']) is not int or not 1 <= action['action_id'] <= 7 or type(action['action_data']) is not dict:
        raise ValueError('invalid action')
    return action


def check_observation(observation):
    if type(observation) is not dict or type(observation.get('frames')) is not list or not observation['frames']:
        raise ValueError('observation needs at least one frame')
    if type(observation.get('levels_completed')) is not int:
        raise ValueError('observation needs an integer levels_completed')
    frames_sha256(observation['frames'])
    return observation


def effect_record(pre, action, outcome):
    """Build one record. `outcome` is one of:
    {'status': 'acknowledged', 'post': <observation>}
    {'status': 'dispatch_failed', 'error': <str>}       request rejected or never delivered
    {'status': 'outcome_unknown', 'reason': <str>}      delivered, but the result was not observed
    """
    check_observation(pre)
    check_action(action)
    status = outcome.get('status') if type(outcome) is dict else None
    if status not in STATUSES:
        raise ValueError('unknown outcome status')
    record = {'version': VERSION, 'action_id': action['action_id'], 'action_data': dict(action['action_data']),
              'status': status, 'pre_frames_sha256': frames_sha256(pre['frames']),
              'pre_canonical_hash': pre.get('canonical_hash'), 'pre_levels_completed': pre['levels_completed'],
              'post_canonical_hash': None, 'detail': None, **{field: None for field in EFFECT_FIELDS}}
    if status != 'acknowledged':
        # A failed or unobserved dispatch is never a no-op observation: every effect field stays null.
        text = outcome.get('error' if status == 'dispatch_failed' else 'reason')
        if type(text) is not str or not text:
            raise ValueError('failed or unknown outcomes need a reason')
        record['detail'] = text[:256]
        return record
    post = check_observation(outcome.get('post'))
    reference = pre['frames'][-1]
    counts = [changed_cells(reference, frame) for frame in post['frames']]
    changed = [count is None or count > 0 for count in counts]
    record.update(returned_frame_count=len(post['frames']), returned_frames_sha256=frames_sha256(post['frames']),
                  changed_cells_by_frame=counts, dimension_changed_by_frame=[count is None for count in counts],
                  final_frame_changed=changed[-1], any_frame_changed=any(changed),
                  returned_to_pre_frame=any(changed) and not changed[-1],
                  level_delta=post['levels_completed'] - pre['levels_completed'],
                  reset=post.get('full_reset') is True, state_after=post.get('state'),
                  post_canonical_hash=post.get('canonical_hash'))
    return record


def policy_view(record):
    """The fields a policy may see: what was done and what was measured. No hashes or diagnostics."""
    return {key: record[key] for key in ('action_id', 'action_data', 'status', 'returned_frame_count',
                                         'changed_cells_by_frame', 'final_frame_changed', 'level_delta', 'reset')}


class EffectHistory:
    """Ordered records with segment numbers; a new segment starts after a reset or level change."""

    def __init__(self, limit=8):
        if type(limit) is not int or limit < 1:
            raise ValueError('history limit')
        self.limit = limit
        self.records = []
        self.segment = 0

    def append(self, record):
        if record.get('version') != VERSION or record.get('status') not in STATUSES:
            raise ValueError('not an action-effect record')
        if self.records:
            last = self.records[-1]
            if last['status'] == 'acknowledged' and (last['reset'] or last['level_delta']):
                self.segment += 1
        entry = {'step': len(self.records), 'segment': self.segment, **policy_view(record)}
        self.records.append({**record, 'step': entry['step'], 'segment': entry['segment']})
        return entry

    def view(self):
        """The most recent entries, oldest first, with the count of omitted earlier entries."""
        shown = self.records[-self.limit:]
        return {'omitted_entries': len(self.records) - len(shown),
                'entries': [{'step': r['step'], 'segment': r['segment'], **policy_view(r)} for r in shown]}
