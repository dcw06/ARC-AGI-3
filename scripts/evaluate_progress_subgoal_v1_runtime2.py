"""Independent evaluation of a retained progress_subgoal_v1 evidence folder from the verified runtime (read-only;
no model, no GPU, no provider).

Nothing the run concluded is trusted. The evaluator:
- verifies every retained file against the evidence manifest (an unfinalized folder is never complete);
- checks the lifecycle verdict, cleanup, final deadline and limits against the declared (frozen) protocol, never
  against values claimed by the evidence;
- re-derives the call order and every request from the frozen question set with the unchanged modules
  (research.progress_subgoal_v1.probes / schedule) and requires the retained calls to be exactly a prefix of that
  order, each started and returned inside the frozen admission cutoff and per-call bound;
- re-reads each raw HTTP reply itself (served model, one choice, finish reason, token usage within the 32-token cap,
  prompt tokens equal to the frozen offline token audit) and recomputes every timeout's idle verdict from its
  measurements;
- scores only the retained replies with the unchanged scorer (research/progress_subgoal_v1/score.py, through the
  unchanged rule research.progress_subgoal_v1.evaluate_run.score_call: a `length` finish is always invalid) and
  analyses the decision partition by identified pass, so missing answers or passes stay `incomplete`.

Usage: python scripts/evaluate_progress_subgoal_v1_runtime2.py OUTPUT
(a rehearsal is evaluated with its harness-declared protocol; see research/progress_subgoal_v1_runtime2/rehearsal.py)
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ADMISSION_SLACK_SECONDS = 0.5  # stamps are taken just after admission and just after the reply or its rejection
FINISH_REASONS = ('stop', 'length')
STOP_STATUSES = ('transport_failure', 'rejected', 'canceled', 'deadline_expired')
MAX_PROMPT_TOKENS = 60000


def finite(value, low=None, high=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        return False
    return (low is None or value >= low) and (high is None or value <= high)


def whole(value, low, high):
    return type(value) is int and low <= value <= high


def read_json(folder, name, limit=64 * 1024**2):
    path = Path(folder) / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError('missing or oversized evidence: ' + name)
    return json.loads(path.read_bytes())


def manifest_errors(folder):
    """Every retained file must be listed with its SHA-256; nothing may be missing, extra or partial."""
    folder = Path(folder)
    try:
        listed = read_json(folder, 'evidence-manifest.json')['files']
    except Exception as exc:
        return ['evidence manifest: ' + type(exc).__name__ + ': ' + str(exc)[:120]]
    errors = []
    present = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    present.discard('evidence-manifest.json')
    if set(listed) != present:
        errors.append(f'manifest inventory differs: missing {sorted(set(listed) - present)[:3]}, '
                      f'unlisted {sorted(present - set(listed))[:3]}')
    for name, digest in sorted(listed.items()):
        path = folder / name
        if name in present and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append('manifest hash differs: ' + name)
    return errors


def declared_protocol(mode, root=ROOT, protocol=None):
    """Live: the frozen protocol (validated). Rehearsal: the harness-declared rehearsal protocol, passed in."""
    if mode == 'live':
        from research.progress_subgoal_v1_runtime2.binding import load_protocol
        return load_protocol(root)
    if mode == 'rehearsal' and isinstance(protocol, dict):
        return protocol
    raise ValueError('rehearsal evaluation needs the harness-declared protocol')


def lifecycle_errors(result, mode, protocol):
    from research.progress_subgoal_v1_runtime2.evidence import evidence_class
    errors = []
    if result.get('mode') != mode or result.get('evidence_class') != evidence_class(mode):
        errors.append('mode or evidence class differs')
    if result.get('passed') is not True or result.get('verdict_status') != 'passed':
        errors.append('lifecycle verdict: ' + str(result.get('failed_stage')) + ': ' + str(result.get('error'))[:160])
    if result.get('cleanup_verified') is not True or (result.get('cleanup') or {}).get('groups_absent') is not True:
        errors.append('process cleanup not verified')
    if mode == 'live' and ((result.get('cleanup') or {}).get('gpu') or {}).get('gpu_cleanup_verified') is not True:
        errors.append('GPU cleanup not verified')
    if (result.get('lifecycle_deadline') or {}).get('met') is not True:
        errors.append('final lifecycle deadline not met')
    if result.get('limits') != protocol['limits']:
        errors.append('reported limits differ from the declared protocol')
    elapsed = result.get('elapsed_seconds')
    if not finite(elapsed, 0, protocol['limits']['internal_seconds']):
        errors.append('elapsed time outside the internal limit')
    cache = (result.get('stages') or {}).get('cache_config')
    if not isinstance(cache, dict) or cache.get('disabled') is not True:
        errors.append('prefix caching not shown disabled in the retained server configuration')
    if result.get('completed_plan') is not True:
        errors.append('the frozen request plan did not complete')
    return errors


def ledger_errors(result, protocol, records):
    """The counted-request ledger against the declared plan and the retained calls."""
    errors = []
    ledger = result.get('ledger') or {}
    plan = {item['id']: item for item in protocol['requests']}
    entries = ledger.get('entries') or []
    if ledger.get('maximum_model_requests') != protocol['limits']['maximum_model_requests']:
        errors.append('ledger cap differs from the declared limit')
    if len(entries) > protocol['limits']['maximum_model_requests'] or ledger.get('issued') != len(entries):
        errors.append('ledger count exceeds the cap or is inconsistent')
    issued = {}
    for entry in entries:
        item = plan.get(entry.get('id'))
        if item is None:
            errors.append('unplanned request in the ledger: ' + str(entry.get('id')))
            continue
        issued[entry['id']] = issued.get(entry['id'], 0) + 1
        if issued[entry['id']] > item.get('max_issues', 1):
            errors.append('request issued more often than planned: ' + entry['id'])
    questionnaire = [e['id'] for e in entries if (plan.get(e.get('id')) or {}).get('kind') == 'questionnaire']
    expected = [r['request_id'] for r in records if r.get('status') != 'rejected']
    if questionnaire != expected:
        errors.append('ledger questionnaire requests differ from the retained calls')
    idle_reads = sum((r.get('idle_verification') or {}).get('reads', 0) for r in records)
    if issued.get('QIDLE', 0) != idle_reads:
        errors.append('ledger idle-check reads differ from the retained idle verifications')
    return errors


def answered_errors(n, record, probe, audit_tokens, served):
    from research.progress_subgoal_v1.probes import MAX_TOKENS
    errors = []
    raw = record.get('response')
    if record.get('http_status') != 200 or not isinstance(raw, str):
        return [f'call {n}: answered without an HTTP 200 text reply'], None
    if hashlib.sha256(raw.encode('utf-8')).hexdigest() != record.get('response_sha256'):
        return [f'call {n}: reply differs from its retained hash'], None
    try:
        value = json.loads(raw)
        choices = value.get('choices') if isinstance(value, dict) else None
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise ValueError('not exactly one choice')
        content = (choices[0].get('message') or {}).get('content')
        finish = choices[0].get('finish_reason')
        usage = value.get('usage') or {}
        if not isinstance(content, str):
            raise ValueError('no text content')
    except (ValueError, AttributeError, TypeError) as exc:
        return [f'call {n}: malformed reply ({str(exc)[:80]})'], None
    cap = MAX_TOKENS[probe['family']]
    prompt, completion = usage.get('prompt_tokens'), usage.get('completion_tokens')
    if value.get('model') != served:
        errors.append(f'call {n}: reply names another served model')
    if not whole(prompt, 1, MAX_PROMPT_TOKENS) or prompt != audit_tokens:
        errors.append(f'call {n}: prompt tokens missing, out of bounds or different from the frozen token audit')
    if not whole(completion, 1, cap):
        errors.append(f'call {n}: completion tokens missing or outside 1..{cap}')
    if finish not in FINISH_REASONS:
        errors.append(f'call {n}: finish reason missing or not stop/length')
    elif finish == 'length' and completion != cap:
        errors.append(f'call {n}: length finish without reaching the token cap')
    return errors, {'finish_reason': finish, 'response': content}


def timed_out_errors(n, record, timing):
    """Recompute a timeout's verdict from its own measurements; never trust a recorded flag."""
    errors = []
    t = record.get('cancellation_timing') or {}
    idle = record.get('idle_verification') or {}
    verify_deadline = timing['timeout_seconds'] + timing['teardown_seconds'] + timing['verify_seconds']
    torn = t.get('torn_down_after_seconds')
    if not (finite(torn, timing['timeout_seconds'], timing['timeout_seconds'] + timing['teardown_seconds'])
            and finite(t.get('ended_after_seconds'), torn, verify_deadline + ADMISSION_SLACK_SECONDS)
            and t.get('inference_deadline_after_seconds') == timing['timeout_seconds']
            and finite(t.get('verify_deadline_after_seconds'))
            and abs(t['verify_deadline_after_seconds'] - verify_deadline) < 1e-3):
        errors.append(f'call {n}: cancellation timing outside the frozen deadlines')
    window = idle.get('window_seconds')
    if not (idle.get('running') == 0 and idle.get('waiting') == 0
            and type(idle.get('running')) in (int, float) and type(idle.get('waiting')) in (int, float)
            and finite(window, 0, timing['verify_seconds'] + timing['teardown_seconds'] + ADMISSION_SLACK_SECONDS)
            and finite(idle.get('waited_seconds'), 0, window)):
        errors.append(f'call {n}: server not shown idle within the window by its own measurements')
    return errors


def call_errors(records, rows, audit, index, timing, cutoff, served):
    """Bind the retained calls to the frozen order and requests; returns (errors, counts, answered)."""
    from research.action_effect_history_v1.service import request_hash
    errors, counts, answered = [], {}, {}
    probes = rows['probes']
    previous_returned = 0.0
    total_bound = (timing['timeout_seconds'] + timing['teardown_seconds'] + timing['verify_seconds']
                   + timing['margin_seconds'])
    for n, record in enumerate(records):
        qid, phase, pass_id, probe_id, request = rows['schedule'][n]
        if (record.get('index'), record.get('request_id'), record.get('phase'), record.get('pass_id'),
                record.get('probe_id')) != (n, qid, phase, pass_id, probe_id):
            errors.append(f'call {n}: not the scheduled call')
            continue
        if record.get('request_sha256') != request_hash(request):
            errors.append(f'call {n}: request hash differs from the frozen request')
        if record.get('audit_prompt_tokens') != audit['prompt_tokens'][n]:
            errors.append(f'call {n}: audit tokens differ from the frozen token audit')
        started, returned = record.get('started_at'), record.get('returned_at')
        if not (finite(started, previous_returned) and finite(returned, started)):
            errors.append(f'call {n}: timestamps missing, out of order or overlapping the previous call')
        else:
            if started + total_bound > cutoff + ADMISSION_SLACK_SECONDS:
                errors.append(f'call {n}: started after admission was closed')
            if returned - started > total_bound + ADMISSION_SLACK_SECONDS or returned > cutoff + ADMISSION_SLACK_SECONDS:
                errors.append(f'call {n}: returned outside its bound or after the cutoff')
            previous_returned = returned
        status = record.get('status')
        counts[status] = counts.get(status, 0) + 1
        if status == 'answered':
            found, reply = answered_errors(n, record, probes[probe_id], audit['prompt_tokens'][n], served)
            errors.extend(found)
            if reply is not None:
                answered[n] = reply
        elif status == 'timed_out':
            errors.extend(timed_out_errors(n, record, timing))
        elif status in STOP_STATUSES:
            if n != len(records) - 1:
                errors.append(f'call {n}: a stopping status is not the last retained call')
        else:
            errors.append(f'call {n}: status {status!r} is not a final call status (interrupted call)')
    recorded_counts = index.get('counts') if isinstance(index, dict) else None
    if recorded_counts != counts or index.get('calls_recorded') != len(records):
        errors.append('run index counts differ from the retained calls')
    return errors, counts, answered


def load_records(folder, scheduled_calls):
    calls = Path(folder) / 'questionnaire/calls'
    names = sorted(p.name for p in calls.iterdir()) if calls.is_dir() else []
    expected = [f'{n:05d}.json' for n in range(len(names))]
    if names != expected or len(names) > scheduled_calls:
        raise ValueError('retained calls are not a contiguous prefix of the schedule')
    return [read_json(calls, name, 4 * 1024**2) for name in names]


def evaluate_output(folder, *, mode='live', root=ROOT, protocol=None):
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1.evaluate_run import score_call  # the unchanged scoring rule
    from research.progress_subgoal_v1.score import analyze
    from research.progress_subgoal_v1_runtime2 import questionnaire as QN
    folder = Path(folder)
    protocol = declared_protocol(mode, root, protocol)
    experiment = protocol['experiment']
    timing = QN.call_timing(protocol, mode)
    cutoff = protocol['limits']['admission_cutoff_seconds']
    served = protocol['server']['served_model_name']
    frozen, probe_set_sha256, schedule = QN.scheduled(root)
    audit = QN.token_audit(root)
    hashes = [request_hash(row[4]) for row in schedule]
    binding = []
    if probe_set_sha256 != experiment['probe_set_sha256'] or audit.get('probe_set_sha256') != probe_set_sha256:
        binding.append('frozen question set differs from the protocol or token audit')
    if audit.get('request_digest') != QN.request_digest(hashes) or len(audit.get('prompt_tokens', [])) != len(schedule):
        binding.append('token audit not bound to the scheduled requests')
    manifest = manifest_errors(folder)
    lifecycle, ledger, calls, run_summary, analysis = list(binding), [], [], None, None
    evidence = {'manifest_verified': not manifest, 'manifest_errors': manifest[:10]}
    try:
        result = read_json(folder, 'result.json')
        lifecycle += lifecycle_errors(result, mode, protocol)
    except Exception as exc:
        result = {}
        lifecycle.append('result: ' + type(exc).__name__ + ': ' + str(exc)[:120])
    try:
        index = read_json(folder, 'questionnaire/run.json')
        if (index.get('probe_set_sha256') != probe_set_sha256 or index.get('request_digest') != audit.get('request_digest')
                or index.get('scheduled_calls') != len(schedule) or index.get('cutoff_seconds') != cutoff
                or index.get('call_timing') != timing or not finite(index.get('bound_seconds'))
                or abs(index['bound_seconds'] - QN.bound(timing)) > 1e-9):
            calls.append('run index limits differ from the frozen cutoff, bound, timing or schedule')
        records = load_records(folder, len(schedule))
        rows = {'probes': {p['probe_id']: p for p in frozen['probes']}, 'schedule': schedule}
        found, counts, answered = call_errors(records, rows, audit, index, timing, cutoff, served)
        calls += found
        if result:
            ledger = ledger_errors(result, protocol, records)
        finalized = index.get('status') in ('complete', 'incomplete')
        complete_calls = (len(records) == len(schedule) and set(counts) <= {'answered', 'timed_out'})
        if finalized and (index['status'] == 'complete') != (complete_calls and not index.get('stop_reason')):
            calls.append('run index status differs from the retained calls')
        recovered = not finalized or bool(manifest)
        passes = {'pass_1': {}, 'pass_2': {}}  # as the reviewed evaluator: every answer, by identified pass
        probes = rows['probes']
        for n, reply in sorted(answered.items()):
            _, _, pass_id, probe_id, _ = schedule[n]
            passes[pass_id][probe_id] = score_call(probes[probe_id], reply)
        if not calls:
            analysis = analyze(frozen['probes'], {k: v for k, v in passes.items() if v}, 'withheld',
                               recovered=recovered)
        run_summary = {'status': index.get('status') if finalized else 'never_finalized',
                       'stop_reason': index.get('stop_reason'), 'calls_recorded': len(records),
                       'scheduled_calls': len(schedule), 'counts': counts, 'evidence_recovered': recovered,
                       'phase_reached': records[-1].get('phase') if records else None}
    except Exception as exc:
        calls.append('questionnaire evidence: ' + type(exc).__name__ + ': ' + str(exc)[:200])
    gate_status = ('complete' if analysis and not analysis['evidence_recovered']
                   and analysis['completeness']['primary'] == analysis['completeness']['over_claim_gates'] == 'complete'
                   else 'incomplete')
    collected = (not manifest and not calls and run_summary is not None and run_summary['status'] == 'complete'
                 and gate_status == 'complete')
    technically_complete = collected and not lifecycle and not ledger
    descriptive = {arm: row['status'] for arm, row in analysis['readiness'].items()} if analysis else None
    # Frozen protocol v2 §9: an attempt that is not technically complete qualifies no arm, even when every answer was
    # retained (for example, required post-run checks refused after the admission cutoff). Its scores stay descriptive.
    gate = descriptive if technically_complete or descriptive is None else {arm: 'incomplete' for arm in descriptive}
    return {'mode': mode, 'lifecycle_passed': not lifecycle and not ledger, 'lifecycle_errors': lifecycle + ledger,
            'evidence': evidence, 'call_errors': calls[:20], 'run': run_summary, 'gate_status': gate_status,
            'gate': gate, 'descriptive_readiness': descriptive, 'questionnaire_collected': collected,
            'attempt_verdict': 'technically_complete' if technically_complete else 'failed_technically_incomplete',
            'analysis': analysis, 'technically_complete': technically_complete,
            'exact_provider_billed_seconds': None, 'scoring': 'research/progress_subgoal_v1/score.py (unchanged)'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--mode', choices=('live', 'rehearsal'), default='live')
    parser.add_argument('--declared', type=Path, help='rehearsal only: the harness-declared protocol (JSON file)')
    parser.add_argument('--json-out', type=Path)
    args = parser.parse_args()
    declared = json.loads(args.declared.read_bytes()) if args.mode == 'rehearsal' and args.declared else None
    value = evaluate_output(args.output, mode=args.mode, protocol=declared)
    if args.json_out:
        args.json_out.write_bytes((json.dumps(value, sort_keys=True, indent=1) + '\n').encode())
    print(json.dumps({k: v for k, v in value.items() if k != 'analysis'}, indent=1))
