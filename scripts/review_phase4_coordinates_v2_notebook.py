"""Verify a frozen review package and its refusal to execute; never upload it."""
import argparse,ast,base64,hashlib,json,lzma,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def review(folder):
    lock=json.loads((folder/'review-source-lock.json').read_bytes())
    for base,key in [(ROOT,'bindings'),(folder,'artifacts')]:
        for name,expected in lock[key].items():
            path=(base/name).resolve()
            if not path.is_relative_to(base.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                raise ValueError('review drift: '+name)
    metadata=json.loads((folder/'kernel-metadata.json').read_bytes())
    assert metadata['enable_gpu'] is False and metadata['enable_tpu'] is False
    assert metadata['enable_internet'] is False and metadata['is_private'] is True
    notebook=json.loads((folder/'profile.ipynb').read_bytes())
    code=next(c['source'] for c in notebook['cells'] if c['cell_type']=='code')
    tree=ast.parse(code);assignment=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='payload' for t in n.targets))
    packed=ast.literal_eval(assignment.value.args[0].args[0].args[0])
    payload=json.loads(lzma.decompress(base64.b85decode(packed)))
    assert set(payload)==set(lock['bindings'])
    for name,encoded in payload.items():
        raw=base64.b64decode(encoded)
        assert hashlib.sha256(raw).hexdigest()==lock['bindings'][name],name
        if name.endswith('.py'):compile(raw,name,'exec')
    assert not any(name.startswith('certification/phase4_coordinates_v2/') and
        Path(name).name in ('execution_lock.json','reservation.json') for name in payload)
    with tempfile.TemporaryDirectory(prefix='transient-review-exec-') as tmp:
        script=Path(tmp)/'review.py';script.write_text(code,encoding='utf-8')
        environment=dict(os.environ,TMP=tmp,TEMP=tmp,TMPDIR=tmp)
        result=subprocess.run([sys.executable,str(script)],cwd=tmp,env=environment,capture_output=True,text=True,timeout=60)
        assert result.returncode!=0 and 'PermissionError: coordinates v2 requires matching source/compute approvals' in result.stderr,result.stderr[-500:]
        assert {p.name for p in Path(tmp).iterdir()}=={'review.py'},'source staging leaked'
    receipt={'status':'package_verified_pending_external_source_review_not_compute_authority',
        'notebook':(folder/'profile.ipynb').relative_to(ROOT).as_posix(),
        'source_bindings_verified':len(payload),'notebook_bytes':(folder/'profile.ipynb').stat().st_size,
        'review_lock_sha256':hashlib.sha256((folder/'review-source-lock.json').read_bytes()).hexdigest(),
        'notebook_sha256':lock['artifacts']['profile.ipynb'],'compiled_all_packaged_python':True,
        'gpu_disabled':True,'internet_disabled':True,'live_gate_refused':True,'temporary_source_removed':True,
        'authorized_seconds':0,'gpu_runs':0}
    print(json.dumps(receipt,indent=2))
    (ROOT/'reports/phase4_coordinates_v2_package_review.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',type=Path,required=True)
    review(parser.parse_args().folder.resolve())
