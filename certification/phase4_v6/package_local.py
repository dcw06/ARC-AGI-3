"""Archive the retained CPU pilot, review notebook, tests and exact source snapshot."""
import hashlib
import json
from pathlib import Path
import zipfile

from certification.phase4_v4.authority import ROOT


if __name__=='__main__':
    notebook=ROOT/'notebooks/phase4-lifecycle-v6-review-r2'
    lock=json.loads((notebook/'review-source-lock.json').read_text())
    run=ROOT/'reports/runs/phase4-v6-integrated-local-20260916'
    archive=ROOT/'evidence/phase4-v6-integrated-local-review-r2.zip'
    inventory={}
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        entries=[('source/'+name,ROOT/name) for name in lock['bindings']]
        entries += [('notebook/'+p.name,p) for p in notebook.iterdir() if p.is_file()]
        entries += [('run/'+p.relative_to(run).as_posix(),p) for p in run.rglob('*') if p.is_file()]
        for name,path in entries:
            data=path.read_bytes(); digest=hashlib.sha256(data).hexdigest()
            if name.startswith('source/') and digest!=lock['bindings'][name[7:]]:
                raise ValueError('source changed after review snapshot: '+name)
            z.writestr(name,data); inventory[name]={'sha256':digest,'bytes':len(data)}
        z.writestr('inventory.json',json.dumps(inventory,sort_keys=True))
    with zipfile.ZipFile(archive) as z:
        for name,info in inventory.items():
            data=z.read(name)
            if len(data)!=info['bytes'] or hashlib.sha256(data).hexdigest()!=info['sha256']:
                raise ValueError('archive verification failed')
    print(json.dumps({'archive':str(archive.relative_to(ROOT)),
        'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(inventory)}))
