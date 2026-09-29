"""Derive the post-run evidence-comprehension v3 scripts, without touching the hash-bound v3 derivation.

scripts/derive_evidence_comprehension_v3.py is a review document bound by v3's package lock (`66713c62…5cfd`) and
stays byte-identical. Post-run tooling is derived here from v2's post-run script, with v3's renames (imported from
the frozen v3 derivation, unchanged) and counted substitutions.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.derive_evidence_comprehension_v3 import GLOBAL  # noqa: E402  (the frozen v2 -> v3 renames)

BANNER = ('# Derived from {source} by scripts/derive_evidence_comprehension_v3_postrun.py; '
          'edit the derivation, not this file.\n')
DERIVED = {
    'scripts/archive_evidence_comprehension_v3_live.py': ('scripts/archive_evidence_comprehension_v2_live.py', (
        ("ATTEMPT = 'ecv3-65759c16cf1648a19f8bf0128a070826'", "ATTEMPT = 'ecv3-089bf11fd38c41f88808794a134a3d56'", 1),
    )),
}


def derive_one(target):
    source, rules = DERIVED[target]
    lines = (ROOT / source).read_text(encoding='utf-8').splitlines(keepends=True)
    if lines and lines[0].startswith('# Derived from '):
        lines = lines[1:]
    text = ''.join(lines)
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for old, new, count in rules:
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    if 'evidence_comprehension_v2' in text or 'ecv2-' in text or '65759c16' in text:
        raise ValueError(f'{target}: unexpected remaining v2 reference')
    return BANNER.format(source=source) + text


def stale():
    return [t for t in DERIVED if not (ROOT / t).is_file()
            or (ROOT / t).read_text(encoding='utf-8') != derive_one(t)]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    if parser.parse_args().check:
        drift = stale()
        if drift:
            raise SystemExit('post-run derived files differ: ' + ', '.join(drift))
        print(f'{len(DERIVED)} post-run derived file(s) match')
    else:
        for target in DERIVED:
            (ROOT / target).write_text(derive_one(target), encoding='utf-8', newline='\n')
        print(f'wrote {len(DERIVED)} post-run derived file(s)')
