"""Licence-evidence extraction for the R2 wheelhouse review (reads wheel archives as data; never installs or runs code).

For every artifact of the approved download manifest: verify the downloaded wheel's size and SHA-256, list the
licence material it ships (dist-info LICENSE/NOTICE/COPYING files, PEP 639 dist-info/licenses/, and licence or notice
files elsewhere in the archive), copy the full texts to a directory OUTSIDE the repository, and record an index:
file paths, sizes and hashes, heuristically detected licence families, review flags, and short excerpts of clauses
that mention redistribution for proprietary or unrecognised texts.

The detection is a reading aid for the human reviewer, not a legal conclusion. Every row stays 'unresolved' in
reports/wheelhouse_license_review.csv until the owner decides it.

  python scripts/extract_wheelhouse_licenses.py --wheels ~/.local/share/agi/wheelhouse-r2 \
      --texts ~/.local/share/agi/wheelhouse-r2-licenses
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.download_wheelhouse import APPROVED_MANIFEST_SHA256, load_manifest  # noqa: E402
MANIFEST = ROOT / 'reports/wheelhouse_download_manifest.json'
INDEX_JSON = ROOT / 'reports/wheelhouse_license_evidence.json'
INDEX_MD = ROOT / 'reports/wheelhouse_license_evidence.md'
MAX_TEXT = 4 * 1024 ** 2
NAME = re.compile(r'(^|[-_.])(licen[cs]e|copying|notice|eula|copyright|third[-_]?party[-_]?notices?)([-_.]|$)', re.I)

FAMILIES = [  # (family, all of these phrases, none of these phrases); matched case-insensitively
    ('Apache-2.0', ['apache license', 'version 2.0'], []),
    ('MIT', ['permission is hereby granted, free of charge'], []),
    ('BSD-3-Clause', ['redistribution and use in source and binary forms', 'neither the name'], []),
    ('BSD-2-Clause', ['redistribution and use in source and binary forms'], ['neither the name']),
    ('PSF-2.0', ['python software foundation license'], []),
    ('MPL-2.0', ['mozilla public license'], []),
    ('LGPL', ['gnu lesser general public license'], []),
    ('GPL', ['gnu general public license'], ['gnu lesser general public license']),
    ('ISC', ['permission to use, copy, modify, and/or distribute'], []),
    ('Zlib', ['this software is provided \'as-is\'', 'altered source versions must be plainly marked'], []),
    ('Unlicense', ['this is free and unencumbered software released into the public domain'], []),
    ('CC0', ['creative commons', 'cc0'], []),
    ('NVIDIA-proprietary', ['nvidia', 'license agreement'], []),
    ('NVIDIA-proprietary', ['nvidia', 'end user license'], []),
]
COPYLEFT = {'LGPL', 'GPL', 'MPL-2.0'}


class ExtractError(Exception):
    pass


def is_licence_member(name):
    if name.endswith('/'):
        return False
    parts = name.split('/')
    if len(parts) >= 3 and parts[0].endswith('.dist-info') and parts[1] == 'licenses':
        return True
    return bool(NAME.search(parts[-1]))


def families(text):
    low = ' '.join(text.lower().split())
    found = []
    for family, need, avoid in FAMILIES:
        if all(n in low for n in need) and not any(a in low for a in avoid) and family not in found:
            found.append(family)
    return found


def redistribution_excerpts(text, limit=4, width=300):
    flat = ' '.join(text.split())
    out = []
    for sentence in re.split(r'(?<=[.;])\s+', flat):
        if re.search(r'redistribut|distribut(e|ion) .*(binary|software|sdk|object)', sentence, re.I):
            out.append(sentence[:width])
        if len(out) >= limit:
            break
    return out


def safe_target(texts, wheel, member):
    target = (texts / wheel / member).resolve()
    if texts.resolve() not in target.parents:
        raise ExtractError(f'unsafe archive path {member!r} in {wheel}')
    return target


def extract(manifest, wheels, texts):
    rows = []
    for a in sorted(manifest['artifacts'], key=lambda a: a['filename']):
        path = wheels / a['filename']
        data = path.read_bytes()
        if len(data) != a['size'] or hashlib.sha256(data).hexdigest() != a['sha256']:
            raise ExtractError(f"{a['filename']} does not match the manifest")
        name, version = a['filename'][:-4].split('-')[:2]
        files, fams, excerpts = [], [], []
        metadata = ''
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.filename.endswith('.dist-info/METADATA'):
                    metadata = z.read(info).decode('utf-8', 'replace')
                if not is_licence_member(info.filename) or info.file_size > MAX_TEXT:
                    continue
                raw = z.read(info)
                text = raw.decode('utf-8', 'replace')
                target = safe_target(texts, a['filename'], info.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                found = families(text)
                files.append({'path': info.filename, 'size': info.file_size,
                              'sha256': hashlib.sha256(raw).hexdigest(), 'families': found})
                for f in found:
                    if f not in fams:
                        fams.append(f)
                if not found or 'NVIDIA-proprietary' in found:
                    excerpts += [{'file': info.filename, 'text': e} for e in redistribution_excerpts(text)]
        declared = [l.split(':', 1)[1].strip() for l in metadata.splitlines()
                    if l.startswith(('License-Expression:', 'License:')) and len(l) < 200]
        declared += [l.split('::', 1)[1].strip() for l in metadata.splitlines()
                     if l.startswith('Classifier: License ::')]
        flags = []
        if not files:
            flags.append('no_licence_file_in_wheel')
        if any(re.search(r'\b(L?GPL|MPL)\b|general public license|mozilla public', d, re.I) for d in declared):
            flags.append('declared_copyleft')
        if any(f in COPYLEFT for f in fams):
            flags.append('copyleft_terms_present')
        if 'NVIDIA-proprietary' in fams or any(re.search(r'nvidia|proprietary', d, re.I) for d in declared):
            flags.append('proprietary_terms_present')
        if files and not fams and 'proprietary_terms_present' not in flags:
            flags.append('unrecognised_licence_text')
        rows.append({'artifact': a['filename'], 'distribution': name, 'version': version,
                     'metadata_declared': declared, 'detected_families': fams, 'flags': flags,
                     'licence_files': files, 'redistribution_excerpts': excerpts[:6]})
    return rows


def render(rows):
    from collections import Counter
    flag_counts = Counter(f for r in rows for f in r['flags'])
    fam_counts = Counter(f for r in rows for f in r['detected_families'])
    lines = ['# Wheelhouse R2 licence evidence (reading aid, not a legal review)', '',
             'Extracted from the 174 downloaded, hash-verified wheels of manifest `3691cb88…d546` by '
             '`scripts/extract_wheelhouse_licenses.py`. Full texts are kept outside the repository '
             '(`~/.local/share/agi/wheelhouse-r2-licenses/`). Family detection is heuristic. Every row remains '
             '`unresolved` in `reports/wheelhouse_license_review.csv` until the owner (dcw06) decides it.', '',
             '**How to read the families and flags.** A family is listed when its licence text appears anywhere in '
             'the wheel’s licence files. That includes bundled third-party notices (for example the NVIDIA '
             '`License.txt` files and torch’s `NOTICE` reproduce the licences of components they include) and mere '
             'mentions (the PSF licence text mentions GPL compatibility, so PSF-licensed packages show `GPL`). '
             '`declared_copyleft` is the stronger signal: the package’s own metadata declares an MPL, LGPL or GPL '
             'licence. `copyleft_terms_present` only says such text appears somewhere and needs reading.', '',
             '## Summary', '', f'- Wheels: {len(rows)}',
             f"- Wheels shipping licence material: {sum(1 for r in rows if r['licence_files'])}",
             f"- Licence files found: {sum(len(r['licence_files']) for r in rows)}", '',
             '| Detected family | Wheels |', '|---|---|']
    lines += [f'| {f} | {n} |' for f, n in sorted(fam_counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    lines += ['', '| Review flag | Wheels |', '|---|---|']
    lines += [f'| `{f}` | {n} |' for f, n in sorted(flag_counts.items())]
    for flag, title in (('proprietary_terms_present', 'Proprietary terms (decide redistribution first)'),
                        ('declared_copyleft', 'Package declares a copyleft licence itself'),
                        ('copyleft_terms_present', 'Copyleft terms present (notice and source obligations to check)'),
                        ('unrecognised_licence_text', 'Licence text not recognised by the heuristics'),
                        ('no_licence_file_in_wheel', 'No licence file in the wheel (rely on metadata/upstream)')):
        flagged = [r for r in rows if flag in r['flags']]
        lines += ['', f'## {title} ({len(flagged)})', '']
        for r in flagged:
            files = ', '.join(f"`{f['path'].split('/')[-1]}`" for f in r['licence_files'][:4]) or 'none'
            lines.append(f"- **{r['distribution']} {r['version']}** — declared: "
                         f"{'; '.join(r['metadata_declared']) or 'none'}; detected: "
                         f"{', '.join(r['detected_families']) or 'none'}; files: {files}")
            for e in r['redistribution_excerpts'][:2]:
                lines.append(f"  - _{e['file'].split('/')[-1]}_: “{e['text']}”")
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--wheels', required=True)
    parser.add_argument('--texts', required=True)
    args = parser.parse_args(argv)
    wheels, texts = Path(args.wheels).resolve(), Path(args.texts).resolve()
    if texts == ROOT.resolve() or ROOT.resolve() in texts.parents:
        raise SystemExit('refused: licence texts must be kept outside the repository')
    manifest = load_manifest(MANIFEST, APPROVED_MANIFEST_SHA256)  # recomputed digest and structure
    if wheels == texts or wheels in texts.parents or texts in wheels.parents:
        raise SystemExit('refused: the licence text directory overlaps the wheel directory')
    rows = extract(manifest, wheels, texts)
    INDEX_JSON.write_text(json.dumps({'manifest_sha256': manifest['manifest_sha256'], 'wheels': rows},
                                     indent=1, sort_keys=True) + '\n', encoding='utf-8')
    INDEX_MD.write_text(render(rows), encoding='utf-8')
    print(json.dumps({'wheels': len(rows), 'with_licence_files': sum(1 for r in rows if r['licence_files']),
                      'flags': {f: sum(1 for r in rows if f in r['flags'])
                                for f in sorted({f for r in rows for f in r['flags']})}}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
