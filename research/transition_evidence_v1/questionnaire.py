"""Workstream 3 factual transition questionnaire (DRAFT r2: for review; not frozen; no model calls).

Question: can the model read what happened after an action, keeping dispatch, observation availability, visual
change, reported environment events and progress apart, and without asserting unsupported causes?

Cases are single transitions from fresh fixture sequences (fixtures.Builder and fixtures.FAMILIES, new seeds; a whole
sequence stays in one partition). Every key is derived three ways and must agree:
1. from the transition record (transition.build via transition.history);
2. from the import-free reference (reference.facts);
3. from the fixture's construction.

Conditions (Experiment B, computed assistance; recommended in the design draft):
- `raw_evidence`: dispatch status and reason, the frame before the action, the returned frames exactly as
  returned (including invalid ones), and the environment fields before and after;
- `raw_plus_computed_record`: the same plus one field, `computed_measurements`, derived from the transition record
  and labelled as computed by a deterministic tool.
The questions and answer schemas are identical across conditions. This measures tool-assisted factual
interpretation, not independent visual reasoning.

Revision 2 (design review of r0):
- primary families, extraction checks and a boundary check are declared; each question is tagged for whether the
  candidate's record states its answer directly (`extraction_under_candidate`), reported separately;
- a larger pool with explicit floors (100 questions per primary family, 20 best-shortcut-disagreement questions,
  20 contexts per critical class, 100 contexts per over-claim denominator), and more dimension-change cases;
- keys respect the information boundary: construction knowledge that is not observable from the supplied evidence
  (e.g. whether an unobserved action changed the game) never enters a key;
- a preselected, descriptive transfer group of complete archived real transitions (previously exposed);
- a frozen schedule: withheld pass 1 with condition order balanced per pair, pass 2 exactly reversed; development and
  transfer once.
"""
import copy
import hashlib
import json
import random

from research.transition_evidence_v1 import fixtures as F, reference as REF, transition as T, vocabulary as V

VERSION = 'ws3_transition_questionnaire_draft_r2'
PARTITIONS = {'development': ('ws3-questionnaire-development', 3), 'withheld': ('ws3-questionnaire-withheld', 30)}
# Balanced selection, two levels: each answer key (claims: each claim-and-key pair) gets the same cap, filled
# round-robin across strata of (visual effect, dispatch status). The cap is set so each family reaches about TARGET
# questions: ceil(TARGET / number of key groups in the family).
TARGET = {'development': 18, 'withheld': 120}
# claim_descriptive's shortcut fails only on failed or unknown dispatches; a larger target reaches its disagreement floor.
TARGET_FACTOR = {'claim_descriptive': 1.5}
CONDITIONS = ('raw_evidence', 'raw_plus_computed_record')

CLAIMS = {
    'any_change': 'At least one returned frame differs from the frame before the action.',
    'no_change': 'No returned frame differs from the frame before the action.',
    'progress_reported': 'The environment reported progress (a completed level or a win) after this action.',
    'action_executed': 'The game received and carried out this action.',
    'caused_change': 'This action caused a visible change in the frames.',
}
ANSWERS = {
    'dispatch_status': ['acknowledged', 'failed', 'outcome_unknown'],
    'observation_availability': ['complete', 'partial', 'missing', 'not_applicable'],
    'any_frame_differs': ['yes', 'no', 'cannot_tell'],
    'final_equals_initial': ['yes', 'no', 'cannot_tell'],
    'count_defined': ['defined', 'undefined_dimensions_differ', 'undefined_no_valid_final_frame'],
    'level_completion_reported': ['yes', 'no', 'not_observed'],
    'progress_status': ['confirmed', 'unknown'],
    'claim_descriptive': ['supported', 'contradicted', 'not_established'],
    'claim_progress': ['supported', 'contradicted', 'not_established'],
    'claim_causal': ['supported', 'contradicted', 'not_established'],
}
FAMILIES = tuple(ANSWERS)
# Claims are split so each error pattern has its own family: descriptive facts, reported progress, and causes.
CLAIM_FAMILIES = {'claim_descriptive': ('action_executed', 'any_change', 'no_change'),
                  'claim_progress': ('progress_reported',), 'claim_causal': ('caused_change',)}
ROLES = {
    'primary': ('observation_availability', 'any_frame_differs', 'final_equals_initial', 'progress_status',
                'claim_descriptive', 'claim_progress', 'claim_causal'),
    'extraction_check': ('dispatch_status', 'level_completion_reported'),
    'boundary_check': ('count_defined',),
}
ROLE_OF = {f: role for role, fams in ROLES.items() for f in fams}
# Families whose answer the candidate's computed record states directly (reported separately from families that
# require combining fields or rejecting unsupported claims).
EXTRACTION_UNDER_CANDIDATE = frozenset({'dispatch_status', 'observation_availability', 'any_frame_differs',
                                        'final_equals_initial', 'count_defined', 'level_completion_reported',
                                        'progress_status'})
# Critical classes of transition that every withheld question set must cover (distinct contexts).
CRITICAL_CLASSES = ('failed_dispatch', 'unknown_outcome', 'acknowledged_missing_observation', 'transient_change',
                    'final_frame_difference', 'progress_without_visible_change', 'visible_change_without_progress',
                    'dimension_change')
FLOORS = {'primary_questions': 100, 'shortcut_disagreement': 20, 'critical_class_contexts': 20,
          'over_claim_denominator_contexts': 100}
SYSTEM_PROMPT = (
    "This is a retrospective questionnaire about one action in a grid game. It is not a decision: do not choose an "
    "action. Answer using only the supplied evidence. Return only one compact JSON object matching the supplied "
    "answer schema, with no rationale or Markdown.\n"
    "Evidence: 'dispatched_action' is the action that was sent; 'frame_before' is the frame before the action; "
    "'returned_frames' are the frames the game returned "
    "after it, in order. A frame is a list of rows (grid[y][x], x is the column, y is the row); a valid frame is a "
    "non-empty rectangle of integers 0 to 15. A dispatch that failed was not delivered; an outcome that is unknown "
    "may have been delivered but its result was not observed. Environment fields are what the game reported. "
    "A visible change is not by itself progress, and a sequence of events is not by itself a cause.")


def question_text(family, arg=None):
    if family in CLAIM_FAMILIES:
        return (f'Claim: "{CLAIMS[arg]}" Is this claim supported by the evidence, contradicted by it, or not '
                'established by it?')
    return {
        'dispatch_status': 'Was the action acknowledged by the game, did the dispatch fail, or is its outcome unknown?',
        'observation_availability': (
            'Which describes the returned frames? "complete": at least one frame was returned and every returned frame '
            'is valid; "partial": some returned frames are valid and some are not; "missing": the action was '
            'acknowledged but no valid frame was returned, or its outcome is unknown; "not_applicable": the dispatch '
            'failed, so no frame was expected.'),
        'any_frame_differs': ('Across the returned frames, does the evidence show that at least one returned frame differs '
                              'from the frame before the action? Answer "yes" if a valid returned frame differs; "no" only '
                              'if frames were returned, every returned frame is valid, and none differs; otherwise '
                              '"cannot_tell" (the dispatch failed, the outcome is unknown, no frame was returned, or some '
                              'returned frames are invalid and no valid one differs: an invalid frame could hide a '
                              'change).'),
        'final_equals_initial': ('Is the final returned frame valid and identical to the frame before the action? Answer '
                                 '"yes", "no", or "cannot_tell" if there is no valid final returned frame.'),
        'count_defined': ('Is a cell-by-cell count of differences between the final returned frame and the frame before '
                          'the action defined? "defined": both are valid frames of the same dimensions; '
                          '"undefined_dimensions_differ": both are valid but their dimensions differ; '
                          '"undefined_no_valid_final_frame": there is no valid final returned frame.'),
        'level_completion_reported': ('Did the environment report that a level was completed after this action (the '
                                      'completed-level count increased)? Answer "not_observed" if no environment state '
                                      'after the action was observed.'),
        'progress_status': ('Does the evidence confirm progress: a reported increase in completed levels, or a win? '
                            'Answer "confirmed" or "unknown". A visible change alone does not confirm progress, and '
                            'the absence of a report does not show that no progress occurred.'),
    }[family]


def response_schema(family):
    return {'type': 'object', 'properties': {'answer': {'type': 'string', 'enum': list(ANSWERS[family])}},
            'required': ['answer'], 'additionalProperties': False}


def build_request(presented, probe):
    user = {'evidence': presented, 'question': probe['question']}
    return {'model': 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8', 'messages': [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': json.dumps(user, sort_keys=True, separators=(',', ':'))}],
        'temperature': 0, 'seed': 0, 'max_tokens': 32, 'chat_template_kwargs': {'enable_thinking': False},
        'response_format': {'type': 'json_schema', 'json_schema': {'name': f'{VERSION}_{probe["family"]}',
                                                                   'strict': True, 'schema': response_schema(probe['family'])}}}


# ------------------------------------------------------------------ presentations

def raw_view(raw):
    outcome = raw['outcome']
    view = {'dispatched_action': copy.deepcopy(raw['dispatched']),
            'dispatch': {'status': outcome['status'], 'reason': outcome.get('reason')},
            'frame_before': copy.deepcopy(raw['before']['frames'][-1]),
            'environment_before': {k: raw['before'].get(k) for k in ('levels_completed', 'state', 'full_reset')}}
    if outcome['status'] == 'acknowledged':
        view['returned_frames'] = copy.deepcopy(outcome['after'].get('frames') or [])
        view['environment_after'] = {k: outcome['after'].get(k) for k in ('levels_completed', 'state', 'full_reset')}
    else:
        view['returned_frames'] = 'none observed'
        view['environment_after'] = 'not observed'
    return view


def computed_view(record):
    m = record['measurements']
    frames = [{'index': f['index'], 'valid': f['valid'], **({'reason': f['reason']} if not f['valid'] else {
        'comparability_to_frame_before': f['vs_pre']['comparability'],
        'changed_cells_vs_frame_before': f['vs_pre']['changed_cells'],
        'changed_cells_vs_previous_frame': f['vs_previous']['changed_cells']})} for f in m['frames']]
    return {'computed_by': 'deterministic tool from the evidence above, not the model',
            'observation_availability': record['observations']['availability'],
            'returned_frames': frames, 'any_returned_frame_differs': m['any_returned_frame_differs'],
            'final_frame_equals_frame_before': m['final_frame_equals_pre'], 'visual_effect': m['visual_effect'],
            'environment_events': record['environment']['events'],
            'progress': {k: v for k, v in record['progress'].items() if k != 'source'}}  # provenance stays in the record


def present(raw, record, condition):
    view = raw_view(raw)
    if condition == 'raw_plus_computed_record':
        view['computed_measurements'] = computed_view(record)
    return view


# ------------------------------------------------------------------ keys (three derivations)

def _tri(measure):
    return 'cannot_tell' if measure['status'] != 'measured' else ('yes' if measure['value'] else 'no')


def key_from_record(record, family, arg=None):
    m = record['measurements']
    events = record['environment']['events']
    if family == 'dispatch_status':
        return record['dispatch']['status']
    if family == 'observation_availability':
        return record['observations']['availability']['status']
    if family == 'any_frame_differs':
        return _tri(m['any_returned_frame_differs'])
    if family == 'final_equals_initial':
        return _tri(m['final_frame_equals_pre'])
    if family == 'count_defined':
        final = m['frames'][-1] if m['frames'] else None
        if not final or not final['valid']:
            return 'undefined_no_valid_final_frame'
        return 'defined' if final['vs_pre']['comparability'] == V.COMPARABLE else 'undefined_dimensions_differ'
    if family == 'level_completion_reported':
        return 'not_observed' if V.NOT_OBSERVED in events else ('yes' if V.LEVEL_COMPLETED in events else 'no')
    if family == 'progress_status':
        return record['progress']['status']
    if family in CLAIM_FAMILIES:
        differs = m['any_returned_frame_differs']
        if arg == 'any_change':
            return {'yes': 'supported', 'no': 'contradicted', 'cannot_tell': 'not_established'}[_tri(differs)]
        if arg == 'no_change':
            return {'yes': 'contradicted', 'no': 'supported', 'cannot_tell': 'not_established'}[_tri(differs)]
        if arg == 'progress_reported':
            return 'supported' if record['progress']['status'] == V.CONFIRMED else 'not_established'
        if arg == 'action_executed':
            return {V.ACKNOWLEDGED: 'supported', V.FAILED: 'contradicted',
                    V.OUTCOME_UNKNOWN: 'not_established'}[record['dispatch']['status']]
        if arg == 'caused_change':  # a sequence alone never establishes a cause; no visible change contradicts it
            return 'contradicted' if _tri(differs) == 'no' else 'not_established'
    raise ValueError(family)


def key_from_reference(raw, family, arg=None):
    f = REF.facts(raw)
    tri = lambda v: 'cannot_tell' if v is None else ('yes' if v else 'no')  # noqa: E731
    if family == 'dispatch_status':
        return f['dispatch']
    if family == 'observation_availability':
        return f['availability']
    if family == 'any_frame_differs':
        return tri(f['any_differs'])
    if family == 'final_equals_initial':
        return tri(f['final_equals'])
    if family == 'count_defined':
        if not f['vs_pre'] or f['vs_pre'][-1] == 'invalid':
            return 'undefined_no_valid_final_frame'
        return 'undefined_dimensions_differ' if f['vs_pre'][-1] is None else 'defined'
    if family == 'level_completion_reported':
        return 'not_observed' if 'not_observed' in f['events'] else ('yes' if 'level_completed' in f['events'] else 'no')
    if family == 'progress_status':
        return f['progress']
    if family in CLAIM_FAMILIES:
        d = tri(f['any_differs'])
        return {'any_change': {'yes': 'supported', 'no': 'contradicted', 'cannot_tell': 'not_established'}[d],
                'no_change': {'yes': 'contradicted', 'no': 'supported', 'cannot_tell': 'not_established'}[d],
                'progress_reported': 'supported' if f['progress'] == 'confirmed' else 'not_established',
                'action_executed': {'acknowledged': 'supported', 'failed': 'contradicted',
                                    'outcome_unknown': 'not_established'}[f['dispatch']],
                'caused_change': 'contradicted' if d == 'no' else 'not_established'}[arg]
    raise ValueError(family)


def key_from_construction(expected, family, arg=None):
    tri = lambda v: 'cannot_tell' if v is None else ('yes' if v else 'no')  # noqa: E731
    if family == 'dispatch_status':
        return expected['dispatch']
    if family == 'observation_availability':
        return expected['availability']
    if family == 'any_frame_differs':
        return tri(expected['any_differs'])
    if family == 'final_equals_initial':
        return tri(expected['final_equals'])
    if family == 'count_defined':
        last = expected['vs_pre'][-1] if expected['vs_pre'] else 'invalid'
        return 'undefined_no_valid_final_frame' if last == 'invalid' else (
            'undefined_dimensions_differ' if last is None else 'defined')
    if family == 'level_completion_reported':
        return ('not_observed' if 'not_observed' in expected['events'] else
                'yes' if 'level_completed' in expected['events'] else 'no')
    if family == 'progress_status':
        return expected['progress']
    if family in CLAIM_FAMILIES:
        d = tri(expected['any_differs'])
        return {'any_change': {'yes': 'supported', 'no': 'contradicted', 'cannot_tell': 'not_established'}[d],
                'no_change': {'yes': 'contradicted', 'no': 'supported', 'cannot_tell': 'not_established'}[d],
                'progress_reported': 'supported' if expected['progress'] == 'confirmed' else 'not_established',
                'action_executed': {'acknowledged': 'supported', 'failed': 'contradicted',
                                    'outcome_unknown': 'not_established'}[expected['dispatch']],
                'caused_change': 'contradicted' if d == 'no' else 'not_established'}[arg]
    raise ValueError(family)


# ------------------------------------------------------------------ predeclared shortcuts

def shortcuts(record, family, arg=None):
    """Answers available without reading the evidence correctly, including the error patterns this stream guards
    against: always unknown; any change means progress; a failed or unknown dispatch read as no change; final frame
    only (misses transients); a temporal sequence taken as a cause."""
    m = record['measurements']
    differs = _tri(m['any_returned_frame_differs'])
    final = _tri(m['final_frame_equals_pre'])
    unobserved = record['dispatch']['status'] != V.ACKNOWLEDGED
    table = {
        'dispatch_status': {'always_acknowledged': 'acknowledged'},
        'observation_availability': {'always_complete': 'complete',
                                     'failed_or_unknown_as_complete': 'complete' if unobserved else
                                     record['observations']['availability']['status']},
        'any_frame_differs': {'always_cannot_tell': 'cannot_tell', 'always_no': 'no',
                              'failed_or_unknown_as_no_change': 'no' if unobserved else differs,
                              'final_frame_only': {'yes': 'no', 'no': 'yes'}.get(final, 'cannot_tell')},
        'final_equals_initial': {'always_cannot_tell': 'cannot_tell', 'always_yes': 'yes',
                                 'failed_or_unknown_as_no_change': 'yes' if unobserved else final},
        'count_defined': {'always_defined': 'defined'},
        'level_completion_reported': {'always_no': 'no',
                                      'change_means_progress': 'yes' if differs == 'yes' else ('no' if differs == 'no'
                                                                                             else 'not_observed')},
        'progress_status': {'always_unknown': 'unknown',
                            'change_means_progress': 'confirmed' if differs == 'yes' else 'unknown'},
        'claim_descriptive': {'always_not_established': 'not_established', 'always_supported': 'supported',
                              'failed_or_unknown_as_no_change': (
                                  ('contradicted' if arg == 'any_change' else 'supported' if arg == 'no_change'
                                   else key_from_record(record, family, arg)) if unobserved
                                  else key_from_record(record, family, arg))},
        'claim_progress': {'always_not_established': 'not_established',
                           'change_means_progress': 'supported' if differs == 'yes' else
                           key_from_record(record, family, arg)},
        'claim_causal': {'always_not_established': 'not_established',
                         'sequence_as_cause': 'supported' if differs == 'yes' else key_from_record(record, family, arg)},
    }
    return table[family]


# ------------------------------------------------------------------ build

# Construction knowledge that is not observable from the supplied evidence. key_from_construction never reads it;
# tests flip it and require identical keys.
UNOBSERVABLE_CONSTRUCTION = ('changed_underneath',)


def critical_classes(record):
    m = record['measurements']
    status, visual = record['dispatch']['status'], m['visual_effect']['status']
    differs = _tri(m['any_returned_frame_differs'])
    final = m['frames'][-1] if m['frames'] else None
    classes = []
    if status == V.FAILED:
        classes.append('failed_dispatch')
    if status == V.OUTCOME_UNKNOWN:
        classes.append('unknown_outcome')
    if status == V.ACKNOWLEDGED and record['observations']['availability']['status'] == V.MISSING:
        classes.append('acknowledged_missing_observation')
    if visual == V.CHANGED_THEN_RETURNED:
        classes.append('transient_change')
    if visual == V.FINAL_FRAME_DIFFERS:
        classes.append('final_frame_difference')
    if record['progress']['status'] == V.CONFIRMED and differs == 'no':
        classes.append('progress_without_visible_change')
    if differs == 'yes' and record['progress']['status'] == V.UNKNOWN:
        classes.append('visible_change_without_progress')
    if final and final['valid'] and final['vs_pre']['comparability'] == V.DIMENSIONS_DIFFER:
        classes.append('dimension_change')
    return classes


def cases(partition):
    seed, count = PARTITIONS[partition]
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    out = []
    for family, make in F.FAMILIES.items():
        for i in range(count):
            b = F.Builder(random.Random(rng.random()))
            make(b)
            opaque = 'q-' + hashlib.sha256(f'{partition}:{family}:{i}'.encode()).hexdigest()[:12]
            for n, raw in enumerate(b.raws):
                raw['identity'] = {'episode_id': opaque, 'action_index': n}
            expected = F.sequence_expectations(b)
            for raw, record, exp in zip(b.raws, T.history(b.raws), expected):
                out.append({'case_id': f"{opaque}-{raw['identity']['action_index']}", 'sequence': opaque,
                            'fixture_family': family, 'raw': raw, 'record': record, 'expected': exp,
                            'classes': critical_classes(record)})
    return out


# Transfer: preselected by a written rule before any model answer: in each first-block action-effect-history v1
# episode (b1-*), the steps with index 3 and 9; and every Stage B R8 step. Complete transitions only (pre-action
# frame, dispatched action, dispatch status, ordered returned frames, retained environment fields). Previously
# exposed development evidence: descriptive, never part of the gate.
TRANSFER_STEPS = (3, 9)


def transfer_cases():
    from scripts.replay_transition_evidence_v1 import (AEH_LOCK, R8_LOCK, R8_TRAJECTORY, parse_action, raw_step,
                                                       verified_zip)
    out = []
    lock, bundle = verified_zip(AEH_LOCK)
    for name in sorted(n for n in lock['members'] if '/episodes/b1-' in n and n.endswith('.json')):
        raw_bytes = bundle.read(name)
        if hashlib.sha256(raw_bytes).hexdigest() != lock['members'][name]['sha256']:
            raise ValueError('member hash mismatch: ' + name)
        episode = json.loads(raw_bytes)
        steps = [s for s in episode['steps'] if s['index'] in TRANSFER_STEPS]
        raws = [raw_step(episode['episode_id'], s, parse_action(episode['calls'][s['call_index']]['response']),
                         'offline_development_engine') for s in episode['steps']]
        records = T.history(raws)
        for s, raw, record in zip(episode['steps'], raws, records):
            if s in steps:
                out.append(_transfer_case(f"aeh-{episode['episode_id']}-{s['index']}", raw, record))
    lock, bundle = verified_zip(R8_LOCK)
    raw_bytes = bundle.read(R8_TRAJECTORY)
    if hashlib.sha256(raw_bytes).hexdigest() != lock['members'][R8_TRAJECTORY]['sha256']:
        raise ValueError('R8 trajectory hash mismatch')
    trajectory = json.loads(raw_bytes)
    for n, episode in enumerate(trajectory['episodes']):
        episode_id = f"r8-{episode['arm']}-{n}"
        raws = [raw_step(episode_id, s, parse_action(episode['calls'][s['decision_call']]['response']),
                         trajectory['kind']) for s in episode['steps']]
        for s, raw, record in zip(episode['steps'], raws, T.history(raws)):
            out.append(_transfer_case(f"{episode_id}-{s['index']}", raw, record))
    return out


def _transfer_case(name, raw, record):
    opaque = 't-' + hashlib.sha256(name.encode()).hexdigest()[:12]
    raw = {**raw, 'identity': {'episode_id': opaque, 'action_index': raw['identity']['action_index']}}
    return {'case_id': opaque, 'sequence': opaque, 'fixture_family': 'archived_transition', 'raw': raw,
            'record': record, 'expected': None, 'classes': critical_classes(record), 'source': name}


def _keys(case, family, arg):
    keys = [key_from_record(case['record'], family, arg), key_from_reference(case['raw'], family, arg)]
    if case['expected'] is not None:
        keys.append(key_from_construction(case['expected'], family, arg))
    return keys


def _probe(partition, case, family, arg, key, condition):
    cid = f"{partition}:{condition}:{case['case_id']}"
    suffix = family if arg is None else f'{family}:{arg}'
    right = sorted(n for n, v in shortcuts(case['record'], family, arg).items() if v == key)
    return cid, {'probe_id': f'{cid}:{suffix}', 'pair_id': f"{partition}:{case['case_id']}:{suffix}",
                 'context_id': cid, 'case_context': f"{partition}:{case['case_id']}", 'source_context': case['sequence'],
                 'partition': partition, 'condition': condition, 'family': family, 'role': ROLE_OF[family],
                 'extraction_under_candidate': family in EXTRACTION_UNDER_CANDIDATE, 'arg': arg,
                 'question': question_text(family, arg), 'key': key, 'fixture_family': case['fixture_family'],
                 'critical_classes': case['classes'], 'shortcuts_correct': right}


def _select(partition, pool, family, rng, errors):
    groups = {}
    for case in pool:
        for arg in (CLAIM_FAMILIES.get(family) or [None]):
            keys = _keys(case, family, arg)
            if len(set(keys)) != 1:
                errors.append((case['case_id'], family, arg, keys))
            strata = groups.setdefault((arg, keys[0]), {})
            strata.setdefault((case['record']['measurements']['visual_effect']['status'],
                               case['record']['dispatch']['status']), []).append((case, arg, keys[0]))
    cap = -(-int(TARGET[partition] * TARGET_FACTOR.get(family, 1)) // len(groups))
    used, chosen_all = {}, []
    for strata in (groups[k] for k in sorted(groups, key=str)):
        queues = []
        for name in sorted(strata):
            queue = strata[name]
            rng.shuffle(queue)
            queues.append(queue)
        chosen = []
        while len(chosen) < cap and any(queues):
            for queue in queues:
                if queue and len(chosen) < cap:
                    queue.sort(key=lambda c: used.get(c[0]['sequence'], 0))  # spread across sequences
                    chosen.append(queue.pop(0))
                    used[chosen[-1][0]['sequence']] = used.get(chosen[-1][0]['sequence'], 0) + 1
        chosen_all += chosen
    return chosen_all


def build():
    probes, contexts, errors = [], {}, []
    for partition in PARTITIONS:
        pool = cases(partition)
        rng = random.Random(hashlib.sha256(f'{VERSION}:{partition}:select'.encode()).hexdigest())
        for family in FAMILIES:
            for case, arg, key in _select(partition, pool, family, rng, errors):
                for condition in CONDITIONS:
                    cid, probe = _probe(partition, case, family, arg, key, condition)
                    contexts[cid] = present(case['raw'], case['record'], condition)
                    probes.append(probe)
    seen_views = set()
    transfer = []
    for case in transfer_cases():  # identical archived transitions (same frames, action and fields) are asked once
        view = json.dumps(raw_view(case['raw']), sort_keys=True)
        if view not in seen_views:
            seen_views.add(view)
            transfer.append(case)
    for n, case in enumerate(transfer):  # every family once; claims rotate by a fixed rule
        for family in FAMILIES:
            args = CLAIM_FAMILIES.get(family) or [None]
            arg = args[n % len(args)]
            keys = _keys(case, family, arg)
            if len(set(keys)) != 1:
                errors.append((case['case_id'], family, arg, keys))
            for condition in CONDITIONS:
                cid, probe = _probe('transfer', case, family, arg, keys[0], condition)
                contexts[cid] = present(case['raw'], case['record'], condition)
                probes.append(probe)
    if errors:
        raise ValueError(f'key derivations disagree: {errors[:5]}')
    value = {'version': VERSION, 'system_prompt': SYSTEM_PROMPT, 'contexts': contexts, 'probes': probes,
             'schedule': schedule(probes)}
    coverage(value['probes'])
    return value


SCHEDULE_SEED = 'ws3-questionnaire-schedule'


def schedule(probes):
    """Withheld pass 1: cases in seeded order; each question's two conditions adjacent, the reference first for half
    the pairs and the candidate first for the other half (alternating in seeded pair order). Pass 2: pass 1 exactly
    reversed. Development and transfer: pass 1 only."""
    rng = random.Random(hashlib.sha256(SCHEDULE_SEED.encode()).hexdigest())
    order = []
    for partition, passes in (('withheld', 2), ('development', 1), ('transfer', 1)):
        pairs = {}
        for p in probes:
            if p['partition'] == partition:
                pairs.setdefault(p['case_context'], {}).setdefault(p['pair_id'], {})[p['condition']] = p['probe_id']
        ids, flip = [], 0
        cases_ = sorted(pairs)
        rng.shuffle(cases_)
        for case in cases_:
            for pair in sorted(pairs[case]):
                first, second = CONDITIONS if flip % 2 == 0 else CONDITIONS[::-1]
                ids += [pairs[case][pair][first], pairs[case][pair][second]]
                flip += 1
        order.append({'partition': partition, 'pass': 'pass_1', 'probe_ids': ids})
        if passes == 2:
            order.append({'partition': partition, 'pass': 'pass_2', 'probe_ids': ids[::-1]})
    return order


def coverage(probes, strict=True):
    """The design floors, on the withheld partition (reference condition; the candidate asks the same questions)."""
    held = [p for p in probes if p['partition'] == 'withheld' and p['condition'] == 'raw_evidence']
    report, failures = {'families': {}, 'critical_classes': {}, 'over_claim_denominators': {}}, []
    for family in FAMILIES:
        group = [p for p in held if p['family'] == family]
        counts = {}
        for p in group:
            for name in p['shortcuts_correct']:
                counts[name] = counts.get(name, 0) + 1
        best = max(counts.values(), default=0)
        row = {'n': len(group), 'best_shortcut_accuracy': round(best / len(group), 4) if group else None,
               'shortcut_disagreement_n': len(group) - best, 'role': ROLE_OF[family]}
        report['families'][family] = row
        if ROLE_OF[family] == 'primary' and (row['n'] < FLOORS['primary_questions']
                                             or row['shortcut_disagreement_n'] < FLOORS['shortcut_disagreement']):
            failures.append((family, row))
    for name in CRITICAL_CLASSES:
        n = len({p['case_context'] for p in held if name in p['critical_classes']})
        report['critical_classes'][name] = n
        if n < FLOORS['critical_class_contexts']:
            failures.append((name, n))
    for gate, members in OVER_CLAIM_GATES.items():
        n = len({p['case_context'] for p in held if (p['family'], p['key']) in members})
        report['over_claim_denominators'][gate] = n
        if n < FLOORS['over_claim_denominator_contexts']:
            failures.append((gate, n))
    if failures and strict:
        raise ValueError(f'coverage below the design floors: {failures}')
    return report


# Over-claim gates: (family, key) pairs whose context enters the denominator; an affirmative answer on such a
# question (or an invalid one, so avoidance cannot help) in either pass is an over-claim.
OVER_CLAIM_GATES = {
    'false_progress': {('progress_status', 'unknown'), ('claim_progress', 'not_established'),
                       ('level_completion_reported', 'no'), ('level_completion_reported', 'not_observed')},
    'unsupported_causal_claim': {('claim_causal', 'not_established'), ('claim_causal', 'contradicted')},
}
AFFIRMATIVE = {'progress_status': 'confirmed', 'claim_progress': 'supported', 'level_completion_reported': 'yes',
               'claim_causal': 'supported'}
