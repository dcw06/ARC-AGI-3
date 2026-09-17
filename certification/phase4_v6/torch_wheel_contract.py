"""Read Torch distribution and runtime versions without importing wheel code."""
import ast
from email.parser import BytesParser
import hashlib
import zipfile


def inspect(wheel):
    with zipfile.ZipFile(wheel) as bundle:
        names = [name for name in bundle.namelist() if name.endswith('.dist-info/METADATA')]
        if len(names) != 1:
            raise ValueError('expected one wheel distribution metadata file')
        metadata_bytes = bundle.read(names[0])
        version_bytes = bundle.read('torch/version.py')
    metadata = BytesParser().parsebytes(metadata_bytes)
    values = {}
    for node in ast.parse(version_bytes).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in ('__version__', 'cuda', 'hip', 'git_version'):
                    if target.id in values:
                        raise ValueError('duplicate runtime version field')
                    values[target.id] = ast.literal_eval(node.value)
    return {'distribution_name': metadata['Name'], 'distribution_version': metadata['Version'],
            'runtime_build': values, 'requires_dist': metadata.get_all('Requires-Dist', []),
            'metadata_sha256': hashlib.sha256(metadata_bytes).hexdigest(),
            'version_source_sha256': hashlib.sha256(version_bytes).hexdigest()}


def validate(contract, expected):
    for key in ('distribution_name', 'distribution_version', 'metadata_sha256', 'version_source_sha256'):
        if contract[key] != expected[key]:
            raise ValueError('Torch wheel contract mismatch: '+key)
    if contract['runtime_build'] != expected['runtime_build']:
        raise ValueError('Torch runtime build mismatch')
