"""Freeze a complete split-pilot review snapshot; never authorize GPU compute."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import zlib
from certification.phase4_v4.authority import inventory,ROOT

def build(output):
    names=set(inventory())
    for revision in ('phase4_v5','phase4_v6','phase4_v7','phase4_v8'):
        names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'certification'/revision).glob('*.py'))
    names.update(['certification/phase4_v8/protocol.json','reports/phase4_torch_wheel_inspection.json',
                  'reports/phase4_v6_install_r5_evaluation.json'])
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'tests').glob('test_phase4*.py'))
    names.add('tests/__init__.py')
    bindings={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(names)}
    payload={name:base64.b64encode((ROOT/name).read_bytes()).decode() for name in names}
    packed=base64.b64encode(zlib.compress(json.dumps(payload).encode())).decode()
    code=f'''import base64,hashlib,json,pathlib,shutil,sys,tempfile,time,zlib
started=time.monotonic()
source=pathlib.Path(tempfile.mkdtemp(prefix='p4-v8-source-'))
admitted=False
completed=False
try:
    payload=json.loads(zlib.decompress(base64.b64decode({packed!r})))
    bindings={bindings!r}
    for name,value in payload.items():
        data=base64.b64decode(value)
        assert hashlib.sha256(data).hexdigest()==bindings[name]
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    sys.path.insert(0,str(source))
    from certification.phase4_v8.live_probes import require_live_authority
    require_live_authority() # Review stops here before installation or GPU queries.
    admitted=True
    from certification.phase4_v8.finalize import finalize
    from certification.phase4_v8.entry import main
    sys.argv=['v8','--started',str(started),'--output','/kaggle/working/phase4-development-v8']
    main()
    completed=True
finally:
    shutil.rmtree(source)
    if admitted:
        finalize('/kaggle/working/phase4-development-v8',started,completed)
'''
    notebook={'nbformat':4,'nbformat_minor':4,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}},
        'cells':[{'cell_type':'markdown','metadata':{},'source':'# Split-environment development pilot v8 — source review\nInstallation basis: successful r5 target check. GPU disabled; separate source approval and pilot reservation required. No model pilot certification claimed.'},
                 {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':code}]}
    metadata={'id':'daichongwei06/arc3-phase4-development-v8-review','title':'ARC3 Phase4 Development v8 Review',
        'code_file':'profile.ipynb','language':'python','kernel_type':'notebook','is_private':True,
        'enable_gpu':False,'enable_tpu':False,'enable_internet':False,
        'competition_sources':['arc-prize-2026-arc-agi-3'],
        'dataset_sources':['driessmit1/arc3-vllm-h100-wheelhouse-v3'],
        'model_sources':['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1']}
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    for name,value in [('profile.ipynb',notebook),('kernel-metadata.json',metadata)]:
        (output/name).write_text(json.dumps(value,indent=1),encoding='utf-8')
    lock={'status':'implementation_review_snapshot_pending_user_source_approval_not_compute_authority',
          'bindings':bindings,'artifacts':{name:hashlib.sha256((output/name).read_bytes()).hexdigest()
              for name in ('profile.ipynb','kernel-metadata.json')}}
    (output/'review-source-lock.json').write_text(json.dumps(lock,indent=2),encoding='utf-8')
    return lock

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    print(json.dumps(build(p.parse_args().output)))
