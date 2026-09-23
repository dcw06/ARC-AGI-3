"""Build/replay local fixtures and scoring; no model inputs are submitted."""
import argparse,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.perception_v1.fixtures import build,gold,digest
from research.perception_v1.scoring import score
from research.perception_v1.controls import cases as control_cases,score as control_score
from certification.phase4_multimodal_preflight_v3.images import png,grid_from_png

def run(check=False):
    folder=ROOT/'reports/perception_v1_local_r2';cases=build();controls=control_cases()
    for c in cases:assert grid_from_png(png(c['grid']))==c['grid']
    values={'fixtures.json':{'status':'local_fixtures_only_not_a_frozen_model_experiment','cases':cases,'controls':controls},
        'gold_scores.json':{'perception':[score(c,json.dumps(gold(c))) for c in cases],
            'controls':[control_score(c,json.dumps(c['expected'])) for c in controls]}}
    suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_perception_v1_local','tests.test_transition_chronology'])
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    data={name:(json.dumps(value,indent=1)+'\n').encode() for name,value in values.items()}
    for c in cases:data[c['id']+'.png']=png(c['grid'])
    sources=['research/perception_v1/'+p.name for p in sorted((ROOT/'research/perception_v1').glob('*.py'))]+[
        'scripts/build_perception_v1_local.py','tests/test_perception_v1_local.py','tests/test_transition_chronology.py',
        'reports/integrated_case_v1/initial_observation.json','reports/integrated_case_v1/geometry_reference.json',
        'certification/phase4_multimodal_preflight_v3/images.py','certification/phase4_multimodal_preflight_v3/action_contract.py']
    lock={'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources},
        'artifacts':{n:hashlib.sha256(raw).hexdigest() for n,raw in data.items()},'tests_passed':result.testsRun,
        'model_calls':0,'environment_actions':0,'gpu_runs':0,'representation_comparison_blocked':True}
    data['fixture-lock.json']=(json.dumps(lock,indent=2)+'\n').encode()
    if check:
        for n,raw in data.items():assert (folder/n).read_bytes()==raw,n
    else:
        folder.mkdir(parents=True,exist_ok=False)
        for n,raw in data.items():(folder/n).write_bytes(raw)
    print(json.dumps(lock,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');run(p.parse_args().check)
