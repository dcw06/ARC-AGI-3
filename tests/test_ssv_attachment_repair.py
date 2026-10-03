import base64,copy,hashlib,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
from scripts.stagnation_supervision_launch_preflight_v1 import REQUIRED,validate_preflight,validate_response,consume_explicit_approvals
from scripts.kaggle_stagnation_supervision_attachment_repair_v1 import KaggleNoRetry
ROOT=Path(__file__).resolve().parents[1]

class Repair(unittest.TestCase):
 def fixtures(self,root):
  (root/'kernel-metadata.json').write_text(json.dumps(REQUIRED))
  now=datetime.now(timezone.utc);body=b'{"fixture":"synthetic access response"}'
  return now,[{'kind':kind,'reference':ref,'resolved_reference':ref,'http_status':200,'accessible':True,
   'observed_at_utc':now.isoformat(),'response_hex':body.hex(),'response_sha256':hashlib.sha256(body).hexdigest()}
   for kind,refs in REQUIRED.items() for ref in refs]

 def test_required_preflight_missing_denied_stale_and_mismatch(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);now,rows=self.fixtures(root);validate_preflight(root,rows,now=now)
   for kind in REQUIRED:
    for field,value in [('http_status',403),('accessible',False),('resolved_reference','wrong'),
                        ('response_sha256','0'*64),('observed_at_utc',(now-timedelta(seconds=301)).isoformat())]:
     with self.subTest(kind=kind,field=field):
      changed=copy.deepcopy(rows);next(r for r in changed if r['kind']==kind)[field]=value
      with self.assertRaises((ValueError,PermissionError)):validate_preflight(root,changed,now=now)
   with self.assertRaises(PermissionError):validate_preflight(root,rows[:-1],now=now)
   with self.assertRaises(ValueError):validate_preflight(root,rows+[rows[0]],now=now)
   meta=copy.deepcopy(REQUIRED);meta['model_sources']=[];(root/'kernel-metadata.json').write_text(json.dumps(meta))
   with self.assertRaises(ValueError):validate_preflight(root,rows,now=now)

 def test_archived_response_and_all_attachment_rejections_retained_no_retry(self):
  archive=ROOT/'reports/stagnation_supervision_v1_r5_session1_authority/provider-response.json'
  actual=json.loads(base64.b64decode(json.loads(archive.read_bytes())['response_base64']))
  cases=[actual]+[{'url':'https://www.kaggle.com/code/test/fixture',key:['rejected']}
    for key in ('invalidDatasetSources','invalidModelSources','invalidCompetitionSources','invalidKernelSources')]
  for value in cases:
   with self.subTest(value=value),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);_,rows=self.fixtures(root);(root/'submission-claim.json').write_text('{}')
    response_bytes=json.dumps(value).encode();body=b'fixture request'
    class Response:
     status_code=200
     def __enter__(self):return self
     def __exit__(self,*a):pass
     def iter_content(self,n):yield response_bytes
    class Session:
     calls=0;used=False
     def post(self,*a,**kw):self.calls+=1;self.used=True;return Response()
     def close(self):pass
    session=Session();adapter=KaggleNoRetry(session,root,hashlib.sha256(body).hexdigest(),source_observations=rows)
    with patch('scripts.kaggle_stagnation_supervision_attachment_repair_v1.request_body',return_value=body):
     with self.assertRaises(ValueError):adapter(root)
     with self.assertRaises(FileExistsError):adapter(root)
    self.assertEqual(session.calls,1)
    self.assertEqual(base64.b64decode(json.loads((root/'provider-response.json').read_bytes())['response_base64']),response_bytes)
    self.assertTrue(json.loads((root/'provider-attachment-disposition.json').read_bytes())['consumed'])

 def test_denied_preflight_makes_zero_posts(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);_,rows=self.fixtures(root);rows[0]['http_status']=403
   (root/'submission-claim.json').write_text('{}')
   class Session:
    used=False
    def post(self,*a,**k):raise AssertionError('must not POST')
   with self.assertRaises(PermissionError):
    KaggleNoRetry(Session(),root,'0'*64,source_observations=rows)(root)

 def test_planning_text_and_historical_approvals_not_explicit_confirmation(self):
  ledger=ROOT/'reports/stagnation_supervision_v1_r5_session1_authority/reports'
  with self.assertRaises(PermissionError):
   consume_explicit_approvals(ledger/'stagnation_supervision_v1_r6_source_approval.json',
    ledger/'stagnation_supervision_v1_r6_launch_approval.json',source_hash='365572597cc972268dc0cb7b52d5b10ea2b5f4f31ea22bbbaf77285d2272bd03',reservation_hash='unused')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);s=root/'source.json';l=root/'launch.json'
   source={'approval_kind':'source','status':'approved','review_lock_sha256':'source','explicit_confirmation':True,
     'provenance':{'type':'user_confirmation','message_reference':'synthetic-source-message','verbatim_text':'approve source','interpretation_only':False}}
   s.write_text(json.dumps(source));launch={'approval_kind':'launch','status':'approved','review_lock_sha256':'source',
     'explicit_confirmation':True,'provenance':{'type':'user_confirmation','message_reference':'synthetic-launch-message','verbatim_text':'authorize launch','interpretation_only':False},
     'source_approval_sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'reservation_sha256':'reserve',
     'authorization_scope':'submit_and_execute_one_attempt','submission_authorized':True}
   l.write_text(json.dumps(launch));consume_explicit_approvals(s,l,source_hash='source',reservation_hash='reserve')
   source['provenance']['type']='planning_recommendation';s.write_text(json.dumps(source))
   with self.assertRaises(PermissionError):consume_explicit_approvals(s,l,source_hash='source',reservation_hash='reserve')
