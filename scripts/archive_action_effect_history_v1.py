"""Portable checked archive and read-only replay for the completed action-effect history v1 attempt.

observe   records read-only Kaggle status and GPU quota for the consumed attempt;
manifest  hashes the downloaded provider output into a download manifest (written once);
archive   builds the zip and its lock after re-running the independent evaluator;
replay    extracts the archive to a temporary folder, re-verifies every member and re-runs the
          independent evaluator, which must reproduce the archived evaluation exactly.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = 'aeh1-4c75150a156640fcad105a770ce81119'
URL = 'https://www.kaggle.com/code/daichongwei06/arc3-action-effect-history-v1'
RUN = 'reports/runs/action-effect-history-v1'
DOWNLOAD = ROOT / RUN / 'download'
OUTPUT = 'action-effect-history-v1'  # the notebook's output tree inside the download
ARCHIVE = ROOT / 'evidence/action-effect-history-v1-complete.zip'
LOCK = ROOT / 'reports/action_effect_history_v1_archive.json'
MANIFEST = ROOT / 'reports/action_effect_history_v1_download.json'
EVALUATION = ROOT / 'reports/action_effect_history_v1_live_evaluation.json'
RECORDS = (
    'reports/action_effect_history_v1_download.json',
    'reports/action_effect_history_v1_live_evaluation.json',
    'reports/action_effect_history_v1_results.md',
    'reports/action_effect_history_v1_launch.json',
    'reports/action_effect_history_v1_launch_claim.json',
    'reports/action_effect_history_v1_prelaunch.json',
    'reports/action_effect_history_v1_source_approval.json',
    'reports/action_effect_history_v1_compute_authorization.json',
    RUN + '/provider-observations.jsonl',
    'research/action_effect_history_v1/execution_lock.json',
    'research/action_effect_history_v1/reservation.json',
    'notebooks/action-effect-history-v1-run/launch-package-lock.json',
    'notebooks/action-effect-history-v1-review-r3/review-source-lock.json',
)
EVALUATION_BINDINGS = ('attempt_id', 'run_manifest_sha256')  # added to the saved evaluation, not evaluator output


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def evaluate_tree(download):
    from scripts.evaluate_action_effect_history_v1 import evaluate_output
    return canonical(evaluate_output(Path(download) / OUTPUT, mode='live'))


def saved_evaluation(root=ROOT):
    saved = json.loads((Path(root) / EVALUATION.relative_to(ROOT)).read_bytes())
    if saved.get('attempt_id') != ATTEMPT:
        raise ValueError('saved evaluation belongs to another attempt')
    return {k: v for k, v in saved.items() if k not in EVALUATION_BINDINGS}, saved


def observe():
    launch = json.loads((ROOT / 'reports/action_effect_history_v1_launch.json').read_bytes())
    if launch.get('attempt_consumed') is not True or launch.get('attempt_id') != ATTEMPT or launch.get('url') != URL:
        raise ValueError('launch receipt is not the accepted attempt')
    from scripts.phase4_install_kaggle import environment
    env = environment()
    for key in ('KAGGLE_API_TOKEN', 'KAGGLE_USERNAME', 'KAGGLE_KEY'):
        if env.get(key):
            os.environ[key] = env[key]
    import requests
    original = requests.Session.send

    def send(session, request, **kwargs):
        kwargs.update(timeout=(10, 30), allow_redirects=False)
        return original(session, request, **kwargs)

    requests.Session.send = send
    from kaggle import api
    status = api.kernels_status(URL.split('/code/', 1)[1])
    row = {'observed_at': now(), 'attempt_id': ATTEMPT, 'url': URL,
           'provider_version': launch['provider_version'], 'status': str(status.status),
           'failure_message': (status.failure_message or '')[:1000]}
    try:
        quota = api.quota_view().gpu_quota
        row['gpu_quota_seconds'] = {k: getattr(quota, k).total_seconds()
                                    for k in ('time_used', 'time_reserved', 'total_time_allowed')}
    except Exception as exc:
        row['quota_error'] = type(exc).__name__
    (ROOT / RUN).mkdir(parents=True, exist_ok=True)
    with (ROOT / RUN / 'provider-observations.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, sort_keys=True) + '\n')
    return row


def manifest():
    files = []
    for path in sorted(p for p in DOWNLOAD.rglob('*') if not p.is_dir()):
        if path.is_symlink():
            raise ValueError('symlink in provider download')
        raw = path.read_bytes()
        files.append({'path': path.relative_to(DOWNLOAD).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)})
    run_manifest = f'{OUTPUT}/worker/run/manifest.json'
    value = {'attempt_id': ATTEMPT, 'url': URL, 'provider_version': 1, 'recorded_at': now(),
             'file_count': len(files), 'total_bytes': sum(f['bytes'] for f in files), 'files': files,
             'run_manifest_sha256': next(f['sha256'] for f in files if f['path'] == run_manifest)}
    with MANIFEST.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
    return {k: v for k, v in value.items() if k != 'files'}


def entries():
    listing = json.loads(MANIFEST.read_bytes())
    if listing['file_count'] != len(listing['files']) or listing['attempt_id'] != ATTEMPT:
        raise ValueError('download inventory')
    present = {p.relative_to(DOWNLOAD).as_posix() for p in DOWNLOAD.rglob('*') if not p.is_dir()}
    if present != {row['path'] for row in listing['files']}:
        raise ValueError('download differs from its manifest')
    result = {}
    for row in listing['files']:
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('unsafe provider path')
        path = DOWNLOAD / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing provider file')
        raw = path.read_bytes()
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise ValueError('provider hash/size mismatch: ' + row['path'])
        result[f'{RUN}/download/{relative.as_posix()}'] = raw
    for name in RECORDS:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing local record: ' + name)
        result[name] = path.read_bytes()
    return result


def archive():
    verdict = evaluate_tree(DOWNLOAD)
    expected, saved = saved_evaluation()
    if verdict != expected:
        raise ValueError('evaluation drift before archive')
    listing = json.loads(MANIFEST.read_bytes())
    if saved['run_manifest_sha256'] != listing['run_manifest_sha256']:
        raise ValueError('saved evaluation is bound to another run manifest')
    result = entries()
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with ARCHIVE.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w') as bundle:
            for name, raw in sorted(result.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, raw, compresslevel=9)
    lock = {'attempt_id': ATTEMPT, 'archive': ARCHIVE.relative_to(ROOT).as_posix(),
            'archive_sha256': sha(ARCHIVE.read_bytes()),
            'run_manifest_sha256': listing['run_manifest_sha256'],
            'members': {name: {'bytes': len(raw), 'sha256': sha(raw)} for name, raw in sorted(result.items())},
            'evaluation': verdict}
    with LOCK.open('x', encoding='utf-8') as stream:
        json.dump(lock, stream, sort_keys=True, indent=2)
        stream.write('\n')
    return replay()


def extract(lock, target):
    archive_path = ROOT / lock['archive']
    if sha(archive_path.read_bytes()) != lock['archive_sha256']:
        raise ValueError('archive hash mismatch')
    with zipfile.ZipFile(archive_path) as bundle:
        if set(bundle.namelist()) != set(lock['members']):
            raise ValueError('archive inventory')
        for name, row in lock['members'].items():
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts or name.endswith('/'):
                raise ValueError('unsafe archive member')
            raw = bundle.read(name)
            if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
                raise ValueError('archive member hash/size mismatch: ' + name)
            path = Path(target) / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)


def replay():
    lock = json.loads(LOCK.read_bytes())
    with tempfile.TemporaryDirectory() as folder:
        extract(lock, folder)
        verdict = evaluate_tree(Path(folder) / RUN / 'download')
        archived_expected, _ = saved_evaluation(folder)
        if verdict != lock['evaluation'] or verdict != archived_expected:
            raise ValueError('archived independent evaluation drift')
        evaluation = verdict['evaluation']
        return {'status': 'archive_verified', 'archive_sha256': lock['archive_sha256'],
                'files': len(lock['members']), 'technically_complete': verdict['technically_complete'],
                'replay_passed': evaluation['replay_passed'], 'behaviour_result': evaluation['behaviour_result'],
                'solving_result': evaluation['solving_result'], 'run_status': evaluation['run_status']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('observe', 'manifest', 'archive', 'replay'))
    args = parser.parse_args()
    print(json.dumps({'observe': observe, 'manifest': manifest, 'archive': archive, 'replay': replay}[args.operation](),
                     sort_keys=True))
