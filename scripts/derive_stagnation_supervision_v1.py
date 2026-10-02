"""Derive the GPU-disabled stagnation-supervision closed-loop runner from action-effect-history v1's reviewed files.

Sources: action-effect-history v1's files, bound by the separately versioned derivation-source manifest
(reports/stagnation_supervision_v1_derivation_sources_r1.json). All but the supplementary rehearsal script are
also bound by the unchanged historical review lock
(notebooks/action-effect-history-v1-review-r3/review-source-lock.json) and run live as attempt aeh1-4c75150a:
research/action_effect_history_v1/{runner,contract,engine,evidence,service,host,worker,supervisor,monitor,resources,
authority}.py and scripts/{action_effect_history_v1_launch,rehearse_action_effect_history_v1}.py. They are reused, not
edited. Each derived file is its source with the global renames below and that file's own substitutions, each
required to match an exact number of times. A span substitution (('span', start, end), new, 1) replaces the text from
`start` through `end`; each marker must occur exactly once.

Hand-written (not derived): research/stagnation_supervision_v1/closed_loop/{bridge,service,fake_server,rehearsal,
requests,evaluate}.py and protocol.json. Not yet derived (needed before an exact package lock): the package, review
and notebook scripts and the notebook.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = 'research/stagnation_supervision_v1/closed_loop/'
SOURCE_DIR = 'research/action_effect_history_v1/'
BANNER = '# Derived from {source} by scripts/derive_stagnation_supervision_v1.py; edit the derivation, not this file.\n'
GLOBAL = (('research.action_effect_history_v1.service', 'research.stagnation_supervision_v1.closed_loop.model_service'),
          ('research.action_effect_history_v1', 'research.stagnation_supervision_v1.closed_loop'),
          ('research/action_effect_history_v1/', 'research/stagnation_supervision_v1/closed_loop/'),
          ('action_effect_history_run_v1', 'stagnation_supervision_run_v1'),
          ('action_effect_history_evidence_v1', 'stagnation_supervision_evidence_v1'),
          ('action-effect-history-v1', 'stagnation-supervision-v1'),
          ('action_effect_history_v1', 'stagnation_supervision_v1'),
          ('from .service import', 'from .model_service import'),
          ('HistoryModelService', 'SupervisionModelService'),
          ('AEH_', 'SSV_'),
          ('aeh1-', 'ssv1-'),
          # closed_loop/ is one directory deeper than research/action_effect_history_v1/ (scripts use parents[1])
          ('ROOT = Path(__file__).resolve().parents[2]', 'ROOT = Path(__file__).resolve().parents[3]'))

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
        ("VERSION = 'stagnation_supervision_run_v1'", "VERSION = 'stagnation_supervision_run_v2'", 1),
        ("class TechnicalFailure(Exception):\n    pass\n",
         "class TechnicalFailure(Exception):\n    pass\n\n\n"
         "class FailureRuleStop(Exception):\n    \"\"\"A predeclared scientific/reliability rule stopped the session.\"\"\"\n"
         "    pass\n", 1),
        ('from research.stagnation_supervision_v1.closed_loop.contract import policy_request\n',
         'from research.stagnation_supervision_v1.closed_loop.contract import policy_request\n'
         'from research.stagnation_supervision_v1.closed_loop.bridge import raw_transition, reflection_request, '
         'supervisor_view\n', 1),
        ('        evidence_lock_root=None):', '        evidence_lock_root=None, supervision_factory=None):', 1),
        ("'pairs': [], 'episodes': [], 'calls': 0, 'dispatches': 0, 'prompt_tokens': 0, 'completion_tokens': 0}",
         "'pairs': [], 'episodes': [], 'calls': 0, 'dispatches': 0, 'prompt_tokens': 0, 'completion_tokens': 0,\n"
         "              'reflection_calls': 0, 'reflection_prompt_tokens': 0, 'reflection_completion_tokens': 0,\n"
         "              'dispatch_failures': 0, 'reflection_arms_stopped': False, 'failure_rule': None,\n"
         "              'full_protocol_proof': limits['actions_per_episode'] == 40}", 1),
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
        ("                persist(episode)\n                if supervisor is not None:  # the detector observes every step in every arm\n",
         "                persist(episode)\n"
         "                if outcome['status'] != 'acknowledged':\n"
         "                    report['dispatch_failures'] += 1\n"
         "                    if report['dispatch_failures'] * 10 > report['dispatches']:\n"
         "                        report['failure_rule'] = {'rule': 'dispatch_reliability',\n"
         "                                                  'failed_or_unknown': report['dispatch_failures'],\n"
         "                                                  'dispatches': report['dispatches']}\n"
         "                        persist(episode)\n"
         "                if supervisor is not None:  # the detector observes every step in every arm\n", 1),
        ("                    if any(r['status'] == 'audit_failure' for r in episode['reflections']):\n"
         "                        raise TechnicalFailure('reflection response/token audit')\n"
         "                    check()\n",
         "                    if any(r['status'] == 'audit_failure' for r in episode['reflections']):\n"
         "                        raise TechnicalFailure('reflection response/token audit')\n"
         "                    attempted = [e['call'] for ep in report['episodes'] for e in\n"
         "                                 (ep.get('supervision') or {}).get('events', []) if e['outcome'] == 'called']\n"
         "                    invalid = sum(c['error'] is None and not c['parsed']['valid'] for c in attempted)\n"
         "                    if (episode['arm'] in ('periodic', 'triggered') and not report['reflection_arms_stopped']\n"
         "                            and len(attempted) >= 10 and invalid * 2 > len(attempted)):\n"
         "                        report['reflection_arms_stopped'] = True\n"
         "                        report['failure_rule'] = {'rule': 'reflection_interface', 'attempted': len(attempted),\n"
         "                                                  'invalid_outputs': invalid}\n"
         "                        episode['stop_reason'] = 'reflection_interface_stop'\n"
         "                        persist(episode)\n"
         "                    check()\n", 1),
        ("                if outcome['status'] != 'acknowledged':\n"
         "                    episode['stop_reason'] = 'dispatch_failure'\n",
         "                if report['failure_rule'] is not None and report['failure_rule']['rule'] == 'dispatch_reliability':\n"
         "                    raise FailureRuleStop('dispatch_reliability')\n"
         "                if outcome['status'] != 'acknowledged':\n"
         "                    episode['stop_reason'] = 'dispatch_failure'\n", 1),
        ("                obs = post\n            else:\n",
         "                obs = post\n"
         "                if episode['stop_reason'] == 'reflection_interface_stop':\n"
         "                    break\n"
         "            else:\n", 1),
        ("            episode['status'] = 'complete'\n            episode['final'] = pack(obs)\n",
         "            episode['status'] = ('failure_rule_stopped' if episode['stop_reason'] ==\n"
         "                                 'reflection_interface_stop' else 'complete')\n"
         "            episode['final'] = pack(obs)\n", 1),
        ("        except DeadlineExceeded:\n            episode.update(status='interrupted', stop_reason='interrupted')\n",
         "        except FailureRuleStop:\n"
         "            episode.update(status='failure_rule_stopped', stop_reason='dispatch_reliability_stop')\n"
         "            raise\n"
         "        except DeadlineExceeded:\n            episode.update(status='interrupted', stop_reason='interrupted')\n", 1),
        ("            for index, arm in enumerate(pair['order']):\n"
         "                episode_run(pair, arm, index)\n"
         "            entry['status'] = 'complete'\n",
         "            for index, arm in enumerate(pair['order']):\n"
         "                if report['reflection_arms_stopped'] and arm in ('periodic', 'triggered'):\n"
         "                    entry.setdefault('skipped_arms', []).append({'arm': arm,\n"
         "                                                                'reason': 'reflection_interface_stop'})\n"
         "                    persist()\n"
         "                    continue\n"
         "                episode = episode_run(pair, arm, index)\n"
         "                if (limits['actions_per_episode'] == 40 and pair['pair_id'] == 'b1-ar25'\n"
         "                        and arm == 'continuation' and episode['status'] == 'complete'\n"
         "                        and episode['stop_reason'] in ('action_cap', 'win', 'game_over')\n"
         "                        and episode['supervision']['summary']['detector_firings'] == 0):\n"
         "                    report['failure_rule'] = {'rule': 'zero_detector_firings',\n"
         "                                              'episode_id': episode['episode_id']}\n"
         "                    persist()\n"
         "                    raise FailureRuleStop('zero_detector_firings')\n"
         "            entry['status'] = ('partial' if entry.get('skipped_arms') or\n"
         "                               any(e['pair_id'] == pair['pair_id'] and e['status'] == 'failure_rule_stopped'\n"
         "                                   for e in report['episodes']) else 'complete')\n", 1),
        ("        report['status'] = 'complete' if all(p['status'] == 'complete' for p in report['pairs']) else 'incomplete'",
         "        report['status'] = ('failure_rule_stopped' if report['reflection_arms_stopped'] else\n"
         "                            'complete' if all(p['status'] == 'complete' for p in report['pairs']) else 'incomplete')", 1),
        ("    except DeadlineExceeded as exc:\n        canceled = 'cancellation' in str(exc)\n",
         "    except FailureRuleStop as exc:\n"
         "        report.update(status='failure_rule_stopped', error=str(exc))\n"
         "        if report['pairs'] and report['pairs'][-1].get('status') == 'running':\n"
         "            report['pairs'][-1]['status'] = 'interrupted'\n"
         "    except DeadlineExceeded as exc:\n        canceled = 'cancellation' in str(exc)\n", 1),
    ),
    'engine.py': (),
    'evidence.py': (),
}


# ---- process stack (host, worker, supervisor, monitor, resources, authority, model service, launch, rehearse)

MODEL_COMPLETE_OLD = """        if self.calls >= MAX_POLICY_CALLS:
            raise ValueError('policy call ceiling (144)')
        self.calls += 1  # a failed call still consumes the allowance
        validate_policy_request(request)
"""
MODEL_COMPLETE_NEW = """        from research.stagnation_supervision_v1.closed_loop.service import kind as request_kind
        if request_kind(request) == 'reflection':
            if self.reflection_calls >= MAX_REFLECTION_CALLS:
                raise ValueError('reflection call ceiling')
            self.reflection_calls += 1  # a failed call still consumes the allowance
        else:
            if self.calls >= MAX_POLICY_CALLS:
                raise ValueError('policy call ceiling')
            self.calls += 1  # a failed call still consumes the allowance
        validate_policy_request(request)
"""
VALIDATE_NEW = '''def validate_policy_request(request):
    """Exact frozen request contracts (policy or reflection); raises ValueError before any transport."""
    from research.stagnation_supervision_v1.closed_loop.service import (
        kind, validate_policy_request as policy, validate_reflection_request as reflection)
    return reflection(request) if kind(request) == 'reflection' else policy(request)
'''
SESSION_LIMITS = """LIVE_DISABLED = True  # this source revision cannot launch; a reviewed revision must remove this line explicitly
SESSION_LIMITS = {  # protocol v2 section 11 (proposal; nothing is authorized)
    '1': {'authorized_seconds': 5400, 'internal_seconds': 5100, 'maximum_attempts': 1, 'maximum_policy_calls': 600,
          'maximum_reflection_calls': 32, 'maximum_canaries': 1, 'maximum_episodes': 15,
          'maximum_actions_per_episode': 40, 'automatic_retries': 0, 'scored_submissions': 0, 'holdout_runs': 0},
    '2': {'authorized_seconds': 4800, 'internal_seconds': 4500, 'maximum_attempts': 1, 'maximum_policy_calls': 480,
          'maximum_reflection_calls': 32, 'maximum_canaries': 1, 'maximum_episodes': 12,
          'maximum_actions_per_episode': 40, 'automatic_retries': 0, 'scored_submissions': 0, 'holdout_runs': 0}}
"""
REQUIRED_NEW = """REQUIRED_SOURCE = {'research/stagnation_supervision_v1/closed_loop/' + name for name in
                   ('authority.py', 'contract.py', 'protocol.json', 'runner.py', 'evaluate.py', 'engine.py',
                    'model_service.py', 'service.py', 'bridge.py', 'host.py', 'worker.py', 'monitor.py',
                    'resources.py', 'supervisor.py', 'evidence.py', 'rehearsal.py', 'fake_server.py',
                    'token_bridge.py')}
REQUIRED_SOURCE |= {'research/stagnation_supervision_v1/' + name for name in
                    ('detector.py', 'supervision.py', 'intervention.py', 'outcomes.py', 'thresholds.py',
                     'trigger_spec.json')}
REQUIRED_SOURCE |= {'research/transition_evidence_v2/' + name for name in ('transition.py', 'vocabulary.py')}
REQUIRED_SOURCE |= {'research/transition_evidence_v1/' + name for name in ('transition.py', 'vocabulary.py')}
REQUIRED_SOURCE |= {'research/action_effect_v1/records.py', 'scripts/stagnation_supervision_v1_launch.py',
                    'reports/m0_profiles/m0-q3vl30-instruct.json', 'config/operational_primary.yaml'}
"""

DERIVED.update({
    'model_service.py': (
        ('MAX_POLICY_CALLS = 144\n',
         'MAX_POLICY_CALLS = 1080  # the whole protocol (closed_loop/protocol.json); each session runs fewer\n'
         'MAX_REFLECTION_CALLS = 64\n', 1),
        (('span', 'def validate_policy_request(request):\n',
          "    return 'history' if HISTORY_FIELD in observation else 'baseline'\n"), VALIDATE_NEW, 1),
        ('    """One canary, then at most 144 contract-checked policy calls; raw evidence returned for retention."""',
         '    """One canary, then contract-checked policy and reflection calls within separate ceilings; raw evidence\n'
         '    returned for retention."""', 1),
        ('        self.calls = 0\n', '        self.calls = 0\n        self.reflection_calls = 0\n', 1),
        (MODEL_COMPLETE_OLD, MODEL_COMPLETE_NEW, 1),
        ("            or type(audit.get('server_prompt_tokens')) is not int\n"
         "            or audit.get('server_prompt_tokens') != audit.get('tokenizer_prompt_tokens')\n"
         "            or audit.get('finish_reason') != 'stop'):" ,
         "            or type(audit.get('server_prompt_tokens')) is not int\n"
         "            or type(audit.get('tokenizer_prompt_tokens')) is not int\n"
         "            or not 0 < audit['server_prompt_tokens'] <= MAX_PROMPT_TOKENS\n"
         "            or audit.get('server_prompt_tokens') != audit.get('tokenizer_prompt_tokens')\n"
         "            or type(audit.get('server_completion_tokens')) is not int\n"
         "            or not 0 < audit['server_completion_tokens'] <= MAX_COMPLETION_TOKENS\n"
         "            or audit.get('finish_reason') != 'stop'):", 1),
    ),
    'host.py': (
        ('from certification.phase4_integrated_v2.bridge import BridgeServer\n',
         'from research.stagnation_supervision_v1.closed_loop.token_bridge import TokenBridgeServer as BridgeServer\n', 1),
        ("'action_effect_history_model_readiness'", "'stagnation_supervision_model_readiness'", 1),
        ('hard_seconds=3300, finalization_reserve_seconds=300)',
         'hard_seconds=5100, finalization_reserve_seconds=300)  # the longer session', 1),
        ("'scope': 'action_effect_history_model_host'", "'scope': 'stagnation_supervision_model_host'", 1),
        ('policy_calls=service.calls)', 'policy_calls=service.calls, reflection_calls=service.reflection_calls)', 1),
    ),
    'worker.py': (
        ('    gate(mode)  # before model subprocess, game import or GPU access\n',
         "    execution = gate(mode)  # before model subprocess, game import or GPU access\n"
         "    if mode == 'live' and str(execution.get('session')) != str(session):\n"
         "        raise PermissionError('worker session differs from the approved execution')\n", 1),
        ("FAULTS = ('none', 'model_startup', 'transport', 'slow', 'invalid_history', 'storage', 'surviving_child')",
         "FAULTS = ('none', 'model_startup', 'transport', 'slow', 'reflection_invalid', 'reflection_length', 'storage',\n"
         "          'surviving_child')", 1),
        ("def run_worker(output, scratch, environments, model_python, *, deadline, mode, fault='none'):",
         "def run_worker(output, scratch, environments, model_python, *, deadline, mode, fault='none', session=None):", 1),
        ("    host_fault = fault if fault in ('model_startup', 'transport', 'slow', 'invalid_history') else 'none'",
         "    host_fault = fault if fault in ('model_startup', 'transport', 'slow', 'reflection_invalid',\n"
         "                                    'reflection_length') else 'none'", 1),
        ('        from .runner import run\n',
         '        from .runner import run\n'
         '        from .bridge import session_run_spec, supervision_factory, worker_token_counter\n'
         '        from research.stagnation_supervision_v1 import thresholds\n'
         '        spec = session_run_spec(session, mode)\n', 1),
        ('                     deadline_seconds=max(.01, deadline - time.monotonic()), cancel=cancel,\n',
         '                     deadline_seconds=max(.01, deadline - time.monotonic()), cancel=cancel, spec=spec,\n'
         '                     supervision_factory=supervision_factory(spec, thresholds.load(),\n'
         '                                                             token_counter=worker_token_counter(mode, proxy)),\n', 1),
        ("    parser.add_argument('--fault', default='none')\n",
         "    parser.add_argument('--fault', default='none')\n"
         "    parser.add_argument('--session', choices=('1', '2'), required=True)\n", 1),
        ('               mode=args.mode, fault=args.fault)', '               mode=args.mode, fault=args.fault, session=args.session)', 1),
    ),
    'resources.py': (
        ("'scope': 'action_effect_history_independent_gpu_cleanup'", "'scope': 'stagnation_supervision_independent_gpu_cleanup'", 1),
    ),
    'monitor.py': (
        ('interval=.25, clock=time.monotonic', 'interval=.5, clock=time.monotonic', 1),
        ('not 0 < interval <= 1', 'interval != .5 or not 0 < deadline - started <= 5100', 1),
        ("'first_cell_monotonic': started, 'samples': []", "'first_cell_monotonic': started, 'sampling_interval_seconds': .5, 'samples': []", 1),
        ("SCOPES = {'live': 'action_effect_history_live_resource_monitor',\n"
         "          'rehearsal': 'action_effect_history_rehearsal_monitor_injected_gpu'}",
         "SCOPES = {'live': 'stagnation_supervision_live_resource_monitor',\n"
         "          'rehearsal': 'stagnation_supervision_rehearsal_monitor_injected_gpu'}", 1),
    ),
    'supervisor.py': (
        ('LIVE_INTERNAL_SECONDS = 3300\n',
         "LIVE_INTERNAL_SECONDS = {'1': 5100, '2': 4500}  # per session: proposed reservation minus 300 s (protocol v2)\n", 1),
        ("        internal_seconds=LIVE_INTERNAL_SECONDS, fault='none', claimed=False, prepared=False, spawn=subprocess.Popen):",
         "        internal_seconds=None, fault='none', claimed=False, prepared=False, spawn=subprocess.Popen, session=None):", 1),
        ('    gate(mode)  # before output, subprocess or GPU query\n',
         "    execution = gate(mode)  # before output, subprocess or GPU query\n"
         "    if mode == 'live' and str(execution.get('session')) != str(session):\n"
         "        raise PermissionError('supervisor session differs from the approved execution')\n"
         '    if str(session) not in LIVE_INTERNAL_SECONDS:\n'
         "        raise ValueError('unknown session')\n"
         '    live_seconds = LIVE_INTERNAL_SECONDS[str(session)]\n'
         '    internal_seconds = live_seconds if internal_seconds is None else internal_seconds\n', 1),
        ("internal_seconds != LIVE_INTERNAL_SECONDS):", 'internal_seconds != live_seconds):', 1),
        ('not 60 <= internal_seconds <= LIVE_INTERNAL_SECONDS:', 'not 60 <= internal_seconds <= live_seconds:', 1),
        ("    report = {'scope': 'action_effect_history_' + mode, 'mode': mode,",
         "    report = {'scope': 'stagnation_supervision_' + mode, 'mode': mode, 'session': str(session),", 1),
        ("prefix='action-effect-history-'", "prefix='stagnation-supervision-'", 1),
        ("'--mode', mode, '--fault', worker_fault],", "'--mode', mode, '--fault', worker_fault,\n"
         "                             '--session', str(session)],", 1),
        ("    parser.add_argument('--internal-seconds', type=int, default=LIVE_INTERNAL_SECONDS)",
         "    parser.add_argument('--internal-seconds', type=int, default=None)\n"
         "    parser.add_argument('--session', choices=('1', '2'), required=True)", 1),
        ("claimed=args.mode == 'live', prepared=True)", "claimed=args.mode == 'live', prepared=True, session=args.session)", 1),
    ),
    'authority.py': (
        ('"""Action-effect-history-only source, compute and one-attempt reservation gate.',
         '"""Stagnation-supervision-only source, compute and one-attempt-per-session reservation gate.\n\n'
         'Live mode is disabled in this source revision (LIVE_DISABLED); no review lock, approval, authorization or\n'
         'reservation exists.', 1),
        ("REVIEW = 'notebooks/stagnation-supervision-v1-review-r3/review-source-lock.json'",
         "REVIEW = 'notebooks/stagnation-supervision-v1-review-r1/review-source-lock.json'", 1),
        (('span', 'LIMITS = {', "'holdout_runs': 0}\n"), SESSION_LIMITS, 1),
        (('span', 'REQUIRED_SOURCE = {', "'config/operational_primary.yaml'}\n"), REQUIRED_NEW, 1),
        ('    """Fail before installation, subprocess creation, GPU query or model import."""\n',
         '    """Fail before installation, subprocess creation, GPU query or model import."""\n'
         '    if LIVE_DISABLED:\n'
         "        raise PermissionError('stagnation-supervision-v1 live mode is disabled in this source revision')\n", 1),
        ("        for name, expected in LIMITS.items():\n"
         "            if type(compute.get(name)) is not int or compute[name] != expected:\n"
         "                raise ValueError('compute limit: ' + name)",
         "        execution = _read(root, EXECUTION)\n"
         "        session = execution.get('session')\n"
         "        granted_sessions = compute.get('sessions')\n"
         "        if (type(session) is not str or session not in SESSION_LIMITS or\n"
         "                type(granted_sessions) is not dict or set(granted_sessions) != {session}):\n"
         "            raise ValueError('compute must authorize exactly the execution session')\n"
         "        for name, expected in SESSION_LIMITS[session].items():\n"
         "            if (type(granted_sessions[session].get(name)) is not int or\n"
         "                    granted_sessions[session][name] != expected):\n"
         "                raise ValueError(f'compute limit: session {session} {name}')", 1),
        ('        execution, reservation = _read(root, EXECUTION), _read(root, RESERVATION)\n',
         '        reservation = _read(root, RESERVATION)\n', 1),
        ("reservation.get('seconds') != LIMITS['authorized_seconds'] or",
         "reservation.get('seconds') != SESSION_LIMITS.get(str(execution.get('session')), {}).get('authorized_seconds') or", 1),
        ("        raise PermissionError('action-effect-history v1 requires reviewed source, separate compute '\n"
         "                              'approval and one fresh reservation') from exc",
         "        raise PermissionError('stagnation-supervision v1 requires reviewed source, separate compute '\n"
         "                              'approval and one fresh reservation per session') from exc", 1),
    ),
    'scripts/stagnation_supervision_v1_launch.py': (
        ('        require(root)\n        if fault !=',
         "        execution = require(root)\n"
         "        if str(execution.get('session')) != str(session):\n"
         "            raise PermissionError('launch session differs from the approved execution')\n"
         "        if fault !=", 1),
        ('"""First-cell lifecycle for the action-effect-history comparison (live needs separate reviewed authority)."""',
         '"""First-cell lifecycle for one stagnation-supervision session (live needs separate reviewed authority)."""', 1),
        ("def run_supervisor(output, working, game_python, model_python, games, *, started, mode, internal_seconds,\n"
         "                   fault='none', root=ROOT, spawn=subprocess.Popen):",
         "def run_supervisor(output, working, game_python, model_python, games, *, started, mode, internal_seconds,\n"
         "                   fault='none', root=ROOT, spawn=subprocess.Popen, session=None):", 1),
        ("'--internal-seconds', str(internal_seconds), '--fault', fault]",
         "'--internal-seconds', str(internal_seconds), '--fault', fault,\n"
         "               '--session', str(session)]", 1),
        ("def run(output, working, *, started, root=ROOT, mode='live', internal_seconds=3300, fault='none'):\n"
         '    """Installation, supervisor, evidence and cleanup all charged to `started`."""\n',
         "def run(output, working, *, started, root=ROOT, mode='live', internal_seconds=None, fault='none', session=None):\n"
         '    """Installation, supervisor, evidence and cleanup all charged to `started`."""\n'
         '    from research.stagnation_supervision_v1.closed_loop.supervisor import LIVE_INTERNAL_SECONDS\n'
         '    if str(session) not in LIVE_INTERNAL_SECONDS:\n'
         "        raise ValueError('unknown session')\n"
         '    internal_seconds = LIVE_INTERNAL_SECONDS[str(session)] if internal_seconds is None else internal_seconds\n', 1),
        ("        if fault != 'none' or internal_seconds != 3300:",
         "        if fault != 'none' or internal_seconds != LIVE_INTERNAL_SECONDS[str(session)]:", 1),
        ("prefix='action-effect-history-dependencies-'", "prefix='stagnation-supervision-dependencies-'", 1),
        ('mode=mode, internal_seconds=internal_seconds, root=root)',
         'mode=mode, internal_seconds=internal_seconds, root=root, session=session)', 1),
        ('started=started, mode=mode, internal_seconds=internal_seconds, fault=fault, root=root)',
         'started=started, mode=mode, internal_seconds=internal_seconds, fault=fault, root=root,\n'
         '                                    session=session)', 1),
        ("    receipt = {'scope': 'action_effect_history_first_cell', 'mode': mode,",
         "    receipt = {'scope': 'stagnation_supervision_first_cell', 'mode': mode, 'session': str(session),", 1),
        ('def notebook_entry(source, started, mode):', 'def notebook_entry(source, started, mode, session):', 1),
        ("started=started, root=source, mode='live')", "started=started, root=source, mode='live', session=session)", 1),
        ("started=started, root=source, mode='rehearsal',\n",
         "started=started, root=source, mode='rehearsal', session=session,\n", 1),
    ),
    'scripts/rehearse_stagnation_supervision_v1.py': (
        ("def rehearse(fault='none', seconds=2400, workdir=None, root=ROOT):",
         "def rehearse(fault='none', seconds=2400, workdir=None, root=ROOT, session='1'):", 1),
        ("prefix='aeh-rehearsal-'", "prefix='ssv-rehearsal-'", 1),
        ("mode='rehearsal', internal_seconds=seconds, fault=fault)",
         "mode='rehearsal', internal_seconds=seconds, fault=fault, session=session)", 1),
        ("    parser.add_argument('--seconds', type=int, default=2400)\n",
         "    parser.add_argument('--seconds', type=int, default=2400)\n"
         "    parser.add_argument('--session', choices=('1', '2'), default='1')\n", 1),
        ("Path.home() / 'aeh-rehearsal'", "Path.home() / 'ssv-rehearsal'", 1),
        ('rehearse(args.fault, args.seconds, tempfile.mkdtemp(dir=base))',
         'rehearse(args.fault, args.seconds, tempfile.mkdtemp(dir=base), session=args.session)', 1),
    ),
})


# R3 launch-review repairs. Historical sources and embedded R1/R2 notebooks stay intact.
DERIVED['host.py'] += (
    (("span", '    class ServerWithoutLegacyCanary(ModelService):',
      '    owner = ServerWithoutLegacyCanary(primary)\n'),
     '    from .server_config import model_owner\n'
     '    owner = model_owner(primary, retain)\n', 1),
    ("    service.artifact = {'rehearsal': 'scripted_model_not_target_evidence'}\n",
     "    service.artifact = {'rehearsal': 'scripted_model_not_target_evidence'}\n"
     "    from .server_config import rehearsal_record\n"
     "    retain(rehearsal_record())\n", 1),
    ("'startup_seconds': None, 'error': None}",
     "'startup_seconds': None, 'error': None, 'started_monotonic': begun}", 1),
    ("        store.save('canary.json', record)\n",
     "        from .server_config import KIND\n"
     "        name = 'server-configuration.json' if record.get('kind') == KIND else 'canary.json'\n"
     "        store.save(name, record)\n", 1),
)
DERIVED['worker.py'] += (
    ("'canary_sha256': ready['canary_audit']['response_sha256'], 'mode': mode}",
     "'canary_sha256': ready['canary_audit']['response_sha256'], 'mode': mode,\n"
     "                                        'ready_monotonic': time.monotonic()}", 1),
)
DERIVED['supervisor.py'] += (
    ("            released = time.monotonic()\n",
     "            released = time.monotonic()\n"
     "            report['worker_released_seconds'] = released - started\n", 1),
    ("            if worker.returncode != 0:\n",
     "            report['worker_completed_seconds'] = time.monotonic() - started\n"
     "            if worker.returncode != 0:\n", 1),
    ("control.save('stop-monitor.json', {'worker_group_exited': True})",
     "control.save('stop-monitor.json', {'worker_group_exited': True, 'elapsed_seconds': time.monotonic() - started})", 1),
)
DERIVED['resources.py'] += (
    ("        result.update(gpu_uuid=sample['uuid'], remaining_gpu_pids=0, gpu_cleanup_verified=True)",
     "        if clock() >= deadline:\n"
     "            raise TimeoutError('GPU cleanup deadline after query')\n"
     "        result.update(gpu_uuid=sample['uuid'], remaining_gpu_pids=0, gpu_cleanup_verified=True,\n"
     "                      checked_monotonic=clock())", 1),
)
DERIVED['scripts/stagnation_supervision_v1_launch.py'] += (
    ("'returncode': process.returncode, 'errors': errors}",
     "'returncode': process.returncode, 'errors': errors,\n"
     "                                                            'checked_monotonic': time.monotonic()}", 1),
    ("'dependency_trees_removed': (not Path(folder).exists()) if folder else None,",
     "'first_cell_monotonic': started, 'internal_seconds': internal_seconds,\n"
     "               'dependency_trees_removed': (not Path(folder).exists()) if folder else None,", 1),
)
DERIVED['authority.py'] += (
    ("'token_bridge.py')}", "'token_bridge.py', 'server_config.py', 'target_evaluate.py')}", 1),
)

RENAMED_SOURCE = {'model_service.py': 'service.py'}
SCRIPT_SOURCES = {'scripts/stagnation_supervision_v1_launch.py': 'scripts/action_effect_history_v1_launch.py',
                  'scripts/rehearse_stagnation_supervision_v1.py': 'scripts/rehearse_action_effect_history_v1.py'}
SOURCE_MANIFEST = 'reports/stagnation_supervision_v1_derivation_sources_r1.json'


def src(target):
    return SCRIPT_SOURCES.get(target) or SOURCE_DIR + RENAMED_SOURCE.get(target, target)


def target_path(target):
    return target if target in SCRIPT_SOURCES else TARGET_DIR + target


def verify_source_bindings():
    """Require every derivation source and its stated provenance; never extend the historical lock in place."""
    manifest = json.loads((ROOT / SOURCE_MANIFEST).read_bytes())
    lock_path = manifest['historical_review_lock']
    lock_raw = (ROOT / lock_path).read_bytes()
    if hashlib.sha256(lock_raw).hexdigest() != manifest['historical_review_lock_sha256']:
        raise ValueError('historical source review lock drift')
    historical = json.loads(lock_raw)['bindings']
    expected_sources = {src(target) for target in DERIVED}
    if set(manifest['sources']) != expected_sources:
        raise ValueError('derivation source inventory drift')
    supplementary = {'scripts/rehearse_action_effect_history_v1.py'}
    if expected_sources - set(historical) != supplementary:
        raise ValueError('supplementary source inventory drift')
    for source in sorted(expected_sources):
        entry = manifest['sources'][source]
        expected_provenance = 'supplementary_source_review' if source in supplementary else 'historical_review_lock'
        if set(entry) != {'sha256', 'provenance'} or entry['provenance'] != expected_provenance:
            raise ValueError('source provenance drift: ' + source)
        if source in historical and entry['sha256'] != historical[source]:
            raise ValueError('historical source binding drift: ' + source)
        if hashlib.sha256((ROOT / source).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('derivation source bytes drift: ' + source)
    return manifest


def derive_one(target):
    source = src(target)
    text = (ROOT / source).read_text(encoding='utf-8')
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for old, new, count in DERIVED[target]:
        if isinstance(old, tuple):  # ('span', start, end)
            _, start, end = old
            if text.count(start) != 1 or text.count(end) != 1 or text.index(end) < text.index(start):
                raise ValueError(f'{target}: span markers {start[:50]!r} .. {end[:50]!r} not unique and ordered')
            i, j = text.index(start), text.index(end) + len(end)
            text = text[:i] + new + text[j:]
            continue
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    if 'action_effect_history_v1' in text or 'action-effect-history-v1' in text:
        raise ValueError(f'{target}: unexpected remaining source reference')
    return BANNER.format(source=source) + text


def derive():
    verify_source_bindings()
    return {target_path(target): derive_one(target) for target in DERIVED}


def substitution_counts():
    return {target_path(t): len(subs) for t, subs in DERIVED.items()}


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
