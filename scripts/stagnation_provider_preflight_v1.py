"""Read-only Kaggle source access receipts, reconstructed from exact RPC requests and raw responses."""
import base64
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from scripts.stagnation_supervision_launch_preflight_v1 import REQUIRED,validate_preflight
from scripts.kaggle_stagnation_supervision_v1_r6_no_retry import credential_session

MAX_BYTES=262144
MODEL={'ownerSlug':'qwen-lm','modelSlug':'qwen-3-vl','framework':'MODEL_FRAMEWORK_TRANSFORMERS','instanceSlug':'30b-a3b-instruct-fp8'}
PLANS={
 'dataset_sources': [('datasets.DatasetApiService/GetDataset',{'ownerSlug':'driessmit1','datasetSlug':'arc3-vllm-h100-wheelhouse-v3'}),
                     ('datasets.DatasetApiService/ListDatasetFiles',{'ownerSlug':'driessmit1','datasetSlug':'arc3-vllm-h100-wheelhouse-v3','pageSize':20})],
 'model_sources': [('models.ModelApiService/GetModelInstance',MODEL),
                   ('models.ModelApiService/ListModelInstanceVersionFiles',{**MODEL,'versionNumber':1,'pageSize':20})],
 'competition_sources': [('competitions.CompetitionApiService/GetCompetition',{'competitionName':'arc-prize-2026-arc-agi-3'}),
                        ('competitions.CompetitionApiService/ListDataFiles',{'competitionName':'arc-prize-2026-arc-agi-3','pageSize':20})]}


def collect(kind,reference,session_factory=credential_session):
 if kind not in REQUIRED or REQUIRED[kind]!=[reference]:raise ValueError('unknown source')
 calls=[]
 for endpoint,request in PLANS[kind]:
  with session_factory() as session:
   response=session.post('https://api.kaggle.com/v1/'+endpoint,json=request)
   body=bytearray()
   with response:
    for chunk in response.iter_content(8192):
     body.extend(chunk[:MAX_BYTES+1-len(body)])
     if len(body)>MAX_BYTES:break
   calls.append({'endpoint':endpoint,'request':request,'http_status':response.status_code,
    'observed_at_utc':datetime.now(timezone.utc).isoformat(),'response_base64':base64.b64encode(body).decode(),
    'response_sha256':hashlib.sha256(body).hexdigest(),'truncated':len(body)>MAX_BYTES})
 return {'kind':kind,'reference':reference,'calls':calls}


def normalize(record,now=None):
 now=now or datetime.now(timezone.utc);kind=record['kind'];ref=record['reference']
 if kind not in REQUIRED or REQUIRED[kind]!=[ref]:raise ValueError('source identity')
 if len(record['calls'])!=len(PLANS[kind]):raise ValueError('RPC inventory')
 decoded=[];dates=[]
 for call,(endpoint,request) in zip(record['calls'],PLANS[kind]):
  if call['endpoint']!=endpoint or call['request']!=request:raise ValueError('RPC identity')
  body=base64.b64decode(call['response_base64'],validate=True)
  if call['truncated'] is not False or len(body)>MAX_BYTES or hashlib.sha256(body).hexdigest()!=call['response_sha256']:
   raise ValueError('raw receipt integrity')
  stamp=datetime.fromisoformat(call['observed_at_utc']);dates.append(stamp)
  if stamp.tzinfo is None or not 0<=(now-stamp).total_seconds()<=300:raise ValueError('stale provider observation')
  if type(call['http_status']) is not int or call['http_status']!=200:raise PermissionError('source inaccessible: '+ref)
  value=json.loads(body)
  if not isinstance(value,dict) or value.get('error'):raise ValueError('provider error')
  decoded.append(value)
 identity,listing=decoded
 if kind=='dataset_sources':
  if identity.get('ref')!=ref:raise ValueError('dataset returned another identity')
 elif kind=='competition_sources':
  if identity.get('ref') not in (ref,'https://www.kaggle.com/competitions/'+ref):raise ValueError('competition identity')
 else:
  expected='https://www.kaggle.com/models/qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8'
  if identity.get('slug')!='30b-a3b-instruct-fp8' or str(identity.get('url','')).rstrip('/')!=expected:
   raise ValueError('model instance identity')
  # The explicit version-1 listing RPC, not the current instance version, binds the version.
 files=listing.get('files')
 if not isinstance(files,list) or not files or any(not isinstance(f,dict) or not isinstance(f.get('name'),str) or not f['name'] for f in files):
  raise ValueError('readable nonempty file page required')
 raw=json.dumps(record,sort_keys=True,separators=(',',':')).encode()
 return {'kind':kind,'reference':ref,'resolved_reference':ref,'http_status':200,'accessible':True,
  'observed_at_utc':min(dates).isoformat(),'response_hex':raw.hex(),'response_sha256':hashlib.sha256(raw).hexdigest(),
  'limitation':'Identity and first-page read access only; not full inventory, checksums, mount or installation proof.'}


def validate_provider_preflight(folder,records,now=None):
 # Always recompute normalized claims; caller-supplied accessible booleans are never trusted.
 rows=[normalize(record,now) for record in records]
 validate_preflight(folder,rows,now=now)
 return rows


def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 args.output.mkdir(parents=True,exist_ok=False)
 records=[];failures=[]
 for kind,refs in REQUIRED.items():
  try:
   record=collect(kind,refs[0]);records.append(record)
   (args.output/(kind+'.json')).write_text(json.dumps(record,indent=2)+'\n')
   normalize(record)
  except Exception as exc:failures.append({'kind':kind,'error_type':type(exc).__name__,'error':str(exc)[:180]})
 result={'status':'blocked' if failures else 'read_access_verified_only','failures':failures,'gpu_runs':0,'new_reservations':0}
 (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
