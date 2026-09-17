"""Package approved v9 sources with separate authority sidecars; never upload."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'notebooks/phase4-lifecycle-v9-review-r1'
APPROVAL=ROOT/'reports/phase4_v9_source_approval.json'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def build(output,authority):
    approval=json.loads(APPROVAL.read_text())
    if approval['status']!='approved' or approval['review_lock_sha256']!=sha(REVIEW/'review-source-lock.json'):
        raise PermissionError('approved source snapshot required')
    review=json.loads((REVIEW/'review-source-lock.json').read_text())
    for name,expected in review['bindings'].items():
        if sha(ROOT/name)!=expected: raise ValueError('approved source drift: '+name)
    for name,expected in review['artifacts'].items():
        if sha(REVIEW/name)!=expected: raise ValueError('approved artifact drift: '+name)
    sidecars={
        'certification/phase4_v9/execution_lock.json':(authority/'execution_lock.json').read_bytes(),
        'certification/phase4_v9/compute_ledger.json':(authority/'compute_ledger.json').read_bytes(),
        'notebooks/phase4-lifecycle-v9-review-r1/review-source-lock.json':(REVIEW/'review-source-lock.json').read_bytes(),
        'reports/phase4_v9_source_approval.json':APPROVAL.read_bytes()}
    execution=json.loads(sidecars['certification/phase4_v9/execution_lock.json'])
    if (execution['review_lock']!='notebooks/phase4-lifecycle-v9-review-r1/review-source-lock.json'
            or execution['review_sha256']!=approval['review_lock_sha256']
            or execution['source_approval_reference']!='reports/phase4_v9_source_approval.json'):
        raise ValueError('execution/source approval mismatch')
    encoded={name:base64.b64encode(data).decode() for name,data in sidecars.items()}
    hashes={name:hashlib.sha256(data).hexdigest() for name,data in sidecars.items()}
    notebook=json.loads((REVIEW/'profile.ipynb').read_text(encoding='utf-8'))
    injection=f'''    authority_payload={encoded!r}
    authority_hashes={hashes!r}
    for name,value in authority_payload.items():
        data=base64.b64decode(value)
        if hashlib.sha256(data).hexdigest()!=authority_hashes[name]: raise ValueError('authority sidecar drift')
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
'''
    code=notebook['cells'][1]['source']
    marker='    sys.path.insert(0,str(source))\n'
    if code.count(marker)!=1: raise ValueError('unexpected approved notebook wrapper')
    notebook['cells'][1]['source']=code.replace(marker,injection+marker)
    notebook['cells'][0]['source']='# V9 single development pilot launch package\nApproved sources; compute authority remains separate. An unreserved proposal fails before installation. No retries or production certification.'
    metadata=json.loads((REVIEW/'kernel-metadata.json').read_text())
    metadata.update(id='daichongwei06/arc3-phase4-development-v9-pilot',
        title='ARC3 Phase4 Development V9 Pilot',enable_gpu=True,machine_shape='NvidiaRtxPro6000')
    output.mkdir(parents=True,exist_ok=False)
    for name,value in [('profile.ipynb',notebook),('kernel-metadata.json',metadata)]:
        (output/name).write_text(json.dumps(value,indent=1),encoding='utf-8')
    lock={'approved_source_lock_sha256':approval['review_lock_sha256'],
          'sidecars':hashes,'packager_sha256':sha(Path(__file__)),
          'artifacts':{name:sha(output/name) for name in ('profile.ipynb','kernel-metadata.json')}}
    (output/'launch-package-lock.json').write_text(json.dumps(lock,indent=2))
    return lock

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--authority',type=Path,required=True)
    print(json.dumps(build(**vars(p.parse_args()))))
