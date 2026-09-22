import copy,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from certification.phase4_integrated_v1.worker import run_cases
from certification.phase4_integrated_v1.fixtures import ScriptedService,adapter_factory,initial,prediction
from certification.phase4_integrated_v1.evidence import EvidenceStore
from certification.phase4_integrated_v1.trajectory import evaluate_trajectories
from certification.phase4_integrated_v1.request_contract import make_request,validate_request,parse
from certification.phase4_integrated_v1.predicates import verdict,changes

class IntegratedTests(unittest.TestCase):
 def run_fixture(self,mode='correct'):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name);start=time.monotonic()
  with patch.dict('os.environ',{'INTEGRATED_FIXTURE':mode}):
   state=run_cases(ScriptedService(),EvidenceStore(root,'worker'),adapter_factory,started=start,deadline=start+100,cancel=root/'cancel',live=False)
  return root,state
 def test_complete_and_incorrect_are_technical_success(self):
  for mode in ('correct','incorrect','invalid'):
   root,s=self.run_fixture(mode);r=evaluate_trajectories(s,root/'worker',seconds=120)
   self.assertEqual(len(r['episodes']),2)
   if mode=='invalid':self.assertEqual(r['episodes'][1]['terminal_reason'],'invalid_output')
   elif mode=='incorrect':self.assertFalse(r['episodes'][1]['feedback'][0]['feedback_verdicts_exact'])
   else:self.assertEqual((r['actions'],r['calls']),(4,7))
 def test_replay_mutations(self):
  root,s=self.run_fixture();bad=copy.deepcopy(s);bad['episodes'].pop()
  with self.assertRaises(ValueError):evaluate_trajectories(bad,root/'worker',seconds=120)
  ep=s['episodes'][1];path=root/'worker'/ep['steps'][0];raw=path.read_bytes();v=json.loads(raw);v['action']['action_id']=2;path.write_text(json.dumps(v))
  with self.assertRaises(ValueError):evaluate_trajectories(s,root/'worker',seconds=120)
  path.write_bytes(raw);path=root/'worker'/ep['calls'][2];raw=path.read_bytes();path.unlink()
  with self.assertRaises(OSError):evaluate_trajectories(s,root/'worker',seconds=120)
 def test_full_cap_and_late_return(self):
  root,s=self.run_fixture('cap');r=evaluate_trajectories(s,root/'worker',seconds=120)
  self.assertEqual((r['actions'],r['calls']),(16,25))
  path=root/'worker'/s['episodes'][0]['calls'][0];v=json.loads(path.read_bytes())
  v['returned_seconds']=s['request_window_cutoff_seconds'];path.write_text(json.dumps(v))
  with self.assertRaises(ValueError):evaluate_trajectories(s,root/'worker',seconds=120)
 def test_baseline_equivalence(self):
  from certification.phase4_integrated_v1.contract import unpack,baseline_request
  from certification.phase4_transient_v2.contract import request_for
  from agent.state import GameRuntimeState
  state=GameRuntimeState(unpack(initial()),action_budget_limit=8)
  self.assertEqual(baseline_request(state),request_for(state,'control',seed=0,previous_transition=None))
 def test_geometry_assignment(self):
  from certification.phase4_integrated_v1.geometry import evaluate_inventory
  r=evaluate_inventory({'objects':[{'id':'one','bbox':[36,15,44,23],'spans':[[y,36,44 if y<=17 else 38] for y in range(15,24)]}]})
  self.assertTrue(r['mask_matches'][1]['silhouette_exact']);self.assertFalse(r['mask_matches'][0]['localized'])
 def test_failures_retain_state(self):
  for mode in ('mismatch','transport','initial','cleanup'):
   with self.assertRaises((ValueError,RuntimeError)):self.run_fixture(mode)
 def test_deadline(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   with self.assertRaises(TimeoutError):run_cases(ScriptedService(),EvidenceStore(root,'worker'),adapter_factory,started=time.monotonic(),deadline=0,cancel=root/'cancel',live=False)
 def test_contract_and_predicates(self):
  r=make_request('inventory',initial(),{});self.assertEqual(validate_request(r),'inventory')
  r['max_tokens']=128
  with self.assertRaises(ValueError):validate_request(r)
  g=[[1,2],[3,4]];self.assertEqual(changes(g,g),{'count':0,'bbox':[]})
  self.assertEqual(changes(g,[[1]]),{'count':-1,'bbox':[]})
  p=prediction('any_cell_change');p['frame']='any_returned'
  self.assertEqual(verdict(p,g,[[[0,2],[3,4]],g],0,0),'supported')
  self.assertEqual(verdict(p,g,[[[1]]],0,0),'unresolved')
  with self.assertRaises(ValueError):make_request('feedback',{**initial(),'frames':initial()['frames']*9},{})
 def test_response_retention_and_exhaustion(self):
  from certification.phase4_integrated_v1.response_evidence import capture
  e=capture('x'*32769,{'server_prompt_tokens':9});self.assertTrue(e['response_truncated']);self.assertEqual(len(e['response_content']),32768)
  from certification.phase4_integrated_v1.evidence import LIMITS
  with tempfile.TemporaryDirectory() as t,patch.dict(LIMITS,{'worker':5000}):
   with self.assertRaises(Exception):EvidenceStore(Path(t),'worker').save('x.json',{'data':'x'*6000})

if __name__=='__main__':unittest.main()
