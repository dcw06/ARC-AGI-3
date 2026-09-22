"""Verify small frozen tokenizer files before any live template/token use."""
import hashlib,json
from pathlib import Path

def verify(folder):
    manifest=json.loads(Path(__file__).with_name('tokenizer_manifest.json').read_bytes())
    for name,info in manifest['files'].items():
        path=Path(folder)/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size!=info['bytes']:
            raise ValueError('tokenizer artifact layout: '+name)
        observed=hashlib.sha256(path.read_bytes()).hexdigest()
        if observed!=info['sha256']:
            print(json.dumps({'tokenizer_binding_failure':{'file':name,'expected_sha256':info['sha256'],'observed_sha256':observed,'bytes':path.stat().st_size}}),flush=True)
            raise ValueError('tokenizer artifact hash: '+name+' expected='+info['sha256']+' observed='+observed)
    return manifest
