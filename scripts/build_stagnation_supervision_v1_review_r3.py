"""Build an immutable, GPU-disabled Track 3 target review candidate R3; grants no authority."""
import argparse
import base64
import hashlib
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'notebooks/stagnation-supervision-v1-review-r3'
MODE_LINE = "MODE='live'\n"
REVIEW_DOCUMENTS = (
    'reports/stagnation_supervision_v1_protocol_v2.md',
    'reports/stagnation_supervision_v1_ls20_decision.json',
    'reports/stagnation_supervision_v1_derivation_sources_r1.json',
    'reports/stagnation_supervision_v1_token_audit.json',
    'reports/stagnation_supervision_v1_token_audit_provenance_r1.json',
    'reports/stagnation_supervision_v1_token_audit_input_replay_r2.json',
    'reports/stagnation_supervision_v1_connected_review_r3.md',
    'reports/stagnation_supervision_v1_local_checks_r3.json',
    'scripts/derive_stagnation_supervision_v1.py',
    'scripts/build_action_effect_history_v1_review.py',
    'scripts/review_action_effect_history_v1_notebook.py',
    'scripts/build_stagnation_supervision_v1_review_r3.py',
    'scripts/check_stagnation_supervision_v1_review_r3.py',
    'scripts/review_stagnation_supervision_v1_notebook_r3.py',
    'scripts/audit_stagnation_supervision_v1_tokens.py',
    'scripts/verify_stagnation_supervision_v1_audit_inputs_r2.py',
    'scripts/rehearse_stagnation_supervision_v1.py',
    'scripts/evaluate_stagnation_supervision_v1_target.py',
    'tests/test_stagnation_supervision_v1_target.py',
    'tests/test_stagnation_supervision_v1_outcomes.py',
    'tests/test_stagnation_supervision_v1_connected.py',
    'tests/test_stagnation_supervision_v1_token_bridge.py',
    'tests/test_stagnation_supervision_v1_failure_rules.py',
    'tests/test_stagnation_supervision_v1_snapshot.py',
    'tests/test_stagnation_supervision_v1_live_evaluator.py',
    'tests/test_stagnation_supervision_v1_closed_loop.py',
)


def inventory():
    from scripts.build_action_effect_history_v1_review import inventory as inherited
    names = set(inherited())
    for directory in ('research/stagnation_supervision_v1', 'research/transition_evidence_v1',
                      'research/transition_evidence_v2'):
        names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob('*.py')
                     if '__pycache__' not in p.parts)
    names.update(('research/stagnation_supervision_v1/trigger_spec.json',
                  'research/stagnation_supervision_v1/closed_loop/protocol.json',
                  'scripts/stagnation_supervision_v1_launch.py', 'scripts/replay_transition_evidence_v1.py',
                  'scripts/evaluate_stagnation_supervision_v1_target.py'))
    from research.stagnation_supervision_v1.closed_loop.authority import REQUIRED_SOURCE
    if not REQUIRED_SOURCE <= names:
        raise ValueError('package omits required source')
    for name in names:
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('missing or linked review source: ' + name)
    return sorted(names)


def cell(hashes, packed):
    return ('import base64,hashlib,json,lzma,pathlib,shutil,sys,tempfile,time\n'
            'started=time.monotonic()\n' + MODE_LINE + "SESSION='1'\n"
            "source=pathlib.Path(tempfile.mkdtemp(prefix='stagnation-supervision-source-'))\n"
            'try:\n'
            f'    bindings={hashes!r}\n'
            f'    payload=json.loads(lzma.decompress(base64.b85decode({packed!r})))\n'
            '    if set(payload)!=set(bindings): raise ValueError("source inventory")\n'
            '    for name,encoded in payload.items():\n'
            '        raw=base64.b64decode(encoded,validate=True)\n'
            '        if hashlib.sha256(raw).hexdigest()!=bindings[name]: raise ValueError("source hash: "+name)\n'
            '        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)\n'
            '    # SSV_AUTHORITY_SIDECARS: only a separately reviewed launch revision may insert authority.\n'
            '    sys.path.insert(0,str(source))\n'
            '    from scripts.stagnation_supervision_v1_launch import notebook_entry\n'
            '    notebook_entry(source,started,MODE,SESSION)\n'
            'finally:\n'
            '    shutil.rmtree(source)\n')


def build(output=OUT):
    output = Path(output)
    if output.exists():
        raise FileExistsError('review revisions are immutable; choose a new revision')
    audit = json.loads((ROOT / 'reports/stagnation_supervision_v1_token_audit.json').read_bytes())
    if audit.get('all_checks_pass') is not True:
        raise ValueError('token audit must pass before a review freeze')
    from scripts.verify_stagnation_supervision_v1_audit_inputs_r2 import check
    check()
    checks = json.loads((ROOT / 'reports/stagnation_supervision_v1_local_checks_r3.json').read_bytes())
    if checks.get('status') != 'passed_cpu_scope' or checks.get('gpu_runs') != 0:
        raise ValueError('passing CPU test receipt required before review freeze')
    payload = {n: (ROOT / n).read_bytes() for n in inventory()}
    hashes = {n: hashlib.sha256(raw).hexdigest() for n, raw in payload.items()}
    if checks.get('tested_source_bindings') != hashes:
        raise ValueError('packaged source differs from the final tested source')
    packed = base64.b85encode(lzma.compress(json.dumps(
        {n: base64.b64encode(raw).decode() for n, raw in payload.items()}, sort_keys=True).encode(), preset=6)).decode()
    notebook = {'nbformat': 4, 'nbformat_minor': 4,
                'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}},
                'cells': [{'cell_type': 'markdown', 'metadata': {}, 'source':
                           '# Track 3 stagnation supervision: R3 target review candidate\n'
                           'GPU disabled; live execution deliberately rejected. CPU rehearsal is supported. '
                           'Two separately proposed sessions: 15/12 episodes, 600/480 policy calls, '
                           '32 reflections and one canary each. Reservations of 5,400/4,800 seconds are '
                           'proposals only. ls20 is retained with its documented display-novelty limitation. '
                           'This cell selects session 1; it never automatically launches session 2.'},
                          {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [],
                           'source': cell(hashes, packed)}]}
    metadata = {'id': 'daichongwei06/arc3-stagnation-supervision-v1-review-r3',
                'title': 'ARC3 Stagnation Supervision V1 Review R3', 'code_file': 'profile.ipynb',
                'language': 'python', 'kernel_type': 'notebook', 'is_private': True, 'enable_gpu': False,
                'enable_tpu': False, 'enable_internet': False,
                'competition_sources': ['arc-prize-2026-arc-agi-3'],
                'dataset_sources': ['driessmit1/arc3-vllm-h100-wheelhouse-v3'],
                'model_sources': ['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1']}
    encoded = (json.dumps(notebook, indent=2) + '\n').encode()
    if len(encoded) >= 900000:
        raise ValueError('review notebook exceeds upload size guard')
    documents = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in REVIEW_DOCUMENTS}
    output.mkdir(parents=True)
    (output / 'profile.ipynb').write_bytes(encoded)
    (output / 'kernel-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8', newline='\n')
    lock = {'status': 'review_candidate_gpu_disabled', 'scope': 'stagnation-supervision-v1', 'revision': 'r3',
            'bindings': hashes, 'artifacts': {n: hashlib.sha256((output / n).read_bytes()).hexdigest()
                                            for n in ('profile.ipynb', 'kernel-metadata.json')},
            'review_documents': documents, 'authorized_seconds': 0, 'gpu_launch_authorized': False,
            'live_gate_deliberately_disabled': True}
    (output / 'review-source-lock.json').write_text(json.dumps(lock, indent=2) + '\n', encoding='utf-8', newline='\n')
    return lock


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    lock = build(parser.parse_args().output)
    print(json.dumps({'source_files': len(lock['bindings']), 'launch_authorized': False}))
