"""Workstream 3 factual transition questionnaire (DRAFT r0: for review; not frozen; no model calls).

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
The questions and answer schemas are identical across conditions.
"""
import copy
import hashlib
import json
import random

from research.transition_evidence_v1 import fixtures as F, reference as REF, transition as T, vocabulary as V

VERSION = 'ws3_transition_questionnaire_draft_r0'
PARTITIONS = {'development': ('ws3-questionnaire-development', 3), 'withheld': ('ws3-questionnaire-withheld', 12)}
# Balanced selection: each family's questions are drawn so every stratum appears at most CAP times, so no constant
# answer or single error pattern can dominate a family.
# Two levels: each answer key (claims: each claim-and-key pair) gets the same cap, filled round-robin across strata of
# (visual effect, dispatch status), so transients, change without progress and failed or unknown dispatches are all
# represented within each key.
CAP = {'development': 6, 'withheld': 32}
CLAIM_CAP = {'development': 2, 'withheld': 8}
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
SYSTEM_PROMPT = (
    "This is a retrospective questionnaire about one action in a grid game. It is not a decision: do not choose an "
    "action. Answer using only the supplied evidence. Return only one compact JSON object matching the supplied "
    "answer schema, with no rationale or Markdown.\n"
    "Evidence: 'frame_before' is the frame before the action; 'returned_frames' are the frames the game returned "
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
        'any_frame_differs': ('Does at least one valid returned frame differ from the frame before the action? Answer '
                              '"cannot_tell" if the evidence cannot decide.'),
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
    view = {'dispatch': {'status': outcome['status'], 'reason': outcome.get('reason')},
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
                            'fixture_family': family, 'raw': raw, 'record': record, 'expected': exp})
    return out


def build():
    probes, contexts, errors = [], {}, []
    for partition in PARTITIONS:
        pool = cases(partition)
        rng = random.Random(hashlib.sha256(f'{VERSION}:{partition}:select'.encode()).hexdigest())
        for family in FAMILIES:
            candidates = []
            for case in pool:
                for arg in (CLAIM_FAMILIES.get(family) or [None]):
                    keys = (key_from_record(case['record'], family, arg), key_from_reference(case['raw'], family, arg),
                            key_from_construction(case['expected'], family, arg))
                    if len(set(keys)) != 1:
                        errors.append((case['case_id'], family, arg, keys))
                    candidates.append((case, arg, keys[0]))
            groups = {}
            for c in candidates:
                strata = groups.setdefault((c[1], c[2]), {})
                strata.setdefault((c[0]['record']['measurements']['visual_effect']['status'],
                                   c[0]['record']['dispatch']['status']), []).append(c)
            cap = CLAIM_CAP[partition] if len(CLAIM_FAMILIES.get(family, ())) > 1 else CAP[partition]
            used = {}
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
                group = chosen
                for case, arg, key in group:
                    right = sorted(n for n, v in shortcuts(case['record'], family, arg).items() if v == key)
                    for condition in CONDITIONS:
                        cid = f"{partition}:{condition}:{case['case_id']}"
                        contexts[cid] = present(case['raw'], case['record'], condition)
                        suffix = family if arg is None else f'{family}:{arg}'
                        probes.append({'probe_id': f'{cid}:{suffix}', 'pair_id': f"{partition}:{case['case_id']}:{suffix}",
                                       'context_id': cid, 'source_context': case['sequence'], 'partition': partition,
                                       'condition': condition, 'family': family, 'arg': arg,
                                       'question': question_text(family, arg), 'key': key,
                                       'fixture_family': case['fixture_family'], 'shortcuts_correct': right})
    if errors:
        raise ValueError(f'key derivations disagree: {errors[:5]}')
    return {'version': VERSION, 'system_prompt': SYSTEM_PROMPT, 'contexts': contexts, 'probes': probes}
