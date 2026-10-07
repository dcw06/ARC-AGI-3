"""Compare the trusted 174-wheel inventory with exact PyPI release records.

Read-only HTTPS metadata requests; never download/install wheels or contact
Kaggle. Retain raw responses separately for review. Hash identity establishes
release-file provenance evidence, not any licence or distribution permission.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'certification/direct_publisher_smoke_v1/trusted_manifest.json'
CAP = 4 * 1024 * 1024


def check_artifact(artifact, raw_dir):
    name, version = artifact['filename'].split('-')[:2]
    name = name.replace('_', '-')
    url = 'https://pypi.org/pypi/' + urllib.parse.quote(name, safe='') + '/' + urllib.parse.quote(version, safe='') + '/json'
    row = {'artifact': artifact['filename'], 'project': name, 'version': version, 'release_metadata_url': url,
           'expected_sha256': artifact['sha256'], 'expected_size': artifact['size'], 'verified': False}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'arc3-direct-use-evidence/1'})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(CAP + 1)
            if len(raw) > CAP or urllib.parse.urlsplit(response.url).hostname != 'pypi.org':
                raise ValueError('release response exceeds size/host boundary')
        raw_name = name + '-' + version + '.json'
        with (raw_dir / raw_name).open('xb') as stream:
            stream.write(raw)
        data = json.loads(raw)
        matches = [f for f in data.get('urls', []) if f.get('filename') == artifact['filename']]
        row.update(raw_metadata_file=raw_name, raw_metadata_sha256=hashlib.sha256(raw).hexdigest(),
                   listed_project=data['info']['name'], listed_version=data['info']['version'],
                   declared_author=data['info'].get('author'), organization=data.get('ownership', {}).get('organization'),
                   project_urls=data['info'].get('project_urls'))
        if len(matches) != 1:
            raise ValueError('expected wheel is not uniquely listed in this release')
        match = matches[0]
        row.update(listed_sha256=match['digests']['sha256'], listed_size=match['size'],
                   listed_download_url=match['url'], yanked=match.get('yanked'),
                   uploaded_at=match.get('upload_time_iso_8601'))
        row['verified'] = (row['listed_sha256'] == artifact['sha256'] and row['listed_size'] == artifact['size']
                           and row['listed_download_url'] == artifact['url']
                           and data['info']['version'] == version
                           and data['info']['name'].lower().replace('_', '-') == name.lower())
        if not row['verified']:
            row['error'] = 'release filename/hash/size/URL/project/version differs from the trusted manifest'
    except Exception as exc:
        row['error'] = f'{type(exc).__name__}: {str(exc)[:300]}'
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=MANIFEST,
                        help='exact retained manifest to compare; report hashes these input bytes')
    parser.add_argument('--raw-dir', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.raw_dir.mkdir(parents=True, exist_ok=False)
    manifest_raw = args.manifest.read_bytes()
    manifest = json.loads(manifest_raw)
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(lambda artifact: check_artifact(artifact, args.raw_dir), manifest['artifacts']))
    report = {'schema': 'direct_publisher_upstream_release_provenance_v1',
              'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'trusted_manifest_sha256': hashlib.sha256(manifest_raw).hexdigest(),
              'artifact_count': len(rows), 'release_file_matches': sum(r['verified'] for r in rows),
              'all_release_files_match': all(r['verified'] for r in rows), 'artifacts': rows,
              'limits': ['PyPI release identity does not establish publisher redistribution permission',
                         'author/project metadata is recorded evidence, not independent legal-authority proof',
                         'no wheels downloaded or executed; actual mounted-byte evidence remains separate',
                         'raw release metadata retained locally under the supplied raw directory'],
              'permission_cleared': False, 'gpu_launched': False}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('artifact_count', 'release_file_matches',
                                           'all_release_files_match', 'permission_cleared', 'gpu_launched')}, indent=2))
    return 0 if report['all_release_files_match'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
