"""Audit target install-report metadata and frozen game wheels without GPU compute."""
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import zipfile
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def audit(packages, environment):
    active = {name: {''} for name in packages}
    changed = True
    while changed:
        changed = False
        for name, metadata in packages.items():
            for raw in metadata.get('requires_dist', []):
                req = Requirement(raw)
                if req.marker and not any(req.marker.evaluate({**environment, 'extra': extra})
                                          for extra in active[name]):
                    continue
                target = canonicalize_name(req.name)
                if target in active:
                    new = set(req.extras)-active[target]
                    if new:
                        active[target].update(new)
                        changed = True
    errors = []
    for name, metadata in packages.items():
        for raw in metadata.get('requires_dist', []):
            req = Requirement(raw)
            if req.marker and not any(req.marker.evaluate({**environment, 'extra': extra})
                                      for extra in active[name]):
                continue
            found = packages.get(canonicalize_name(req.name))
            if found is None or not req.specifier.contains(found['version'], prereleases=True):
                errors.append({'package': name, 'requirement': raw,
                               'installed': found['version'] if found else None})
    return {'package_count': len(packages), 'passed': not errors, 'conflicts': errors}


def main():
    run = ROOT/'reports/runs/phase4-v6-install-r3-20260917'
    report_path = run/'output/phase4-v6-install-check/bootstrap/install_model_service.json'
    evaluation = json.loads((ROOT/'reports/phase4_v6_install_r3_evaluation.json').read_text())
    expected = evaluation['evidence'][report_path.relative_to(run).as_posix()]['sha256']
    assert hashlib.sha256(report_path.read_bytes()).hexdigest() == expected
    report = json.loads(report_path.read_text(encoding='utf-8'))
    model = {canonicalize_name(row['metadata']['name']): row['metadata'] for row in report['install']}
    manifest = json.loads((ROOT/'reports/phase4_v2_offline_package.json').read_text())
    game = {}
    folder = ROOT/'reports/runs/phase4-v2-assets/arc_agi_3_wheels'
    for name, info in manifest['files'].items():
        if not name.startswith('wheels/'):
            continue
        path = folder/Path(name).name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == info['sha256']
        with zipfile.ZipFile(path) as bundle:
            entry = next(n for n in bundle.namelist() if n.endswith('.dist-info/METADATA'))
            metadata = BytesParser().parsebytes(bundle.read(entry))
        game[canonicalize_name(metadata['Name'])] = {
            'name': metadata['Name'], 'version': metadata['Version'],
            'requires_dist': metadata.get_all('Requires-Dist', [])}
    result = {'scope': 'Static metadata dependency audit; not installation or GPU execution',
              'target': report['environment'], 'model_report_sha256': expected,
              'model': audit(model, report['environment']),
              'game_inventory': audit(game, report['environment']),
              'combined': audit({**model, **game}, report['environment']),
              'model_numpy': model['numpy']['version'], 'game_numpy': game['numpy']['version'],
              'gpu_run_launched': False}
    (ROOT/'reports/phase4_split_dependency_audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    assert result['model']['passed'] and result['game_inventory']['passed']
    assert not result['combined']['passed']


if __name__ == '__main__':
    main()
