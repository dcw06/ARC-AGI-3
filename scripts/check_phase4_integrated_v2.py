"""Supervised CPU fixtures and checksum-bound portable replay; no model calls."""
import argparse,hashlib,json,os,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def replay_manifest(path):
 lock=ROOT/'notebooks/phase4-integrated-v2-review-r1/review-source-lock.json'
 if lock.exists():
  frozen=json.loads(lock.read_bytes())
  for name,h in frozen['bindings'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
  for name,h in frozen['artifacts'].items():assert hashlib.sha256((lock.parent/name).read_bytes()).hexdigest()==h,name
 from certification.phase4_integrated_v2.replay import replay
 m=json.loads(path.read_bytes());archive=path.parent/m['archive']
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['sha256']
 result={}
 with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(archive) as z:
  assert len(z.namelist())==len(m['members']) and set(z.namelist())==set(m['members'])
  for name,h in m['members'].items():
   p=(Path(tmp)/name).resolve();assert p.is_relative_to(Path(tmp).resolve());raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==h
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  for mode in m['modes']:
   r=replay(Path(tmp)/mode,live=False,seconds=120);result[mode]={'passed':r['passed'],'errors':r['errors'],'comparison':r.get('comparison')}
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--replay',action='store_true');a=p.parse_args()
 manifest=ROOT/'reports/phase4_integrated_v2_local_archive.json'
 if a.replay:print(json.dumps(replay_manifest(manifest),indent=2));return
 suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_phase4_integrated_v2','tests.test_phase4_integrated_v2_launch','tests.test_phase4_integrated_v2_service'])
 r=unittest.TextTestRunner(verbosity=2).run(suite)
 if not r.wasSuccessful():raise SystemExit(1)
 from certification.phase4_integrated_v2.pilot import run
 modes=('correct','cap','incorrect','invalid','partial_inventory','partial_decision','partial_feedback','v1_inventory','mismatch','transport','cleanup');timings={};results={};members={}
 archive=ROOT/'evidence/phase4-integrated-v2-local.zip'
 with tempfile.TemporaryDirectory() as tmp:
  for mode in modes:
   with patch.dict(os.environ,{'INTEGRATED_FIXTURE':mode}):outer,value=run(Path(tmp)/mode,ROOT,mode='local',seconds=120,reserve=10)
   assert outer['cleanup_verified'] and outer['scratch_removed']
   assert value['passed']==(mode in ('correct','cap','incorrect','invalid','partial_inventory','partial_decision','partial_feedback','v1_inventory')),(mode,value['errors'])
   timings[mode]=outer['elapsed_seconds'];results[mode]=value['passed']
  # Monitor failure also runs independent process cleanup through the supervisor.
  outer,value=run(Path(tmp)/'monitor_failure',ROOT,mode='local',seconds=120,reserve=10,fault='monitor')
  assert not value['passed'] and outer['cleanup_verified'] and outer['scratch_removed']
  with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
   for p in sorted(Path(tmp).rglob('*')):
    if p.is_file():
     raw=p.read_bytes();name=p.relative_to(tmp).as_posix();z.writestr(name,raw);members[name]=hashlib.sha256(raw).hexdigest()
 manifest.write_text(json.dumps({'archive':'../evidence/'+archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':members,'modes':list(modes)},indent=2)+'\n')
 replayed=replay_manifest(manifest)
 assert all(replayed[m]['passed']==results[m] for m in modes)
 report={'tests_passed':r.testsRun,'supervised_results':results,'fixture_seconds':timings,'monitor_failure_rejected_cleanup_verified':True,'archive_replay_verified':True,'model_calls':0,'gpu_runs':0}
 (ROOT/'reports/phase4_integrated_v2_local_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
