"""CPU-only reconstruction, including semantic comparison beyond hash manifests."""
import hashlib
import json
import gzip
from pathlib import Path
from . import fixtures as FX, independent_keys as IK, writer as W, schema as S


def digest(value):
    return hashlib.sha256(S.compact(value).encode()).hexdigest()


def validate_case(case):
    # Rebuild from declared development identity; updated hashes cannot legitimise
    # forged evidence. Reserved final cases require separate generation review.
    if case.get('split') != 'development':
        raise ValueError('replay only accepts the frozen development partition')
    expected = FX.build(case['family'], case['group'], case['delay'])
    if case != expected:
        raise ValueError('scenario differs from frozen construction')
    if IK.derive_facts(case['raws']) != W.source_facts(case):
        raise ValueError('independent fact derivations disagree')
    return True


def verify_directory(path):
    root = Path(path)
    manifest = json.loads((root / 'manifest.json').read_text())
    for name, expected in manifest['sha256'].items():
        p = Path(name)
        if p.is_absolute() or '..' in p.parts:
            raise ValueError('unsafe manifest path')
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('manifest mismatch: ' + name)
    from . import dependencies as D
    D.verify_bindings(root, Path(__file__).resolve().parents[2])
    cases = json.loads(gzip.decompress((root / 'benchmark.json.gz').read_bytes()))
    for case in cases:
        validate_case(case)
    if len(cases) != 144 or len({(c['family'], c['group'], c['delay']) for c in cases}) != 144:
        raise ValueError('missing or duplicated development case')
    stored = json.loads((root / 'independent_keys.json').read_text())
    expected = [{'scenario_id': c['scenario_id'], 'delay': c['delay'], 'keys': IK.keys(c)} for c in cases]
    if stored != expected:
        raise ValueError('answer keys differ from independent reconstruction')
    # The manifest is not an oracle. Reconstruct every request, selected package,
    # token audit and verdict so edited renderings with refreshed hashes fail too.
    from .build import artifacts
    reconstructed, _, _ = artifacts()
    for name, data in reconstructed.items():
        if (root / name).read_bytes() != data:
            raise ValueError('semantic package reconstruction differs: ' + name)
    if {p.name for p in root.iterdir() if p.is_file()} != set(reconstructed):
        raise ValueError('unexpected package file')
    return {'cases': len(cases), 'clusters': len({c['scenario_id'] for c in cases}), 'verified': True}


def main():
    import argparse
    p = argparse.ArgumentParser(description='Offline semantic replay; no model or network calls')
    p.add_argument('--path', default='reports/conditional_transfer_v1/review_package')
    args = p.parse_args()
    print(S.compact(verify_directory(args.path)))


if __name__ == '__main__':
    main()
