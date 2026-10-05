"""Declared-licence discrepancies for ninja, regex and prometheus_client (evidence pack; a proposal for the designated
reviewer, not a decision and never legal clearance).

  python scripts/evidence_metadata.py

Each of the three wheels declares, in its metadata, a licence that the inventory did not find in the wheel's bundled
licence documents (ninja: BSD; regex: CNRI-Python; prometheus_client: BSD-2-Clause). For each wheel this checks:

- the local wheel, opened only after its SHA-256 matches the approved manifest: every licence/notice/authors file
  with the licence families its text carries, the METADATA licence fields, licence headers in every text file and
  licence strings embedded in every compiled file;
- the PyPI sdist of the exact version, verified against PyPI's SHA-256: its licence documents and every text member
  whose header carries a licence signal other than the wheel's detected family;
- where useful, upstream files at a verified commit or tag (ninja: the Kitware/ninja submodule commit of the
  ninja-python-distributions 1.13.0 tag, whose version file carries the version string embedded in the shipped
  binary; regex: the SPDX text of the declared identifier and CPython's licence files at the tags regex derives
  from; prometheus_client: the PyPI sdist of the vendored decorator release);

and then names the component carrying the extra licence, whether its files ship in the wheel, where its licence text
is, a proposed obligation, a classification (explained / partially_explained / unexplained) and the uncertainty left.
Licence texts and key excerpts relied on are retained under reports/wheelhouse_evidence/sources/ (prefix
metadata-<distribution>-). Writes reports/wheelhouse_evidence/metadata_discrepancies.{json,md}. At most two GitHub
API requests per run (raw file fetches do not use the API).
"""
import csv
import difflib
import io
import json
import posixpath
import re
import struct
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evidence_common import (artifact_for, fetch, open_wheel, retain, sha256_bytes,  # noqa: E402
                                     try_fetch_retained, verified_sdist, write_pack)

INVENTORY = ROOT / 'reports/wheelhouse_redistribution_inventory.csv'
WHEELS = (('ninja', '1.13.0'), ('regex', '2026.4.4'), ('prometheus_client', '0.25.0'))
CLASSIFICATIONS = ('explained', 'partially_explained', 'unexplained')
HEADER_CHARS = 4000
SMALL = 4 * 1024 ** 2

NINJA_SUBMODULE_API = ('https://api.github.com/repos/scikit-build/ninja-python-distributions/contents/ninja-upstream'
                       '?ref=1.13.0')
# Looked up through the API above on 2026-10-05; re-checked on every run in which the API answers.
NINJA_UPSTREAM_COMMIT = 'd74efef9fa331d3ae60b62479d49254827c081fe'
KITWARE_RAW = 'https://raw.githubusercontent.com/Kitware/ninja/{commit}/{path}'
NINJA_BINARY = 'ninja-1.13.0.data/scripts/ninja'
RAPIDHASH = 'src/third_party/rapidhash/rapidhash.h'
EMHASH = 'src/third_party/emhash/hash_table8.hpp'
RAPIDHASH_SECRETS = (0x2d358dccaa6c78a5, 0x8bb84b93962eacc9, 0x4b33a62ed433d4a3)  # rapid_secret[3] in rapidhash.h
NINJA_HISTORY_VERSION = '1.7.2'

SPDX_CNRI = 'https://raw.githubusercontent.com/spdx/license-list-data/v3.27.0/text/CNRI-Python.txt'
CPYTHON_RAW = 'https://raw.githubusercontent.com/python/cpython/{tag}/{path}'
CPYTHON_TAGS = {'v2.6': '2.6', 'v3.1': '3.1'}
CPYTHON_1_6_TAGS_API = 'https://api.github.com/repos/python/cpython/git/matching-refs/tags/v1.6'

LICENCE_DOC = re.compile(r'(?i)((^|/)(licen[cs]e|copying|notice|authors)[^/]*$|\.dist-info/licenses/)')
TEXT_PATTERNS = {  # wording that only a full licence text carries
    'Apache-2.0': r'TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION',
    'BSD': r'Redistribution and use in source and binary forms',
    'MIT': r'Permission is hereby granted, free of charge',
    'CNRI-Python': r'CNRI (OPEN SOURCE )?(GPL-COMPATIBLE )?LICENSE AGREEMENT',
    'PSF-2.0': r'PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2',
}
REFERENCE_PATTERNS = (  # wording that names or points to a licence
    ('Apache-2.0', r'Licensed under the Apache License|Apache License,? Version 2\.0|Apache 2\.0 License|\bApache-2\.0\b'),
    ('BSD-2-Clause', r'(?i)\bBSD[ -]2-Clause\b|\b2-clause BSD\b'),
    ('BSD-3-Clause', r'(?i)\bBSD[ -]3-Clause\b|\b3-clause BSD\b'),
    ('BSD (variant not named)', r'\bBSD License\b'),
    ('MIT', r'\bMIT License\b'),
    ('CNRI-Python', r"(?i)CNRI'?s Python 1\.6 license|\bCNRI-Python\b"),
    ('PSF-2.0', r'Python Software Foundation License|\bPSF License\b'),
    ('public-domain', r'(?i)\bpublic domain\b'),
)
SPDX = re.compile(r'SPDX-License-Identifier:\s*([^\s*]+(?:\s+(?:AND|OR|WITH)\s+[^\s*]+)*)')
INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)
PLATFORM_ONLY = re.compile(r'(-win32\.cc|(^|/)getopt\.c|\.manifest)$')  # CMakeLists adds these only for WIN32/OS400/AIX
PRINTABLE = re.compile(rb'[\x20-\x7e]{6,}')
MARKER_WORDS = re.compile(r'(?i)(copyright|licen[cs]e|\bBSD\b|\bMIT\b|public domain|secret labs|\bCNRI\b)')

RETAINED, FAILURES = [], []


# ---------------------------------------------------------------- pure helpers (unit-tested offline)

def plain(text):
    """Text with comment leaders (#, //, /*, *, */) removed from each line and whitespace collapsed."""
    lines = (re.sub(r'^\s*(#+|//+|/\*+|\*+/?|\*/)?\s?', '', line) for line in text.splitlines())
    return ' '.join(' '.join(lines).split())


def licence_signals(text):
    """Licence families a text carries as full licence wording ('text'), names or points to ('reference'), and its
    SPDX-License-Identifier values. Platform macros such as __FreeBSD__ are not licence signals."""
    flat = plain(text)
    found = sorted(f for f, p in TEXT_PATTERNS.items() if re.search(p, flat))
    if 'BSD' in found:
        found.remove('BSD')
        found.append('BSD-3-Clause-style' if re.search(r'Neither the name|endorse or promote', flat)
                     else 'BSD-2-Clause-style')
    return {'text': sorted(found), 'reference': sorted({f for f, p in REFERENCE_PATTERNS if re.search(p, flat)}),
            'spdx': sorted(set(SPDX.findall(text)))}


def any_signal(signals):
    return bool(signals['text'] or signals['reference'] or signals['spdx'])


def families(signals):
    return set(signals['text']) | set(signals['reference']) | set(signals['spdx'])


def leading_comment(text):
    """(first, last) 1-based line numbers of the leading comment block (a shebang line is skipped), or None."""
    lines = text.splitlines()
    i = 1 if lines and lines[0].startswith('#!') else 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return None
    first = lines[i].lstrip()
    if first.startswith('/*'):
        for j in range(i, len(lines)):
            if '*/' in lines[j]:
                return i + 1, j + 1
        return None
    prefix = '//' if first.startswith('//') else '#' if first.startswith('#') else None
    if prefix is None:
        return None
    last = i
    for j in range(i, len(lines)):
        stripped = lines[j].strip()
        if stripped.startswith(prefix):
            last = j
        elif stripped:
            break
    return i + 1, last + 1


def excerpt(text, span):
    first, last = span
    return '\n'.join(text.splitlines()[first - 1:last]) + '\n'


def declared_fields(metadata):
    """The METADATA lines that declare a licence (License, License-Expression, License-File, licence classifiers)."""
    header = metadata.split('\n\n', 1)[0]
    return [line for line in header.splitlines()
            if line.split(':', 1)[0] in ('License', 'License-Expression', 'License-File')
            or line.startswith('Classifier: License ::')]


def classify(component_found, ships_in_wheel, licence_text_located):
    """explained: a component carrying the extra licence was identified, its files ship in the wheel and its licence
    text was located; partially_explained: component identified but shipping or text not established;
    unexplained: no component identified."""
    if not component_found:
        return 'unexplained'
    return 'explained' if ships_in_wheel is True and licence_text_located else 'partially_explained'


def include_closure(sources, start):
    """Every file in `sources` (path -> text) reachable from `start` through #include "..." directives, resolved
    against the including file's directory and then the source root."""
    seen, todo = set(), [start]
    while todo:
        path = todo.pop()
        if path in seen or path not in sources:
            continue
        seen.add(path)
        folder = posixpath.dirname(path)
        for name in INCLUDE.findall(sources[path]):
            for candidate in (posixpath.normpath(posixpath.join(folder, name)), posixpath.normpath(name)):
                if candidate in sources:
                    todo.append(candidate)
                    break
    return seen


def cmake_linux_sources(text):
    """Sources of the ninja executable on Linux per ninja's CMakeLists.txt: the libninja* OBJECT libraries, the
    executable, and target_sources additions; files the CMakeLists adds only for WIN32 or OS400/AIX are dropped."""
    blocks = re.findall(r'(?:add_library\(libninja[-\w]* OBJECT|add_executable\(ninja |'
                        r'target_sources\((?:libninja|ninja) PRIVATE)(.*?)\)', text, re.S)
    tokens = {t for block in blocks for t in block.split() if t.startswith('src/')}
    return sorted(t for t in tokens if not PLATFORM_ONLY.search(t))


def count_u64(data, value):
    return data.count(struct.pack('<Q', value))


def compiled_markers(data):
    """Printable strings in a compiled file that name a copyright holder or a licence."""
    return sorted({s.decode('ascii').strip()[:120] for s in PRINTABLE.findall(data)
                   if MARKER_WORDS.search(s.decode('ascii'))})


def is_text(data):
    return b'\x00' not in data[:8192]


def fmt_signals(signals):
    return '; '.join(f"{k}: {', '.join(signals[k]) or '—'}" for k in ('text', 'reference', 'spdx'))


def fmt_span(span):
    return f'{span[0]}-{span[1]}' if span else 'none'


def fmt_matches(matches):
    return ', '.join(f"`{path}` {'yes' if same else 'NO'}" for path, same in matches.items())


# ---------------------------------------------------------------- retention and scanning

def keep(name, url, cap=SMALL):
    data, record = try_fetch_retained(name, url, cap)
    (RETAINED if data is not None else FAILURES).append(record)
    return data, record


def keep_member(name, source_url, member, data, span=None, what=''):
    """Retain an archive member, or a fetched file when member is None (whole, or the given line span as an
    excerpt), with its provenance and the SHA-256 of the whole member."""
    body = data if span is None else excerpt(data.decode('utf-8', 'replace'), span).encode('utf-8')
    url = f'{source_url}#{member}' if member else source_url
    record = retain(name, url, body, kind=('archive member' if member else 'file') if span is None else 'excerpt')
    record.update(member=member, member_sha256=sha256_bytes(data), what=what)
    if span:
        record['lines'] = list(span)
    RETAINED.append(record)
    return record


def inventory_row(distribution):
    with INVENTORY.open(encoding='utf-8', newline='') as handle:
        row = next(r for r in csv.DictReader(handle) if r['distribution'] == distribution)
    return {k: row[k] for k in ('metadata_declared', 'detected_families', 'licence_documents', 'flags')}


def wheel_scan(distribution):
    artifact = artifact_for(distribution)
    z = open_wheel(artifact)
    files, documents, signalled, compiled = [], [], [], []
    for info in z.infolist():
        if info.filename.endswith('/'):
            continue
        data = z.read(info)
        entry = {'path': info.filename, 'bytes': info.file_size, 'sha256': sha256_bytes(data)}
        files.append(entry)
        if not is_text(data):
            compiled.append(dict(entry, markers=compiled_markers(data)))
        elif LICENCE_DOC.search(info.filename):
            documents.append(dict(entry, signals=licence_signals(data.decode('utf-8', 'replace'))))
        elif '.dist-info/' not in info.filename:
            text = data.decode('utf-8', 'replace')
            signals = licence_signals(text[:HEADER_CHARS])
            if any_signal(signals):
                signalled.append(dict(entry, signals=signals, leading_comment=leading_comment(text)))
    metadata = z.read(next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))).decode('utf-8')
    record = {'artifact': artifact['filename'], 'sha256': artifact['sha256'], 'url': artifact['url'],
              'files': len(files), 'text_files_scanned': len(files) - len(compiled),
              'declared': declared_fields(metadata), 'licence_documents': documents,
              'files_with_licence_signals': signalled, 'compiled_files': compiled,
              'inventory': inventory_row(distribution)}
    return record, z, {f['path']: f['sha256'] for f in files}, metadata


def sdist_scan(project, version, wheel_family='Apache-2.0'):
    data, record = verified_sdist(project, version, f'metadata-{project}')
    tar = tarfile.open(fileobj=io.BytesIO(data))
    members = {m.name.split('/', 1)[1]: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    documents, other = [], []
    scanned = 0
    for path, body in sorted(members.items()):
        if not is_text(body):
            continue
        scanned += 1
        text = body.decode('utf-8', 'replace')
        if LICENCE_DOC.search(path):
            documents.append({'member': path, 'sha256': sha256_bytes(body), 'signals': licence_signals(text)})
        signals = licence_signals(text[:HEADER_CHARS])
        if families(signals) - {wheel_family}:
            other.append({'member': path, 'sha256': sha256_bytes(body), 'signals': signals})
    record.update(files=len(members), text_files_scanned=scanned, licence_documents=documents,
                  members_with_signals_other_than_wheel_family=other, wheel_family=wheel_family)
    return record, members


def same_as_sdist(wheel_hashes, members, pairs):
    return {wheel_path: wheel_hashes[wheel_path] == sha256_bytes(members[member]) for wheel_path, member in pairs}


# ---------------------------------------------------------------- per-wheel checks

def ninja_pack():
    wheel, z, hashes, metadata = wheel_scan('ninja')
    sdist, members = sdist_scan('ninja', '1.13.0')
    up = {k[len('ninja-upstream/'):]: v.decode('utf-8', 'replace') for k, v in members.items()
          if k.startswith('ninja-upstream/') and is_text(v)}
    linux = cmake_linux_sources(up['CMakeLists.txt'])
    closures = {src: include_closure(up, src) for src in linux}
    rapid_users = sorted(s for s, c in closures.items() if RAPIDHASH in c)
    emhash_users = sorted(s for s, c in closures.items() if EMHASH in c)
    rapid_callers = sorted(p for p, t in up.items() if p.startswith('src/') and p != RAPIDHASH and 'rapidhash(' in t)
    wyhash_switch = sorted(p for p, t in up.items() if p != EMHASH and 'EMH_WYHASH_HASH' in t)

    binary = z.read(NINJA_BINARY)
    version = re.search(r'kNinjaVersion = "([^"]+)"', up['src/version.cc']).group(1)
    readme_version = re.search(r'provide `ninja (\S+) <', metadata)
    markers = next(c['markers'] for c in wheel['compiled_files'] if c['path'] == NINJA_BINARY)
    binary_evidence = {
        'path': NINJA_BINARY, 'sha256': hashes[NINJA_BINARY],
        'sdist_kNinjaVersion': version, 'kNinjaVersion_embedded_in_binary': version.encode() in binary,
        'version_named_in_wheel_readme': readme_version.group(1) if readme_version else None,
        'rapidhash_secret_occurrences': {hex(s): count_u64(binary, s) for s in RAPIDHASH_SECRETS},
        'rapidhash_secrets_also_in_emhash_header': all(f'{s:#x}' in up[EMHASH].lower() for s in RAPIDHASH_SECRETS),
        'files_mentioning_EMH_WYHASH_HASH_outside_emhash': wyhash_switch,
        'embedded_licence_strings': markers,
        'embedded_licence_strings_all_from_src_browse_py': all(m in up['src/browse.py'] for m in markers),
        'stripped_no_symbol_names': b'rapidhash' not in binary and b'emhash' not in binary,
    }

    upstream = {'submodule_lookup': NINJA_SUBMODULE_API}
    api, api_record = keep('metadata-ninja-github-submodule-at-1.13.0.json', NINJA_SUBMODULE_API, 1024 ** 2)
    commit = json.loads(api)['sha'] if api else NINJA_UPSTREAM_COMMIT
    upstream.update(commit=commit, commit_from_api_this_run=api is not None,
                    commit_matches_recorded=commit == NINJA_UPSTREAM_COMMIT,
                    readme_short_hash_matches=bool(readme_version) and f'.g{commit[:5]}.' in readme_version.group(1),
                    files={})
    for path in ('src/version.cc', 'src/hash_map.h', 'src/third_party/rapidhash/README.ninja', RAPIDHASH,
                 'src/third_party/emhash/README.ninja'):
        data, record = keep(f"metadata-ninja-kitware-{commit[:8]}-{path.replace('/', '_')}",
                            KITWARE_RAW.format(commit=commit, path=path))
        upstream['files'][path] = {'retained': record.get('file'), 'sha256': record.get('sha256'),
                                   'error': record.get('error'),
                                   'identical_to_sdist': data == members['ninja-upstream/' + path] if data else None}
        if path == 'src/version.cc' and data:
            upstream['version_file_contains_binary_version'] = f'"{version}"' in data.decode('utf-8', 'replace')

    history, history_record = keep(f'metadata-ninja-pypi-{NINJA_HISTORY_VERSION}.json',
                                   f'https://pypi.org/pypi/ninja/{NINJA_HISTORY_VERSION}/json')
    history_classifiers = ([c for c in json.loads(history)['info']['classifiers'] if c.startswith('License')]
                           if history else None)

    rh_bytes = members['ninja-upstream/' + RAPIDHASH]
    em_bytes = members['ninja-upstream/' + EMHASH]
    rh_span = leading_comment(rh_bytes.decode())
    rh_record = keep_member('metadata-ninja-rapidhash-licence-header.txt', sdist['url'], 'ninja-upstream/' + RAPIDHASH,
                            rh_bytes, rh_span, 'rapidhash BSD 2-Clause notice')
    em_record = keep_member('metadata-ninja-emhash-licence-header.txt', sdist['url'], 'ninja-upstream/' + EMHASH,
                            em_bytes, leading_comment(em_bytes.decode()), 'emhash MIT notice')
    rh_signals = licence_signals(excerpt(rh_bytes.decode(), rh_span))

    copying = members['ninja-upstream/COPYING']
    shipped = bool(rapid_users) and binary_evidence['kNinjaVersion_embedded_in_binary'] and \
        all(binary_evidence['rapidhash_secret_occurrences'].values()) and not wyhash_switch
    component = {
        'name': 'rapidhash (Copyright (C) 2024 Nicolas De Carli; based on wyhash by Wang Yi), vendored by ninja at '
                'ninja-upstream/src/third_party/rapidhash/',
        'licence': 'BSD-2-Clause (SPDX identifier in README.ninja; BSD 2-Clause wording in the rapidhash.h header)',
        'source_members': {m: sha256_bytes(members['ninja-upstream/' + m]) for m in
                           (RAPIDHASH, 'src/third_party/rapidhash/README.ninja')},
        'linux_sources_of_the_binary': linux,
        'linux_sources_including_it': rapid_users,
        'sources_calling_rapidhash': rapid_callers,
        'ships_in_wheel': True if shipped else None,
        'shipped_as': {'path': NINJA_BINARY, 'sha256': hashes[NINJA_BINARY], 'form': 'compiled into the ninja '
                       'executable (ELF, stripped)'},
    }
    located = 'BSD-2-Clause-style' in rh_signals['text']
    emhash = {
        'name': 'emhash8::HashMap 1.6.5 (Copyright (c) 2021-2024 Huang Yuanbing & bailuzhou), vendored at '
                'ninja-upstream/src/third_party/emhash/',
        'licence': 'MIT (SPDX identifier in README.ninja and the header; full MIT wording in the header)',
        'linux_sources_including_it': emhash_users, 'declared_in_wheel_metadata': False,
        'licence_text_retained': em_record['file'],
    }
    return {
        'distribution': 'ninja', 'version': '1.13.0', 'wheel': wheel, 'sdist': sdist, 'upstream': upstream,
        'extra_declared_licence': 'BSD (classifier "License :: OSI Approved :: BSD License", variant not named)',
        'classifier_history': {'version': NINJA_HISTORY_VERSION, 'licence_classifiers': history_classifiers,
                               'retained': history_record.get('file'), 'error': history_record.get('error')},
        'binary_evidence': binary_evidence,
        'wheel_apache_text_identical_to_ninja_COPYING': hashes['ninja-1.13.0.dist-info/licenses/LICENSE_Apache_20']
        == sha256_bytes(copying),
        'component': component,
        'licence_text_location': {
            'in_wheel': 'no (the wheel carries only LICENSE_Apache_20 and AUTHORS.rst)',
            'in_sdist': f'yes: ninja-upstream/{RAPIDHASH} lines {rh_span[0]}-{rh_span[1]} (licence header); '
                        'README.ninja beside it names SPDX BSD-2-Clause',
            'upstream': f'Kitware/ninja@{commit[:12]}/{RAPIDHASH}', 'retained': [rh_record['file']],
            'retained_text_signals': rh_signals},
        'proposed_obligation': (
            f'Ship, alongside the wheel and its bundled LICENSE_Apache_20 and AUTHORS.rst, the rapidhash BSD-2-Clause '
            f'notice (copyright line, both conditions and the disclaimer) from {rh_record["file"]}: rapidhash code is '
            f'compiled into {NINJA_BINARY}, and the licence asks binary redistributions to reproduce the notice in '
            f'the documentation or other materials; the wheel carries no copy. Because emhash (MIT) is compiled into '
            f'the same binary and is not declared, also ship its MIT notice from {em_record["file"]}.'),
        'classification': classify(bool(rapid_users), component['ships_in_wheel'], located),
        'uncertainty': [
            f'The BSD classifier is already in the ninja {NINJA_HISTORY_VERSION} metadata (2016; retained PyPI JSON), '
            'long before ninja vendored rapidhash. The classifier names no variant and its original basis was not '
            'established: rapidhash accounts for a BSD-licensed component in this wheel, which may not be the '
            'reason the maintainers added the classifier.',
            'The binary is stripped. That rapidhash ships rests on the Linux source set (files including hash_map.h, '
            'and build_log.cc, call rapidhash()) and on its three 64-bit secret constants occurring in the binary. '
            'The same constants also appear in the emhash header, but only under EMH_WYHASH_HASH, which '
            + ('no other ninja-upstream file mentions.' if not wyhash_switch else
               f'is also mentioned in {", ".join(wyhash_switch)}, so the constants do not single out rapidhash.'),
            'The wheel was not rebuilt from these sources. The link between the shipped binary and the sdist and '
            'submodule sources rests on the kNinjaVersion string (sdist, submodule commit and binary agree) and on '
            'the commit hash abbreviated in the wheel README.',
            'emhash presence rests on source evidence only (header-only template code; no distinctive marker in '
            'the stripped binary).',
            'Not examined: toolchain runtime code statically linked by the manylinux2014 toolchain (GCC 10.2.1 and '
            '4.8.5 ident strings in the binary) and its terms.'],
        'other_observations': [
            {'component': emhash['name'], 'licence': emhash['licence'],
             'note': 'compiled into the binary per the Linux source set; licence not declared in the metadata; text '
                     f'retained at {em_record["file"]}', 'linux_sources_including_it': emhash_users},
            {'component': 'ninja-upstream/src/getopt.c (public domain)',
             'note': 'not compiled on Linux: CMakeLists adds it only under WIN32 and OS400/AIX',
             'in_linux_source_set': 'src/getopt.c' in linux},
            {'component': 'embedded browse.py text', 'note': 'the licence strings in the binary all come from '
             'src/browse.py (Apache-2.0, Google)' if binary_evidence['embedded_licence_strings_all_from_src_browse_py']
             else 'some licence strings in the binary are not from src/browse.py'}],
    }


def regex_pack():
    wheel, z, hashes, _ = wheel_scan('regex')
    sdist, members = sdist_scan('regex', '2026.4.4')
    so_path = 'regex/_regex.cpython-312-x86_64-linux-gnu.so'
    so = z.read(so_path)
    c_text = members['src/_regex.c'].decode('utf-8')
    copyright_string = re.search(r'static char copyright\[\] =\s*"([^"]+)"', c_text).group(1)
    secret_labs_wheel = [{'path': p, 'sha256': hashes[p], 'header_lines': leading_comment(z.read(p).decode())}
                         for p in ('regex/_main.py', 'regex/_regex_core.py')
                         if 'CNRI-Python' in licence_signals(z.read(p).decode()[:HEADER_CHARS])['reference']]
    extension_sources = re.findall(r"'(src/[^']+\.c)'", members['setup.py'].decode())
    unicode_version = re.search(r'RE_UNICODE_VERSION "([^"]+)"', members['src/_regex_unicode.h'].decode()).group(1)

    keep_member('metadata-regex-_main.py-licence-header.txt', wheel['url'], 'regex/_main.py',
                z.read('regex/_main.py'), leading_comment(z.read('regex/_main.py').decode()),
                'SRE copyright and CNRI statement as shipped in the wheel')
    c_record = keep_member('metadata-regex-_regex.c-licence-header.txt', sdist['url'], 'src/_regex.c',
                           members['src/_regex.c'], leading_comment(c_text),
                           'SRE copyright and CNRI statement in the C source of the compiled module')
    spdx, spdx_record = keep('metadata-regex-spdx-v3.27.0-CNRI-Python.txt', SPDX_CNRI)
    spdx_text = spdx.decode('utf-8') if spdx else ''
    clause_2 = re.search(r'2\. Subject to.*?(?= 3\. )', plain(spdx_text))
    cpython = {}
    for tag, version in CPYTHON_TAGS.items():
        patch, patch_record = keep(f'metadata-regex-cpython-{tag}-patchlevel.h',
                                   CPYTHON_RAW.format(tag=tag, path='Include/patchlevel.h'))
        lic, lic_record = keep(f'metadata-regex-cpython-{tag}-LICENSE.txt', CPYTHON_RAW.format(tag=tag, path='LICENSE'))
        cpython[tag] = {
            'tag_carries_version': bool(patch) and re.search(rf'#define PY_VERSION\s+"{re.escape(version)}"',
                                                             patch.decode()) is not None,
            'patchlevel': patch_record.get('file'), 'licence': lic_record.get('file'),
            'licence_signals': licence_signals(lic.decode()) if lic else None,
            'cnri_1_6_1_agreement_present': bool(lic) and 'CNRI LICENSE AGREEMENT FOR PYTHON 1.6.1' in lic.decode()}
    sre_url = CPYTHON_RAW.format(tag='v3.1', path='Modules/_sre.c')
    try:
        sre = fetch(sre_url)
        keep_member('metadata-regex-cpython-v3.1-_sre.c-licence-header.txt', sre_url, None, sre,
                    leading_comment(sre.decode('utf-8', 'replace')),
                    "CPython 3.1 Modules/_sre.c header: the statement regex's headers repeat")
        sre_statement_same = ("This version of the SRE library can be redistributed under CNRI's Python 1.6 license"
                              in plain(sre.decode('utf-8', 'replace')))
    except Exception as exc:  # recorded, not treated as absence
        FAILURES.append({'url': sre_url, 'error': f'{type(exc).__name__}: {str(exc)[:200]}'})
        sre_statement_same = None
    tags, tags_record = keep('metadata-regex-cpython-tags-v1.6.json', CPYTHON_1_6_TAGS_API, 1024 ** 2)
    v16_tags = sorted(r['ref'].rsplit('/', 1)[1] for r in json.loads(tags)) if tags else None

    in_so = copyright_string.encode() in so
    component = {
        'name': "SRE regular expression engine (Copyright (c) 1997-2001 Secret Labs AB), from CPython 2.6/3.1's re "
                'module, from which regex derives',
        'licence': "CNRI's Python 1.6 license (source headers); declared as SPDX CNRI-Python",
        'files_in_wheel': secret_labs_wheel + [{'path': so_path, 'sha256': hashes[so_path],
                                                'embedded_string': copyright_string.strip(),
                                                'string_from_src__regex_c_present': in_so}],
        'compiled_from': extension_sources,
        'ships_in_wheel': True if secret_labs_wheel and in_so else None,
        'wheel_matches_sdist': same_as_sdist(hashes, members, [('regex/_main.py', 'regex/_main.py'),
                                                               ('regex/_regex_core.py', 'regex/_regex_core.py'),
                                                               ('regex-2026.4.4.dist-info/licenses/LICENSE.txt',
                                                                'LICENSE.txt')]),
        'cpython_3_1_sre_header_carries_same_statement': sre_statement_same,
    }
    located = 'CNRI-Python' in licence_signals(spdx_text)['text']
    return {
        'distribution': 'regex', 'version': '2026.4.4', 'wheel': wheel, 'sdist': sdist,
        'extra_declared_licence': 'CNRI-Python (License-Expression "Apache-2.0 AND CNRI-Python")',
        'component': component,
        'licence_text_location': {
            'in_wheel': 'no: LICENSE.txt names "CNRI\'s Python 1.6 license" in its first paragraph but carries only '
                        'the Apache-2.0 text', 'in_sdist': 'no (same LICENSE.txt)',
            'upstream': {'spdx_CNRI-Python': spdx_record.get('file'), 'cpython': cpython,
                         'cpython_v1.6_tags': v16_tags, 'cpython_v1.6_tags_error': tags_record.get('error')},
            'retained': [r for r in (spdx_record.get('file'), cpython['v3.1']['licence'], cpython['v2.6']['licence'])
                         if r],
            'spdx_clause_2': ' '.join(clause_2.group(0).split())[:1200] if clause_2 else None},
        'proposed_obligation': (
            'Ship, alongside the wheel and its bundled LICENSE.txt, a copy of the CNRI licence text. Proposed: '
            f'{spdx_record.get("file")} (the text of the declared SPDX identifier, which in clause 2 asks that the '
            'CNRI agreement be retained in any derivative version). The reviewer may instead or also choose the '
            f'CPython licence file ({cpython["v3.1"]["licence"]}), which carries the CNRI agreement for Python 1.6.1 '
            'within the PSF licence history. The Secret Labs AB copyright notices already ship in the headers of '
            'regex/_main.py and regex/_regex_core.py; keep those files unmodified.'),
        'classification': classify(bool(secret_labs_wheel), component['ships_in_wheel'], located),
        'uncertainty': [
            '"CNRI\'s Python 1.6 license" in the headers does not pin a text: SPDX CNRI-Python is worded for Python '
            '1.6b1, CPython 2.6/3.1 carry the agreement for Python 1.6.1, and the Python 1.6 final text was not '
            'retrieved' + (f' (the CPython repository has tags {", ".join(v16_tags)} only, no v1.6 final)'
                           if v16_tags else ' (the CPython tag lookup failed this run)') +
            '. Which text satisfies the headers is for the reviewer.',
            'regex derives from the re module of CPython 2.6 and 3.1. Changes made inside CPython between 2001 and '
            '2009 may fall under the PSF licence history, which the declared expression does not name. Not resolved.',
            f'src/_regex_unicode.c, compiled into the module, holds tables generated from the Unicode Character '
            f'Database {unicode_version} (tools/build_regex_unicode.py). Whether Unicode data licence terms apply '
            'was not examined.'],
        'other_observations': [{'note': 'src/_regex.h (sdist only, compiled in) carries the Secret Labs AB copyright '
                                        'line without the CNRI statement', 'retained': c_record['file']}],
    }


def prometheus_pack():
    wheel, z, hashes, _ = wheel_scan('prometheus_client')
    sdist, members = sdist_scan('prometheus_client', '0.25.0')
    path, notice_path = 'prometheus_client/decorator.py', 'prometheus_client-0.25.0.dist-info/licenses/NOTICE'
    vendored = z.read(path)
    text = vendored.decode('utf-8')
    span = leading_comment(text)
    bundled_version = re.search(r"__version__ = '([^']+)'", text).group(1)
    holder = re.search(r'Copyright \(c\) ([0-9-]+, [^\n]+)', text).group(1).strip()
    importers = sorted(n for n in z.namelist() if n.endswith('.py') and n != path
                       and re.search(r'from \.decorator import|from prometheus_client\.decorator import|'
                                     r'import decorator', z.read(n).decode('utf-8')))
    header_record = keep_member('metadata-prometheus_client-decorator-licence-header.txt', wheel['url'], path,
                                vendored, span, 'decorator BSD-style licence text as shipped in the wheel')
    notice_record = keep_member('metadata-prometheus_client-NOTICE.txt', wheel['url'], notice_path,
                                z.read(notice_path), None, 'NOTICE bundled in the wheel')
    notice = z.read(notice_path).decode('utf-8')
    header_signals = licence_signals(excerpt(text, span))

    data, dec_sdist = verified_sdist('decorator', bundled_version, 'metadata-prometheus_client-decorator')
    tar = tarfile.open(fileobj=io.BytesIO(data))
    dec_members = {m.name.split('/', 1)[1]: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    upstream_py = dec_members['src/decorator.py'].decode('utf-8')
    upstream_header = excerpt(upstream_py, leading_comment(upstream_py))
    licence_record = keep_member(f'metadata-prometheus_client-decorator-{bundled_version}-LICENSE.txt',
                                 dec_sdist['url'], 'LICENSE.txt', dec_members['LICENSE.txt'], None,
                                 f'decorator {bundled_version} LICENSE.txt (upstream sdist)')
    licence_years = re.search(r'Copyright \(c\) ([0-9-]+)', dec_members['LICENSE.txt'].decode()).group(1)
    header_diff = [line for line in difflib.unified_diff(upstream_header.splitlines(), excerpt(text, span).splitlines(),
                                                         lineterm='', n=0) if line[:1] in '+-'
                   and not line.startswith(('+++', '---'))]
    component = {
        'name': f'decorator {bundled_version} (Copyright (c) {holder}), vendored as {path}',
        'licence': 'BSD-style 2-clause licence (header of the vendored file; "bytecode form" wording)',
        'files_in_wheel': [{'path': path, 'sha256': hashes[path], 'licence_header_lines': list(span)}],
        'imported_by': importers,
        'ships_in_wheel': True,
        'notice_points_to_it': 'decorator' in notice and path in notice,
        'wheel_matches_sdist': same_as_sdist(hashes, members, [(path, path), (notice_path, 'NOTICE'),
                                                               ('prometheus_client-0.25.0.dist-info/licenses/LICENSE',
                                                                'LICENSE')]),
        'upstream_release': dict(dec_sdist, vendored_file_identical_to_upstream=upstream_py.encode() == vendored,
                                 licence_header_differences_from_upstream_src=header_diff),
    }
    located = 'BSD-2-Clause-style' in header_signals['text']
    return {
        'distribution': 'prometheus_client', 'version': '0.25.0', 'wheel': wheel, 'sdist': sdist,
        'extra_declared_licence': 'BSD-2-Clause (License-Expression "Apache-2.0 AND BSD-2-Clause")',
        'component': component,
        'licence_text_location': {
            'in_wheel': f'yes: {path} lines {span[0]}-{span[1]} (the licence text itself), pointed to by the bundled '
                        'NOTICE; the inventory read only dist-info/licenses/ and so did not see it',
            'in_sdist': 'yes (same file and NOTICE)', 'upstream': f'decorator {bundled_version} LICENSE.txt',
            'retained': [header_record['file'], notice_record['file'], licence_record['file']],
            'retained_text_signals': header_signals},
        'proposed_obligation': (
            f'Ship the wheel unmodified: {path} carries the licence text in its header and the bundled NOTICE points '
            f'to it. Where licence documents are collected separately from the wheel, add the decorator notice from '
            f'{header_record["file"]} beside LICENSE and NOTICE. If the module is ever redistributed only as '
            'bytecode, the licence asks for the notice in the accompanying documentation.'),
        'classification': classify(True, True, located),
        'uncertainty': [
            'The licence says "Redistributions in bytecode form" where SPDX BSD-2-Clause says "binary form". The '
            'declared identifier is close to the text but not verbatim. Whether SPDX matching treats it as '
            'BSD-2-Clause was not checked.',
            f'The vendored file differs from decorator {bundled_version} src/decorator.py (formatting and Python 3 '
            'changes). The file does not state the licence of the Prometheus authors\' changes; presumably it is the '
            'project licence (Apache-2.0).',
            'Licence header differences from upstream src/decorator.py: ' + ('; '.join(header_diff) or 'none') +
            f'. Upstream LICENSE.txt gives the years as {licence_years}.'],
        'other_observations': [],
    }


def build():
    RETAINED.clear()
    FAILURES.clear()
    wheels = [ninja_pack(), regex_pack(), prometheus_pack()]
    return {'schema': 'wheelhouse_evidence_metadata_discrepancies_v1',
            'scope': 'three wheels whose declared licence metadata names a licence not found in the wheel\'s bundled '
                     'licence documents (inventory flag "declared licence not found in documents")',
            'classifications': list(CLASSIFICATIONS), 'wheels': wheels,
            'retained_sources': RETAINED, 'fetch_failures': FAILURES}


# ---------------------------------------------------------------- markdown

def table_of_documents(w):
    lines = ['| Path | SHA-256 | Licence signals |', '|---|---|---|']
    for d in w['wheel']['licence_documents']:
        lines.append(f"| `{d['path']}` | `{d['sha256'][:12]}…` | {fmt_signals(d['signals'])} |")
    return lines


def searched(w):
    wh, sd = w['wheel'], w['sdist']
    lines = [f"- Wheel: {wh['files']} files; {wh['text_files_scanned']} text files scanned for licence headers (first "
             f"{HEADER_CHARS} characters), licence documents read in full; {len(wh['compiled_files'])} compiled "
             'file(s) scanned for embedded licence strings.']
    for f in wh['files_with_licence_signals']:
        lines.append(f"  - `{f['path']}` (`{f['sha256'][:12]}…`, header lines {fmt_span(f['leading_comment'])}): "
                     f"{fmt_signals(f['signals'])}")
    for c in wh['compiled_files']:
        lines.append(f"  - compiled `{c['path']}` (`{c['sha256'][:12]}…`): "
                     + ('; '.join(f'"{m}"' for m in c['markers']) or 'no licence strings'))
    lines.append(f"- Sdist `{sd['sdist']}` (sha256 `{sd['sha256']}`, verified against PyPI): {sd['files']} files, "
                 f"{sd['text_files_scanned']} text files scanned. Licence documents: "
                 + ', '.join(f"`{d['member']}` ({fmt_signals(d['signals'])})" for d in sd['licence_documents']) + '.')
    lines.append(f"  Members whose header carries a licence signal other than {sd['wheel_family']}:")
    for m in sd['members_with_signals_other_than_wheel_family']:
        lines.append(f"  - `{m['member']}`: {fmt_signals(m['signals'])}")
    return lines


def retained_table(names, p):
    by_file = {r['file']: r for r in p['retained_sources']}
    lines = ['| Retained file | SHA-256 | Source |', '|---|---|---|']
    for name in names:
        r = by_file[name]
        lines.append(f"| `{r['file']}` | `{r['sha256'][:12]}…` | {r['url']}"
                     + (f" (lines {r['lines'][0]}-{r['lines'][1]})" if r.get('lines') else '') + ' |')
    return lines


def wheel_section(w, p):
    c, loc = w['component'], w['licence_text_location']
    lines = [f"## {w['distribution']} {w['version']}", '',
             f"- Wheel: `{w['wheel']['artifact']}` (sha256 `{w['wheel']['sha256']}`), opened after hash verification "
             'against the approved manifest.',
             f"- Declared: {'; '.join(w['wheel']['declared'])}",
             f"- Detected in the wheel's licence documents (inventory): {w['wheel']['inventory']['detected_families']}",
             f"- Extra declared licence: {w['extra_declared_licence']}",
             f"- **Classification: {w['classification']}**", '', '### Licence documents in the wheel', '']
    lines += table_of_documents(w) + ['', '### Files searched', ''] + searched(w)
    if w['distribution'] == 'ninja':
        u, b = w['upstream'], w['binary_evidence']
        lines.append(f"- Upstream: the ninja-python-distributions tag 1.13.0 pins the ninja-upstream submodule at "
                     f"Kitware/ninja `{u['commit']}` (API lookup this run: {u['commit_from_api_this_run']}; matches the "
                     f"recorded commit: {u['commit_matches_recorded']}; the wheel README's "
                     f"`{b['version_named_in_wheel_readme']}` abbreviates it: {u['readme_short_hash_matches']}). Its "
                     f"src/version.cc contains the binary's version string: "
                     f"{u.get('version_file_contains_binary_version')}. Files fetched at that commit, and whether "
                     'they match the sdist:')
        for path, f in u['files'].items():
            lines.append(f"  - `{path}`: identical to sdist {f['identical_to_sdist']}; retained `{f['retained']}`"
                         + (f" (error {f['error']})" if f['error'] else ''))
        h = w['classifier_history']
        lines.append(f"- Classifier history: ninja {h['version']} declared {h['licence_classifiers']} (retained "
                     f"`{h['retained']}`).")
    lines += ['', '### Component carrying the extra licence', '', f"**{c['name']}**, licence {c['licence']}.", '']
    if w['distribution'] == 'ninja':
        b = w['binary_evidence']
        lines += [f"- Linux sources of the binary that include rapidhash.h (via hash_map.h): "
                  f"{', '.join(c['linux_sources_including_it'])}.",
                  f"- Sources calling rapidhash(): {', '.join(c['sources_calling_rapidhash'])}.",
                  f"- Ships in the wheel: {c['ships_in_wheel']}: compiled into `{b['path']}` (sha256 `{b['sha256']}`). "
                  f"The binary embeds the sdist's kNinjaVersion `{b['sdist_kNinjaVersion']}`: "
                  f"{b['kNinjaVersion_embedded_in_binary']}. rapidhash's secret constants occur "
                  + ', '.join(f'{k} ×{v}' for k, v in b['rapidhash_secret_occurrences'].items())
                  + f". The constants are also in the emhash header: {b['rapidhash_secrets_also_in_emhash_header']}, "
                  f"but only under EMH_WYHASH_HASH, which no other file mentions "
                  f"({b['files_mentioning_EMH_WYHASH_HASH_outside_emhash'] or 'none'}).",
                  f"- The bundled LICENSE_Apache_20 is byte-identical to ninja's COPYING: "
                  f"{w['wheel_apache_text_identical_to_ninja_COPYING']}."]
    else:
        for f in c['files_in_wheel']:
            lines.append(f"- Ships in the wheel: `{f['path']}` (sha256 `{f['sha256']}`)"
                         + (f"; embeds \"{f['embedded_string']}\" from src/_regex.c: "
                            f"{f['string_from_src__regex_c_present']}" if 'embedded_string' in f else ''))
        if w['distribution'] == 'regex':
            lines += [f"- The compiled module is built from {', '.join(c['compiled_from'])} (setup.py).",
                      f"- Wheel files identical to the sdist: {fmt_matches(c['wheel_matches_sdist'])}.",
                      f"- CPython 3.1 Modules/_sre.c carries the same statement: "
                      f"{c['cpython_3_1_sre_header_carries_same_statement']}."]
        else:
            u = c['upstream_release']
            lines += [f"- Imported by: {', '.join(c['imported_by']) or 'none'}. NOTICE points to it: "
                      f"{c['notice_points_to_it']}. Wheel files identical to the sdist: "
                      f"{fmt_matches(c['wheel_matches_sdist'])}.",
                      f"- Upstream decorator release `{u['sdist']}` (sha256 `{u['sha256']}`, verified against PyPI): "
                      f"vendored file identical to upstream src/decorator.py: "
                      f"{u['vendored_file_identical_to_upstream']}."]
    lines += ['', '### Licence text location', '', f"- In the wheel: {loc['in_wheel']}",
              f"- In the sdist: {loc['in_sdist']}"]
    if w['distribution'] == 'regex':
        up = loc['upstream']
        lines.append('- Upstream: SPDX license-list-data v3.27.0 `text/CNRI-Python.txt`. CPython '
                     + '; '.join(f"{tag} (tag carries the version: {v['tag_carries_version']}; contains the CNRI 1.6.1 "
                                 f"agreement: {v['cnri_1_6_1_agreement_present']})" for tag, v in up['cpython'].items())
                     + '.')
        if loc['spdx_clause_2']:
            lines.append(f"- SPDX CNRI-Python clause 2 (excerpt): \"{loc['spdx_clause_2']}\"")
    else:
        lines.append(f"- Upstream: {loc['upstream']}")
    names = loc['retained'] + [r['file'] for r in p['retained_sources']
                               if r['file'].startswith(f"sources/metadata-{w['distribution']}-")
                               and r['file'] not in loc['retained']]
    lines += [''] + retained_table(names, p)
    lines += ['', '### Proposed obligation', '', w['proposed_obligation'], '', '### Uncertainty', '']
    lines += [f'- {u}' for u in w['uncertainty']]
    if w['other_observations']:
        lines += ['', '### Other observations', '']
        for o in w['other_observations']:
            lines.append('- ' + ' — '.join(str(o[k]) for k in ('component', 'licence', 'note') if k in o))
    return lines


def markdown(p):
    lines = ['# Declared-licence discrepancies: ninja, regex, prometheus_client', '',
             '**Evidence for the designated reviewer: a proposal, not a decision, and not legal clearance.**', '',
             'Each of these wheels declares in its metadata a licence that the inventory did not find in the wheel\'s '
             'bundled licence documents. For each one this pack checks the hash-verified local wheel, the '
             'hash-verified PyPI sdist of the exact version and, where useful, upstream files at a verified commit or '
             'tag. It then names the component that carries the extra licence, says whether that component ships in '
             'the wheel and where its licence text is, and proposes an obligation. Classification: `explained` '
             '(component identified, ships in the wheel, licence text located), `partially_explained`, or '
             '`unexplained`. Retained sources are under `reports/wheelhouse_evidence/sources/` with URL, date and '
             'SHA-256.', '',
             '| Wheel | Declared | Detected in wheel documents | Component carrying the extra licence | Ships in wheel '
             '| Licence text | Classification |', '|---|---|---|---|---|---|---|']
    for w in p['wheels']:
        c = w['component']
        lines.append(f"| {w['distribution']} {w['version']} | {w['wheel']['inventory']['metadata_declared']} | "
                     f"{w['wheel']['inventory']['detected_families']} | {c['name']} | {c['ships_in_wheel']} | "
                     f"{'; '.join(f'`{r}`' for r in w['licence_text_location']['retained'][:1])} | "
                     f"**{w['classification']}** |")
    for w in p['wheels']:
        lines += [''] + wheel_section(w, p)
    if p['fetch_failures']:
        lines += ['', '## Fetch failures (recorded; not evidence of absence)', '']
        lines += [f"- {f['url']}: {f['error']}" for f in p['fetch_failures']]
    return '\n'.join(lines)


if __name__ == '__main__':
    payload = build()
    write_pack('metadata_discrepancies', payload, markdown(payload))
    print(json.dumps({w['distribution']: w['classification'] for w in payload['wheels']}, indent=1))
    print(json.dumps({'retained': len(payload['retained_sources']), 'fetch_failures': payload['fetch_failures']},
                     indent=1))
