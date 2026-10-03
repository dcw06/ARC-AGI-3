"""Freeze a GPU-disabled R7 preparatory package; source access remains blocked."""
import base64,hashlib,json,lzma,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'notebooks/stagnation-supervision-v1-preparation-r7'
EXTRA=('scripts/stagnation_provider_preflight_v1.py','scripts/stagnation_successor_preparation_v1.py',
 'scripts/stagnation_supervision_launch_preflight_v1.py','scripts/kaggle_stagnation_supervision_attachment_repair_v1.py',
 'scripts/kaggle_stagnation_supervision_v1_r6_no_retry.py','scripts/submit_stagnation_supervision_v1_r6_once.py',
 'scripts/prepare_stagnation_supervision_v1_authorization_r6.py')

def sha(b):return hashlib.sha256(b).hexdigest()
def raw(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
def build():
 from scripts.review_action_effect_history_v1_notebook import verify_bindings
 from scripts.build_stagnation_supervision_v1_review_r4 import cell
 parent=ROOT/'notebooks/stagnation-supervision-v1-review-r4'
 lock,_,encoded=verify_bindings(parent)
 payload={n:base64.b64decode(v) for n,v in encoded.items()}
 for name in EXTRA:payload[name]=(ROOT/name).read_bytes()
 bindings={n:sha(v) for n,v in payload.items()}
 packed=base64.b85encode(lzma.compress(json.dumps({n:base64.b64encode(v).decode() for n,v in payload.items()},sort_keys=True).encode())).decode()
 code=cell(bindings,packed)
 call='    from scripts.stagnation_supervision_v1_launch import notebook_entry\n    notebook_entry(source,started,MODE,SESSION)\n'
 assert code.count(call)==1
 code=code.replace(call,'    from scripts.stagnation_successor_preparation_v1 import refuse_live\n    refuse_live()\n')
 notebook=json.loads((parent/'profile.ipynb').read_bytes());notebook['cells'][1]['source']=code
 notebook['cells'][0]['source']='# R7 provider-preflight preparation snapshot\nGPU disabled. Live entry deliberately refuses. Dataset access remains denied; no replacement authority or budget. Runtime unchanged from R4. Not a launch-ready notebook.'
 metadata=json.loads((parent/'kernel-metadata.json').read_bytes());metadata.update(id='daichongwei06/arc3-stagnation-supervision-v1-preparation-r7',title='ARC3 Stagnation Supervision V1 Preparation R7')
 files={'profile.ipynb':raw(notebook),'kernel-metadata.json':raw(metadata)}
 if len(files['profile.ipynb'])>=900000:raise ValueError('upload guard')
 documents=['scripts/build_review_stagnation_preparation_r7.py','tests/test_ssv_provider_preflight.py','reports/stagnation_provider_preflight_review_r7.md']
 documents += [p.relative_to(ROOT).as_posix() for p in (ROOT/'reports/stagnation_provider_preflight_v1_observations').glob('*.json')]
 review={'revision':'r7','status':'preparation_only_access_blocked','parent_review_sha256':sha((parent/'review-source-lock.json').read_bytes()),
  'bindings':bindings,'artifacts':{n:sha(v) for n,v in files.items()},'review_documents':{n:sha((ROOT/n).read_bytes()) for n in documents},
  'authorized_seconds':0,'gpu_launch_authorized':False}
 OUT.mkdir()
 for n,b in {**files,'review-source-lock.json':raw(review)}.items():(OUT/n).write_bytes(b)
 return review

def check():
 import ast
 review=json.loads((OUT/'review-source-lock.json').read_bytes())
 for base,key in ((ROOT,'bindings'),(ROOT,'review_documents'),(OUT,'artifacts')):
  for n,h in review[key].items():
   if sha((base/n).read_bytes())!=h:raise ValueError('binding drift: '+n)
 nb=json.loads((OUT/'profile.ipynb').read_bytes());code=nb['cells'][1]['source']
 node=next(n for n in ast.walk(ast.parse(code)) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='payload' for t in n.targets))
 payload=json.loads(lzma.decompress(base64.b85decode(node.value.args[0].args[0].args[0].value)))
 if set(payload)!=set(review['bindings']):raise ValueError('embedded inventory')
 for n,v in payload.items():
  b=base64.b64decode(v)
  if sha(b)!=review['bindings'][n]:raise ValueError('embedded binding')
  if n.endswith('.py'):compile(b,n,'exec')
 with tempfile.TemporaryDirectory() as tmp:
  p=Path(tmp)/'cell.py';p.write_text(code)
  env=dict(os.environ,CUDA_VISIBLE_DEVICES='',TMPDIR=tmp,TEMP=tmp,TMP=tmp)
  r=subprocess.run([sys.executable,str(p)],cwd=tmp,env=env,capture_output=True,text=True,timeout=120)
  if r.returncode==0 or 'R7 preparation-only package' not in r.stderr:raise ValueError('live refusal: '+r.stderr[-500:])
  if {p.name for p in Path(tmp).iterdir()}!={'cell.py'}:raise ValueError('source cleanup')
 return {'status':'reviewed_preparation_only_access_blocked','source_bindings':len(payload),'embedded_compilation':True,
  'live_refusal_and_source_cleanup':True,'review_lock_sha256':sha((OUT/'review-source-lock.json').read_bytes()),'gpu_runs':0,'new_reservations':0}

if __name__=='__main__':
 if not OUT.exists():build()
 result=check();destination=ROOT/'reports/stagnation_preparation_r7_package_checks.json'
 if destination.exists():
  if json.loads(destination.read_bytes())!=result:raise ValueError('receipt drift')
 else:destination.write_bytes(raw(result))
 print(json.dumps(result,indent=2))
