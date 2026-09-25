"""Independent evaluation of a downloaded (or rehearsal) output tree. Read-only; no model or GPU."""
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


def evaluate_output(output, *, mode='live'):
    """Lifecycle checks, verified run evidence and the frozen behaviour/solving/reliability evaluation.

    Lifecycle and evidence problems are reported alongside whatever run evidence verifies; partial
    evidence is evaluated as partial and never promoted to complete.
    """
    from research.action_effect_history_v1.evidence import load_verified
    from research.action_effect_history_v1.evaluate import evaluate
    from research.action_effect_history_v1.service import validate_ready
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
    elapsed = cost.get('elapsed_seconds')
    if type(elapsed) not in (int, float) or not 0 <= elapsed < outer.get('internal_seconds', 3300):
        lifecycle.append('first-cell deadline')
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
                    __import__('research.action_effect_history_v1.host', fromlist=['expected_artifact']).expected_artifact())
        validate_ready({'artifact': model['artifact'], 'startup_seconds': model['startup_seconds'],
                        'canary_audit': {**canary, 'audit': canary.get('audit')}}, expected)
    except Exception as exc:
        lifecycle.append('model readiness/canary: ' + type(exc).__name__ + ': ' + str(exc)[:120])
    try:
        run = load_verified(output / 'worker/run')
        evidence = {'verified': True, 'run_status': run['status']}
        result = evaluate(run)
    except Exception as exc:
        evidence = {'verified': False, 'error': type(exc).__name__ + ': ' + str(exc)[:200]}
        result = None
    return {'mode': mode, 'lifecycle_passed': not lifecycle, 'lifecycle_errors': lifecycle,
            'run_evidence': evidence, 'evaluation': result,
            'technically_complete': not lifecycle and evidence['verified'] and evidence.get('run_status') == 'complete'
            and bool(result and result['replay_passed']),
            'exact_provider_billed_seconds': None, 'phase4_complete': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--mode', choices=('live', 'rehearsal'), default='live')
    args = parser.parse_args()
    value = evaluate_output(args.output, mode=args.mode)
    summary = {k: v for k, v in value.items() if k != 'evaluation'}
    if value['evaluation']:
        summary.update({k: value['evaluation'][k] for k in ('replay_passed', 'behaviour_result', 'solving_result',
                                                            'reliability_by_arm', 'arm_specific_reliability_differences')})
    print(json.dumps(summary, indent=1))
