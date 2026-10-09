"""The progress_subgoal_v1 questionnaire on the verified direct-publisher runtime (hand-written adapter).

Nothing scientific is defined here. The frozen question set (research/progress_subgoal_v1/probes.json), each
request (research.progress_subgoal_v1.probes.build_request), the call order and the admission and stop rules
(research.progress_subgoal_v1.schedule: admission cutoff, 80-second per-call bound, two consecutive timeouts) are
imported unchanged. This module only sends each scheduled request, in order, through the verified runtime's counted
HTTP client (certification/direct_publisher_smoke_v1/client.py) and retains the raw reply.

As in the reviewed runner it replaces (research/progress_subgoal_v1/runner.py):
- every call is retained as its own atomically written file (`questionnaire/calls/NNNNN.json`), first as an intent
  record before the request is sent, then with its status and, when answered, the raw HTTP reply;
- the runner never scores: research/progress_subgoal_v1_runtime2/evaluate.py re-derives every request and scores only
  the retained replies;
- a call still running at its per-call timeout is torn down (the client closes the socket, which vLLM treats as a
  cancellation) and the server must then be observed idle within the cancellation-verification window; the call is
  then `timed_out` (its answer missing, never scored) and the run continues; a server not observed idle in time is a
  `transport_failure` and stops the run;
- a rejected request, a transport failure or the admission cutoff ends the run with an explicit stop reason;
- an ended run is `incomplete` unless every scheduled call was answered or timed out.

Runtime differences from the reviewed runner (all recorded in derivation.json): idle verification uses counted
`/metrics` reads (request id QIDLE) through the same client; prompt-token parity is checked against the frozen
offline token audit rather than an in-process tokenizer; prefix caching is verified from the server's retained
startup configuration (runtime_controls.verify_cache_disabled), not by per-call counters.
"""
import hashlib
import json
from pathlib import Path
import time

PACKAGE = 'research/progress_subgoal_v1_runtime2'
FROZEN = 'research/progress_subgoal_v1/probes.json'
TOKEN_AUDIT = PACKAGE + '/token-audit.json'
VERSION = 'progress_subgoal_v1_runtime2_questionnaire'
KIND = 'questionnaire'
IDLE_REQUEST = 'QIDLE'
IDLE_KIND = 'questionnaire_idle_check'
# Idle verification after a timed-out call: one /metrics read per second, each bounded to one second, inside the
# frozen 15-second window. A timed-out call spends at least its 60-second timeout of the 3,000-second admission
# window, so at most 50 calls can time out in a session.
IDLE_POLL_SECONDS = 1.0
IDLE_READ_TIMEOUT_SECONDS = 1
IDLE_READS_PER_TIMEOUT = 15
MAX_TIMED_OUT_CALLS = 50
STATUSES = ('answered', 'timed_out', 'transport_failure', 'rejected', 'canceled', 'deadline_expired')


def request_id(n):
    return f'Q{n:05d}'


def load_frozen(root):
    """(frozen question set, its SHA-256), always from the frozen file under `root` (never an override)."""
    raw = (Path(root) / FROZEN).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def scheduled(root):
    """(frozen, probe_set_sha256, [(request_id, phase, pass_id, probe_id, request)]) in the frozen call order."""
    from research.progress_subgoal_v1.probes import build_request
    from research.progress_subgoal_v1.schedule import call_order
    frozen, digest = load_frozen(root)
    contexts = {c['context_id']: c for c in frozen['contexts']}
    probes = {p['probe_id']: p for p in frozen['probes']}
    rows = []
    for n, (phase, pass_id, probe_id) in enumerate(call_order(frozen)):
        probe = probes[probe_id]
        rows.append((request_id(n), phase, pass_id, probe_id, build_request(contexts[probe['context_id']], probe)))
    return frozen, digest, rows


def request_digest(hashes):
    """One digest over every scheduled request hash, in call order."""
    return hashlib.sha256(''.join(h + '\n' for h in hashes).encode()).hexdigest()


def frozen_timing():
    from research.progress_subgoal_v1 import schedule as S
    return {'timeout_seconds': S.PER_CALL_TIMEOUT_SECONDS, 'teardown_seconds': S.TEARDOWN_SECONDS,
            'verify_seconds': S.CANCELLATION_VERIFY_SECONDS, 'margin_seconds': S.BRIDGE_MARGIN_SECONDS}


def bound(timing):
    return (timing['timeout_seconds'] + timing['teardown_seconds'] + timing['verify_seconds']
            + timing['margin_seconds'])


def call_timing(protocol, mode):
    """The per-call timing the run uses. Live: exactly the frozen schedule's values. Rehearsal: inside them."""
    declared = protocol['experiment']['call_timing']
    frozen = frozen_timing()
    if set(declared) != set(frozen) or any(type(v) not in (int, float) or v <= 0 for v in declared.values()):
        raise ValueError('call timing')
    if mode == 'live' and declared != frozen:
        raise PermissionError('live mode uses the frozen per-call timing')
    if any(declared[k] > frozen[k] for k in frozen):
        raise ValueError('rehearsal timing outside the live envelope')
    return dict(declared)


def request_plan(count, timeout_seconds):
    """The counted-request plan entries for the questionnaire (in the protocol's `requests`)."""
    items = [{'id': request_id(n), 'kind': KIND, 'method': 'POST', 'path': '/v1/chat/completions',
              'timeout_seconds': timeout_seconds} for n in range(count)]
    items.append({'id': IDLE_REQUEST, 'kind': IDLE_KIND, 'method': 'GET', 'path': '/metrics',
                  'timeout_seconds': IDLE_READ_TIMEOUT_SECONDS,
                  'max_issues': IDLE_READS_PER_TIMEOUT * MAX_TIMED_OUT_CALLS})
    return items


def token_audit(root):
    return json.loads((Path(root) / TOKEN_AUDIT).read_bytes())


def verify_idle(client, deadline, *, now=time.monotonic, sleep=time.sleep):
    """Counted /metrics reads until nothing is running or waiting, all finished by the absolute `deadline`.

    Returns the measurements; never raises. A read that cannot finish by the deadline is not started, and an
    observation completing after the deadline is rejected (as research/evidence_comprehension_v1/transport.py)."""
    from research.evidence_comprehension_v1.transport import parse_metrics, server_load
    begun = now()
    reads, last, error = 0, None, None
    while reads < IDLE_READS_PER_TIMEOUT and now() + IDLE_READ_TIMEOUT_SECONDS <= deadline:
        reads += 1
        try:
            status, raw = client.call(IDLE_REQUEST)
            observed = now()
            if observed > deadline:
                error = 'observation completed after the deadline'
                break
            if status != 200:
                raise ConnectionError(f'metrics endpoint returned HTTP {status}')
            last, error = server_load(parse_metrics(raw.decode('utf-8', 'replace'))), None
            if last['running'] == 0 and last['waiting'] == 0:
                return {'idle': True, 'waited_seconds': round(observed - begun, 3),
                        'window_seconds': round(deadline - begun, 3), 'reads': reads, **last}
        except Exception as exc:  # a refused or failed read is recorded; the window decides
            error = type(exc).__name__ + ': ' + str(exc)[:160]
        pause = min(IDLE_POLL_SECONDS, deadline - now())
        if pause > 0:
            sleep(pause)
    return {'idle': False, 'waited_seconds': round(now() - begun, 3), 'window_seconds': round(deadline - begun, 3),
            'reads': reads, **(last or {'running': None, 'waiting': None, 'aborted_total': None}), 'error': error}


def completion_content(raw):
    """The transport-level reading of a 200 reply, as the reviewed transport read it: one choice with text content.
    Returns (content, finish_reason, usage) or raises ValueError. Never judges the answer."""
    value = json.loads(raw)
    choice = value['choices'][0]
    content = choice['message']['content']
    if not isinstance(content, str):
        raise ValueError('model server returned no text content')
    return content, choice.get('finish_reason'), value.get('usage') or {}


def run_questionnaire(root, client, evidence, clock, protocol, *, now=time.monotonic, sleep=time.sleep):
    """Run the frozen schedule under the frozen admission and stop rules; retain every call. Never scores.

    `protocol` is the run's protocol: live, the gate-validated frozen protocol; rehearsal, the declared rehearsal
    protocol (shortened limits and timing inside the live envelope)."""
    from certification.direct_publisher_smoke_v1.accounting import RequestRefused
    from certification.direct_publisher_smoke_v1.client import RequestFailed
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1.schedule import Admission, ADMISSION_CUTOFF_SECONDS
    mode = evidence.mode
    experiment = protocol['experiment']
    frozen, probe_set_sha256, rows = scheduled(root)
    if probe_set_sha256 != experiment['probe_set_sha256'] or len(rows) != experiment['scheduled_calls']:
        raise ValueError('frozen question set differs from the protocol')
    timing = call_timing(protocol, mode)
    plan = {item['id']: item for item in protocol['requests']}
    if (any(plan[request_id(n)]['timeout_seconds'] != timing['timeout_seconds'] for n in range(len(rows)))
            or plan[IDLE_REQUEST]['timeout_seconds'] != IDLE_READ_TIMEOUT_SECONDS):
        raise ValueError('request plan timeouts differ from the call timing')
    audit = token_audit(root)
    hashes = [request_hash(row[4]) for row in rows]
    if (audit.get('passed') is not True or audit.get('probe_set_sha256') != probe_set_sha256
            or audit.get('request_digest') != request_digest(hashes) or len(audit['prompt_tokens']) != len(rows)):
        raise ValueError('token audit not bound to the scheduled requests')
    cutoff = clock.limits['admission_cutoff_seconds']
    if mode == 'live' and cutoff != ADMISSION_CUTOFF_SECONDS:
        raise PermissionError('live mode uses the frozen admission cutoff')
    admission = Admission(cutoff, bound(timing))
    index = {'version': VERSION, 'kind': 'target_model_questionnaire' if mode == 'live'
             else 'rehearsal_scripted_stub_questionnaire', 'probe_set_sha256': probe_set_sha256,
             'request_digest': audit['request_digest'], 'scheduled_calls': len(rows), 'cutoff_seconds': cutoff,
             'bound_seconds': bound(timing), 'call_timing': timing, 'status': 'running', 'stop_reason': None,
             'calls_recorded': 0, 'counts': {}, 'phase_reached': None}
    evidence.json('questionnaire/run.json', index)
    for n, (qid, phase, pass_id, probe_id, request) in enumerate(rows):
        if not admission.may_start(clock.elapsed()):
            index['stop_reason'] = admission.stopped
            break
        record = {'index': n, 'request_id': qid, 'phase': phase, 'pass_id': pass_id, 'probe_id': probe_id,
                  'request_sha256': hashes[n], 'audit_prompt_tokens': audit['prompt_tokens'][n],
                  'started_at': round(clock.elapsed(), 6), 'status': 'intent'}
        evidence.json(f'questionnaire/calls/{n:05d}.json', record)
        begun = now()
        try:
            status, raw = client.call(qid, request)
        except RequestRefused as exc:
            record.update(status='rejected', error=str(exc)[:300])
        except RequestFailed as exc:
            torn_down = now()
            if torn_down >= begun + timing['timeout_seconds']:
                # The call reached its per-call timeout and its connection was closed: verify the server idle.
                deadline = begun + timing['timeout_seconds'] + timing['teardown_seconds'] + timing['verify_seconds']
                idle = verify_idle(client, deadline, now=now, sleep=sleep)
                ended = now()
                record.update(status='timed_out' if idle['idle'] else 'transport_failure', error=str(exc)[:300],
                              idle_verification=idle,
                              cancellation_timing={'torn_down_after_seconds': round(torn_down - begun, 6),
                                                   'ended_after_seconds': round(ended - begun, 6),
                                                   'inference_deadline_after_seconds': timing['timeout_seconds'],
                                                   'verify_deadline_after_seconds': round(deadline - begun, 6)})
                if not idle['idle']:
                    record['error'] = 'server not observed idle in time after a timed-out call'
            else:
                record.update(status='transport_failure', error=str(exc)[:300])
        else:
            record.update(http_status=status, response_sha256=hashlib.sha256(raw).hexdigest())
            try:
                record['response'] = raw.decode('utf-8')
                if status != 200:
                    raise ConnectionError(f'model server returned HTTP {status}')
                completion_content(record['response'])
                record['status'] = 'answered'
            except Exception as exc:
                record.update(status='transport_failure', error=type(exc).__name__ + ': ' + str(exc)[:200])
        record['returned_at'] = round(clock.elapsed(), 6)
        evidence.json(f'questionnaire/calls/{n:05d}.json', record)
        index['calls_recorded'] = n + 1
        index['counts'][record['status']] = index['counts'].get(record['status'], 0) + 1
        index['phase_reached'] = phase
        admission.record(record['status'])
        if admission.stopped:
            index['stop_reason'] = admission.stopped
            break
    index['status'] = ('complete' if index['calls_recorded'] == len(rows) and not index['stop_reason']
                       else 'incomplete')
    evidence.json('questionnaire/run.json', index)
    # As the reviewed worker: a complete run, or one stopped only at the admission cutoff, is a reported result
    # (the independent evaluator decides completeness); any other stop is a lifecycle failure.
    if index['status'] != 'complete' and index['stop_reason'] != 'admission_cutoff':
        raise RuntimeError('questionnaire run stopped: ' + str(index['stop_reason']))
    return {k: index[k] for k in ('status', 'stop_reason', 'calls_recorded', 'scheduled_calls', 'counts',
                                  'phase_reached', 'probe_set_sha256')}
