"""Archive and read-only replay the failed, one-use Stage B R2 attempt."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'evidence/phase4-grounded-action-v1-r2-failure.zip'
LOCK = ROOT / 'reports/perception_stage_b_r2_archive.json'
DOWNLOAD = ROOT / 'reports/runs/phase4-grounded-action-v1-r2/download'
DOWNLOAD_LOCK = ROOT / 'reports/perception_stage_b_r2_download.json'
RECORDS = (
    'reports/perception_stage_b_r2_download.json',
    'reports/perception_stage_b_r2_failure_evaluation.json',
    'reports/perception_stage_b_r2_failure.md',
    'reports/perception_stage_b_r2_launch.json',
    'reports/perception_stage_b_r2_launch_claim.json',
    'reports/perception_stage_b_r2_prelaunch.json',
    'reports/perception_stage_b_r2_source_approval.json',
    'reports/perception_stage_b_r2_compute_authorization.json',
    'reports/runs/phase4-grounded-action-v1-r2/provider-observations.jsonl',
    'research/grounded_action_v1/execution_lock_r2.json',
    'research/grounded_action_v1/reservation_r2.json',
    'notebooks/phase4-grounded-action-v1-run-r2/launch-package-lock.json',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def entries():
    lock = json.loads(DOWNLOAD_LOCK.read_bytes())
    if lock['file_count'] != len(lock['files']) or lock['requested_version'] != 1:
        raise ValueError('download inventory')
    result = {}
    for row in lock['files']:
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('unsafe provider path')
        path = DOWNLOAD / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing provider file')
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise ValueError('provider hash/size mismatch')
        result[f'download/{relative.as_posix()}'] = raw
    for name in RECORDS:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing local record: ' + name)
        result[name] = path.read_bytes()
    return result


def validate(result):
    download = json.loads(result['reports/perception_stage_b_r2_download.json'])
    launch = json.loads(result['reports/perception_stage_b_r2_launch.json'])
    reservation = json.loads(result['research/grounded_action_v1/reservation_r2.json'])
    evaluation = json.loads(result['reports/perception_stage_b_r2_failure_evaluation.json'])
    installation = json.loads(result['download/phase4-grounded-action-v1/control/installation.json'])
    cost = json.loads(result['download/phase4-grounded-action-v1/control/notebook-cost.json'])
    observations = [json.loads(line) for line in result[
        'reports/runs/phase4-grounded-action-v1-r2/provider-observations.jsonl'].splitlines()]
    if (not launch['attempt_id'] or launch['attempt_id'] != reservation['attempt_id'] or
            launch['attempt_id'] != evaluation['attempt_id'] or
            launch['attempt_id'] != download['attempt_id']):
        raise ValueError('attempt binding')
    if not (launch['attempt_consumed'] and reservation['status'] == 'consumed' and
            launch['provider_version'] == 1 and launch['error'] == '' and
            installation['passed'] is True and
            cost['error'] == evaluation['failure'] and
            cost['study_status'] is None and cost['dependency_trees_removed'] is True):
        raise ValueError('failure classification evidence')
    if not any(row['status'] == 'KernelWorkerStatus.ERROR' for row in observations):
        raise ValueError('missing provider terminal status')
    if any(name.startswith('download/phase4-grounded-action-v1/worker/') or
           name.startswith('download/phase4-grounded-action-v1/monitor/') for name in result):
        raise ValueError('unexpected study evidence; use trajectory evaluator')
    if (evaluation['classification'] != 'pre_study_import_failure' or
            evaluation['trajectory_replay_applicable'] is not False or
            evaluation['independent_gpu_cleanup_verified'] is not False or
            evaluation['exact_provider_billed_seconds'] is not None):
        raise ValueError('disposition drift')
    before = json.loads(result['reports/perception_stage_b_r2_prelaunch.json'])['gpu_quota_seconds']['time_used']
    after = observations[-1]['gpu_quota_seconds']['time_used']
    if (abs(evaluation['account_gpu_time_used_before_seconds'] - before) > 1e-6 or
            abs(evaluation['account_gpu_time_used_after_seconds'] - after) > 1e-6 or
            abs(evaluation['account_gpu_time_used_delta_seconds'] - (after - before)) > 1e-3):
        raise ValueError('account-wide quota arithmetic')
    return {'status': 'verified_pre_study_import_failure',
            'attempt_id': launch['attempt_id'], 'downloaded_files': download['file_count'],
            'study_calls_observed': 0, 'game_actions_observed': 0,
            'account_gpu_time_used_delta_seconds': evaluation['account_gpu_time_used_delta_seconds'],
            'exact_provider_billed_seconds': None}


def archive():
    result = entries()
    verdict = validate(result)
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with ARCHIVE.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
            for name, raw in sorted(result.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, raw)
    lock = {'archive': ARCHIVE.relative_to(ROOT).as_posix(),
            'archive_sha256': sha(ARCHIVE.read_bytes()),
            'members': {name: {'bytes': len(raw), 'sha256': sha(raw)}
                        for name, raw in sorted(result.items())},
            'evaluation': verdict}
    with LOCK.open('x', encoding='utf-8') as stream:
        json.dump(lock, stream, sort_keys=True, indent=2)
        stream.write('\n')
    return replay()


def replay():
    lock = json.loads(LOCK.read_bytes())
    archive_path = ROOT / lock['archive']
    if sha(archive_path.read_bytes()) != lock['archive_sha256']:
        raise ValueError('archive hash mismatch')
    with zipfile.ZipFile(archive_path) as bundle:
        if set(bundle.namelist()) != set(lock['members']):
            raise ValueError('archive inventory')
        result = {}
        for name, row in lock['members'].items():
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts or name.endswith('/'):
                raise ValueError('unsafe archive member')
            raw = bundle.read(name)
            if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
                raise ValueError('archive member hash/size mismatch')
            result[name] = raw
    verdict = validate(result)
    if verdict != lock['evaluation']:
        raise ValueError('archived evaluation drift')
    return verdict


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('archive', 'replay'))
    args = parser.parse_args()
    print(json.dumps(archive() if args.operation == 'archive' else replay(), sort_keys=True))
