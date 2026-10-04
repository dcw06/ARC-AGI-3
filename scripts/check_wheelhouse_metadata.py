"""Metadata-only reconstruction check for the offline vLLM wheelhouse (wheelhouse replacement plan, step after
Milestone A). No wheel is ever requested, downloaded, installed or executed.

Three separable stages:

  inventory  Recover the original 179-file inventory from evidence/phase4-torch-version-repair.zip, trusting it only
             after its two manifests match the hashes pinned in config/model_manifest.yaml.
  acquire    NETWORK. For every wheel, query PyPI's Simple JSON API (PEP 691) for the exact filename and SHA-256,
             read its core-metadata reference (PEP 658/714), fetch only that metadata file and verify its hash.
             Bounded: host allow-list, no automatic redirects, size caps, deadlines, a fixed request budget, and a
             hard refusal of any URL that names a wheel. Writes a retained acquisition record (metadata included).
  analyze    OFFLINE. Evaluate the dependency closure of the install pins against an explicitly declared Linux
             x86-64 / CPython 3.12 target (every marker value supplied; no host default can leak in), compatible
             tags, Requires-Python, extras, duplicates and conflicts. Writes the JSON and Markdown reports.

Usage (from the repository root, in an environment with `packaging`):
  python scripts/check_wheelhouse_metadata.py acquire          # network, metadata only
  python scripts/check_wheelhouse_metadata.py analyze          # offline, from the retained acquisition record
  python scripts/check_wheelhouse_metadata.py analyze --check  # offline; fails if the committed reports differ
"""
import argparse
import email.parser
import gzip
import hashlib
import io
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.tags import Tag, compatible_tags, cpython_tags
from packaging.utils import InvalidWheelFilename, canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'evidence/phase4-torch-version-repair.zip'
ACQUISITION = ROOT / 'reports/wheelhouse_metadata_acquisition.json.gz'
REPORT_JSON = ROOT / 'reports/wheelhouse_metadata_closure.json'
REPORT_MD = ROOT / 'reports/wheelhouse_metadata_closure.md'

# --- declared target (never the host) -------------------------------------------------------------------------
# Values and their sources. python_full_version: the passing target install check
# (reports/phase4_v6_install_r5_evaluation.json, runtime.model.python). platform_release / platform_version: the
# target platform recorded in reports/phase4_split_dependency_audit.json. Every PEP 508 marker variable is supplied.
TARGET_ENVIRONMENT = {
    'implementation_name': 'cpython',
    'implementation_version': '3.12.13',
    'os_name': 'posix',
    'platform_machine': 'x86_64',
    'platform_python_implementation': 'CPython',
    'platform_release': '6.12.90+',
    'platform_system': 'Linux',
    'platform_version': '#1 SMP Sat May 30 15:40:53 UTC 2026',
    'python_full_version': '3.12.13',
    'python_version': '3.12',
    'sys_platform': 'linux',
}
# The minimum glibc the target is known to provide: the retained target install accepted
# cryptography-47.0.0-...-manylinux_2_34_x86_64.whl, which pip installs only on glibc >= 2.34. The exact target glibc
# is not retained; this lower bound is what the tag set is generated from.
TARGET_GLIBC = (2, 34)
TARGET_PYTHON = (3, 12)
# The current install path's pins (certification/phase4_v6/target_install_probe_r5.py MODEL_PINS; a test checks this).
ROOT_PINS = ('vllm==0.19.0', 'torch==2.10.0', 'transformers==4.57.6', 'numpy==2.2.6')

# --- network bounds ----------------------------------------------------------------------------------------------
INDEX_HOST, FILES_HOST = 'pypi.org', 'files.pythonhosted.org'
ALLOWED_HOSTS = {INDEX_HOST, FILES_HOST}
SIMPLE_JSON = 'application/vnd.pypi.simple.v1+json'
INDEX_CAP = 64 * 1024 ** 2        # bytes; the largest project indexes (e.g. torch) are tens of MB
METADATA_CAP = 4 * 1024 ** 2      # bytes; core metadata is normally tens of KB
CONNECT_READ_TIMEOUT = 30          # seconds per request
ATTEMPTS_PER_REQUEST = 3
MAX_REDIRECTS = 2


class FetchError(Exception):
    """A request that could not produce verified bytes. The caller records the item as unknown."""


class WheelRequestRefused(FetchError):
    pass


def is_wheel_url(url):
    path = urllib.parse.urlsplit(url).path.lower()
    return path.endswith('.whl') or '.whl/' in path


def check_url(url):
    parts = urllib.parse.urlsplit(url)
    if is_wheel_url(url):
        raise WheelRequestRefused(f'refused: the URL names a wheel ({url})')
    if parts.scheme != 'https' or parts.hostname not in ALLOWED_HOSTS or parts.port not in (None, 443) \
            or parts.username or parts.password:
        raise FetchError(f'refused: unexpected destination {url}')


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # surface 3xx to the caller, which validates the destination itself


class Client:
    """Bounded HTTPS GETs to the allow-listed PyPI hosts only."""

    def __init__(self, budget, opener=None, sleep=time.sleep):
        self.budget = budget
        self.requests = []          # every URL actually requested, for the record and for tests
        self._opener = opener or urllib.request.build_opener(_NoRedirect)
        self._sleep = sleep

    def get(self, url, cap, accept=None):
        for _ in range(MAX_REDIRECTS + 1):
            check_url(url)
            status, headers, body = self._attempts(url, cap, accept)
            if status in (301, 302, 303, 307, 308):
                location = headers.get('Location')
                if not location:
                    raise FetchError(f'redirect without a location from {url}')
                url = urllib.parse.urljoin(url, location)
                continue
            if status != 200:
                raise FetchError(f'HTTP {status} for {url}')
            return body, url
        raise FetchError(f'too many redirects from {url}')

    def _attempts(self, url, cap, accept):
        last = None
        for attempt in range(ATTEMPTS_PER_REQUEST):
            if self.budget <= 0:
                raise FetchError('request budget exhausted')
            self.budget -= 1
            self.requests.append(url)
            request = urllib.request.Request(url, headers={'User-Agent': 'arc-agi-3-wheelhouse-metadata-check'})
            if accept:
                request.add_header('Accept', accept)
            try:
                with self._opener.open(request, timeout=CONNECT_READ_TIMEOUT) as response:
                    declared = response.headers.get('Content-Length')
                    if declared is not None and declared.isdigit() and int(declared) > cap:
                        raise FetchError(f'declared size {declared} exceeds the {cap}-byte cap for {url}')
                    body = response.read(cap + 1)
                    if len(body) > cap:
                        raise FetchError(f'response exceeds the {cap}-byte cap for {url}')
                    if declared is not None and declared.isdigit() and len(body) != int(declared):
                        raise FetchError(f'truncated response for {url} ({len(body)} of {declared} bytes)')
                    return response.status, response.headers, body
            except urllib.error.HTTPError as error:
                if error.code in (301, 302, 303, 307, 308, 404, 410):
                    return error.code, error.headers, b''
                last = FetchError(f'HTTP {error.code} for {url}')
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as error:
                last = FetchError(f'{type(error).__name__} for {url}: {error}')
            self._sleep(2 ** attempt)
        raise last


# --- stage 1: inventory -----------------------------------------------------------------------------------------
def pinned_manifest_hashes():
    engine = json.loads((ROOT / 'config/model_manifest.yaml').read_text(encoding='utf-8'))['engine']
    return {'SHA256SUMS': engine['wheelhouse_sha256s_manifest_sha256'],
            'wheelhouse-manifest.json': engine['wheelhouse_index_manifest_sha256']}


def wheel_identity(filename):
    name, version, build, tags = parse_wheel_filename(filename)
    return {'distribution': str(name), 'version': str(version), 'build': ''.join(map(str, build)) if build else None,
            'tags': sorted(str(t) for t in tags)}


def inventory(archive=ARCHIVE):
    pinned = pinned_manifest_hashes()
    found = {}
    with zipfile.ZipFile(archive) as z:
        for member in z.namelist():
            base = member.rsplit('/', 1)[-1]
            if base in pinned:
                if base in found:
                    raise SystemExit(f'duplicate {base} in {archive.name}')
                data = z.read(member)
                if hashlib.sha256(data).hexdigest() != pinned[base]:
                    raise SystemExit(f'{base} does not match the hash pinned in config/model_manifest.yaml')
                found[base] = data
    if set(found) != set(pinned):
        raise SystemExit('the retained original manifests are incomplete')
    manifest = json.loads(found['wheelhouse-manifest.json'])
    sums = {}
    for line in found['SHA256SUMS'].decode().splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            sums[name.lstrip('*')] = digest
    if {f['name']: f['sha256'] for f in manifest['files']} != sums or len(sums) != manifest['file_count']:
        raise SystemExit('SHA256SUMS and wheelhouse-manifest.json disagree')
    wheels, other = [], []
    for f in sorted(manifest['files'], key=lambda f: f['name']):
        row = {'filename': f['name'], 'size': f['size'], 'sha256': f['sha256']}
        if f['name'].endswith('.whl'):
            wheels.append({**row, **wheel_identity(f['name'])})
        else:
            other.append(row)
    return {'archive': archive.relative_to(ROOT).as_posix() if archive.is_relative_to(ROOT) else str(archive),
            'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'manifest_hashes': pinned, 'manifests_verified': True,
            'original': {k: manifest[k] for k in ('dataset', 'platform', 'python', 'core_versions', 'install',
                                                  'file_count')},
            'wheels': wheels, 'non_wheel_files': other}


# --- stage 2: acquisition (network, metadata only) ------------------------------------------------------------
def index_url(distribution):
    return f'https://{INDEX_HOST}/simple/{canonicalize_name(distribution)}/'


def core_metadata_hash(entry):
    for key in ('core-metadata', 'data-dist-info-metadata'):
        value = entry.get(key)
        if isinstance(value, dict) and isinstance(value.get('sha256'), str):
            return value['sha256'], key
        if value is True:
            return None, key  # declared but without a hash: not verifiable
    return None, None


def acquire_one(wheel, client, index_cache):
    record = {'filename': wheel['filename'], 'index_url': index_url(wheel['distribution'])}
    try:
        if record['index_url'] not in index_cache:
            body, _ = client.get(record['index_url'], INDEX_CAP, accept=SIMPLE_JSON)
            index_cache[record['index_url']] = json.loads(body.decode('utf-8'))
        files = index_cache[record['index_url']].get('files', [])
    except (FetchError, ValueError) as error:
        return {**record, 'status': 'unknown', 'reason': f'index: {error}'}
    matches = [f for f in files if f.get('filename') == wheel['filename']]
    if not matches:
        return {**record, 'status': 'missing', 'reason': 'the exact filename is not in the index'}
    entry = matches[0]
    upstream_sha = (entry.get('hashes') or {}).get('sha256')
    record.update(upstream_url=entry.get('url'), upstream_sha256=upstream_sha,
                  yanked=bool(entry.get('yanked')))
    if upstream_sha != wheel['sha256']:
        return {**record, 'status': 'conflicting', 'reason': 'same filename, different SHA-256'}
    record['located'] = True  # exact filename and SHA-256 found upstream
    meta_sha, key = core_metadata_hash(entry)
    record['metadata_key'] = key
    if meta_sha is None:
        return {**record, 'status': 'unknown',
                'reason': 'no hash-bearing core-metadata reference; the wheel is not fetched as a fallback'}
    metadata_url = entry['url'] + '.metadata'
    record.update(metadata_url=metadata_url, metadata_sha256=meta_sha)
    try:
        body, final_url = client.get(metadata_url, METADATA_CAP)
    except FetchError as error:
        return {**record, 'status': 'unknown', 'reason': f'metadata: {error}'}
    if hashlib.sha256(body).hexdigest() != meta_sha:
        return {**record, 'status': 'unknown', 'reason': 'metadata hash mismatch'}
    return {**record, 'status': 'verified', 'metadata_final_url': final_url, 'metadata': body.decode('utf-8')}


def acquire(inv, client):
    cache, rows = {}, []
    for wheel in inv['wheels']:
        rows.append(acquire_one(wheel, client, cache))
    return {'acquired_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'index': f'https://{INDEX_HOST}/simple/ (PEP 691 JSON)',
            'bounds': {'index_cap_bytes': INDEX_CAP, 'metadata_cap_bytes': METADATA_CAP,
                       'timeout_seconds': CONNECT_READ_TIMEOUT, 'attempts_per_request': ATTEMPTS_PER_REQUEST,
                       'max_redirects': MAX_REDIRECTS, 'allowed_hosts': sorted(ALLOWED_HOSTS)},
            'requests_made': len(client.requests),
            'wheel_urls_requested': [u for u in client.requests if is_wheel_url(u)],
            'inventory_archive_sha256': inv['archive_sha256'], 'wheels': rows}


def write_acquisition(record, path=ACQUISITION):
    raw = json.dumps(record, indent=1, sort_keys=True).encode('utf-8')
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb', mtime=0, compresslevel=9) as stream:
        stream.write(raw)
    path.write_bytes(buffer.getvalue())


def read_acquisition(path=ACQUISITION):
    return json.loads(gzip.decompress(path.read_bytes()).decode('utf-8'))


# --- stage 3: offline analysis --------------------------------------------------------------------------------
def target_tags(python=TARGET_PYTHON, glibc=TARGET_GLIBC):
    major, minor = glibc
    platforms = [f'manylinux_{major}_{m}_x86_64' for m in range(minor, 4, -1)]
    legacy = {(2, 17): 'manylinux2014_x86_64', (2, 12): 'manylinux2010_x86_64', (2, 5): 'manylinux1_x86_64'}
    platforms += [alias for floor, alias in legacy.items() if (major, minor) >= floor]
    platforms.append('linux_x86_64')
    tags = list(cpython_tags(python_version=python, platforms=platforms))
    tags += list(compatible_tags(python_version=python, interpreter=f'cp{python[0]}{python[1]}', platforms=platforms))
    return set(tags)


def environment_for(extra=''):
    missing = set(default_environment()) - set(TARGET_ENVIRONMENT)
    if missing:
        raise SystemExit(f'target environment does not supply every marker variable: {sorted(missing)}')
    return {**TARGET_ENVIRONMENT, 'extra': extra}


def min_glibc(tags):
    best = None
    for tag in tags:
        m = re.match(r'manylinux_(\d+)_(\d+)_', tag.platform)
        legacy = {'manylinux2014': (2, 17), 'manylinux2010': (2, 12), 'manylinux1': (2, 5)}
        value = (int(m.group(1)), int(m.group(2))) if m else next(
            (v for k, v in legacy.items() if tag.platform.startswith(k + '_')), None)
        if value and (best is None or value < best):
            best = value
    return best


def parse_metadata(text):
    message = email.parser.Parser().parsestr(text, headersonly=True)
    licenses = [message.get('License-Expression'), message.get('License')]
    classifiers = [c for c in message.get_all('Classifier') or [] if c.startswith('License ::')]
    return {'name': message.get('Name'), 'version': message.get('Version'),
            'requires_python': message.get('Requires-Python'),
            'requires_dist': message.get_all('Requires-Dist') or [],
            'provides_extra': [canonicalize_name(e) for e in message.get_all('Provides-Extra') or []],
            'license': next((l.strip() for l in licenses if l and l.strip() and len(l.strip()) < 200), None),
            'license_classifiers': classifiers}


def applies(requirement, extras):
    if requirement.marker is None:
        return True
    return any(requirement.marker.evaluate(environment_for(e)) for e in [''] + sorted(extras))


def analyze(inv, acq, tags=None):
    tags = tags or target_tags()
    by_file = {row['filename']: row for row in acq['wheels']}
    wheels, problems = [], []
    by_name = {}
    for wheel in sorted(inv['wheels'], key=lambda w: w['filename']):  # order-independent report
        a = by_file.get(wheel['filename'], {'status': 'unknown', 'reason': 'not in the acquisition record'})
        row = {k: wheel[k] for k in ('filename', 'distribution', 'version', 'build', 'size', 'sha256', 'tags')}
        row.update(status=a['status'], reason=a.get('reason'), located=bool(a.get('located')),
                   upstream_url=a.get('upstream_url'),
                   metadata_url=a.get('metadata_url'), metadata_sha256=a.get('metadata_sha256'))
        wheel_tags = parse_wheel_filename(wheel['filename'])[3]
        row['tag_compatible'] = bool(wheel_tags & tags)
        glibc = min_glibc(wheel_tags)
        row['min_glibc'] = f'{glibc[0]}.{glibc[1]}' if glibc else None
        if not row['tag_compatible']:
            problems.append({'kind': 'incompatible_tags', 'filename': wheel['filename']})
        if a['status'] == 'verified':
            meta = parse_metadata(a['metadata'])
            row['metadata'] = {k: meta[k] for k in ('requires_python', 'license', 'license_classifiers')}
            if canonicalize_name(meta['name'] or '') != canonicalize_name(wheel['distribution']) or \
                    Version(meta['version']) != Version(wheel['version']):
                problems.append({'kind': 'metadata_identity_mismatch', 'filename': wheel['filename']})
            try:
                rp = SpecifierSet(meta['requires_python'] or '')
                row['requires_python_ok'] = rp.contains(TARGET_ENVIRONMENT['python_full_version'], prereleases=True)
            except InvalidSpecifier:
                row['requires_python_ok'] = False
            if not row['requires_python_ok']:
                problems.append({'kind': 'requires_python', 'filename': wheel['filename'],
                                 'requires_python': meta['requires_python']})
            row['_meta'] = meta
        wheels.append(row)
        by_name.setdefault(canonicalize_name(wheel['distribution']), []).append(row)

    duplicates = {n: [r['filename'] for r in rows] for n, rows in by_name.items() if len(rows) > 1}
    for name, files in sorted(duplicates.items()):
        problems.append({'kind': 'duplicate_distribution', 'distribution': name, 'files': files})

    # closure from the install pins
    missing, conflicts, unknown, prerelease, extra_warnings = [], [], [], [], []
    reached = {}
    queue = [(Requirement(pin), 'install pin') for pin in ROOT_PINS]
    seen = set()
    while queue:
        requirement, parent = queue.pop(0)
        name = canonicalize_name(requirement.name)
        candidates = by_name.get(name)
        if not candidates:
            missing.append({'requirement': str(requirement), 'required_by': parent})
            continue
        row = candidates[0]
        version = Version(row['version'])
        if requirement.specifier and not requirement.specifier.contains(version, prereleases=True):
            conflicts.append({'requirement': str(requirement), 'required_by': parent, 'available': row['version']})
        elif requirement.specifier and version.is_prerelease and not requirement.specifier.prereleases:
            prerelease.append({'requirement': str(requirement), 'required_by': parent, 'available': row['version']})
        extras = {canonicalize_name(e) for e in requirement.extras}
        entry = reached.setdefault(name, {'filename': row['filename'], 'extras': set(), 'required_by': set()})
        entry['required_by'].add(parent)
        key = (name, frozenset(extras))
        if key in seen:
            continue
        seen.add(key)
        entry['extras'] |= extras
        meta = row.get('_meta')
        if meta is None:
            unknown.append({'distribution': name, 'filename': row['filename'], 'status': row['status']})
            continue
        for e in extras - set(meta['provides_extra']):
            extra_warnings.append({'distribution': name, 'extra': e, 'required_by': parent})
        for text in meta['requires_dist']:
            try:
                dep = Requirement(text)
            except InvalidRequirement:
                problems.append({'kind': 'invalid_requirement', 'distribution': name, 'requirement': text})
                continue
            if applies(dep, extras):
                queue.append((dep, f"{name}=={row['version']}" + (f"[{','.join(sorted(extras))}]" if extras else '')))

    unrequired = sorted(r['filename'] for n, rows in by_name.items() for r in rows if n not in reached)
    for row in wheels:
        row.pop('_meta', None)
        row['required'] = canonicalize_name(row['distribution']) in reached
    counts = {}
    for row in wheels:
        counts[row['status']] = counts.get(row['status'], 0) + 1
    closure_complete = not (missing or conflicts or unknown or problems)
    glibc_needed = max((tuple(map(int, r['min_glibc'].split('.'))) for r in wheels
                        if r['min_glibc'] and r['required']), default=None)
    proprietary = sorted({r['distribution'] for r in wheels
                          if any('Proprietary' in c for c in (r.get('metadata') or {}).get('license_classifiers', []))
                          or 'proprietary' in str((r.get('metadata') or {}).get('license') or '').lower()})
    return {
        'scope': 'metadata only: no wheel requested, downloaded, installed or executed; no GPU',
        'target': {'environment': TARGET_ENVIRONMENT, 'glibc_lower_bound': '.'.join(map(str, TARGET_GLIBC)),
                   'python': '.'.join(map(str, TARGET_PYTHON)), 'install_pins': list(ROOT_PINS),
                   'compatible_tag_count': len(tags)},
        'inventory': {'archive': inv['archive'], 'archive_sha256': inv['archive_sha256'],
                      'manifest_hashes': inv['manifest_hashes'], 'wheel_count': len(inv['wheels']),
                      'wheel_bytes': sum(w['size'] for w in inv['wheels']),
                      'non_wheel_files_missing': [f['filename'] for f in inv['non_wheel_files']]},
        'acquisition': {'acquired_at': acq.get('acquired_at'), 'requests_made': acq.get('requests_made'),
                        'wheel_urls_requested': acq.get('wheel_urls_requested'), 'bounds': acq.get('bounds')},
        'summary': {'located_exact': sum(1 for r in wheels if r['located']),
                    'metadata_verified': counts.get('verified', 0), 'status_counts': counts,
                    'closure_complete': closure_complete, 'required_wheels': len(reached),
                    'unrequired_wheels': len(unrequired),
                    'glibc_required_by_closure': '.'.join(map(str, glibc_needed)) if glibc_needed else None,
                    'verdict': 'metadata_closure_complete' if closure_complete else 'unresolved'},
        'missing': missing, 'conflicts': conflicts, 'unknown': unknown, 'problems': problems,
        'prerelease_accepted': prerelease, 'extra_warnings': extra_warnings, 'unrequired': unrequired,
        'license_review_flags': {'proprietary_license_declared': proprietary},
        'next_download': [{'filename': r['filename'], 'url': r['upstream_url'], 'size': r['size'],
                           'sha256': r['sha256']} for r in wheels],
        'wheels': wheels,
        'not_established': ['wheel bytes verified after download', 'offline installation', 'GPU runtime',
                            'exact target glibc and driver (only a lower bound is known)',
                            'torch runtime build 2.10.0+cu128 (metadata reports 2.10.0; the runtime build is in the '
                            'wheel, not its metadata)'],
    }


def render_markdown(report):
    s, t, inv = report['summary'], report['target'], report['inventory']
    lines = [
        '# Wheelhouse metadata closure (metadata only)', '',
        'Generated offline by `scripts/check_wheelhouse_metadata.py analyze` from the retained acquisition record '
        '`reports/wheelhouse_metadata_acquisition.json.gz`. No wheel was requested, downloaded, installed or executed.',
        '', '## Answers', '',
        f"| Question | Answer |", '|---|---|',
        f"| Exact wheels located upstream (filename and SHA-256) | {s['located_exact']} of {inv['wheel_count']} |",
        f"| Wheels with hash-verified core metadata | {s['metadata_verified']} of {inv['wheel_count']} |",
        f"| Dependency closure of the install pins complete? | **{'yes' if s['closure_complete'] else 'no'}** "
        f"(`{s['verdict']}`) |",
        f"| Wheels required by the closure / unrequired | {s['required_wheels']} / {s['unrequired_wheels']} |",
        f"| glibc required by the closure | {s['glibc_required_by_closure']} (target lower bound "
        f"{t['glibc_lower_bound']}) |",
        f"| Package or build changes needed? | {'none indicated by metadata' if s['closure_complete'] else 'see unresolved items'} |",
        f"| Non-wheel bundle files missing (new bundle identity required) | {len(inv['non_wheel_files_missing'])}: "
        f"{', '.join('`%s`' % f for f in inv['non_wheel_files_missing'])} |",
        f"| Requests made / wheel URLs requested | {report['acquisition']['requests_made']} / "
        f"{len(report['acquisition']['wheel_urls_requested'] or [])} |", '',
        '## Established versus not established', '',
        '| Level | Status |', '|---|---|',
        f"| Metadata verified | {'established for all wheels' if s['metadata_verified'] == inv['wheel_count'] else 'partial'} |",
        '| Wheel bytes verified after download | not established (no download) |',
        '| Offline installation passed | not established |', '| GPU runtime passed | not established |', '',
        '## Target (declared, not the host)', '',
        f"Python {t['python']}, Linux x86-64, glibc ≥ {t['glibc_lower_bound']}, {t['compatible_tag_count']} compatible "
        f"tags. Install pins: {', '.join('`%s`' % p for p in t['install_pins'])}. Marker values: "
        + ', '.join(f'`{k}={v}`' for k, v in sorted(t['environment'].items())) + '.', '',
        '## Unresolved and diagnostics', '',
    ]
    for label, key in (('Missing dependencies', 'missing'), ('Conflicting constraints', 'conflicts'),
                       ('Required wheels without verified metadata', 'unknown'), ('Problems', 'problems'),
                       ('Pre-release versions accepted', 'prerelease_accepted'),
                       ('Requested extras not provided', 'extra_warnings')):
        items = report[key]
        lines.append(f"- **{label}:** {len(items)}" + ('' if not items else ''))
        for item in items[:25]:
            lines.append(f"  - `{json.dumps(item, sort_keys=True)}`")
        if key == 'prerelease_accepted' and items:
            lines.append('  - These are the only candidates in the inventory. An installer accepts a pre-release when no '
                         'final release satisfies the specifier (PEP 440; `packaging` `SpecifierSet.filter` semantics), '
                         'which is how an offline `--no-index` install from this set resolves them. They are reported, '
                         'not counted as conflicts.')
    lines += ['', f"**Unrequired wheels ({len(report['unrequired'])})** — reported, not removed; each needs a decision "
              'on whether it serves a runtime feature or is a historical extra:', '']
    lines += [f'- `{f}`' for f in report['unrequired']]
    flags = report['license_review_flags']['proprietary_license_declared']
    lines += ['', '## Redistribution questions', '',
              f"Distributions whose metadata declares a proprietary licence ({len(flags)}): "
              + (', '.join(f'`{d}`' for d in flags) or 'none') + '. Every wheel still needs licence and '
              'redistribution review before any team-owned upload; metadata licence fields are not a legal review.', '',
              '## Not established by this check', '']
    lines += [f'- {item}' for item in report['not_established']]
    lines += ['', 'The exact artifacts a later, separately approved download would acquire are listed in '
              '`reports/wheelhouse_metadata_closure.json` under `next_download` (filename, upstream URL, size, SHA-256).']
    return '\n'.join(lines) + '\n'


def dumps(report):
    return json.dumps(report, indent=1, sort_keys=True, default=sorted) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('inventory')
    a = sub.add_parser('acquire')
    a.add_argument('--force', action='store_true')
    z = sub.add_parser('analyze')
    z.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    inv = inventory()
    if args.command == 'inventory':
        print(json.dumps({k: v for k, v in inv.items() if k not in ('wheels',)}, indent=1))
        return 0
    if args.command == 'acquire':
        if ACQUISITION.exists() and not args.force:
            raise SystemExit(f'{ACQUISITION} exists (retained input); pass --force to re-acquire')
        budget = 2 * len({canonicalize_name(w['distribution']) for w in inv['wheels']}) * ATTEMPTS_PER_REQUEST \
            + len(inv['wheels']) * ATTEMPTS_PER_REQUEST
        client = Client(budget)
        record = acquire(inv, client)
        if record['wheel_urls_requested']:
            raise SystemExit('a wheel URL was requested; refusing to write the record')
        write_acquisition(record)
        print(json.dumps({'requests': record['requests_made'],
                          'statuses': {s: sum(1 for r in record['wheels'] if r['status'] == s)
                                       for s in sorted({r['status'] for r in record['wheels']})}}))
        return 0
    report = analyze(inv, read_acquisition())
    text, markdown = dumps(report), render_markdown(report)
    if args.check:
        same = REPORT_JSON.read_text(encoding='utf-8') == text and REPORT_MD.read_text(encoding='utf-8') == markdown
        print('reports match a fresh offline analysis' if same else 'REPORTS DIFFER from a fresh offline analysis')
        return 0 if same else 1
    REPORT_JSON.write_text(text, encoding='utf-8')
    REPORT_MD.write_text(markdown, encoding='utf-8')
    print(json.dumps(report['summary']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
