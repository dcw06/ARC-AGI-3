"""Verify a frozen review package: bindings, refusal without authority, notebook-bootstrap rehearsal, approval path."""
import argparse
import ast
import base64
import hashlib
import json
import lzma
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODE_LINE = "MODE='live'\n"
REHEARSAL_SECONDS = 480


def code_cell(folder):
    notebook = json.loads((folder / 'profile.ipynb').read_bytes())
    return next(c['source'] for c in notebook['cells'] if c['cell_type'] == 'code')


def verify_bindings(folder):
    lock = json.loads((folder / 'review-source-lock.json').read_bytes())
    for base, key in ((ROOT, 'bindings'), (folder, 'artifacts'), (ROOT, 'review_documents')):
        for name, expected in lock[key].items():
            path = (base / name).resolve()
            if not path.is_relative_to(base.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('review drift: ' + name)
    metadata = json.loads((folder / 'kernel-metadata.json').read_bytes())
    assert metadata['enable_gpu'] is False and metadata['enable_tpu'] is False
    assert metadata['enable_internet'] is False and metadata['is_private'] is True
    assert lock['authorized_seconds'] == 0 and lock['gpu_launch_authorized'] is False
    code = code_cell(folder)
    assert code.count(MODE_LINE) == 1, 'frozen notebook must run in live mode only'
    assign = next(n for n in ast.walk(ast.parse(code)) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'payload' for t in n.targets))
    payload = json.loads(lzma.decompress(base64.b85decode(assign.value.args[0].args[0].args[0].value)))
    assert set(payload) == set(lock['bindings'])
    for name, encoded in payload.items():
        raw = base64.b64decode(encoded)
        assert hashlib.sha256(raw).hexdigest() == lock['bindings'][name], name
        if name.endswith('.py'):
            compile(raw, name, 'exec')
    return lock, code, payload


def execute(code, env, cwd, timeout):
    script = Path(cwd) / 'cell.py'
    script.write_text(code, encoding='utf-8')
    return subprocess.run([sys.executable, str(script)], cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def review(folder):
    folder = Path(folder).resolve()
    lock, code, payload = verify_bindings(folder)
    base_env = {k: v for k, v in os.environ.items() if not k.startswith('ECV_') and k not in ('PYTHONPATH',)}
    # 1. As frozen (live mode, no authority): refuse before installation and remove the extracted source.
    with tempfile.TemporaryDirectory(prefix='ecv-review-refusal-') as tmp:
        env = dict(base_env, TMP=tmp, TEMP=tmp, TMPDIR=tmp, CUDA_VISIBLE_DEVICES='')
        result = execute(code, env, tmp, 120)
        assert result.returncode != 0 and 'PermissionError' in result.stderr, result.stderr[-600:]
        assert {p.name for p in Path(tmp).iterdir()} == {'cell.py'}, 'extracted source leaked'
    # 2. The same cell with only the MODE token switched: the full connected questionnaire against the CPU fake server.
    from scripts.evaluate_evidence_comprehension_v1 import evaluate_output
    base = Path.home() / 'ecv-review'
    base.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=base))
    (work / 'working').mkdir()
    env = dict(base_env, ECV_REHEARSAL='1', CUDA_VISIBLE_DEVICES='', ECV_REHEARSAL_WORKING=str(work / 'working'),
               ECV_REHEARSAL_SECONDS=str(REHEARSAL_SECONDS), TMPDIR=str(work))
    result = execute(code.replace(MODE_LINE, "MODE='rehearsal'\n"), env, work, 1200)
    assert result.returncode == 0, result.stderr[-1500:]
    output = work / 'working/evidence-comprehension-v1'
    value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=REHEARSAL_SECONDS)
    assert value['technically_complete'], (value['lifecycle_errors'], value['call_errors'])
    assert not any(p.name.startswith('evidence-comprehension-source-') for p in work.iterdir()), 'source not removed'
    # 3. The actual snapshot through the real approval/reservation/package path and the packaged gate.
    snapshot = subprocess.run([sys.executable, '-m', 'unittest', 'tests.test_evidence_comprehension_v1_snapshot'],
                              cwd=ROOT, capture_output=True, text=True, timeout=600)
    assert snapshot.returncode == 0, snapshot.stderr[-1500:]
    receipt = {'status': 'package_verified_pending_independent_review_not_compute_authority',
               'notebook': (folder / 'profile.ipynb').relative_to(ROOT).as_posix(),
               'review_lock_sha256': hashlib.sha256((folder / 'review-source-lock.json').read_bytes()).hexdigest(),
               'source_bindings_verified': len(payload), 'notebook_bytes': (folder / 'profile.ipynb').stat().st_size,
               'compiled_all_packaged_python': True, 'gpu_disabled': True, 'internet_disabled': True,
               'refuses_without_authority_before_installation': True, 'extracted_source_removed': True,
               'notebook_bootstrap_rehearsal': {'technically_complete': True,
                                                'calls_answered': value['run']['counts'].get('answered'),
                                                'gate_status': value['gate_status'],
                                                'note': 'CPU fake server with scripted answers; labels here are not results'},
               'actual_snapshot_approval_package_gate_verified': True, 'authorized_seconds': 0, 'gpu_runs': 0}
    (ROOT / 'reports/evidence_comprehension_v1_package_review.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    print(json.dumps(review(parser.parse_args().folder), indent=2))
