"""Derive the GPU-disabled stagnation-supervision closed-loop runner from action-effect-history v1's reviewed files.

Sources: research/action_effect_history_v1/{runner,contract,engine,evidence}.py, each bound by action-effect-history
v1's review lock (notebooks/action-effect-history-v1-review-r3/review-source-lock.json) and run live as attempt
aeh1-4c75150a. They are reused, not edited. Each derived file is its source with the global renames below and that
file's own substitutions, each required to match an exact number of times.

Hand-written (not derived): research/stagnation_supervision_v1/closed_loop/{bridge,service,fake_server,authority}.py
and protocol.json. Not yet derived (needed before an exact package lock): host, worker, supervisor, monitor,
resources, launch, package and review scripts.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = 'research/stagnation_supervision_v1/closed_loop/'
SOURCE_DIR = 'research/action_effect_history_v1/'
BANNER = '# Derived from {source} by scripts/derive_stagnation_supervision_v1.py; edit the derivation, not this file.\n'
GLOBAL = (('research.action_effect_history_v1', 'research.stagnation_supervision_v1.closed_loop'),
          ('action_effect_history_run_v1', 'stagnation_supervision_run_v1'),
          ('action_effect_history_evidence_v1', 'stagnation_supervision_evidence_v1'),
          ('action-effect-history-v1', 'stagnation-supervision-v1'),
          ('action_effect_history_v1', 'stagnation_supervision_v1'))

CONTRACT_DOC_OLD = '''"""Common corrected baseline and the action-effect-history candidate (request construction only).

This is a new baseline: not unchanged E1S-R and not a continuation of R8. Both arms use the same
system prompt, observation payload, response schema and decoding settings. The history arm's
observation carries exactly one extra field, `action_effect_history`, computed by a deterministic
frame-comparison tool from already-observed dispatches only.
"""'''
CONTRACT_DOC_NEW = '''"""Policy requests for the three stagnation-supervision arms (request construction only).

Action-effect-history v1's common baseline request (system prompt, observation payload, response schema and
decoding settings) is used unchanged in every arm, except for one sentence added to the shared system prompt that
describes the suggestion block. The periodic and triggered arms may carry exactly one extra top-level field,
`model_generated_suggestion`, beside (never inside) the factual observation; continuation never does. The history
helpers below are retained, unused, from the source.
"""'''
POLICY_OLD = '''def policy_request(runtime, arm, history=None, *, model='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8', seed=0):
    if arm not in ('baseline', 'history'):
        raise ValueError('arm')
    observation = observation_payload(runtime)
    if arm == 'history':
        observation[HISTORY_FIELD] = history_field(history)
    return build_request(observation, model=model, seed=seed)
'''
POLICY_NEW = '''def policy_request(runtime, arm, suggestion=None, *, model='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8', seed=0):
    if arm not in ('continuation', 'periodic', 'triggered'):
        raise ValueError('arm')
    if suggestion is not None and arm == 'continuation':
        raise ValueError('the continuation arm never carries a suggestion')
    observation = observation_payload(runtime)
    return build_request(observation, model=model, seed=seed, suggestion=suggestion)
'''
BUILD_OLD = '''def build_request(observation, *, model='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8', seed=0):
    from certification.phase4_transient_v2.action_contract import response_format
    legal = observation['legal_actions']
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': json.dumps({'observation': observation}, sort_keys=True, separators=(',', ':'))}]
'''
BUILD_NEW = '''def build_request(observation, *, model='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8', seed=0, suggestion=None):
    from certification.phase4_transient_v2.action_contract import response_format
    legal = observation['legal_actions']
    payload = {'observation': observation}
    if suggestion is not None:  # a labelled model-generated block beside the factual observation
        payload[SUGGESTION_FIELD] = suggestion_payload(suggestion)
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': json.dumps(payload, sort_keys=True, separators=(',', ':'))}]
'''
STRIP_OLD = '''def strip_history(request):
    """The request with the history field removed; must equal the baseline request exactly."""
    value = copy.deepcopy(request)
    payload = json.loads(value['messages'][1]['content'])
    payload['observation'].pop(HISTORY_FIELD, None)
'''
STRIP_NEW = '''def strip_suggestion(request):
    """The request with the suggestion block removed; must equal the continuation request exactly."""
    value = copy.deepcopy(request)
    payload = json.loads(value['messages'][1]['content'])
    payload.pop(SUGGESTION_FIELD, None)
'''

RUNNER_DOC_OLD = '''"""Two-block action-effect-history comparison runner (CPU-rehearsable; no launch authority here).

Evidence discipline follows Stage B: intent is durable before every call and dispatch, and received
bytes are durable before validation. Differences from Stage B: twelve isolated episodes, per-episode
stop reasons, pair admission against a frozen allowance, a run deadline enforced even mid-pair, and
accounting for every attempted episode.
"""'''
RUNNER_DOC_NEW = '''"""Stagnation-supervision comparison runner (CPU-rehearsable; GPU-disabled; no launch authority here).

Evidence discipline follows action-effect-history v1: intent is durable before every call and dispatch, and
received bytes are durable before validation. Differences: one game group runs the arms in its frozen order;
episodes follow the frozen protocol's length; the frozen detector observes every step in every arm through the
supervision layer; reflection calls go through the same service with intent durable before the call, are charged
and audited like policy calls; and a labelled model-generated suggestion block may accompany policy requests in
the reflection arms only.
"""'''
REFLECT_ANCHOR = '''        row['status'] = 'valid'
        persist(episode)
        return action
'''
REFLECT_NEW = REFLECT_ANCHOR + '''
    def reflect(episode, text):
        """One reflection call: intent durable before the call and received bytes before validation; every call is
        charged. Returns the supervisor's response, or raises (the supervisor retains the failure)."""
        check()
        if report['reflection_calls'] >= limits['maximum_reflection_calls']:
            raise TechnicalFailure('reflection call ceiling')
        request = reflection_request(text, seed=limits['request_seed'])
        row = {'request': request, 'request_sha256': digest(request), 'started_at': now(), 'status': 'started'}
        episode['reflections'].append(row)
        report['reflection_calls'] += 1
        persist(episode)
        began = clock()
        try:
            result = service.complete(request)
        except Exception as exc:
            row.update(status='failed', returned_at=now(), error=type(exc).__name__ + ': ' + str(exc)[:200])
            persist(episode)
            raise
        raw = result['content']
        blob = raw.encode() if type(raw) is str else b''
        p, c = result.get('server_prompt_tokens'), result.get('server_completion_tokens')
        row.update(status='received', returned_at=now(),
                   response=blob[:limits['max_response_bytes']].decode('utf-8', errors='replace'),
                   response_bytes=len(blob), response_sha256=hashlib.sha256(blob).hexdigest(),
                   tokenizer_prompt_tokens=result.get('tokenizer_prompt_tokens'), server_prompt_tokens=p,
                   server_completion_tokens=c, finish_reason=result.get('finish_reason'),
                   latency_s=round(clock() - began, 6))
        persist(episode)  # received evidence survives every later check
        if (type(raw) is not str or type(p) is not int or p != row['tokenizer_prompt_tokens']
                or not 0 < p <= limits['live_prompt_token_ceiling'] or type(c) is not int
                or not 0 < c <= request['max_tokens']):
            row['status'] = 'audit_failure'
            persist(episode)
            raise TechnicalFailure('reflection response/token audit')
        report['reflection_prompt_tokens'] += p
        report['reflection_completion_tokens'] += c
        # finish_reason is passed on as reported; the supervisor accepts only 'stop' (anything else is an invalid,
        # charged, retained reflection that delivers nothing)
        return {'text': raw, 'input_tokens': p, 'output_tokens': c, 'latency_s': row['latency_s'],
                'finish_reason': row['finish_reason']}
'''
OBSERVE_ANCHOR = '''                step.update(status=outcome['status'], effect_record=record, history_entry=entry, returned_at=now(),
                            after=outcome.get('post'))
                persist(episode)
'''
OBSERVE_NEW = OBSERVE_ANCHOR + '''                if supervisor is not None:  # the detector observes every step in every arm
                    raws.append(raw_transition(episode_id, step))
                    ended = outcome['status'] != 'acknowledged' or outcome['post']['state'] in ('WIN', 'GAME_OVER')
                    supervisor.observe(raws[-1], remaining_actions=(
                        0 if ended else limits['actions_per_episode'] - (step_index + 1)))  # actual play
                    episode['supervision'] = supervisor_view(supervisor)
                    persist(episode)
                    if any(r['status'] == 'audit_failure' for r in episode['reflections']):
                        raise TechnicalFailure('reflection response/token audit')
                    check()
'''

DERIVED = {
    'contract.py': (
        (CONTRACT_DOC_OLD, CONTRACT_DOC_NEW, 1),
        ('import copy\nimport json\n',
         'import copy\nimport json\n\n'
         'from research.stagnation_supervision_v1.closed_loop.bridge import SUGGESTION_FIELD, suggestion_payload\n', 1),
        ('"reports any older transitions omitted from this prompt."',
         '"reports any older transitions omitted from this prompt. A separate model_generated_suggestion field may "\n'
         '    "appear beside the observation: it is a hypothesis written by another model, not an observation, and it "\n'
         '    "may be wrong."', 1),
        (POLICY_OLD, POLICY_NEW, 1),
        (BUILD_OLD, BUILD_NEW, 1),
        (STRIP_OLD, STRIP_NEW, 1),
    ),
    'runner.py': (
        (RUNNER_DOC_OLD, RUNNER_DOC_NEW, 1),
        ('from research.stagnation_supervision_v1.closed_loop.contract import policy_request\n',
         'from research.stagnation_supervision_v1.closed_loop.contract import policy_request\n'
         'from research.stagnation_supervision_v1.closed_loop.bridge import raw_transition, reflection_request, '
         'supervisor_view\n', 1),
        ('        evidence_lock_root=None):', '        evidence_lock_root=None, supervision_factory=None):', 1),
        ("'pairs': [], 'episodes': [], 'calls': 0, 'dispatches': 0, 'prompt_tokens': 0, 'completion_tokens': 0}",
         "'pairs': [], 'episodes': [], 'calls': 0, 'dispatches': 0, 'prompt_tokens': 0, 'completion_tokens': 0,\n"
         "              'reflection_calls': 0, 'reflection_prompt_tokens': 0, 'reflection_completion_tokens': 0}", 1),
        (REFLECT_ANCHOR, REFLECT_NEW, 1),
        ("'calls': [], 'steps': [], 'cleanup': None, 'started_at': now()}",
         "'calls': [], 'steps': [], 'reflections': [], 'supervision': None, 'cleanup': None,\n"
         "                   'started_at': now()}", 1),
        ('            history = EffectHistory(limit=16)  # isolated per episode and arm\n',
         '            history = EffectHistory(limit=16)  # effect records retained per episode; never shown to the policy\n'
         '            supervisor = (supervision_factory(arm, lambda text: reflect(episode, text))\n'
         '                          if supervision_factory is not None else None)\n'
         '            raws = []\n', 1),
        ("                request = policy_request(runtime, arm, history if arm == 'history' else None, "
         "seed=limits['request_seed'])\n",
         "                suggestion = supervisor.suggestion_for(step_index) if supervisor is not None else None\n"
         "                request = policy_request(runtime, arm, suggestion, seed=limits['request_seed'])\n", 1),
        ("                step = {'index': step_index, 'call_index': len(episode['calls']) - 1, 'before': pack(obs),\n",
         "                step = {'index': step_index, 'call_index': len(episode['calls']) - 1, 'before': pack(obs),\n"
         "                        'suggestion_shown': suggestion,\n", 1),
        (OBSERVE_ANCHOR, OBSERVE_NEW, 1),
    ),
    'engine.py': (),
    'evidence.py': (),
}


def src(target):
    return SOURCE_DIR + target


def derive_one(target):
    source = src(target)
    text = (ROOT / source).read_text(encoding='utf-8')
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for old, new, count in DERIVED[target]:
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    if 'action_effect_history_v1' in text or 'action-effect-history-v1' in text:
        raise ValueError(f'{target}: unexpected remaining source reference')
    return BANNER.format(source=source) + text


def derive():
    return {TARGET_DIR + target: derive_one(target) for target in DERIVED}


def substitution_counts():
    return {TARGET_DIR + t: len(subs) for t, subs in DERIVED.items()}


def stale():
    return [t for t, text in derive().items()
            if not (ROOT / t).is_file() or (ROOT / t).read_text(encoding='utf-8') != text]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    if parser.parse_args().check:
        drift = stale()
        if drift:
            raise SystemExit('derived files differ from the derivation: ' + ', '.join(drift))
        print(f'{len(DERIVED)} derived files match the derivation')
        sys.exit(0)
    for target, text in derive().items():
        (ROOT / target).write_text(text, encoding='utf-8', newline='\n')
    print(f'wrote {len(DERIVED)} derived files')
