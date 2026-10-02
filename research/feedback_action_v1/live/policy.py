"""Live decision policy for the derived runner (hand-written; the only experiment-specific runtime code).

The observation comes from the existing pipeline exactly as action-effect history v1 built it
(`research.action_effect_history_v1.contract.observation_payload`, reused unchanged). The evidence view, carried
statement, request construction and parsing are the feedback-action v1 adapter (`research/feedback_action_v1/
adapter.py`, `evidence.py`), unchanged. Transitions are retained in the transition_evidence_v2 raw format and built
with its default arguments; candidate statements become v2 model-statement records.

Nothing here starts a model, a GPU or a game.
"""
import copy
import json

from research.feedback_action_v1 import adapter as AD, evidence as E
from research.transition_evidence_v2 import transition as T

SOURCE = 'offline_development_engine'
EVIDENCE_KEYS = set(E.DESCRIPTION) | {'current_state', 'omitted_entries', 'entries'}
ENTRY_KEYS = {'ref', 'action_id', 'action_data', 'dispatch', 'from_state', 'returned_frames', 'valid_returned_frames',
              'visual_effect', 'final_frame_changed_cells', 'to_state', 'events', 'progress', 'continuity'}
STATEMENT_KEYS = {'record', 'available', 'statement_status', 'note', 'about', 'hypothesis', 'status', 'prediction',
                  'if_different'}
SETTINGS = {'model', 'messages', 'temperature', 'seed', 'max_tokens', 'chat_template_kwargs', 'response_format'}


def session_spec(block):
    """The runner spec for one session: the protocol with only that block's pairs (one block per session)."""
    from research.feedback_action_v1.live.runner import protocol
    spec = protocol()
    if str(block) not in spec['sessions']:
        raise ValueError('session')
    spec['schedule'] = [p for p in spec['schedule'] if p['block'] == spec['sessions'][str(block)]['block']]
    return spec


def observation_payload(runtime):
    from research.action_effect_history_v1.contract import observation_payload as reviewed
    return reviewed(runtime)


def observed(packed):
    """The v2 raw observation from a packed engine observation (the runner's frozen `pack`)."""
    return {'frames': copy.deepcopy(packed['frames']), 'levels_completed': packed['levels_completed'],
            'state': packed['state'], 'full_reset': packed['full_reset'],
            'available_actions': list(packed['available_actions'])}


def raw_transition(episode_id, action_index, before, action, outcome):
    """One transition in the transition_evidence_v2 raw format, from the runner's step and outcome records."""
    if outcome['status'] == 'acknowledged':
        result = {'status': 'acknowledged', 'after': observed(outcome['post'])}
    elif outcome['status'] == 'dispatch_failed':
        result = {'status': 'failed', 'reason': outcome['error']}
    else:
        result = {'status': 'outcome_unknown', 'reason': outcome['reason']}
    return {'identity': {'episode_id': episode_id, 'action_index': action_index}, 'before': observed(before),
            'proposal': copy.deepcopy(action), 'dispatched': copy.deepcopy(action), 'outcome': result,
            'environment_source': SOURCE}


def arm_of(request):
    system = request['messages'][0]['content']
    if system == AD.SYSTEM_PROMPT:
        return 'baseline'
    if system == AD.SYSTEM_PROMPT + '\n' + AD.PROCEDURE:
        return 'candidate'
    raise ValueError('frozen prompt')


def parse_action(raw, legal, request):
    """The runner's parse: the adapter's, for the request's arm (the frozen validator checks the action)."""
    decision = AD.parse({'content': raw, 'finish_reason': 'stop'}, sorted(legal), arm_of(request))
    if decision['action'] is None:
        raise ValueError(decision['action_error'])
    return decision['action']


def validate_policy_request(request):
    """Exact request contract for both arms; raises ValueError before any transport. Returns the arm."""
    from research.feedback_action_v1.live.service import MODEL_ID, MAX_REQUEST_BYTES, BASELINE_FIELDS
    if (type(request) is not dict or set(request) != SETTINGS or request['model'] != MODEL_ID
            or request['temperature'] != 0 or request['seed'] != 0
            or request['chat_template_kwargs'] != {'enable_thinking': False}):
        raise ValueError('frozen model settings')
    messages = request['messages']
    if (type(messages) is not list or len(messages) != 2 or set(messages[0]) != {'role', 'content'}
            or messages[0]['role'] != 'system' or messages[1].get('role') != 'user'
            or set(messages[1]) != {'role', 'content'}):
        raise ValueError('frozen prompt')
    arm = arm_of(request)
    if request['max_tokens'] != (AD.CANDIDATE_MAX_TOKENS if arm == 'candidate' else AD.BASELINE_MAX_TOKENS):
        raise ValueError('completion cap')
    payload = json.loads(messages[1]['content'])
    if set(payload) != ({'observation', AD.PREVIOUS_FIELD} if arm == 'candidate' else {'observation'}):
        raise ValueError('payload envelope')
    observation = payload['observation']
    if set(observation) != BASELINE_FIELDS | {E.FIELD}:
        raise ValueError('observation fields')
    view = observation[E.FIELD]
    if (set(view) != EVIDENCE_KEYS or type(view['entries']) is not list or len(view['entries']) > E.WINDOW
            or any(set(entry) != ENTRY_KEYS for entry in view['entries'])
            or {k: view[k] for k in E.DESCRIPTION} != E.DESCRIPTION):
        raise ValueError('evidence view shape')
    if arm == 'candidate':
        statement = payload[AD.PREVIOUS_FIELD]
        if not isinstance(statement, dict) or statement.get('record') != 'model_statement':
            raise ValueError('carried statement')
        if statement.get('available') is True:
            if set(statement) != STATEMENT_KEYS or AD.procedure_problems(
                    {k: statement[k] for k in ('hypothesis', 'status', 'prediction', 'if_different')}
                    | {'supporting': [], 'conflicting': []}):
                raise ValueError('carried statement shape')
        elif set(statement) != {'record', 'available', 'reason'} or statement['available'] is not False:
            raise ValueError('carried statement shape')
        expected_format = AD.candidate_response_format(observation['legal_actions'])
    else:
        from certification.phase4_transient_v2.action_contract import response_format
        expected_format = response_format(observation['legal_actions'])
    if request['response_format'] != expected_format:
        raise ValueError('legal-action schema')
    if len(json.dumps(request, separators=(',', ':')).encode()) > MAX_REQUEST_BYTES:
        raise ValueError('request byte ceiling')
    if arm == 'candidate' and validate_policy_request(AD.strip_procedure(request)) != 'baseline':
        raise ValueError('treatment isolation')
    return arm


def trajectory(episode):
    """A runner episode in the independent evaluator's trajectory format, from retained bytes only: each call's
    request and response, and each step's raw transition. Every call is a decision (invalid ones included)."""
    raws = [s['raw_transition'] for s in episode['steps'] if 'raw_transition' in s]
    by_call = {s['call_index']: n for n, s in enumerate(s for s in episode['steps'] if 'raw_transition' in s)}
    steps = []
    for index, call in enumerate(episode['calls']):
        if call.get('status') not in ('valid', 'invalid_output'):
            raise ValueError('a call without a retained response cannot be evaluated: ' + str(call.get('status')))
        user = json.loads(call['request']['messages'][1]['content'])
        observation = user['observation']
        steps.append({'raws_before': sum(1 for c in by_call if c < index), 'legal_actions': observation['legal_actions'],
                      'current_frame': observation['current_grid'], 'request_user_content': call['request']['messages'][1]['content'],
                      'response': {'content': call['response'], 'finish_reason': call['finish_reason'],
                                   'completion_tokens': call['server_completion_tokens']},
                      'prompt_chars': len(call['request']['messages'][0]['content']) + len(call['request']['messages'][1]['content']),
                      'dispatched_index': by_call.get(index)})
    return {'arm': episode['arm'], 'environment': episode['game_id'], 'raws': raws, 'steps': steps,
            'stop_reason': episode['stop_reason']}


class EpisodePolicy:
    """Per episode and arm: the raw transitions so far, the carried statement and the model-statement records."""

    def __init__(self, arm, episode_id, *, seed=0):
        if arm not in AD.ARMS:
            raise ValueError('arm')
        self.arm, self.episode_id, self.seed = arm, episode_id, seed
        self.raws, self.statements = [], []
        self.previous = None  # (adapter decision, events of its transition or None, its ref or None)
        self.decision, self.legal = None, None

    def request(self, runtime, obs):
        from research.feedback_action_v1.live.service import MODEL_ID
        observation = observation_payload(runtime)
        self.legal = list(observation['legal_actions'])
        carried = AD.carried_statement(*(self.previous or (None,))) if self.arm == 'candidate' else None
        view = E.view(self.raws, obs.frames[-1].tolist())
        return AD.build_request(observation, view, self.arm, carried, model=MODEL_ID, seed=self.seed)

    def decided(self, call_row, obs):
        """Record the adapter's decision for the call just made (from the retained response bytes)."""
        self.decision = AD.parse({'content': call_row.get('response'), 'finish_reason': call_row.get('finish_reason')},
                                 self.legal, self.arm)
        if self.decision['action'] is None:
            self.previous = (self.decision, None, None)  # nothing dispatched; its block (if valid) is about nothing
        return self.decision

    def dispatched(self, raw):
        self.raws.append(raw)
        record = T.build(raw)
        events, ref = record['environment']['events'], f"T{raw['identity']['action_index']}"
        if self.decision['procedure'] is not None:
            self.statements.append(T.model_statement(raw['identity'], 'hypothesis_test', self.decision['procedure'],
                                                     'candidate_policy'))
        self.previous = (self.decision, events, ref)
        return record
