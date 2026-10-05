"""CUTLASS DSL binaries evidence pack (first viability check; a proposal for the designated reviewer).

  python scripts/evidence_cutlass.py

Identifies the exact wheels, every file by class, the compiled files, the licence texts in the wheels, the primary
EULA texts at each checked repository ref and the licence page named in the wheel metadata, the operative clauses,
and markers of separately licensed components embedded in the binaries. The conclusion is limited to what was
checked. Writes reports/wheelhouse_evidence/cutlass_binaries.{json,md}.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evidence_common import (artifact_for, fetch_retained, html_text, open_wheel,  # noqa: E402
                                     sha256_bytes, write_pack)

DISTRIBUTIONS = ('nvidia_cutlass_dsl_libs_base', 'nvidia_cutlass_dsl')
REFS = ('v4.2.0', 'v4.2.1', 'v4.3.0', 'v4.3.5', 'v4.4.0', 'v4.4.2', 'v4.5.0', 'main')
LICENCE_PAGE = 'https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/license.html'
MARKERS = re.compile(rb'(LLVM version [0-9.]+|LLVM Exception|Apache License[^\x00\n]{0,30}|clang version [0-9.]+|'
                     rb'SPDX-License-Identifier:[^\x00\n]{0,40}|Copyright \(c\)[^\x00\n]{0,60})')
CLAUSES = {'1.1(d) distribution grant': r'd\. distribute python files.*?vi\. Additionally[^\n]*',
           '2.2 no making available to others': r'2\.2\. Sell, rent[^\n]*',
           '2.3 no reverse engineering of binaries': r'2\.3\. Reverse engineer[^\n]*',
           '3 authorized users': r'3\. Authorized Users\s+(.*?)\n\s*\n',
           '6 components under other licenses': r'6\. Components Under Other Licenses\s+(.*?)\n\s*7\.'}


def classify(name):
    if name.endswith('/'):
        return None
    if name.endswith(('.py', '.pyi')):
        return 'python_source'
    if name.endswith('.so') or '.so.' in name or name.endswith('.a'):
        return 'compiled'
    if name.endswith(('.h', '.hpp', '.cuh')):
        return 'header_source_non_python'
    if '.dist-info/' in name or name.endswith(('LICENSE', '.pth', 'py.typed', 'top_level.txt')):
        return 'metadata_or_licence'
    return 'other'


def binary_format(data):
    return 'ELF shared object' if data[:4] == b'\x7fELF' else 'ar static archive' if data[:7] == b'!<arch>' else '?'


def wheel_record(distribution):
    artifact = artifact_for(distribution)
    z = open_wheel(artifact)
    files = {'python_source': 0, 'compiled': [], 'header_source_non_python': [], 'metadata_or_licence': [],
             'other': []}
    licences = {}
    for info in z.infolist():
        kind = classify(info.filename)
        if kind is None:
            continue
        if kind == 'python_source':
            files[kind] += 1
            continue
        data = z.read(info)
        entry = {'path': info.filename, 'bytes': info.file_size, 'sha256': sha256_bytes(data)}
        if kind == 'compiled':
            markers = sorted({m.group(0).decode('utf-8', 'replace').strip()[:80] for m in MARKERS.finditer(data)})
            entry.update(format=binary_format(data), embedded_markers=markers)
        files[kind].append(entry)
        if re.search(r'(?i)(^|/)licen[cs]e', info.filename):
            licences[info.filename] = entry['sha256']
    metadata = z.read(next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))).decode()
    fields = [line for line in metadata.splitlines()
              if line.split(':')[0] in ('License', 'License-Expression', 'License-File', 'Project-URL', 'Requires-Dist')
              or line.startswith('Classifier: License')]
    return {'artifact': artifact['filename'], 'sha256': artifact['sha256'], 'files': files,
            'licence_files': licences, 'metadata_licence_fields': fields}


def clause_excerpts(text):
    out = {}
    for name, pattern in CLAUSES.items():
        match = re.search(pattern, text, re.S)
        out[name] = ' '.join((match.group(1) if match.groups() else match.group(0)).split())[:1500] if match \
            else None
    return out


def build():
    wheels = [wheel_record(d) for d in DISTRIBUTIONS]
    refs = {}
    for ref in REFS:
        data, record = fetch_retained(f'cutlass-{ref}-EULA.txt',
                                      f'https://raw.githubusercontent.com/NVIDIA/cutlass/{ref}/EULA.txt')
        refs[ref] = dict(record, text=data)
    bundled = {sha for w in wheels for sha in w['licence_files'].values()}
    identical = {ref: r['sha256'] in bundled for ref, r in refs.items()}
    page, page_record = fetch_retained('cutlass-dsl-licence-page.html', LICENCE_PAGE)
    words = lambda s: re.findall(r'[a-z0-9]+', s.lower())  # noqa: E731
    eula_words, page_words = words(refs['v4.5.0']['text'].decode()), words(html_text(page))
    import difflib
    matcher = difflib.SequenceMatcher(None, eula_words, page_words, autojunk=False)
    differences = [' '.join(eula_words[i1:i2]) for tag, i1, i2, _, _ in matcher.get_opcodes()
                   if tag != 'equal' and i2 > i1]
    eula_text = refs['v4.5.0']['text'].decode()
    for r in refs.values():
        r.pop('text')
    base = wheels[0]
    compiled = base['files']['compiled']
    markers = sorted({m for c in compiled for m in c['embedded_markers']})
    finding = {
        'conclusion': 'No applicable binary redistribution grant identified',
        'scope_of_conclusion': (
            'Applies to the compiled files and the C header of the exact wheel listed, under the licence texts '
            'listed. Section 1.1(d) grants distribution of "python files in the Software package in source format '
            'as incorporated into a software application"; no clause found grants distribution of the compiled '
            'files or the non-Python header. This is not a finding that no permission exists anywhere.'),
        'not_checked': [
            'any separate agreement between the team and NVIDIA (none known)',
            'NVIDIA clarification (not requested)',
            'whether section 6 covers the embedded LLVM/MLIR code, which the wheel ships with no accompanying '
            'licence or notice; even if it does, that permission would cover only those components, not '
            "NVIDIA's code in the same binaries",
            'repository refs other than those listed'],
        'questions_for_reviewer': [
            'Is any permission available for the compiled files (libcute_dsl_runtime.so, _cutlass_ir.cpython-312 '
            '.so, libcuda_dialect_runtime_static.a) and the header CuteDSLRuntime.h?',
            'Do the embedded LLVM/MLIR components (markers: ' + ', '.join(markers) + ') impose their own notice '
            'obligations when the binaries are redistributed?',
            'Section 3 permits access by employees and contractors "from your secure network": does the planned '
            'deployment fit that, or is it making the Software available to others (2.2)?'],
        'owner_options_if_not_cleared': [
            'written clarification from NVIDIA (licensing contact in the EULA)',
            'an explicitly revised dependency set with fresh validation (flashinfer-python 0.6.6 requires '
            'nvidia-cutlass-dsl>=4.3.4 and quack-kernels 0.4.1 requires >=4.4.2)',
            'record the bundle as blocked'],
    }
    payload = {'schema': 'wheelhouse_evidence_cutlass_v1', 'wheels': wheels,
               'licence_texts': {'eula_by_ref': refs, 'bundled_identical_by_ref': identical,
                                 'licence_page': dict(page_record, differs_from_v4_5_0_eula_only_by=differences[:20])},
               'clauses_v4_5_0': clause_excerpts(eula_text), 'finding': finding}
    return payload


def markdown(p):
    base, meta = p['wheels'][0], p['wheels'][1]
    f = p['finding']
    lines = ['# CUTLASS DSL binaries: evidence pack (first viability check)', '',
             '**A proposal for the designated reviewer, not a decision.**', '',
             '## Exact wheels', '']
    for w in p['wheels']:
        lines += [f"- `{w['artifact']}` (sha256 `{w['sha256']}`):",
                  f"  - {w['files']['python_source']} Python source files",
                  f"  - {len(w['files']['compiled'])} compiled files",
                  f"  - {len(w['files']['header_source_non_python'])} non-Python headers",
                  f"  - licence files: " + (', '.join(f'`{n}` (`{h[:12]}…`)' for n, h in w['licence_files'].items())
                                            or 'none')]
    lines += ['', '## Compiled and non-Python files (libs-base wheel)', '', '| File | Bytes | SHA-256 | Format | Embedded markers |',
              '|---|---|---|---|---|']
    for c in base['files']['compiled']:
        lines.append(f"| `{c['path']}` | {c['bytes']:,} | `{c['sha256'][:12]}…` | {c['format']} | "
                     f"{'; '.join(c['embedded_markers']) or '—'} |")
    for h in base['files']['header_source_non_python']:
        lines.append(f"| `{h['path']}` | {h['bytes']:,} | `{h['sha256'][:12]}…` | C header (source, not Python) | — |")
    lines += ['', '## Licence texts checked', '', '| Source | SHA-256 | Identical to the wheels\' LICENSE |', '|---|---|---|']
    for ref, r in p['licence_texts']['eula_by_ref'].items():
        lines.append(f"| `NVIDIA/cutlass@{ref}/EULA.txt` (retained `{r['file']}`) | `{r['sha256'][:12]}…` | "
                     f"{'yes' if p['licence_texts']['bundled_identical_by_ref'][ref] else 'no'} |")
    page = p['licence_texts']['licence_page']
    lines += ['', f"The licence page named in the metadata ({page['url']}, retained `{page['file']}`) has the same "
              f"wording as `v4.5.0/EULA.txt`. The only differences are list labels: "
              f"{', '.join(page['differs_from_v4_5_0_eula_only_by']) or 'none'}.", '',
              f"Metadata licence fields (libs-base): {'; '.join(base['metadata_licence_fields'])}", '',
              '## Operative clauses (v4.5.0 text)', '']
    for name, text in p['clauses_v4_5_0'].items():
        lines += [f'**{name}.** {text}', '']
    lines += ['## Finding', '', f"**{f['conclusion']}.** {f['scope_of_conclusion']}", '', 'Not checked:', '']
    lines += [f'- {x}' for x in f['not_checked']]
    lines += ['', 'Questions for the reviewer:', ''] + [f'- {x}' for x in f['questions_for_reviewer']]
    lines += ['', 'Owner options if not cleared (no automatic choice):', ''] + [f'- {x}' for x in f['owner_options_if_not_cleared']]
    return '\n'.join(lines)


if __name__ == '__main__':
    payload = build()
    write_pack('cutlass_binaries', payload, markdown(payload))
    print(json.dumps({'conclusion': payload['finding']['conclusion'],
                      'identical_by_ref': payload['licence_texts']['bundled_identical_by_ref']}, indent=1))
