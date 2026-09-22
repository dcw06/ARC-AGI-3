"""Self-contained GPU-disabled review snapshot; authority is always separate."""
import base64,hashlib,json,lzma
from pathlib import Path
from certification.phase4_v4.authority import inventory,ROOT

def build(output):
 names=set(inventory())
 # Freeze imported historical implementations, not mutable runtime imports.
 for folder in (ROOT/'certification').iterdir():
  if folder.is_dir():names.update(p.relative_to(ROOT).as_posix() for p in folder.glob('*.py'))
 names.update(['certification/phase4_integrated_v1/protocol.json','certification/phase4_integrated_v1/tokenizer_manifest.json',
  'certification/phase4_transient_v2/protocol.json','reports/phase4_transient_v2_protocol.json',
  'reports/phase4_torch_wheel_inspection.json','reports/phase4_v6_install_r5_evaluation.json',
  'reports/phase4_integrated_v1_review.md','reports/phase4_integrated_v1_token_audit.json',
  'reports/phase4_integrated_v1_local_checks.json','reports/phase4_integrated_v1_local_archive.json',
  'reports/phase4_integrated_v1_launch_intent.json'])
 names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'reports/integrated_case_v1').glob('*') if p.is_file())
 names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'tests').glob('test_phase4_integrated_v1*.py'))
 names.add('tests/__init__.py')
 for n in ('check_phase4_integrated_v1','audit_phase4_integrated_v1','phase4_integrated_v1_launch','review_phase4_integrated_v1_notebook','observe_phase4_integrated_v1'):
  names.add('scripts/'+n+'.py')
 bindings={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(names)}
 payload={n:base64.b64encode((ROOT/n).read_bytes()).decode() for n in sorted(names)}
 packed=base64.b85encode(lzma.compress(json.dumps(payload).encode(),preset=6)).decode()
 code=f'''import base64,hashlib,json,pathlib,shutil,sys,tempfile,time,lzma
started=time.monotonic()
source=pathlib.Path(tempfile.mkdtemp(prefix='integrated-v1-source-'))
admitted=False
completed=False
try:
    payload=json.loads(lzma.decompress(base64.b85decode({packed!r})))
    bindings={bindings!r}
    for name,value in payload.items():
        raw=base64.b64decode(value)
        if hashlib.sha256(raw).hexdigest()!=bindings[name]:raise ValueError('source digest')
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    sys.path.insert(0,str(source))
    from certification.phase4_integrated_v1.authority import require,consume_runtime
    require(source)
    consume_runtime(source,pathlib.Path('/kaggle/working'))
    admitted=True
    from certification.phase4_integrated_v1.finalize import finalize
    from certification.phase4_integrated_v1.entry import main
    sys.argv=['integrated-v1','--started',str(started),'--output','/kaggle/working/phase4-integrated-v1']
    main()
    completed=True
finally:
    shutil.rmtree(source)
    if admitted:finalize('/kaggle/working/phase4-integrated-v1',started,completed)
'''
 notebook={'nbformat':4,'nbformat_minor':4,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}},'cells':[
  {'cell_type':'markdown','metadata':{},'source':'# Integrated ar25 case: executable review only\nTwo isolated arms; eight actions each; up to 25 study calls plus canary. Raw-grid scaffold bundle, not production certification. GPU disabled. New source approval and separate 3600-second compute authorization required.'},
  {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':code}]}
 metadata={'id':'daichongwei06/arc3-phase4-integrated-v1-review','title':'ARC3 Integrated V1 Review','code_file':'profile.ipynb','language':'python','kernel_type':'notebook','is_private':True,'enable_gpu':False,'enable_tpu':False,'enable_internet':False,
  'competition_sources':['arc-prize-2026-arc-agi-3'],'dataset_sources':['driessmit1/arc3-vllm-h100-wheelhouse-v3'],'model_sources':['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1']}
 assert len(json.dumps(notebook,indent=1).encode())<850000,'review upload headroom'
 output=Path(output);output.mkdir(parents=True,exist_ok=False)
 for n,v in [('profile.ipynb',notebook),('kernel-metadata.json',metadata)]: (output/n).write_bytes((json.dumps(v,indent=1)+'\n').encode())
 lock={'status':'executable_review_pending_bound_approval_no_compute_authority','bindings':bindings,'artifacts':{n:hashlib.sha256((output/n).read_bytes()).hexdigest() for n in ('profile.ipynb','kernel-metadata.json')}}
 (output/'review-source-lock.json').write_bytes((json.dumps(lock,indent=2)+'\n').encode());return lock
