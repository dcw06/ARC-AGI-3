"""Portable checked archive and read-only replay for the Stage B R3 failure."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from scripts.evaluate_grounded_action_v1_r3 import evaluate


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'evidence/phase4-grounded-action-v1-r3-failure.zip'
LOCK = ROOT / 'reports/perception_stage_b_r3_archive.json'
MANIFEST = ROOT / 'reports/perception_stage_b_r3_download.json'
DOWNLOAD = ROOT / 'reports/runs/phase4-grounded-action-v1-r3/download'
RECORDS = (
    'reports/perception_stage_b_r3_download.json',
    'reports/perception_stage_b_r3_evaluation.json',
    'reports/perception_stage_b_r3_failure.md',
    'reports/perception_stage_b_r3_pilot_status.md',
    'reports/perception_stage_b_r3_launch.json',
    'reports/perception_stage_b_r3_launch_claim.json',
    'reports/perception_stage_b_r3_prelaunch.json',
    'reports/perception_stage_b_r3_source_approval.json',
    'reports/perception_stage_b_r3_compute_authorization.json',
    'reports/runs/phase4-grounded-action-v1-r3/provider-observations.jsonl',
    'research/grounded_action_v1/execution_lock_r3.json',
    'research/grounded_action_v1/reservation_r3.json',
    'notebooks/phase4-grounded-action-v1-run-r3/launch-package-lock.json',
    'notebooks/phase4-grounded-action-v1-launch-r6/review-source-lock.json',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def entries():
    manifest = json.loads(MANIFEST.read_bytes())
    if manifest['file_count'] != len(manifest['files']):
        raise ValueError('download inventory')
    result = {}
    for row in manifest['files']:
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('unsafe provider path')
        path = DOWNLOAD / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing provider file')
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise ValueError('provider hash/size mismatch')
        name = 'reports/runs/phase4-grounded-action-v1-r3/download/' + relative.as_posix()
        result[name] = raw
    for name in RECORDS:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing local record: ' + name)
        result[name] = path.read_bytes()
    return result


def archive():
    verdict = evaluate()
    expected = json.loads((ROOT / 'reports/perception_stage_b_r3_evaluation.json').read_bytes())
    if verdict != expected:
        raise ValueError('evaluation drift before archive')
    result = entries()
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
    with zipfile.ZipFile(archive_path) as bundle, tempfile.TemporaryDirectory() as folder:
        if set(bundle.namelist()) != set(lock['members']):
            raise ValueError('archive inventory')
        target = Path(folder)
        for name, row in lock['members'].items():
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts or name.endswith('/'):
                raise ValueError('unsafe archive member')
            raw = bundle.read(name)
            if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
                raise ValueError('archive member hash/size mismatch')
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        verdict = evaluate(
            download=target / 'reports/runs/phase4-grounded-action-v1-r3/download',
            manifest_path=target / 'reports/perception_stage_b_r3_download.json',
            record_root=target)
        if verdict != lock['evaluation']:
            raise ValueError('archived independent evaluation drift')
        return {'status': 'archive_verified', 'archive_sha256': lock['archive_sha256'],
                'files': len(lock['members']), 'evaluation_status': verdict['status'],
                'study_calls': verdict['study_calls'], 'game_actions': verdict['game_actions']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('archive', 'replay'))
    args = parser.parse_args()
    print(json.dumps(archive() if args.operation == 'archive' else replay(), sort_keys=True))
