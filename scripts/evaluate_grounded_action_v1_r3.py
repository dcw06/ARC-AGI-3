"""Independently classify the consumed Stage B R3 provider evidence."""
import hashlib
import json
from pathlib import Path

from certification.phase4_integrated_v2.monitor import validate_binding
from certification.phase4_integrated_v2.telemetry import read_telemetry
from research.grounded_action_v1.artifact_contract import expected_artifact
from research.grounded_action_v1.bridge_service import validate_ready
from research.grounded_action_v1.replay import replay_file


ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD = ROOT / 'reports/runs/phase4-grounded-action-v1-r3/download'
MANIFEST = ROOT / 'reports/perception_stage_b_r3_download.json'
RESULT = ROOT / 'reports/perception_stage_b_r3_evaluation.json'
ERROR_PREFIX = "ValueError: Key backend: 'module://matplotlib_inline.backend_inline' is not a valid value for backend"


def read(relative, download=DOWNLOAD):
    path = download / relative
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024**2:
        raise ValueError('missing/oversized downloaded evidence: ' + relative)
    return json.loads(path.read_bytes())


def evaluate(download=DOWNLOAD, manifest_path=MANIFEST, record_root=ROOT):
    download, manifest_path, record_root = Path(download), Path(manifest_path), Path(record_root)
    manifest = json.loads(manifest_path.read_bytes())
    if manifest['kernel'] != 'daichongwei06/arc3-grounded-action-v1-r3' or manifest['requested_version'] != 1:
        raise ValueError('provider version binding')
    files = manifest['files']
    if len(files) != manifest['file_count'] or len({row['path'] for row in files}) != len(files):
        raise ValueError('download inventory')
    actual = {p.relative_to(download).as_posix() for p in download.rglob('*') if p.is_file()}
    if actual != {row['path'] for row in files}:
        raise ValueError('download file set')
    for row in files:
        path = download / row['path']
        if path.is_symlink() or not path.is_file():
            raise ValueError('unsafe downloaded file')
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('download hash/size mismatch: ' + row['path'])
    launch = json.loads((record_root / 'reports/perception_stage_b_r3_launch.json').read_bytes())
    reservation = json.loads((record_root / 'research/grounded_action_v1/reservation_r3.json').read_bytes())
    prelaunch = json.loads((record_root / 'reports/perception_stage_b_r3_prelaunch.json').read_bytes())
    observations = [json.loads(line) for line in
        (record_root / 'reports/runs/phase4-grounded-action-v1-r3/provider-observations.jsonl').read_text().splitlines()]
    if not (launch['attempt_id'] == reservation['attempt_id'] == prelaunch['attempt_id'] ==
            manifest['attempt_id'] and launch['provider_version'] == 1 and
            launch['attempt_consumed'] is True and reservation['status'] == 'consumed' and
            launch['automatic_retry_authorized'] is False and
            observations[-1]['status'] == 'KernelWorkerStatus.ERROR'):
        raise ValueError('attempt/provider binding')
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
    if not installation['passed'] or not cost['dependency_trees_removed']:
        raise ValueError('installation/temporary-dependency cleanup')
    if not (outer['status'] == 'failed' and outer['error'] == 'RuntimeError: game worker failed' and
            outer['worker_released'] is True and outer['process_groups_exited'] is True and
            outer['independent_gpu_cleanup_verified'] is True and outer['scratch_removed'] is True and
            outer['elapsed_seconds'] < outer['internal_seconds'] == 3300):
        raise ValueError('supervisor failure/cleanup record')
    if not (gpu['gpu_cleanup_verified'] is True and gpu['groups_absent'] is True and
            gpu['remaining_gpu_pids'] == 0 and gpu['gpu_uuid'] == validate_binding(ready['gpu_binding'])):
        raise ValueError('independent GPU cleanup record')
    if not (parent['drain_finished'] is True and parent['errors'] == [] and
            parent['returncode'] == 1 and parent['groups'] and
            all(value is True for value in parent['groups'].values())):
        raise ValueError('first-cell process-group cleanup record')
    if not telemetry['samples'] or ready['sample'] != telemetry['samples'][0]:
        raise ValueError('monitor readiness/telemetry')
    if model['artifact'] != expected_artifact():
        raise ValueError('frozen model artifact')
    validate_ready({'artifact': model['artifact'],
                    'startup_seconds': model['startup_seconds'],
                    'canary_audit': canary}, expected_artifact())
    if not (trajectory['status'] == 'failed' and trajectory['kind'] == 'offline_development_engine' and
            trajectory['calls'] == trajectory['dispatches'] == 0 and trajectory['episodes'] == [] and
            trajectory['error'].startswith(ERROR_PREFIX) and
            worker_failure['error'].startswith('RuntimeError: Stage B study failed: ' + ERROR_PREFIX) and
            cost['error'].startswith('RuntimeError: target supervisor failed: RuntimeError: game worker failed')):
        raise ValueError('study failure classification')
    try:
        replay_file(download / base / 'worker/trajectory.json')
    except ValueError as exc:
        if 'incomplete pair' not in str(exc):
            raise
    else:
        raise ValueError('incomplete trajectory incorrectly passed replay')
    before = prelaunch['gpu_quota_seconds']['time_used']
    after = observations[-1]['gpu_quota_seconds']['time_used']
    return {'status': 'verified_pre_action_environment_failure',
            'attempt_id': launch['attempt_id'], 'provider_status': observations[-1]['status'],
            'downloaded_files_verified': len(files), 'installation_passed': True,
            'model_ready': True, 'startup_canary_passed': True,
            'canary_prompt_tokens': canary['audit']['server_prompt_tokens'],
            'canary_completion_tokens': canary['audit']['server_completion_tokens'],
            'monitor_samples': len(telemetry['samples']),
            'study_calls': 0, 'game_actions': 0, 'episodes_completed': 0,
            'trajectory_replay_rejected_incomplete_pair': True,
            'independent_gpu_cleanup_verified': True,
            'process_groups_exited': True, 'dependency_trees_removed': True,
            'failure': trajectory['error'],
            'first_cell_elapsed_seconds': cost['elapsed_seconds'],
            'account_gpu_time_used_before_seconds': before,
            'account_gpu_time_used_after_seconds': after,
            'account_gpu_time_used_delta_seconds': round(after - before, 6),
            'exact_provider_billed_seconds': None, 'phase4_complete': False,
            'automatic_retry_authorized': False}


if __name__ == '__main__':
    value = evaluate()
    with RESULT.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(value, sort_keys=True))
