"""CPU-only supervised fixtures and portable evidence; no model/GPU calls."""
import argparse,hashlib,json,os,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def replay_archive():
    from scripts.build_phase4_grounding_v1 import generate
    from certification.phase4_grounding_v1.cases import load_cases
    from certification.phase4_grounding_v1.replay import replay
    assert generate()==load_cases(),'retained-source case drift'
    manifest=json.loads((ROOT/'reports/phase4_grounding_v1_local_archive.json').read_bytes())
    archive=ROOT/manifest['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['sha256']
    results={}
    with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(archive) as z:
        folder=Path(tmp);assert set(z.namelist())==set(manifest['members']) and len(z.namelist())==len(manifest['members'])
        for name,digest in manifest['members'].items():
            path=(folder/name).resolve();assert path.is_relative_to(folder.resolve())
            raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==digest
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        for mode in ('correct','incorrect','malformed','transport','mismatch'):
            value=replay(folder/mode,live=False,seconds=120)
            assert value['passed']==(mode in ('correct','incorrect','malformed')),(mode,value['errors'])
            results[mode]={'technical_passed':value['passed'],'correct':sum(v['correct'] for v in value['comparison']['by_task'].values()),
                'malformed':value['comparison']['malformed_responses'],'transport_failures':value['comparison']['transport_failures']}
    return results

def build():
    suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_phase4_grounding_v1','tests.test_phase4_grounding_v1_launch'])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    from certification.phase4_grounding_v1.pilot import run
    archive=ROOT/'evidence/phase4-grounding-v1-local.zip';members={};timings={}
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        from unittest.mock import patch
        for mode in ('correct','incorrect','malformed','transport','mismatch'):
            with patch.dict(os.environ,{'GROUNDING_FIXTURE_MODE':mode}):
                report,value=run(folder/mode,ROOT,mode='local',seconds=120,reserve=10)
            assert report['cleanup_verified'] and report['scratch_removed']
            timings[mode]=report['elapsed_seconds']
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    raw=p.read_bytes();name=p.relative_to(folder).as_posix();members[name]=hashlib.sha256(raw).hexdigest();z.writestr(name,raw)
    manifest={'archive':archive.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':members}
    (ROOT/'reports/phase4_grounding_v1_local_archive.json').write_text(json.dumps(manifest,indent=2)+'\n')
    receipt={'tests_passed':result.testsRun,'fixture_elapsed_seconds':timings,'archive_replay':replay_archive(),'model_calls':0,'gpu_runs':0,'environment_actions':0,'scorecards':0}
    (ROOT/'reports/phase4_grounding_v1_local_checks.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay',action='store_true');args=p.parse_args()
    print(json.dumps(replay_archive() if args.replay else build(),indent=2))
