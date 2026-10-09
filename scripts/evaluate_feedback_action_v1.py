# Derived from scripts/evaluate_action_effect_history_v1.py by research/feedback_action_v1/derive.py; edit the derivation, not this file.
"""Independent evaluation of one downloaded (or rehearsal) feedback-action v1 session output tree. Read-only; no
model or GPU. Lifecycle checks are derived from action-effect history v1; the study evaluation is
research/feedback_action_v1/live_evaluation.py (verified manifest, verify_history, carried statements, every
rate, failure rules F1-F6)."""
import argparse
import json
from pathlib import Path

from certification.phase4_integrated_v2.monitor import validate_binding
from certification.phase4_integrated_v2.telemetry import read_telemetry


def read(output, name, limit=4 * 1024**2):
    path = Path(output) / name
    if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
        raise ValueError('missing or oversized evidence: ' + name)
    return json.loads(path.read_bytes())


REHEARSAL_INTERNAL_SECONDS = 2400  # the rehearsal harness's declared lifecycle


def evaluate_output(output, *, mode='live', rehearsal_seconds=None):
    """Lifecycle checks, verified run evidence and the frozen behaviour/solving/reliability evaluation.

    Lifecycle and evidence problems are reported alongside whatever run evidence verifies; partial
    evidence is evaluated as partial and never promoted to complete.
    """
    from research.feedback_action_v1.live.evidence import load_verified
    from research.feedback_action_v1.live_evaluation import evaluate_session
    from research.feedback_action_v1.live.service import validate_ready
    output = Path(output)
    lifecycle = []
    outer = read(output, 'control/outer.json')
    first_cell = read(output, 'control/first-cell-supervisor-cleanup.json')
    cost = read(output, 'control/notebook-cost.json')
    gpu = read(output, 'control/gpu-cleanup.json')
    if outer.get('mode') != mode:
        lifecycle.append('mode binding')
    if outer.get('status') != 'study_complete_pending_independent_evaluation' or outer.get('error'):
        lifecycle.append('supervisor: ' + str(outer.get('error') or outer.get('status')))
    if not (outer.get('process_groups_exited') is True and outer.get('independent_gpu_cleanup_verified') is True
            and outer.get('scratch_removed') is True):
        lifecycle.append('supervisor cleanup')
    if outer.get('worker_released') is not True or (outer.get('run_evidence') or {}).get('verified') is not True:
        lifecycle.append('supervisor release/run-evidence verification')
    # First-cell ownership cleanup: nonempty, every owned group verified gone, drain finished, clean exit.
    groups = first_cell.get('groups')
    if (first_cell.get('errors') != [] or not isinstance(groups, dict) or not groups
            or not all(v is True for v in groups.values()) or first_cell.get('drain_finished') is not True
            or first_cell.get('returncode') != 0):
        lifecycle.append('first-cell group cleanup, log drain or supervisor return code')
    try:
        ownership = read(output, 'control/ownership.json', 8192)
        owned = {str(ownership['worker_pgid']), str(ownership['monitor_pgid'])}
        if not owned <= set(groups or {}):
            raise ValueError('owned groups missing from cleanup evidence')
    except Exception as exc:
        lifecycle.append('ownership evidence: ' + type(exc).__name__ + ': ' + str(exc)[:80])
    # Notebook finalization receipt.
    trees = cost.get('dependency_trees_removed')
    if (cost.get('error') is not None or cost.get('study_status') != 'study_complete_pending_independent_evaluation'
            or cost.get('first_cell_cleanup_verified') is not True
            or (trees is not True if mode == 'live' else trees is not None)):
        lifecycle.append('notebook finalization receipt')
    if (gpu.get('gpu_cleanup_verified') is not True or gpu.get('remaining_gpu_pids') != 0
            or gpu.get('groups_absent') is not True):
        lifecycle.append('independent GPU cleanup')
    if mode == 'live':  # successor-runtime evidence: installation, the model server's own group, prefix caching
        try:
            installation = read(output, 'control/installation.json')
            server_config = read(output, 'worker/model-server-config.json')
            server_group = outer.get('model_server_group') or {}
            host_receipt = (read(output, 'worker/model-server-cleanup.json')['receipt']
                            if (output / 'worker/model-server-cleanup.json').is_file() else None)
            if (installation.get('passed') is not True
                    or (installation.get('process_cleanup') or {}).get('groups_absent') is not True
                    or server_config['prefix_caching'].get('disabled') is not True
                    or server_group.get('recorded') is not True or server_group.get('exited') is not True
                    or (host_receipt is not None and host_receipt.get('groups_absent') is not True)):
                raise ValueError('installation, model-server group cleanup or prefix caching not verified')
        except Exception as exc:
            lifecycle.append('successor runtime evidence: ' + type(exc).__name__ + ': ' + str(exc)[:120])
    # Deadlines are judged against the frozen limit, never a limit claimed by the report itself.
    import math
    from research.feedback_action_v1.live.runner import protocol
    limits = protocol()['limits']
    frozen = limits['internal_seconds'] if mode == 'live' else (rehearsal_seconds or REHEARSAL_INTERNAL_SECONDS)
    if mode == 'rehearsal' and not 60 <= frozen <= limits['internal_seconds']:
        lifecycle.append('rehearsal limit outside the frozen envelope')
    if (outer.get('internal_seconds') != frozen
            or outer.get('admission_cutoff_seconds') != frozen - limits['cleanup_reserve_seconds']):
        lifecycle.append('reported limits conflict with the frozen lifecycle')
    for label, value in (('first-cell', cost.get('elapsed_seconds')), ('supervisor', outer.get('elapsed_seconds'))):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value < frozen:
            lifecycle.append(f'{label} deadline (frozen {frozen} s)')
    try:
        telemetry = read_telemetry(output / 'monitor')
        ready = read(output, 'monitor/ready.json', 65536)
        if validate_binding(ready['gpu_binding']) is None or not telemetry['samples']:
            raise ValueError('monitor')
    except Exception as exc:
        lifecycle.append('monitor evidence: ' + type(exc).__name__)
    try:
        model = read(output, 'worker/model-ready.json')
        canary = read(output, 'worker/canary.json')
        expected = ({'rehearsal': 'scripted_model_not_target_evidence'} if mode == 'rehearsal' else
                    __import__('research.feedback_action_v1.live.host', fromlist=['expected_artifact']).expected_artifact())
        validate_ready({'artifact': model['artifact'], 'startup_seconds': model['startup_seconds'],
                        'canary_audit': {**canary, 'audit': canary.get('audit')}}, expected)
    except Exception as exc:
        lifecycle.append('model readiness/canary: ' + type(exc).__name__ + ': ' + str(exc)[:120])
    try:
        run = load_verified(output / 'worker/run')
        evidence = {'verified': True, 'run_status': run['status']}
        result = evaluate_session(run, session=outer.get('session'), mode=mode, output=output,
                                  lifecycle_errors=lifecycle)
    except Exception as exc:
        evidence = {'verified': False, 'error': type(exc).__name__ + ': ' + str(exc)[:200]}
        result = None
    return {'mode': mode, 'lifecycle_passed': not lifecycle, 'lifecycle_errors': lifecycle,
            'run_evidence': evidence, 'evaluation': result,
            'technically_complete': not lifecycle and evidence['verified'] and evidence.get('run_status') == 'complete'
            and bool(result and result['replay_passed']),
            'exact_provider_billed_seconds': None, 'phase4_complete': False,
            'session': outer.get('session'), 'attempt_id': cost.get('attempt_id')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--mode', choices=('live', 'rehearsal'), default='live')
    args = parser.parse_args()
    value = evaluate_output(args.output, mode=args.mode)
    summary = {k: v for k, v in value.items() if k != 'evaluation'}
    if value['evaluation']:
        summary.update({k: value['evaluation'][k] for k in ('replay_passed', 'session', 'failure_rules',
                                                            'session_2_permitted', 'technical_validity')})
    print(json.dumps(summary, indent=1))
