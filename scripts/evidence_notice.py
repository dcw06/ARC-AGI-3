"""Apache-2.0 NOTICE check for the wheels flagged "Apache-2.0 without a NOTICE in the wheel" (a proposal for the
designated reviewer, never a decision).

  python scripts/evidence_notice.py

Apache-2.0 section 4(d) requires a redistributor to pass on a NOTICE file only if the Work as distributed includes
one. For every decision-worksheet row carrying that flag, this checks whether the EXACT upstream release includes a
NOTICE-named file (NOTICE, NOTICE.txt, NOTICE.md, NOTICES, ... at any path, case-insensitive) and records exactly one
outcome per wheel:

  found            the local wheel, the exact-version sdist verified against PyPI's SHA-256, or the upstream repository
                   at a commit whose version file carries the exact version contains one or more NOTICE-named files.
                   Each path and SHA-256 is recorded and the bytes are retained as sources/notice-<distribution>-...
  verified_absent  ALL of: (a) the exact-version sdist is on PyPI, its bytes match PyPI's SHA-256 and its PKG-INFO
                   carries the exact version; (b) the complete listing of the sdist has no NOTICE-named file (and no
                   other file named like a notice) at any path; (c) every component of the local wheel is traced to
                   that sdist: no auditwheel-bundled libraries (<pkg>.libs/), no native binary that may link code
                   from outside the sdist (Rust crates resolved from a registry, download directives in the build
                   scripts other than test-only ones inside a CMake if(BUILD_TESTING) branch, embedded third-party
                   library markers, or no matching source file in the sdist), and no wheel file that is absent from
                   the sdist by both content and path (a small generated version stub carrying the exact version
                   excepted); and no code reaching the wheel from a trimmed third-party copy in the sdist (a
                   third-party directory without any top-level licence file), unless that copy is a git submodule
                   whose pinned upstream tree at the version-verified release commit has no NOTICE-named file and
                   matches every file of the copy; AND (d) the release repository (named by the wheel METADATA)
                   is listed at the release tag, a version file at that commit carries the exact version, and its
                   complete (untruncated) tree has no NOTICE-named or notice-like file. Absence from the wheel and the
                   sdist alone does not establish absence upstream (a repository-only NOTICE is possible).
  inconclusive     anything else, with the precise reason. A fetch failure, a missing sdist or a missing root-level
                   file is never treated as absence. A row absent from the inspected wheel and sdist whose release
                   repository could not be verified stays inconclusive, with the upstream NOTICE question open.
Every row not already found in the wheel or sdist gets the repository check (2 GitHub API calls per repository, plus
1 per git submodule that holds a trimmed third-party copy). A NOTICE there counts only if a version file at that
commit carries the exact version; such a repository-only NOTICE is reported as found, with the note that the PyPI
sdist and the wheel lack it.

The check is limited to what is listed in the pack. It does not establish legal clearance, and a verified_absent
outcome removes only the "confirm no upstream NOTICE" question: shipping the licence texts and keeping the other
attribution notices remain required. Local wheels are opened only after their SHA-256 matches the approved manifest;
no wheel is downloaded. Whole sdists and repository trees are not retained (they are content-addressed by the
recorded SHA-256 / commit); NOTICE files and version-check files are. Writes
reports/wheelhouse_evidence/apache_notice_check.{json,md}.
"""
import csv
import hashlib
import io
import json
import re
import sys
import tarfile
import time
import tomllib
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evidence_common import (TIMEOUT, UA, artifact_for, fetch, open_wheel, retain,  # noqa: E402
                                     sha256_bytes, verified_sdist, write_pack)

WORKSHEET = ROOT / 'reports/wheelhouse_redistribution_decision_worksheet.csv'
INVENTORY = ROOT / 'reports/wheelhouse_redistribution_inventory.csv'
FLAG = 'Apache-2.0 without a NOTICE in the wheel'
OUTCOMES = ('found', 'verified_absent', 'inconclusive')
NOTICE_NAME = re.compile(r'(?i)^notices?(\.[a-z0-9_-]+)*$')
NOTICE_LIKE_EXT = ('', '.txt', '.md', '.rst', '.html', '.htm', '.text')
CODE_EXT = ('.py', '.pyi', '.pyx', '.pxd', '.pyc', '.c', '.h', '.cc', '.cpp', '.hpp', '.cu', '.cuh', '.rs', '.js',
            '.ts', '.go', '.java', '.so')  # a module named notice.py is code, not a NOTICE file
SOURCE_EXT = ('.c', '.cc', '.cpp', '.cxx', '.pyx', '.cu', '.f', '.f90', '.m', '.mm')
BUILD_FILES = re.compile(r'(?i)(^|/)(CMakeLists\.txt|[^/]+\.cmake|setup\.py|build\.rs|meson\.build|pyproject\.toml|'
                         r'Makefile|configure\.py|build_[^/]*\.py)$')
DOWNLOAD_DIRECTIVES = re.compile(r'FetchContent_Declare|ExternalProject_Add|CPMAddPackage|file\s*\(\s*DOWNLOAD|'
                                 r'["\']git["\']\s*,\s*["\'](?:clone|submodule)["\']|'
                                 r'(?:subprocess|os\.system|check_call|check_output)[^\n]*git (?:clone|submodule)|'
                                 r'urlretrieve|urllib\.request\.urlopen|requests\.get\(|\bwget |\bcurl -')
GENERATED_VERSION_FILES = {'_version.py', 'version.py', '__version__.py', '_version.txt', 'VERSION'}
VENDORED_DIR = re.compile(r'(?i)(^|/)(3rdparty|third[_-]?party|vendor|vendored|_vendor|external|extern|deps)/[^/]+/')
THIRD_PARTY_MARKERS = re.compile(rb'OpenSSL \d+\.\d+\.\d+[a-z]?|LLVM version \d+\.\d+\.\d+|LLVM \d+\.\d+\.\d+|'
                                 rb'BoringSSL|LibreSSL \d+\.\d+')
GITHUB = re.compile(r'https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)')
API = 'https://api.github.com'
RAW = 'https://raw.githubusercontent.com'
TAG_PROBES = ('LICENSE', 'README.md', 'README.rst', 'pyproject.toml', 'LICENSE.txt', 'setup.py', 'Cargo.toml')
VERSION_FILES = {'_version.py': 0, 'version.py': 0, '__about__.py': 0, 'VERSION': 0, 'version.txt': 0,
                 'Cargo.toml': 1, 'pyproject.toml': 1, 'setup.py': 2, 'setup.cfg': 2, 'package.json': 2,
                 '__init__.py': 3}  # file name -> search priority
MAX_LISTED = 25


# ---------------------------------------------------------------- pure helpers (unit-tested offline)

def is_notice_name(path):
    """NOTICE, NOTICE.txt, NOTICE.md, NOTICES, notice.rst ... (any case) at any path; code files excluded."""
    base = path.rstrip('/').rsplit('/', 1)[-1]
    return bool(NOTICE_NAME.match(base)) and not base.lower().endswith(CODE_EXT)


def is_notice_like(path):
    """A text document named like a notice (e.g. THIRD_PARTY_NOTICES.txt, NOTICE-binary) that is not a NOTICE name:
    a reviewer must look. Code, data and certificate files that merely contain the word are not counted."""
    base = path.rstrip('/').rsplit('/', 1)[-1]
    ext = base[base.rfind('.'):].lower() if '.' in base else ''
    return 'notice' in base.lower() and not is_notice_name(base) and ext in NOTICE_LIKE_EXT


def source_name(distribution, source, path):
    safe = re.sub(r'[^A-Za-z0-9._@+-]', '_', path.strip('/').replace('/', '+'))
    return f'notice-{distribution}-{source}-{safe}'


def wheel_relpath(path):
    """Install-relative path of a wheel member (strips <dist>.data/<category>/)."""
    return re.sub(r'^[^/]+\.data/[^/]+/', '', path)


def rust_summary(sdist_files, cargo_locks):
    """External Rust crates compiled into the extension: registry/git packages in Cargo.lock not vendored in the sdist."""
    if not any(p.rsplit('/', 1)[-1] == 'Cargo.toml' for p in sdist_files):
        return None
    vendored = {p.rsplit('/', 2)[-2] for p in sdist_files if p.endswith('/.cargo-checksum.json')}
    external = []
    for lock in cargo_locks.values():
        for pkg in tomllib.loads(lock).get('package', []):
            src = pkg.get('source', '')
            if src.startswith(('registry+', 'git+')) and pkg['name'] not in vendored \
                    and f"{pkg['name']}-{pkg['version']}" not in vendored:
                external.append(f"{pkg['name']} {pkg['version']}")
    return {'cargo_lock_files': sorted(cargo_locks), 'external_crates': len(set(external)),
            'external_crates_sample': sorted(set(external))[:10], 'vendored_crate_dirs': len(vendored)}


def cmake_test_only(text, pos):
    """True if offset `pos` of a CMake file lies inside an if(BUILD_TESTING ...) branch (code built only for tests)."""
    stack = []
    for line in text[:pos].splitlines():
        s = line.strip().lower()
        guard = bool(re.search(r'\bbuild_testing\b', s)) and not re.search(r'\bnot\s+build_testing\b', s)
        if re.match(r'if\s*\(', s):
            stack.append(guard)
        elif re.match(r'elseif\s*\(', s) and stack:
            stack[-1] = guard
        elif re.match(r'else\s*\(', s) and stack:
            stack[-1] = False
        elif re.match(r'endif\s*\(', s) and stack:
            stack.pop()
    return any(stack)


def download_hits(build_files):
    """Download directives in the sdist's build scripts: [{'path', 'line', 'directive', 'text', 'test_only'}]."""
    hits = []
    for path, content in sorted(build_files.items()):
        text = content.decode('utf-8', 'replace') if isinstance(content, bytes) else content
        is_cmake = path.endswith(('CMakeLists.txt', '.cmake'))
        for m in DOWNLOAD_DIRECTIVES.finditer(text):
            line_no = text.count('\n', 0, m.start()) + 1
            hits.append({'path': path, 'line': line_no, 'directive': m.group(0).strip(),
                         'text': text.split('\n')[line_no - 1].strip()[:160],
                         'test_only': is_cmake and cmake_test_only(text, m.start())})
    return hits


def vendored_dirs(sdist_files):
    """Third-party-looking directories carried in the sdist (judged only as the sdist carries them), with their
    file count and the licence-like files at their top level."""
    dirs = sorted({p[:m.end()].rstrip('/') for p in sdist_files if (m := VENDORED_DIR.search(p))
                   and not re.search(r'(?i)(^|/)(tests?|docs?)/', p[:m.start()])})
    out = []
    for d in dirs:
        inside = [p[len(d) + 1:] for p in sdist_files if p.startswith(d + '/')]
        out.append({'dir': d, 'files': len(inside),
                    'top_level_licence_files': sorted(p for p in inside if '/' not in p and
                                                      re.search(r'(?i)licen[cs]e|copying|notice', p))})
    return out


def native_findings(member, sdist_basenames, rust):
    """Reasons a native binary in the wheel may contain code from outside the sdist ([] if none found)."""
    path = member['path']
    base = path.rsplit('/', 1)[-1]
    reasons = []
    if rust is not None and (rust['external_crates'] or not rust['cargo_lock_files']):
        reasons.append(f"{path}: Rust build; {rust['external_crates']} crates resolved from a registry/git per "
                       f"Cargo.lock are compiled in and are not vendored in the sdist" if rust['cargo_lock_files']
                       else f'{path}: Rust build without Cargo.lock in the sdist; crate dependencies are resolved at '
                            f'build time from outside the sdist')
    stem = base.split('.')[0]
    stems = {stem, stem[3:]} if stem.startswith('lib') and len(stem) > 3 else {stem}
    is_module = bool(re.search(r'\.(cpython-[^/]*|abi3)\.so$', base))
    exts = SOURCE_EXT + (('.py', '.rs') if is_module else ('.rs',))
    if not any(f'{s}{e}' in sdist_basenames for s in stems for e in exts) and rust is None:
        reasons.append(f'{path}: no source file named {"/".join(sorted(stems))}.{{c,cc,cpp,pyx,cu,...}} in the sdist; '
                       f'provenance of the binary not established')
    if member.get('markers'):
        reasons.append(f"{path}: embeds third-party library markers ({', '.join(member['markers'][:4])})")
    return reasons


def outside_components(wheel_members, sdist_files, rust=None, downloads=(), version=None):
    """(reasons, coverage): which local-wheel components are not traced to the sdist.

    wheel_members: [{'path', 'sha256', 'elf', 'markers'?, 'text'?}]; sdist_files: {relative path: sha256} (regular
    files); downloads: download_hits() of the sdist's build scripts; version: the exact release version."""
    hashes = set(sdist_files.values())
    by_base = {}
    for p in sdist_files:
        by_base.setdefault(p.rsplit('/', 1)[-1], []).append(p)
    reasons, native_reasons, native, matched_path_only, unmatched, generated = [], [], [], [], [], []
    matched_hash = 0
    libs = [m['path'] for m in wheel_members if re.match(r'^[^/]+\.libs/', m['path'])]
    if libs:
        reasons.append(f"auditwheel-bundled third-party libraries ({len(libs)}): {', '.join(libs[:5])}")
    for m in wheel_members:
        path = m['path']
        if '.dist-info/' in path or path in libs:
            continue
        if m['elf']:
            found = native_findings(m, by_base, rust)
            native.append({'path': path, 'sha256': m['sha256'], 'bytes': m.get('bytes'), 'markers': m.get('markers', []),
                           'outside_sdist_reasons': found})
            native_reasons += found
            continue
        if m['sha256'] in hashes:
            matched_hash += 1
            continue
        rel = wheel_relpath(path)
        base = rel.rsplit('/', 1)[-1]
        if any(c == rel or c.endswith('/' + rel) for c in by_base.get(base, [])):
            matched_path_only.append(path)
        elif base in GENERATED_VERSION_FILES and version and \
                re.search(r'["\']' + re.escape(version) + r'["\']', m.get('text') or ''):
            generated.append(path)  # a small version stub written by the build backend from the sdist's metadata
        else:
            unmatched.append(path)
    live = [h for h in downloads if not h.get('test_only')]
    if native and live:
        reasons.append(f"{len(native)} native binar{'y' if len(native) == 1 else 'ies'}; the sdist's build scripts "
                       'contain download directives (' + '; '.join(f"{h['path']}:{h['line']} {h['directive']}"
                                                                   for h in live[:4]) +
                       (f' +{len(live) - 4} more' if len(live) > 4 else '') +
                       '); whether the shipped binaries include downloaded code was not established')
    if unmatched:
        reasons.append(f"{len(unmatched)} wheel file(s) present in the sdist by neither content nor path "
                       f"(e.g. {', '.join(unmatched[:3])})")
    reasons += native_reasons
    coverage = {'wheel_files_checked': matched_hash + len(matched_path_only) + len(generated) + len(unmatched) +
                len(native),
                'matched_by_content': matched_hash, 'matched_by_path_content_differs': len(matched_path_only),
                'matched_by_path_content_differs_sample': matched_path_only[:MAX_LISTED],
                'generated_version_files': generated[:MAX_LISTED],
                'unmatched': len(unmatched), 'unmatched_sample': unmatched[:MAX_LISTED],
                'auditwheel_libs': libs[:MAX_LISTED], 'native_binaries': native,
                'download_directives': list(downloads)[:MAX_LISTED] if native else [],
                'download_directives_note': 'test-only directives (inside if(BUILD_TESTING)) are listed but not '
                                            'counted' if native and any(h.get('test_only') for h in downloads) else ''}
    return reasons, coverage


def classify(e):
    """(outcome, reason) from the gathered evidence; exactly one of OUTCOMES.

    e: {'notices': [{'source', 'path', ...}] (wheel, sdist, or repository at a version-verified commit),
        'sdist': {'status': 'verified'|'none'|'error', 'reason'?, 'sdist'?}, 'listing_complete': bool,
        'listing_error'?: str, 'member_count'?: int, 'pkg_info_version_matches': bool, 'notice_like': [paths],
        'outside': [reasons], 'trimmed'?: {dir: reason} (open), 'cleared'?: [dirs resolved upstream]}"""
    sdist = e.get('sdist') or {'status': 'error', 'reason': 'no sdist evidence recorded'}
    if e.get('notices'):
        reason = 'NOTICE file(s) in the exact release: ' + '; '.join(f"{n['source']}: {n['path']}" for n in e['notices'])
        if not any(n['source'].startswith(('sdist', 'wheel')) for n in e['notices']):
            reason += ('; none of them is in the PyPI-verified sdist or in the wheel (repository only), so the '
                       'reviewer decides whether the Work as distributed in this wheel includes them'
                       if sdist.get('status') == 'verified' and e.get('listing_complete') else
                       '; repository only, with no verified sdist listing to compare')
        return 'found', reason
    if sdist.get('status') == 'none':
        return 'inconclusive', f"no sdist for this exact version on PyPI ({sdist.get('reason', 'none listed')}); " \
                               'absence cannot be verified'
    if sdist.get('status') != 'verified':
        return 'inconclusive', f"sdist not obtained or not verified ({sdist.get('reason', 'unknown')}); a fetch " \
                               'failure is not evidence of absence'
    if not e.get('listing_complete'):
        return 'inconclusive', f"sdist {sdist.get('sdist')} could not be listed completely " \
                               f"({e.get('listing_error', 'unknown error')})"
    if not e.get('pkg_info_version_matches'):
        return 'inconclusive', f"sdist {sdist.get('sdist')} PKG-INFO does not carry the exact version"
    if e.get('notice_like'):
        return 'inconclusive', 'file(s) named like a notice but not NOTICE need a reviewer look: ' + \
            ', '.join(e['notice_like'][:5])
    if e.get('outside'):
        return 'inconclusive', 'the wheel contains components not traced to the sdist, whose NOTICE status is ' \
                               'unknown: ' + '; '.join(e['outside'][:6]) + \
            (f' (+{len(e["outside"]) - 6} more)' if len(e['outside']) > 6 else '')
    if e.get('trimmed'):
        return 'inconclusive', 'the wheel carries code from third-party copies that the sdist holds in trimmed ' \
                               'form, so their upstream NOTICE status is unknown: ' + '; '.join(e['trimmed'].values())
    package = (f"exact-version sdist {sdist.get('sdist')} verified against PyPI's SHA-256; its complete listing "
               f"({e.get('member_count')} members) has no NOTICE-named file at any path; every wheel component is "
               'traced to the sdist' + ('; trimmed third-party copies cleared at their pinned upstream commits: '
                                        + ', '.join(e['cleared']) if e.get('cleared') else ''))
    repository = e.get('repository') or {}
    if not repository.get('verified_clean'):
        return 'inconclusive', ('absent from the inspected wheel and sdist (' + package + '), but the release '
                                'repository was not verified free of a NOTICE (' +
                                repository.get('summary', 'not checked') + '), so the upstream NOTICE question stays '
                                'open')
    return 'verified_absent', package + '; the release repository at a version-verified commit has no NOTICE-named ' \
                                        'or notice-like file: ' + repository['summary']


def trimmed_copies(vendored, wheel_members, sdist_files):
    """{dir: reason} for third-party directories that the sdist carries without their top-level licence files (a
    trimmed copy, so a NOTICE at the component's root may have been left out) and whose code reaches the wheel:
    files shipped verbatim, or any native binary in the wheel (which may compile them in)."""
    wheel_hashes = {m['sha256'] for m in wheel_members if '.dist-info/' not in m['path']}
    native = any(m['elf'] for m in wheel_members)
    out = {}
    for v in vendored:
        if v['top_level_licence_files']:
            continue
        shipped = sum(sha in wheel_hashes for p, sha in sdist_files.items() if p.startswith(v['dir'] + '/'))
        if shipped or native:
            how = f'{shipped} of its files ship in the wheel' if shipped else 'it may be compiled into the native ' \
                                                                              'binaries'
            out[v['dir']] = f"{v['dir']} ({v['files']} files, no top-level licence file; {how})"
    return out


def remains(outcome, licence_documents, declared, vendored=(), repository_only=False):
    docs = licence_documents or 'none listed'
    common = (f'ship the licence texts bundled in the wheel ({docs}) with the redistributed wheel (Apache-2.0 4(a)); '
              f'keep the copyright and attribution notices in the files (4(c)); declared licence: {declared or "n/a"}')
    if vendored:
        common += ('; third-party directories carried in the sdist (' + ', '.join(v['dir'] for v in vendored[:4]) +
                   (f' +{len(vendored) - 4} more' if len(vendored) > 4 else '') +
                   ') have their own licence terms, not checked here, which may require their licence texts too')
    if outcome == 'found' and repository_only:
        return ('the NOTICE is in the upstream repository at the release commit but not in the PyPI sdist or the '
                'wheel: the reviewer decides whether 4(d) reaches this wheel (shipping the retained NOTICE alongside '
                'is the cautious option); also ' + common)
    if outcome == 'found':
        return ('pass on the NOTICE file(s) listed in a readable form (4(d)), after the reviewer confirms which of '
                'them belong to the Work as distributed in this wheel; also ' + common)
    if outcome == 'verified_absent':
        return 'the "confirm no upstream NOTICE" question can be dropped for this exact release; still ' + common
    return 'the NOTICE question stays open (see reason); in any case ' + common


# ---------------------------------------------------------------- evidence gathering (network / local wheels)

def flagged_rows():
    with WORKSHEET.open(encoding='utf-8', newline='') as f:
        return [r for r in csv.DictReader(f) if FLAG in r['additional_obligations']]


def inventory_rows():
    with INVENTORY.open(encoding='utf-8', newline='') as f:
        return {r['artifact']: r for r in csv.DictReader(f)}


def scan_wheel(artifact):
    z = open_wheel(artifact)
    members, notice_bytes = [], {}
    for info in z.infolist():
        if info.is_dir():
            continue
        digest, head, tail, markers = hashlib.sha256(), b'', b'', set()
        with z.open(info) as f:
            while chunk := f.read(1 << 20):
                if not head:
                    head = chunk[:4]
                digest.update(chunk)
                if head == b'\x7fELF':
                    markers.update(m.group(0).decode('ascii', 'replace') for m in
                                   THIRD_PARTY_MARKERS.finditer(tail + chunk))
                    tail = chunk[-64:]
        m = {'path': info.filename, 'sha256': digest.hexdigest(), 'bytes': info.file_size, 'elf': head == b'\x7fELF'}
        if m['elf']:
            m['markers'] = sorted(markers)
        if info.filename.rsplit('/', 1)[-1] in GENERATED_VERSION_FILES and info.file_size <= 4096:
            m['text'] = z.read(info).decode('utf-8', 'replace')
        members.append(m)
        if is_notice_name(info.filename) or is_notice_like(info.filename):
            notice_bytes[info.filename] = z.read(info)
    metadata = z.read(next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))).decode('utf-8', 'replace')
    return members, notice_bytes, metadata


def repository_from_metadata(metadata):
    ranked = []
    for line in metadata.splitlines():
        key, _, value = line.partition(':')
        if key not in ('Project-URL', 'Home-page'):
            continue
        label = value.split(',')[0].lower() if key == 'Project-URL' else 'home-page'
        match = GITHUB.search(value)
        if match and match.group(2) not in ('.github',):
            rank = 0 if re.search(r'repo|source', label) else 1 if 'home' in label else 2
            ranked.append((rank, match.group(1), re.sub(r'\.git$', '', match.group(2))))
    return (ranked and sorted(ranked)[0][1:]) or None


def read_sdist(data, filename):
    """(listing, kept) of an sdist: every member, regular-file hashes, and the bytes of the files the check needs."""
    listing = {'members': 0, 'files': {}, 'git_blobs': {}, 'types': {}}
    kept = {'notice': {}, 'cargo_lock': {}, 'build': {}, 'pkg_info': None}
    entries = []
    if filename.endswith('.zip'):
        z = zipfile.ZipFile(io.BytesIO(data))
        if z.testzip() is not None:
            raise ValueError('zip CRC error')
        entries = [(i.filename.rstrip('/'), 'dir' if i.is_dir() else 'file', (lambda i=i: z.read(i)))
                   for i in z.infolist()]
    else:
        tf = tarfile.open(fileobj=io.BytesIO(data), mode='r:*')
        for m in tf:  # reads the whole stream, so a truncated archive raises here
            kind = 'file' if m.isfile() else 'dir' if m.isdir() else 'symlink' if m.issym() else \
                'hardlink' if m.islnk() else 'other'
            content = tf.extractfile(m).read() if m.isfile() else None
            entries.append((m.name.rstrip('/'), kind, (lambda c=content: c)))
    tops = {n.split('/', 1)[0] for n, _, _ in entries}
    root = tops.pop() + '/' if len(tops) == 1 else ''  # the single <name>-<version>/ directory of the sdist
    for name, kind, read in entries:
        listing['members'] += 1
        listing['types'][kind] = listing['types'].get(kind, 0) + 1
        rel = name[len(root):] if root and name.startswith(root) else name
        if kind == 'file':
            content = read()
            listing['files'][rel] = sha256_bytes(content)
            listing['git_blobs'][rel] = hashlib.sha1(b'blob %d\0' % len(content) + content).hexdigest()
            if is_notice_name(rel) or is_notice_like(rel):
                kept['notice'][rel] = content
            if rel.rsplit('/', 1)[-1] == 'Cargo.lock':
                kept['cargo_lock'][rel] = content.decode('utf-8', 'replace')
            if BUILD_FILES.search(rel) and len(content) < 2 * 1024 ** 2:
                kept['build'][rel] = content
            if rel == 'PKG-INFO':
                kept['pkg_info'] = content.decode('utf-8', 'replace')
        elif is_notice_name(rel) or is_notice_like(rel):
            kept['notice'][rel] = None  # a non-regular member (dir/link) with a notice name; recorded by path
    listing['root'] = root
    return listing, kept


def gh_api(path, accept='application/vnd.github+json', cap=32 * 1024 ** 2, max_wait=3900):
    """Unauthenticated GitHub API GET. If the hourly quota is exhausted and resets within max_wait seconds, waits
    for the reset once instead of recording a failure."""
    request = urllib.request.Request(f'{API}/{path}', headers={**UA, 'Accept': accept,
                                                               'X-GitHub-Api-Version': '2022-11-28'})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                data = response.read(cap + 1)
            break
        except urllib.error.HTTPError as exc:
            reset, remaining = exc.headers.get('X-RateLimit-Reset'), exc.headers.get('X-RateLimit-Remaining')
            delay = int(reset) - time.time() + 5 if reset and reset.isdigit() else None
            if attempt == 1 and exc.code in (403, 429) and remaining == '0' and delay is not None \
                    and delay <= max_wait:
                print(f'GitHub API quota exhausted; waiting {max(int(delay), 0)} s for its reset', flush=True)
                time.sleep(max(delay, 0))
                continue
            raise
    if len(data) > cap:
        raise ValueError(f'{path} exceeds {cap} bytes')
    return data


VERSION_LINE = r'(?im)^\s*["\']?(__version__|version|VERSION)["\']?\s*[:=]\s*["\']{v}["\']\s*,?\s*$'


def version_line(text, version):
    """The line of a version file that assigns exactly `version` (None if there is none)."""
    if text.strip() == version:
        return text.strip()
    match = re.search(VERSION_LINE.format(v=re.escape(version)), text)
    return match.group(0).strip() if match else None


def version_file_candidates(blobs, distribution, limit=30):
    """Repository files that may carry the release version: root-level files first (the usual place in a
    single-package repository), then files whose path names this distribution (most specific first, as in a
    monorepository), then the rest."""
    tokens = [t for t in re.split(r'[_-]', distribution.lower()) if len(t) > 2]
    files = [p for p in blobs if p.rsplit('/', 1)[-1] in VERSION_FILES and p.count('/') <= 5
             and not re.search(r'(?i)(^|/)(tests?|benchmarks?|examples?|docs?)/', p)]
    priority = lambda p: VERSION_FILES[p.rsplit('/', 1)[-1]]  # noqa: E731
    matches = lambda p: sum(t in p.lower() for t in tokens)  # noqa: E731
    root = sorted((p for p in files if '/' not in p), key=lambda p: (priority(p), p))
    named = sorted((p for p in files if '/' in p and matches(p)), key=lambda p: (-matches(p), priority(p),
                                                                                p.count('/'), p))[:15]
    rest = sorted((p for p in files if '/' in p and not matches(p)), key=lambda p: (priority(p), p.count('/'), p))
    return (root + named + rest)[:limit]


def repository_check(distribution, version, repo, trimmed=None):
    """Tree of the upstream repository at the release tag; NOTICE files there count only at a version-verified commit.
    trimmed: {sdist directory: {path inside it: git blob sha1}} for trimmed third-party copies to resolve upstream."""
    if repo is None:
        return {'performed': False, 'reason': 'the wheel METADATA names no GitHub repository'}
    owner, name = repo
    out = {'performed': True, 'repository': f'https://github.com/{owner}/{name}'}
    dashed = distribution.replace('_', '-')
    tags = list(dict.fromkeys([f'v{version}', version, f'{dashed}-v{version}', f'{dashed}-{version}',
                               f'{distribution}-v{version}', f'{distribution}-{version}']))
    out['tags_probed'] = tags
    tag = None
    for candidate in tags:
        for probe in TAG_PROBES:
            try:
                fetch(f'{RAW}/{owner}/{name}/refs/tags/{candidate}/{probe}', 4 * 1024 ** 2)
            except Exception:
                continue
            tag = candidate
            break
        if tag:
            break
    if tag is None:
        out['reason'] = 'no release tag among those probed resolved on raw.githubusercontent.com'
        return out
    out['tag'] = tag
    try:
        commit = gh_api(f'repos/{owner}/{name}/commits/{tag}', accept='application/vnd.github.sha').decode().strip()
        if not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError(f'unexpected commit response {commit[:60]!r}')
        tree_bytes = gh_api(f'repos/{owner}/{name}/git/trees/{commit}?recursive=1')
    except Exception as exc:
        out['reason'] = f'GitHub API failure: {type(exc).__name__}: {str(exc)[:160]}'
        return out
    tree = json.loads(tree_bytes)
    blobs = [t['path'] for t in tree['tree'] if t['type'] == 'blob']
    out.update(commit=commit, tree_sha=tree['sha'], tree_response_sha256=sha256_bytes(tree_bytes),
               tree_entries=len(tree['tree']), tree_truncated=bool(tree.get('truncated')),
               submodules=[t['path'] for t in tree['tree'] if t['type'] == 'commit'][:MAX_LISTED])
    candidates = version_file_candidates(blobs, distribution)
    out['version_check'] = {'verified': False, 'files_checked': []}
    for path in candidates:
        url = f'{RAW}/{owner}/{name}/{commit}/{path}'
        try:
            data = fetch(url, 4 * 1024 ** 2)
        except Exception as exc:
            out['version_check']['files_checked'].append(f'{path}: fetch failed {type(exc).__name__}')
            continue
        line = version_line(data.decode('utf-8', 'replace'), version)
        out['version_check']['files_checked'].append(path)
        if line:
            record = retain(source_name(distribution, f'repo-{commit[:12]}', path), url, data, kind='version-file')
            out['version_check'] = {'verified': True, 'path': path, 'line': line[:200], 'retained': record,
                                    'files_checked': out['version_check']['files_checked']}
            break
    notices = [p for p in blobs if is_notice_name(p)]
    out['notice_like'] = [p for p in blobs if is_notice_like(p)][:MAX_LISTED]
    out['notices'] = []
    for path in notices:
        url = f'{RAW}/{owner}/{name}/{commit}/{path}'
        entry = {'source': f'repository {owner}/{name}@{commit[:12]}', 'path': path,
                 'counts_for_outcome': out['version_check']['verified'],
                 'scope_note': 'repository-wide path: the reviewer confirms whether it belongs to the Work shipped in '
                               'this wheel (e.g. another package of a monorepo, or test data)' if '/' in path else
                               'repository root'}
        if out['version_check']['verified']:
            try:
                data = fetch(url)
                entry.update(sha256=sha256_bytes(data),
                             retained=retain(source_name(distribution, f'repo-{commit[:12]}', path), url, data,
                                             kind='notice'))
            except Exception as exc:
                entry.update(counts_for_outcome=False, error=f'{type(exc).__name__}: {str(exc)[:120]}')
        out['notices'].append(entry)
    out['submodule_checks'] = submodule_checks(distribution, owner, name, commit, tree, trimmed or {},
                                               out['version_check']['verified'])
    out['reason'] = ('tree listed at a commit whose version file carries the exact version' if
                     out['version_check']['verified'] else
                     'tree listed, but no version file at the commit carries the exact version string; NOTICE files '
                     'there (if any) are recorded but do not count')
    return out


def gitmodules_urls(text):
    """{submodule path: url} from a .gitmodules file."""
    urls = {}
    for block in re.split(r'(?m)^\s*\[submodule', text)[1:]:
        path, url = re.search(r'(?m)^\s*path\s*=\s*(\S+)', block), re.search(r'(?m)^\s*url\s*=\s*(\S+)', block)
        if path and url:
            urls[path.group(1)] = url.group(1)
    return urls


def submodule_checks(distribution, owner, name, commit, tree, trimmed, version_verified):
    """For trimmed third-party copies that are git submodules at the release commit: the upstream tree at the pinned
    commit (1 GitHub API call each), whether the sdist's copy matches its blobs, and any NOTICE files there."""
    wanted = [t for t in tree['tree'] if t['type'] == 'commit' and t['path'] in trimmed]
    if not wanted:
        return []
    try:
        urls = gitmodules_urls(fetch(f'{RAW}/{owner}/{name}/{commit}/.gitmodules', 1024 ** 2).decode('utf-8', 'replace'))
    except Exception as exc:
        return [{'path': t['path'], 'error': f'.gitmodules fetch failed: {type(exc).__name__}'} for t in wanted]
    checks = []
    for t in wanted[:4]:
        entry = {'path': t['path'], 'pinned_commit': t['sha'], 'url': urls.get(t['path']), 'cleared': False,
                 'notices': []}
        match = re.search(r'github\.com[:/]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$', entry['url'] or '')
        if not match:
            checks.append(dict(entry, error='submodule URL is not a GitHub repository'))
            continue
        sub_owner, sub_name = match.groups()
        try:
            sub_tree = json.loads(gh_api(f'repos/{sub_owner}/{sub_name}/git/trees/{t["sha"]}?recursive=1'))
        except Exception as exc:
            checks.append(dict(entry, error=f'GitHub API failure: {type(exc).__name__}: {str(exc)[:120]}'))
            continue
        blobs = {x['path']: x['sha'] for x in sub_tree['tree'] if x['type'] == 'blob'}
        copy = trimmed[t['path']]
        matched = sum(blobs.get(p) == sha for p, sha in copy.items())
        entry.update(repository=f'https://github.com/{sub_owner}/{sub_name}', tree_entries=len(sub_tree['tree']),
                     tree_truncated=bool(sub_tree.get('truncated')), sdist_copy_files=len(copy),
                     sdist_copy_files_matching_pinned_blobs=matched,
                     notice_like=[p for p in blobs if is_notice_like(p)][:MAX_LISTED])
        for path in (p for p in blobs if is_notice_name(p)):
            notice = {'source': f'submodule {sub_owner}/{sub_name}@{t["sha"][:12]} (pinned by {owner}/{name}@'
                                f'{commit[:12]} at {t["path"]})', 'path': f'{t["path"]}/{path}',
                      'counts_for_outcome': version_verified}
            if version_verified:
                url = f'{RAW}/{sub_owner}/{sub_name}/{t["sha"]}/{path}'
                try:
                    data = fetch(url)
                    notice.update(sha256=sha256_bytes(data), retained=retain(
                        source_name(distribution, f'submodule-{t["sha"][:12]}', f'{t["path"]}/{path}'), url, data,
                        kind='notice'))
                except Exception as exc:
                    notice.update(counts_for_outcome=False, error=f'{type(exc).__name__}: {str(exc)[:120]}')
            entry['notices'].append(notice)
        entry['cleared'] = (version_verified and not entry['notices'] and not entry['notice_like'] and
                            not entry['tree_truncated'] and len(copy) > 0 and matched == len(copy))
        checks.append(entry)
    return checks


def repository_summary(repo):
    if not repo.get('commit'):
        return f"not checked ({repo.get('reason', 'not performed')})"
    vc = repo.get('version_check', {})
    found = [n['path'] for n in repo.get('notices', [])]
    version = f"version verified in {vc['path']}" if vc.get('verified') else 'version NOT verified at the commit'
    subs = '; '.join(
        f"submodule {s['path']}@{s.get('pinned_commit', '?')[:12]}: " +
        (s['error'] if s.get('error') else
         f"{len(s['notices'])} NOTICE-named file(s), {s['sdist_copy_files_matching_pinned_blobs']}/"
         f"{s['sdist_copy_files']} sdist files match its blobs, {'cleared' if s['cleared'] else 'not cleared'}")
        for s in repo.get('submodule_checks', []))
    return (f"{repo['repository'].split('github.com/')[1]}@{repo['commit'][:12]} (tag {repo['tag']}, {version}): "
            + (f"NOTICE-named paths {', '.join(found)} (not counted)" if found else
               f"no NOTICE-named file in {repo['tree_entries']} tree entries"
               f"{' (tree truncated)' if repo.get('tree_truncated') else ''}")
            + (f'; {subs}' if subs else '')
            + '; a NOTICE-free repository is required for, but does not alone establish, verified_absent')


def decide(evidence, notices, lookup_repository):
    """(outcome, reason, repository record). Unless a NOTICE was already found in the wheel or the sdist, the release
    repository is always consulted: absence from the wheel and sdist does not establish absence upstream, and only a
    version-verified, complete, NOTICE-free repository tree lets a row be verified_absent."""
    outcome, reason = classify(evidence)
    if outcome == 'found':
        return outcome, reason, {'performed': False,
                                 'reason': 'not needed (a NOTICE was found in the wheel or sdist)'}
    repo = lookup_repository()
    subs = repo.get('submodule_checks', [])
    counted = [n for n in repo.get('notices', []) + [n for s in subs for n in s.get('notices', [])]
               if n.get('counts_for_outcome')]
    for path in [s['path'] for s in subs if s.get('cleared')]:
        evidence.setdefault('trimmed', {}).pop(path, None)
    evidence['cleared'] = [f"{s['path']} ({s['repository'].split('github.com/')[1]}@{s['pinned_commit'][:12]}, "
                           f"{s['sdist_copy_files']} files matching its blobs, no NOTICE-named file)"
                           for s in subs if s.get('cleared')]
    evidence['repository'] = {
        'verified_clean': bool(repo.get('commit') and repo.get('version_check', {}).get('verified')
                               and not repo.get('notices') and not repo.get('notice_like')
                               and not repo.get('tree_truncated')),
        'summary': repository_summary(repo)}
    if counted:
        evidence['notices'] = notices + counted
    outcome, reason = classify(evidence)
    if outcome == 'inconclusive' and 'release repository was not verified' not in reason:
        reason += '. Repository: ' + repository_summary(repo)
    return outcome, reason, repo


def check(row, inventory):
    distribution, version = row['distribution'], row['version']
    artifact = artifact_for(distribution)
    if (artifact['filename'], artifact['sha256']) != (row['artifact'], row['sha256']):
        raise SystemExit(f"{row['artifact']}: worksheet row does not match the approved manifest")
    members, wheel_notice_bytes, metadata = scan_wheel(artifact)
    record = {'artifact': row['artifact'], 'sha256': row['sha256'], 'distribution': distribution, 'version': version,
              'licence_documents': inventory.get('licence_documents', ''),
              'metadata_declared': inventory.get('metadata_declared', ''),
              'wheel': {'files': len(members), 'native_binaries': sum(m['elf'] for m in members)}}
    notices, notice_like = [], []
    for path, data in sorted(wheel_notice_bytes.items()):
        if is_notice_name(path):
            notices.append({'source': 'wheel', 'path': path, 'sha256': sha256_bytes(data),
                            'retained': retain(source_name(distribution, 'wheel', path),
                                               f"wheel:{artifact['filename']}#{path}", data, kind='notice')})
        else:
            notice_like.append(f'wheel: {path}')
    evidence = {'notices': notices, 'notice_like': notice_like, 'outside': [], 'trimmed': {}}
    listing, trimmed_blobs, vendored = None, {}, []
    try:
        data, sdist = verified_sdist(distribution, version, f'notice-{distribution}')
        if data is None:
            evidence['sdist'] = {'status': 'none', 'reason': sdist['reason']}
        else:
            evidence['sdist'] = dict(sdist, status='verified')
    except (Exception, SystemExit) as exc:
        data, evidence['sdist'] = None, {'status': 'error', 'reason': f'{type(exc).__name__}: {str(exc)[:200]}'}
    record['sdist'] = evidence['sdist']
    if data is not None:
        try:
            listing, kept = read_sdist(data, evidence['sdist']['sdist'])
            evidence.update(listing_complete=True, member_count=listing['members'])
        except Exception as exc:
            listing, kept = None, None
            evidence.update(listing_complete=False, listing_error=f'{type(exc).__name__}: {str(exc)[:200]}')
        if listing is not None:
            pkg_version = re.search(r'(?m)^Version:\s*(\S+)', kept['pkg_info'] or '')
            evidence['pkg_info_version_matches'] = bool(pkg_version and pkg_version.group(1) == version)
            for path, content in sorted(kept['notice'].items()):
                url = f"{evidence['sdist']['url']}#{listing['root']}{path}"
                if is_notice_name(path):
                    entry = {'source': f"sdist {evidence['sdist']['sdist']}", 'path': path}
                    if content is not None:
                        entry.update(sha256=sha256_bytes(content),
                                     retained=retain(source_name(distribution, 'sdist', path), url, content,
                                                     kind='notice'))
                    else:
                        entry['note'] = 'non-regular member with a NOTICE name'
                    notices.append(entry)
                else:
                    notice_like.append(f'sdist: {path}')
            rust = rust_summary(listing['files'], kept['cargo_lock'])
            hits = download_hits(kept['build'])
            evidence['outside'], coverage = outside_components(members, listing['files'], rust, hits, version)
            vendored = vendored_dirs(listing['files'])
            evidence['trimmed'] = trimmed_copies(vendored, members, listing['files'])
            trimmed_blobs = {d: {p[len(d) + 1:]: b for p, b in listing['git_blobs'].items() if p.startswith(d + '/')}
                             for d in evidence['trimmed']}
            record['sdist_listing'] = {'members': listing['members'], 'member_types': listing['types'],
                                       'regular_files': len(listing['files']), 'root': listing['root'],
                                       'pkg_info_version_matches': evidence['pkg_info_version_matches'],
                                       'notice_named_paths': [n['path'] for n in notices if n['source'] != 'wheel'],
                                       'notice_like_paths': [p for p in notice_like if p.startswith('sdist')],
                                       'rust': rust, 'third_party_dirs': vendored[:MAX_LISTED],
                                       'third_party_dirs_total': len(vendored),
                                       'trimmed_third_party_copies': dict(evidence['trimmed'])}
            record['wheel_traced_to_sdist'] = coverage
    outcome, reason, record['repository_check'] = decide(
        evidence, notices,
        lambda: repository_check(distribution, version, repository_from_metadata(metadata), trimmed_blobs))
    record.update(outcome=outcome, reason=reason, notices=evidence['notices'], notice_like=notice_like,
                  remains=remains(outcome, record['licence_documents'], record['metadata_declared'], vendored,
                                  not any(n['source'].startswith(('sdist', 'wheel')) for n in evidence['notices'])))
    return record


def build():
    inventory = inventory_rows()
    rows = flagged_rows()
    records = []
    for row in rows:
        try:
            records.append(check(row, inventory.get(row['artifact'], {})))
        except Exception as exc:  # recorded as inconclusive, never silently dropped
            records.append({'artifact': row['artifact'], 'sha256': row['sha256'], 'distribution': row['distribution'],
                            'version': row['version'], 'outcome': 'inconclusive', 'notices': [], 'notice_like': [],
                            'reason': f'processing error: {type(exc).__name__}: {str(exc)[:200]}',
                            'remains': remains('inconclusive', inventory.get(row['artifact'], {}).get(
                                'licence_documents'), inventory.get(row['artifact'], {}).get('metadata_declared'))})
        print(f"{row['artifact']}: {records[-1]['outcome']}", flush=True)
    counts = {o: sum(r['outcome'] == o for r in records) for o in OUTCOMES}
    return {'schema': 'wheelhouse_evidence_apache_notice_v1',
            'question': 'Does the exact upstream release include a NOTICE file that Apache-2.0 4(d) would require '
                        'to accompany the redistributed wheel?',
            'selection': f'decision-worksheet rows whose additional_obligations contain "{FLAG}"',
            'outcome_definitions': {
                'found': 'a NOTICE-named file is in the local wheel, the PyPI-verified exact-version sdist, or the '
                         'repository at a commit whose version file carries the exact version',
                'verified_absent': 'exact-version sdist verified against PyPI; complete listing has no NOTICE-named '
                                   'or notice-like file; every wheel component traced to the sdist; no wheel code '
                                   'from a trimmed third-party copy left unresolved; AND the release repository at a '
                                   'version-verified commit has no NOTICE-named or notice-like file',
                'inconclusive': 'anything else; the reason is recorded'},
            'notice_name_pattern': NOTICE_NAME.pattern, 'counts': counts, 'rows': records,
            'limits': [
                'a NOTICE file is identified by its name only; contents of other files were not searched for notices',
                'native binaries are traced by member inspection (auditwheel .libs, Rust Cargo.lock, download '
                'directives found by pattern in build scripts, matching source names, a few embedded library '
                'markers); static linking of toolchain runtime libraries was not assessed',
                'download directives inside a CMake if(BUILD_TESTING) branch are treated as test-only and not '
                'counted; they are listed in the pack',
                'a small wheel file named like a version stub (_version.py etc.) that is absent from the sdist but '
                'carries the exact version is treated as generated by the build backend',
                'a third-party directory carried inside an sdist counts as a complete copy if it keeps a top-level '
                'licence file (a NOTICE is conventionally top-level too); one without any is treated as a trimmed '
                'copy whose upstream NOTICE status is unknown, unless it is a git submodule at the version-verified '
                'release commit whose pinned upstream tree has no NOTICE-named file and whose blobs match every file '
                'of the copy',
                'repository trees do not show the contents of git submodules',
                'no legal conclusion is drawn; the reviewer decides']}


def cell(text):
    return str(text).replace('|', '\\|').replace('\n', ' ')


def markdown(p):
    c = p['counts']
    lines = ['# Apache-2.0 NOTICE check (three outcomes)', '',
             '**Evidence for the designated reviewer: a proposal, not a decision, and not legal clearance.**', '',
             'Apache-2.0 section 4(d) requires passing on a NOTICE file only if the Work as distributed includes one. '
             f"For each of the {len(p['rows'])} wheels whose worksheet row says \"{FLAG}\", this checks whether the "
             'exact upstream release includes a NOTICE-named file. `verified_absent` requires a PyPI-verified '
             'exact-version sdist whose complete listing has no NOTICE-named file and a wheel whose every component '
             'is traced to that sdist (third-party copies that the sdist carries in trimmed form must be resolved '
             'upstream); anything short of that is `inconclusive` with the reason. A fetch failure or a '
             'missing root-level file is never read as absence. Absence from the wheel and the sdist does not by '
             'itself establish absence upstream: `verified_absent` also requires the release repository, at a commit '
             'whose version file carries the exact version, to have no NOTICE-named or notice-like file. Where the '
             'repository cannot be verified the row stays `inconclusive` and the upstream question stays open.', '',
             f"**Counts:** found {c['found']}, verified_absent {c['verified_absent']}, inconclusive "
             f"{c['inconclusive']}.", '',
             '| Artifact | Outcome | Exact-release source | NOTICE paths (SHA-256) | Reason | What remains |',
             '|---|---|---|---|---|---|']
    for r in p['rows']:
        sd = r.get('sdist') or {}
        source = f"`{sd['sdist']}` (sha256 `{sd['sha256'][:12]}…`, PyPI-verified)" if sd.get('status') == 'verified' \
            else f"no verified sdist: {sd.get('reason', '?')}"
        repo = r.get('repository_check') or {}
        if repo.get('commit'):
            vc = repo.get('version_check', {})
            source += (f"; repo {repo['repository'].split('github.com/')[1]}@`{repo['commit'][:12]}` (tag "
                       f"`{repo['tag']}`, version {'verified in `' + vc['path'] + '`' if vc.get('verified') else 'NOT verified'})")
        notices = '; '.join(f"`{n['path']}` ({n['source'].split(' ')[0]}, `{n.get('sha256', '?')[:12]}…`)"
                            for n in r['notices']) or '—'
        lines.append(f"| `{r['artifact']}` | **{r['outcome']}** | {cell(source)} | {cell(notices)} | {cell(r['reason'])} "
                     f"| {cell(r['remains'])} |")
    lines += ['', '## Limits', ''] + [f'- {x}' for x in p['limits']]
    lines += ['', 'Retained files are under `reports/wheelhouse_evidence/sources/notice-*`; the JSON pack records each '
              "sdist's URL and SHA-256, the listing counts, the wheel-to-sdist tracing and any repository commit."]
    return '\n'.join(lines)


if __name__ == '__main__':
    payload = build()
    write_pack('apache_notice_check', payload, markdown(payload))
    print(json.dumps(payload['counts'], indent=1))
