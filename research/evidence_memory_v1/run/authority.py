# Derived from research/ws3_questionnaire_v1/authority.py by research/evidence_memory_v1/derive_run.py; edit the derivation, not this file.
"""Evidence-comprehension-only source, compute and one-attempt reservation gate.

A review snapshot alone never authorizes a live run. Separate source approval, compute
authorization, and an unconsumed reservation bound to the exact review lock are required.
"""
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
SCOPE = 'evidence-memory-v1-stage1'
REVIEW = 'notebooks/evidence-memory-v1-stage1-review-r1/review-source-lock.json'
SOURCE = 'reports/evidence_memory_v1_stage1_source_approval.json'
COMPUTE = 'reports/evidence_memory_v1_stage1_compute_authorization.json'
EXECUTION = 'research/evidence_memory_v1/run/execution_lock.json'
RESERVATION = 'research/evidence_memory_v1/run/reservation.json'
ATTEMPT_PATTERN = r'em1s-[A-Za-z0-9-]{8,80}'
LIMITS = {'authorized_seconds': 3600, 'internal_seconds': 3300, 'maximum_attempts': 1,
          'maximum_questionnaire_calls': 2896, 'maximum_canaries': 1, 'per_call_timeout_seconds': 60,
          'game_actions': 0, 'automatic_retries': 0, 'scored_submissions': 0,
          'holdout_runs': 0}
LIVE_ENABLED = False  # Track 2 Stage 1: GPU-disabled; no live run is approved
REQUIRED_SOURCE = {'research/evidence_memory_v1/run/' + name for name in
                   ('__init__.py', 'authority.py', 'probes.py', 'probes.json', 'score.py', 'schedule.py',
                    'transport.py', 'service.py', 'host.py', 'worker.py', 'runner.py', 'monitor.py', 'resources.py',
                    'supervisor.py', 'evidence.py', 'fake_server.py', 'evaluate.py')}
REQUIRED_SOURCE |= {'research/evidence_memory_v1/' + name for name in  # the Stage 1 question set and its scorer
                    ('__init__.py', 'stage1.py', 'protocol.py', 'readers.py', 'render.py', 'schema.py', 'fidelity.py',
                     'trajectories.py', 'writers.py', 'tokens.py')}
REQUIRED_SOURCE |= {'research/transition_evidence_v2/' + name for name in ('transition.py', 'vocabulary.py')}
REQUIRED_SOURCE |= {'research/transition_evidence_v1/' + name for name in ('transition.py', 'vocabulary.py')}
REQUIRED_SOURCE |= {'research/ws3_questionnaire_v1/evidence.py'}  # WS3's committed-state recovery, re-exported
REQUIRED_SOURCE |= {'research/evidence_comprehension_v2/' + name for name in  # v2's modules, reused unchanged
                    ('score.py', 'evidence.py', 'schedule.py', 'fake_server.py')}
REQUIRED_SOURCE |= {'research/evidence_comprehension_v1/' + name for name in  # v1's modules, reused unchanged
                    ('probes.py', 'probes.json', 'score.py', 'schedule.py', 'transport.py', 'service.py',
                     'evidence.py', 'fake_server.py')}
REQUIRED_SOURCE |= {'research/action_effect_v1/records.py', 'research/action_effect_history_v1/contract.py',
                    'research/action_effect_history_v1/service.py', 'research/action_effect_history_v1/rehearsal.py',
                    'research/evidence_memory_v1/run/launch.py', 'reports/m0_profiles/m0-q3vl30-instruct.json',
                    'config/operational_primary.yaml', 'config/m0_launch_spec_q3vl30.json'}


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
        if not LIVE_ENABLED:  # GPU-disabled package: refuse before reading any approval or touching a GPU
            raise ValueError('Stage 1 has no approved live run')
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
        for name, expected in LIMITS.items():
            if type(compute.get(name)) is not int or compute[name] != expected:
                raise ValueError('compute limit: ' + name)
        execution, reservation = _read(root, EXECUTION), _read(root, RESERVATION)
        if (execution.get('scope') != SCOPE or execution.get('review_lock_sha256') != lock_hash or
                execution.get('source_approval_sha256') != source_hash or
                execution.get('compute_authorization_sha256') != _sha(_path(root, COMPUTE)) or
                not isinstance(execution.get('attempt_id'), str) or
                not re.fullmatch(ATTEMPT_PATTERN, execution['attempt_id'])):
            raise ValueError('execution binding')
        if (reservation.get('status') != 'reserved' or reservation.get('attempt_id') != execution['attempt_id'] or
                reservation.get('seconds') != LIMITS['authorized_seconds'] or
                reservation.get('execution_sha256') != _sha(_path(root, EXECUTION)) or
                reservation.get('events') != ['reserve']):
            raise ValueError('unconsumed reservation binding')
        return execution
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise PermissionError('evidence memory v1 stage 1 requires reviewed source, separate compute '
                              'approval and one fresh reservation') from exc


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
    if os.environ.get('EM1S_REHEARSAL') != '1' or os.environ.get('CUDA_VISIBLE_DEVICES', '') != '':
        raise PermissionError('rehearsal mode requires EM1S_REHEARSAL=1 and no visible GPU')
    return {'mode': 'rehearsal', 'attempt_id': None}
