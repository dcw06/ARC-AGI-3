# Derived from research/control_interface_action_selection_v2/runtime_controls.py (5a21dd3) by scripts/build_progress_subgoal_v1_runtime2.py; edit the derivation.
"""Research-specific preconditions layered over the unchanged smoke lifecycle."""
import hashlib
import json
from pathlib import Path
import re
from . import questionnaire as QN

# The unchanged progress_subgoal_v1 sources the live and rehearsal paths import or read (every module-level import
# of these resolves inside this set; scripts/build_progress_subgoal_v1_runtime2.py recomputes it). Their hashes are
# the ones review r4 bound: the science is reused, never edited.
EXPERIMENT_SOURCES = ('research/action_effect_history_v1/__init__.py', 'research/action_effect_history_v1/contract.py', 'research/action_effect_history_v1/service.py', 'research/action_effect_v1/__init__.py', 'research/action_effect_v1/records.py', 'research/evidence_comprehension_v1/__init__.py', 'research/evidence_comprehension_v1/fake_server.py', 'research/evidence_comprehension_v1/probes.py', 'research/evidence_comprehension_v1/schedule.py', 'research/evidence_comprehension_v1/transport.py', 'research/evidence_comprehension_v2/__init__.py', 'research/evidence_comprehension_v2/fake_server.py', 'research/evidence_comprehension_v2/schedule.py', 'research/progress_subgoal_v1/__init__.py', 'research/progress_subgoal_v1/decision_rules.json', 'research/progress_subgoal_v1/fake_server.py', 'research/progress_subgoal_v1/fixtures.py', 'research/progress_subgoal_v1/probes.json', 'research/progress_subgoal_v1/probes.py', 'research/progress_subgoal_v1/questions.py', 'research/progress_subgoal_v1/reference.py', 'research/progress_subgoal_v1/rehearsal_timing.py', 'research/progress_subgoal_v1/schedule.py', 'research/progress_subgoal_v1/subgoal.py', 'research/transition_evidence_v1/__init__.py', 'research/transition_evidence_v1/transition.py', 'research/transition_evidence_v1/vocabulary.py')
DECISION_RULES = 'research/progress_subgoal_v1/decision_rules.json'
DECISION_RULES_SHA256 = '38c8de63a875e54949fc0ecede9c0dd2b0b603901aad4a3f8348fd6b92089af2'
RUNTIME_PROBES = ('S1', 'S2', 'S3', 'I1', 'I2', 'I3', 'I4', 'C1', 'C2', 'C3')  # the verified runtime's, unchanged
RUNTIME_REQUESTS = 11  # C2 may read /metrics twice
MAXIMUM_MODEL_REQUESTS = RUNTIME_REQUESTS + 5852 + QN.IDLE_READS_PER_TIMEOUT * QN.MAX_TIMED_OUT_CALLS
PROMPT_TOKEN_CEILING, CONTEXT_TOKENS = 60000, 65536


def experiment_record(root):
    """The frozen experiment configuration recomputed from the unchanged sources (never read from the protocol)."""
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1 import questions as Q
    from research.progress_subgoal_v1 import schedule as S
    frozen, digest, rows = QN.scheduled(root)
    requests = [row[4] for row in rows]
    phases = {}
    for _, phase, _, _, _ in rows:
        phases[phase] = phases.get(phase, 0) + 1
    if frozen['system_prompts'] != {c: Q.SYSTEM_PROMPTS[c] for c in frozen['conditions']}:
        raise ValueError('frozen system prompts differ from the question module')
    shapes = {json.dumps({k: v for k, v in r.items() if k not in ('messages', 'response_format')}, sort_keys=True)
              for r in requests}
    formats = {(r['response_format']['type'], r['response_format']['json_schema']['strict']) for r in requests}
    return {'probe_set': QN.FROZEN, 'probe_set_sha256': digest, 'scheduled_calls': len(rows), 'phases': phases,
            'distinct_requests': len({request_hash(r) for r in requests}),
            'request_digest': QN.request_digest([request_hash(r) for r in requests]),
            'arms': list(frozen['conditions']),
            'system_prompt_sha256': {c: hashlib.sha256(p.encode()).hexdigest()
                                     for c, p in sorted(frozen['system_prompts'].items())},
            'decision_source_partition': frozen['decision_source_partition'],
            'request_settings': sorted(json.loads(s) for s in shapes),
            'response_format': sorted([list(f) for f in formats]),
            'max_tokens': Q.MAX_TOKENS, 'served_model': Q.MODEL,
            'call_timing': QN.frozen_timing(), 'per_call_bound_seconds': S.PER_CALL_BOUND_SECONDS,
            'max_consecutive_timeouts': S.MAX_CONSECUTIVE_TIMEOUTS,
            'admission_cutoff_seconds': S.ADMISSION_CUTOFF_SECONDS,
            'idle_check': {'poll_seconds': QN.IDLE_POLL_SECONDS, 'read_timeout_seconds': QN.IDLE_READ_TIMEOUT_SECONDS,
                           'reads_per_timeout': QN.IDLE_READS_PER_TIMEOUT,
                           'max_timed_out_calls': QN.MAX_TIMED_OUT_CALLS},
            'prefix_caching': False, 'prompt_token_ceiling': PROMPT_TOKEN_CEILING, 'context_tokens': CONTEXT_TOKENS}


def validate_protocol(root, protocol):
    experiment = protocol['experiment']
    expected = experiment_record(root)
    drift = sorted(k for k, v in expected.items() if experiment.get(k) != v)
    if drift:
        raise ValueError('frozen experiment configuration drift: ' + ', '.join(drift))
    raw = (Path(root) / DECISION_RULES).read_bytes()
    if hashlib.sha256(raw).hexdigest() != DECISION_RULES_SHA256 or experiment.get('decision_rules_sha256') != DECISION_RULES_SHA256:
        raise ValueError('frozen decision rules drift')
    package, limits = json.loads(raw)['package_limits'], protocol['limits']
    if (package['sessions'] != 1 or limits['authorized_seconds'] != package['maximum_reservation_seconds_per_session']
            or any(limits[k] != package[k] for k in ('internal_seconds', 'admission_cutoff_seconds',
                                                     'cleanup_reserve_seconds', 'maximum_attempts', 'automatic_retries'))
            or limits.get('environment_actions') != 0 or limits.get('scorecards') != 0
            or limits['maximum_model_requests'] != MAXIMUM_MODEL_REQUESTS):
        raise ValueError('limits differ from the frozen package limits')
    audit = QN.token_audit(root)
    tokens = audit.get('prompt_tokens')
    if (audit.get('passed') is not True or audit.get('probe_set_sha256') != expected['probe_set_sha256']
            or audit.get('request_digest') != expected['request_digest'] or not isinstance(tokens, list)
            or len(tokens) != expected['scheduled_calls']
            or any(type(t) is not int or not 0 < t <= PROMPT_TOKEN_CEILING or t + expected['max_tokens'] > CONTEXT_TOKENS
                   for t in tokens)
            or audit.get('max_tokens_check', {}).get('all_cover') is not True):
        raise ValueError('token audit missing, incomplete or not bound to actual requests')
    if protocol['server']['served_model_name'] != expected['served_model']:
        raise ValueError('served model differs from the frozen requests')
    argv = protocol['server']['argv']
    if argv.count('--no-enable-prefix-caching') != 1 or '--enable-prefix-caching' in argv:
        raise ValueError('prefix caching must be explicitly disabled')
    requests = protocol['requests']
    if (len({r['id'] for r in requests}) != len(requests)
            or sum(r.get('max_issues', 1) for r in requests) != MAXIMUM_MODEL_REQUESTS):
        raise ValueError('frozen counted request cap drift')
    research = [r for r in requests if r['kind'] in (QN.KIND, QN.IDLE_KIND)]
    if research != QN.request_plan(expected['scheduled_calls'], expected['call_timing']['timeout_seconds']):
        raise ValueError('questionnaire request plan drift')
    if [r['id'] for r in requests if r not in research] != list(RUNTIME_PROBES):
        raise ValueError('runtime probe plan drift')


def verify_cache_disabled(log):
    with Path(log).open('rb') as stream:
        stream.seek(max(0, Path(log).stat().st_size - 2097152))
        text = stream.read().decode('utf-8', errors='replace')
    values = re.findall(r"enable_prefix_caching(?:['\"])?\s*[:=]\s*(True|False)", text)
    if not values or any(value != 'False' for value in values):
        raise ValueError('server log does not confirm prefix caching disabled')
    return {'disabled': True, 'confirmation': 'all retained startup configuration entries say enable_prefix_caching=False',
            'matches': len(values)}
