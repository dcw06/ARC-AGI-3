"""Fetch only the manifest-bound public tokenizer files for a CPU audit."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'certification/phase4_integrated_v2/tokenizer_manifest.json'
OUT = ROOT / 'reports/runs/phase4-grounded-action-v1-r9-tokenizer'


def run(output=OUT):
    manifest = json.loads(MANIFEST.read_bytes())
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    base = 'https://huggingface.co/' + manifest['repo'] + '/resolve/' + manifest['revision'] + '/'
    for name, binding in manifest['files'].items():
        if Path(name).name != name:
            raise ValueError('unsafe tokenizer file name')
        target = output / name
        if target.exists():
            raw = target.read_bytes()
        else:
            request = urllib.request.Request(base + name, headers={'User-Agent': 'stage-b-cpu-token-audit/1'})
            with urllib.request.urlopen(request, timeout=60) as stream:
                raw = stream.read(binding['bytes'] + 1)
            if len(raw) > binding['bytes']:
                raise ValueError('oversized tokenizer file: ' + name)
        if len(raw) != binding['bytes'] or hashlib.sha256(raw).hexdigest() != binding['sha256']:
            raise ValueError('tokenizer manifest mismatch: ' + name)
        if not target.exists():
            target.write_bytes(raw)
    return {'files': len(manifest['files']), 'output': str(output), 'manifest_sha256':
            hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
