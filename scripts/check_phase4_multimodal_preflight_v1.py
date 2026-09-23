"""CPU-only supervised fixtures for every outcome class and portable evidence; no model/GPU calls."""
import argparse,hashlib,json,os,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
MODES={'verified':'image_input_verified','incorrect':'image_input_verified','identical':'image_input_verified',
    'invalid':'image_input_verified','arithmetic':'image_input_verified','dependency':'dependency_missing',
    'rejected':'image_rejected_by_server','mismatch':'token_accounting_mismatch','not_consumed':'image_not_consumed',
    'transport':'lifecycle_failure'}
MANIFEST=ROOT/'reports/phase4_multimodal_preflight_v1_local_archive.json'

def replay_archive():
    from certification.phase4_multimodal_preflight_v1.cases import load_cases,generate
    from certification.phase4_multimodal_preflight_v1.replay import replay
    frozen=[{k:v for k,v in r.items() if k!='frozen_local_expectation'} for r in load_cases()]
    assert generate()==frozen,'retained-source probe drift'
    manifest=json.loads(MANIFEST.read_bytes())
    archive=ROOT/manifest['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['sha256']
    results={}
    with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(archive) as z:
        folder=Path(tmp);assert set(z.namelist())==set(manifest['members']) and len(z.namelist())==len(manifest['members'])
        for name,digest in manifest['members'].items():
            path=(folder/name).resolve();assert path.is_relative_to(folder.resolve())
            raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==digest
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        for mode,verdict in MODES.items():
            value=replay(folder/mode,live=False,seconds=120);c=value['comparison']
            assert value['passed']==(mode!='transport') and c['verdict']==verdict,(mode,value['errors'],c['verdict'])
            results[mode]={'technical_passed':value['passed'],'verdict':c['verdict'],'flags':c['flags'],
                'representation_comparison_unblocked':c['representation_comparison_unblocked']}
    return results

def build():
    suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_phase4_multimodal_preflight_v1','tests.test_phase4_multimodal_preflight_v1_launch'])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    from certification.phase4_multimodal_preflight_v1.pilot import run
    from unittest.mock import patch
    archive=ROOT/'evidence/phase4-multimodal-preflight-v1-local.zip';members={};timings={}
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        for mode in MODES:
            with patch.dict(os.environ,{'PREFLIGHT_FIXTURE_MODE':mode}):
                report,value=run(folder/mode,ROOT,mode='local',seconds=120,reserve=10)
            assert report['cleanup_verified'] and report['scratch_removed']
            timings[mode]=report['elapsed_seconds']
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    raw=p.read_bytes();name=p.relative_to(folder).as_posix();members[name]=hashlib.sha256(raw).hexdigest();z.writestr(name,raw)
    manifest={'archive':archive.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':members}
    MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
    receipt={'tests_passed':result.testsRun,'fixture_elapsed_seconds':timings,'archive_replay':replay_archive(),
        'model_calls':0,'gpu_runs':0,'environment_actions':0,'scorecards':0}
    (ROOT/'reports/phase4_multimodal_preflight_v1_local_checks.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay',action='store_true');args=p.parse_args()
    print(json.dumps(replay_archive() if args.replay else build(),indent=2))
