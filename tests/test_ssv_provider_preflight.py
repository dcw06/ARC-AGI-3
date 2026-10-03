import base64,copy,hashlib,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from scripts.stagnation_provider_preflight_v1 import PLANS,REQUIRED,normalize,validate_provider_preflight
from scripts.stagnation_successor_preparation_v1 import review_inputs,refuse_live
ROOT=Path(__file__).resolve().parents[1]

class Receipts(unittest.TestCase):
 def fixture(self,kind):
  ref=REQUIRED[kind][0];now=datetime.now(timezone.utc)
  identity={'ref':ref}
  if kind=='model_sources':identity={'slug':'30b-a3b-instruct-fp8','url':'https://www.kaggle.com/models/qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8'}
  calls=[]
  for (endpoint,request),value in zip(PLANS[kind],[identity,{'files':[{'name':'fixture'}]}]):
   body=json.dumps(value).encode();calls.append({'endpoint':endpoint,'request':copy.deepcopy(request),
    'http_status':200,'observed_at_utc':now.isoformat(),'response_base64':base64.b64encode(body).decode(),
    'response_sha256':hashlib.sha256(body).hexdigest(),'truncated':False})
  return {'kind':kind,'reference':ref,'calls':calls},now
 def test_all_kinds_positive_and_semantic_mutations(self):
  for kind in REQUIRED:
   record,now=self.fixture(kind);self.assertTrue(normalize(record,now)['accessible'])
   for key,value in [('endpoint','wrong'),('request',{}),('http_status',403),('truncated',True),
                     ('response_sha256','0'*64),('observed_at_utc',(now-timedelta(seconds=301)).isoformat())]:
    changed=copy.deepcopy(record);changed['calls'][0][key]=value
    with self.subTest(kind=kind,key=key),self.assertRaises((ValueError,PermissionError)):normalize(changed,now)
   changed=copy.deepcopy(record);body=b'{"ref":"wrong","slug":"wrong","url":"wrong"}'
   changed['calls'][0].update(response_base64=base64.b64encode(body).decode(),response_sha256=hashlib.sha256(body).hexdigest())
   with self.assertRaises(ValueError):normalize(changed,now)
 def test_archived_access_and_model_competition_replay(self):
  folder=ROOT/'reports/stagnation_provider_preflight_v1_observations'
  for kind in REQUIRED:
   record=json.loads((folder/(kind+'.json')).read_bytes())
   now=max(datetime.fromisoformat(c['observed_at_utc']) for c in record['calls'])
   if kind=='dataset_sources':
    with self.assertRaises(PermissionError):normalize(record,now)
   else:self.assertTrue(normalize(record,now)['accessible'])
 def test_integrated_boundary_no_access_means_no_authority_or_launch(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'kernel-metadata.json').write_text(json.dumps(REQUIRED))
   records=[self.fixture(kind)[0] for kind in REQUIRED];records[0]['calls'][0]['http_status']=403
   with patch('scripts.stagnation_successor_preparation_v1.consume_explicit_approvals') as approval:
    with self.assertRaises(PermissionError):review_inputs(root,records,'missing','missing',source_hash='x',reservation_hash='y')
    approval.assert_not_called()
   records=[self.fixture(kind)[0] for kind in REQUIRED]
   validate_provider_preflight(root,records)
   with self.assertRaises(FileNotFoundError):review_inputs(root,records,'missing','missing',source_hash='x',reservation_hash='y')
   with self.assertRaises(PermissionError):refuse_live()
