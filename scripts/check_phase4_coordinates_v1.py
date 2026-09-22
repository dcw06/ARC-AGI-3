"""CPU-only supervised fixtures and portable evidence; no model/GPU calls."""
import argparse,hashlib,json,os,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def replay_archive():
    verify_sources()
    from certification.phase4_coordinates_v1.cases import generate
    from certification.phase4_coordinates_v1.cases import load_cases
    from certification.phase4_coordinates_v1.replay import replay
    assert generate()==load_cases(),'retained-source case drift'
    manifest=json.loads((ROOT/'reports/phase4_coordinates_v1_local_archive.json').read_bytes())
    archive=ROOT/manifest['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['sha256']
    results={}
    with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(archive) as z:
        folder=Path(tmp);assert set(z.namelist())==set(manifest['members']) and len(z.namelist())==len(manifest['members'])
        for name,digest in manifest['members'].items():
            path=(folder/name).resolve();assert path.is_relative_to(folder.resolve())
            raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==digest
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        for mode in ('correct','transposed','other','malformed','transport','mismatch'):
            value=replay(folder/mode,live=False,seconds=120)
            assert value['passed']==(mode in ('correct','transposed','other','malformed')),(mode,value['errors'])
            results[mode]={'technical_passed':value['passed'],'correct':sum(v.get('correct',0) for v in value['comparison']['by_condition'].values()),
                'malformed':sum(v.get('malformed',0) for v in value['comparison']['by_condition'].values()),'transport_failures':value['comparison']['transport_failures']}
    return results

def verify_sources():
    lockpath=ROOT/'notebooks/phase4-coordinates-v1-review-r2/review-source-lock.json'
    if lockpath.exists():
        lock=json.loads(lockpath.read_bytes())
        for name,h in lock['bindings'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
        for name,h in lock['artifacts'].items():assert hashlib.sha256((lockpath.parent/name).read_bytes()).hexdigest()==h,name

def replay_live(manifest_path):
    # Future downloaded evidence manifests must bind every archive member.
    verify_sources()
    from certification.phase4_coordinates_v1.cases import generate,load_cases
    assert generate()==load_cases(),'source provenance drift'
    from certification.phase4_coordinates_v1.replay import replay
    m=json.loads(manifest_path.read_bytes());archive=manifest_path.parent/m['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['sha256']
    with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(archive) as z:
        root=Path(tmp);assert len(z.namelist())==len(m['members']) and set(z.namelist())==set(m['members'])
        for name,h in m['members'].items():
            raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==h
            path=(root/name).resolve();assert path.is_relative_to(root.resolve())
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        output=(root/m['output_prefix']).resolve();assert output.is_relative_to(root.resolve())
        return replay(output,live=True,seconds=1980)

def build():
    suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_phase4_coordinates_v1','tests.test_phase4_coordinates_v1_lifecycle','tests.test_phase4_coordinates_v1_launch'])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    from certification.phase4_coordinates_v1.pilot import run
    archive=ROOT/'evidence/phase4-coordinates-v1-local.zip';members={};timings={}
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        from unittest.mock import patch
        for mode in ('correct','transposed','other','malformed','transport','mismatch'):
            with patch.dict(os.environ,{'GROUNDING_FIXTURE_MODE':mode}):
                report,value=run(folder/mode,ROOT,mode='local',seconds=120,reserve=10)
            assert report['cleanup_verified'] and report['scratch_removed']
            timings[mode]=report['elapsed_seconds']
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(folder.rglob('*')):
                if p.is_file():
                    raw=p.read_bytes();name=p.relative_to(folder).as_posix();members[name]=hashlib.sha256(raw).hexdigest();z.writestr(name,raw)
    manifest={'archive':archive.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':members}
    (ROOT/'reports/phase4_coordinates_v1_local_archive.json').write_text(json.dumps(manifest,indent=2)+'\n')
    receipt={'tests_passed':result.testsRun,'fixture_elapsed_seconds':timings,'archive_replay':replay_archive(),'model_calls':0,'gpu_runs':0,'environment_actions':0,'scorecards':0}
    (ROOT/'reports/phase4_coordinates_v1_local_checks.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replay',action='store_true');p.add_argument('--live-manifest',type=Path);args=p.parse_args()
    print(json.dumps(replay_live(args.live_manifest) if args.live_manifest else replay_archive() if args.replay else build(),indent=2))
