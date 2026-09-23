"""Supervised CPU evidence with read-only portable replay; never uses a model."""
import hashlib,json,os,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
MODES={'verified':True,'incorrect':True,'invalid':True,'mismatch':False,'transport':False,'evidence':False}
MANIFEST=ROOT/'reports/phase4_perception_v1_local_archive.json'
def replay_archive():
    from certification.phase4_perception_v1.replay import replay
    m=json.loads(MANIFEST.read_bytes());archive=ROOT/m['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['sha256']
    results={}
    with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==len(m['members']) and set(z.namelist())==set(m['members'])
        for name,h in m['members'].items():
            p=(Path(tmp)/name).resolve();assert p.is_relative_to(Path(tmp).resolve())
            raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==h
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        for mode,want in MODES.items():
            result=replay(Path(tmp)/mode,live=False,seconds=120)
            assert result['passed']==want,(mode,result['errors']);results[mode]=result['passed']
    return results
def build():
    suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_phase4_perception_v1','tests.test_phase4_perception_v1_launch'])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    from certification.phase4_perception_v1.pilot import run
    members={};timings={}
    archive=ROOT/'evidence/phase4-perception-v1-local.zip'
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        for mode in MODES:
            with patch.dict(os.environ,{'PREFLIGHT_FIXTURE_MODE':mode}):report,value=run(folder/mode,ROOT,mode='local',seconds=120,reserve=10)
            assert report['cleanup_verified'] and report['scratch_removed'];timings[mode]=report['elapsed_seconds']
        for fault in ('monitor','cancel'):
            report,value=run(folder/fault,ROOT,mode='local',seconds=12,reserve=10,fault=fault)
            assert not value['passed'] and report['cleanup_verified'] and report['scratch_removed']
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    raw=p.read_bytes();name=p.relative_to(folder).as_posix();members[name]=hashlib.sha256(raw).hexdigest();z.writestr(name,raw)
    m={'archive':archive.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':members}
    MANIFEST.write_bytes((json.dumps(m,indent=2)+'\n').encode())
    value={'tests_passed':result.testsRun,'fixture_elapsed_seconds':timings,'archive_replay':replay_archive(),
        'monitor_and_cancellation_cleanup_verified':True,'model_calls':0,'gpu_runs':0,'environment_actions':0,'scorecards':0}
    (ROOT/'reports/phase4_perception_v1_local_checks.json').write_bytes((json.dumps(value,indent=2)+'\n').encode());return value
if __name__=='__main__':print(json.dumps(replay_archive() if '--replay' in sys.argv else build(),indent=2))
