"""Record offline hardening replay and development-only capacity disposition."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from certification.phase4_v14.replay import load
from certification.phase4_v14.evaluate import evaluate
report,rows=load()
result=evaluate(report,rows)
assert result['passed'],result['errors']
candidate=result['capacity_candidate']
assert candidate['C_nominal']==39322 and candidate['C_admit_candidate']==22358
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[*sorted((ROOT/'certification/phase4_v14').glob('*.py')),ROOT/'tests/test_phase4_v14_evaluate.py',Path(__file__)]
record={'recorded_at':datetime.now(timezone.utc).isoformat(),
 'scope':'offline_v14_evaluator_replay_of_v13_target_evidence','result':result,
 'successful_configuration':'E1S-R-derived arc_action_v12; revised prompt and constrained decoding',
 'source_bindings':{p.relative_to(ROOT).as_posix():sha(p) for p in paths},
 'evidence_receipt_sha256':sha(ROOT/'reports/phase4_v13_pilot_evaluation.json'),
 'tests_passed':5,'negative_mutations':19,'original_verdict_changed':False,
 'gpu_run_performed':False,'gpu_seconds_authorized':0}
with (ROOT/'reports/phase4_v14_replay.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
disposition={'status':'reviewed_accepted_as_development_projection_only',
 'basis':'v13 real target evidence independently replayed with v14 cleanup and policy-binding gates',
 'configuration':record['successful_configuration'],'measured_candidate':candidate,
 'production_capacity_approved':False,'C_admit':None,'new_spending_authorized':False,
 'advanced_scheduling_justified':False,'reason':'No observed allocation failure; zero completed levels directs next work to separately scoped action selection.',
 'limitations':['110 clients repeat 15 development games on separate scorecards',
 'Empirical single-run rate margin, not a confidence bound or production guarantee',
 'Prompt lengths, trajectories and model behavior may differ on distinct unseen games',
 'Rate haircut and service-time headroom are separate reductions'],
 'replay_reference':'reports/phase4_v14_replay.json'}
with (ROOT/'reports/phase4_development_capacity_disposition.json').open('x',encoding='utf-8') as f:json.dump(disposition,f,indent=2)
print(json.dumps({'passed':result['passed'],'capacity_disposition':disposition['status']}))
