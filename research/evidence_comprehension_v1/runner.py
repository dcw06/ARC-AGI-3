"""Questionnaire runner (worker interpreter): the frozen call order under admission control.

Every call is retained as its own atomically written file (`calls/NNNNN.json`) with its status and,
when answered, the raw response. The runner never scores: the independent evaluator re-derives
every request and scores only the retained responses. A timeout leaves the answer missing; a
rejected request, transport failure, service stop, storage limit, cancellation or the admission
cutoff ends the run with an explicit stop reason. An ended run is `incomplete` unless every
scheduled call was answered or timed out.
"""
from pathlib import Path
import time

from .evidence import RunEvidence, StorageExhausted
from .probes import build_request, load_frozen
from .schedule import Admission, call_order, ADMISSION_CUTOFF_SECONDS, PER_CALL_BOUND_SECONDS

VERSION = 'evidence_comprehension_v1_run'
INDEX_RESERVE_BYTES = 8192  # the run index stays well under this


def classify(exc):
    """Map a bridge error to a call status. The model host reports errors as 'Type: message'."""
    text = str(exc)
    if text.startswith('CallCancelled:'):
        return 'timed_out'
    if text.startswith('ValueError: request not in the frozen probe set') or text.startswith('ValueError: questionnaire call ceiling'):
        return 'rejected'
    return 'transport_failure'


def run(path, service, *, started, kind, cutoff_seconds=ADMISSION_CUTOFF_SECONDS, bound_seconds=PER_CALL_BOUND_SECONDS,
        evidence_budget_bytes=32 * 1024**2, cancel=None, evidence_lock_root=None, clock=time.monotonic):
    from research.action_effect_history_v1.service import request_hash
    path = Path(path)
    frozen, probe_set_sha256 = load_frozen()
    contexts = {c['context_id']: c for c in frozen['contexts']}
    probes = {p['probe_id']: p for p in frozen['probes']}
    order = call_order(frozen['probes'])
    writer = RunEvidence(path, evidence_budget_bytes, evidence_lock_root)
    admission = Admission(cutoff_seconds, bound_seconds)
    index = {'version': VERSION, 'kind': kind, 'probe_set_sha256': probe_set_sha256, 'scheduled_calls': len(order),
             'cutoff_seconds': cutoff_seconds, 'bound_seconds': bound_seconds, 'status': 'running',
             'stop_reason': None, 'calls_recorded': 0, 'counts': {}, 'phase_reached': None}

    def save_index():
        writer(path / 'run.json', index)

    try:
        save_index()
        for n, (phase, pass_id, probe_id) in enumerate(order):
            if cancel is not None and Path(cancel).exists():
                index['stop_reason'] = 'canceled'
                break
            if not admission.may_start(clock() - started):
                index['stop_reason'] = admission.stopped
                break
            probe = probes[probe_id]
            request = build_request(contexts[probe['context_id']], probe)
            call_started = clock()
            record = {'index': n, 'phase': phase, 'pass_id': pass_id, 'probe_id': probe_id,
                      'request_sha256': request_hash(request), 'started_at': round(call_started - started, 6)}
            try:
                # The reply must arrive within the call's whole bound; a later reply is rejected by the proxy.
                result = service.complete(request, deadline=call_started + bound_seconds)
                record.update(status='answered', response=result['content'],
                              tokenizer_prompt_tokens=result['tokenizer_prompt_tokens'],
                              server_prompt_tokens=result['server_prompt_tokens'],
                              server_completion_tokens=result['server_completion_tokens'],
                              finish_reason=result['finish_reason'], cache_check=result.get('cache_check'),
                              host_timing=result.get('host_timing'))
            except Exception as exc:
                record.update(status=classify(exc), error=str(exc)[:300])
            record['returned_at'] = round(clock() - started, 6)
            writer(path / f'calls/{n:05d}.json', record, reserve_bytes=INDEX_RESERVE_BYTES)
            index['calls_recorded'] = n + 1
            index['counts'][record['status']] = index['counts'].get(record['status'], 0) + 1
            index['phase_reached'] = phase
            save_index()
            admission.record(record['status'])
            if admission.stopped:
                index['stop_reason'] = admission.stopped
                break
        index['status'] = 'complete' if index['calls_recorded'] == len(order) and not index['stop_reason'] else 'incomplete'
    except StorageExhausted as exc:
        # The failed write reserved room for this final index, so the retained evidence stays consistent.
        index.update(status='incomplete', stop_reason='storage_exhausted', evidence_error=str(exc)[:200])
    try:
        save_index()
    except StorageExhausted as exc:
        index.update(status='incomplete', stop_reason='storage_exhausted', evidence_error=str(exc)[:200])
    return index


def load(path):
    from .evidence import load_verified
    return load_verified(path)

