"""Freeze a complete split-pilot review snapshot; never authorize GPU compute."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import lzma
from certification.phase4_v4.authority import inventory,ROOT

def build(output):
    names=set(inventory())
    for revision in ('phase4_v5','phase4_v6','phase4_v7','phase4_v8','phase4_v9','phase4_v10','phase4_v11','phase4_v12','phase4_v13','phase4_v14','phase4_diagnostic_v1','phase4_diagnostic_v2','phase4_diagnostic_v3','phase4_multimodal_preflight_v3'):
        names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'certification'/revision).glob('*.py'))
    names.update(['certification/phase4_multimodal_preflight_v3/protocol.json','reports/phase4_torch_wheel_inspection.json',
                  'reports/phase4_v6_install_r5_evaluation.json'])
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'tests').glob('test_phase4*.py'))
    names.add('tests/__init__.py')
    names.add('reports/phase4_action_selection_probe_proposal.json')
    names.update(['scripts/audit_phase4_multimodal_preflight_v3_processor.py',
        'reports/phase4_multimodal_preflight_v3_processor_audit.json'])
    names.update(['scripts/build_phase4_multimodal_preflight_v3.py','scripts/check_phase4_multimodal_preflight_v3.py',
        'scripts/phase4_multimodal_preflight_v3_launch.py','scripts/review_phase4_multimodal_preflight_v3_notebook.py',
        'reports/phase4_multimodal_preflight_v3_review.md','reports/phase4_multimodal_preflight_v3_local_checks.json',
        'reports/phase4_multimodal_preflight_v3_local_archive.json','reports/phase4_perception_v1_protocol.md',
        'certification/phase4_multimodal_preflight_v3/cases.json',
        'certification/phase4_multimodal_preflight_v3/tokenizer_manifest.json','certification/phase4_transient_v2/protocol.json'])
    bindings={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(names)}
    payload={name:base64.b64encode((ROOT/name).read_bytes()).decode() for name in names}
    packed=base64.b85encode(lzma.compress(json.dumps(payload).encode(),preset=6)).decode()
    code=f'''import base64,hashlib,json,pathlib,shutil,sys,tempfile,time,lzma
started=time.monotonic()
source=pathlib.Path(tempfile.mkdtemp(prefix='p4-multimodal-preflight-v2-source-'))
admitted=False
completed=False
try:
    payload=json.loads(lzma.decompress(base64.b85decode({packed!r})))
    bindings={bindings!r}
    for name,value in payload.items():
        data=base64.b64decode(value)
        assert hashlib.sha256(data).hexdigest()==bindings[name]
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    sys.path.insert(0,str(source))
    from certification.phase4_multimodal_preflight_v3.live_probes import require_live_authority
    require_live_authority() # Review stops here before installation or GPU queries.
    from certification.phase4_multimodal_preflight_v3.authority import consume_runtime
    consume_runtime(source,pathlib.Path('/kaggle/working'))
    admitted=True
    from certification.phase4_multimodal_preflight_v3.finalize import finalize
    from certification.phase4_multimodal_preflight_v3.entry import main
    sys.argv=['multimodal-preflight-v2','--started',str(started),'--output','/kaggle/working/phase4-multimodal-preflight-v3']
    main()
    completed=True
finally:
    shutil.rmtree(source)
    if admitted:
        finalize('/kaggle/working/phase4-multimodal-preflight-v3',started,completed)
'''
    notebook={'nbformat':4,'nbformat_minor':4,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}},
        'cells':[{'cell_type':'markdown','metadata':{},'source':'# Multimodal image-input preflight v3: processor repair, review only\nPyTorch processor tensors, explicit failure stage/type/transport evidence, real pinned processor CPU audit. Unchanged startup diagnostics, 900-second startup ceiling, one text canary and four probes. Zero actions/scorecards. GPU disabled. Separate source approval and new 1800-second compute authorization required.'},
                 {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':code}]}
    metadata={'id':'daichongwei06/arc3-phase4-multimodal-preflight-v3-review','title':'ARC3 Phase4 Multimodal Preflight V3 Review',
        'code_file':'profile.ipynb','language':'python','kernel_type':'notebook','is_private':True,
        'enable_gpu':False,'enable_tpu':False,'enable_internet':False,
        'competition_sources':['arc-prize-2026-arc-agi-3'],
        'dataset_sources':['driessmit1/arc3-vllm-h100-wheelhouse-v3'],
        'model_sources':['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1']}
    if len(json.dumps(notebook,indent=1).encode())>=900000: raise ValueError('notebook exceeds upload size guard')
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
