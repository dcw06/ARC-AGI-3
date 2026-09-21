"""Offline integration check with temporary synthetic authority, never upload."""
import ast,base64,json,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from certification.phase4_transient_v2 import authority as auth
from scripts import phase4_transient_v2_launch as launch
from tests.test_phase4_transient_v2_launch import Backend

def main():
    historical=ROOT/'notebooks/phase4-transient-v1-review-r3/review-source-lock.json'
    assert auth.sha(historical)=='7cf4378b3e4674b6c74ddac119ab4ce8d637272bf2b109b88ebb1605fa0be943'
    old=json.loads(historical.read_bytes())
    for name,digest in old['bindings'].items():assert auth.sha(ROOT/name)==digest,name
    for name,digest in old['artifacts'].items():assert auth.sha(historical.parent/name)==digest,name
    unchanged=[]
    for path in (ROOT/'certification/phase4_transient_v1').glob('*'):
        if path.suffix not in ('.py','.json') or path.name in ('authority.py','build_notebook.py'):continue
        expected=path.read_text().replace('phase4_transient_v1','phase4_transient_v2').replace('phase4-transient-v1','phase4-transient-v2')
        assert expected==(ROOT/'certification/phase4_transient_v2'/path.name).read_text(),path.name
        unchanged.append(path.name)
    review=auth.source_snapshot(ROOT)
    with tempfile.TemporaryDirectory(prefix='tf2-package-test-') as tmp:
        root=Path(tmp)
        names=list(review['bindings'])+[auth.REVIEW]+[str(Path(auth.REVIEW).parent/n) for n in review['artifacts']]
        for name in names:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        for kind in ('source','compute'):launch.record_approval(root,kind,'SYNTHETIC OFFLINE TEST ONLY',auth.sha(root/auth.REVIEW))
        launch.reserve(root);launch.package(root);launch.validate(root)
        notebook=json.loads((root/launch.PACKAGE/'profile.ipynb').read_bytes());code=notebook['cells'][1]['source']
        compile(code,'launch-notebook','exec')
        tree=ast.parse(code)
        assignment=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='authority_payload' for t in n.targets))
        for name,encoded in ast.literal_eval(assignment.value).items():
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(encoded))
        auth.require(root);auth.consume_runtime(root,root)
        backend=Backend();launch.launch(root,backend)
        try:launch.launch(root,backend)
        except PermissionError:pass
        else:raise AssertionError('second upload admitted')
        assert backend.calls==1
        size=(root/launch.PACKAGE/'profile.ipynb').stat().st_size
    assert not any((ROOT/name).exists() for name in (auth.SOURCE,auth.COMPUTE,launch.RESERVATION,launch.CLAIM,launch.RECEIPT,launch.PACKAGE))
    receipt={'status':'offline_package_integration_passed','review_lock_sha256':auth.sha(ROOT/auth.REVIEW),
        'historical_r3_bindings_verified':len(old['bindings']),'unchanged_runtime_files_except_revision_identity':unchanged,
        'synthetic_launch_notebook_bytes':size,'embedded_authority_validated':True,'fake_backend_uploads':1,
        'second_upload_rejected':True,'real_authorizations':0,'gpu_runs':0,
        'local_regressions':{'command':'python -m unittest tests.test_phase4_transient_v2 tests.test_phase4_transient_v2_launch -v','tests_passed':20}}
    (ROOT/'reports/phase4_transient_v2_integration_review.json').write_bytes(launch.data(receipt))
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
