"""Milestone A of the wheelhouse replacement plan: component-by-component diff of the original offline wheelhouse
against official PyPI release metadata (metadata only; no wheel is downloaded or installed).

Inputs:
- the original wheelhouse inventory retained in evidence/phase4-torch-version-repair.zip (SHA256SUMS and
  wheelhouse-manifest.json), accepted only if their hashes equal the ones pinned in config/model_manifest.yaml;
- https://pypi.org/pypi/<distribution>/<version>/json for every wheel (small JSON documents).

Output: reports/wheelhouse_replacement_audit_milestone_a.json (write-once unless --force).
Classification per component: identical (same filename and SHA-256 on PyPI), changed (same filename, different
SHA-256), missing (not obtainable from PyPI: the version, the filename, or a non-wheel file whose content was not
retained), unknown (metadata could not be fetched).
"""
import argparse
import datetime
import hashlib
import json
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'evidence/phase4-torch-version-repair.zip'
OUTPUT = ROOT / 'reports/wheelhouse_replacement_audit_milestone_a.json'


def pinned():
    engine = json.loads((ROOT / 'config/model_manifest.yaml').read_text(encoding='utf-8'))['engine']
    return {'SHA256SUMS': engine['wheelhouse_sha256s_manifest_sha256'],
            'wheelhouse-manifest.json': engine['wheelhouse_index_manifest_sha256']}, engine


def original_inventory():
    want, engine = pinned()
    found = {}
    with zipfile.ZipFile(ARCHIVE) as z:
        for name in z.namelist():
            base = name.rsplit('/', 1)[-1]
            if base in want:
                data = z.read(name)
                if hashlib.sha256(data).hexdigest() != want[base]:
                    raise SystemExit(f'{base} in {ARCHIVE.name} does not match the hash pinned in config/model_manifest.yaml')
                found[base] = data
    if set(found) != set(want):
        raise SystemExit('the retained original manifests are incomplete')
    manifest = json.loads(found['wheelhouse-manifest.json'])
    sums = {line.split(maxsplit=1)[1].lstrip('*'): line.split()[0]
            for line in found['SHA256SUMS'].decode().splitlines() if line.strip()}
    if {f['name']: f['sha256'] for f in manifest['files']} != sums:
        raise SystemExit('SHA256SUMS and wheelhouse-manifest.json disagree')
    return manifest, engine, hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()


def pypi(dist, version, cache):
    key = (dist.lower(), version)
    if key not in cache:
        url = f'https://pypi.org/pypi/{dist}/{version}/json'
        cache[key] = {'status': 'unfetched', 'urls': []}
        for _ in range(3):
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    cache[key] = {'status': 200, 'urls': json.loads(response.read().decode('utf-8'))['urls']}
                break
            except urllib.error.HTTPError as error:
                cache[key] = {'status': error.code, 'urls': []}
                break
            except OSError as error:
                cache[key] = {'status': f'error: {type(error).__name__}', 'urls': []}
                time.sleep(2)
        time.sleep(0.1)
    return cache[key]


def tags(filename):
    python, abi, platform = filename[:-4].split('-')[-3:]
    return {'python': python, 'abi': abi, 'platform': platform}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if OUTPUT.exists() and not args.force:
        raise SystemExit(f'{OUTPUT} exists (write-once); pass --force to regenerate')
    manifest, engine, archive_sha = original_inventory()
    cache, rows = {}, []
    for f in manifest['files']:
        name = f['name']
        row = {'file': name, 'size': f['size'], 'sha256': f['sha256']}
        if not name.endswith('.whl'):
            row.update(kind='non_wheel', verdict='missing',
                       reason='only the hash and size were retained; the content is not in the repository or its archives')
        else:
            dist, version = name.split('-')[:2]
            info = pypi(dist, version, cache)
            match = next((u for u in info['urls'] if u['filename'] == name), None)
            if info['status'] == 404:
                verdict = 'missing'
            elif info['status'] != 200:
                verdict = 'unknown'
            elif match is None:
                verdict = 'missing'
            else:
                verdict = 'identical' if match['digests']['sha256'] == f['sha256'] else 'changed'
            row.update(kind='wheel', distribution=dist, version=version, tags=tags(name), pypi_status=info['status'],
                       verdict=verdict, pypi_url=match['url'] if match else None,
                       pypi_upload_time=match['upload_time_iso_8601'] if match else None)
        rows.append(row)
    report = {
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        'scope': 'metadata-only comparison; no wheel downloaded, installed or executed; no GPU',
        'original': {'dataset': engine['wheelhouse'], 'retained_in': str(ARCHIVE.relative_to(ROOT)),
                     'archive_sha256': archive_sha, 'manifest_hashes_match_model_manifest': True,
                     'platform_label': manifest['platform'], 'python': manifest['python'],
                     'core_versions': manifest['core_versions'], 'install_command': manifest['install'],
                     'file_count': manifest['file_count']},
        'summary': dict(Counter(r['verdict'] for r in rows)),
        'wheel_bytes': sum(r['size'] for r in rows if r['kind'] == 'wheel'),
        'components': rows,
    }
    OUTPUT.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'summary': report['summary'], 'wheel_bytes': report['wheel_bytes']}))


if __name__ == '__main__':
    main()
