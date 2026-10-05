"""Bundled native libraries: provenance evidence pack (a proposal for the designated reviewer).

  python scripts/evidence_native.py

Traces the third-party shared libraries that auditwheel grafted into <dist>.libs/ of three R2 wheels
(opencv_python_headless 4.13.0.92, pillow 12.2.0, pyzmq 27.1.0) back to their builds:

  wheel -> build commit: PyPI Integrity API attestation for the exact file (Fulcio certificate claims), else the
           release tag resolved through the GitHub API (inferred, not attested)
        -> the build file at that commit that pins the library version (path, line, value)
        -> the source archive URL / checksum the build names, its configure flags and any patches
        -> clue-level corroboration from the LOCAL wheel's binaries: embedded version or configure strings, file-name
           interface numbers checked against upstream libtool version-info at the pinned tag, EL8 package build ids
           from .gnu_debuglink

and classifies each chain as complete / partial / clue_only, naming the missing links. File names and SONAMEs are
clues only. Every fetched file is retained under reports/wheelhouse_evidence/sources/native-*. The licence column
states the licence as built and what corresponding source a redistributor would need: evidence for the designated
reviewer, not a licence decision or legal clearance. Writes reports/wheelhouse_evidence/native_libraries.{json,md}.
"""
import base64
import json
import re
import shlex
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evidence_common import (SOURCES, artifact_for, fetch_retained, open_wheel,  # noqa: E402
                                     sha256_bytes, try_fetch_retained, write_pack)

RAW = 'https://raw.githubusercontent.com/{repo}/{ref}/{path}'
API = 'https://api.github.com/repos/{repo}/{endpoint}'
INTEGRITY = 'https://pypi.org/integrity/{project}/{version}/{filename}/provenance'
STATUSES = ('complete', 'partial', 'clue_only')
STATUS_RULES = {
    'complete': 'build commit attested or tag-resolved -> explicit version pin in a build file at that commit -> '
                'source URL named by that build WITH a pinned checksum (so the exact source bytes are established) -> '
                'built in the same CI run -> binary corroboration (embedded version string, libtool mapping at the '
                'pinned upstream tag, or EL8 package build id)',
    'partial': 'some links established; the missing links are listed on the row',
    'clue_only': 'no build file names the library or pins its version; its version rests on binary / file-name '
                 'clues'}
CORROBORATING = ('embedded_version', 'libtool_mapping', 'package_build_id')
FULCIO = {'9': 'build_signer_uri', '10': 'build_signer_digest', '11': 'runner_environment',
          '12': 'source_repository_uri', '13': 'source_repository_digest', '14': 'source_repository_ref',
          '18': 'build_config_uri', '19': 'build_config_digest', '20': 'build_trigger', '21': 'run_invocation_uri',
          '22': 'source_repository_visibility'}
HASH_WORDS = re.compile(r'(?i)sha(?:1|256|512)sum|sha256|sha512|md5|checksum|URL_HASH|--hash')
DEBUGLINK = re.compile(r'^(?P<file>.+?\.so(?:\.[0-9][0-9.]*[a-z]?)?)-(?P<version>[^-]+)-(?P<release>[^-]+)'
                       r'\.(?P<arch>x86_64|i686|aarch64|noarch)\.debug$')
FFMPEG_IDENT = re.compile(rb'(?:Lav[cfu]|SwR|SwS)\d+\.\d+\.\d+')


# ---------------------------------------------------------------- pure helpers (unit-tested offline)

def libtool_suffix(version_info):
    """The Linux file-name suffix libtool derives from -version-info current:revision:age: (current-age).age.revision."""
    current, revision, age = (int(x) for x in version_info.split(':'))
    return f'{current - age}.{age}.{revision}'


def so_suffix(filename):
    """Interface numbers after '.so.' in a bundled file name (a clue, not a release version); None if absent."""
    match = re.search(r'\.so\.([0-9][0-9.]*[0-9a-z]?)$', filename)
    return match.group(1) if match else None


def pin_line(text, pattern, flags=re.M):
    """First match of `pattern` as {line, text, value}; value is group 1 (or the groups joined by ':') if any."""
    match = re.search(pattern, text, flags)
    if not match:
        return None
    line = text.count('\n', 0, match.start()) + 1
    groups = match.groups()
    value = None if not groups else groups[0] if len(groups) == 1 else ':'.join(groups)
    if value is not None:
        value = value.rstrip(' \\')
    return {'line': line, 'text': text.splitlines()[line - 1].strip()[:400], 'value': value}


def expand(template, variables):
    """Substitute ${VAR} and $VAR shell references from `variables` (unknown references are left as they are)."""
    return re.sub(r'\$\{(\w+)\}|\$(\w+)', lambda m: variables.get(m.group(1) or m.group(2), m.group(0)), template)


def checksum_lines(text):
    """Every line of a build file that mentions a checksum/hash mechanism ([] = the file pins no checksum)."""
    return [{'line': n, 'text': line.strip()[:200]} for n, line in enumerate(text.splitlines(), 1)
            if HASH_WORDS.search(line)]


def rpm_build(debuglink):
    """(original file, version-release) from an EL-style .gnu_debuglink name; None if it does not look like one."""
    match = DEBUGLINK.match(debuglink or '')
    return (match.group('file'), f"{match.group('version')}-{match.group('release')}") if match else None


def ffmpeg_licence(flags):
    """The licence label FFmpeg's configure assigns (n8.0.1 logic, quoted in the pack) for a set of configure flags."""
    def on(name):
        return f'--enable-{name}' in flags
    if on('nonfree'):
        return 'nonfree and unredistributable'
    if on('version3'):
        return 'GPL version 3 or later' if on('gpl') else 'LGPL version 3 or later'
    return 'GPL version 2 or later' if on('gpl') else 'LGPL version 2.1 or later'


def chain_status(commit, pin, source, environment, corroboration):
    """(status, missing links) for one library.

    complete:  build commit attested or tag-resolved -> explicit version pin in a build file at that commit -> source
               URL named by that build with a pinned checksum -> built in the same CI run -> binary corroboration;
               a named URL without a checksum is a plausible release, not established source, so it stays partial;
    clue_only: no build file names the library (its version rests on binary / file-name clues);
    partial:   anything in between; the missing links are listed."""
    missing = []
    if commit not in ('attested', 'tag_resolved'):
        missing.append('build commit not established')
    if pin in (None, 'package_transitive'):
        return 'clue_only', missing + ['no build file names this library or pins its version']
    if pin == 'package_named':
        missing.append('installed from distribution packages without a version pin')
    if source == 'upstream_url':
        missing.append('source archive named by URL but no checksum pinned: the exact source bytes are not '
                       'established')
    elif source != 'upstream_url_with_checksum':
        missing.append({'unpinned_mirror': 'source archive comes from an unpinned branch (identified only by inference)',
                        'distro_srpm': 'corresponding source is a distribution source package (not fetched or verified)'
                        }.get(source, 'no source location named'))
    if environment != 'same_run':
        missing.append('built inside a separately published container image (image not verified against the '
                       'Dockerfile at the commit)')
    if corroboration not in CORROBORATING:
        missing.append('no binary corroboration of the pinned version (file name only)')
    return ('complete' if not missing else 'partial'), missing


def der_header(data, i):
    tag, length, i = data[i], data[i + 1], i + 2
    if length & 0x80:
        count = length & 0x7F
        length, i = int.from_bytes(data[i:i + count], 'big'), i + count
    return tag, i, length


def oid_text(raw):
    parts, value = [raw[0] // 40, raw[0] % 40], 0
    for byte in raw[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(value)
            value = 0
    return '.'.join(map(str, parts))


def der_extensions(data, prefix='1.3.6.1.4.1.57264.1.'):
    """{oid: text} of X.509 extensions under `prefix` (Fulcio's CI claims). DER UTF8String values are unwrapped;
    legacy raw values are decoded as they are. No signature or chain verification is done here."""
    out = {}

    def walk(start, end):
        i = start
        while i < end:
            tag, body, length = der_header(data, i)
            if tag & 0x20:
                if tag == 0x30 and body < body + length:
                    t, j, n = der_header(data, body)
                    if t == 0x06 and j + n < body + length:
                        oid = oid_text(data[j:j + n])
                        t, k, m = der_header(data, j + n)
                        if t == 0x01 and k + m < body + length:
                            t, k, m = der_header(data, k + m)
                        if t == 0x04 and oid.startswith(prefix):
                            value = data[k:k + m]
                            if value[:1] == b'\x0c':
                                _, v, vn = der_header(value, 0)
                                value = value[v:v + vn]
                            out[oid] = value.decode('utf-8', 'replace')
                walk(body, body + length)
            i = body + length

    walk(0, len(data))
    return out


def cstr(data, offset):
    return data[offset:data.index(b'\0', offset)].decode('utf-8', 'replace')


def elf_dynamic(data):
    """SONAME, DT_NEEDED, .comment and .gnu_debuglink of an ELF64 little-endian object; None if not one."""
    if data[:4] != b'\x7fELF' or data[4] != 2 or data[5] != 1:
        return None
    shoff, = struct.unpack_from('<Q', data, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', data, 0x3A)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, shoff + k * shentsize) for k in range(shnum)]
    names = headers[shstrndx][4]
    sections = {cstr(data, names + h[0]): (h[4], h[5]) for h in headers}
    out = {'soname': None, 'needed': [], 'compiler_comment': [], 'debuglink': None}
    if '.dynamic' in sections and '.dynstr' in sections:
        (dyn, size), (strtab, _) = sections['.dynamic'], sections['.dynstr']
        for k in range(size // 16):
            tag, value = struct.unpack_from('<qQ', data, dyn + 16 * k)
            if tag == 0:
                break
            if tag == 1:
                out['needed'].append(cstr(data, strtab + value))
            elif tag == 14:
                out['soname'] = cstr(data, strtab + value)
    if '.comment' in sections:
        off, size = sections['.comment']
        out['compiler_comment'] = sorted({x.decode('utf-8', 'replace') for x in data[off:off + size].split(b'\0') if x})
    if '.gnu_debuglink' in sections:
        out['debuglink'] = cstr(data, sections['.gnu_debuglink'][0])
    return out


def version_patterns(templates, value):
    """Byte regexes for an expected embedded version: {v} = pinned value, {vn} = without a leading 'v'."""
    v = value or ''
    return [t.replace('{v}', re.escape(v)).replace('{vn}', re.escape(v.lstrip('v'))).encode() for t in templates]


def shell_list(text, name):
    """Members of a configure-style NAME=\"...\" multi-line list."""
    match = re.search(rf'^{name}="\n(.*?)\n"', text, re.M | re.S)
    return match.group(1).split() if match else None


# ---------------------------------------------------------------- retrieval

def api_json(name, url):
    """GitHub API JSON, retained. If the API refuses (e.g. rate limit) an earlier retained copy is reused and flagged."""
    data, record = try_fetch_retained(name, url, 8 * 1024 ** 2)
    if data is None:
        path = SOURCES / name
        if not path.exists():
            raise SystemExit(f"{url}: {record['error']} and no retained copy")
        data = path.read_bytes()
        record = dict(record, file=f'sources/{name}', sha256=sha256_bytes(data), bytes=len(data), kind='raw',
                      reused_retained_copy=True)
    return json.loads(data), record


def build_commit(wheel, artifact):
    """Attestation (if PyPI has one for the exact file) and the release tag resolved to a commit."""
    project, version, repo, tag = wheel['project'], wheel['version'], wheel['repo'], wheel['tag']
    prefix = f"native-{wheel['distribution']}"
    release, release_record = fetch_retained(f'{prefix}-pypi-release.json',
                                             f'https://pypi.org/pypi/{project}/{version}/json', 8 * 1024 ** 2)
    entry = next(u for u in json.loads(release)['urls'] if u['filename'] == artifact['filename'])
    pypi = {'record': release_record, 'upload_time': entry['upload_time_iso_8601'],
            'sha256_matches_manifest': entry['digests']['sha256'] == artifact['sha256']}
    data, record = try_fetch_retained(f'{prefix}-provenance.json', INTEGRITY.format(
        project=project, version=version, filename=artifact['filename']), 8 * 1024 ** 2)
    attestation = {'record': record, 'available': data is not None}
    if data is not None:
        bundle = json.loads(data)['attestation_bundles'][0]
        att = bundle['attestations'][0]
        statement = json.loads(base64.b64decode(att['envelope']['statement']))
        claims = der_extensions(base64.b64decode(att['verification_material']['certificate']))
        attestation.update(
            publisher=bundle['publisher'], predicate_type=statement['predicateType'],
            subject=statement['subject'],
            subject_matches_wheel=any(s['name'] == artifact['filename'] and s['digest'].get('sha256') ==
                                      artifact['sha256'] for s in statement['subject']),
            certificate_claims={FULCIO.get(oid.rsplit('.', 1)[1], oid): v for oid, v in sorted(claims.items())
                                if oid.rsplit('.', 1)[1] in FULCIO},
            transparency_log_index=att['verification_material']['transparency_entries'][0].get('logIndex'),
            verification_note=('Claims read from the Fulcio certificate PyPI returned; the Sigstore signature, '
                               'certificate chain and transparency-log inclusion were not re-verified here '
                               '(PyPI verifies attestations at upload under PEP 740).'))
    tag_json, tag_record = api_json(f'{prefix}-tag-{tag}-commit.json',
                                    API.format(repo=repo, endpoint=f'commits/{tag}'))
    tag_info = {'tag': tag, 'commit': tag_json['sha'], 'commit_date': tag_json['commit']['committer']['date'],
                'message_first_line': tag_json['commit']['message'].splitlines()[0], 'record': tag_record}
    claimed = attestation.get('certificate_claims', {})
    if attestation['available'] and attestation['subject_matches_wheel']:
        commit, status = claimed['source_repository_digest'], 'attested'
    else:
        commit, status = tag_info['commit'], 'tag_resolved'
    return {'status': status, 'commit': commit, 'repository': f'https://github.com/{repo}',
            'workflow': claimed.get('build_config_uri') or wheel.get('workflow'),
            'run': claimed.get('run_invocation_uri'), 'attestation': attestation, 'release_tag': tag_info,
            'tag_agrees_with_attestation': (tag_info['commit'] == claimed.get('source_repository_digest')
                                            if attestation['available'] else None),
            'pypi': pypi}


def retain_files(distribution, specs, commit):
    """{key: {'text', 'record'}} for build files, fetched at the build commit (or the ref given) and retained."""
    out = {}
    for key, spec in specs.items():
        repo, path, ref = spec['repo'], spec['path'], spec.get('ref') or commit
        data, record = fetch_retained(f'native-{distribution}-{key}', RAW.format(repo=repo, ref=ref, path=path))
        out[key] = {'text': data.decode('utf-8', 'replace'),
                    'record': dict(record, repository=repo, path=path, ref=ref)}
    return out


# ---------------------------------------------------------------- wheel / binary inspection

def wheel_listing(artifact):
    """Bundled shared libraries (<dist>.libs/*), the wheel's own extension modules and its licence texts."""
    z = open_wheel(artifact)
    libs, extensions, notices = {}, {}, {}
    for info in z.infolist():
        name = info.filename
        if name.endswith('/'):
            continue
        if '.libs/' in name:
            libs[name] = z.read(info)
        elif name.endswith('.so') and '.dist-info/' not in name:
            extensions[name] = z.read(info)
        elif re.search(r'(?i)licen[cs]e', name.rsplit('/', 1)[-1]) and name.endswith(('.txt', '.md', 'LICENSE')):
            notices[name] = z.read(info).decode('utf-8', 'replace')
    return libs, extensions, notices


def file_record(path, data):
    elf = elf_dynamic(data) or {}
    return {'path': path, 'bytes': len(data), 'sha256': sha256_bytes(data), 'soname': elf.get('soname'),
            'needed': elf.get('needed', []), 'compiler_comment': elf.get('compiler_comment', []),
            'debuglink': elf.get('debuglink'), 'debuglink_package_build': rpm_build(elf.get('debuglink')),
            'file_name_interface_numbers': so_suffix(path)}


def opencv_build_information(data):
    """Selected lines of the OpenCV build-information block embedded in cv2.abi3.so (clue-level)."""
    start = data.find(b'General configuration for OpenCV')
    block = data[start:data.index(b'\0', start)].decode('utf-8', 'replace')
    keys = ('General configuration', 'Version control', 'Timestamp', 'Extra dependencies', '3rdparty dependencies',
            'ZLib', 'JPEG:', 'WEBP', 'AVIF', 'PNG', 'TIFF', 'JPEG 2000', 'OpenEXR', 'FFMPEG', 'avcodec', 'avformat',
            'avutil', 'swscale', 'Trace', 'Intel IPP', 'Lapack', 'Protobuf', 'Flatbuffers', 'Non-free algorithms')
    return [line.strip() for line in block.splitlines() if line.strip().startswith(keys)]


# ---------------------------------------------------------------- specifications per wheel

WHEELS = [
    {'distribution': 'opencv_python_headless', 'project': 'opencv-python-headless', 'version': '4.13.0.92',
     'repo': 'opencv/opencv-python', 'tag': '92',
     'workflow': 'https://github.com/opencv/opencv-python/.github/workflows/build_wheels_manylinux.yml (inferred)',
     'files': {'dockerfile': {'repo': 'opencv/opencv-python', 'path': 'docker/manylinux_2_28/Dockerfile_x86_64'},
               'workflow': {'repo': 'opencv/opencv-python', 'path': '.github/workflows/build_wheels_manylinux.yml'},
               'setup.py': {'repo': 'opencv/opencv-python', 'path': 'setup.py'},
               'ffmpeg-n8.0.1-configure': {'repo': 'FFmpeg/FFmpeg', 'path': 'configure', 'ref': 'n8.0.1'},
               'ffmpeg-n8.0.1-LICENSE.md': {'repo': 'FFmpeg/FFmpeg', 'path': 'LICENSE.md', 'ref': 'n8.0.1'},
               'libavif-v1.3.0-LocalLibyuv.cmake': {'repo': 'AOMediaCodec/libavif', 'ref': 'v1.3.0',
                                                    'path': 'cmake/Modules/LocalLibyuv.cmake'}},
     'environment': 'prebuilt_image'},
    {'distribution': 'pillow', 'project': 'pillow', 'version': '12.2.0', 'repo': 'python-pillow/Pillow',
     'tag': '12.2.0',
     'files': {'wheels-dependencies.sh': {'repo': 'python-pillow/Pillow', 'path': '.github/workflows/wheels-dependencies.sh'},
               'wheels.yml': {'repo': 'python-pillow/Pillow', 'path': '.github/workflows/wheels.yml'},
               'pyproject.toml': {'repo': 'python-pillow/Pillow', 'path': 'pyproject.toml'},
               'setup.py': {'repo': 'python-pillow/Pillow', 'path': 'setup.py'},
               'requirements-cibw.txt': {'repo': 'python-pillow/Pillow', 'path': '.ci/requirements-cibw.txt'},
               'freetype-VER-2-14-3-configure.raw': {'repo': 'freetype/freetype', 'ref': 'VER-2-14-3',
                                                     'path': 'builds/unix/configure.raw'},
               'libwebp-v1.6.0-src-Makefile.am': {'repo': 'webmproject/libwebp', 'ref': 'v1.6.0', 'path': 'src/Makefile.am'},
               'libwebp-v1.6.0-mux-Makefile.am': {'repo': 'webmproject/libwebp', 'ref': 'v1.6.0', 'path': 'src/mux/Makefile.am'},
               'libwebp-v1.6.0-demux-Makefile.am': {'repo': 'webmproject/libwebp', 'ref': 'v1.6.0',
                                                    'path': 'src/demux/Makefile.am'},
               'libwebp-v1.6.0-sharpyuv-Makefile.am': {'repo': 'webmproject/libwebp', 'ref': 'v1.6.0',
                                                       'path': 'sharpyuv/Makefile.am'},
               'lcms2-2.18-configure.ac': {'repo': 'mm2/Little-CMS', 'ref': 'lcms2.18', 'path': 'configure.ac'},
               'libavif-v1.4.1-LocalAom.cmake': {'repo': 'AOMediaCodec/libavif', 'ref': 'v1.4.1',
                                                 'path': 'cmake/Modules/LocalAom.cmake'},
               'libavif-v1.4.1-LocalDav1d.cmake': {'repo': 'AOMediaCodec/libavif', 'ref': 'v1.4.1',
                                                   'path': 'cmake/Modules/LocalDav1d.cmake'},
               'libavif-v1.4.1-LocalLibyuv.cmake': {'repo': 'AOMediaCodec/libavif', 'ref': 'v1.4.1',
                                                    'path': 'cmake/Modules/LocalLibyuv.cmake'},
               'libavif-v1.4.1-LocalLibsharpyuv.cmake': {'repo': 'AOMediaCodec/libavif', 'ref': 'v1.4.1',
                                                         'path': 'cmake/Modules/LocalLibsharpyuv.cmake'}},
     'submodule_files': {'multibuild-library_builders.sh': 'library_builders.sh',
                         'multibuild-common_utils.sh': 'common_utils.sh'},
     'environment': 'same_run'},
    {'distribution': 'pyzmq', 'project': 'pyzmq', 'version': '27.1.0', 'repo': 'zeromq/pyzmq', 'tag': 'v27.1.0',
     'files': {'bundle.py': {'repo': 'zeromq/pyzmq', 'path': 'buildutils/bundle.py'},
               'install_libzmq.sh': {'repo': 'zeromq/pyzmq', 'path': 'tools/install_libzmq.sh'},
               'pyproject.toml': {'repo': 'zeromq/pyzmq', 'path': 'pyproject.toml'},
               'CMakeLists.txt': {'repo': 'zeromq/pyzmq', 'path': 'CMakeLists.txt'},
               'wheels.yml': {'repo': 'zeromq/pyzmq', 'path': '.github/workflows/wheels.yml'},
               'wheel-requirements.txt': {'repo': 'zeromq/pyzmq', 'path': 'tools/wheel-requirements.txt'},
               'libzmq-v4.3.5-configure.ac': {'repo': 'zeromq/libzmq', 'ref': 'v4.3.5', 'path': 'configure.ac'},
               'libzmq-v4.3.5-LICENSE': {'repo': 'zeromq/libzmq', 'ref': 'v4.3.5', 'path': 'LICENSE'},
               'libsodium-1.0.20-RELEASE-LICENSE': {'repo': 'jedisct1/libsodium', 'ref': '1.0.20-RELEASE',
                                                    'path': 'LICENSE'}},
     'environment': 'same_run'},
]

NO_CHECKSUM = 'the build pins no checksum for this source'
COPYLEFT_AS_BUILT = {'ffmpeg': 'LGPL-2.1-or-later', 'libquadmath': 'LGPL-2.1-or-later',
                     'libgfortran': 'GPL-3.0-or-later WITH GCC-exception-3.1', 'libzmq': 'MPL-2.0'}
DUAL_WITH_GPL_OPTION = {'freetype': 'FTL OR GPL-2.0-or-later', 'zstd': 'BSD-3-Clause OR GPL-2.0-only'}
MB_CONFIGURE = ('multibuild-library_builders.sh',  # build_simple's configure line (no library-specific flags)
                r'^\s*&& (\./configure --prefix=\$BUILD_PREFIX \$HOST_CONFIGURE_FLAGS \$configure_args)')
MB_OPENJPEG = ('multibuild-library_builders.sh', r'(\$cmake -DCMAKE_INSTALL_PREFIX=\$BUILD_PREFIX -DCMAKE_INSTALL_LIBDIR='
                                                 r'\$BUILD_PREFIX/lib -DCMAKE_INSTALL_NAME_DIR=\$BUILD_PREFIX/lib '
                                                 r'\$HOST_CMAKE_FLAGS \.)')

COMPONENTS = {
    'opencv_python_headless': [
        {'name': 'FFmpeg (libavcodec, libavformat, libavutil, libswresample, libswscale)', 'key': 'ffmpeg',
         'files': [r'libavcodec-', r'libavformat-', r'libavutil-', r'libswresample-', r'libswscale-'],
         'pin': ('dockerfile', r'^ARG FFMPEG_VERSION=(\S+)'),
         'source': ('dockerfile', r'curl -O -L (https://ffmpeg\.org/releases/ffmpeg-\$\{FFMPEG_VERSION\}\.tar\.gz)',
                    {'FFMPEG_VERSION': 'pin'}),
         'flags': [('dockerfile', r'PKG_CONFIG_PATH="/ffmpeg_build/lib/pkgconfig" \./configure (--prefix=.*?) &&')],
         'expect': [r'\x00{vn}\x00'],
         'licence': 'LGPL-2.1-or-later, as FFmpeg\'s configure labels this build (see the FFmpeg licence logic '
                    'section). Linked at run time against bundled OpenSSL 1.1.1k (libavformat, libavutil), libvpx '
                    '(libavcodec), libdrm (libavutil) and the system zlib. FFmpeg LICENSE.md also notes three '
                    'libavcodec files under libjpeg (IJG) terms.',
         'provide': 'Corresponding source for the LGPL libraries: ffmpeg-8.0.1.tar.gz from the URL shown (no checksum '
                    'pinned; the reviewer may wish to record FFmpeg\'s published signature), the configure command and '
                    'the Dockerfile; the LGPL-2.1 text (present in the wheel\'s LICENSE-3RD-PARTY.txt); terms that '
                    'allow replacing the shared libraries (auditwheel renamed them with hash suffixes).',
         'notice': r'FFmpeg is redistributed',
         'uncertainty': ['libraries built in the prebuilt image, not in the wheel run',
                         'FFmpeg\'s statement that OpenSSL is LGPL-compatible is FFmpeg\'s assessment ("to the best of '
                         'our knowledge"), not a legal conclusion']},
        {'name': 'libvpx', 'key': 'libvpx', 'files': [r'libvpx-'],
         'pin': ('dockerfile', r'^ARG VPX_VERSION=(\S+)'),
         'source': ('dockerfile', r'git clone --depth 1 -b \$\{VPX_VERSION\} (https://chromium\.googlesource\.com/webm/libvpx\.git)',
                    {}),
         'source_kind': 'git tag (no commit hash pinned)',
         'flags': [('dockerfile', r'\./configure (--prefix="/ffmpeg_build" --disable-examples.*?) &&')],
         'expect': [r'\x00{v}\x00'], 'embedded_configure': rb'--prefix=/ffmpeg_build --disable-examples[^\x00]*',
         'licence': 'BSD-3-Clause, with the WebM additional IP rights grant (PATENTS).',
         'provide': 'BSD notice and PATENTS text (the wheel\'s LICENSE-3RD-PARTY.txt has a libvpx section); source '
                    'not required by the licence.',
         'notice': r'libvpx is redistributed',
         'uncertainty': ['git tag, not a commit hash, is pinned', 'built in the prebuilt image']},
        {'name': 'libaom', 'key': 'libaom', 'files': [r'libaom-'],
         'pin': ('dockerfile', r'^ARG AOM_VERSION=(\S+)'),
         'source': ('dockerfile', r'git clone --depth 1 -b \$\{AOM_VERSION\} (https://aomedia\.googlesource\.com/aom)', {}),
         'source_kind': 'git tag (no commit hash pinned)',
         'flags': [('dockerfile', r'(cmake -DCMAKE_C_COMPILER=.*\.\./aom/)')],
         'expect': [r'\x00{vn}\x00'],
         'licence': 'BSD-2-Clause, with the Alliance for Open Media Patent License 1.0.',
         'provide': 'BSD notice and AOM patent licence text; source not required by the licence.',
         'notice': r'aom library and it',
         'uncertainty': ['git tag, not a commit hash, is pinned', 'built in the prebuilt image']},
        {'name': 'libavif', 'key': 'libavif', 'files': [r'libavif-'],
         'pin': ('dockerfile', r'^ARG AVIF_VERSION=(\S+)'),
         'source': ('dockerfile', r'git clone -b \$\{AVIF_VERSION\} (https://github\.com/AOMediaCodec/libavif\.git)', {}),
         'source_kind': 'git tag (no commit hash pinned)',
         'flags': [('dockerfile', r'(cmake -DCMAKE_INSTALL_PREFIX=/usr -DAVIF_CODEC_AOM=SYSTEM.*\.\./libavif)')],
         'expect': [r'\x00{vn}\x00'],
         'subcomponents': [{'name': 'libyuv (AVIF_LIBYUV=LOCAL, statically linked)',
                            'pin': ('libavif-v1.3.0-LocalLibyuv.cmake', r'set\(AVIF_LIBYUV_TAG "([0-9a-f]+)"\)'),
                            'licence': 'BSD-3-Clause', 'source': 'https://chromium.googlesource.com/libyuv/libyuv '
                            '(commit pinned by libavif v1.3.0)'}],
         'licence': 'BSD-2-Clause (libavif); statically includes libyuv (BSD-3-Clause); uses the bundled libaom.',
         'provide': 'BSD notices for libavif and libyuv; source not required by these licences.',
         'notice': r'libavif library and it',
         'uncertainty': ['git tag, not a commit hash, is pinned', 'built in the prebuilt image',
                         'libyuv revision taken from libavif\'s own pin at the tag (not verified in the binary)']},
        {'name': 'libpng', 'key': 'libpng', 'files': [r'libpng16-'],
         'pin': ('dockerfile', r'^ARG LIBPNG_VERSION=(\S+)'),
         'source': ('dockerfile', r'curl -O -L (https://download\.sourceforge\.net/libpng/libpng-\$\{LIBPNG_VERSION\}\.tar\.gz)',
                    {'LIBPNG_VERSION': 'pin'}),
         'flags': [('dockerfile', r'(\./configure --prefix=/usr/local) &&')],
         'expect': [r'libpng version {v}'],
         'licence': 'libpng-2.0 (PNG Reference Library License version 2).',
         'provide': 'libpng licence notice (the wheel has a libpng section); source not required.',
         'notice': r'libpng is redistributed',
         'uncertainty': ['built in the prebuilt image']},
        {'name': 'OpenSSL (libcrypto, libssl)', 'key': 'openssl', 'files': [r'libcrypto-', r'libssl-'],
         'package': ('dockerfile', r'^\s*yum install (openblas-devel .*openssl openssl-devel -y)'),
         'origin': 'package_named', 'expect_regex': rb'OpenSSL \d\.\d\.\d+[a-z]?\s+(?:FIPS\s+)?\d{1,2} \w{3} \d{4}',
         'licence': 'OpenSSL License AND SSLeay License (the OpenSSL 1.1.1 dual licence, with advertising-'
                    'acknowledgement clauses). This is the EL8 package build (Red Hat "FIPS" variant per the '
                    'embedded version string), which carries distribution patches.',
         'provide': 'The OpenSSL/SSLeay licence text and required acknowledgements (present in the wheel\'s notice '
                    'file). Source is not required by these licences; if offered, it is the AlmaLinux 8 source '
                    'package of the build shown (not fetched).',
         'notice': r'libcrypto and libssl are redistributed',
         'uncertainty': ['package version not pinned by the build; identified from .gnu_debuglink',
                         'licence compatibility with LGPL FFmpeg rests on FFmpeg\'s own statement']},
        {'name': 'OpenBLAS', 'key': 'openblas', 'files': [r'libopenblasp-'],
         'package': ('dockerfile', r'^\s*yum install (openblas-devel .*-y)'), 'origin': 'package_named',
         'expect_regex': rb'OpenBLAS \d+\.\d+\.\d+[^\x00]*',
         'licence': 'BSD-3-Clause (EL8 package build).',
         'provide': 'BSD notice. No OpenBLAS section was found in the wheel\'s LICENSE-3RD-PARTY.txt.',
         'notice': r'openblas', 'uncertainty': ['package version not pinned; identified from .gnu_debuglink']},
        {'name': 'libgfortran (GCC runtime)', 'key': 'libgfortran', 'files': [r'libgfortran-'],
         'origin': 'package_transitive',
         'licence': 'GPL-3.0-or-later WITH GCC-exception-3.1 (GCC Runtime Library Exception); EL8 gcc package build.',
         'provide': 'Reviewer to judge whether the Runtime Library Exception covers redistributing the runtime '
                    'library file itself or whether GPLv3 source terms apply to it; if source is offered, it is the '
                    'AlmaLinux 8 gcc source package of the build shown (not fetched). No notice section in the '
                    'wheel.',
         'notice': r'gfortran',
         'uncertainty': ['pulled in as a dependency of OpenBLAS; no build file names it',
                         'version known only from .gnu_debuglink and file name']},
        {'name': 'libquadmath (GCC runtime)', 'key': 'libquadmath', 'files': [r'libquadmath-'],
         'origin': 'package_transitive',
         'licence': 'LGPL-2.1-or-later (GCC\'s libquadmath); EL8 gcc package build.',
         'provide': 'Corresponding source for an LGPL library: the AlmaLinux 8 gcc source package of the build shown '
                    '(not fetched), the LGPL-2.1 text, and replaceability terms. No notice section in the wheel.',
         'notice': r'quadmath',
         'uncertainty': ['pulled in as a dependency of libgfortran; no build file names it',
                         'version known only from .gnu_debuglink and file name']},
        {'name': 'libdrm', 'key': 'libdrm', 'files': [r'libdrm-'], 'origin': 'package_transitive',
         'licence': 'MIT (EL8 package build).',
         'provide': 'MIT notice. No libdrm section was found in the wheel\'s LICENSE-3RD-PARTY.txt.',
         'notice': r'libdrm',
         'uncertainty': ['detected by FFmpeg\'s configure (libavutil needs it); no build file names it',
                         'version known only from .gnu_debuglink']},
    ],
    'pillow': [
        {'name': 'FreeType', 'key': 'freetype', 'files': [r'libfreetype-'],
         'pin': ('wheels-dependencies.sh', r'^FREETYPE_VERSION=(\S+)'),
         'source': ('multibuild-library_builders.sh',
                    r'build_simple freetype \$FREETYPE_VERSION (https://download\.savannah\.gnu\.org/releases/freetype)$',
                    {}), 'archive': 'freetype-{v}.tar.gz', 'url_suffix': '/freetype-{v}.tar.gz',
         'flags': [('wheels-dependencies.sh', r'^\s*(build_freetype)$'), MB_CONFIGURE],
         'libtool': ('freetype-VER-2-14-3-configure.raw', r"^version_info='(\d+:\d+:\d+)'", r'libfreetype-'),
         'subcomponents': [{'name': 'bzip2 (appears statically linked: no libbz2 in DT_NEEDED, "1.0.8" string)',
                            'pin': ('wheels-dependencies.sh', r'^BZIP2_VERSION=(\S+)'), 'licence': 'bzip2-1.0.6',
                            'source': 'https://mirrors.kernel.org/sourceware/bzip2/bzip2-1.0.8.tar.gz via multibuild '
                                      'build_bzip2 (archive also in pillow-depends)',
                            'expect': r'\x00{v}, \d{1,2}-\w{3}-\d{4}\x00|/project/build/bzip2-{v}\x00'}],
         'licence': 'FTL OR GPL-2.0-or-later (FreeType dual licence; the redistributor chooses); appears to include '
                    'bzip2 1.0.8 statically (bzip2-1.0.6 licence).',
         'provide': 'Under the FTL: the FTL text and the documentation credit it requires; no source obligation. '
                    'Choosing GPL-2.0 instead would bring source obligations.',
         'notice': r'FREETYPE2', 'uncertainty': []},
        {'name': 'HarfBuzz', 'key': 'harfbuzz', 'files': [r'libharfbuzz-'],
         'pin': ('wheels-dependencies.sh', r'^HARFBUZZ_VERSION=(\S+)'),
         'source': ('wheels-dependencies.sh', r'fetch_unpack (https://github\.com/harfbuzz/harfbuzz/releases/download/'
                    r'\$HARFBUZZ_VERSION/harfbuzz-\$HARFBUZZ_VERSION\.tar\.xz)', {'HARFBUZZ_VERSION': 'pin'}),
         'archive': 'harfbuzz-{v}.tar.xz',
         'flags': [('wheels-dependencies.sh', r'(meson setup build .*?)\$HOST_MESON_FLAGS')],
         'expect': [r'\x00{v}\x00'], 'licence': 'MIT ("Old MIT", HarfBuzz COPYING).',
         'provide': 'MIT notice (present in the wheel LICENSE).', 'notice': r'HARFBUZZ', 'uncertainty': []},
        {'name': 'libjpeg-turbo', 'key': 'libjpeg-turbo', 'files': [r'libjpeg-'],
         'pin': ('wheels-dependencies.sh', r'^JPEGTURBO_VERSION=(\S+)'),
         'source': ('multibuild-library_builders.sh', r'fetch_unpack (https://github\.com/libjpeg-turbo/libjpeg-turbo/'
                    r'releases/download/\$\{JPEGTURBO_VERSION\}/libjpeg-turbo-\$\{JPEGTURBO_VERSION\}\.tar\.gz)',
                    {'JPEGTURBO_VERSION': 'pin'}), 'archive': 'libjpeg-turbo-{v}.tar.gz',
         'flags': [('multibuild-library_builders.sh', r'(\$cmake -G"Unix Makefiles" -DCMAKE_INSTALL_PREFIX=\$BUILD_PREFIX.*)')],
         'expect': [r'libjpeg-turbo version {v} \(build \d+\)'],
         'licence': 'IJG AND BSD-3-Clause AND Zlib (libjpeg-turbo LICENSE.md).',
         'provide': 'Notices, including the IJG documentation credit; source not required.', 'notice': r'LIBJPEG',
         'uncertainty': []},
        {'name': 'Little CMS 2', 'key': 'lcms2', 'files': [r'liblcms2-'],
         'pin': ('wheels-dependencies.sh', r'^LCMS2_VERSION=(\S+)'),
         'source': ('multibuild-library_builders.sh', r'build_simple lcms2 \$LCMS2_VERSION (https://downloads\.sourceforge'
                    r'\.net/project/lcms/lcms/\$LCMS2_VERSION)', {'LCMS2_VERSION': 'pin'}),
         'archive': 'lcms2-{v}.tar.gz', 'url_suffix': '/lcms2-{v}.tar.gz', 'flags': [MB_CONFIGURE],
         'libtool': ('lcms2-2.18-configure.ac', r'^LIBRARY_CURRENT=(\d+)\s+LIBRARY_REVISION=(\d+)\s+LIBRARY_AGE=(\d+)',
                     r'liblcms2-'),
         'licence': 'MIT.', 'provide': 'MIT notice (present).', 'notice': r'LCMS2', 'uncertainty': []},
        {'name': 'xz (liblzma)', 'key': 'xz', 'files': [r'liblzma-'],
         'pin': ('wheels-dependencies.sh', r'^XZ_VERSION=(\S+)'),
         'source': ('multibuild-library_builders.sh', r'build_simple xz \$XZ_VERSION (https://github\.com/tukaani-project'
                    r'/xz/releases/download/v\$XZ_VERSION)', {'XZ_VERSION': 'pin'}),
         'archive': 'xz-{v}.tar.gz', 'url_suffix': '/xz-{v}.tar.gz', 'flags': [MB_CONFIGURE], 'expect': [r'\x00{v}\x00'],
         'licence': '0BSD (liblzma since xz 5.6.0).', 'provide': 'Notice (present as LIBLZMA).',
         'notice': r'LIBLZMA', 'uncertainty': []},
        {'name': 'OpenJPEG', 'key': 'openjpeg', 'files': [r'libopenjp2-'],
         'pin': ('wheels-dependencies.sh', r'^OPENJPEG_VERSION=(\S+)'),
         'source': ('multibuild-library_builders.sh', r'fetch_unpack (https://github\.com/uclouvain/openjpeg/archive/'
                    r'\$\{archive_prefix\}\$\{OPENJPEG_VERSION\}\.tar\.gz)',
                    {'OPENJPEG_VERSION': 'pin', 'archive_prefix': 'v'}), 'archive': 'v{v}.tar.gz', 'flags': [MB_OPENJPEG],
         'expect': [r'\x00{v}\x00'], 'licence': 'BSD-2-Clause.', 'provide': 'BSD notice (present).',
         'notice': r'OPENJPEG', 'uncertainty': []},
        {'name': 'libpng', 'key': 'libpng', 'files': [r'libpng16-'],
         'pin': ('wheels-dependencies.sh', r'^LIBPNG_VERSION=(\S+)'),
         'source': ('multibuild-library_builders.sh', r'build_simple libpng \$LIBPNG_VERSION '
                    r'(https://download\.sourceforge\.net/libpng)$', {}),
         'archive': 'libpng-{v}.tar.gz', 'url_suffix': '/libpng-{v}.tar.gz', 'flags': [MB_CONFIGURE], 'expect': [r'libpng version {v}'],
         'licence': 'libpng-2.0.', 'provide': 'Notice (present).', 'notice': r'LIBPNG', 'uncertainty': []},
        {'name': 'libtiff', 'key': 'libtiff', 'files': [r'libtiff-'],
         'pin': ('wheels-dependencies.sh', r'^TIFF_VERSION=(\S+)'),
         'source': ('multibuild-library_builders.sh', r'build_simple tiff \$TIFF_VERSION (https://download\.osgeo\.org'
                    r'/libtiff)$', {}), 'archive': 'tiff-{v}.tar.gz', 'url_suffix': '/tiff-{v}.tar.gz', 'flags': [MB_CONFIGURE],
         'expect': [r'LIBTIFF, Version {v}'], 'licence': 'libtiff (MIT-style).', 'provide': 'Notice (present).',
         'notice': r'LIBTIFF', 'uncertainty': []},
        {'name': 'Zstandard', 'key': 'zstd', 'files': [r'libzstd-'],
         'pin': ('wheels-dependencies.sh', r'^ZSTD_VERSION=(\S+)'),
         'source': ('wheels-dependencies.sh', r'fetch_unpack (https://github\.com/facebook/zstd/releases/download/'
                    r'v\$ZSTD_VERSION/zstd-\$ZSTD_VERSION\.tar\.gz)', {'ZSTD_VERSION': 'pin'}),
         'archive': 'zstd-{v}.tar.gz', 'expect': [r'\x00{v}\x00'],
         'licence': 'BSD-3-Clause OR GPL-2.0-only (dual; the redistributor chooses).',
         'provide': 'BSD notice under the BSD option (present as ZSTD).', 'notice': r'ZSTD', 'uncertainty': []},
        {'name': 'libwebp', 'key': 'libwebp', 'files': [r'libwebp-'],
         'pin': ('wheels-dependencies.sh', r'^LIBWEBP_VERSION=(\S+)'),
         'source': ('wheels-dependencies.sh', r'^\s*(https://storage\.googleapis\.com/downloads\.webmproject\.org/'
                    r'releases/webp) tar\.gz', {}), 'archive': 'libwebp-{v}.tar.gz', 'url_suffix': '/libwebp-{v}.tar.gz',
         'flags': [('wheels-dependencies.sh', r'^\s*(--enable-libwebpmux --enable-libwebpdemux)'), MB_CONFIGURE],
         'libtool': ('libwebp-v1.6.0-src-Makefile.am', r'libwebp_la_LDFLAGS = .*-version-info (\d+:\d+:\d+)', r'libwebp-'),
         'licence': 'BSD-3-Clause, with the WebM additional IP rights grant.', 'provide': 'Notice (present).',
         'notice': r'LIBWEBP', 'uncertainty': []},
        {'name': 'libwebpmux (libwebp)', 'key': 'libwebpmux', 'files': [r'libwebpmux-'],
         'same_as': 'libwebp',
         'libtool': ('libwebp-v1.6.0-mux-Makefile.am', r'libwebpmux_la_LDFLAGS = .*-version-info (\d+:\d+:\d+)',
                     r'libwebpmux-')},
        {'name': 'libwebpdemux (libwebp)', 'key': 'libwebpdemux', 'files': [r'libwebpdemux-'],
         'same_as': 'libwebp',
         'libtool': ('libwebp-v1.6.0-demux-Makefile.am', r'libwebpdemux_la_LDFLAGS = .*-version-info (\d+:\d+:\d+)',
                     r'libwebpdemux-')},
        {'name': 'libsharpyuv (libwebp)', 'key': 'libsharpyuv', 'files': [r'libsharpyuv-'],
         'same_as': 'libwebp',
         'libtool': ('libwebp-v1.6.0-sharpyuv-Makefile.am', r'libsharpyuv_la_LDFLAGS = .*-version-info (\d+:\d+:\d+)',
                     r'libsharpyuv-')},
        {'name': 'libxcb', 'key': 'libxcb', 'files': [r'libxcb-'],
         'pin': ('wheels-dependencies.sh', r'^LIBXCB_VERSION=(\S+)'),
         'source': ('wheels-dependencies.sh', r'build_simple libxcb \$LIBXCB_VERSION (https://www\.x\.org/releases/'
                    r'individual/lib)', {}), 'archive': 'libxcb-{v}.tar.gz', 'url_suffix': '/libxcb-{v}.tar.gz', 'flags': [MB_CONFIGURE],
         'licence': 'X11 (MIT-style).', 'provide': 'Notice (present as XCB).', 'notice': r'\bXCB\b',
         'uncertainty': ['libxcb\'s SONAME/interface numbers do not change between releases; no embedded version']},
        {'name': 'Brotli (libbrotlicommon, libbrotlidec)', 'key': 'brotli',
         'files': [r'libbrotlicommon-', r'libbrotlidec-'],
         'pin': ('wheels-dependencies.sh', r'^BROTLI_VERSION=(\S+)'),
         'source': ('wheels-dependencies.sh', r'fetch_unpack (https://github\.com/google/brotli/archive/v\$BROTLI_VERSION'
                    r'\.tar\.gz) brotli-\$BROTLI_VERSION\.tar\.gz', {'BROTLI_VERSION': 'pin'}),
         'archive': 'brotli-{v}.tar.gz',
         'flags': [('wheels-dependencies.sh', r'(cmake -DCMAKE_INSTALL_PREFIX=\$BUILD_PREFIX -DCMAKE_INSTALL_LIBDIR.*'
                                              r'MACOSX_BUNDLE=OFF)')],
         'licence': 'MIT.', 'provide': 'Notice (present as BROTLI).', 'notice': r'BROTLI',
         'uncertainty': ['no embedded version string; file-name numbers only']},
        {'name': 'libavif', 'key': 'libavif', 'files': [r'libavif-'],
         'pin': ('wheels-dependencies.sh', r'^LIBAVIF_VERSION=(\S+)'),
         'source': ('wheels-dependencies.sh', r'fetch_unpack (https://github\.com/AOMediaCodec/libavif/archive/refs/tags/'
                    r'v\$LIBAVIF_VERSION\.tar\.gz) libavif-\$LIBAVIF_VERSION\.tar\.gz', {'LIBAVIF_VERSION': 'pin'}),
         'archive': 'libavif-{v}.tar.gz',
         'flags': [('wheels-dependencies.sh', r'^\s*(-DAVIF_LIBSHARPYUV=LOCAL) \\'),
                   ('wheels-dependencies.sh', r'^\s*(-DAVIF_LIBYUV=LOCAL) \\'),
                   ('wheels-dependencies.sh', r'^\s*(-DAVIF_CODEC_AOM=LOCAL) \\'),
                   ('wheels-dependencies.sh', r'^\s*(-DAVIF_CODEC_AOM_DECODE=OFF) \\'),
                   ('wheels-dependencies.sh', r'^\s*(-DAVIF_CODEC_DAV1D=LOCAL)$'),
                   ('wheels-dependencies.sh', r'^\s*(-DCONFIG_AV1_HIGHBITDEPTH=0) \\')],
         'expect': [r'\x00{v}\x00'],
         'subcomponents': [
             {'name': 'libaom encoder (AVIF_CODEC_AOM=LOCAL, static)',
              'pin': ('libavif-v1.4.1-LocalAom.cmake', r'set\(AVIF_AOM_GIT_TAG (\S+)\)'),
              'licence': 'BSD-2-Clause + AOM Patent License 1.0', 'expect': r'AOMedia Project AV1 Encoder {vn}\x00',
              'source': 'https://aomedia.googlesource.com/aom (git tag pinned by libavif v1.4.1)'},
             {'name': 'dav1d decoder (AVIF_CODEC_DAV1D=LOCAL, static)',
              'pin': ('libavif-v1.4.1-LocalDav1d.cmake', r'set\(AVIF_DAV1D_TAG "([^"]+)"\)'),
              'licence': 'BSD-2-Clause', 'expect': r'(?<![0-9.]){vn}-\d+-g[0-9a-f]+\x00',
              'source': 'https://code.videolan.org/videolan/dav1d.git (git tag pinned by libavif v1.4.1)'},
             {'name': 'libyuv (AVIF_LIBYUV=LOCAL, static)',
              'pin': ('libavif-v1.4.1-LocalLibyuv.cmake', r'set\(AVIF_LIBYUV_TAG "([0-9a-f]+)"\)'),
              'licence': 'BSD-3-Clause', 'source': 'https://chromium.googlesource.com/libyuv/libyuv (commit pinned '
                                                    'by libavif v1.4.1)'},
             {'name': 'libsharpyuv (AVIF_LIBSHARPYUV=LOCAL, static)',
              'pin': ('libavif-v1.4.1-LocalLibsharpyuv.cmake', r'set\(AVIF_LIBSHARPYUV_GIT_TAG (\S+)\)'),
              'licence': 'BSD-3-Clause', 'source': 'https://chromium.googlesource.com/webm/libwebp (git tag pinned '
                                                    'by libavif v1.4.1)'}],
         'licence': 'BSD-2-Clause (libavif) with statically included libaom encoder (BSD-2-Clause + AOM Patent '
                    'License 1.0), dav1d (BSD-2-Clause), libyuv and libsharpyuv (BSD-3-Clause).',
         'provide': 'Notices for libavif, aom (incl. patent licence), dav1d, libyuv (present as LIBAVIF, AOM, DAV1D, '
                    'LIBYUV); source not required by these licences.',
         'notice': r'LIBAVIF', 'uncertainty': ['statically included codecs are fetched by git tag/commit inside '
                                               'libavif\'s CMake (FetchContent), not by Pillow\'s script']},
        {'name': 'libXau', 'key': 'libXau', 'files': [r'libXau-'], 'origin': 'package_transitive',
         'not_linux_pin': ('wheels-dependencies.sh', r'^\s*(build_simple libXau \S+ \S+)'),
         'licence': 'X11-style (The Open Group permission notice); EL8 package build.',
         'provide': 'Notice (present as XAU); source not required. If offered: the AlmaLinux 8 libXau source package '
                    'of the build shown (not fetched).',
         'notice': r'\bXAU\b',
         'uncertainty': ['the script builds libXau only on macOS; the Linux copy is the image\'s EL8 package (version '
                         'from .gnu_debuglink), pulled in by libxcb']},
    ],
    'pyzmq': [
        {'name': 'libzmq (ZeroMQ)', 'key': 'libzmq', 'files': [r'libzmq-'],
         'pin': ('bundle.py', r'^bundled_version = "([^"]+)"'),
         'also_pinned': [('CMakeLists.txt', r'set\(PYZMQ_LIBZMQ_VERSION "([^"]+)"')],
         'source': ('install_libzmq.sh', r'curl -L -O "(https://github\.com/zeromq/libzmq/releases/download/'
                    r'v\$\{LIBZMQ_VERSION\}/zeromq-\$\{LIBZMQ_VERSION\}\.tar\.gz)"', {'LIBZMQ_VERSION': 'pin'}),
         'flags': [('install_libzmq.sh', r'^(\./configure --prefix="\$PREFIX" --disable-perf.*)$')],
         'libtool': ('libzmq-v4.3.5-configure.ac', r'^LTVER="(\d+:\d+:\d+)"', r'libzmq-'),
         'licence_file': ('libzmq-v4.3.5-LICENSE', 'licenses/LICENSE.zeromq.txt'),
         'licence': 'MPL-2.0 (libzmq 4.3.5 LICENSE). Built with CURVE via libsodium and without draft APIs; '
                    'DT_NEEDED shows no GnuTLS/NSS/PGM/NORM.',
         'provide': 'MPL-2.0 s3.2: make the Source Code Form of the MPL-covered files available (zeromq-4.3.5.tar.gz '
                    'from the URL shown; no checksum pinned) and tell recipients how to obtain it; keep the MPL-2.0 '
                    'text (present in the wheel).',
         'notice': r'Mozilla Public License',
         'uncertainty': ['no embedded version string; version corroborated only by libtool interface mapping, '
                         'which is consistent with but does not uniquely prove 4.3.5']},
        {'name': 'libsodium', 'key': 'libsodium', 'files': [r'libsodium-'],
         'pin': ('bundle.py', r'^bundled_libsodium_version = "([^"]+)"'),
         'also_pinned': [('CMakeLists.txt', r'set\(PYZMQ_LIBSODIUM_VERSION "([^"]+)"')],
         'source': ('install_libzmq.sh', r'curl -L -O "(https://github\.com/jedisct1/libsodium/releases/download/'
                    r'\$\{LIBSODIUM_VERSION\}-RELEASE/libsodium-\$\{LIBSODIUM_VERSION\}\.tar\.gz)"',
                    {'LIBSODIUM_VERSION': 'pin'}),
         'flags': [('install_libzmq.sh', r'^(\./configure --prefix="\$PREFIX")$')],
         'expect': [r'\x00{v}\x00'],
         'licence_file': ('libsodium-1.0.20-RELEASE-LICENSE', 'licenses/LICENSE.libsodium.txt'),
         'licence': 'ISC.', 'provide': 'ISC notice (present in the wheel).', 'notice': r'ISC License|Permission to use',
         'uncertainty': []},
    ],
}


# ---------------------------------------------------------------- assembly

def locate(files, spec):
    if not spec:
        return None
    key, pattern = spec[0], spec[1]
    found = pin_line(files[key]['text'], pattern)
    return dict(found, file=files[key]['record']['file'], path=files[key]['record']['path'],
                ref=files[key]['record']['ref'], repository=files[key]['record']['repository']) if found else None


def component_record(distribution, spec, files, libs, notices_text, commit, environment, mirror):
    if spec.get('same_as'):
        base = next(c for c in COMPONENTS[distribution] if c['key'] == spec['same_as'])
        spec = dict(base, **{k: v for k, v in spec.items() if k != 'same_as'}, expect=None, subcomponents=[],
                    notice=base['notice'])
    paths = sorted(p for p in libs if any(re.match(f, p.rsplit('/', 1)[-1]) for f in spec['files']))
    records = [file_record(p, libs[p]) for p in paths]
    origin = spec.get('origin', 'source_build')
    pin = locate(files, spec.get('pin')) if origin == 'source_build' else None
    version = pin['value'] if pin else None
    rec = {'component': spec['name'], 'key': spec['key'], 'files': records, 'origin': origin,
           'claimed_upstream_version': version, 'pin': pin,
           'also_pinned': [locate(files, s) for s in spec.get('also_pinned', [])],
           'licence_as_built': spec['licence'], 'redistributor_would_need': spec['provide'],
           'copyleft_as_built': COPYLEFT_AS_BUILT.get(spec['key']),
           'dual_licence_with_gpl_option': DUAL_WITH_GPL_OPTION.get(spec['key']),
           'uncertainty': list(spec.get('uncertainty', []))}
    # source location and checksum
    source_kind = None
    if spec.get('source'):
        found = locate(files, spec['source'])
        variables = {k: (version if v == 'pin' else v) for k, v in spec['source'][2].items()}
        url = expand(found['value'], variables) + (spec.get('url_suffix', '').replace('{v}', version or ''))
        build_text = files[spec['source'][0]]['text']
        sums = checksum_lines(build_text)
        rec['source'] = {'url': url, 'kind': spec.get('source_kind', 'archive URL'), 'named_at': found,
                         'checksum_pinned': [s for s in sums if spec['key'].lower() in s['text'].lower()] or None,
                         'checksum_lines_in_file': len(sums)}
        if not rec['source']['checksum_pinned']:
            rec['uncertainty'].insert(0, NO_CHECKSUM)
        source_kind = 'upstream_url_with_checksum' if rec['source']['checksum_pinned'] else 'upstream_url'
        if spec.get('archive') and mirror is not None:
            name = spec['archive'].replace('{v}', version)
            blob = mirror['archives'].get(name)
            rec['source']['pillow_depends_archive'] = {'archive_name_fetch_unpack_looks_for': name,
                                                       'present_at_inferred_commit': blob is not None,
                                                       'git_blob_sha1': blob, 'commit': mirror['commit']}
            if blob:
                source_kind = 'unpinned_mirror'
                rec['uncertainty'].append(
                    f"multibuild's fetch_unpack uses {name} from the unpinned python-pillow/pillow-depends@main zip "
                    f"when present; it is present at {mirror['commit'][:12]} (latest main commit before upload), so "
                    "the upstream URL is only the fallback; byte identity with upstream not checked")
    elif origin != 'source_build':
        source_kind = 'distro_srpm'
    rec['flags'] = [f for f in (locate(files, s) for s in spec.get('flags', [])) if f]
    keys = sorted({s[0] for s in [spec.get('source'), *spec.get('flags', [])] if s})
    rec['patch_commands'] = [{'file': files[k]['record']['path'], 'line': n, 'text': t.strip()[:200]} for k in keys
                             for n, t in enumerate(files[k]['text'].splitlines(), 1)
                             if re.search(r'(?<![\w-])patch\s+-', t)]
    if spec.get('package'):
        rec['package_install_line'] = locate(files, spec['package'])
    if spec.get('not_linux_pin'):
        rec['macos_only_build_line'] = locate(files, spec['not_linux_pin'])
    # binary corroboration
    blobs = [libs[p] for p in paths]
    evidence, corroboration = {}, None
    if spec.get('expect') and version:
        hits = sorted({m.group(0).strip(b'\0').decode('utf-8', 'replace') for data in blobs
                       for pat in version_patterns(spec['expect'], version) for m in re.finditer(pat, data)})
        evidence['embedded_version_strings'] = hits
        if hits:
            corroboration = 'embedded_version'
    if spec.get('expect_regex'):
        evidence['embedded_version_strings'] = sorted({m.group(0).decode('utf-8', 'replace').strip()[:80]
                                                       for data in blobs for m in re.finditer(spec['expect_regex'], data)})
    if spec.get('embedded_configure'):
        evidence['embedded_configure'] = sorted({m.group(0).decode().strip() for data in blobs
                                                 for m in re.finditer(spec['embedded_configure'], data)})
        evidence['embedded_configure_matches_flags'] = bool(rec['flags']) and [
            x.split() for x in evidence['embedded_configure']] == [shlex.split(rec['flags'][0]['value'])]
    if spec.get('libtool'):
        key, pattern, lib = spec['libtool']
        found = locate(files, (key, pattern))
        target = next(r for r in records if re.match(lib, r['path'].rsplit('/', 1)[-1]))
        expected = libtool_suffix(found['value'])
        evidence['libtool_mapping'] = {'upstream_version_info': found, 'expected_file_suffix': expected,
                                       'file_suffix': target['file_name_interface_numbers'],
                                       'matches': expected == target['file_name_interface_numbers']}
        if corroboration is None and evidence['libtool_mapping']['matches']:
            corroboration = 'libtool_mapping'
    if origin != 'source_build':
        builds = sorted({r['debuglink_package_build'][1] for r in records if r['debuglink_package_build']})
        evidence['el8_package_build'] = builds
        rec['claimed_upstream_version'] = (', '.join(builds) + ' (EL8 package build from .gnu_debuglink)') if builds \
            else None
        if builds:
            corroboration = 'package_build_id'
    if spec.get('licence_file'):
        key, member = spec['licence_file']
        wheel_text = next((t for n, t in notices_text.items() if n.endswith(member)), None)
        rec['licence_text_check'] = {'upstream': files[key]['record'], 'wheel_member': member,
                                     'identical': wheel_text is not None and
                                     sha256_bytes(wheel_text.encode()) == files[key]['record']['sha256']}
    rec['binary_evidence'] = evidence
    rec['corroboration'] = corroboration
    rec['subcomponents'] = []
    for sub in spec.get('subcomponents', []):
        found = locate(files, sub['pin'])
        item = {'name': sub['name'], 'pin': found, 'licence': sub['licence'], 'source': sub['source']}
        if sub.get('expect') and found:
            pats = version_patterns([sub['expect']], found['value'])
            item['embedded_version_strings'] = sorted({m.group(0).strip(b'\0').decode() for data in blobs
                                                       for p in pats for m in re.finditer(p, data)})
        rec['subcomponents'].append(item)
    pin_kind = 'explicit' if pin else origin if origin != 'source_build' else None
    rec['chain_links'] = {'build_commit': commit, 'pin': pin_kind, 'source': source_kind,
                          'build_environment': environment, 'corroboration': corroboration}
    rec['chain_status'], rec['missing_links'] = chain_status(commit, pin_kind, source_kind, environment,
                                                             corroboration)
    rec['named_in_wheel_notice'] = bool(re.search(spec['notice'], notices_text_all(notices_text), re.I))
    if not rec['named_in_wheel_notice']:
        rec['uncertainty'].append('no matching section found in the licence/notice files shipped in the wheel')
    return rec


def notices_text_all(notices_text):
    return '\n'.join(notices_text.values())


def ffmpeg_logic(files, component):
    """What FFmpeg's own configure/LICENSE.md at n8.0.1 say about OpenSSL and the licence label (verbatim lines)."""
    configure = files['ffmpeg-n8.0.1-configure']['text']
    lines = configure.splitlines()

    def block(start_pattern, count):
        found = pin_line(configure, start_pattern)
        return {'start_line': found['line'], 'lines': lines[found['line'] - 1:found['line'] - 1 + count]}
    openssl = block(r'^enabled openssl\s+&& \{ \{ check_pkg_config openssl "openssl >= 3\.0\.0"', 7)
    text = '\n'.join(openssl['lines'])
    for needle in ('! enabled gpl', 'enabled gpl && ! enabled nonfree && die "ERROR: OpenSSL <3.0.0 is incompatible'):
        if needle not in text:
            raise SystemExit(f'FFmpeg configure OpenSSL logic changed; re-read before restating it ({needle!r})')
    lists = {n: shell_list(configure, n) for n in ('EXTERNAL_LIBRARY_GPL_LIST', 'EXTERNAL_LIBRARY_NONFREE_LIST',
                                                   'EXTERNAL_LIBRARY_VERSION3_LIST', 'EXTERNAL_LIBRARY_GPLV3_LIST')}
    licence_md = files['ffmpeg-n8.0.1-LICENSE.md']['text']
    statement = re.search(r'The Fraunhofer FDK AAC and OpenSSL libraries.*?LGPL\.', licence_md, re.S)
    embedded = sorted({m.group(0).decode().strip() for r in component['files']
                       for m in re.finditer(rb'--prefix=/ffmpeg_build --extra-cflags[^\x00]*', r['_data'])})
    licence_strings = sorted({m.group(0).decode() for r in component['files']
                              for m in re.finditer(rb'(?:L?GPL|nonfree)[^\x00]{0,10}version[^\x00]{0,30}|nonfree '
                                                   rb'and unredistributable', r['_data'])})
    idents = {r['path'].rsplit('/', 1)[-1]: sorted({m.group(0).decode() for m in FFMPEG_IDENT.finditer(r['_data'])})
              for r in component['files']}
    raw_flags = shlex.split(component['flags'][0]['value'])
    docker_flags = [expand(f, {'HOME': '/root'}) for f in raw_flags]
    embedded_flags = embedded[0].split() if len(embedded) == 1 else []
    return {
        'configure_retained': files['ffmpeg-n8.0.1-configure']['record'],
        'licence_md_retained': files['ffmpeg-n8.0.1-LICENSE.md']['record'],
        'openssl_in_lists': {n: ('openssl' in (v or [])) for n, v in lists.items()},
        'lists': lists,
        'licence_label_logic': block(r'^if enabled nonfree; then$', 11),
        'openssl_check': openssl,
        'reading': ('At n8.0.1, --enable-openssl is not in the GPL, nonfree or version3 library lists. The OpenSSL '
                    'check requires --enable-version3 only for OpenSSL >= 3.0.0 combined with --enable-gpl, and '
                    'refuses OpenSSL < 3.0.0 only with --enable-gpl (unless --enable-nonfree). Without --enable-gpl '
                    'neither --enable-nonfree nor --enable-version3 is required, and the label stays "LGPL version '
                    '2.1 or later".'),
        'licence_md_statement': ' '.join(statement.group(0).split()) if statement else None,
        'dockerfile_configure_flags': raw_flags,
        'dockerfile_flags_compared_as': docker_flags,
        'home_substitution_note': ('$HOME is compared as /root: the Dockerfile RUN steps before "USER ci" run as '
                                   'root, and the embedded string carries --bindir=/root/bin. This also indicates the '
                                   'libraries were built during the image build, not in the wheel CI run.'),
        'embedded_equals_dockerfile': embedded_flags == docker_flags,
        'embedded_configuration_strings': embedded,
        'flags_in_dockerfile_not_embedded': [f for f in docker_flags if f not in embedded_flags],
        'embedded_flags_not_in_dockerfile': [f for f in embedded_flags if f not in docker_flags],
        'licence_relevant_flags_present': sorted({f for f in docker_flags + embedded_flags
                                                  if f in ('--enable-gpl', '--enable-version3', '--enable-nonfree')}),
        'label_from_flags': ffmpeg_licence(embedded_flags or docker_flags),
        'embedded_licence_strings': licence_strings,
        'embedded_library_idents': idents,
        'uncertainty': ('The label is FFmpeg\'s; whether linking LGPL-2.1 FFmpeg with OpenSSL 1.1.1 (OpenSSL/SSLeay '
                        'licences) is acceptable is FFmpeg\'s stated view ("to the best of our knowledge"), not a '
                        'legal conclusion of this pack.')}


def pillow_depends(upload_time, distribution):
    commits, record = api_json(f'native-{distribution}-pillow-depends-main-commits.json', API.format(
        repo='python-pillow/pillow-depends', endpoint=f'commits?sha=main&until={upload_time}&per_page=1'))
    sha = commits[0]['sha']
    tree, tree_record = api_json(f'native-{distribution}-pillow-depends-tree.json',
                                 API.format(repo='python-pillow/pillow-depends', endpoint=f'git/trees/{sha}'))
    return {'commit': sha, 'commit_date': commits[0]['commit']['committer']['date'],
            'message_first_line': commits[0]['commit']['message'].splitlines()[0],
            'archives': {e['path']: e['sha'] for e in tree['tree'] if e['type'] == 'blob'},
            'records': [record, tree_record],
            'basis': ('wheels-dependencies.sh downloads https://github.com/python-pillow/pillow-depends/archive/'
                      'main.zip at build time (branch, not a commit); the commit shown is the latest on main before '
                      'the PyPI upload time, an inference about what the build saw.')}


def build_wheel(wheel):
    distribution = wheel['distribution']
    artifact = artifact_for(distribution)
    libs, extensions, notices = wheel_listing(artifact)
    commit = build_commit(wheel, artifact)
    files = retain_files(distribution, wheel['files'], commit['commit'])
    extra = {}
    if distribution == 'opencv_python_headless':
        tree, record = api_json(f'native-{distribution}-tree.json', API.format(
            repo=wheel['repo'], endpoint=f"git/trees/{commit['commit']}"))
        submodules = {e['path']: e['sha'] for e in tree['tree'] if e['type'] == 'commit'}
        info = opencv_build_information(extensions['cv2/cv2.abi3.so'])
        vc = next((line for line in info if line.startswith('Version control')), '')
        abbrev = re.search(r'-g([0-9a-f]{7,})', vc)
        image = pin_line(files['workflow']['text'], r'DOCKER_IMAGE: (quay\.io/opencv-ci/opencv-python-manylinux_2_28-'
                                                    r'x86-64:\S+)')
        version_comment = pin_line(files['dockerfile']['text'], r'^# Version: (\S+)')
        base = pin_line(files['dockerfile']['text'], r'^FROM (\S+)')
        commit['corroboration'] = {
            'submodules_at_commit': submodules, 'submodule_tree_record': record,
            'embedded_version_control': vc,
            'embedded_opencv_commit_matches_submodule': bool(abbrev and submodules.get('opencv', '').startswith(
                abbrev.group(1))),
            'embedded_build_timestamp': next((line for line in info if line.startswith('Timestamp')), None)}
        extra['build_image'] = {'workflow_image_line': image, 'dockerfile_version_comment': version_comment,
                                'dockerfile_base_image': base,
                                'image_tag_matches_dockerfile_version': bool(
                                    image and version_comment and image['value'].endswith(':' + version_comment['value'])),
                                'note': ('The libraries in opencv_python_headless.libs/ were built into the prebuilt '
                                         'image named by the workflow, not in the wheel run. The Dockerfile at the '
                                         'commit carries the same version tag, but the image (and its unpinned '
                                         '":latest" base) was not inspected or verified.')}
        extra['extension_module_notes'] = {
            'cv2/cv2.abi3.so embedded build information (clue-level, not traced here)': info,
            'patches': [pin_line(files['setup.py']['text'], r'^\s*(subprocess\.check_call\("patch -p0 < patches/patchOpenEXR".*)'),
                        pin_line(files['setup.py']['text'], r'^\s*(subprocess\.check_call\("patch -p1 < patches/patchQtPlugins".*)')],
            'patches_note': ('opencv-python applies patches only to OpenEXR on 32-bit Linux and to the Qt plugins for '
                             'non-headless builds; the Dockerfile applies no patches to the bundled libraries.')}
    if distribution == 'pillow':
        sub, record = api_json(f'native-{distribution}-multibuild-submodule.json', API.format(
            repo=wheel['repo'], endpoint=f"contents/wheels/multibuild?ref={commit['commit']}"))
        extra['multibuild_submodule'] = {'commit': sub['sha'], 'record': record}
        files.update(retain_files(distribution, {k: {'repo': 'multi-build/multibuild', 'path': p, 'ref': sub['sha']}
                                                 for k, p in wheel['submodule_files'].items()}, commit['commit']))
        extra['pillow_depends'] = pillow_depends(commit['pypi']['upload_time'], distribution)
        extra['cibuildwheel'] = pin_line(files['requirements-cibw.txt']['text'], r'^(cibuildwheel==\S+)')
        extra['patch_mechanism'] = {
            'fetch_unpack_patch_hook': pin_line(files['multibuild-common_utils.sh']['text'],
                                                r'^\s*(if \[ -e "\$\{PATCH_DIR\}/\$\{archive_fname\}\.patch" \]; then)'),
            'PATCH_DIR_set_in_wheels_dependencies': 'PATCH_DIR' in files['wheels-dependencies.sh']['text'],
            'note': 'multibuild applies ${PATCH_DIR}/<archive>.patch if present; Pillow\'s script does not set '
                    'PATCH_DIR, so no patches are applied by this route.'}
        extra['extension_module_notes'] = {
            'config_settings': pin_line(files['pyproject.toml']['text'], r'^(config-settings = "raqm=enable.*")'),
            'fribidi_shim': pin_line(files['setup.py']['text'], r'^\s*(srcs\.append\("src/thirdparty/fribidi-shim/fribidi\.c"\))'),
            'note': ('_imagingft compiles the vendored raqm (src/thirdparty, MIT) and a FriBiDi shim that loads '
                     'libfribidi at run time if present; FriBiDi itself (LGPL) is not shipped in the wheel. zlib-ng is '
                     'built but no libz is bundled (DT_NEEDED libz.so.1 is left to the system).')}
    if distribution == 'pyzmq':
        extra['linux_build_hook'] = pin_line(files['pyproject.toml']['text'], r'^before-all = "(bash tools/install_libzmq\.sh)"')
        extra['cibuildwheel'] = pin_line(files['wheel-requirements.txt']['text'], r'^(cibuildwheel\S*)')
        extra['linux_image'] = pin_line(files['pyproject.toml']['text'], r'^manylinux-x86_64-image = "(\S+)"')
    environment = wheel['environment']
    mirror = extra.get('pillow_depends')
    components = []
    for spec in COMPONENTS[distribution]:
        comp = component_record(distribution, spec, files, libs, notices, commit['status'], environment, mirror)
        components.append(comp)
    ffmpeg = None
    if distribution == 'opencv_python_headless':
        comp = next(c for c in components if c['key'] == 'ffmpeg')
        for r in comp['files']:
            r['_data'] = libs[r['path']]
        ffmpeg = ffmpeg_logic(files, comp)
        for r in comp['files']:
            r.pop('_data')
        comp['binary_evidence']['embedded_configuration_strings'] = ffmpeg['embedded_configuration_strings']
        comp['binary_evidence']['embedded_licence_strings'] = ffmpeg['embedded_licence_strings']
        comp['binary_evidence']['embedded_library_idents'] = ffmpeg['embedded_library_idents']
    covered = {r['path'] for c in components for r in c['files']}
    return {'distribution': distribution, 'artifact': artifact['filename'], 'sha256': artifact['sha256'],
            'bundled_libraries': sorted(libs), 'unassigned_bundled_libraries': sorted(set(libs) - covered),
            'licence_files_in_wheel': sorted(notices), 'build_commit': commit, 'build_files': {
                k: v['record'] for k, v in files.items()}, 'components': components, 'ffmpeg_licence_logic': ffmpeg,
            **extra}


def build():
    wheels = [build_wheel(w) for w in WHEELS]
    status_counts = {}
    for w in wheels:
        for c in w['components']:
            status_counts[c['chain_status']] = status_counts.get(c['chain_status'], 0) + 1
    return {'schema': 'wheelhouse_evidence_native_libraries_v1', 'wheels': wheels, 'status_counts': status_counts,
            'method': {
                'chain': 'wheel -> build commit -> pin at that commit -> source URL/checksum -> flags/patches -> '
                         'binary corroboration',
                'statuses': STATUS_RULES,
                'complete_note': ('"complete" requires a named source URL with a pinned checksum; none of the three '
                                  'builds pins a checksum for any source archive, so no chain is complete and each '
                                  'such row lists the missing checksum as a missing link.'),
                'clues': ('File names, SONAMEs and libtool interface numbers are clues: a libtool mapping that '
                          'matches the pinned release is consistent with it but does not prove it.')}}


# ---------------------------------------------------------------- markdown

def cell(text):
    return str(text).replace('|', '\\|').replace('\n', ' ')


def pin_cell(pin):
    if not pin:
        return '—'
    return f"`{pin['path']}` L{pin['line']} @`{pin['ref'][:12]}`: `{cell(pin['text'])}`"


def library_rows(w):
    rows = ['| Library | File(s) in wheel (sha256) | Claimed upstream version | Pin location | Source URL / checksum | '
            'Patches / flags | Licence as built | Chain | Uncertainty |', '|---|---|---|---|---|---|---|---|---|']
    for c in w['components']:
        files = '<br>'.join(f"`{r['path'].rsplit('/', 1)[-1]}` (`{r['sha256'][:12]}…`)" for r in c['files'])
        if c.get('source'):
            s = c['source']
            source = f"{s['url']} ({s['kind']}); checksum: " + (
                'pinned' if s['checksum_pinned'] else 'none pinned')
            pd = s.get('pillow_depends_archive')
            if pd:
                source += (f"; pillow-depends `{pd['archive_name_fetch_unpack_looks_for']}`: "
                           + (f"present (blob `{pd['git_blob_sha1'][:12]}…`), used in preference" if
                              pd['present_at_inferred_commit'] else 'absent, so upstream URL used'))
        elif c['origin'] != 'source_build':
            source = 'EL8 distribution source package (not fetched)'
        else:
            source = '—'
        flags = '; '.join(f"`{cell(f['value'] or f['text'])}` (L{f['line']})" for f in c['flags']) or (
            f"installed by `{cell(c['package_install_line']['text'][:120])}` (L{c['package_install_line']['line']})"
            if c.get('package_install_line') else 'defaults (no library-specific flags in the build file)'
            if c['origin'] == 'source_build' else 'not named in any build file')
        if c['origin'] == 'source_build':
            flags += '; patch commands in these build files: ' + (
                ', '.join(f"L{x['line']} `{cell(x['text'])}`" for x in c['patch_commands']) or 'none')
        licence = c['licence_as_built']
        if c.get('licence_text_check'):
            lt = c['licence_text_check']
            licence += (f" Wheel's `{lt['wheel_member']}` {'is identical to' if lt['identical'] else 'DIFFERS from'} "
                        f"`{lt['upstream']['path']}` at `{lt['upstream']['ref']}`.")
        ev = c['binary_evidence']
        corr = []
        if ev.get('embedded_version_strings'):
            corr.append('embedded: ' + ', '.join(f'`{cell(x)}`' for x in ev['embedded_version_strings'][:3]))
        if ev.get('libtool_mapping'):
            lt = ev['libtool_mapping']
            corr.append(f"libtool `{lt['upstream_version_info']['value']}` → `.so.{lt['expected_file_suffix']}` "
                        f"({'matches' if lt['matches'] else 'DIFFERS from'} file)")
        if ev.get('el8_package_build'):
            corr.append('debuglink build ' + ', '.join(f'`{x}`' for x in ev['el8_package_build']))
        if ev.get('embedded_configure'):
            corr.append('embedded configure string ' + ('identical to' if ev['embedded_configure_matches_flags']
                                                        else 'DIFFERS from') + ' the Dockerfile flags')
        subs = ''.join(f"<br>+ {cell(s['name'])}: `{s['pin']['value'] if s['pin'] else '?'}` "
                       f"({s['pin']['path'] if s['pin'] else ''} L{s['pin']['line'] if s['pin'] else ''}), "
                       f"{cell(s['licence'])}" + (f", embedded `{', '.join(s['embedded_version_strings'])}`"
                                                  if s.get('embedded_version_strings') else '')
                       for s in c['subcomponents'])
        status = f"**{c['chain_status']}**" + (f"; missing: {'; '.join(c['missing_links'])}" if c['missing_links']
                                                else '')
        rows.append(f"| {cell(c['component'])} | {files} | `{cell(c['claimed_upstream_version'] or '—')}`"
                    f"{('<br>' + '; '.join(corr)) if corr else ''} | {pin_cell(c['pin'])} | {cell(source)} | "
                    f"{flags}{subs} | {cell(licence)} | {status} | "
                    f"{cell('; '.join(c['uncertainty']) or '—')} |")
    return rows


def commit_lines(w):
    bc = w['build_commit']
    att = bc['attestation']
    lines = [f"- Wheel: `{w['artifact']}` (sha256 `{w['sha256']}`), uploaded to PyPI {bc['pypi']['upload_time']} "
             f"(PyPI sha256 {'matches' if bc['pypi']['sha256_matches_manifest'] else 'DIFFERS from'} the manifest)."]
    if att['available']:
        claims = att['certificate_claims']
        lines += [f"- **Build commit ATTESTED**: `{bc['commit']}` ({claims.get('source_repository_ref')}) in "
                  f"{claims.get('source_repository_uri')}; workflow `{claims.get('build_config_uri')}`; run "
                  f"{claims.get('run_invocation_uri')}; publisher {att['publisher']}. Statement subject matches the "
                  f"wheel file and sha256: {att['subject_matches_wheel']}. {att['verification_note']}",
                  f"- Release tag `{bc['release_tag']['tag']}` resolves to `{bc['release_tag']['commit']}` "
                  f"(agrees with attestation: {bc['tag_agrees_with_attestation']})."]
    else:
        lines += [f"- **No PyPI attestation** for this file ({att['record'].get('error', 'absent')}).",
                  f"- **Build commit INFERRED** from release tag `{bc['release_tag']['tag']}` → `{bc['commit']}` "
                  f"({bc['release_tag']['commit_date']}, \"{bc['release_tag']['message_first_line']}\"); workflow "
                  f"{bc['workflow']}."]
        corr = bc.get('corroboration')
        if corr:
            lines.append(f"- Corroboration: cv2.abi3.so embeds `{corr['embedded_version_control']}`; the opencv "
                         f"submodule at the tag commit is `{corr['submodules_at_commit'].get('opencv')}` (match: "
                         f"{corr['embedded_opencv_commit_matches_submodule']}); `{corr['embedded_build_timestamp']}`. "
                         "This ties the wheel to the submodule state, not cryptographically to the commit.")
    return lines


def summary_lines(p):
    out = []
    for w in p['wheels']:
        bc, counts = w['build_commit'], {}
        for c in w['components']:
            counts[c['chain_status']] = counts.get(c['chain_status'], 0) + 1
        copyleft = [f"{c['component']} ({c['copyleft_as_built']})" for c in w['components'] if c['copyleft_as_built']]
        dual = [f"{c['component']} ({c['dual_licence_with_gpl_option']})" for c in w['components']
                if c['dual_licence_with_gpl_option']]
        gaps = [c['component'] for c in w['components'] if not c['named_in_wheel_notice']]
        out.append(f"- **{w['distribution']}**: build commit **{bc['status'].replace('_', '-')}** `{bc['commit'][:12]}`; "
                   + ', '.join(f'{v} {k}' for k, v in sorted(counts.items())) + '. '
                   + (f"Copyleft as built: {'; '.join(copyleft)}. " if copyleft else
                      'No bundled library is copyleft-only as built. ')
                   + (f"Dual licences with a GPL option: {'; '.join(dual)}. " if dual else '')
                   + (f"No section found in the wheel's notice files for: {', '.join(gaps)}." if gaps else
                      "Every bundled library has a matching section in the wheel's notice files."))
    for w in p['wheels']:
        f = w.get('ffmpeg_licence_logic')
        if f:
            out.append(f"- **FFmpeg 8.0.1 (opencv)**: configure flags `{' '.join(f['dockerfile_configure_flags'])}`; "
                       f"licence-relevant flags present: {', '.join(f['licence_relevant_flags_present']) or 'none'}; "
                       f"embedded licence string {', '.join(f['embedded_licence_strings'])}; {f['reading']}")
        for c in w['components']:
            if c['key'] == 'libzmq':
                lt = c.get('licence_text_check') or {}
                out.append(f"- **libzmq (pyzmq)**: pinned {c['claimed_upstream_version']} "
                           f"(`{c['pin']['path']}` L{c['pin']['line']}); {c['copyleft_as_built']}; wheel licence text "
                           f"identical to upstream LICENSE at v4.3.5: {lt.get('identical')}; version corroborated by "
                           "libtool mapping only (no embedded version string).")
    out += ['- **Main uncertainties**: no build pins a checksum for any source archive; opencv-python has no PyPI '
            'attestation (commit inferred from tag 92, corroborated by the embedded opencv submodule hash) and its '
            'libraries were built in a separately published image (not verified); Pillow takes most source archives '
            'from the unpinned pillow-depends@main zip (commit inferred); EL8 package libraries are identified only '
            'from .gnu_debuglink and their source packages were not fetched; attestation signatures were not '
            're-verified locally.']
    return out


def markdown(p):
    lines = ['# Bundled native libraries: provenance evidence pack', '',
             '**A proposal for the designated reviewer, not a decision and not legal clearance.**', '',
             'For each library that auditwheel grafted into `<dist>.libs/` of the three wheels, this pack traces: '
             'wheel → build commit (PyPI attestation, else release tag) → the build file at that commit that pins '
             'the version → the source archive URL/checksum → configure flags and patches → clue-level corroboration '
             'from the local wheel\'s binaries. **File names, SONAMEs and libtool interface numbers are clues only**; '
             'where a version is corroborated, the evidence (embedded string, libtool mapping at the pinned upstream '
             'tag, or EL8 package build id) is named.', '',
             'Chain status rules:', '']
    lines += [f'- `{k}`: {v}' for k, v in p['method']['statuses'].items()]
    lines += ['', p['method']['complete_note'], p['method']['clues'], '',
              'Status counts: ' + ', '.join(f'{k}: {v}' for k, v in sorted(p['status_counts'].items())), '',
              '## Summary (proposal)', ''] + summary_lines(p) + ['']
    for w in p['wheels']:
        lines += [f"## {w['distribution']}", '', '### Build commit evidence', ''] + commit_lines(w) + ['']
        if w.get('build_image'):
            bi = w['build_image']
            lines += [f"- Build image: workflow L{bi['workflow_image_line']['line']} uses "
                      f"`{bi['workflow_image_line']['value']}`; the Dockerfile at the commit says "
                      f"`{bi['dockerfile_version_comment']['text']}` (tag match: "
                      f"{bi['image_tag_matches_dockerfile_version']}) and `{bi['dockerfile_base_image']['text']}`. "
                      f"{bi['note']}", '']
        if w.get('multibuild_submodule'):
            pd = w['pillow_depends']
            lines += [f"- multibuild submodule at the commit: `{w['multibuild_submodule']['commit']}` (provides "
                      f"`build_freetype`, `build_libpng`, `build_tiff`, `build_lcms2`, `build_openjpeg`, `build_xz`, "
                      f"`build_libjpeg_turbo`, `fetch_unpack`).",
                      f"- Archive cache: {pd['basis']} Inferred commit `{pd['commit']}` ({pd['commit_date']}, "
                      f"\"{pd['message_first_line']}\").",
                      f"- cibuildwheel: `{w['cibuildwheel']['text']}` (`.ci/requirements-cibw.txt`). "
                      f"{w['patch_mechanism']['note']}", '']
        if w.get('linux_build_hook'):
            lines += [f"- Linux build hook: `pyproject.toml` L{w['linux_build_hook']['line']} "
                      f"`{w['linux_build_hook']['text']}`; image `{w['linux_image']['value']}`; "
                      f"`{w['cibuildwheel']['text']}` (`tools/wheel-requirements.txt`).", '']
        if w.get('ffmpeg_licence_logic'):
            f = w['ffmpeg_licence_logic']
            lines += ['### FFmpeg licence logic at the pinned release (n8.0.1)', '',
                      f"- Configure flags in the Dockerfile: `{' '.join(f['dockerfile_configure_flags'])}`.",
                      f"- Configuration string embedded in all five FFmpeg libraries: "
                      f"`{'` / `'.join(f['embedded_configuration_strings'])}` (identical to the Dockerfile flags: "
                      f"{f['embedded_equals_dockerfile']}; Dockerfile flags not embedded: "
                      f"{', '.join(f'`{x}`' for x in f['flags_in_dockerfile_not_embedded']) or 'none'}; embedded but "
                      f"not in the Dockerfile: {', '.join(f['embedded_flags_not_in_dockerfile']) or 'none'}). "
                      f"{f['home_substitution_note']}",
                      f"- Licence-relevant flags (`--enable-gpl`, `--enable-version3`, `--enable-nonfree`) present: "
                      f"{', '.join(f['licence_relevant_flags_present']) or '**none**'}. Label implied by configure's "
                      f"logic: **{f['label_from_flags']}**; licence string embedded in the libraries: "
                      f"{', '.join(f'`{x}`' for x in f['embedded_licence_strings'])}.",
                      f"- `openssl` in configure's library lists: {f['openssl_in_lists']}.",
                      f"- OpenSSL check (configure L{f['openssl_check']['start_line']}):", '', '```']
            lines += f['openssl_check']['lines'] + ['```', '',
                                                     f"- Licence label logic (configure L{f['licence_label_logic']['start_line']}):",
                                                     '', '```'] + f['licence_label_logic']['lines'] + ['```', '',
                                                                                                      f"- Reading: {f['reading']}",
                                                                                                      f"- FFmpeg LICENSE.md: \"{f['licence_md_statement']}\"",
                                                                                                      f"- Uncertainty: {f['uncertainty']}", '']
        lines += ['### Bundled libraries', ''] + library_rows(w) + ['']
        if w['unassigned_bundled_libraries']:
            lines += ['Unassigned bundled files (not traced): ' + ', '.join(w['unassigned_bundled_libraries']), '']
        notes = w.get('extension_module_notes')
        if notes:
            lines += ['### Extension-module notes (clue-level, outside the bundled-library scope)', '']
            for k, v in notes.items():
                if isinstance(v, list):
                    vals = [x if isinstance(x, str) else f"L{x['line']}: {x['text']}" for x in v if x]
                    lines += [f'- {k}:'] + [f'  - `{cell(x)}`' for x in vals]
                elif isinstance(v, dict) or v is None:
                    lines.append(f"- {k}: " + (f"L{v['line']} `{cell(v['text'])}`" if v else 'not found'))
                else:
                    lines.append(f'- {k}: {v}')
            lines.append('')
        lines += ['### What a redistributor would need to provide (proposal)', '']
        lines += [f"- **{c['component']}**: {c['redistributor_would_need']}" for c in w['components']]
        lines.append('')
    lines += ['## Retained sources', '',
              'All fetched files are under `reports/wheelhouse_evidence/sources/native-*`; each record in the JSON '
              'gives URL, retrieval date and SHA-256. GitHub API responses reused from an earlier retained copy (if '
              'the API refused) are flagged `reused_retained_copy`.']
    return '\n'.join(lines)


if __name__ == '__main__':
    payload = build()
    write_pack('native_libraries', payload, markdown(payload))
    print(json.dumps({w['distribution']: {'build_commit': [w['build_commit']['status'], w['build_commit']['commit']],
                                          'components': {c['key']: c['chain_status'] for c in w['components']}}
                      for w in payload['wheels']}, indent=1))
