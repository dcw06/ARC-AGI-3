"""Independent evaluation of a downloaded (or rehearsal) evidence-comprehension output tree. Read-only; no model.

Nothing the runner concluded is trusted. The evaluator:
- checks the lifecycle receipts against the frozen limits (never a limit claimed by the report);
- re-validates the host's server evidence (prefix caching verified disabled; live launch flags);
- re-derives the call order and every request hash from the frozen probe set, and requires the
  retained calls to be exactly a prefix of that order;
- requires every timed-out call to have a host cancellation record with the server observed idle;
- scores only the retained responses with the independent scorer, and analyses them by
  identified pass, so missing answers or passes stay `incomplete`.
"""
import argparse
import json
import math
from pathlib import Path

LIVE_INTERNAL_SECONDS, CLEANUP_RESERVE_SECONDS = 3300, 300
STATUSES = ('answered', 'timed_out', 'rejected', 'transport_failure')


def read(output, name, limit=4 * 1024**2):
    path = Path(output) / name
    if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
        raise ValueError('missing or oversized evidence: ' + name)
    return json.loads(path.read_bytes())


def lifecycle_errors(output, mode, frozen_internal):
    from certification.phase4_integrated_v2.monitor import validate_binding
    from certification.phase4_integrated_v2.telemetry import read_telemetry
    errors, receipts = [], {}
    for key, name in (('outer', 'control/outer.json'), ('first_cell', 'control/first-cell-supervisor-cleanup.json'),
                      ('cost', 'control/notebook-cost.json'), ('gpu', 'control/gpu-cleanup.json')):
        try:
            receipts[key] = read(output, name)
        except Exception as exc:
            errors.append('lifecycle receipt: ' + type(exc).__name__ + ': ' + str(exc)[:100])
            receipts[key] = {}
    outer, first_cell, cost, gpu = receipts['outer'], receipts['first_cell'], receipts['cost'], receipts['gpu']
    if outer.get('mode') != mode:
        errors.append('mode binding')
    if outer.get('status') != 'study_ended_pending_independent_evaluation' or outer.get('error'):
        errors.append('supervisor: ' + str(outer.get('error') or outer.get('status')))
    if not (outer.get('process_groups_exited') is True and outer.get('independent_gpu_cleanup_verified') is True
            and outer.get('scratch_removed') is True):
        errors.append('supervisor cleanup')
    if outer.get('worker_released') is not True or (outer.get('run_evidence') or {}).get('verified') is not True:
        errors.append('supervisor release/run-evidence verification')
    groups = first_cell.get('groups')
    if (first_cell.get('errors') != [] or not isinstance(groups, dict) or not groups
            or not all(v is True for v in groups.values()) or first_cell.get('drain_finished') is not True
            or first_cell.get('returncode') != 0):
        errors.append('first-cell group cleanup, log drain or supervisor return code')
    try:
        ownership = read(output, 'control/ownership.json', 8192)
        if not {str(ownership['worker_pgid']), str(ownership['monitor_pgid'])} <= set(groups or {}):
            raise ValueError('owned groups missing from cleanup evidence')
    except Exception as exc:
        errors.append('ownership evidence: ' + type(exc).__name__ + ': ' + str(exc)[:80])
    trees = cost.get('dependency_trees_removed')
    if (cost.get('error') is not None or cost.get('study_status') != 'study_ended_pending_independent_evaluation'
            or cost.get('first_cell_cleanup_verified') is not True
            or (trees is not True if mode == 'live' else trees is not None)):
        errors.append('notebook finalization receipt')
    if (gpu.get('gpu_cleanup_verified') is not True or gpu.get('remaining_gpu_pids') != 0
            or gpu.get('groups_absent') is not True):
        errors.append('independent GPU cleanup')
    if (outer.get('internal_seconds') != frozen_internal
            or outer.get('admission_cutoff_seconds') != frozen_internal - CLEANUP_RESERVE_SECONDS):
        errors.append('reported limits conflict with the frozen lifecycle')
    for label, value in (('first-cell', cost.get('elapsed_seconds')), ('supervisor', outer.get('elapsed_seconds'))):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value < frozen_internal:
            errors.append(f'{label} deadline (frozen {frozen_internal} s)')
    try:
        telemetry = read_telemetry(Path(output) / 'monitor')
        ready = read(output, 'monitor/ready.json', 65536)
        if validate_binding(ready['gpu_binding']) is None or not telemetry['samples']:
            raise ValueError('monitor')
    except Exception as exc:
        errors.append('monitor evidence: ' + type(exc).__name__)
    return errors


def model_errors(output, mode, probe_set_sha256):
    from research.evidence_comprehension_v1.service import validate_ready, validate_server_config
    errors = []
    try:
        model = read(output, 'worker/model-ready.json')
        canary = read(output, 'worker/canary.json')
        expected = ({'rehearsal': 'scripted_model_not_target_evidence'} if mode == 'rehearsal' else
                    __import__('research.evidence_comprehension_v1.host', fromlist=['expected_artifact']).expected_artifact())
        validate_ready({'artifact': model['artifact'], 'startup_seconds': model['startup_seconds'],
                        'canary_audit': canary}, expected)
    except Exception as exc:
        errors.append('model readiness/canary: ' + type(exc).__name__ + ': ' + str(exc)[:120])
    try:
        validate_server_config(read(output, 'worker/server-config.json', 65536), mode, probe_set_sha256)
    except Exception as exc:
        errors.append('server configuration: ' + type(exc).__name__ + ': ' + str(exc)[:120])
    return errors


def call_errors(run, frozen, probe_set_sha256, cancellations):
    """Bind retained calls to the frozen order and requests; returns (errors, per-status counts)."""
    from research.action_effect_history_v1.service import request_hash
    from research.evidence_comprehension_v1.probes import build_request
    from research.evidence_comprehension_v1.schedule import call_order
    errors, counts = [], {}
    if run.get('probe_set_sha256') != probe_set_sha256:
        errors.append('run evidence names a different probe set')
    contexts = {c['context_id']: c for c in frozen['contexts']}
    probes = {p['probe_id']: p for p in frozen['probes']}
    order = call_order(frozen['probes'])
    if len(run['calls']) > len(order):
        errors.append('more calls than scheduled')
    cancelled = {}
    for record in cancellations:
        if record.get('idle_verification', {}).get('idle') is True:
            cancelled[record['request_sha256']] = cancelled.get(record['request_sha256'], 0) + 1
    for call, (phase, pass_id, probe_id) in zip(run['calls'], order):
        n = call['index']
        if (call.get('phase'), call.get('pass_id'), call.get('probe_id')) != (phase, pass_id, probe_id):
            errors.append(f'call {n}: not the scheduled call')
            continue
        probe = probes[probe_id]
        if call.get('request_sha256') != request_hash(build_request(contexts[probe['context_id']], probe)):
            errors.append(f'call {n}: request hash differs from the frozen request')
        status = call.get('status')
        counts[status] = counts.get(status, 0) + 1
        if status not in STATUSES:
            errors.append(f'call {n}: unknown status')
        elif status == 'answered':
            if (type(call.get('response')) is not str or type(call.get('server_prompt_tokens')) is not int
                    or call.get('server_prompt_tokens') != call.get('tokenizer_prompt_tokens')):
                errors.append(f'call {n}: answered call lacks a response or token parity')
        elif status == 'timed_out':
            if cancelled.get(call['request_sha256'], 0) < 1:
                errors.append(f'call {n}: timed out without a verified server-side cancellation')
            else:
                cancelled[call['request_sha256']] -= 1
    return errors, counts


def evaluate_output(output, *, mode='live', rehearsal_seconds=None):
    from research.evidence_comprehension_v1.evidence import load_verified
    from research.evidence_comprehension_v1.probes import load_frozen
    from research.evidence_comprehension_v1.score import analyze, score
    output = Path(output)
    if mode == 'live':
        frozen_internal = LIVE_INTERNAL_SECONDS
    elif type(rehearsal_seconds) is int and CLEANUP_RESERVE_SECONDS + 60 <= rehearsal_seconds <= LIVE_INTERNAL_SECONDS:
        frozen_internal = rehearsal_seconds
    else:
        raise ValueError('rehearsal evaluation needs the harness-declared internal seconds')
    frozen, probe_set_sha256 = load_frozen()
    lifecycle = lifecycle_errors(output, mode, frozen_internal)
    lifecycle += model_errors(output, mode, probe_set_sha256)
    evidence, analysis, run_summary, calls_errors = {'verified': False}, None, None, []
    try:
        run = load_verified(output / 'worker/run')
        cancellations = []
        if (output / 'worker/cancellations.json').exists():
            cancellations = read(output, 'worker/cancellations.json')
        calls_errors, counts = call_errors(run, frozen, probe_set_sha256, cancellations)
        evidence = {'verified': True}
        passes = {'pass_1': {}, 'pass_2': {}}
        probes = {p['probe_id']: p for p in frozen['probes']}
        if not calls_errors:
            for call in run['calls']:
                if call['status'] == 'answered':
                    passes[call['pass_id']][call['probe_id']] = score(probes[call['probe_id']], call['response'])
            analysis = analyze(frozen['probes'], {k: v for k, v in passes.items() if v})
        run_summary = {'status': run['status'], 'stop_reason': run['stop_reason'], 'calls_recorded': len(run['calls']),
                       'scheduled_calls': run['scheduled_calls'], 'counts': counts,
                       'phase_reached': run['calls'][-1]['phase'] if run['calls'] else None}
    except Exception as exc:
        evidence = {'verified': False, 'error': type(exc).__name__ + ': ' + str(exc)[:200]}
    gate_status = analysis['gate_status'] if analysis else 'incomplete'
    return {'mode': mode, 'frozen_internal_seconds': frozen_internal, 'lifecycle_passed': not lifecycle,
            'lifecycle_errors': lifecycle, 'run_evidence': evidence, 'call_errors': calls_errors[:20],
            'run': run_summary, 'gate_status': gate_status,
            'gate': analysis['gate'] if analysis else None, 'analysis': analysis,
            'technically_complete': (not lifecycle and evidence['verified'] and not calls_errors
                                     and gate_status == 'complete'),
            'exact_provider_billed_seconds': None, 'phase4_complete': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--mode', choices=('live', 'rehearsal'), default='live')
    parser.add_argument('--rehearsal-seconds', type=int)
    args = parser.parse_args()
    value = evaluate_output(args.output, mode=args.mode, rehearsal_seconds=args.rehearsal_seconds)
    print(json.dumps({k: v for k, v in value.items() if k != 'analysis'}, indent=1))
