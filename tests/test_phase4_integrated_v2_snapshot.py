"""The actual frozen review snapshot through approval, reservation, packaging and the packaged gate.

Run only after freezing a review revision: it verifies the committed snapshot, not
synthetic fixtures. Everything happens in a temporary copy; no provider is contacted.
"""
import ast,base64,json,lzma,re,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from scripts import phase4_integrated_v2_launch as launch
from certification.phase4_integrated_v2 import authority as auth
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
        revisions=[p for p in (ROOT/'notebooks').glob('phase4-integrated-v2-review-r*') if re.fullmatch(r'.*-r\d+',p.name)]
        newest=max(revisions,key=lambda p:int(p.name.rsplit('-r',1)[1]))
        self.assertEqual(Path(auth.REVIEW).parent.name,newest.name)
        self.assertEqual(launch.REVIEW,auth.REVIEW)

    def test_actual_snapshot_approval_package_and_packaged_gate(self):
        auth.source_snapshot(ROOT) # The working tree must match the referenced lock.
        review=json.loads((ROOT/auth.REVIEW).read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo'
            for name in list(review['bindings'])+[str(Path(auth.REVIEW).parent/n) for n in ('review-source-lock.json','profile.ipynb','kernel-metadata.json')]:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
            review_sha=auth.sha(root/auth.REVIEW)
            for kind in ('source','compute'):launch.record_approval(root,kind,'TEST FIXTURE ONLY',review_sha)
            execution=launch.reserve(root);launch.package(root)
            self.assertEqual(execution['review_lock'],auth.REVIEW)
            backend=Backend();receipt=launch.launch(root,backend)
            self.assertTrue(receipt['attempt_consumed']);self.assertEqual(backend.calls,1)
            with self.assertRaises(PermissionError):launch.launch(root,Backend())
            # Unpack the launch notebook exactly as the Kaggle cell would and run the packaged gate.
            notebook=json.loads((root/launch.PACKAGE/'profile.ipynb').read_bytes())
            code=notebook['cells'][1]['source']
            payload=json.loads(lzma.decompress(base64.b85decode(literal(code,'payload').args[0].args[0].args[0].value)))
            sidecars=ast.literal_eval(literal(code,'authority_payload'))
            source=Path(tmp)/'packaged'
            for name,value in list(payload.items())+list(sidecars.items()):
                target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(value))
            check=('import sys;sys.path.insert(0,sys.argv[1]);'
                   'from certification.phase4_integrated_v2.authority import require;print(require(sys.argv[1])["attempt_id"])')
            result=subprocess.run([sys.executable,'-c',check,str(source)],cwd=source,capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stderr[-800:])
            self.assertEqual(result.stdout.strip(),execution['attempt_id'])
            # The unapproved review notebook itself still refuses.
            (source/'certification/phase4_integrated_v2/reservation.json').unlink()
            result=subprocess.run([sys.executable,'-c',check,str(source)],cwd=source,capture_output=True,text=True,timeout=120)
            self.assertNotEqual(result.returncode,0);self.assertIn('PermissionError',result.stderr)

if __name__=='__main__':unittest.main()
