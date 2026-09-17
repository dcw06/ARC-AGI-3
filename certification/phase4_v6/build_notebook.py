"""Package a hash-bound v6 REVIEW notebook; GPU disabled and authority closed."""
import base64
import argparse
import json
from pathlib import Path
import zlib

from certification.phase4_v4.authority import inventory, sha, ROOT
from scripts.build_m0_profile_notebook import code_cell, markdown_cell, _install_cell
from scripts.build_e1_four_cell_notebook import _arc_install_cell


def build():
    names=set(inventory())
    for revision in ('phase4_v5','phase4_v6'):
        names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'certification'/revision).glob('*.py'))
    names.add('certification/phase4_v6/protocol.json')
    names.add('tests/__init__.py')
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'tests').glob('test_phase4*.py'))
    lock={'status':'review_source_protocol_snapshot_not_launch_approval',
          'bindings':{name:sha(ROOT/name) for name in sorted(names)}}
    files={name:base64.b64encode((ROOT/name).read_bytes()).decode() for name in sorted(names)}
    packed=base64.b64encode(zlib.compress(json.dumps(files).encode())).decode()
    install_code=_install_cell()['source']+'\n'+_arc_install_cell()['source']+'''
import importlib.metadata, arc_agi, arcengine, torch, transformers, vllm
assert importlib.metadata.version('vllm').split('+')[0]=='0.19.0'
assert importlib.metadata.version('torch').split('+')[0]=='2.10.0'
assert importlib.metadata.version('transformers').split('+')[0]=='4.57.6'
'''
    body=f'''import base64,hashlib,json,pathlib,shutil,subprocess,sys,tempfile,time,zlib
started=time.monotonic()
source=pathlib.Path(tempfile.mkdtemp(prefix='p4-v6-review-'))
try:
    files=json.loads(zlib.decompress(base64.b64decode({packed!r})))
    bindings={lock['bindings']!r}
    for name,payload in files.items():
        data=base64.b64decode(payload)
        if hashlib.sha256(data).hexdigest()!=bindings[name]: raise ValueError('source hash mismatch')
        path=source/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    gate="import sys;sys.path.insert(0,sys.argv[1]);from certification.phase4_v6.live_probes import require_live_authority;require_live_authority()"
    subprocess.run([sys.executable,'-S','-c',gate,str(source)],check=True,timeout=30)
    # Review build always stops above, before package installs or hardware queries.
    sys.path.insert(0,str(source))
    from certification.phase4_v6.evidence import EvidenceStore
    from certification.phase4_v6.install import install
    output=pathlib.Path('/kaggle/working/phase4-development-v6')
    output.mkdir(exist_ok=False)
    manifest=json.loads((source/'reports/phase4_v2_offline_package.json').read_text())
    mount=pathlib.Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3')
    for name,info in manifest['files'].items():
        relative=name.replace('wheels/','arc_agi_3_wheels/',1) if name.startswith('wheels/') else name
        path=mount/relative
        if path.is_symlink() or path.stat().st_size!=info['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:
            raise ValueError('offline environment/dependency mismatch: '+name)
        if name.startswith('environment_files/'):
            dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    try:
        install({install_code!r},output,started)
        from certification.phase4_v6.pilot import run
        report,result=run(output,source/'environment_files',mode='live',seconds=27540,
                          reserve=600,started=started,prepared=True)
        if not result['passed']: raise RuntimeError('independent pilot evaluation failed')
    finally:
        EvidenceStore(output,'control').save('notebook-cost.json',
            {{'elapsed_seconds':time.monotonic()-started,'provider_reconciliation_required':True,'phase4_complete':False}})
finally:
    shutil.rmtree(source)
'''
    notebook={'nbformat':4,'nbformat_minor':4,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}},
        'cells':[markdown_cell('# v6 integrated development pilot — REVIEW ONLY\nGPU disabled. No authorized compute. Clean target-compatible installation remains unverified. Not production certification.'),code_cell(body)]}
    metadata={'id':'daichongwei06/arc3-phase4-development-v6-review','title':'ARC3 Phase4 Development v6 REVIEW ONLY',
        'code_file':'profile.ipynb','language':'python','kernel_type':'notebook','is_private':True,
        'enable_gpu':False,'enable_tpu':False,'enable_internet':False,
        'competition_sources':['arc-prize-2026-arc-agi-3'],
        'dataset_sources':['driessmit1/arc3-vllm-h100-wheelhouse-v3'],
        'model_sources':['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1']}
    return notebook,metadata,lock


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'notebooks/phase4-lifecycle-v6-review-r2')
    args=parser.parse_args()
    output=args.output;output.mkdir(parents=True,exist_ok=False)
    for name,value in zip(('profile.ipynb','kernel-metadata.json','review-source-lock.json'),build()):
        (output/name).write_text(json.dumps(value,indent=1))
    print(output)
