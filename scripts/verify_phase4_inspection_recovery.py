"""Regenerate the recovered inspection in a temporary directory; preserve history."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import shutil
import zipfile

import inspect_phase4_closed_loop_v1 as generator

def main():
    root = Path(__file__).resolve().parents[1]
    historical = root/'reports/phase4_closed_loop_v1_inspection/inspection-lock.json'
    lock = json.loads(historical.read_bytes())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = sha(historical)
    original_output = generator.OUT
    original_root = generator.ROOT
    newline_adaptations = []
    try:
        with tempfile.TemporaryDirectory(prefix='inspection-recovery-') as folder:
            # A clean checkout contains archives, not ignored reports/runs assets.
            # Give the unchanged historical generator a private archive-backed root.
            shadow = Path(folder)/'checkout'
            receipt = json.loads((root/'reports/phase4_closed_loop_v1_evidence_receipt.json').read_bytes())
            names = ['reports/phase4_closed_loop_v1_evidence_receipt.json', receipt['archive'],
                'notebooks/phase4-closed-loop-v1-review-r1/review-source-lock.json',
                'reports/phase4_v2_offline_package.json', 'agent/representation.py',
                'certification/phase4_closed_loop_v1/contract.py',
                'evidence/phase4-v2-development-offline.zip']
            for name in names:
                target = shadow/name
                if not target.resolve().is_relative_to(shadow.resolve()):
                    raise ValueError('unsafe archive reference')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root/name, target)
            manifest = json.loads((shadow/'reports/phase4_v2_offline_package.json').read_bytes())
            with zipfile.ZipFile(shadow/'evidence/phase4-v2-development-offline.zip') as archive:
                for name, info in manifest['files'].items():
                    if not name.startswith('environment_files/'):
                        continue
                    target = shadow/'reports/runs/phase4-v2-assets'/name
                    if not target.resolve().is_relative_to(shadow.resolve()):
                        raise ValueError('unsafe game path')
                    raw = archive.read(name)
                    if len(raw) != info['bytes'] or hashlib.sha256(raw).hexdigest() != info['sha256']:
                        raise ValueError('game archive drift: '+name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
            generator.ROOT = shadow
            generator.OUT = Path(folder)/'output'
            with contextlib.redirect_stdout(io.StringIO()):
                generator.main()
            for name, expected in lock['bindings'].items():
                retained = root/name
                candidate = generator.OUT/retained.name if retained.parent.name == 'phase4_closed_loop_v1_inspection' else retained
                # The recovered generator used native text newlines on Windows.
                # Recreate those bytes on Linux only when the historical hash proves
                # the conversion exact; never normalize retained files or binary PNGs.
                if sha(candidate) != expected and candidate.parent == generator.OUT and candidate.suffix in ('.json','.html'):
                    converted = candidate.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
                    if hashlib.sha256(converted).hexdigest() == expected:
                        candidate.write_bytes(converted)
                        newline_adaptations.append(name)
                assert sha(candidate) == expected, name
                assert sha(retained) == expected, name
    finally:
        generator.OUT = original_output
        generator.ROOT = original_root
    assert sha(historical) == before
    print(json.dumps({'verified_bindings':len(lock['bindings']),
        'historical_lock_sha256':before,'historical_outputs_overwritten':False,
        'generated_text_newline_adaptations':newline_adaptations}))

if __name__ == '__main__':
    main()
