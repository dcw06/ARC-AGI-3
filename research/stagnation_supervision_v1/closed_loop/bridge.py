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


def supervision_factory(spec, trigger_spec, policy=EXPERIMENT_POLICY, clock=None):
    """`factory(arm, call)` for the runner: the frozen detector observes in every arm; reflection only in its two
    arms."""
    import time

    def factory(arm, call):
        return SV.Supervisor(arm, trigger_spec, call, policy, clock=clock or time.perf_counter,
                             episode_actions=spec['limits']['actions_per_episode'])
    return factory
