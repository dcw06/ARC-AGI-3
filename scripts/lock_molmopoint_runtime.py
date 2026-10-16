"""Resolve image-only MolmoPoint metadata, pin all transitive wheels; no installs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.object_identification_v1.install_check import requirement_pins
from research.object_identification_v1.mount_check import canonical


def build(output,cache=None):
    from packaging.markers import default_environment
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    from packaging.specifiers import SpecifierSet
    from packaging.tags import cpython_tags, compatible_tags
    from packaging.utils import parse_wheel_filename
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    trusted = ROOT/'certification/direct_publisher_smoke_v1'
    preferred = requirement_pins((trusted/'trusted_requirements.lock').read_bytes())
    preferred.update(transformers={'version':'4.57.1'},accelerate={'version':'1.12.0'})
    manifest = json.loads((trusted/'trusted_manifest.json').read_bytes())['artifacts']
    old_by_hash = {row['sha256']:row for row in manifest}
    pending = [Requirement(r) for r in ['torch==2.10.0','torchvision==0.25.0',
               'transformers==4.57.1','accelerate==1.12.0','einops==0.8.2']]
    selected, metadata, checks = {}, {}, []
    env = default_environment()
    env.update(extra='',os_name='posix',sys_platform='linux',platform_machine='x86_64',
        platform_system='Linux',python_version='3.12',python_full_version='3.12.3',
        implementation_name='cpython',implementation_version='3.12.3')
    platforms = ['manylinux_2_'+str(v)+'_x86_64' for v in range(40,4,-1)]+[
        'manylinux2014_x86_64','manylinux2010_x86_64','manylinux1_x86_64','linux_x86_64']
    tags = set(cpython_tags((3,12),['cp312'],platforms)) | set(compatible_tags((3,12),platforms=platforms))
    def read(url):
        with urllib.request.urlopen(url,timeout=60) as response:
            return response.read()
    while pending:
        req = pending.pop(0)
        if req.marker and not req.marker.evaluate(env):
            continue
        name = canonicalize_name(req.name)
        if name not in preferred:
            raise ValueError('choose an explicit version for new dependency: '+name)
        version = preferred[name]['version']
        if version not in req.specifier:
            raise ValueError(f'constraint conflict: {req} versus {name}=={version}')
        checks.append({'requirement':str(req),'satisfied_by':name+'=='+version})
        if name in selected:
            continue
        raw = ((Path(cache)/'metadata'/(name+'.json')).read_bytes() if cache else
               read(f'https://pypi.org/pypi/{name}/{version}/json'))
        data = json.loads(raw)
        if canonicalize_name(data['info']['name']) != name or data['info']['version'] != version:
            raise ValueError('package metadata identity/version differs')
        if env['python_full_version'] not in SpecifierSet(data['info'].get('requires_python') or ''):
            raise ValueError('package does not support reviewed Python version: '+name)
        metadata[name] = raw
        old = old_by_hash.get(preferred[name].get('sha256'))
        if old:
            row = dict(filename=old['filename'],sha256=old['sha256'],bytes=old['size'],
                       acquisition='existing publisher dataset v1; verify exact mounted bytes')
            if not set(parse_wheel_filename(row['filename'])[3]) & tags:
                raise ValueError('publisher wheel incompatible with resolving interpreter: '+name)
        else:
            wheels = [f for f in data['urls'] if f['packagetype']=='bdist_wheel'
                      and set(parse_wheel_filename(f['filename'])[3]) & tags]
            if len(wheels) != 1:
                raise ValueError('one unambiguous compatible new wheel required: '+name)
            wheel = wheels[0]
            if urlsplit(wheel['url']).hostname != 'files.pythonhosted.org':
                raise ValueError('unexpected package source')
            wheel_raw = (Path(cache)/wheel['filename']).read_bytes() if cache else read(wheel['url'])
            if len(wheel_raw) != wheel['size'] or hashlib.sha256(wheel_raw).hexdigest() != wheel['digests']['sha256']:
                raise ValueError('new dependency hash/size mismatch')
            (output/wheel['filename']).write_bytes(wheel_raw)
            row = dict(filename=wheel['filename'],sha256=wheel['digests']['sha256'],
                       bytes=wheel['size'],acquisition=wheel['url'])
        selected[name] = dict(name=name,version=version,**row)
        for dependency in data['info'].get('requires_dist') or []:
            parsed = Requirement(dependency)
            if parsed.marker and not parsed.marker.evaluate(env):
                continue
            if parsed.extras:
                raise ValueError('explicit extra dependency review required: '+dependency)
            pending.append(parsed)
    lock = ''.join(f'{n}=={r["version"]} --hash=sha256:{r["sha256"]}\n'
                   for n,r in sorted(selected.items())).encode('ascii')
    (output/'requirements.lock').write_bytes(lock)
    (output/'dependency-manifest.json').write_bytes(canonical(dict(
        schema='molmopoint_runtime_v1',python='3.12',platform='linux_x86_64',
        image_only=True,torch_cuda_build_expected='12.8',packages=list(sorted(selected.values(),key=lambda r:r['name'])),
        metadata_constraint_checks=checks,requirements_sha256=hashlib.sha256(lock).hexdigest(),
        metadata_sha256={n:hashlib.sha256(raw).hexdigest() for n,raw in sorted(metadata.items())},
        isolated_installation_verified=False)))
    (output/'metadata').mkdir()
    for name,raw in metadata.items():
        (output/'metadata'/(name+'.json')).write_bytes(raw)
    print(json.dumps({'pinned_packages':len(selected),'new_wheels':len(list(output.glob('*.whl'))),
                      'requirements_sha256':hashlib.sha256(lock).hexdigest()}))


if __name__ == '__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output',required=True)
    cli.add_argument('--cache',help='recheck retained metadata/wheels without networking')
    args=cli.parse_args()
    build(args.output,args.cache)
