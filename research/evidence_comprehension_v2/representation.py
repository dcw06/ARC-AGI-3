"""History-reading track: the baseline history field and the normalized candidate.

The candidate presents exactly the same evidence and uncertainty as the baseline field, entry by entry:
`normalize_entry` and `denormalize_entry` are exact inverses (tested on every shown entry). Each
candidate field is derived from its own entry only; no field aggregates across entries, so nothing like
"tried here without change" is computed for the model. Differences from the baseline:
- the action is one object, `action`, instead of two top-level fields;
- `dispatch` names the dispatch status in words;
- every returned frame's comparison is a phrase ("same as the frame before the action", "differs from
  the frame before the action (12 cells)") instead of a bare count;
- a failed or unknown dispatch says "none observed" / "not observed" instead of null, so an absent
  observation cannot be read as "no change";
- the field description is rewritten to match (and no longer calls every null a failed dispatch).
"""
import copy

from research.action_effect_history_v1.contract import HISTORY_DESCRIPTION, HISTORY_FIELD

SAME = 'same as the frame before the action'
DIFFERS = 'differs from the frame before the action'
DIMENSIONS = 'differs from the frame before the action (dimensions changed)'
NOT_OBSERVED = 'not observed'
NONE_OBSERVED = 'none observed'
DISPATCH = {'acknowledged': 'acknowledged by the game',
            'dispatch_failed': 'failed: not delivered to the game',
            'outcome_unknown': 'unknown: may have been delivered, but its result was not observed'}
CANDIDATE_DESCRIPTION = {
    'computed_by': HISTORY_DESCRIPTION['computed_by'],
    'scope': HISTORY_DESCRIPTION['scope'],
    'fields': ('Each entry is one dispatched action. dispatch says whether the game acknowledged it. '
               'returned_frames compares each frame the game returned for that action, in order, with the frame '
               'before the action; final_frame compares the last returned frame with the frame before the action. '
               'When the dispatch failed or its outcome is unknown, no frame was observed: that is not evidence '
               'that nothing changed.'),
}
BASELINE_ENTRY_KEYS = ('step', 'action_id', 'action_data', 'status', 'returned_frame_count',
                       'changed_cells_by_frame', 'final_frame_changed', 'level_delta', 'reset')


def _frame_phrase(count):
    if count is None:
        return DIMENSIONS
    return SAME if count == 0 else f'{DIFFERS} ({count} cells)'


def _frame_count(phrase):
    if phrase == DIMENSIONS:
        return None
    if phrase == SAME:
        return 0
    prefix = DIFFERS + ' ('
    if not (phrase.startswith(prefix) and phrase.endswith(' cells)')):
        raise ValueError('frame phrase')
    count = int(phrase[len(prefix):-len(' cells)')])
    if count <= 0:
        raise ValueError('frame count')
    return count


def normalize_entry(entry):
    if tuple(sorted(entry)) != tuple(sorted(BASELINE_ENTRY_KEYS)):
        raise ValueError('not a baseline history entry')
    out = {'step': entry['step'], 'action': {'action_id': entry['action_id'],
                                              'action_data': copy.deepcopy(entry['action_data'])},
           'dispatch': DISPATCH[entry['status']]}
    if entry['status'] != 'acknowledged':
        if any(entry[k] is not None for k in BASELINE_ENTRY_KEYS[4:]):
            raise ValueError('a failed or unknown dispatch has no observed effect')
        return {**out, 'returned_frames': NONE_OBSERVED, 'final_frame': NOT_OBSERVED,
                'level_delta': NOT_OBSERVED, 'reset': NOT_OBSERVED}
    counts = entry['changed_cells_by_frame']
    if len(counts) != entry['returned_frame_count'] or entry['final_frame_changed'] != (counts[-1] is None or counts[-1] > 0):
        raise ValueError('inconsistent entry')
    return {**out, 'returned_frames': [_frame_phrase(c) for c in counts],
            'final_frame': SAME if not entry['final_frame_changed'] else DIFFERS,
            'level_delta': entry['level_delta'], 'reset': entry['reset']}


def denormalize_entry(entry):
    status = {v: k for k, v in DISPATCH.items()}[entry['dispatch']]
    out = {'step': entry['step'], 'action_id': entry['action']['action_id'],
           'action_data': copy.deepcopy(entry['action']['action_data']), 'status': status}
    if status != 'acknowledged':
        if (entry['returned_frames'], entry['final_frame'], entry['level_delta'], entry['reset']) != (
                NONE_OBSERVED, NOT_OBSERVED, NOT_OBSERVED, NOT_OBSERVED):
            raise ValueError('a failed or unknown dispatch has no observed effect')
        return {**out, **{k: None for k in BASELINE_ENTRY_KEYS[4:]}}
    counts = [_frame_count(p) for p in entry['returned_frames']]
    return {**out, 'returned_frame_count': len(counts), 'changed_cells_by_frame': counts,
            'final_frame_changed': {SAME: False, DIFFERS: True}[entry['final_frame']],
            'level_delta': entry['level_delta'], 'reset': entry['reset']}


def normalize_field(field):
    """The candidate history field: same scope, same omitted count, same entries in the same order."""
    extra = set(field) - {'computed_by', 'scope', 'fields', 'omitted_entries', 'entries'}
    if extra:
        raise ValueError(f'unexpected history keys {sorted(extra)}')
    return {**CANDIDATE_DESCRIPTION, 'omitted_entries': field['omitted_entries'],
            'entries': [normalize_entry(e) for e in field['entries']]}


def candidate_observation(observation):
    """The observation with only the history field replaced."""
    return {**copy.deepcopy(observation), HISTORY_FIELD: normalize_field(observation[HISTORY_FIELD])}
