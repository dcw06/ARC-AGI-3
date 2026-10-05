"""Gather upstream licence texts for the wheels that ship none (licence-review preparation; reads archives as data).

For each listed artifact the source is, in order of preference:
  1. the package's own source distribution on PyPI for the exact version, verified against PyPI's recorded SHA-256
     before it is opened; only licence/notice members are read (no code is extracted or run);
  2. the licence notice embedded in a named source file of that verified sdist (e.g. a header comment);
  3. otherwise the upstream repository's licence file at a release tag whose name matches the version (recorded as
     such; the tag-to-version mapping is an assumption for the reviewer to confirm).
Texts are written to reports/wheelhouse_upstream_licenses/<artifact>/ with an index recording each file's source URL,
source hash, member path and SHA-256. Bounded: size caps, timeouts, https only, no installs.

  python scripts/gather_upstream_licenses.py
"""
import hashlib
import io
import json
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.extract_wheelhouse_licenses import is_licence_member  # noqa: E402

OUT = ROOT / 'reports/wheelhouse_upstream_licenses'
INDEX = OUT / 'index.json'
SDIST_CAP = 16 * 1024 ** 2
TEXT_CAP = 2 * 1024 ** 2
TIMEOUT = 60
GH = 'https://raw.githubusercontent.com/'
# artifact -> (PyPI project, version, source file whose header holds the licence, repository URL at the release tag)
TARGETS = {
    'flashinfer_cubin-0.6.6-py3-none-any.whl': ('flashinfer-cubin', '0.6.6', None, GH + 'flashinfer-ai/flashinfer/v0.6.6/LICENSE'),
    'loguru-0.7.3-py3-none-any.whl': ('loguru', '0.7.3', None, GH + 'Delgan/loguru/0.7.3/LICENSE'),
    'mistral_common-1.11.1-py3-none-any.whl': ('mistral-common', '1.11.1', None, GH + 'mistralai/mistral-common/v1.11.1/LICENCE'),
    'model_hosting_container_standards-0.1.14-py3-none-any.whl': (
        'model-hosting-container-standards', '0.1.14', None, GH + 'aws/model-hosting-container-standards/v0.1.14/LICENSE'),
    'nvidia_ml_py-13.595.45-py3-none-any.whl': ('nvidia-ml-py', '13.595.45', 'pynvml.py', None),
    'opentelemetry_semantic_conventions_ai-0.5.1-py3-none-any.whl': (
        'opentelemetry-semantic-conventions-ai', '0.5.1', None, GH + 'traceloop/openllmetry/v0.5.1/LICENSE'),
    'sentencepiece-0.2.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl': ('sentencepiece', '0.2.1', None, None),
    'supervisor-4.3.0-py2.py3-none-any.whl': ('supervisor', '4.3.0', None, None),
    'tokenizers-0.22.2-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl': ('tokenizers', '0.22.2', None, None),
}
# sdist members read in addition to the licence-name pattern (named explicitly, recorded in the index)
EXTRA_MEMBERS = {
    # COPYRIGHT.txt names the holders only; the BSD-derived (Repoze) terms are in LICENSES.txt, which the pattern misses
    'supervisor-4.3.0-py2.py3-none-any.whl': ['LICENSES.txt'],
}


def embedded_header(data, filename, source_file):
    """The leading comment block of `source_file` inside a verified .tar.gz sdist (the licence notice)."""
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as t:
        for member in t.getmembers():
            if member.isfile() and Path(member.name).name == source_file and member.size <= TEXT_CAP:
                lines = []
                for line in t.extractfile(member).read().decode('utf-8', 'replace').splitlines():
                    if not line.startswith('#') and lines:
                        break
                    if line.startswith('#'):
                        lines.append(line)
                return member.name, ('\n'.join(lines) + '\n').encode('utf-8')
    return None


def fetch(url, cap):
    if not url.startswith('https://'):
        raise ValueError(f'refused non-https URL {url}')
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'arc-agi-3-licence-review'}),
                                timeout=TIMEOUT) as response:
        data = response.read(cap + 1)
    if len(data) > cap:
        raise ValueError(f'{url} exceeds {cap} bytes')
    return data


def sdist_members(data, filename, extra=()):
    """(member path, bytes) for licence/notice members (plus the named `extra` basenames) of a .tar.gz or .zip sdist;
    nothing else is read."""
    out = []
    wanted = lambda name: is_licence_member(name) or Path(name).name in extra  # noqa: E731
    if filename.endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if wanted(info.filename) and info.file_size <= TEXT_CAP:
                    out.append((info.filename, z.read(info)))
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as t:
            for member in t.getmembers():
                if member.isfile() and member.size <= TEXT_CAP and wanted(member.name):
                    out.append((member.name, t.extractfile(member).read()))
    return out


def safe_name(member):
    return '__'.join(p for p in Path(member).parts if p not in ('', '.', '..'))


def gather():
    expected_artifacts = {a['filename'] for a in json.loads((ROOT / 'reports/wheelhouse_download_manifest.json')
                                                            .read_text(encoding='utf-8'))['artifacts']}
    index = []
    for artifact, (project, version, source_file, fallback) in sorted(TARGETS.items()):
        if artifact not in expected_artifacts:
            raise SystemExit(f'{artifact} is not in the approved manifest')
        entry = {'artifact': artifact, 'project': project, 'version': version, 'files': []}
        info = json.loads(fetch(f'https://pypi.org/pypi/{project}/{version}/json', 4 * 1024 ** 2))
        sdists = [u for u in info['urls'] if u['packagetype'] == 'sdist']
        if sdists:
            s = sdists[0]
            data = fetch(s['url'], SDIST_CAP)
            if hashlib.sha256(data).hexdigest() != s['digests']['sha256']:
                raise SystemExit(f"{s['filename']}: SHA-256 differs from PyPI's record")
            entry['source'] = {'kind': 'pypi_sdist', 'url': s['url'], 'filename': s['filename'],
                               'sha256': s['digests']['sha256']}
            if artifact in EXTRA_MEMBERS:
                entry['source']['extra_members_named'] = EXTRA_MEMBERS[artifact]
            members = sdist_members(data, s['filename'], EXTRA_MEMBERS.get(artifact, ()))
            if not members and source_file:
                found = embedded_header(data, s['filename'], source_file)
                if found:
                    member, header = found
                    members = [(member + '.licence-header.txt', header)]
                    entry['source']['note'] = f'licence notice embedded in the header of {member} (the same file ships in the wheel)'
        else:
            members = []
        if not members and fallback:
            text = fetch(fallback, TEXT_CAP)
            entry['source'] = {'kind': 'repository_file_at_release_tag', 'url': fallback,
                               'sha256': hashlib.sha256(text).hexdigest(),
                               'note': ('licence file at the release tag matching the version (no licence file in a '
                                        'PyPI sdist for this version); the tag-to-version mapping and that the '
                                        'repository-level licence covers this package are for the reviewer to confirm')}
            members = [(fallback.rsplit('/', 1)[-1], text)]
        folder = OUT / artifact
        folder.mkdir(parents=True, exist_ok=True)
        for member, raw in members:
            name = safe_name(member)
            (folder / name).write_bytes(raw)
            entry['files'].append({'member': member, 'path': f'{artifact}/{name}', 'size': len(raw),
                                   'sha256': hashlib.sha256(raw).hexdigest()})
        entry['found'] = bool(entry['files'])
        index.append(entry)
    INDEX.write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    return index


if __name__ == '__main__':
    result = gather()
    for e in result:
        print(f"{e['artifact']}: {e.get('source', {}).get('kind', 'none')} -> "
              f"{[f['member'] for f in e['files']] or 'NOTHING FOUND'}")
    sys.exit(0 if all(e['found'] for e in result) else 1)
