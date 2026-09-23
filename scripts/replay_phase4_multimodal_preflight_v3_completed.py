"""Read-only completed-archive verification and frozen live replay."""
import hashlib,json,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def run():
 lockpath=ROOT/'notebooks/phase4-multimodal-preflight-v3-review-r1/review-source-lock.json'
 lock=json.loads(lockpath.read_bytes())
 for base,key in ((ROOT,'bindings'),(lockpath.parent,'artifacts')):
  for name,h in lock[key].items():assert hashlib.sha256((base/name).read_bytes()).hexdigest()==h,name
 m=json.loads((ROOT/'reports/phase4_multimodal_preflight_v3_completed_archive.json').read_bytes())
 archive=ROOT/'reports'/m['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['sha256']
 from certification.phase4_multimodal_preflight_v3.replay import replay
 with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(archive) as z:
  assert len(z.namelist())==len(m['members']) and set(z.namelist())==set(m['members'])
  for name,h in m['members'].items():
   p=(Path(tmp)/name).resolve();assert p.is_relative_to(Path(tmp).resolve());raw=z.read(name)
   assert hashlib.sha256(raw).hexdigest()==h,name
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  return replay(Path(tmp)/m['output_prefix'],live=True,seconds=1680)
if __name__=='__main__':print(json.dumps(run(),indent=2))
