"""Independently evaluate the consumed Stage B R8 provider evidence."""
import hashlib
import json
from pathlib import Path

from certification.phase4_integrated_v2.monitor import validate_binding
from certification.phase4_integrated_v2.telemetry import read_telemetry
from research.grounded_action_v1.artifact_contract import expected_artifact
from research.grounded_action_v1.bridge_service import validate_ready
from research.grounded_action_v1.replay import replay_file

ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD = ROOT / 'reports/runs/phase4-grounded-action-v1-r8/download'
MANIFEST = ROOT / 'reports/perception_stage_b_r8_download.json'
RESULT = ROOT / 'reports/perception_stage_b_r8_evaluation.json'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def read(download, name):
    path = download / ('phase4-grounded-action-v1/' + name)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 4 * 1024**2,
            'missing or oversized provider evidence: ' + name)
    return json.loads(path.read_bytes())


def evaluate(download=DOWNLOAD, manifest_path=MANIFEST, record_root=ROOT):
    download, manifest_path, record_root = map(Path, (download, manifest_path, record_root))
    manifest = json.loads(manifest_path.read_bytes())
    require(manifest['kernel'] == 'daichongwei06/arc3-grounded-action-v1-r8' and
            manifest['requested_version'] == 1 and manifest['file_count'] == len(manifest['files']),
            'provider version/inventory binding')
    rows = manifest['files']
    paths = {row['path'] for row in rows}
    require(len(paths) == len(rows) and paths ==
            {path.relative_to(download).as_posix() for path in download.rglob('*') if path.is_file()},
            'provider output inventory')
    for row in rows:
        relative = Path(row['path'])
        require(not relative.is_absolute() and '..' not in relative.parts,
                'unsafe provider path')
        path = download / relative
        require(path.is_file() and not path.is_symlink(), 'missing provider file')
        raw = path.read_bytes()
        require(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'],
                'provider hash/size mismatch: ' + row['path'])

    launch = json.loads((record_root / 'reports/perception_stage_b_r8_launch.json').read_bytes())
    reservation = json.loads((record_root / 'research/grounded_action_v1/reservation_r8.json').read_bytes())
    execution = json.loads((record_root / 'research/grounded_action_v1/execution_lock_r8.json').read_bytes())
    prelaunch = json.loads((record_root / 'reports/perception_stage_b_r8_prelaunch.json').read_bytes())
    observations = [json.loads(line) for line in
        (record_root / 'reports/runs/phase4-grounded-action-v1-r8/provider-observations.jsonl').read_text().splitlines()]
    require(observations and launch['attempt_id'] == reservation['attempt_id'] ==
            execution['attempt_id'] == prelaunch['attempt_id'] == manifest['attempt_id'] and
            launch['provider_version'] == 1 and launch['attempt_consumed'] is True and
            launch['automatic_retry_authorized'] is False and
            reservation['status'] == 'consumed' and
            observations[-1]['status'] == 'KernelWorkerStatus.COMPLETE',
            'attempt/provider binding')
    review = record_root / 'notebooks/phase4-grounded-action-v1-launch-r11/review-source-lock.json'
    package = record_root / 'notebooks/phase4-grounded-action-v1-run-r8/launch-package-lock.json'
    package_lock = json.loads(package.read_bytes())
    require(execution['review_lock_sha256'] == package_lock['review_lock_sha256'] ==
            hashlib.sha256(review.read_bytes()).hexdigest() and
            package_lock['attempt_id'] == launch['attempt_id'] and
            package_lock['authorized_seconds'] == 3600 and
            package_lock['automatic_retries'] == 0,
            'review/package binding')

    installation = read(download, 'control/installation.json')
    cost = read(download, 'control/notebook-cost.json')
    outer = read(download, 'control/outer.json')
    gpu = read(download, 'control/gpu-cleanup.json')
    parent = read(download, 'control/first-cell-supervisor-cleanup.json')
    stop = read(download, 'control/stop-monitor.json')
    model = read(download, 'worker/model-ready.json')
    canary = read(download, 'worker/canary.json')
    worker = read(download, 'worker/worker-result.json')
    trajectory = read(download, 'worker/trajectory.json')
    ready = read(download, 'monitor/ready.json')
    monitor = read(download, 'monitor/monitor-result.json')
    telemetry = read_telemetry(download / 'phase4-grounded-action-v1/monitor')
    require(installation['passed'] is True and cost['dependency_trees_removed'] is True and
            cost['error'] is None and cost['study_status'] ==
            'development_study_complete_pending_archive_review', 'installation/finalization')
    require(outer['status'] == 'development_study_complete_pending_archive_review' and
            outer['error'] is None and
            outer['worker_released'] is True and outer['process_groups_exited'] is True and
            outer['independent_gpu_cleanup_verified'] is True and outer['scratch_removed'] is True and
            outer['elapsed_seconds'] < outer['internal_seconds'] == 3300 and
            outer['admission_cutoff_seconds'] == 3000, 'supervisor deadline/cleanup')
    require(gpu['gpu_cleanup_verified'] is True and gpu['groups_absent'] is True and
            gpu['remaining_gpu_pids'] == 0 and gpu['gpu_uuid'] == validate_binding(ready['gpu_binding']) and
            parent['drain_finished'] is True and parent['errors'] == [] and
            parent['returncode'] == 0 and parent['groups'] and
            all(value is True for value in parent['groups'].values()) and
            stop['worker_group_exited'] is True, 'independent process/GPU cleanup')
    require(monitor['status'] == 'live_monitor_completed' and monitor['error'] is None and
            telemetry['status'] == monitor['status'] and telemetry['error'] is None and
            telemetry['samples'] and ready['sample'] == telemetry['samples'][0] and
            telemetry['gpu_binding'] == ready['gpu_binding'], 'monitor evidence')
    require(model['artifact'] == expected_artifact(), 'model artifact binding')
    validate_ready({'artifact': model['artifact'], 'startup_seconds': model['startup_seconds'],
                    'canary_audit': canary}, expected_artifact())
    require(trajectory['version'] == 'grounded_action_local_v4' and
            trajectory['kind'] == 'offline_development_engine' and
            trajectory['status'] == 'complete' and trajectory['error'] is None and
            trajectory['calls'] == 12 and trajectory['dispatches'] == 4,
            'study completion/call ceiling')
    independent = replay_file(download / 'phase4-grounded-action-v1/worker/trajectory.json')
    require(independent['status'] == 'valid_offline_development_pair' and
            independent == worker['replay'] == outer['replay'] and
            worker['status'] == 'complete',
            'independent trajectory replay')
    require([episode['arm'] for episode in independent['episodes']] == ['control', 'target'] and
            all(episode['actions'] == 2 for episode in independent['episodes']),
            'matched episode horizon')

    before = prelaunch['gpu_quota_seconds']['time_used']
    after = observations[-1]['gpu_quota_seconds']['time_used']
    return {'status': 'verified_complete_development_pair',
            'attempt_id': launch['attempt_id'], 'provider_status': observations[-1]['status'],
            'downloaded_files_verified': len(rows), 'model_ready': True,
            'startup_canary_passed': True, 'study_calls': independent['calls'],
            'game_actions': independent['dispatches'], 'prompt_tokens': independent['prompt_tokens'],
            'completion_tokens': independent['completion_tokens'],
            'episodes': independent['episodes'], 'monitor_samples': len(telemetry['samples']),
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
    print(json.dumps({key: value for key, value in result.items() if key != 'episodes'}, sort_keys=True))
