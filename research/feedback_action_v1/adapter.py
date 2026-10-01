"""Isolated decision-procedure adapter: baseline and structured hypothesis-testing candidate.

The adapter changes only the decision procedure. It receives an observation already produced by the existing
pipeline and the evidence view (`evidence.view`, identical in both arms); it never builds observations, history,
dispatches or environments. Both arms return the same `action` object, validated by the same frozen validator
(`certification.phase4_transient_v2.action_contract`). The candidate differs in exactly four places, and
`strip_procedure` removes all four to give the baseline request byte for byte:

1. one extra system-prompt paragraph (PROCEDURE);
2. one extra required response property, `hypothesis_test`, placed before `action`;
3. a larger completion budget (CANDIDATE_MAX_TOKENS against BASELINE_MAX_TOKENS);
4. carried state: a top-level `previous_model_statement` beside (never inside) `observation`.

The candidate's extra prompt and completion tokens are reported, never called compute-matched.

Carried-state rules (`carried_statement`). Requests are otherwise stateless, so the candidate's previous belief must
be sent explicitly or it cannot be revised. The field is labelled a model statement (a hypothesis), not an
observation or evidence, and it is never written into a transition record. Exactly one of:
- the previous decision's valid hypothesis_test (hypothesis, status, prediction, if_different; text capped at
  TEXT_LIMIT), with `about` = the ref of the transition its action produced, or null if the action was not
  dispatched;
- `available: false` with a reason, when there was no previous decision in the episode, when the previous output
  had no valid hypothesis_test (an older statement is never carried in its place), or when the previous transition
  ended the segment (reset, level-count change or terminal state: the statement is cleared, like the evidence
  window).

Dispatch rule (same in both arms): a decision is dispatched if and only if its `action` is valid. A candidate whose
action is valid but whose `hypothesis_test` block is invalid is still dispatched; the block failure is retained and
counted separately. A truncated response (`finish_reason == 'length'`) is invalid in both arms.
"""
import copy
import json

from certification.phase4_transient_v2.action_contract import response_format, validate_action
from research.feedback_action_v1 import evidence as E

VERSION = 'feedback_action_v1_adapter'
ARMS = ('baseline', 'candidate')
BASELINE_MAX_TOKENS = 128
CANDIDATE_MAX_TOKENS = 640
TEXT_LIMIT = 240
CITATION_LIMIT = 4

SYSTEM_PROMPT = (
    "You control one ARC-AGI-3 game from the supplied observation. Return only one JSON object matching the "
    "supplied response schema, with no Markdown.\n"
    "Actions: choose exactly one action_id from legal_actions. Never choose reset or action 0. ACTION6 is the only "
    "action that takes arguments: action_data must be {\"x\": X, \"y\": Y} with integers 0 to 63, where x is the "
    "column counted left to right and y is the row counted top to bottom, so the selected cell is "
    "current_grid[y][x]. Every other action takes empty action_data {}.\n"
    "An action being legal does not mean its effect is known. Effects can only be learned from observations. "
    "action_effect_history lists earlier transitions measured by a deterministic tool; its description explains "
    "every field."
)
PROCEDURE = (
    "Before the action, fill hypothesis_test, a short structured test of one hypothesis about this game:\n"
    "- hypothesis: one sentence you are currently testing. status: new, retained, or revised (revise when an "
    "observation conflicts with it).\n"
    "- supporting and conflicting: earlier transitions as {\"ref\": \"T<n>\", \"claim\": ...}. Cite only refs listed "
    "in action_effect_history. Each claim must be exactly what that entry shows: its visual_effect, "
    "dispatch_failed, outcome_unknown, level_completed, reset_acknowledged, or whether its from_state is "
    "same_state_as_now or different_state_from_now. A failed or unknown dispatch is not evidence of no change.\n"
    "- prediction: what the next returned frames will show after your action: visual_effect, whether a level "
    "will be completed, and optionally changed_region_xyxy [x0, y0, x1, y1] containing every cell that will "
    "differ (null when you do not predict a region or predict no change).\n"
    "- if_different: one sentence on what a different result would imply for the hypothesis.\n"
    "previous_model_statement is your own previous hypothesis_test, carried forward when available. It is a "
    "statement, not an observation and not evidence, and cannot be cited. Its about field names the transition "
    "its prediction was about: compare them, and revise when the transition conflicts with it."
)
PREVIOUS_FIELD = 'previous_model_statement'
STATEMENT_NOTE = 'your own previous statement: a hypothesis, not an observation and not evidence'

VISUAL_PREDICTIONS = ('no_observed_change', 'changed_then_returned', 'final_frame_differs')
CLAIMS = ('no_observed_change', 'changed_then_returned', 'final_frame_differs', 'indeterminate', 'dispatch_failed',
          'outcome_unknown', 'level_completed', 'reset_acknowledged', 'same_state_as_now', 'different_state_from_now')
STATUSES = ('new', 'retained', 'revised')
CITATION = {'type': 'object', 'properties': {'ref': {'type': 'string', 'pattern': '^T[0-9]+$'},
                                             'claim': {'type': 'string', 'enum': list(CLAIMS)}},
            'required': ['ref', 'claim'], 'additionalProperties': False}
HYPOTHESIS_TEST = {
    'type': 'object',
    'properties': {
        'hypothesis': {'type': 'string', 'maxLength': TEXT_LIMIT},
        'status': {'type': 'string', 'enum': list(STATUSES)},
        'supporting': {'type': 'array', 'items': CITATION, 'maxItems': CITATION_LIMIT},
        'conflicting': {'type': 'array', 'items': CITATION, 'maxItems': CITATION_LIMIT},
        'prediction': {'type': 'object', 'properties': {
            'visual_effect': {'type': 'string', 'enum': list(VISUAL_PREDICTIONS)},
            'level_completed': {'type': 'boolean'},
            'changed_region_xyxy': {'anyOf': [{'type': 'null'}, {
                'type': 'array', 'items': {'type': 'integer', 'minimum': 0, 'maximum': 63},
                'minItems': 4, 'maxItems': 4}]}},
            'required': ['visual_effect', 'level_completed', 'changed_region_xyxy'], 'additionalProperties': False},
        'if_different': {'type': 'string', 'maxLength': TEXT_LIMIT}},
    'required': ['hypothesis', 'status', 'supporting', 'conflicting', 'prediction', 'if_different'],
    'additionalProperties': False}


def candidate_response_format(legal):
    value = copy.deepcopy(response_format(legal))
    schema = value['json_schema']['schema']
    schema['properties'] = {'hypothesis_test': copy.deepcopy(HYPOTHESIS_TEST), **schema['properties']}
    schema['required'] = ['hypothesis_test', 'action']
    return value


def no_statement(reason):
    return {'record': 'model_statement', 'available': False, 'reason': reason}


def carried_statement(previous_decision, previous_events=None, previous_ref=None):
    """The candidate's carried state for the next request (rules in the module docstring).

    previous_decision: the adapter decision record of the previous call in this episode, or None.
    previous_events: the environment events of the transition that call's action produced (None if not dispatched).
    previous_ref: that transition's ref, 'T<n>' (None if not dispatched).
    """
    if previous_decision is None:
        return no_statement('no earlier decision in this episode')
    block = previous_decision.get('procedure')
    if block is None:
        return no_statement('the previous output had no valid hypothesis_test; no older statement is carried')
    if previous_events is not None and set(previous_events) & E.BOUNDARY_EVENTS:
        return no_statement('cleared: the previous transition ended the segment (reset, level change or terminal)')
    return {'record': 'model_statement', 'available': True, 'statement_status': 'hypothesis', 'note': STATEMENT_NOTE,
            'about': previous_ref, 'hypothesis': block['hypothesis'][:TEXT_LIMIT], 'status': block['status'],
            'prediction': copy.deepcopy(block['prediction']), 'if_different': block['if_different'][:TEXT_LIMIT]}


def build_request(observation, evidence_view, arm, previous=None, *, model='scripted', seed=0):
    """One policy request. `observation` comes from the existing pipeline and is not modified. The candidate must be
    given its carried state explicitly (`carried_statement`); the baseline never carries any."""
    if arm not in ARMS:
        raise ValueError('arm')
    if (arm == 'candidate') != (previous is not None):
        raise ValueError('the candidate needs carried state (possibly unavailable); the baseline takes none')
    payload = copy.deepcopy(observation)
    payload[E.FIELD] = copy.deepcopy(evidence_view)
    legal = payload['legal_actions']
    system = SYSTEM_PROMPT + ('\n' + PROCEDURE if arm == 'candidate' else '')
    user = {'observation': payload}
    if arm == 'candidate':
        user[PREVIOUS_FIELD] = copy.deepcopy(previous)
    return {'model': model, 'seed': seed, 'temperature': 0,
            'max_tokens': CANDIDATE_MAX_TOKENS if arm == 'candidate' else BASELINE_MAX_TOKENS,
            'messages': [{'role': 'system', 'content': system},
                         {'role': 'user', 'content': json.dumps(user, sort_keys=True, separators=(',', ':'))}],
            'chat_template_kwargs': {'enable_thinking': False},
            'response_format': candidate_response_format(legal) if arm == 'candidate' else response_format(legal)}


def strip_procedure(request):
    """The candidate request with the treatment removed; must equal the baseline request exactly."""
    value = copy.deepcopy(request)
    user = json.loads(value['messages'][1]['content'])
    user.pop(PREVIOUS_FIELD, None)
    value['messages'][1]['content'] = json.dumps(user, sort_keys=True, separators=(',', ':'))
    legal = user['observation']['legal_actions']
    value['messages'][0]['content'] = SYSTEM_PROMPT
    value['max_tokens'] = BASELINE_MAX_TOKENS
    value['response_format'] = response_format(legal)
    return value


def size(request):
    """Character counts of what the model reads. Token counts need the model tokenizer and are not estimated."""
    return {'system_chars': len(request['messages'][0]['content']), 'user_chars': len(request['messages'][1]['content']),
            'schema_chars': len(json.dumps(request['response_format'], sort_keys=True, separators=(',', ':')))}


def procedure_problems(block):
    """Structural check of a hypothesis_test block (the adapter's own; the evaluator checks independently)."""
    if not isinstance(block, dict) or set(block) != set(HYPOTHESIS_TEST['required']):
        return ['hypothesis_test must have exactly the required fields']
    problems = []
    for name in ('hypothesis', 'if_different'):
        if not isinstance(block[name], str) or not block[name].strip() or len(block[name]) > TEXT_LIMIT:
            problems.append(f'{name}: a non-empty string of at most {TEXT_LIMIT} characters')
    if block['status'] not in STATUSES:
        problems.append('status outside the vocabulary')
    for name in ('supporting', 'conflicting'):
        cites = block[name]
        if not isinstance(cites, list) or len(cites) > CITATION_LIMIT:
            problems.append(f'{name}: a list of at most {CITATION_LIMIT} citations')
            continue
        for cite in cites:
            if (not isinstance(cite, dict) or set(cite) != {'ref', 'claim'} or not isinstance(cite['ref'], str)
                    or not cite['ref'][1:].isdigit() or cite['ref'][:1] != 'T' or cite['claim'] not in CLAIMS):
                problems.append(f'{name}: malformed citation')
    p = block['prediction']
    if not isinstance(p, dict) or set(p) != {'visual_effect', 'level_completed', 'changed_region_xyxy'}:
        problems.append('prediction must have exactly visual_effect, level_completed, changed_region_xyxy')
    else:
        if p['visual_effect'] not in VISUAL_PREDICTIONS:
            problems.append('prediction.visual_effect outside the vocabulary')
        if type(p['level_completed']) is not bool:
            problems.append('prediction.level_completed must be a boolean')
        r = p['changed_region_xyxy']
        if r is not None and (not isinstance(r, list) or len(r) != 4 or
                              any(type(v) is not int or not 0 <= v <= 63 for v in r)):
            problems.append('prediction.changed_region_xyxy must be null or four integers 0..63')
    return problems


def parse(response, legal, arm):
    """A decision record from a model response {'content', 'finish_reason', ...}. Never raises on model output."""
    decision = {'arm': arm, 'action': None, 'action_error': None, 'procedure': None, 'procedure_error': None,
                'finish_reason': response.get('finish_reason')}
    content = response.get('content')
    if response.get('finish_reason') == 'length':
        decision['action_error'] = 'truncated: completion budget exhausted'
        if arm == 'candidate':
            decision['procedure_error'] = decision['action_error']
        return decision
    try:
        value = json.loads(content)
    except (TypeError, ValueError):
        decision['action_error'] = 'not JSON'
        if arm == 'candidate':
            decision['procedure_error'] = 'not JSON'
        return decision
    expected = {'action'} if arm == 'baseline' else {'hypothesis_test', 'action'}
    if not isinstance(value, dict) or set(value) - expected:
        decision['action_error'] = 'unexpected top-level fields'
    else:
        try:
            decision['action'] = validate_action(json.dumps({'action': value.get('action')}), legal)['action']
        except ValueError as exc:
            decision['action_error'] = str(exc)
    if arm == 'candidate':
        block = value.get('hypothesis_test') if isinstance(value, dict) else None
        problems = procedure_problems(block)
        if problems:
            decision['procedure_error'] = '; '.join(problems)
        else:
            decision['procedure'] = copy.deepcopy(block)
    return decision


def decide(model, observation, evidence_view, arm, previous=None):
    """One policy call. `model(request)` returns {'content', 'finish_reason', 'completion_tokens'}."""
    request = build_request(observation, evidence_view, arm, previous)
    response = model(request)
    return request, response, parse(response, observation['legal_actions'], arm)
