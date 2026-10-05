"""Shared helpers for the wheelhouse licence evidence packs (review preparation; proposals, never decisions).

Local wheels are opened only after their SHA-256 matches the approved manifest. Every fetched source is retained
byte-for-byte under reports/wheelhouse_evidence/sources/ with its URL, retrieval date and SHA-256, so a pack can be
re-derived offline from what it retained."""
import datetime
import hashlib
import json
import re
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'reports/wheelhouse_evidence'
SOURCES = EVIDENCE / 'sources'
MANIFEST = ROOT / 'reports/wheelhouse_download_manifest.json'
WHEELHOUSE = Path.home() / '.local/share/agi/wheelhouse-r2'
CAP = 64 * 1024 ** 2
TIMEOUT = 60
UA = {'User-Agent': 'arc-agi-3-licence-review'}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def manifest_artifacts():
    return {a['filename']: a for a in json.loads(MANIFEST.read_text(encoding='utf-8'))['artifacts']}


def artifact_for(distribution):
    """The approved-manifest artifact whose filename starts with `distribution-` (normalised name)."""
    matches = [a for name, a in manifest_artifacts().items() if name.split('-')[0].lower() == distribution.lower()]
    if len(matches) != 1:
        raise SystemExit(f'{distribution}: expected exactly one artifact, found {len(matches)}')
    return matches[0]


def open_wheel(artifact, wheelhouse=WHEELHOUSE):
    """A ZipFile for a local wheel whose bytes match the approved manifest (refuses otherwise)."""
    path = Path(wheelhouse) / artifact['filename']
    data = path.read_bytes()
    if sha256_bytes(data) != artifact['sha256']:
        raise SystemExit(f"{artifact['filename']}: local wheel differs from the approved manifest")
    return zipfile.ZipFile(path)


def fetch(url, cap=CAP):
    if not url.startswith('https://'):
        raise ValueError(f'refused non-https URL {url}')
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=TIMEOUT) as response:
        data = response.read(cap + 1)
    if len(data) > cap:
        raise ValueError(f'{url} exceeds {cap} bytes')
    return data


def retain(name, url, data, kind='raw'):
    """Keep fetched bytes under sources/<name>; returns the provenance record."""
    if not re.fullmatch(r'[A-Za-z0-9._@+-]+', name):
        raise ValueError(f'unsafe source name {name!r}')
    SOURCES.mkdir(parents=True, exist_ok=True)
    (SOURCES / name).write_bytes(data)
    return {'file': f'sources/{name}', 'url': url, 'retrieved_on': datetime.date.today().isoformat(),
            'sha256': sha256_bytes(data), 'bytes': len(data), 'kind': kind}


def fetch_retained(name, url, cap=CAP):
    data = fetch(url, cap)
    return data, retain(name, url, data)


def try_fetch_retained(name, url, cap=CAP):
    """(data, record) or (None, failure record): a failed fetch is evidence of absence only if stated so."""
    try:
        return fetch_retained(name, url, cap)
    except Exception as exc:  # recorded, never silently treated as absence
        return None, {'url': url, 'error': f'{type(exc).__name__}: {str(exc)[:200]}',
                      'retrieved_on': datetime.date.today().isoformat()}


def pypi_release(project, version):
    data = fetch(f'https://pypi.org/pypi/{project}/{version}/json', 8 * 1024 ** 2)
    return json.loads(data)


def verified_sdist(project, version, name_prefix):
    """(bytes, record) of the exact-version sdist, verified against PyPI's SHA-256; (None, reason) if none."""
    info = pypi_release(project, version)
    sdists = [u for u in info['urls'] if u['packagetype'] == 'sdist']
    if not sdists:
        return None, {'project': project, 'version': version, 'sdist': None, 'reason': 'no sdist on PyPI'}
    s = sdists[0]
    data = fetch(s['url'])
    if sha256_bytes(data) != s['digests']['sha256']:
        raise SystemExit(f"{s['filename']}: SHA-256 differs from PyPI's record")
    record = {'project': project, 'version': version, 'sdist': s['filename'], 'url': s['url'],
              'sha256': s['digests']['sha256'], 'verified_against_pypi': True}
    return data, record


def html_text(raw):
    import html
    text = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', raw.decode('utf-8', 'replace'))
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', text)).split())


def write_pack(name, payload, markdown):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    payload = dict(payload, status='evidence for the designated reviewer; a proposal, not a decision',
                   prepared_on=datetime.date.today().isoformat())
    (EVIDENCE / f'{name}.json').write_text(json.dumps(payload, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    (EVIDENCE / f'{name}.md').write_text(markdown.rstrip() + '\n', encoding='utf-8')
    return payload
