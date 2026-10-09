"""Check the actual extracted notebook's default verification inputs in an isolated CPU process.

No mounted wheels, installation, network, GPU or model are used. This exercises
the live verifier's default data path, which fixture-input overrides bypass.
"""
import argparse
import ast
import base64
import hashlib
import json
import lzma
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = '''import json, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from certification.direct_publisher_smoke_v1 import preflight as P, install as I
from importlib import import_module
load_protocol = import_module(sys.argv[2] + '.binding').load_protocol
try:
    proposal, artifacts, pins = P.load_inputs()
    protocol = load_protocol(root)
    seen = []
    def verify_fixture(mount, *, package, now):
        # Only the streamed mount hashing is replaced. Default trusted-file
        # loading and dataset/manifest/requirements binding checks are real.
        if package != P.PACKAGE:
            raise ValueError('default shared-package input path changed')
        now()
        seen.append(str(package))
        return {'verification_boundary_reached': True}
    P.verify_mounted = verify_fixture
    result = I.verify_bundle('/unmounted-cpu-check', protocol['dataset'], protocol['bundle'])
    print(json.dumps({'passed': len(artifacts) == len(pins) == 174 and len(seen) == 1,
        'default_inputs_loaded': True, 'trusted_wheels': len(artifacts), **result}))
except Exception as exc:
    message = ('missing default verifier input: ' + Path(exc.filename).relative_to(root).as_posix()
               if isinstance(exc, FileNotFoundError) else str(exc).replace(str(root), '<extracted-notebook>'))
    print(json.dumps({'passed': False, 'default_inputs_loaded': False, 'error_type': type(exc).__name__,
                     'error': message}))
    raise SystemExit(1)
'''


def extract(notebook, folder):
    """Decode the exact reviewed payload, without executing the notebook or its live gate."""
    code = notebook['cells'][1]['source']
    if isinstance(code, list):
        code = ''.join(code)
    tree = ast.parse(code)
    packed = [n.args[0].value for n in ast.walk(tree) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == 'b85decode'
              and len(n.args) == 1 and isinstance(n.args[0], ast.Constant)]
    bindings = [ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'bindings' for t in n.targets)]
    if len(packed) != 1 or len(bindings) != 1:
        raise ValueError('ambiguous notebook payload or bindings')
    payload = json.loads(lzma.decompress(base64.b85decode(packed[0])))
    if set(payload) != set(bindings[0]):
        raise ValueError('embedded inventory differs from bindings')
    folder = Path(folder).resolve()
    for name, encoded in payload.items():
        raw = base64.b64decode(encoded)
        if hashlib.sha256(raw).hexdigest() != bindings[0][name]:
            raise ValueError('embedded byte drift')
        path = (folder / name).resolve()
        if not path.is_relative_to(folder):
            raise ValueError('unsafe embedded path')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def check(notebook, package='research.control_interface_action_selection_v1'):
    if package not in ('research.control_interface_action_selection_v1', 'research.control_interface_action_selection_v2'):
        raise ValueError('unknown extracted probe package')
    with tempfile.TemporaryDirectory(prefix='control-interface-extracted-check-') as folder:
        extract(notebook, folder)
        result = subprocess.run([sys.executable, '-I', '-c', SCRIPT, folder, package],
                                cwd=folder, capture_output=True, text=True, timeout=60)
        try:
            record = json.loads(result.stdout)
        except ValueError:
            record = {'passed': False, 'error_type': 'ChildProcessError', 'stderr': result.stderr[-1000:]}
        record.update(exit_code=result.returncode, evidence_class='cpu_extracted_default_input_check',
                      network_calls=0, gpu_used=False, model_calls=0, mounted_wheel_bytes_checked=False)
        return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', type=int, required=True)
    parser.add_argument('--version', type=int, choices=(1, 2), default=1)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expect-missing-proposal', action='store_true')
    args = parser.parse_args()
    folder = ROOT / f'notebooks/control-interface-action-selection-v{args.version}-review-r{args.revision}'
    record = check(json.loads((folder / 'profile.ipynb').read_bytes()),
                   f'research.control_interface_action_selection_v{args.version}')
    record.update(review_revision=args.revision,
                  review_lock_sha256=hashlib.sha256((folder / 'review-source-lock.json').read_bytes()).hexdigest())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes((json.dumps(record, sort_keys=True, indent=1) + '\n').encode('utf-8'))
    print(json.dumps(record, indent=1))
    if args.expect_missing_proposal:
        return 0 if not record['passed'] and record.get('error_type') == 'FileNotFoundError' and '/proposal.json' in record.get('error', '') else 1
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
