"""Derive the post-run evidence-comprehension v2 scripts from v1's, without touching the frozen derivation.

scripts/derive_evidence_comprehension_v2.py is a hash-bound review document of package r1 (lock `de9642c6…82a3`)
and stays byte-identical to what was approved. Post-run tooling that did not exist at review time is derived
here with the same global renames (imported from the frozen script) and its own counted substitutions.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.derive_evidence_comprehension_v2 import GLOBAL  # noqa: E402  (the frozen renames, unchanged)

BANNER = ('# Derived from {source} by scripts/derive_evidence_comprehension_v2_postrun.py; '
          'edit the derivation, not this file.\n')
DERIVED = {
    'scripts/archive_evidence_comprehension_v2_live.py': ('scripts/archive_evidence_comprehension_v1_live.py', (
        ("ATTEMPT = 'ecv2-4458251ee9aa4e1b9ca39844a1c3a70b'", "ATTEMPT = 'ecv2-65759c16cf1648a19f8bf0128a070826'", 1),
        ("'notebooks/evidence-comprehension-v2-review-r3/review-source-lock.json'",
         "'notebooks/evidence-comprehension-v2-review-r1/review-source-lock.json'", 1),
    )),
}


def derive_one(target):
    source, rules = DERIVED[target]
    text = (ROOT / source).read_text(encoding='utf-8')
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for old, new, count in rules:
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    if 'evidence_comprehension_v1' in text or 'ecv1-' in text:
        raise ValueError(f'{target}: unexpected remaining v1 reference')
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
