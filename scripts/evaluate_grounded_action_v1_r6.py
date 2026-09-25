"""Independently classify the consumed Stage B R6 provider evidence."""
import hashlib
import json
from pathlib import Path

from agent.state import GameRuntimeState
from certification.phase4_integrated_v2.monitor import validate_binding
from certification.phase4_integrated_v2.telemetry import read_telemetry
from certification.phase4_transient_v2.contract import unpack
from research.grounded_action_v1.artifact_contract import expected_artifact
from research.grounded_action_v1.bridge_service import validate_ready
from research.grounded_action_v1.contract import audit_request, digest, parse_audit, parse_policy, policy_request
from research.grounded_action_v1.replay import replay_file

ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD = ROOT / 'reports/runs/phase4-grounded-action-v1-r6/download'
MANIFEST = ROOT / 'reports/perception_stage_b_r6_download.json'
RESULT = ROOT / 'reports/perception_stage_b_r6_evaluation.json'
ERROR = 'ValueError: prediction alternatives'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(relative, download):
    path = download / relative
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 4 * 1024**2,
            'missing or oversized evidence: ' + relative)
    return json.loads(path.read_bytes())


def evaluate(download=DOWNLOAD, manifest_path=MANIFEST, record_root=ROOT):
    download, manifest_path, record_root = Path(download), Path(manifest_path), Path(record_root)
    manifest = json.loads(manifest_path.read_bytes())
    require(manifest['kernel'] == 'daichongwei06/arc3-grounded-action-v1-r6' and
            manifest['requested_version'] == 1 and manifest['file_count'] == len(manifest['files']),
            'provider version/inventory binding')
    rows = manifest['files']
    require(len({r['path'] for r in rows}) == len(rows), 'duplicate provider file')
    actual = {p.relative_to(download).as_posix() for p in download.rglob('*') if p.is_file()}
    require(actual == {r['path'] for r in rows}, 'download file set')
    for row in rows:
        relative = Path(row['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'unsafe provider path')
        path = download / relative
        require(path.is_file() and not path.is_symlink(), 'missing provider file')
        raw = path.read_bytes()
        require(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'],
                'provider hash/size mismatch: ' + row['path'])

    launch = json.loads((record_root / 'reports/perception_stage_b_r6_launch.json').read_bytes())
    reservation = json.loads((record_root / 'research/grounded_action_v1/reservation_r6.json').read_bytes())
    prelaunch = json.loads((record_root / 'reports/perception_stage_b_r6_prelaunch.json').read_bytes())
    observations = [json.loads(line) for line in
        (record_root / 'reports/runs/phase4-grounded-action-v1-r6/provider-observations.jsonl').read_text().splitlines()]
    require(observations and launch['attempt_id'] == reservation['attempt_id'] ==
            prelaunch['attempt_id'] == manifest['attempt_id'] and
            launch['provider_version'] == 1 and launch['attempt_consumed'] is True and
            reservation['status'] == 'consumed' and launch['automatic_retry_authorized'] is False and
            observations[-1]['status'] == 'KernelWorkerStatus.ERROR', 'attempt/provider binding')

    base = 'phase4-grounded-action-v1/'
    installation = read(base + 'control/installation.json', download)
    cost = read(base + 'control/notebook-cost.json', download)
    outer = read(base + 'control/outer.json', download)
    gpu = read(base + 'control/gpu-cleanup.json', download)
    parent = read(base + 'control/first-cell-supervisor-cleanup.json', download)
    model = read(base + 'worker/model-ready.json', download)
    canary = read(base + 'worker/canary.json', download)
    worker_failure = read(base + 'worker/failure.json', download)
    trajectory = read(base + 'worker/trajectory.json', download)
    ready = read(base + 'monitor/ready.json', download)
    telemetry = read_telemetry(download / base / 'monitor')
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
    require(parent['drain_finished'] is True and parent['errors'] == [] and
            parent['returncode'] == 1 and parent['groups'] and
            all(value is True for value in parent['groups'].values()), 'first-cell group cleanup')
    require(telemetry['samples'] and ready['sample'] == telemetry['samples'][0], 'monitor evidence')
    require(model['artifact'] == expected_artifact(), 'model artifact binding')
    validate_ready({'artifact': model['artifact'], 'startup_seconds': model['startup_seconds'],
                    'canary_audit': canary}, expected_artifact())

    require(trajectory['version'] == 'grounded_action_local_v2' and
            trajectory['kind'] == 'offline_development_engine' and trajectory['status'] == 'failed' and
            trajectory['error'] == ERROR and trajectory['calls'] == 2 and
            trajectory['dispatches'] == 0 and
            trajectory['case_protocol_sha256'] == hashlib.sha256(
                (ROOT / 'reports/perception_stage_b_v1_case_protocol.json').read_bytes()).hexdigest() and
            trajectory['limit']['calls'] == 12 and trajectory['limit']['steps_per_arm'] == 2 and
            0 < trajectory['limit']['seconds'] <= 3300 and
            0 <= trajectory['ended_at'] <= trajectory['limit']['seconds'] and
            worker_failure['error'] == 'RuntimeError: Stage B study failed: ' + ERROR and
            len(trajectory['episodes']) == 2 and
            [ep['arm'] for ep in trajectory['episodes']] == ['control', 'target'] and
            [len(ep['calls']) for ep in trajectory['episodes']] == [2, 0] and
            all(ep['status'] == 'bootstrapped' and ep['steps'] == [] and ep['final'] is None
                for ep in trajectory['episodes']), 'study failure/censoring')
    first, second = (unpack(ep['initial']) for ep in trajectory['episodes'])
    frozen = json.loads((ROOT / 'reports/integrated_case_v1/initial_observation.json').read_bytes())
    require(first.canonical_hash == second.canonical_hash == frozen['canonical_hash'] and
            first.game_id == second.game_id == frozen['game_id'] and
            first.full_reset and second.full_reset,
            'initial-state equality')
    for episode in trajectory['episodes']:
        cleanup = episode['cleanup']
        require(cleanup['closed'] is True and cleanup['client_closed'] is True and
                cleanup['scorecard_closed'] is True and
                cleanup['scorecard_receipt']['total_actions'] == 0 and
                cleanup['scorecard_receipt']['total_levels_completed'] == 0,
                'episode/scorecard cleanup')
    control, prediction = trajectory['episodes'][0]['calls']
    expected_control = policy_request(GameRuntimeState(first, action_budget_limit=2), 'control')
    require(control['request'] == expected_control and control['request_sha256'] == digest(expected_control),
            'control request binding')
    action = parse_policy(control['response'], 'control', first.available_actions,
                          first.latest_frame.tolist())['action']
    expected_prediction = audit_request('prediction', trajectory['episodes'][0]['initial'], action,
                                        prediction_contract='legacy_pair_v1')
    require(prediction['request'] == expected_prediction and
            prediction['request_sha256'] == digest(expected_prediction), 'prediction request binding')
    for row, expected_status in ((control, 'valid'), (prediction, 'failed')):
        raw = row['response'].encode()
        require(row['status'] == expected_status and row['pre_hash'] == first.canonical_hash and
                row['response_truncated'] is False and row['response_bytes'] == len(raw) and
                row['response_sha256'] == hashlib.sha256(raw).hexdigest() and
                row['finish_reason'] == 'stop' and
                0 < row['tokenizer_prompt_tokens'] == row['server_prompt_tokens'] <= 60000 and
                0 < row['server_completion_tokens'] <= 128 and
                0 <= row['started_at'] <= row['returned_at'] <= trajectory['ended_at'],
                'retained call/token evidence')
    require(control['returned_at'] <= prediction['started_at'] and
            prediction['error'] == ERROR and
            trajectory['prompt_tokens'] == sum(r['server_prompt_tokens'] for r in (control, prediction)) and
            trajectory['completion_tokens'] == sum(r['server_completion_tokens'] for r in (control, prediction)),
            'call chronology/totals')
    try:
        parse_audit(prediction['response'], 'prediction', first.frames,
                    prediction_contract='legacy_pair_v1')
    except ValueError as exc:
        require(str(exc) == 'prediction alternatives', 'wrong prediction rejection')
    else:
        raise ValueError('invalid prediction incorrectly accepted')
    try:
        replay_file(download / base / 'worker/trajectory.json')
    except ValueError as exc:
        require('incomplete pair' in str(exc), 'wrong replay rejection')
    else:
        raise ValueError('incomplete trajectory incorrectly passed replay')

    before = prelaunch['gpu_quota_seconds']['time_used']
    after = observations[-1]['gpu_quota_seconds']['time_used']
    return {'status': 'verified_prediction_contract_failure',
            'attempt_id': launch['attempt_id'], 'provider_status': observations[-1]['status'],
            'downloaded_files_verified': len(rows), 'installation_passed': True,
            'model_ready': True, 'startup_canary_passed': True,
            'study_calls': 2, 'game_actions': 0, 'episodes_completed': 0,
            'prediction_response': prediction['response'],
            'prediction_prompt_tokens': prediction['server_prompt_tokens'],
            'prediction_completion_tokens': prediction['server_completion_tokens'],
            'monitor_samples': len(telemetry['samples']),
            'trajectory_replay_rejected_incomplete_pair': True,
            'independent_gpu_cleanup_verified': True, 'process_groups_exited': True,
            'dependency_trees_removed': True, 'first_cell_elapsed_seconds': cost['elapsed_seconds'],
            'account_gpu_time_used_before_seconds': before,
            'account_gpu_time_used_after_seconds': after,
            'account_gpu_time_used_delta_seconds': round(after - before, 6),
            'exact_provider_billed_seconds': None, 'phase4_complete': False,
            'automatic_retry_authorized': False}


if __name__ == '__main__':
    result = evaluate()
    with RESULT.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(result, sort_keys=True))
