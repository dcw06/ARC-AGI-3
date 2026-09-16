"""Export project plus ignored local evidence/assets, excluding credentials/caches."""
import argparse
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = {'agent','certification','config','docs','environment_files','evaluation',
           'evidence','notebooks','reference','reports','scripts','tests','vendor'}
EXCLUDED = {'.git','.kaggle','.venv','.cache','.uv-cache','.uv-python','.uv-bin',
            '__pycache__','.DS_Store','.idea','.vscode','node_modules'}


def files():
    tracked = set(subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'))
    result=[]
    for path in ROOT.rglob('*'):
        rel=path.relative_to(ROOT)
        if any(p in EXCLUDED for p in rel.parts): continue
        if path.is_symlink(): continue
        if not path.is_file(): continue
        if (path.name=='.env' or path.name.startswith('.env.') and path.name!='.env.example'
                or path.suffix in ('.pyc','.lck')
                or path.name in ('access_token','kaggle.json','logs.log')
                or path.name.endswith(('.pem','.p12','.key'))): continue
        if rel.as_posix() not in tracked and rel.parts[0] not in FOLDERS and len(rel.parts)!=1: continue
        if rel.as_posix() not in tracked and len(rel.parts)==1 and path.suffix not in ('.md','.yaml','.json'): continue
        result.append(path)
    return sorted(result)


def secrets():
    # Only used in memory for exclusion checks. Never print or export values.
    values=[]
    env=ROOT/'.env'
    if env.exists():
        for line in env.read_text().splitlines():
            key,sep,value=line.partition('=')
            if sep and re.search(r'(KEY|TOKEN|SECRET|PASSWORD)',key,re.I):
                value=value.strip().strip('\"\'')
                if len(value)>=8: values.append(value.encode())
    token=ROOT/'.kaggle/access_token'
    if token.exists() and len(token.read_bytes().strip())>=8: values.append(token.read_bytes().strip())
    kaggle=ROOT/'.kaggle/kaggle.json'
    if kaggle.exists():
        value=json.loads(kaggle.read_text()).get('key','')
        if len(value)>=8: values.append(value.encode())
    return values


def scan(data, needles, label, depth=0):
    if any(value in data for value in needles):
        raise ValueError('credential value found in selected file: '+label)
    if re.search(rb'-----BEGIN (?:RSA )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/]{20,}',data):
        raise ValueError('private key found in selected file: '+label)
    if data.startswith(b'PK\x03\x04') and depth<3:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for entry in z.infolist():
                if not entry.is_dir(): scan(z.read(entry),needles,label+'!'+entry.filename,depth+1)


def main():
    p=argparse.ArgumentParser();p.add_argument('--scan-only',action='store_true')
    p.add_argument('--output',type=Path);args=p.parse_args()
    selected=files();needles=secrets()
    for path in selected: scan(path.read_bytes(),needles,path.relative_to(ROOT).as_posix())
    if args.scan_only:
        print(json.dumps({'selected_files':len(selected),'credential_scan':'passed_known_values_and_private_keys'}));return
    if args.output is None: p.error('--output required')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','diff','HEAD','--name-only'],cwd=ROOT).strip():
        raise ValueError('tracked worktree differs from commit; commit first')
    inventory={}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='agi-transfer-') as directory:
        bundle=Path(directory)/'repository.bundle'
        subprocess.run(['git','bundle','create',str(bundle),'HEAD'],cwd=ROOT,check=True)
        subprocess.run(['git','bundle','verify',str(bundle)],cwd=ROOT,check=True,capture_output=True)
        with zipfile.ZipFile(args.output,'x',compression=zipfile.ZIP_DEFLATED) as z:
            def add(name,data):
                z.writestr(name,data)
                inventory[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            for path in selected: add('AGI/'+path.relative_to(ROOT).as_posix(),path.read_bytes())
            add('repository.bundle',bundle.read_bytes())
            packages=sorted({(dist.metadata['Name'],dist.version) for dist in importlib.metadata.distributions()})
            add('installed-packages-macos-reference.txt',
                ('# Reference inventory only, not a validated Windows/Linux dependency lock.\n'+
                 '\n'.join(name+'=='+version for name,version in packages)+'\n').encode())
            add('TRANSFER.json',json.dumps({'commit':head,'project_folder':'AGI',
                'git_bundle':'repository.bundle','credentials_included':False,'macos_venv_included':False,
                'live_gpu_authorized':False,'external_model_weights_and_model_wheelhouse_included':False,
                'restore_instructions':'AGI/docs/WINDOWS_TRANSFER.md'},indent=2).encode())
            z.writestr('SHA256-INVENTORY.json',json.dumps(inventory,indent=2))
        with zipfile.ZipFile(args.output) as z:
            if z.testzip() is not None: raise ValueError('ZIP CRC check failed')
            for name,info in inventory.items():
                data=z.read(name)
                if len(data)!=info['bytes'] or hashlib.sha256(data).hexdigest()!=info['sha256']:
                    raise ValueError('archive hash mismatch: '+name)
    print(json.dumps({'zip':str(args.output),'commit':head,'files':len(inventory),
        'bytes':args.output.stat().st_size,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'zip_and_inventory_verification':'passed'}))


if __name__=='__main__': main()
