"""Independent evaluation of one session's retained output on the verified runtime (read-only; no model).

Nothing the run concluded is trusted, and nothing is taken from the evidence being checked where the frozen package
fixes it. This evaluator:
- verifies the evidence manifest (every retained file, by SHA-256, and no unlisted file);
- checks the verified lifecycle's result against the session protocol's frozen limits and request plan: mode and
  evidence class, every stage passed in order, the final lifecycle deadline, process and (live) GPU cleanup,
  environment removal (live), the request ledger (planned ids only, each within its issues, the cap, no refusals),
  bundle, installation, model-artifact and GPU facts against the pins (live), the canary and the server-log check;
- re-validates the study's server evidence (prefix caching verified from counters after the canary; live launch
  flags; frozen per-call timing) with the reviewed validator;
- binds the retained calls to the frozen call order, requests, cutoff, bound, token parity, counters and
  cancellations with the reviewed checks of run/evaluate.py (`call_errors`), unchanged;
- scores only retained answers (run/evaluate.score_call, run/score.score) and reports run/score.technical: the
  technical report only. No accuracy, contrast or verdict exists per session.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from research.evidence_memory_v1.run import evaluate as RE
from research.evidence_memory_v1.successor import plan as PL

ROOT = Path(__file__).resolve().parents[3]
STAGES = ('host', 'bundle_integrity', 'installation', 'gpu', 'model_artifact', 'server_start', 'server_ready',
          'startup_probe_S1', 'startup_probe_S2', 'startup_probe_S3', 'inference_I1', 'inference_I2', 'inference_I3',
          'inference_I4', 'cache_config', 'study', 'cancellation_C1', 'cancellation_C2_idle',
          'cancellation_C3_responsive')
RESULT_LIMIT = 64 * 1024**2


def session_protocol(root, label):
    package = PL.SESSIONS[label]['package']
    return json.loads((Path(root) / package / 'protocol.json').read_bytes()), package


def evidence_class(label, mode):
    import importlib
    return importlib.import_module(PL.SESSIONS[label]['module'] + '.evidence').evidence_class(mode)


def manifest_errors(output):
    output = Path(output)
    try:
        listed = RE.read(output, 'evidence-manifest.json', RESULT_LIMIT)['files']
        present = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} - {'evidence-manifest.json'}
        if not isinstance(listed, dict) or set(listed) != present:
            return ['evidence manifest inventory differs from the retained files']
        changed = [n for n, digest in listed.items() if hashlib.sha256((output / n).read_bytes()).hexdigest() != digest]
        return ['evidence manifest digest differs: ' + ', '.join(sorted(changed)[:5])] if changed else []
    except Exception as exc:
        return ['evidence manifest: ' + type(exc).__name__ + ': ' + str(exc)[:120]]


def ledger_errors(ledger, protocol, limits):
    errors = []
    plan = {item['id']: item for item in protocol['requests']}
    entries = ledger.get('entries')
    if (not isinstance(entries, list) or ledger.get('maximum_model_requests') != limits['maximum_model_requests']
            or ledger.get('issued') != len(entries) or len(entries) > limits['maximum_model_requests']):
        return ['request ledger missing or over its cap']
    issued = {}
    for n, entry in enumerate(entries, 1):
        item = plan.get(entry.get('id'))
        issued[entry.get('id')] = issued.get(entry.get('id'), 0) + 1
        if item is None or entry.get('sequence') != n or entry.get('kind') != item['kind'] or entry.get('path') != item['path']:
            errors.append(f'ledger entry {n}: not a planned request in sequence')
        elif issued[entry['id']] > item.get('max_issues', 1):
            errors.append(f"ledger entry {n}: {entry['id']} issued more than planned")
    if ledger.get('refusals') != []:
        errors.append('the request ledger refused a request')
    return errors[:10]


def lifecycle_errors(output, mode, label, protocol, limits):
    errors = manifest_errors(output)
    try:
        result = RE.read(output, 'result.json', RESULT_LIMIT)
    except Exception as exc:
        return errors + ['lifecycle result: ' + type(exc).__name__ + ': ' + str(exc)[:100]]
    if result.get('mode') != mode or result.get('evidence_class') != evidence_class(label, mode) \
            or result.get('gpu_compatibility_evidence') is not False:
        errors.append('mode or evidence class binding')
    if (result.get('passed') is not True or result.get('verdict_status') != 'passed' or result.get('error') is not None
            or result.get('failed_stage') is not None or result.get('completed_plan') is not True):
        errors.append('lifecycle: ' + str(result.get('failed_stage')) + ': ' + str(result.get('error'))[:160])
    cleanup = result.get('cleanup') or {}
    server, installation = cleanup.get('server') or {}, cleanup.get('installation') or {}
    if (result.get('cleanup_verified') is not True or cleanup.get('groups_absent') is not True
            or server.get('groups_absent') is not True or installation.get('groups_absent') is not True
            or installation.get('error') is not None or result.get('cleanup_interrupted')):
        errors.append('process cleanup')
    gpu, environment = cleanup.get('gpu'), cleanup.get('environment') or {}
    if mode == 'live':
        if (not isinstance(gpu, dict) or gpu.get('gpu_cleanup_verified') is not True or gpu.get('gpu_processes') != 0
                or environment.get('removed') is not True):
            errors.append('independent GPU cleanup or environment removal')
    elif not (isinstance(gpu, str) and gpu.startswith('not_exercised')):
        errors.append('a rehearsal claims GPU cleanup')
    deadline = result.get('lifecycle_deadline') or {}
    if (deadline.get('met') is not True or deadline.get('internal_seconds') != limits['internal_seconds']
            or not RE.finite(result.get('elapsed_seconds'), 0) or result['elapsed_seconds'] >= limits['internal_seconds']):
        errors.append(f"lifecycle deadline (frozen {limits['internal_seconds']} s)")
    if result.get('limits') != limits:
        errors.append('reported limits conflict with the frozen limits')
    errors += ledger_errors(result.get('ledger') or {}, protocol, limits)
    stages = result.get('stages') or {}
    expected = [s for s in STAGES if mode == 'live' or s != 'gpu']
    passed = [p.get('phase') for p in result.get('phases') or [] if p.get('outcome') == 'passed']
    if [p for p in passed if p in expected] != expected:
        errors.append('lifecycle stages missing, failed or out of order')
    if (stages.get('bundle_integrity') or {}).get('integrity_passed') is not True \
            or (stages.get('installation') or {}).get('passed') is not True \
            or (stages.get('cache_config') or {}).get('disabled') is not True \
            or ((result.get('requests') or {}).get('S3') or {}).get('passed') is not True:
        errors.append('bundle, installation, canary or server-log cache check')
    if mode == 'live':
        bundle, install = stages.get('bundle_integrity') or {}, stages.get('installation') or {}
        runtime, model = protocol['runtime'], protocol['model']
        if (bundle.get('wheel_bytes_verified') != protocol['bundle']['wheel_count']
                or bundle.get('trusted_artifacts_sha256') != protocol['bundle']['approved_manifest_sha256']
                or install.get('versions') != runtime['packages']
                or install.get('torch_cuda_build') != runtime['torch_cuda_build']
                or (stages.get('model_artifact') or {}).get('tree_sha256') != model['tree_sha256']
                or runtime['gpu_name_contains'] not in str((stages.get('gpu') or {}).get('name'))
                or not str((stages.get('host') or {}).get('python', '')).startswith(runtime['python'] + '.')
                or not re.fullmatch(PL.SESSIONS[label]['attempt'] + r'-[a-zA-Z0-9-]{8,80}', str(result.get('attempt_id')))):
            errors.append('live runtime facts differ from the pinned runtime')
    return errors


def server_errors(output, mode, probe_set_sha256, timing):
    """(errors, the prompt-token counter after the canary). The counter is read whether or not the configuration
    validates, as run/evaluate.py reads it, so call checks are not confounded by an unrelated violation."""
    from research.evidence_memory_v1.run.service import validate_server_config
    total = None
    try:
        config = RE.read(output, 'study/server-config.json', 65536)
        total = (config.get('after_canary') or {}).get('prompt_tokens_total')
        validate_server_config(config, mode, probe_set_sha256, timeout_seconds=timing['timeout'],
                               verify_seconds=timing['verify'])
        if config.get('teardown_seconds') != timing['teardown']:
            raise ValueError('teardown differs from the frozen value')
        return [], total
    except Exception as exc:
        return ['study server configuration: ' + type(exc).__name__ + ': ' + str(exc)[:120]], total


def review_errors(root, label):
    """Live: the evaluating checkout must hold exactly the session's reviewed sources and review documents (the frozen
    protocol, this evaluator and the pooled analysis) of its latest review lock. Returns (errors, verified)."""
    import importlib
    B = importlib.import_module(PL.SESSIONS[label]['module'] + '.binding')
    try:
        name = B.review_lock(root)
        B.check_sources(root, name)
        return [], {'review_lock': name, 'review_lock_sha256': B.sha256(Path(root) / name)}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return ['review sources: ' + type(exc).__name__ + ': ' + str(exc)[:160]], None


def evaluate_output(output, label, *, mode='live', rehearsal_limits=None, root=ROOT, frozen=None):
    """One session's technical evaluation. `rehearsal_limits` (rehearsal only) are the harness-declared limits."""
    from research.evidence_memory_v1.run.evidence import load_verified
    from research.evidence_memory_v1.run import score as SC
    output = Path(output)
    protocol, package = session_protocol(root, label)
    if mode == 'live':
        if rehearsal_limits is not None:
            raise ValueError('live evaluation uses the frozen limits only')
        limits = protocol['limits']
    elif mode == 'rehearsal' and isinstance(rehearsal_limits, dict):
        limits = rehearsal_limits
    else:
        raise ValueError('rehearsal evaluation needs the harness-declared limits')
    frozen, digest = frozen or PL.load_frozen(root, package)
    timing = {**PL.timing(mode), 'cutoff': limits['admission_cutoff_seconds']}
    lifecycle = lifecycle_errors(output, mode, label, protocol, limits)
    review = None
    if mode == 'live':  # the reviewed sources and review documents of the evaluating checkout
        found, review = review_errors(root, label)
        lifecycle += found
    found, canary_total = server_errors(output, mode, digest, timing)
    lifecycle += found
    evidence, technical, run_summary, calls_errors, recovered = {'verified': False}, None, None, [], None
    try:
        run = load_verified(output / 'study/run')
        cancellations = RE.read(output, 'study/cancellations.json') if (output / 'study/cancellations.json').exists() else []
        calls_errors, counts = RE.call_errors(run, frozen, digest, cancellations, timing,
                                              canary_total if RE.finite(canary_total, 1) else None)
        recovered = run.get('evidence_recovery')
        evidence = {'verified': True, 'recovered': bool(recovered)}
        if recovered:
            evidence['evidence_recovery'] = recovered
        probes = {p['probe_id']: p for p in frozen['probes']}
        passes = {'pass_1': {}, 'pass_2': {}}
        if not calls_errors:
            for call in run['calls']:
                if call['status'] == 'answered':
                    passes[call['pass_id']][call['probe_id']] = RE.score_call(probes[call['probe_id']], call)
            technical = SC.technical(frozen, passes)
        run_summary = {'status': run['status'], 'stop_reason': run['stop_reason'], 'calls_recorded': len(run['calls']),
                       'scheduled_calls': run['scheduled_calls'], 'counts': counts,
                       'phase_reached': run['calls'][-1]['phase'] if run['calls'] else None}
    except Exception as exc:
        evidence = {'verified': False, 'error': type(exc).__name__ + ': ' + str(exc)[:200]}
    status = (technical['technical_status'] if technical and not recovered else 'incomplete')
    gate_status = 'complete' if technical and technical['completeness']['withheld'] == 'complete' and not recovered \
        else 'incomplete'
    return {'mode': mode, 'session': label, 'package': package, 'frozen_set_sha256': digest,
            'case_source': frozen['case_source'], 'limits': limits, 'lifecycle_passed': not lifecycle,
            'lifecycle_errors': lifecycle, 'run_evidence': evidence, 'call_errors': calls_errors[:20],
            'run': run_summary, 'gate_status': gate_status, 'gate': {'questionnaire': status} if technical else None,
            'analysis': technical, 'review_lock_verified': review,
            'technically_complete': (not lifecycle and evidence['verified'] and not calls_errors and not recovered
                                     and run_summary['status'] == 'complete' and gate_status == 'complete'),
            'exact_provider_billed_seconds': None, 'phase4_complete': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', type=Path)
    parser.add_argument('--session', choices=sorted(PL.SESSIONS), required=True)
    parser.add_argument('--mode', choices=('live', 'rehearsal'), default='live')
    args = parser.parse_args()
    limits = None
    if args.mode == 'rehearsal':
        import importlib
        limits = importlib.import_module(PL.SESSIONS[args.session]['module'] + '.rehearsal').rehearsal_limits(ROOT)
    print(json.dumps(evaluate_output(args.output, args.session, mode=args.mode, rehearsal_limits=limits), indent=1))


if __name__ == '__main__':
    main()
