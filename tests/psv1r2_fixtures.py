"""Test fixtures for the progress_subgoal_v1 runtime2 package: a declared rehearsal protocol and synthetic, internally
consistent evidence folders written without HTTP (scripted answers only; never model evidence)."""
import copy
import functools
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVED = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'


@functools.lru_cache(maxsize=1)
def frozen_protocol():
    from research.progress_subgoal_v1_runtime2.binding import load_protocol
    return load_protocol(ROOT)


def declared_protocol():
    """The frozen protocol with the rehearsal limits and timing (as rehearsal.declared_protocol sets them)."""
    from research.progress_subgoal_v1_runtime2 import questionnaire as QN, rehearsal as R
    protocol = copy.deepcopy(frozen_protocol())
    protocol['limits'].update(R.LIMITS)
    protocol['experiment']['call_timing'] = dict(R.TIMING)
    for item in protocol['requests']:
        item['timeout_seconds'] = (R.TIMING['timeout_seconds'] if item['kind'] == QN.KIND
                                   else QN.IDLE_READ_TIMEOUT_SECONDS if item['kind'] == QN.IDLE_KIND else 5)
    return protocol


@functools.lru_cache(maxsize=1)
def schedule():
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1_runtime2 import questionnaire as QN
    frozen, digest, rows = QN.scheduled(ROOT)
    return frozen, digest, rows, [request_hash(r[4]) for r in rows], QN.token_audit(ROOT)


@functools.lru_cache(maxsize=2)
def scripted_contents(policy='scripted'):
    """(content, finish_reason) per scheduled call, in order, from the stub's scripted rule."""
    from research.progress_subgoal_v1.fake_server import TRUNCATED, ScriptedAnswers
    frozen, _, rows, _, _ = schedule()
    probes = {p['probe_id']: p for p in frozen['probes']}
    answers, out = ScriptedAnswers(), []
    for _, _, _, probe_id, request in rows:
        content = (json.dumps({'answer': probes[probe_id]['key']}) if policy == 'oracle'
                   else answers(json.loads(json.dumps(request))))
        finish = 'stop'
        if content.startswith(TRUNCATED):
            content, finish = content[len(TRUNCATED):], 'length'
        out.append((content, finish))
    return tuple(out)


def reply(content, finish, prompt_tokens, completion=None, model=SERVED):
    completion = completion if completion is not None else (32 if finish == 'length' else max(1, min(31, len(content) // 3)))
    return json.dumps({'model': model, 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': content},
                                                    'finish_reason': finish}],
                       'usage': {'prompt_tokens': prompt_tokens, 'completion_tokens': completion}})


def put(folder, name, value):
    path = Path(folder) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=1, sort_keys=True, default=str) + '\n').encode())


def finalize(folder):
    folder = Path(folder)
    files = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(folder.rglob('*')) if p.is_file() and p.name != 'evidence-manifest.json'}
    put(folder, 'evidence-manifest.json', {'files': files})


def write_evidence(folder, protocol, *, policy='scripted', count=None, stop_reason=None, records_hook=None,
                   manifest=True, result_hook=None):
    """A consistent evidence folder for the first `count` scheduled calls (all answered unless a hook changes them)."""
    from research.progress_subgoal_v1_runtime2 import questionnaire as QN
    folder = Path(folder)
    frozen, digest, rows, hashes, audit = schedule()
    contents = scripted_contents(policy)
    count = len(rows) if count is None else count
    timing = protocol['experiment']['call_timing']
    records, t = [], 10.0
    for n in range(count):
        qid, phase, pass_id, probe_id, _ = rows[n]
        content, finish = contents[n]
        raw = reply(content, finish, audit['prompt_tokens'][n])
        records.append({'index': n, 'request_id': qid, 'phase': phase, 'pass_id': pass_id, 'probe_id': probe_id,
                        'request_sha256': hashes[n], 'audit_prompt_tokens': audit['prompt_tokens'][n],
                        'started_at': round(t, 6), 'status': 'answered', 'http_status': 200, 'response': raw,
                        'response_sha256': hashlib.sha256(raw.encode()).hexdigest(), 'returned_at': round(t + 0.01, 6)})
        t += 0.02
    if records_hook:
        records = records_hook(records)
    counts = {}
    for r in records:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    complete = len(records) == len(rows) and set(counts) <= {'answered', 'timed_out'} and not stop_reason
    index = {'version': QN.VERSION, 'kind': 'rehearsal_scripted_stub_questionnaire', 'probe_set_sha256': digest,
             'request_digest': audit['request_digest'], 'scheduled_calls': len(rows),
             'cutoff_seconds': protocol['limits']['admission_cutoff_seconds'], 'bound_seconds': QN.bound(timing),
             'call_timing': timing, 'status': 'complete' if complete else 'incomplete', 'stop_reason': stop_reason,
             'calls_recorded': len(records), 'counts': counts, 'phase_reached': records[-1]['phase'] if records else None}
    put(folder, 'questionnaire/run.json', index)
    for r in records:
        put(folder, f"questionnaire/calls/{r['index']:05d}.json", r)
    plan = {item['id']: item for item in protocol['requests']}
    entries = [{'id': i, 'kind': plan[i]['kind'], 'method': plan[i]['method'], 'path': plan[i]['path'],
                'outcome': 'http_200'} for i in ('S1', 'S2', 'S3', 'I1', 'I2', 'I3', 'I4')]
    for r in records:
        if r['status'] != 'rejected':
            entries.append({'id': r['request_id'], 'kind': 'questionnaire', 'method': 'POST',
                            'path': '/v1/chat/completions', 'outcome': 'http_200'})
        for _ in range((r.get('idle_verification') or {}).get('reads', 0)):
            entries.append({'id': 'QIDLE', 'kind': 'questionnaire_idle_check', 'method': 'GET', 'path': '/metrics',
                            'outcome': 'http_200'})
    entries += [{'id': i, 'kind': 'cancellation_probe', 'method': plan[i]['method'], 'path': plan[i]['path'],
                 'outcome': 'http_200'} for i in ('C1', 'C2', 'C3')]
    for n, e in enumerate(entries):
        e.update(sequence=n + 1, issued_at=round(1 + n * 0.001, 3))
    result = {'mode': 'rehearsal', 'evidence_class': 'scripted_cpu_rehearsal', 'passed': True,
              'verdict_status': 'passed', 'failed_stage': None, 'error': None, 'cleanup_verified': True,
              'cleanup': {'groups_absent': True, 'gpu': 'not_exercised (no GPU in a CPU rehearsal)'},
              'lifecycle_deadline': {'met': True}, 'limits': protocol['limits'], 'elapsed_seconds': t + 5,
              'stages': {'cache_config': {'disabled': True, 'matches': 1}}, 'completed_plan': True,
              'ledger': {'maximum_model_requests': protocol['limits']['maximum_model_requests'],
                         'issued': len(entries), 'entries': entries, 'refusals': []},
              'gpu_compatibility_evidence': False}
    if result_hook:
        result = result_hook(result)
    put(folder, 'result.json', result)
    if manifest:
        finalize(folder)
    return folder
