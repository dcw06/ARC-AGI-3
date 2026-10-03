# Derived from research/action_effect_history_v1/authority.py by scripts/derive_stagnation_supervision_v1.py; edit the derivation, not this file.
"""Stagnation-supervision-only source, compute and one-attempt-per-session reservation gate.

R6 separates the preserved reservation from explicit source and launch approval.

A review snapshot alone never authorizes a live run. Separate source approval, compute
authorization, and an unconsumed reservation bound to the exact review lock are required.
"""
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
SCOPE = 'stagnation-supervision-v1'
REVIEW = 'notebooks/stagnation-supervision-v1-authorization-r6/source-review.json'
SOURCE = 'reports/stagnation_supervision_v1_source_approval.json'
COMPUTE = 'reports/stagnation_supervision_v1_compute_authorization.json'
EXECUTION = 'research/stagnation_supervision_v1/closed_loop/execution_lock.json'
RESERVATION = 'research/stagnation_supervision_v1/closed_loop/reservation.json'
ATTEMPT_PATTERN = r'ssv1-[A-Za-z0-9-]{8,80}'
LIVE_DISABLED = False  # require() still needs explicit successor source AND launch approval
SESSION_LIMITS = {  # protocol v2 section 11 (proposal; nothing is authorized)
    '1': {'authorized_seconds': 5400, 'internal_seconds': 5100, 'maximum_attempts': 1, 'maximum_policy_calls': 600,
          'maximum_reflection_calls': 32, 'maximum_canaries': 1, 'maximum_episodes': 15,
          'maximum_actions_per_episode': 40, 'automatic_retries': 0, 'scored_submissions': 0, 'holdout_runs': 0},
    '2': {'authorized_seconds': 4800, 'internal_seconds': 4500, 'maximum_attempts': 1, 'maximum_policy_calls': 480,
          'maximum_reflection_calls': 32, 'maximum_canaries': 1, 'maximum_episodes': 12,
          'maximum_actions_per_episode': 40, 'automatic_retries': 0, 'scored_submissions': 0, 'holdout_runs': 0}}
REQUIRED_SOURCE = {'research/stagnation_supervision_v1/closed_loop/' + name for name in
                   ('authority.py', 'contract.py', 'protocol.json', 'runner.py', 'evaluate.py', 'engine.py',
                    'model_service.py', 'service.py', 'bridge.py', 'host.py', 'worker.py', 'monitor.py',
                    'resources.py', 'supervisor.py', 'evidence.py', 'rehearsal.py', 'fake_server.py',
                    'token_bridge.py', 'server_config.py', 'target_evaluate.py')}
REQUIRED_SOURCE |= {'research/stagnation_supervision_v1/' + name for name in
                    ('detector.py', 'supervision.py', 'intervention.py', 'outcomes.py', 'thresholds.py',
                     'trigger_spec.json')}
REQUIRED_SOURCE |= {'research/transition_evidence_v2/' + name for name in ('transition.py', 'vocabulary.py')}
REQUIRED_SOURCE |= {'research/transition_evidence_v1/' + name for name in ('transition.py', 'vocabulary.py')}
REQUIRED_SOURCE |= {'research/action_effect_v1/records.py', 'scripts/stagnation_supervision_v1_launch.py',
                    'reports/m0_profiles/m0-q3vl30-instruct.json', 'config/operational_primary.yaml'}


def _path(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError('unsafe approval reference')
    root = Path(root).resolve()
    unresolved = root / relative
    path = unresolved.resolve()
    if not path.is_relative_to(root) or unresolved.is_symlink():
        raise ValueError('approval reference escapes root')
    return path


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(root, relative):
    path = _path(root, relative)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('oversized authority record')
    return json.loads(path.read_bytes())



RESERVED_HASHES = {'reports/stagnation_supervision_v1_compute_authorization.json': '0d97c067a04fbaf0008e0fda74023a0f9bb613327cf5a530c83fd09a20cb3c96', 'reports/stagnation_supervision_v1_source_approval.json': '34e5961405f97804ce6dc63d5dcfed2a7c2cc88bdcf6c5b49c7f11bdd8d9ca64', 'research/stagnation_supervision_v1/closed_loop/execution_lock.json': '881e83bd166e8f9c884e1fe4a4f1b55dd563923ea0f2871b992e429a279a438c', 'research/stagnation_supervision_v1/closed_loop/reservation.json': 'f55ccb0770d7b26a31fd8b8135cf622a4e2188589d97cee0f932f1f3baa3c70e'}
SUCCESSOR_SOURCE = 'reports/stagnation_supervision_v1_r6_source_approval.json'
LAUNCH = 'reports/stagnation_supervision_v1_r6_launch_approval.json'


def validate_reservation(root=ROOT):
    """The original reservation is immutable and grants no permission to execute."""
    try:
        for name, digest in RESERVED_HASHES.items():
            if _sha(_path(root, name)) != digest:
                raise ValueError('preserved reservation chain differs: ' + name)
        compute, execution, reservation = (_read(root, name) for name in (COMPUTE, EXECUTION, RESERVATION))
        if (compute['authorization_scope'] != 'reserve_one_attempt_only'
                or compute['submission_authorized'] is not False
                or execution['session'] != '1' or reservation['status'] != 'reserved'
                or reservation['events'] != ['reserve'] or reservation['seconds'] != 5400):
            raise ValueError('reservation state')
        return execution
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise PermissionError('valid preserved session-1 reservation required') from exc


def require(root=ROOT):
    """Live paths need a fresh R6 source approval AND a separate explicit launch decision."""
    execution = validate_reservation(root)
    try:
        review = _read(root, REVIEW)
        if (review.get('status') != 'reviewed_launch_source' or review.get('scope') != SCOPE
                or not REQUIRED_SOURCE <= set(review['bindings'])):
            raise ValueError('successor source lock')
        for name, digest in review['bindings'].items():
            if _sha(_path(root, name)) != digest:
                raise ValueError('successor source drift')
        lock_hash = _sha(_path(root, REVIEW))
        source = _read(root, SUCCESSOR_SOURCE)
        launch = _read(root, LAUNCH)
        for value, kind in ((source, 'source'), (launch, 'launch')):
            if (value.get('status') != 'approved' or value.get('scope') != SCOPE
                    or value.get('approval_kind') != kind or value.get('review_lock_sha256') != lock_hash
                    or not isinstance(value.get('user_response'), str) or not value['user_response'].strip()):
                raise ValueError(kind + ' approval')
        if (launch.get('authorization_scope') != 'submit_and_execute_one_attempt'
                or launch.get('submission_authorized') is not True
                or launch.get('source_approval_sha256') != _sha(_path(root, SUCCESSOR_SOURCE))
                or launch.get('reservation_sha256') != RESERVED_HASHES[RESERVATION]
                or launch.get('compute_authorization_sha256') != RESERVED_HASHES[COMPUTE]
                or launch.get('execution_sha256') != RESERVED_HASHES[EXECUTION]
                or launch.get('attempt_id') != execution['attempt_id'] or launch.get('session') != '1'
                or type(launch.get('maximum_submissions')) is not int or launch['maximum_submissions'] != 1
                or type(launch.get('automatic_retries')) is not int or launch['automatic_retries'] != 0):
            raise ValueError('explicit one-use launch binding')
        return execution
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise PermissionError('R6 source approval and explicit hash-bound launch approval required') from exc


def consume_runtime(working, root=ROOT):
    """Persist the one-use claim before target side effects; never retry on conflict."""
    execution = require(root)
    working = Path(working)
    if not working.is_dir() or working.is_symlink():
        raise ValueError('invalid provider working directory')
    marker = working / ('.' + execution['attempt_id'] + '.runtime-consumed.json')
    with marker.open('x', encoding='utf-8') as stream:
        json.dump({'status': 'consumed', 'attempt_id': execution['attempt_id']}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    return marker


def verify_runtime_claim(working, root=ROOT):
    execution = require(root)
    marker = Path(working) / ('.' + execution['attempt_id'] + '.runtime-consumed.json')
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 1024:
        raise PermissionError('runtime claim missing')
    if json.loads(marker.read_bytes()) != {'status': 'consumed', 'attempt_id': execution['attempt_id']}:
        raise PermissionError('runtime claim mismatch')
    return marker


def rehearsal_gate():
    """CPU rehearsal only: explicit opt-in, no visible GPU, never a live authority."""
    if os.environ.get('SSV_REHEARSAL') != '1' or os.environ.get('CUDA_VISIBLE_DEVICES', '') != '':
        raise PermissionError('rehearsal mode requires SSV_REHEARSAL=1 and no visible GPU')
    return {'mode': 'rehearsal', 'attempt_id': None}
