"""Independent validation of split-install receipts and retained command evidence."""
import base64
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from urllib.parse import unquote, urlparse

from research.stagnation_supervision_runtime_v2.authority import ROOT

MODEL_PHASES = ('venv creation', 'offline install', 'pip check', 'package checks', 'model metadata and isolation')
GAME_PHASES = ('host_inventory', 'create_empty_venv', 'verify_empty_isolated_venv', 'host_pip_targets_empty_venv',
               'resolve_game', 'install_game', 'dependency_check', 'installed_inventory', 'game_imports', 'game_metadata')


def require(condition, message):
    if not condition:
        raise ValueError('installation evidence: ' + message)


def _number(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0, 'invalid timing')
    return value


def _read(root, name):
    path = Path(root) / name
    require(path.is_file() and not path.is_symlink() and path.stat().st_size < 4*1024**2,
            'missing or unsafe ' + name)
    return json.loads(path.read_bytes())


def validate_installation(root, first, outer, *, mode):
    if first.get('installation') == 'none':
        require(mode == 'rehearsal' and not (Path(root) / 'control/installation.json').exists(),
                'unstaged rehearsal must not claim an installation')
        return {'verified': True, 'scope': 'unstaged_rehearsal'}
    protocol = json.loads((ROOT / 'research/stagnation_supervision_runtime_v2/protocol.json').read_bytes())
    receipt = _read(root, 'control/installation.json')
    require(receipt.get('passed') is True and receipt.get('error') is None, 'installation did not pass')
    require(receipt.get('scope') == 'runtime_v2_split_install' and receipt.get('runtime_binding') == protocol['scope'],
            'scope/runtime identity')
    require(receipt.get('runtime_identity') == {k: protocol[k] for k in ('dataset', 'bundle', 'runtime')}
            and receipt.get('competition_manifest_sha256') == protocol['competition']['manifest_sha256'],
            'frozen bundle/runtime/competition identity')
    require(receipt.get('first_cell_monotonic') == first['first_cell_monotonic'], 'first-cell origin')
    budget = receipt.get('installation_seconds')
    require(type(budget) is int and budget > 0 and type(receipt.get('override')) is bool, 'installation budget')
    if mode == 'live':
        require(budget == protocol['limits']['installation_seconds'] and receipt['override'] is False
                and receipt.get('evidence_class') == 'first_cell', 'live timing override/class')
    else:
        require(receipt.get('evidence_class') == ('cpu_rehearsal_not_target_timing' if receipt['override'] else 'first_cell'),
                'rehearsal evidence class')
    require(_number(receipt.get('elapsed_seconds')) < budget
            and receipt['elapsed_seconds'] <= _number(outer['worker_released_seconds']), 'installation timing')
    bundle = receipt.get('model_bundle', {})
    require(bundle.get('integrity_passed') is True and bundle.get('wheel_bytes_verified') == protocol['bundle']['wheel_count']
            and bundle.get('trusted_artifacts_sha256') == protocol['bundle']['approved_manifest_sha256']
            and bundle.get('installation_requirements_sha256') == protocol['bundle']['requirements_lock_sha256']
            and bundle.get('dataset_ref') == protocol['dataset']['ref']
            and type(bundle.get('requested_version')) is int
            and bundle.get('requested_version') == protocol['dataset']['version'], 'mounted wheel integrity binding')
    require(type(receipt.get('game_wheels')) is int and receipt['game_wheels'] == protocol['competition']['game_wheel_count'],
            'game wheel inventory')
    torch = json.loads((ROOT / 'reports/phase4_torch_wheel_inspection.json').read_bytes())
    contract = receipt.get('torch_contract', {})
    require(all(contract.get(k) == torch[k] for k in ('distribution_name', 'distribution_version', 'runtime_build',
                    'metadata_sha256', 'version_source_sha256', 'requires_dist')), 'torch wheel contract')
    interpreters = receipt.get('interpreters', {})
    require(set(interpreters) == {'game', 'model'} and interpreters['game'] != interpreters['model'],
            'distinct installed interpreters')
    for role, phases in (('model', MODEL_PHASES), ('game', GAME_PHASES)):
        installed = receipt.get(role + '_install', {})
        require(installed.get('versions') == protocol['runtime'][role]['packages'], role + ' exact versions')
        imports = protocol['runtime']['model']['imports'] if role == 'model' else ['arc_agi', 'arcengine', 'numpy']
        require(set(installed.get('imports', {})) == set(imports)
                and all(isinstance(p, str) and str(Path(p)).startswith(str(Path(interpreters[role]).parent.parent) + '/')
                        for p in installed['imports'].values()), role + ' isolated imports')
        if role == 'model':
            require(installed.get('torch_cuda_build') == protocol['runtime']['model']['torch_cuda_build'], 'torch CUDA build')
        cleanup = receipt.get(role + '_process_cleanup', {})
        commands = cleanup.get('commands', [])
        require(cleanup.get('groups_absent') is True and cleanup.get('error') is None and cleanup.get('interrupted') == []
                and type(cleanup.get('groups')) is int and cleanup['groups'] == len(phases) == len(commands)
                and [c.get('phase') for c in commands] == list(phases), role + ' installer cleanup inventory')
        require(all(c.get('ownership') == 'registered' and c.get('groups_absent') is True
                    and not c.get('error') and not c.get('interrupted') and type(c.get('pgid')) is int and c['pgid'] > 0
                    and type(c.get('returncode')) is int and c['returncode'] == 0
                    and isinstance(c.get('argv'), list) and bool(c['argv']) for c in commands),
                role + ' installer process outcome/cleanup')
        offline = commands[1 if role == 'model' else 5]['argv']
        require(all(flag in offline for flag in ('--no-index', '--no-cache-dir', '--only-binary=:all:'))
                and (role != 'model' or '--require-hashes' in offline), role + ' offline installation contract')
        if role == 'model':
            require('-r' in offline and Path(offline[offline.index('-r')+1]).name == 'trusted_requirements.lock',
                    'hash-pinned requirements input')
        metadata = commands[3 if role == 'model' else 9]['argv']
        from research.stagnation_supervision_runtime_v2.publisher_install import PACKAGE_CHECK
        require(metadata[:3] == [interpreters[role], '-I', '-c']
                and metadata[-2] == PACKAGE_CHECK
                and json.loads(metadata[-1]) == {**protocol['runtime'][role], 'imports': imports},
                role + ' frozen metadata probe')
        packed_record = _read(root, 'logs/install-' + role + '.json')
        require(packed_record.get('encoding') == 'gzip-base64-json', role + ' installer log encoding')
        packed = base64.b64decode(packed_record['data'], validate=True)
        require(hashlib.sha256(packed).hexdigest() == receipt.get('installer_evidence_sha256', {}).get(role),
                role + ' retained installer evidence hash')
        with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
            raw = stream.read(8*1024**2 + 1)
        require(len(raw) <= 8*1024**2, 'decompressed installer evidence budget')
        logs = json.loads(raw)
        require('install.log' in logs if role == 'model' else {'stages.log', 'stages.json', 'resolution.json',
                                                            'install_game.json'} <= set(logs), role + ' log inventory')
        text = base64.b64decode(logs['install.log' if role == 'model' else 'stages.log'], validate=True).decode('utf-8')
        reports = []
        for line in text.splitlines():
            if line.startswith('{'):
                try:
                    reports.append(json.loads(line))
                except ValueError:
                    pass  # command text can also contain a brace; only exact output objects match
        expected_report = {k: installed[k] for k in ('versions', 'imports')}
        if role == 'model':
            expected_report['torch_cuda_build'] = installed['torch_cuda_build']
        require(expected_report in reports, role + ' metadata receipt disagrees with retained stdout')
        if role == 'game':
            stages = json.loads(base64.b64decode(logs['stages.json'], validate=True))
            require([s.get('stage') for s in stages] == list(phases)
                    and all(s.get('passed') is True and s.get('error') is None
                            and _number(s['started_seconds']) <= _number(s['ended_seconds']) <= receipt['elapsed_seconds']
                            for s in stages), 'game installation stage receipts')
            frozen = json.loads((ROOT / 'reports/phase4_v2_offline_package.json').read_bytes())['files']
            wheels = {Path(n).name: row for n, row in frozen.items() if n.startswith('wheels/')}
            for name in ('resolution.json', 'install_game.json'):
                plan = json.loads(base64.b64decode(logs[name], validate=True))
                seen = set()
                for entry in plan['install']:
                    source = entry['download_info']
                    url = urlparse(source['url'])
                    filename = Path(unquote(url.path)).name
                    require(url.scheme == 'file' and filename in wheels and filename not in seen
                            and source['archive_info']['hashes']['sha256'] == wheels[filename]['sha256'],
                            'game resolution/install wheel provenance')
                    seen.add(filename)
                require(seen == set(wheels), 'complete game resolution/install inventory')
    return {'verified': True, 'scope': 'runtime_v2_split_install'}
