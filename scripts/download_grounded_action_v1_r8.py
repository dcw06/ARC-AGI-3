"""Download the consumed Stage B R8 version once and hash every provider file."""
import hashlib
import json
import os
from pathlib import Path

from scripts.phase4_install_kaggle import environment, ROOT


def download():
    launch = json.loads((ROOT / 'reports/perception_stage_b_r8_launch.json').read_bytes())
    if launch.get('provider_version') != 1 or launch.get('attempt_consumed') is not True:
        raise ValueError('unbound Stage B R8 download')
    kernel = launch['url'].split('/code/', 1)[1]
    if kernel != 'daichongwei06/arc3-grounded-action-v1-r8':
        raise ValueError('unexpected Stage B R8 kernel')
    folder = ROOT / 'reports/runs/phase4-grounded-action-v1-r8/download'
    if folder.exists():
        raise FileExistsError('Stage B R8 download destination already exists')
    env = environment()
    for key in ('KAGGLE_API_TOKEN', 'KAGGLE_USERNAME', 'KAGGLE_KEY'):
        if env.get(key):
            os.environ[key] = env[key]
    from kaggle import api
    folder.mkdir(parents=True)
    files, token = api.kernels_output(kernel, str(folder), force=False,
                                      quiet=True, page_size=100)
    if token:
        raise RuntimeError('unconsumed Kaggle output pagination')
    rows = []
    for name in files:
        candidate = Path(name).resolve()
        if not candidate.is_relative_to(folder.resolve()) or not candidate.is_file() or candidate.is_symlink():
            raise ValueError('unsafe or missing provider file')
        raw = candidate.read_bytes()
        rows.append({'path': candidate.relative_to(folder).as_posix(),
                     'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    paths = [row['path'] for row in rows]
    if len(paths) != len(set(paths)):
        raise ValueError('duplicate provider output')
    manifest = {'kernel': kernel, 'requested_version': 1,
                'attempt_id': launch['attempt_id'], 'file_count': len(rows),
                'files': sorted(rows, key=lambda row: row['path'])}
    target = ROOT / 'reports/perception_stage_b_r8_download.json'
    with target.open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')
    return {'file_count': len(rows), 'total_bytes': sum(row['bytes'] for row in rows),
            'paths': paths}


if __name__ == '__main__':
    print(json.dumps(download(), sort_keys=True))
