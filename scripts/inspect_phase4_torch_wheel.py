"""Download and inspect the frozen Torch wheel without importing or executing it."""
import ast
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
from phase4_install_kaggle import ROOT, environment

sys.path.insert(0, str(ROOT))
from certification.phase4_v6.target_install_probe import MODEL_MANIFESTS

def main():
    env = environment()
    for key in ('KAGGLE_API_TOKEN', 'KAGGLE_USERNAME', 'KAGGLE_KEY'):
        if env.get(key):
            os.environ[key] = env[key]
    import requests
    original = requests.Session.send
    def send(self, request, **kwargs):
        kwargs['timeout'] = (10, 60)
        return original(self, request, **kwargs)
    requests.Session.send = send
    from kaggle import api
    folder = ROOT/'reports/runs/phase4-torch-wheel-inspection'
    folder.mkdir(parents=True, exist_ok=True)
    dataset = 'driessmit1/arc3-vllm-h100-wheelhouse-v3'
    def fetch(name, expected):
        path = folder/name
        if not path.exists():
            api.dataset_download_file(dataset, name, path=str(folder), quiet=True)
        if not path.exists():
            archive = folder/(name+'.zip')
            with zipfile.ZipFile(archive) as bundle:
                with path.open('xb') as stream:
                    stream.write(bundle.read(name))
        digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        if digest != expected:
            raise ValueError('Frozen hash mismatch: '+name)
        print('Verified '+name, flush=True)
        return path
    for name, expected in MODEL_MANIFESTS.items():
        fetch(name, expected)
    inventory = {}
    for line in (folder/'SHA256SUMS').read_text().splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            inventory[name.lstrip('*').removeprefix('./')] = digest
    names = [name for name in inventory if name.startswith('torch-') and name.endswith('.whl')]
    assert len(names) == 1, names
    name = names[0]
    wheel = fetch(name, inventory[name])
    with zipfile.ZipFile(wheel) as bundle:
        metadata_name = next(n for n in bundle.namelist() if n.endswith('.dist-info/METADATA'))
        metadata_bytes = bundle.read(metadata_name)
        version_bytes = bundle.read('torch/version.py')
        metadata = BytesParser().parsebytes(metadata_bytes)
        values = {}
        for node in ast.parse(version_bytes).body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and target.id in ('__version__', 'cuda', 'hip', 'git_version'):
                        values[target.id] = ast.literal_eval(node.value)
        (folder/'torch-METADATA.txt').write_bytes(metadata_bytes)
        (folder/'torch-version.py.txt').write_bytes(version_bytes)
    result = {'dataset': dataset, 'wheel': name, 'wheel_sha256': inventory[name],
              'wheel_bytes': wheel.stat().st_size, 'frozen_manifest_hashes': MODEL_MANIFESTS,
              'distribution_name': metadata['Name'], 'distribution_version': metadata['Version'],
              'runtime_build': values, 'requires_dist': metadata.get_all('Requires-Dist', []),
              'metadata_sha256': hashlib.sha256(metadata_bytes).hexdigest(),
              'version_source_sha256': hashlib.sha256(version_bytes).hexdigest(),
              'inspection_method': 'Full wheel SHA256 verified; static ZIP and AST inspection; no imports or GPU run.'}
    (ROOT/'reports/phase4_torch_wheel_inspection.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
