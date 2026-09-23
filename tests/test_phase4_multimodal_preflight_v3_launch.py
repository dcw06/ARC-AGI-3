"""Synthetic local approvals only; never contact a provider."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from scripts import phase4_multimodal_preflight_v3_launch as launch
from certification.phase4_multimodal_preflight_v3 import authority as auth

class Backend:
    def __init__(self,fail=False,remaining=7200):self.calls=0;self.fail=fail;self.remaining=remaining
    def quota(self):return dict(total_time_allowed=self.remaining,time_used=0,time_reserved=0)
    def push(self,folder):
        self.calls+=1
        if self.fail:raise TimeoutError('synthetic')
        return SimpleNamespace(url='https://example.invalid/test',version_number=1,error=None)

class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        bindings={}
        for name in ('authority.py','worker.py','probes.py','cases.py','cases.json','images.py','service.py','evaluate.py','entry.py','protocol.json'):
            path='certification/phase4_multimodal_preflight_v3/'+name
            self.write(path,b'{}' if name.endswith('.json') else b'# synthetic fixture\n');bindings[path]=auth.sha(self.root/path)
        path='scripts/phase4_multimodal_preflight_v3_launch.py';self.write(path,b'# synthetic fixture\n');bindings[path]=auth.sha(self.root/path)
        folder=Path(auth.REVIEW).parent
        self.write(str(folder/'profile.ipynb'),launch.data({'cells':[{'source':''},{'source':'try:\n    sys.path.insert(0,str(source))\nfinally:\n    pass\n'}]}))
        self.write(str(folder/'kernel-metadata.json'),launch.data(dict(enable_gpu=False,enable_internet=False,is_private=True)))
        self.write(auth.REVIEW,launch.data(dict(bindings=bindings,artifacts={n:auth.sha(self.root/folder/n) for n in ('profile.ipynb','kernel-metadata.json')})))
    def write(self,name,raw):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    def mutate(self,name,key,value):
        obj=auth.read(self.root,name);obj[key]=value;self.write(name,launch.data(obj))
    def approve(self):
        for kind in ('source','compute'):launch.record_approval(self.root,kind,'TEST FIXTURE ONLY',auth.sha(self.root/auth.REVIEW))
    def prepare(self):self.approve();launch.reserve(self.root);launch.package(self.root)
    def blocked(self):
        backend=Backend()
        with self.assertRaises((PermissionError,ValueError,FileNotFoundError)):launch.launch(self.root,backend)
        self.assertEqual(backend.calls,0)
    def test_missing_approvals_and_reservation(self):
        self.blocked();self.approve();self.blocked()
    def test_missing_each_receipt(self):
        self.prepare()
        for name in (auth.SOURCE,auth.COMPUTE,launch.RESERVATION):
            raw=(self.root/name).read_bytes();(self.root/name).unlink();self.blocked();self.write(name,raw)
    def test_approval_mutations(self):
        self.prepare()
        for name,key,value in [(auth.SOURCE,'status','consumed'),(auth.COMPUTE,'status','consumed'),
            (auth.SOURCE,'scope','wrong'),(auth.COMPUTE,'review_lock_sha256','wrong'),
            (auth.COMPUTE,'source_approval_sha256','wrong'),(auth.COMPUTE,'authorized_seconds',7200),
            (auth.COMPUTE,'maximum_attempts',True),(auth.SOURCE,'user_response','')]:
            with self.subTest(key=key,value=value):
                raw=(self.root/name).read_bytes();self.mutate(name,key,value);self.blocked();self.write(name,raw)
    def test_reservation_mutations(self):
        self.prepare()
        for name,key,value in [(launch.RESERVATION,'status','consumed'),(launch.RESERVATION,'attempt_id','mm3-wrong-id'),
            (launch.RESERVATION,'seconds',1799),(launch.RESERVATION,'events',['reserve','consumed']),
            (launch.RESERVATION,'execution_sha256','wrong'),(launch.EXECUTION,'review_sha256','wrong')]:
            with self.subTest(key=key):
                raw=(self.root/name).read_bytes();self.mutate(name,key,value);self.blocked();self.write(name,raw)
    def test_source_and_package_drift(self):
        self.prepare()
        for name in ('certification/phase4_multimodal_preflight_v3/worker.py',launch.PACKAGE+'/profile.ipynb',launch.PACKAGE+'/kernel-metadata.json'):
            raw=(self.root/name).read_bytes();self.write(name,raw+b' ');self.blocked();self.write(name,raw)
    def test_one_upload_and_no_reuse(self):
        self.prepare();backend=Backend();receipt=launch.launch(self.root,backend)
        self.assertTrue(receipt['attempt_consumed']);self.assertEqual(backend.calls,1);self.blocked()
        with self.assertRaises(PermissionError):launch.reserve(self.root)
    def test_unknown_outcome_consumes(self):
        self.prepare();backend=Backend(fail=True);receipt=launch.launch(self.root,backend)
        self.assertEqual(receipt['status'],'launch_outcome_unknown_no_retry');self.assertEqual(backend.calls,1);self.blocked()
    def test_quota_fails_before_claim(self):
        self.prepare()
        for value in (1799,float('nan'),float('inf'),-1,True):
            backend=Backend(remaining=value)
            with self.assertRaises(PermissionError):launch.launch(self.root,backend)
            self.assertEqual(backend.calls,0);self.assertFalse((self.root/launch.CLAIM).exists())
    def test_existing_claim_rejects(self):
        self.prepare();self.write(launch.CLAIM,b'{}');self.blocked()
    def test_runtime_ticket_consumed_once(self):
        self.prepare();execution,reservation=launch.validate(self.root)
        prefix='certification/phase4_multimodal_preflight_v3/'
        self.write(prefix+'execution_lock.json',launch.data(execution));self.write(prefix+'reservation.json',launch.data(reservation))
        auth.consume_runtime(self.root,self.root)
        with self.assertRaises(FileExistsError):auth.consume_runtime(self.root,self.root)
        self.mutate(prefix+'reservation.json','status','consumed')
        with self.assertRaises(PermissionError):auth.require(self.root)

if __name__=='__main__':unittest.main()
