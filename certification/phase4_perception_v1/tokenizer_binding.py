"""Verify small frozen tokenizer files before any live template/token use."""
import hashlib,json
from pathlib import Path

def verify(folder):
    manifest=json.loads(Path(__file__).with_name('tokenizer_manifest.json').read_bytes())
    for name,info in manifest['files'].items():
        path=Path(folder)/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size!=info['bytes']:
            raise ValueError('tokenizer artifact layout: '+name)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:
            raise ValueError('tokenizer artifact hash: '+name)
    return manifest
