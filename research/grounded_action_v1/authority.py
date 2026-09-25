"""Stage B-only source, compute and one-attempt reservation gate.

The current review snapshot alone cannot authorize a live run. Separate
source approval, compute authorization, and an unconsumed reservation are
required for each revision.
"""
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SCOPE = 'phase4-grounded-action-stage-b-live-r8'
REVIEW = 'notebooks/phase4-grounded-action-v1-launch-r11/review-source-lock.json'
SOURCE = 'reports/perception_stage_b_r8_source_approval.json'
COMPUTE = 'reports/perception_stage_b_r8_compute_authorization.json'
EXECUTION = 'research/grounded_action_v1/execution_lock_r8.json'
RESERVATION = 'research/grounded_action_v1/reservation_r8.json'
LIMITS = {'authorized_seconds': 3600, 'internal_seconds': 3300,
          'maximum_attempts': 1, 'maximum_study_calls': 12,
          'maximum_total_completions': 13, 'maximum_episodes': 2,
          'maximum_actions_per_episode': 2, 'automatic_retries': 0,
          'scored_submissions': 0}
REQUIRED_SOURCE = {
    'research/grounded_action_v1/' + name for name in
    ('authority.py', 'bridge_service.py', 'target_host.py', 'target_monitor.py',
     'target_resources.py', 'target_worker.py', 'target_supervisor.py',
     'model_service.py', 'engine.py', 'local.py', 'replay.py', 'contract.py')}
REQUIRED_SOURCE |= {'scripts/phase4_grounded_action_v1_launch.py',
                    'reports/perception_stage_b_v1_case_protocol.json',
                    'reports/m0_profiles/m0-q3vl30-instruct.json',
                    'config/operational_primary.yaml'}


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
    try:
        root = Path(root)
        review = _read(root, REVIEW)
        if (review.get('status') != 'reviewed_launch_source' or
                review.get('scope') != SCOPE or
                not isinstance(review.get('bindings'), dict) or
                not REQUIRED_SOURCE <= set(review['bindings'])):
            raise ValueError('launch review source')
        for name, digest in review['bindings'].items():
            if _sha(_path(root, name)) != digest:
                raise ValueError('reviewed source drift: ' + name)
        lock_hash = _sha(_path(root, REVIEW))
        source, compute = _read(root, SOURCE), _read(root, COMPUTE)
        for value, kind in ((source, 'source'), (compute, 'compute')):
            if (value.get('status') != 'approved' or value.get('scope') != SCOPE or
                    value.get('approval_kind') != kind or
                    value.get('review_lock_sha256') != lock_hash or
                    not isinstance(value.get('user_response'), str) or
                    not value['user_response'].strip()):
                raise ValueError(kind + ' approval')
        source_hash = _sha(_path(root, SOURCE))
        if compute.get('source_approval_sha256') != source_hash:
            raise ValueError('compute/source binding')
        for name, expected in LIMITS.items():
            if type(compute.get(name)) is not int or compute[name] != expected:
                raise ValueError('compute limit: ' + name)
        execution, reservation = _read(root, EXECUTION), _read(root, RESERVATION)
        if (execution.get('scope') != SCOPE or execution.get('review_lock_sha256') != lock_hash or
                execution.get('source_approval_sha256') != source_hash or
                execution.get('compute_authorization_sha256') != _sha(_path(root, COMPUTE)) or
                not isinstance(execution.get('attempt_id'), str) or
                not re.fullmatch(r'gab1-[A-Za-z0-9-]{8,80}', execution['attempt_id'])):
            raise ValueError('execution binding')
        if (reservation.get('status') != 'reserved' or
                reservation.get('attempt_id') != execution['attempt_id'] or
                reservation.get('seconds') != LIMITS['authorized_seconds'] or
                reservation.get('execution_sha256') != _sha(_path(root, EXECUTION)) or
                reservation.get('events') != ['reserve']):
            raise ValueError('unconsumed reservation binding')
        return execution
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise PermissionError('Stage B requires reviewed source, separate compute approval and one fresh reservation') from exc


def consume_runtime(working, root=ROOT):
    """Persist one-use claim before target side effects; never retry on conflict."""
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
        raise PermissionError('Stage B runtime claim missing')
    if json.loads(marker.read_bytes()) != {'status': 'consumed', 'attempt_id': execution['attempt_id']}:
        raise PermissionError('Stage B runtime claim mismatch')
    return marker
