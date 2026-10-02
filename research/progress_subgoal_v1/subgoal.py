"""Subgoal verification records and contract-derived sequence facts (progress_subgoal_v1, DRAFT).

Three levels are kept apart and never collapsed:
- observed change: frame comparison only (transition_evidence_v1 measurements, plus the rectangle rule below);
- confirmed progress: only an allowed environment signal (levels_completed increased, or state WIN), read from the
  transition record's `progress` block;
- hypothesized usefulness: the subgoal record's `reason_it_might_help`. It is always a hypothesis. Nothing here can
  confirm it: achieving a subgoal is not progress, and does not show that the subgoal helps solve the level.

Everything is computed from transition records built by research/transition_evidence_v1/transition.py (read-only
use of the transition contract) and from the raw frames those records describe. An independent, import-free
re-derivation is in reference.py.

Rectangle rule (one transition, one rectangle given as [x, y, w, h], cells [x, y] read as grid[y][x]):
- `yes`: some valid returned frame of the pre-action frame's dimensions differs from it inside the rectangle;
- `no`: frames were returned, every one is valid and of the same dimensions, and none differs inside it;
- `cannot_tell`: otherwise (failed or unknown dispatch, no frame, invalid frames, dimension change).

Gap rule (between two consecutive transitions): the earlier transition's last observed frame
(transition.last_observed_frame: the valid final returned frame, or the frame before for a failed dispatch) is
compared with the next frame before, inside the rectangle. After an unknown outcome or a missing final frame there is
no last observed frame and the gap is `cannot_tell`.
"""
import copy

from research.transition_evidence_v1 import transition as T, vocabulary as V

VERSION = 'progress_subgoal_v1'
YES, NO, CANNOT_TELL = 'yes', 'no', 'cannot_tell'

# ------------------------------------------------------------------ rectangle and gap facts


def inside(cell, xywh):
    x, y, w, h = xywh
    return x <= cell[0] < x + w and y <= cell[1] < y + h


def region_status(raw, record, xywh):
    """The rectangle rule for one transition (see module docstring)."""
    if record['dispatch']['status'] != V.ACKNOWLEDGED or record['observations']['availability']['status'] == V.MISSING:
        return CANNOT_TELL
    pre = raw['before']['frames'][-1]
    frames = raw['outcome']['after'].get('frames') or []
    undecided = False
    for grid, row in zip(frames, record['measurements']['frames']):
        if not row['valid']:
            undecided = True
            continue
        comparability, cells = T.compare(pre, grid)
        if comparability != V.COMPARABLE:
            undecided = True
            continue
        if any(inside(c, xywh) for c in cells):
            return YES
    return CANNOT_TELL if undecided else NO


def gap_status(previous_raw, raw, xywh):
    """Did the rectangle change between the previous transition's last observed frame and this frame before?"""
    if previous_raw['outcome']['status'] == V.OUTCOME_UNKNOWN:
        return CANNOT_TELL
    last = T.last_observed_frame(previous_raw)
    if last is None:
        return CANNOT_TELL
    comparability, cells = T.compare(last, raw['before']['frames'][-1])
    if comparability != V.COMPARABLE:
        return CANNOT_TELL
    return YES if any(inside(c, xywh) for c in cells) else NO


# ------------------------------------------------------------------ effect hypothesis (causal restraint)

STRENGTHENED, WEAKENED, INSUFFICIENT = 'strengthened', 'weakened', 'insufficient_evidence'
HYPOTHESIS_RULE = (
    'trials: transitions that dispatched exactly the named action whose rectangle result is yes or no; controls: '
    'transitions that dispatched any other action whose rectangle result is yes or no. A gap between consecutive '
    'transitions that changed the rectangle (gap result yes) also counts as a control that changed it; an unchanged '
    'gap never counts as a control (consecutive observations are normally identical, so it would make the control '
    'requirement vacuous). weakened: a trial left the rectangle unchanged, or a control changed it. strengthened: '
    'otherwise, at least two trials changed it and at least one control transition left it unchanged. '
    'insufficient_evidence: otherwise. strengthened supports a hypothesis; it never identifies a cause or a mechanism.')


def effect_hypothesis(raws, records, action, xywh):
    """Status of the hypothesis 'action is followed by a change inside xywh' over a sequence, with its tallies."""
    tally = {'trials_changed': 0, 'trials_unchanged': 0, 'controls_changed': 0, 'controls_unchanged': 0,
             'gaps_changed': 0, 'undecided': 0}
    for n, (raw, record) in enumerate(zip(raws, records)):
        if n and gap_status(raws[n - 1], raw, xywh) == YES:
            tally['gaps_changed'] += 1
            tally['controls_changed'] += 1
        status = region_status(raw, record, xywh)
        if status == CANNOT_TELL:
            tally['undecided'] += 1
            continue
        kind = 'trials' if raw['dispatched'] == action else 'controls'
        tally[f"{kind}_{'changed' if status == YES else 'unchanged'}"] += 1
    if tally['trials_unchanged'] or tally['controls_changed']:
        status = WEAKENED
    elif tally['trials_changed'] >= 2 and tally['controls_unchanged'] >= 1:
        status = STRENGTHENED
    else:
        status = INSUFFICIENT
    return {'status': status, 'tally': tally, 'mechanism': 'not_identified', 'cause': 'not_established'}


# ------------------------------------------------------------------ subgoal verification record

SUCCESS_KINDS = ('region_all_colour',)
INVALIDATION_KINDS = ('no_region_change_after_attempts', 'state_reported')
FIELDS = ('record', 'version', 'observable_target', 'reason_it_might_help', 'success_test', 'invalidation_evidence',
          'action_budget')
ACHIEVED, NOT_ACHIEVED = 'achieved', 'not_achieved'
STOP_ACHIEVED, ABANDON_INVALIDATED, ABANDON_BUDGET, CONTINUE = (
    'stop_achieved', 'abandon_invalidated', 'abandon_budget_exhausted', 'continue')
EVALUATED_ON = 'every frame before and every final returned frame that is valid; intermediate returned frames do not count'
NEVER_ASSERTED = ('that the subgoal helps solve the level', 'that the subgoal was the best choice', 'confirmed progress')


def subgoal_record(target_xywh, colour, budget, invalidation, reason):
    """A subgoal verification record. Usefulness is stored only as a hypothesis."""
    return {'record': 'subgoal_verification', 'version': VERSION,
            'observable_target': {'region_xywh': list(target_xywh), 'colour': colour,
                                  'text': f'every cell inside the rectangle {list(target_xywh)} has colour {colour}'},
            'reason_it_might_help': {'status': 'hypothesis', 'text': reason},
            'success_test': {'kind': 'region_all_colour', 'region_xywh': list(target_xywh), 'colour': colour,
                             'evaluated_on': EVALUATED_ON},
            'invalidation_evidence': copy.deepcopy(invalidation),
            'action_budget': budget}


def validate_subgoal(sg):
    """Problems with a subgoal record (an empty list is valid). A record claiming usefulness or optimality is invalid."""
    problems = []
    if not isinstance(sg, dict):
        return ['not an object']
    missing = [f for f in FIELDS if f not in sg]
    extra = sorted(set(sg) - set(FIELDS))
    if missing:
        problems.append(f'missing fields: {missing}')
    if extra:
        problems.append(f'unexpected fields (usefulness or optimality may not be asserted): {extra}')
    if missing:
        return problems
    if sg['record'] != 'subgoal_verification' or sg['version'] != VERSION:
        problems.append('wrong record type or version')
    reason = sg['reason_it_might_help']
    if not isinstance(reason, dict) or reason.get('status') != 'hypothesis' or not reason.get('text'):
        problems.append('reason_it_might_help must be a hypothesis with text')
    test = sg['success_test']
    if not isinstance(test, dict) or test.get('kind') not in SUCCESS_KINDS or not _rect(test.get('region_xywh')) or \
            type(test.get('colour')) is not int or not 0 <= test['colour'] <= 15:
        problems.append('success_test must be region_all_colour with a rectangle and a colour 0..15')
    budget = sg['action_budget']
    if type(budget) is not int or budget < 1:
        problems.append('action_budget must be a positive integer')
    inv = sg['invalidation_evidence']
    if not isinstance(inv, list) or not inv:
        problems.append('invalidation_evidence must be a non-empty list')
    else:
        for item in inv:
            kind = item.get('kind') if isinstance(item, dict) else None
            if kind not in INVALIDATION_KINDS:
                problems.append(f'unknown invalidation kind: {kind}')
            elif kind == 'no_region_change_after_attempts' and (
                    not _rect(item.get('region_xywh')) or type(item.get('attempts')) is not int or item['attempts'] < 1
                    or not isinstance(item.get('action'), dict)):
                problems.append('no_region_change_after_attempts needs an action, a rectangle and attempts >= 1')
            elif kind == 'state_reported' and item.get('state') not in ('GAME_OVER',):
                problems.append('state_reported supports GAME_OVER only')
    return problems


def _rect(value):
    return isinstance(value, list) and len(value) == 4 and all(type(v) is int for v in value) and \
        value[2] >= 1 and value[3] >= 1 and value[0] >= 0 and value[1] >= 0


def meets_test(grid, test):
    x, y, w, h = test['region_xywh']
    if T.grid_problem(grid) or y + h > len(grid) or x + w > len(grid[0]):
        return False
    return all(grid[j][i] == test['colour'] for j in range(y, y + h) for i in range(x, x + w))


def check(sg, raws):
    """Mechanical verification of a subgoal over the transitions since it was adopted.

    Returns achievement status, the first achieving observation, the invalidation conditions met, actions used, and
    the decision by the record's own rules. It never asserts that the subgoal helped, was optimal, or produced progress:
    progress is reported separately and only from the transition records' allowed environment signals.
    """
    problems = validate_subgoal(sg)
    if problems:
        raise ValueError(f'invalid subgoal record: {problems}')
    records = T.history(raws)
    test = sg['success_test']
    if meets_test(raws[0]['before']['frames'][-1], test):
        raise ValueError('the success test is already met when the subgoal is adopted')
    achieved_at, unobserved = None, False
    for n, (raw, record) in enumerate(zip(raws, records)):
        if achieved_at is None and meets_test(raw['before']['frames'][-1], test):
            achieved_at = {'transition': n, 'frame': 'before'}
        if record['dispatch']['status'] == V.FAILED:
            continue
        frames = record['measurements']['frames']
        if record['dispatch']['status'] == V.OUTCOME_UNKNOWN or not frames or not frames[-1]['valid']:
            unobserved = True
            continue
        if achieved_at is None and meets_test(raw['outcome']['after']['frames'][-1], test):
            achieved_at = {'transition': n, 'frame': 'final_returned'}
    status = ACHIEVED if achieved_at else CANNOT_TELL if unobserved else NOT_ACHIEVED
    met = []
    for item in sg['invalidation_evidence']:
        if item['kind'] == 'no_region_change_after_attempts':
            attempts = [n for n, (raw, record) in enumerate(zip(raws, records))
                        if raw['dispatched'] == item['action'] and region_status(raw, record, item['region_xywh']) == NO]
            if len(attempts) >= item['attempts']:
                met.append({'kind': item['kind'], 'transitions': attempts[:item['attempts']]})
        elif item['kind'] == 'state_reported':
            hits = [n for n, record in enumerate(records) if (record['environment'].get('reported') or {}).get(
                'state_after') == item['state']]
            if hits:
                met.append({'kind': item['kind'], 'transitions': hits[:1]})
    used = len(raws)
    decision = (STOP_ACHIEVED if status == ACHIEVED else ABANDON_INVALIDATED if met else
                ABANDON_BUDGET if used >= sg['action_budget'] else CONTINUE)
    confirmed = [n for n, record in enumerate(records) if record['progress']['status'] == V.CONFIRMED]
    return {'status': status, 'achieved_at': achieved_at, 'invalidation_met': met, 'actions_used': used,
            'action_budget': sg['action_budget'], 'decision': decision,
            'confirmed_progress_transitions': confirmed,  # environment signal only; separate from the subgoal
            'usefulness': 'untested_hypothesis', 'never_asserted': list(NEVER_ASSERTED)}
