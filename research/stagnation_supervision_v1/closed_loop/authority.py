# Derived from research/action_effect_history_v1/authority.py by scripts/derive_stagnation_supervision_v1.py; edit the derivation, not this file.
"""Stagnation-supervision-only source, compute and one-attempt-per-session reservation gate.

Live mode is disabled in this source revision (LIVE_DISABLED); no review lock, approval, authorization or
reservation exists.

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
REVIEW = 'notebooks/stagnation-supervision-v1-review-r1/review-source-lock.json'
SOURCE = 'reports/stagnation_supervision_v1_source_approval.json'
COMPUTE = 'reports/stagnation_supervision_v1_compute_authorization.json'
EXECUTION = 'research/stagnation_supervision_v1/closed_loop/execution_lock.json'
RESERVATION = 'research/stagnation_supervision_v1/closed_loop/reservation.json'
ATTEMPT_PATTERN = r'ssv1-[A-Za-z0-9-]{8,80}'
LIVE_DISABLED = True  # this source revision cannot launch; a reviewed revision must remove this line explicitly
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


def require(root=ROOT):
    """Fail before installation, subprocess creation, GPU query or model import."""
    if LIVE_DISABLED:
        raise PermissionError('stagnation-supervision-v1 live mode is disabled in this source revision')
    try:
        root = Path(root)
        review = _read(root, REVIEW)
        if (review.get('status') != 'reviewed_launch_source' or review.get('scope') != SCOPE or
                not isinstance(review.get('bindings'), dict) or not REQUIRED_SOURCE <= set(review['bindings'])):
            raise ValueError('launch review source')
        for name, digest in review['bindings'].items():
            if _sha(_path(root, name)) != digest:
                raise ValueError('reviewed source drift: ' + name)
        lock_hash = _sha(_path(root, REVIEW))
        source, compute = _read(root, SOURCE), _read(root, COMPUTE)
        for value, kind in ((source, 'source'), (compute, 'compute')):
            if (value.get('status') != 'approved' or value.get('scope') != SCOPE or
                    value.get('approval_kind') != kind or value.get('review_lock_sha256') != lock_hash or
                    not isinstance(value.get('user_response'), str) or not value['user_response'].strip()):
                raise ValueError(kind + ' approval')
        source_hash = _sha(_path(root, SOURCE))
        if compute.get('source_approval_sha256') != source_hash:
            raise ValueError('compute/source binding')
        execution = _read(root, EXECUTION)
        session = execution.get('session')
        granted_sessions = compute.get('sessions')
        if (type(session) is not str or session not in SESSION_LIMITS or
                type(granted_sessions) is not dict or set(granted_sessions) != {session}):
            raise ValueError('compute must authorize exactly the execution session')
        for name, expected in SESSION_LIMITS[session].items():
            if (type(granted_sessions[session].get(name)) is not int or
                    granted_sessions[session][name] != expected):
                raise ValueError(f'compute limit: session {session} {name}')
        reservation = _read(root, RESERVATION)
        if (execution.get('scope') != SCOPE or execution.get('review_lock_sha256') != lock_hash or
                execution.get('source_approval_sha256') != source_hash or
                execution.get('compute_authorization_sha256') != _sha(_path(root, COMPUTE)) or
                not isinstance(execution.get('attempt_id'), str) or
                not re.fullmatch(ATTEMPT_PATTERN, execution['attempt_id'])):
            raise ValueError('execution binding')
        if (reservation.get('status') != 'reserved' or reservation.get('attempt_id') != execution['attempt_id'] or
                reservation.get('seconds') != SESSION_LIMITS.get(str(execution.get('session')), {}).get('authorized_seconds') or
                reservation.get('execution_sha256') != _sha(_path(root, EXECUTION)) or
                reservation.get('events') != ['reserve']):
            raise ValueError('unconsumed reservation binding')
        return execution
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise PermissionError('stagnation-supervision v1 requires reviewed source, separate compute '
                              'approval and one fresh reservation per session') from exc


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
