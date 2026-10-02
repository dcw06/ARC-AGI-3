"""Hand-written glue between the derived runner and the supervision layer (Track 3; not derived).

- `suggestion_payload`: the clearly labelled model-generated suggestion block the policy request carries beside,
  never inside, the factual observation. Identical form in the periodic and triggered arms; never in continuation.
- `reflection_request`: the chat request that carries an intervention.PROMPT text to the model service.
- `raw_transition`: a runner step as transition_evidence raw input (the same mapping as
  scripts/replay_transition_evidence_v1.py `raw_step`; tested equal).
- `supervisor_view`: the retained supervision state of one episode.
"""
import copy

from research.stagnation_supervision_v1 import supervision as SV

SUGGESTION_FIELD = 'model_generated_suggestion'
SUGGESTION_KEYS = ('label', 'text', 'issued_after_action', 'expires_after_action')
REFLECTION_MAX_TOKENS = 400
REFLECTION_SYSTEM = ('You review an agent\'s recent actions from the evidence supplied. Answer with exactly one JSON '
                     'object in the requested shape and nothing else.')
SOURCE = 'offline_development_engine'


def suggestion_payload(suggestion):
    """The block shown to the policy: exactly the label, the validated rendered text and its lifetime."""
    if set(SUGGESTION_KEYS) - set(suggestion):
        raise ValueError('suggestion block fields')
    block = {k: copy.deepcopy(suggestion[k]) for k in SUGGESTION_KEYS}
    if block['label'] != SV.SUGGESTION_LABEL or not isinstance(block['text'], str):
        raise ValueError('suggestion block label or text')
    if len(block['text']) > SV.POLICY['max_suggestion_chars']:
        raise ValueError('suggestion block longer than its limit')
    return block


def reflection_request(text, *, model='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8', seed=0):
    return {'model': model, 'messages': [{'role': 'system', 'content': REFLECTION_SYSTEM},
                                         {'role': 'user', 'content': text}],
            'temperature': 0, 'seed': seed, 'max_tokens': REFLECTION_MAX_TOKENS,
            'chat_template_kwargs': {'enable_thinking': False}}


def raw_transition(episode_id, step):
    status = step['status']
    outcome = ({'status': 'acknowledged', 'after': step['after']} if status == 'acknowledged' else
               {'status': 'failed' if status == 'dispatch_failed' else 'outcome_unknown',
                'reason': step.get('error') or step.get('reason') or status})
    return {'identity': {'episode_id': episode_id, 'action_index': step['index']}, 'before': step['before'],
            'proposal': None, 'dispatched': step['action'], 'outcome': outcome, 'environment_source': SOURCE}


def supervisor_view(supervisor):
    return {'arm': supervisor.arm, 'policy': supervisor.policy, 'events': supervisor.events,
            'summary': supervisor.summary(),
            'suggestion': None if supervisor.suggestion is None else dict(supervisor.suggestion)}


EXPERIMENT_POLICY = {**SV.POLICY, 'period_actions': 10}  # P = 40 actions / cap 4 (protocol v2)


def session_spec(spec, session):
    """The protocol restricted to one session's game groups (two sessions, one per block)."""
    keep = set(spec['sessions'][str(session)])
    return {**spec, 'schedule': [s for s in spec['schedule'] if s['pair_id'] in keep]}


def session_run_spec(session, mode):
    """The worker's run spec for one session. Rehearsal only: SSV_REHEARSAL_GROUPS (comma-separated group ids) and
    SSV_REHEARSAL_ACTIONS may shorten the CPU rehearsal; live mode ignores both."""
    import os
    from research.stagnation_supervision_v1.closed_loop.runner import protocol
    spec = session_spec(protocol(), session)
    if mode == 'rehearsal':
        groups = os.environ.get('SSV_REHEARSAL_GROUPS')
        if groups:
            keep = set(groups.split(','))
            spec = {**spec, 'schedule': [s for s in spec['schedule'] if s['pair_id'] in keep]}
        actions = os.environ.get('SSV_REHEARSAL_ACTIONS')
        if actions:
            spec = {**spec, 'limits': {**spec['limits'], 'actions_per_episode': int(actions)}}
    elif mode != 'live':
        raise ValueError('mode')
    return spec


def worker_token_counter(mode):
    """Exact reflection admission in the game interpreter. Rehearsal: the fixture tokenizer the rehearsal model host
    also counts with. Live: not available in this source revision; the shared bridge has no count operation, so the
    pinned tokenizer would have to be loaded in the game interpreter (to be decided before a package lock)."""
    if mode == 'rehearsal':
        return fixture_token_counter()
    raise NotImplementedError('live reflection admission needs the pinned tokenizer in the game interpreter')


def chat_token_counter(tokenizer):
    """Exact prompt tokens of the reflection chat request built from `text`, with the same chat-template call the
    model service uses for admission (action-effect-history v1 `_admit`)."""
    def count(text):
        request = reflection_request(text)
        tokens = tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                               truncation=False, **request['chat_template_kwargs'])
        if type(tokens) is not list or not tokens:
            raise ValueError('tokenizer returned no tokens')
        return len(tokens)
    return count


def fixture_token_counter():
    """Rehearsal only: the fixture tokenizer the fake server also counts with, so admission equals the charge."""
    from research.action_effect_history_v1.rehearsal import FixtureTokenizer
    return chat_token_counter(FixtureTokenizer())


def supervision_factory(spec, trigger_spec, policy=EXPERIMENT_POLICY, clock=None, *, token_counter):
    """`factory(arm, call)` for the runner: the frozen detector observes in every arm; reflection only in its two
    arms. Reflection admission always uses an exact `token_counter` here (never the character estimate)."""
    import time
    if token_counter is None:
        raise ValueError('the closed loop requires an exact reflection token counter')

    def factory(arm, call):
        return SV.Supervisor(arm, trigger_spec, call, policy, clock=clock or time.perf_counter,
                             episode_actions=spec['limits']['actions_per_episode'], token_counter=token_counter)
    return factory
