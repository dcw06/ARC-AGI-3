"""Independently classify the consumed Stage B R7 provider evidence."""
import hashlib
import json
from pathlib import Path

from agent.state import GameRuntimeState
from certification.phase4_integrated_v2.monitor import validate_binding
from certification.phase4_integrated_v2.telemetry import read_telemetry
from certification.phase4_transient_v2.contract import pack, unpack
from research.grounded_action_v1.artifact_contract import expected_artifact
from research.grounded_action_v1.bridge_service import validate_ready
from research.grounded_action_v1.contract import audit_request, digest, parse_audit, parse_policy, policy_request
from research.grounded_action_v1.replay import replay_file

ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD = ROOT / 'reports/runs/phase4-grounded-action-v1-r7/download'
MANIFEST = ROOT / 'reports/perception_stage_b_r7_download.json'
RESULT = ROOT / 'reports/perception_stage_b_r7_evaluation.json'
ERROR = 'ValueError: feedback fields'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(download, name):
    path = download / ('phase4-grounded-action-v1/' + name)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 4 * 1024**2,
            'missing or oversized evidence: ' + name)
    return json.loads(path.read_bytes())


def evaluate(download=DOWNLOAD, manifest_path=MANIFEST, record_root=ROOT):
    download, manifest_path, record_root = map(Path, (download, manifest_path, record_root))
    manifest = json.loads(manifest_path.read_bytes())
    require(manifest['kernel'] == 'daichongwei06/arc3-grounded-action-v1-r7' and
            manifest['requested_version'] == 1 and manifest['file_count'] == len(manifest['files']),
            'provider version/inventory binding')
    rows = manifest['files']
    paths = {row['path'] for row in rows}
    require(len(paths) == len(rows) and paths ==
            {p.relative_to(download).as_posix() for p in download.rglob('*') if p.is_file()},
            'download inventory')
    for row in rows:
        relative = Path(row['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'unsafe provider path')
        path = download / relative
        require(path.is_file() and not path.is_symlink() and
                len(path.read_bytes()) == row['bytes'] and
                hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'],
                'provider hash/size mismatch: ' + row['path'])

    launch = json.loads((record_root / 'reports/perception_stage_b_r7_launch.json').read_bytes())
    reservation = json.loads((record_root / 'research/grounded_action_v1/reservation_r7.json').read_bytes())
    prelaunch = json.loads((record_root / 'reports/perception_stage_b_r7_prelaunch.json').read_bytes())
    observations = [json.loads(line) for line in
        (record_root / 'reports/runs/phase4-grounded-action-v1-r7/provider-observations.jsonl').read_text().splitlines()]
    require(observations and launch['attempt_id'] == reservation['attempt_id'] ==
            prelaunch['attempt_id'] == manifest['attempt_id'] and
            launch['provider_version'] == 1 and launch['attempt_consumed'] is True and
            reservation['status'] == 'consumed' and launch['automatic_retry_authorized'] is False and
            observations[-1]['status'] == 'KernelWorkerStatus.ERROR', 'attempt/provider binding')

    installation = read(download, 'control/installation.json')
    cost = read(download, 'control/notebook-cost.json')
    outer = read(download, 'control/outer.json')
    gpu = read(download, 'control/gpu-cleanup.json')
    parent = read(download, 'control/first-cell-supervisor-cleanup.json')
    model = read(download, 'worker/model-ready.json')
    canary = read(download, 'worker/canary.json')
    worker_failure = read(download, 'worker/failure.json')
    trajectory = read(download, 'worker/trajectory.json')
    ready = read(download, 'monitor/ready.json')
    telemetry = read_telemetry(download / 'phase4-grounded-action-v1/monitor')
    require(installation['passed'] is True and cost['dependency_trees_removed'] is True,
            'installation/dependency cleanup')
    require(outer['status'] == 'failed' and outer['error'] == 'RuntimeError: game worker failed' and
            outer['worker_released'] is True and outer['process_groups_exited'] is True and
            outer['independent_gpu_cleanup_verified'] is True and outer['scratch_removed'] is True and
            outer['elapsed_seconds'] < outer['internal_seconds'] == 3300,
            'supervisor failure/cleanup')
    require(gpu['gpu_cleanup_verified'] is True and gpu['groups_absent'] is True and
            gpu['remaining_gpu_pids'] == 0 and gpu['gpu_uuid'] == validate_binding(ready['gpu_binding']),
            'independent GPU cleanup')
    require(parent['drain_finished'] is True and parent['errors'] == [] and parent['returncode'] == 1 and
            parent['groups'] and all(v is True for v in parent['groups'].values()),
            'first-cell group cleanup')
    require(telemetry['samples'] and ready['sample'] == telemetry['samples'][0], 'monitor evidence')
    require(model['artifact'] == expected_artifact(), 'model artifact binding')
    validate_ready({'artifact': model['artifact'], 'startup_seconds': model['startup_seconds'],
                    'canary_audit': canary}, expected_artifact())

    require(trajectory['version'] == 'grounded_action_local_v3' and
            trajectory['kind'] == 'offline_development_engine' and trajectory['status'] == 'failed' and
            trajectory['error'] == ERROR and trajectory['calls'] == 3 and trajectory['dispatches'] == 1 and
            trajectory['case_protocol_sha256'] == hashlib.sha256(
                (ROOT / 'reports/perception_stage_b_v1_case_protocol.json').read_bytes()).hexdigest() and
            trajectory['limit']['calls'] == 12 and trajectory['limit']['steps_per_arm'] == 2 and
            0 < trajectory['limit']['seconds'] <= 3300 and
            0 <= trajectory['ended_at'] <= trajectory['limit']['seconds'] and
            worker_failure['error'] == 'RuntimeError: Stage B study failed: ' + ERROR and
            len(trajectory['episodes']) == 2 and
            [ep['arm'] for ep in trajectory['episodes']] == ['control', 'target'] and
            [len(ep['calls']) for ep in trajectory['episodes']] == [3, 0] and
            [len(ep['steps']) for ep in trajectory['episodes']] == [1, 0] and
            all(ep['status'] == 'bootstrapped' and ep['final'] is None for ep in trajectory['episodes']),
            'study failure/censoring')
    control_ep, target_ep = trajectory['episodes']
    first, second = (unpack(ep['initial']) for ep in trajectory['episodes'])
    frozen = json.loads((ROOT / 'reports/integrated_case_v1/initial_observation.json').read_bytes())
    require(first.canonical_hash == second.canonical_hash == frozen['canonical_hash'] and
            first.game_id == second.game_id == frozen['game_id'] and first.full_reset and second.full_reset,
            'initial-state equality')
    for episode, actions in ((control_ep, 1), (target_ep, 0)):
        cleanup = episode['cleanup']
        require(cleanup['closed'] is True and cleanup['client_closed'] is True and
                cleanup['scorecard_closed'] is True and cleanup['errors'] == [] and
                cleanup['scorecard_receipt']['total_actions'] == actions and
                cleanup['scorecard_receipt']['total_levels_completed'] == 0 and
                len(cleanup['client_journal']) == actions + 1 and
                cleanup['client_journal'][0]['kind'] == 'bootstrap_reset',
                'episode/scorecard cleanup')
    require(control_ep['cleanup']['scorecard_id'] != target_ep['cleanup']['scorecard_id'],
            'scorecard isolation')
    decision, prediction, feedback = control_ep['calls']
    step = control_ep['steps'][0]
    before, after = unpack(step['before']), unpack(step['after'])
    require(before.canonical_hash == first.canonical_hash and after.game_id == before.game_id and
            after.guid == before.guid and not after.full_reset and after.levels_completed == 0 and
            step['index'] == 0 and step['status'] == 'acknowledged' and
            step['decision_call'] == 0 and step['prediction_call'] == 1,
            'transition observation binding')
    expected_decision = policy_request(GameRuntimeState(first, action_budget_limit=2), 'control')
    require(decision['request'] == expected_decision and
            decision['request_sha256'] == digest(expected_decision), 'control request binding')
    action = parse_policy(decision['response'], 'control', first.available_actions,
                          first.latest_frame.tolist())['action']
    require(step['action'] == action and step['target'] is None,
            'decision/action binding')
    expected_prediction = audit_request('prediction', control_ep['initial'], action,
                                        prediction_contract='single_choice_v2')
    require(prediction['request'] == expected_prediction and
            prediction['request_sha256'] == digest(expected_prediction), 'prediction request binding')
    parsed_prediction = parse_audit(prediction['response'], 'prediction', first.frames,
                                    prediction_contract='single_choice_v2')
    require(step['prediction'] == parsed_prediction, 'committed prediction binding')
    expected_feedback = audit_request('feedback', step['after'], action, before=step['before'],
                                      prediction=parsed_prediction, feedback_encoding='hex_rows_v1')
    require(feedback['request'] == expected_feedback and
            feedback['request_sha256'] == digest(expected_feedback), 'feedback request binding')
    receipt = step['receipt']
    require(receipt['acknowledged'] is True and receipt['action'] == action and
            receipt['journal'] == control_ep['cleanup']['client_journal'][1] and
            receipt['journal']['fields']['post_state_hash'] == after.canonical_hash and
            receipt['journal']['prepared_fields']['pre_state_hash'] == before.canonical_hash,
            'action journal binding')
    previous = 0
    for row, stage, pre_hash, expected_status in ((decision, 'control', first.canonical_hash, 'valid'),
                                                   (prediction, 'prediction', first.canonical_hash, 'valid'),
                                                   (feedback, 'feedback', after.canonical_hash, 'failed')):
        raw = row['response'].encode()
        require(row['stage'] == stage and row['status'] == expected_status and
                row['pre_hash'] == pre_hash and row['response_truncated'] is False and
                row['response_bytes'] == len(raw) <= 4096 and
                row['response_sha256'] == hashlib.sha256(raw).hexdigest() and
                row['finish_reason'] == 'stop' and
                0 < row['tokenizer_prompt_tokens'] == row['server_prompt_tokens'] <= 60000 and
                0 < row['server_completion_tokens'] <= 128 and
                previous <= row['started_at'] <= row['returned_at'] <= trajectory['ended_at'],
                'retained call/token evidence')
        previous = row['returned_at']
    require(prediction['returned_at'] <= step['committed_at'] <= step['dispatch_started_at'] <=
            step['returned_at'] <= feedback['started_at'] and
            trajectory['prompt_tokens'] == sum(r['server_prompt_tokens'] for r in control_ep['calls']) and
            trajectory['completion_tokens'] == sum(r['server_completion_tokens'] for r in control_ep['calls']) and
            feedback['error'] == ERROR, 'chronology/totals')
    received = json.loads(feedback['response'])
    require(received['assessment'] == 'contradicted' and
            received['changed_frames'] == [1, 2, 3, 4, 5, 6, 7, 1] and
            len(after.frames) == 1, 'unexpected feedback failure evidence')
    try:
        parse_audit(feedback['response'], 'feedback', after.frames)
    except ValueError as exc:
        require(str(exc) == 'feedback fields', 'wrong feedback rejection')
    else:
        raise ValueError('invalid feedback incorrectly accepted')
    try:
        replay_file(download / 'phase4-grounded-action-v1/worker/trajectory.json')
    except ValueError as exc:
        require('incomplete pair' in str(exc), 'wrong replay rejection')
    else:
        raise ValueError('incomplete trajectory incorrectly passed replay')

    before_quota = prelaunch['gpu_quota_seconds']['time_used']
    after_quota = observations[-1]['gpu_quota_seconds']['time_used']
    return {'status': 'verified_feedback_contract_failure',
            'attempt_id': launch['attempt_id'], 'provider_status': observations[-1]['status'],
            'downloaded_files_verified': len(rows), 'installation_passed': True,
            'model_ready': True, 'startup_canary_passed': True,
            'study_calls': 3, 'game_actions': 1, 'episodes_completed': 0,
            'feedback_response': feedback['response'], 'feedback_frame_count': len(after.frames),
            'feedback_prompt_tokens': feedback['server_prompt_tokens'],
            'feedback_completion_tokens': feedback['server_completion_tokens'],
            'monitor_samples': len(telemetry['samples']),
            'trajectory_replay_rejected_incomplete_pair': True,
            'independent_gpu_cleanup_verified': True, 'process_groups_exited': True,
            'dependency_trees_removed': True, 'first_cell_elapsed_seconds': cost['elapsed_seconds'],
            'account_gpu_time_used_before_seconds': before_quota,
            'account_gpu_time_used_after_seconds': after_quota,
            'account_gpu_time_used_delta_seconds': round(after_quota - before_quota, 6),
            'exact_provider_billed_seconds': None, 'phase4_complete': False,
            'automatic_retry_authorized': False}


if __name__ == '__main__':
    result = evaluate()
    with RESULT.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(result, sort_keys=True))
