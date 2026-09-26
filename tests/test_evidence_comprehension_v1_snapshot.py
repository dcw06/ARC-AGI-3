"""The actual frozen review snapshot through approval, reservation, packaging and the packaged gate.

Run after freezing a review revision. Everything happens in a temporary copy; no provider is contacted.
"""
import ast,base64,json,lzma,re,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from scripts import evidence_comprehension_v1_package as package
from research.evidence_comprehension_v1 import authority as auth
ROOT=Path(__file__).resolve().parents[1]

class Backend:
    calls=0
    def quota(self):return dict(total_time_allowed=7200,time_used=0,time_reserved=0)
    def push(self,folder):
        self.calls+=1;return SimpleNamespace(url='https://example.invalid/snapshot',version_number=1,error=None)

def literal(code,target):
    node=next(n for n in ast.walk(ast.parse(code)) if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id==target for t in n.targets))
    return node.value

class ActualSnapshotTests(unittest.TestCase):
    def test_review_reference_is_newest_revision(self):
        revisions=[p for p in (ROOT/'notebooks').glob('evidence-comprehension-v1-review-r*') if re.fullmatch(r'.*-r\d+',p.name)]
        newest=max(revisions,key=lambda p:int(p.name.rsplit('-r',1)[1]))
        self.assertEqual(Path(auth.REVIEW).parent.name,newest.name)

    def test_actual_snapshot_approval_package_and_packaged_gate(self):
        review=json.loads((ROOT/auth.REVIEW).read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo'
            names=list(review['bindings'])+[str(Path(auth.REVIEW).parent/n) for n in ('review-source-lock.json','profile.ipynb','kernel-metadata.json')]
            for name in names:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
            review_sha=package.digest(root,auth.REVIEW)
            for kind in ('source','compute'):package.record_approval(root,kind,'TEST FIXTURE ONLY',review_sha)
            execution=package.reserve(root);package.package(root)
            backend=Backend();receipt=package.launch(root,backend)
            self.assertTrue(receipt['attempt_consumed']);self.assertEqual(backend.calls,1)
            with self.assertRaises(PermissionError):package.launch(root,Backend())
            notebook=json.loads((root/package.PACKAGE/'profile.ipynb').read_bytes());code=notebook['cells'][1]['source']
            self.assertEqual(code.count("MODE='live'"),1)
            payload=json.loads(lzma.decompress(base64.b85decode(literal(code,'payload').args[0].args[0].args[0].value)))
            sidecars=json.loads(lzma.decompress(base64.b85decode(literal(code,'authority_payload').args[0].args[0].args[0].value)))
            source=Path(tmp)/'packaged'
            for name,value in list(payload.items())+list(sidecars.items()):
                target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(value))
            check=('import sys;sys.path.insert(0,sys.argv[1]);'
                   'from research.evidence_comprehension_v1.authority import require;print(require(sys.argv[1])["attempt_id"])')
            result=subprocess.run([sys.executable,'-c',check,str(source)],cwd=source,capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stderr[-800:]);self.assertEqual(result.stdout.strip(),execution['attempt_id'])
            # After the one launch, the packaged reservation is still the reserved copy, but a removed one must refuse.
            (source/auth.RESERVATION).unlink()
            result=subprocess.run([sys.executable,'-c',check,str(source)],cwd=source,capture_output=True,text=True,timeout=120)
            self.assertNotEqual(result.returncode,0);self.assertIn('PermissionError',result.stderr)

if __name__=='__main__':unittest.main()
