"""Bounded intervention interface (Track 3, stagnation_supervision_v1).

A reflection request is built only from transition_evidence_v1 records the agent already holds, plus the detector's
signals at the decision point and the available actions the agent observed. It has no parameter through which game
source, rules, environment files or solutions could enter. The same template and fields serve the periodic and the
triggered arm; the arm label is metadata and never reaches the prompt text, so timing is the treatment difference.

The supervisor must answer with exactly four fields:
  observed_pattern          what repeats or stalls in the shown evidence;
  evidence_refs             action indices from the shown evidence (nothing else may be cited);
  assumption_to_reconsider  which belief the behaviour seems to rest on;
  distinguishing_test       {'description', 'actions'}: at most MAX_TEST_ACTIONS available actions whose result would
                            separate two explanations, not a plan to finish the level.
`parse` validates an output against its own request; an invalid output is retained with its problems and is never
delivered. The lexical checks for source references and solution claims are a second line of defence only: the
first is that the request never contains such material.
"""
import hashlib
import json
import re

from research.transition_evidence_v1 import vocabulary as V

VERSION = 'stagnation_supervision_v1_intervention'
WINDOW = 12
FIELDS = ('observed_pattern', 'evidence_refs', 'assumption_to_reconsider', 'distinguishing_test')
MAX_TEXT = 300
MAX_TEST_ACTIONS = 3
MAX_OUTPUT_CHARS = 2000
REQUEST_KEYS = ('decision_index', 'evidence', 'frame_shape', 'available_actions', 'available_actions_source',
                'detector_signals')
PROMPT = (
    'You are reviewing the recent actions of an agent playing an unfamiliar grid game. You see only the observed '
    'evidence below: frame fingerprints, the exact actions sent, what the returned frames showed, and whether the '
    'environment reported progress. A missing progress signal does not mean progress is impossible, and a visible '
    'change does not mean progress.\n'
    'Reply with one JSON object with exactly these keys:\n'
    '  "observed_pattern": what repeats or stalls in the evidence (at most 300 characters);\n'
    '  "evidence_refs": the action_index values from the evidence that show it;\n'
    '  "assumption_to_reconsider": which belief the behaviour seems to rest on (at most 300 characters);\n'
    '  "distinguishing_test": {"description": ..., "actions": [at most 3 actions from available_actions, each '
    '{"action_id": ..., "action_data": {...}}]}: a test whose result would separate two explanations, not a plan '
    'to finish the level.\n'
    'Do not claim knowledge of the game\'s code, rules or solution.')
FORBIDDEN = {
    'source_reference': re.compile(r'\.py\b|source code|\bsource\b|game[_ ]?id|environment[_ ]files|\bimport\b|github'
                                   r'|arc[-_ ]?agi', re.I),
    'game_identifier': re.compile(r'\b[a-z]{2}\d{2}\b|\b[a-z]\d[a-z]\d\b', re.I),
    'solution_claim': re.compile(r'\bsolution\b|\bsolves?\b|\bsolved\b|\bthe answer\b|\bwill (complete|win|finish|solve)'
                                 r'|\bguaranteed\b', re.I),
}


def _summary(record):
    m = record['measurements']
    final = m['frames'][-1] if m['frames'] and m['frames'][-1]['valid'] else None
    changed = final['vs_pre']['changed_cells'] if final else None
    return {'action_index': record['identity']['action_index'], 'segment': record['segment'],
            'before': record['observations']['before_frames_sha256'][-1][:16],
            'action': record['action']['dispatched'], 'dispatch': record['dispatch']['status'],
            'visual_effect': m['visual_effect']['status'],
            'changed_cells': changed['value'] if changed and changed['status'] == 'measured' else None,
            'after': final['sha256'][:16] if final else None,
            'environment_events': record['environment']['events'], 'progress': record['progress']['status']}


def build_request(records, decision_index, arm, detector_signals, available_actions=None):
    """A request from records 0..decision_index only. `available_actions` is what the agent observed the
    environment offering; without it, only action ids already in the shown evidence may be proposed."""
    shown = [r for r in records if r['identity']['action_index'] <= decision_index][-WINDOW:]
    if not shown:
        raise ValueError('a request needs at least one record')
    observed_ids = sorted({r['action']['dispatched']['action_id'] for r in shown})
    content = {'decision_index': decision_index, 'evidence': [_summary(r) for r in shown],
               'frame_shape': shown[-1]['observations']['pre_frame_shape'],
               'available_actions': sorted(available_actions) if available_actions is not None else observed_ids,
               'available_actions_source': 'observation' if available_actions is not None else 'shown_evidence',
               'detector_signals': [{k: s[k] for k in ('signal', 'value', 'threshold', 'evidence')}
                                    for s in detector_signals]}
    text = PROMPT + '\n\nEvidence:\n' + json.dumps(content, sort_keys=True, separators=(',', ':'))
    return {'version': VERSION, 'arm': arm, 'episode_id': shown[-1]['identity']['episode_id'], 'content': content,
            'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest()}


def _text_problems(name, value):
    if not isinstance(value, str) or not value.strip():
        return [f'{name}: not a non-empty string']
    if len(value) > MAX_TEXT:
        return [f'{name}: longer than {MAX_TEXT} characters']
    return [f'{name}: {kind}' for kind, pattern in FORBIDDEN.items() if pattern.search(value)]


def _action_problems(action, content):
    if not isinstance(action, dict) or set(action) != {'action_id', 'action_data'}:
        return ['test action: needs exactly action_id and action_data']
    problems = []
    if type(action['action_id']) is not int or action['action_id'] not in content['available_actions']:
        problems.append('test action: action_id not among the available actions')
    data = action['action_data']
    if not isinstance(data, dict) or not set(data) <= {'x', 'y'}:
        problems.append('test action: action_data may hold only x and y')
    elif data:
        height, width = content['frame_shape']
        if set(data) != {'x', 'y'} or any(type(v) is not int for v in data.values()) or not (
                0 <= data['x'] < width and 0 <= data['y'] < height):
            problems.append('test action: coordinates outside the observed frame')
    return problems


def parse(text, request):
    """{'valid', 'problems', 'intervention' (None unless valid), 'raw'}. The raw output is always retained."""
    out = {'valid': False, 'problems': [], 'intervention': None, 'raw': text}
    if not isinstance(text, str):
        out['problems'].append('output is not text')
        return out
    if len(text) > MAX_OUTPUT_CHARS:
        out['problems'].append(f'output longer than {MAX_OUTPUT_CHARS} characters')
        return out
    try:
        value = json.loads(text)
    except ValueError:
        out['problems'].append('output is not JSON')
        return out
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        out['problems'].append('output must have exactly the fields ' + ', '.join(FIELDS))
        return out
    content = request['content']
    problems = _text_problems('observed_pattern', value['observed_pattern'])
    problems += _text_problems('assumption_to_reconsider', value['assumption_to_reconsider'])
    refs = value['evidence_refs']
    shown = {e['action_index'] for e in content['evidence']}
    if not isinstance(refs, list) or not refs or any(type(r) is not int for r in refs) or len(set(refs)) != len(refs):
        problems.append('evidence_refs: needs a non-empty list of distinct action indices')
    elif not set(refs) <= shown:
        problems.append('evidence_refs: cites an action index that was not shown')
    test = value['distinguishing_test']
    if not isinstance(test, dict) or set(test) != {'description', 'actions'}:
        problems.append('distinguishing_test: needs exactly description and actions')
    else:
        problems += _text_problems('distinguishing_test.description', test['description'])
        if not isinstance(test['actions'], list) or not 1 <= len(test['actions']) <= MAX_TEST_ACTIONS:
            problems.append(f'distinguishing_test.actions: 1 to {MAX_TEST_ACTIONS} actions')
        else:
            for action in test['actions']:
                problems += _action_problems(action, content)
    out['problems'] = problems
    if not problems:
        out['valid'] = True
        out['intervention'] = value
    return out


def render(intervention):
    """The only text an agent receives from the supervisor: the four validated fields in a fixed template."""
    test = intervention['distinguishing_test']
    return ('Reflection (a hypothesis from a reviewer, not an observation):\n'
            f'Observed pattern: {intervention["observed_pattern"]}\n'
            f'Evidence: action indices {intervention["evidence_refs"]}\n'
            f'Assumption to reconsider: {intervention["assumption_to_reconsider"]}\n'
            f'A test that would distinguish explanations: {test["description"]}\n'
            f'Test actions: {json.dumps(test["actions"], sort_keys=True)}\n'
            'A missing progress signal does not mean progress is impossible.')


def unobserved_state(record):
    """True when the agent's current state was not observed (the decision would rest on a guess)."""
    return (record['dispatch']['status'] == V.OUTCOME_UNKNOWN
            or record['observations']['availability']['status'] == V.MISSING)
