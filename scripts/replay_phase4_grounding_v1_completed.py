"""Read-only archive replay: no credentials, ignored downloads, or GPU required."""
import hashlib,json,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def run():
    sha=lambda raw:hashlib.sha256(raw).hexdigest()
    lockpath=ROOT/'notebooks/phase4-grounding-v1-review-r1/review-source-lock.json'
    assert sha(lockpath.read_bytes())=='eb3e074882be085de238135b7bc10871cb6290abb085f946aee833c1dfd79370'
    lock=json.loads(lockpath.read_bytes())
    for name,h in lock['bindings'].items():assert sha((ROOT/name).read_bytes())==h,name
    manifest=json.loads((ROOT/'reports/phase4_grounding_v1_completed_archive.json').read_bytes())
    archive=ROOT/manifest['archive'];assert sha(archive.read_bytes())==manifest['sha256']
    from scripts.build_phase4_grounding_v1 import generate
    from certification.phase4_grounding_v1.cases import load_cases
    assert generate()==load_cases(),'source-grid reconstruction drift'
    with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(archive) as z:
        folder=Path(tmp)
        assert len(z.namelist())==len(manifest['members']) and set(z.namelist())==set(manifest['members'])
        for name,h in manifest['members'].items():
            raw=z.read(name);assert sha(raw)==h,name
            path=(folder/name).resolve();assert path.is_relative_to(folder.resolve())
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        downloads=json.loads((folder/'receipts/phase4_grounding_v1_download.json').read_bytes())
        for row in downloads['files']:
            raw=(folder/'download'/row['path']).read_bytes()
            assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
        reservation=folder/'receipts/phase4_grounding_v1_reservation.json'
        assert reservation.read_bytes()==(ROOT/'config/phase4_grounding_v1_reservation.json').read_bytes()
        assert json.loads(reservation.read_bytes())['status']=='consumed'
        from certification.phase4_grounding_v1.replay import replay
        result=replay(folder/'download/phase4-grounding-v1',live=True,seconds=1680)
        assert result['passed'],result['errors']
        return result
if __name__=='__main__':print(json.dumps(run(),indent=2))
