"""The action-effect evidence both arms see (identical in baseline and candidate).

Built only from `research.transition_evidence_v2` records (frozen format, consumed read-only, built with default
arguments only; version 2's optional region-restricted view is never supplied or read anywhere in this track, which
a migration test enforces). Nothing here interprets an effect, assigns a cause or judges an action: every
field is copied or mechanically derived from a transition record. Every field read is one version 2 carries
unchanged from version 1, so the view is byte-identical to the version 1 view (tested).

Window rule (the evaluator re-derives it independently): the transitions of the current segment only, at most
WINDOW of them, oldest first. A segment ends after a reported reset, level-count change or terminal state, so the
first decision after such a boundary sees an empty window. References are `T<action_index>`, the episode-wide
index the transition record carries; they are stable across decisions.

States are observed states only: `S-` plus the first 12 hex digits of the frame's SHA-256. Two transitions "start
in the same state" when their pre-action frames are identical; hidden game state may still differ.
"""
from research.transition_evidence_v2 import transition as T, vocabulary as V

VERSION = 'feedback_action_v1_evidence'
FORMAT = V.VERSION  # transition_evidence_v2
FIELD = 'action_effect_history'
WINDOW = 8
BOUNDARY_EVENTS = {V.RESET_ACKNOWLEDGED, V.LEVEL_COMPLETED, V.LEVEL_COUNT_DECREASED, V.TERMINAL_STATE}
DESCRIPTION = {
    'computed_by': 'deterministic frame-comparison tool, not the model',
    'scope': f'up to {WINDOW} most recent transitions since the last reset, level change or terminal state, oldest first',
    'ref': 'T<n> identifies one earlier transition; only refs listed in entries exist for you',
    'states': 'from_state, to_state and current_state identify observed frames by hash; equal ids mean identical '
              'frames, not identical hidden state',
    'visual_effect': 'no_observed_change: no returned frame differed from the frame before the action. '
                     'changed_then_returned: a returned frame differed, the last one equals the frame before. '
                     'final_frame_differs: the last returned frame differs. indeterminate: the evidence cannot decide '
                     '(for example the dispatch failed or its outcome is unknown); it never means no change',
    'unavailable': 'a value that could not be measured; it is never zero',
}


def state_id_from_sha(sha):
    return 'S-' + sha[:12]


def state_id(grid):
    return state_id_from_sha(T.T1.frame_sha256(grid))  # version 2 reuses version 1's frame hash


def entry(record):
    m = record['measurements']
    final_valid = [f for f in m['frames'] if f['valid']]
    final = m['frames'][-1] if m['frames'] else None
    status = record['dispatch']['status']
    if status != V.ACKNOWLEDGED:
        to_state = 'not_observed'
    elif final is not None and final['valid']:
        to_state = state_id_from_sha(final['sha256'])
    else:
        to_state = 'unavailable'
    changed = (final['vs_pre']['changed_cells'] if final is not None and final['valid'] else
               V.unavailable('no valid final frame'))
    dispatched = record['action']['dispatched']
    return {'ref': f"T{record['identity']['action_index']}",
            'action_id': dispatched['action_id'], 'action_data': dispatched['action_data'],
            'dispatch': status, 'from_state': state_id_from_sha(record['observations']['before_frames_sha256'][-1]),
            'returned_frames': (m['returned_frame_count']['value'] if m['returned_frame_count']['status'] == 'measured'
                                else 'unavailable'),
            'valid_returned_frames': len(final_valid) if status == V.ACKNOWLEDGED else 'unavailable',
            'visual_effect': m['visual_effect']['status'],
            'final_frame_changed_cells': changed['value'] if changed['status'] == 'measured' else 'unavailable',
            'to_state': to_state, 'events': list(record['environment']['events']),
            'progress': record['progress']['status'], 'continuity': record['continuity']['status']}


def current_records(records):
    """The records of the segment the next decision belongs to."""
    if not records:
        return []
    segment = records[-1]['segment']
    if set(records[-1]['environment']['events']) & BOUNDARY_EVENTS:
        return []  # the next decision starts a new segment
    return [r for r in records if r['segment'] == segment]


def view(raws, current_frame):
    """The evidence field for the next decision, from the raw transitions dispatched so far in this episode."""
    records = T.history(raws)  # default arguments only
    current = current_records(records)
    shown = current[-WINDOW:]
    return {**DESCRIPTION, 'current_state': state_id(current_frame), 'omitted_entries': len(current) - len(shown),
            'entries': [entry(r) for r in shown]}
