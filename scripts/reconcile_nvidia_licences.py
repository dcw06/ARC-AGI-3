"""Reconcile the NVIDIA wheels' bundled licence texts with version-specific primary NVIDIA sources (licence-review
preparation; establishes applicability facts and open questions, never redistribution permission).

  python scripts/reconcile_nvidia_licences.py --fetch     retain the primary sources (network: NVIDIA docs, GitHub)
  python scripts/reconcile_nvidia_licences.py             offline: compare against the local R2 wheels

Primary sources are kept byte-for-byte in reports/wheelhouse_primary_licence_sources/ (HTML also as extracted text)
with URL, retrieval date and SHA-256. The offline step lists the library files each wheel ships and records, for
each, whether its name appears in Attachment A of (a) the licence text bundled in that wheel and (b) the official
version-specific EULA, writing reports/wheelhouse_nvidia_licence_reconciliation.{json,md}.
"""
import argparse
import datetime
import hashlib
import html
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = ROOT / 'reports/wheelhouse_primary_licence_sources'
SOURCES_INDEX = SOURCES_DIR / 'index.json'
MANIFEST = ROOT / 'reports/wheelhouse_download_manifest.json'
CLOSURE = ROOT / 'reports/wheelhouse_metadata_closure.json'
OUT_JSON = ROOT / 'reports/wheelhouse_nvidia_licence_reconciliation.json'
OUT_MD = ROOT / 'reports/wheelhouse_nvidia_licence_reconciliation.md'
DEFAULT_WHEELHOUSE = Path.home() / '.local/share/agi/wheelhouse-r2'
CAP = 8 * 1024 ** 2
TIMEOUT = 60

SOURCES = {
    'cuda-12.8.1-eula': {
        'url': 'https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html', 'kind': 'html',
        'basis': 'official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: '
                 'cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)'},
    'nvshmem-v3.4.5-0-license': {
        'url': 'https://raw.githubusercontent.com/NVIDIA/nvshmem/v3.4.5-0/License.txt', 'kind': 'text',
        'basis': 'License.txt at the NVIDIA/nvshmem tag v3.4.5-0 (the release of the 3.4.5 wheel): NVIDIA SDK licence '
                 'plus the NVSHMEM supplement'},
    'nvshmem-sla-latest': {
        'url': 'https://docs.nvidia.com/nvshmem/api/latest/sla.html', 'kind': 'html',
        'basis': 'current NVSHMEM SLA page; NOT version-specific (no 3.4.x SLA page exists in the NVSHMEM archive, '
                 'which ends at 2.8.0)'},
    'cutlass-v4.5.0-eula': {
        'url': 'https://raw.githubusercontent.com/NVIDIA/cutlass/v4.5.0/EULA.txt', 'kind': 'text',
        'basis': 'EULA.txt at the NVIDIA/cutlass tag v4.5.0; the wheels are 4.5.0.dev0, a pre-release with no tag of '
                 'its own'},
}
# wheel distribution prefix -> (primary source id, kind of terms) for the reconciliation
WHEELS = {
    'nvidia_cublas_cu12': 'cuda-12.8.1-eula', 'nvidia_cuda_cupti_cu12': 'cuda-12.8.1-eula',
    'nvidia_cuda_nvrtc_cu12': 'cuda-12.8.1-eula', 'nvidia_cuda_runtime_cu12': 'cuda-12.8.1-eula',
    'nvidia_cufft_cu12': 'cuda-12.8.1-eula', 'nvidia_cufile_cu12': 'cuda-12.8.1-eula',
    'nvidia_curand_cu12': 'cuda-12.8.1-eula', 'nvidia_cusolver_cu12': 'cuda-12.8.1-eula',
    'nvidia_cusparse_cu12': 'cuda-12.8.1-eula', 'nvidia_nvjitlink_cu12': 'cuda-12.8.1-eula',
    'nvidia_nvshmem_cu12': 'nvshmem-v3.4.5-0-license',
    'nvidia_cutlass_dsl': 'cutlass-v4.5.0-eula', 'nvidia_cutlass_dsl_libs_base': 'cutlass-v4.5.0-eula',
}
PRIORITY = ['nvidia_cufile_cu12', 'nvidia_nvjitlink_cu12', 'nvidia_nvshmem_cu12', 'nvidia_cutlass_dsl_libs_base']
LIBRARY = re.compile(r'\.(so(\.\d+)*|a|bc)$')


def html_text(raw):
    text = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', raw.decode('utf-8', 'replace'))
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', text)).split()) + '\n'


def fetch_sources(get=None):
    get = get or (lambda url: urllib.request.urlopen(
        urllib.request.Request(url, headers={'User-Agent': 'arc-agi-3-licence-review'}), timeout=TIMEOUT).read(CAP))
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    index = {}
    for sid, s in SOURCES.items():
        raw = get(s['url'])
        raw_name = f"{sid}.{'html' if s['kind'] == 'html' else 'txt'}"
        (SOURCES_DIR / raw_name).write_bytes(raw)
        entry = {'url': s['url'], 'basis': s['basis'], 'retrieved_on': datetime.date.today().isoformat(),
                 'file': raw_name, 'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}
        if s['kind'] == 'html':
            text = html_text(raw).encode('utf-8')
            (SOURCES_DIR / f'{sid}.extracted.txt').write_bytes(text)
            entry.update(text_file=f'{sid}.extracted.txt', text_sha256=hashlib.sha256(text).hexdigest())
        index[sid] = entry
    SOURCES_INDEX.write_text(json.dumps(index, indent=1) + '\n', encoding='utf-8')
    return index


def source_text(index, sid, folder=None):
    """The text of a retained source, derived only from its hash-verified raw bytes. For HTML, the text is re-extracted
    from the verified page; the retained extraction must match both its recorded hash and that fresh extraction
    (so an altered extraction is refused even if its recorded hash was updated too), and the fresh one is used."""
    folder = folder or SOURCES_DIR
    entry = index[sid]
    raw = (folder / entry['file']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry['sha256']:
        raise SystemExit(f"{entry['file']} does not match its recorded SHA-256")
    if not entry['file'].endswith('.html'):
        return raw.decode('utf-8', 'replace')
    fresh = html_text(raw).encode('utf-8')
    if 'text_file' not in entry or 'text_sha256' not in entry:
        raise SystemExit(f'{sid}: the retained extraction or its recorded SHA-256 is missing')
    stored = (folder / entry['text_file']).read_bytes()
    if hashlib.sha256(stored).hexdigest() != entry['text_sha256']:
        raise SystemExit(f"{entry['text_file']} does not match its recorded SHA-256")
    if stored != fresh:
        raise SystemExit(f"{entry['text_file']} differs from a fresh extraction of the verified {entry['file']}")
    return fresh.decode('utf-8')


def attachment_a(text):
    """The Attachment A section (between the last 'Attachment A' heading before 'Attachment B' and that heading), or
    '' when the text has none."""
    end = text.rfind('Attachment B')
    start = text.rfind('Attachment A', 0, end if end >= 0 else len(text))
    if start < 0:
        return ''
    return text[start:end] if end > start else text[start:]


def normalised(member):
    return re.sub(r'\.so(\.\d+)*$', '.so', Path(member).name)


def listed(name, section):
    return bool(section) and re.search(r'(?<![\w.-])' + re.escape(name) + r'(?![\w-])', section) is not None


def wheel_facts(path):
    """(library members, bundled licence bytes by member, unconditional Requires-Dist lines) of a wheel."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        licences = [n for n in names if re.search(r'(?i)(^|/)licen[cs]e(\.txt|\.md)?$', n)]
        bundled = {n: z.read(n) for n in licences}
        metadata = next((z.read(n).decode('utf-8', 'replace') for n in names
                         if n.endswith('.dist-info/METADATA')), '')
    requires = [line.split(':', 1)[1].strip() for line in metadata.splitlines()
                if line.startswith('Requires-Dist:') and ';' not in line]
    return [n for n in names if LIBRARY.search(n)], bundled, requires


def requirement_name(requirement):
    return re.split(r'[\s<>=!~;\[(]', requirement.strip(), maxsplit=1)[0].lower().replace('-', '_')


def requirers(distribution, requires_by_wheel):
    """Who requires `distribution`: unconditional Requires-Dist of the reconciled wheels (followed transitively) and
    the closure report's records of the pre-release requirements."""
    closure = json.loads(CLOSURE.read_text(encoding='utf-8'))
    found, frontier, seen = set(), [distribution], set()
    while frontier:
        target = frontier.pop()
        if target in seen:
            continue
        seen.add(target)
        for p in closure.get('prerelease_accepted', []):
            if requirement_name(p['requirement']) == target:
                found.add(f"{p['required_by']} ({p['requirement']})")
        for wheel, requires in requires_by_wheel.items():
            for requirement in requires:
                if requirement_name(requirement) == target:
                    found.add(f'{wheel} (Requires-Dist: {requirement})')
                    frontier.append(wheel.split('==')[0].replace('-', '_'))
    return sorted(found)


def reconcile(wheelhouse):
    index = json.loads(SOURCES_INDEX.read_text(encoding='utf-8'))
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    official = {sid: source_text(index, sid) for sid in index}
    facts = {}
    for prefix in WHEELS:
        artifact = next(a for a in manifest['artifacts'] if a['filename'].split('-')[0] == prefix)
        path = wheelhouse / artifact['filename']
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact['sha256']:
            raise SystemExit(f"{artifact['filename']}: local wheel differs from the approved manifest")
        facts[prefix] = (artifact, wheel_facts(path))
    requires_by_wheel = {'{}=={}'.format(*a['filename'].split('-')[:2]).replace('_', '-'): f[2]
                         for a, f in facts.values()}
    rows = []
    for prefix, sid in WHEELS.items():
        artifact, (libraries, bundled, _) = facts[prefix]
        bundled_text = '\n'.join(b.decode('utf-8', 'replace') for b in bundled.values())
        bundled_section, official_section = attachment_a(bundled_text), attachment_a(official[sid])
        files = [{'member': m, 'name': normalised(m), 'in_bundled_attachment_a': listed(normalised(m), bundled_section),
                  'in_official_attachment_a': listed(normalised(m), official_section)} for m in libraries]
        rows.append({
            'artifact': artifact['filename'], 'sha256': artifact['sha256'], 'primary_source': sid,
            'bundled_licences': {n: hashlib.sha256(b).hexdigest() for n, b in bundled.items()},
            'bundled_identical_to_primary': any(b == (SOURCES_DIR / index[sid]['file']).read_bytes()
                                                for b in bundled.values()),
            'bundled_has_attachment_a': bool(bundled_section), 'official_has_attachment_a': bool(official_section),
            'library_files': files, 'required_by': requirers(prefix, requires_by_wheel)})
    return index, rows


FINDINGS = {
    'nvidia_cufile_cu12': (
        'Applicability discrepancy requiring review. The wheel\'s bundled License.txt (the same older CUDA EULA text in '
        'all eleven CUDA wheels) has no cuFile entry in Attachment A, but the official CUDA 12.8.1 EULA Attachment A '
        'lists libcufile.so, libcufile_rdma.so and their static libraries as distributable. Which text governs this '
        'wheel, and whether the proposed private-dataset distribution meets the official conditions (incorporation in '
        'an application with material additional functionality; no stand-alone distribution), is for qualified '
        'review. This is not a finding that no grant exists, and not a grant.'),
    'nvidia_nvjitlink_cu12': (
        'Applicability discrepancy requiring review. As for cuFile: the bundled text omits nvJitLink, while the '
        'official CUDA 12.8.1 EULA Attachment A lists libnvJitLink.so and libnvJitLink_static.a as distributable. '
        'The same applicability and distribution-condition questions apply.'),
    'nvidia_nvshmem_cu12': (
        'Separate product terms. The wheel bundles the CUDA Toolkit EULA, which does not mention NVSHMEM. The '
        'License.txt at NVIDIA/nvshmem tag v3.4.5-0 is the NVIDIA SDK licence plus an NVSHMEM supplement whose '
        'section 2 makes "any portion of the SDK" distributable, still subject to the SDK licence\'s distribution '
        'requirements (incorporation into an application with material additional functionality, accessed only by '
        'it; no stand-alone distribution). The current NVSHMEM SLA page carries the same supplement (v. July 11, '
        '2019) but is not version-specific. GitHub\'s repository metadata reports Apache-2.0 for the default branch, '
        'which differs from the tag\'s License.txt; the tag text is treated as the version-specific source. Which '
        'text governs the wheel, and whether the proposed distribution meets the conditions, is for qualified review.'),
    'nvidia_cutlass_dsl_libs_base': (
        'Bundled text confirmed as the primary text. The wheel\'s LICENSE is byte-identical to EULA.txt at '
        'NVIDIA/cutlass tags v4.2.0 through v4.5.0 and main (sha256 9ed3a034...). Section 1.1(d) grants distribution '
        'of "python files in the Software package in source format as incorporated into a software application"; '
        'the wheel also ships compiled files (listed below) for which no distribution grant has been identified in '
        'that text. Whether another grant covers them is for qualified review or NVIDIA clarification. The package '
        'is a required dependency (see required_by) and must not be dropped without an explicitly revised dependency '
        'set and fresh validation.'),
}


def render(index, rows):
    lines = ['# NVIDIA licence reconciliation (review preparation; not a grant)', '',
             'Applicability facts and open questions for the designated reviewer. Nothing here grants or refuses '
             'redistribution permission.', '', '## Primary sources retained', '',
             '| Source | URL | Retrieved | SHA-256 | Basis |', '|---|---|---|---|---|']
    for sid, e in index.items():
        lines.append(f"| `{sid}` | {e['url']} | {e['retrieved_on']} | `{e['sha256'][:12]}…` | {e['basis']} |")
    by_prefix = {r['artifact'].split('-')[0]: r for r in rows}
    lines += ['', '## Priority artifacts', '']
    for prefix in PRIORITY:
        r = by_prefix[prefix]
        lines += [f"### `{r['artifact']}`", '', FINDINGS[prefix], '',
                  f"- Primary source: `{r['primary_source']}`; bundled licence identical to it: "
                  f"{'yes' if r['bundled_identical_to_primary'] else 'no'}",
                  f"- Bundled licence files: " + ', '.join(f'`{n}` (`{h[:12]}…`)' for n, h in
                                                           r['bundled_licences'].items())]
        if r['required_by']:
            lines.append('- Required by: ' + '; '.join(r['required_by']))
        lines += ['', '| Library file | In bundled Attachment A | In official Attachment A |', '|---|---|---|']
        for f in r['library_files']:
            lines.append(f"| `{f['member']}` | {'yes' if f['in_bundled_attachment_a'] else 'no'} | "
                         f"{'yes' if f['in_official_attachment_a'] else 'no'} |")
        lines.append('')
    lines += ['## All reconciled wheels', '', '| Wheel | Library files | Listed (bundled) | Listed (official) |',
              '|---|---|---|---|']
    for r in rows:
        files = r['library_files']
        lines.append(f"| `{r['artifact']}` | {len(files)} | {sum(f['in_bundled_attachment_a'] for f in files)} | "
                     f"{sum(f['in_official_attachment_a'] for f in files)} |")
    lines += ['', 'Name matching is a string check of library basenames (version suffixes removed) against the '
              'Attachment A text; it does not decide which text governs, whether headers or other files are covered, '
              'or whether a distribution meets the conditions.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--fetch', action='store_true', help='retain the primary sources (network)')
    parser.add_argument('--wheelhouse', type=Path, default=DEFAULT_WHEELHOUSE)
    args = parser.parse_args()
    if args.fetch:
        fetch_sources()
    index, rows = reconcile(args.wheelhouse)
    OUT_JSON.write_text(json.dumps({'sources': index, 'findings': FINDINGS, 'wheels': rows}, indent=1) + '\n',
                        encoding='utf-8')
    OUT_MD.write_text(render(index, rows), encoding='utf-8')
    for r in rows:
        files = r['library_files']
        print(f"{r['artifact'][:44]:44} libs={len(files):3} bundled={sum(f['in_bundled_attachment_a'] for f in files):3} "
              f"official={sum(f['in_official_attachment_a'] for f in files):3}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
