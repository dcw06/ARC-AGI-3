"""Regenerate the recovered inspection in a temporary directory; preserve history."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile

import inspect_phase4_closed_loop_v1 as generator

def main():
    root = Path(__file__).resolve().parents[1]
    historical = root/'reports/phase4_closed_loop_v1_inspection/inspection-lock.json'
    lock = json.loads(historical.read_bytes())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = sha(historical)
    original_output = generator.OUT
    try:
        with tempfile.TemporaryDirectory(prefix='inspection-recovery-') as folder:
            generator.OUT = Path(folder)
            with contextlib.redirect_stdout(io.StringIO()):
                generator.main()
            for name, expected in lock['bindings'].items():
                retained = root/name
                candidate = generator.OUT/retained.name if retained.parent.name == 'phase4_closed_loop_v1_inspection' else retained
                assert sha(candidate) == expected, name
                assert sha(retained) == expected, name
    finally:
        generator.OUT = original_output
    assert sha(historical) == before
    print(json.dumps({'verified_bindings':len(lock['bindings']),
        'historical_lock_sha256':before,'historical_outputs_overwritten':False}))

if __name__ == '__main__':
    main()
