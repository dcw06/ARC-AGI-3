"""Supervision policy, CPU rehearsal and escape metrics (Track 3, stagnation_supervision_v1).

Three arms share one policy and one request template (intervention.py):
  continuation  never calls; the detector still runs as an observer, so loops are measured in every arm;
  periodic      due after every `period_actions`-th action;
  triggered     due when the frozen detector fires.
Policy limits apply to every call in every arm:
  - cooldown: no call within `cooldown_actions` actions of the previous call;
  - at most `max_interventions_per_episode` calls, counting valid, invalid and failed calls alike;
  - a per-episode token ceiling: a call is made only if spent + input + reserved output fits. The input count is
    exact when a `token_counter` is supplied (the closed loop always supplies the serving tokenizer's chat-template
    count); the 4-characters-per-token estimate remains only for synthetic rehearsals without one;
  - no call when the current state was not observed (unknown outcome or missing frames): it is deferred;
  - no call when fewer than `min_remaining_actions` actions (the recovery window) remain in actual play, so every
    reflection can be evaluated. Remaining actions come from the caller when it knows play has ended (the runner
    passes 0 after a terminal state or a stopping dispatch failure), otherwise from the episode length;
  - no call at a terminal state (play has ended: there is no recovery window), and none at a reset or level change
    (the detector's evidence belongs to the segment that just ended). The transition and the detector output are
    still recorded.
Delivery (identical in both reflection arms): a valid reflection becomes a clearly labelled model-generated suggestion
block, kept apart from the factual observation, shown with the next `suggestion_lifetime_actions` policy requests,
at most `max_suggestion_chars` long, replaced only by a later valid reflection, and cleared at a reset, a level
change or a terminal state. An invalid or failed reflection delivers nothing.
Completion semantics: when the service reports a completion status (`finish_reason`, as the runner always does), a
reflection is valid only if it is exactly 'stop'. 'length', a missing (None) or any other value makes it an invalid
reflection: charged, its raw output retained, no new suggestion delivered; an existing suggestion keeps its lifetime.
Every call is charged, including invalid outputs and exceptions. Every decision is retained as an event with its
reason, including suppressed and deferred ones. Records are transition_evidence_v2, unmasked (the masked view is
never requested or read); the detector consumes the v1 fields they contain, and events cite evidence by record_id. Here `call` is scripted; nothing in this module runs a model.
"""
import math
import time

from research.stagnation_supervision_v1 import detector as D, intervention as I
from research.transition_evidence_v2 import transition as T, vocabulary as V

VERSION = 'stagnation_supervision_v1_policy'
ARMS = ('continuation', 'periodic', 'triggered')
POLICY = {'cooldown_actions': 6, 'period_actions': 6, 'max_interventions_per_episode': 4,
          'max_supervisor_tokens_per_episode': 8000, 'reserved_output_tokens': 400,
          'min_remaining_actions': 10, 'suggestion_lifetime_actions': 10, 'max_suggestion_chars': 1600}
SUGGESTION_LABEL = 'MODEL-GENERATED SUGGESTION (a hypothesis from a reviewer model, not an observation)'
CLEARING_EVENTS = (V.RESET_ACKNOWLEDGED, V.LEVEL_COMPLETED, V.LEVEL_COUNT_DECREASED, V.TERMINAL_STATE)
BOUNDARY_EVENTS = (V.RESET_ACKNOWLEDGED, V.LEVEL_COMPLETED, V.LEVEL_COUNT_DECREASED)


def estimate_tokens(text):
    """A declared approximation (4 characters per token) used for admission only; a live run must use the
    serving tokenizer's counts for charging."""
    return math.ceil(len(text) / 4)


class Supervisor:
    def __init__(self, arm, spec, call, policy=POLICY, available_actions=None, clock=time.perf_counter,
                 episode_actions=None, token_counter=None):
        if arm not in ARMS:
            raise ValueError('unknown arm')
        self.arm, self.params, self.call, self.policy = arm, spec['params'], call, dict(policy)
        self.available_actions, self.clock = available_actions, clock
        self.raws, self.records, self.events = [], [], []
        self.stats = D.Statistics()
        self.calls, self.tokens, self.last_call = 0, 0, None
        self.policy = {**POLICY, **self.policy}
        self.episode_actions, self.suggestion = episode_actions, None
        self.token_counter = token_counter

    def observe(self, raw, prediction=None, remaining_actions=None):
        self.raws.append(raw)
        record = self._next_record(raw)
        self.records.append(record)
        index = record['identity']['action_index']
        fired = D.signals(self.stats.update(record, prediction), self.params)
        due = {'continuation': False, 'periodic': (index + 1) % self.policy['period_actions'] == 0,
               'triggered': bool(fired)}[self.arm]
        ids = {r['identity']['action_index']: r['identity']['record_id'] for r in self.records}
        event = {'action_index': index, 'record_id': record['identity']['record_id'], 'arm': self.arm,
                 'detector_signals': fired, 'due': due,
                 'detector_evidence_record_ids': sorted({ids[i] for s in fired for i in s['evidence']})}
        cleared = [e for e in record['environment']['events'] if e in CLEARING_EVENTS]
        if cleared and self.suggestion is not None:
            event['suggestion_cleared'] = cleared
            self.suggestion = None
        events = record['environment']['events']
        terminal = V.TERMINAL_STATE in events
        if terminal:
            remaining = 0  # play has ended, whatever the nominal horizon says
        elif remaining_actions is not None:
            remaining = remaining_actions
        else:
            remaining = None if self.episode_actions is None else self.episode_actions - (index + 1)
        event['remaining_actions'] = remaining
        if not due:
            event['outcome'] = 'not_due'
        elif terminal:
            event['outcome'] = 'suppressed_terminal_state'
        elif any(e in BOUNDARY_EVENTS for e in events):
            event['outcome'] = 'suppressed_segment_boundary'
        elif remaining is not None and remaining < self.policy['min_remaining_actions']:
            event['outcome'] = 'suppressed_insufficient_remaining_actions'
        elif I.unobserved_state(record):
            event['outcome'] = 'deferred_unobserved_state'
        elif self.last_call is not None and index - self.last_call < self.policy['cooldown_actions']:
            event['outcome'] = 'suppressed_cooldown'
        elif self.calls >= self.policy['max_interventions_per_episode']:
            event['outcome'] = 'suppressed_intervention_cap'
        else:
            request = I.build_request(self.records, index, self.arm, fired, self.available_actions)
            prompt_tokens = self._input_tokens(request['text'])
            event['admission'] = {'input_tokens': prompt_tokens,
                                  'counter': 'tokenizer' if self.token_counter else 'estimate_4_chars_per_token',
                                  'reserved_output_tokens': self.policy['reserved_output_tokens'],
                                  'spent_before': self.tokens}
            needed = prompt_tokens + self.policy['reserved_output_tokens']
            if self.tokens + needed > self.policy['max_supervisor_tokens_per_episode']:
                event['outcome'] = 'suppressed_token_budget'
            else:
                event['outcome'] = 'called'
                event['call'] = self._call(request)
                event['delivered'] = (I.render(event['call']['parsed']['intervention'])
                                      if event['call']['parsed']['valid'] else None)
                if event['delivered'] is not None and len(event['delivered']) > self.policy['max_suggestion_chars']:
                    event['call']['parsed']['problems'].append('rendered suggestion longer than the block limit')
                    event['call']['parsed']['valid'] = False
                    event['delivered'] = None
                if event['delivered'] is not None:
                    self.suggestion = {'label': SUGGESTION_LABEL, 'text': event['delivered'],
                                       'issued_after_action': index,
                                       'expires_after_action': index + self.policy['suggestion_lifetime_actions'],
                                       'record_id': record['identity']['record_id']}
        self.events.append(event)
        return event

    def _next_record(self, raw):
        """The record `transition.history(self.raws)[-1]` would give, in constant time: continuity depends only on
        the previous transition, and the segment number only on the previous record's segment and events."""
        if len(self.raws) == 1:
            return T.history([raw])[0]
        pair = T.history([self.raws[-2], raw])
        pair[1]['segment'] = self.records[-1]['segment'] + pair[1]['segment']
        return pair[1]

    def suggestion_for(self, action_index):
        """The suggestion block to show with the policy request for `action_index`, or None (expired or cleared)."""
        s = self.suggestion
        if s is None or not s['issued_after_action'] < action_index <= s['expires_after_action']:
            return None
        return dict(s)

    def _input_tokens(self, text):
        return self.token_counter(text) if self.token_counter is not None else estimate_tokens(text)

    def _call(self, request):
        self.calls += 1
        self.last_call = request['content']['decision_index']
        start = self.clock()
        try:
            response = self.call(request['text'])
            error = None
        except Exception as exc:  # retained and charged, never retried here
            response, error = {}, f'{type(exc).__name__}: {exc}'
        latency = response.get('latency_s', self.clock() - start)
        text = response.get('text')
        # counted only when the service did not report it (dict.get would evaluate the count eagerly)
        charged_in = response['input_tokens'] if 'input_tokens' in response else self._input_tokens(request['text'])
        charged_out = response.get('output_tokens', estimate_tokens(text) if isinstance(text, str) else 0)
        self.tokens += charged_in + charged_out
        finish = response.get('finish_reason', 'stop') if 'finish_reason' in response else None
        if error is not None:
            parsed = {'valid': False, 'problems': ['call failed: ' + error], 'intervention': None, 'raw': None}
        elif 'finish_reason' in response and finish != 'stop':
            parsed = {'valid': False, 'problems': [f'reflection did not finish with stop: {finish!r}'],
                      'intervention': None, 'raw': text}
        else:
            parsed = I.parse(text, request)
        return {'request_sha256': request['sha256'], 'request_text': request['text'], 'error': error,
                'finish_reason': finish,
                'available_actions_field': request['available_actions_field'],
                'raw_output': text, 'parsed': parsed, 'input_tokens': charged_in, 'output_tokens': charged_out,
                'latency_s': latency}

    def summary(self):
        calls = [e['call'] for e in self.events if e['outcome'] == 'called']
        outcomes = {}
        for e in self.events:
            outcomes[e['outcome']] = outcomes.get(e['outcome'], 0) + 1
        return {'arm': self.arm, 'actions': len(self.events), 'outcomes': outcomes, 'calls': len(calls),
                'valid_calls': sum(c['parsed']['valid'] for c in calls),
                'invalid_outputs': sum(c['error'] is None and not c['parsed']['valid'] for c in calls),
                'failed_calls': sum(c['error'] is not None for c in calls),
                'tokens_charged': self.tokens, 'latency_s': sum(c['latency_s'] for c in calls),
                'detector_firings': sum(bool(e['detector_signals']) for e in self.events)}


def scripted(outputs):
    """A scripted supervisor: each item is a response dict or an exception to raise. Running out raises."""
    queue = list(outputs)

    def call(_text):
        if not queue:
            raise RuntimeError('scripted outputs exhausted')
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    return call


def rehearse(raws, arm, spec, outputs, policy=POLICY, predictions=None, available_actions=None):
    by_index = {p['action_index']: p for p in predictions or ()}
    supervisor = Supervisor(arm, spec, scripted(outputs), policy, available_actions, clock=lambda: 0.0)
    for raw in raws:
        supervisor.observe(raw, by_index.get(raw['identity']['action_index']))
    return supervisor


def escapes(events, records):
    """For each attempted intervention at step t: actions until the agent first takes a (state, action) pair it has
    not tried in this segment (leaving the loop), and what came next: 'progress' (a confirmed progress signal
    before the detector fires again after leaving), 'another_detected_loop' (escaping into another loop is not
    success), 'no_progress_before_end', or 'did_not_leave'."""
    out = []
    stats = D.Statistics()
    new_pair = {}
    for record in records:
        s = stats.update(record)
        new_pair[record['identity']['action_index']] = s['evidence_step'] and len(s['state_action_recurrence']) == 1
    firing = {e['action_index'] for e in events if e['detector_signals']}
    for e in events:
        if e['outcome'] != 'called':
            continue
        t = e['action_index']
        later = [r['identity']['action_index'] for r in records if r['identity']['action_index'] > t]
        left = next((i for i in later if new_pair[i]), None)
        result = 'did_not_leave' if left is None else 'no_progress_before_end'
        if left is not None:
            for r in records:
                i = r['identity']['action_index']
                if i < left:
                    continue
                if r['progress']['status'] == V.CONFIRMED:
                    result = 'progress'
                    break
                if i in firing:
                    result = 'another_detected_loop'
                    break
        out.append({'intervention_at': t, 'actions_to_leave': None if left is None else left - t, 'result': result})
    return out
