"""Prepare a separate installation-only proposal; never upload or authorize it."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build(output):
    names = ['certification/phase4_v6/target_install_probe.py',
             'certification/phase4_v6/build_install_probe_r2.py',
             'certification/phase4_v6/target_install_probe_r2.py',
             'certification/phase4_v6/clean_environment.py',
             'reports/phase4_v2_offline_package.json']
    payload = {name: (ROOT/name).read_bytes() for name in names}
    bindings = {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}
    encoded = {name: base64.b64encode(data).decode() for name, data in payload.items()}
    code = f'''import base64, hashlib, json, pathlib, tempfile, sys
payload={encoded!r}
bindings={bindings!r}
decoded={{name:base64.b64decode(value) for name,value in payload.items()}}
assert all(hashlib.sha256(data).hexdigest()==bindings[name] for name,data in decoded.items())
source_root=pathlib.Path(tempfile.mkdtemp(prefix='p4-install-r2-source-'))
for name,data in decoded.items():
    destination=source_root/name
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(data)
sys.path.insert(0,str(source_root))
from certification.phase4_v6.target_install_probe_r2 import run
candidates=[pathlib.Path('/kaggle/input/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3'),
            pathlib.Path('/kaggle/input/arc3-vllm-h100-wheelhouse-v3')]
model=next((path for path in candidates if path.is_dir()),candidates[0])
manifest=json.loads(decoded['reports/phase4_v2_offline_package.json'])
result=run(model,
    pathlib.Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels'),
    manifest,pathlib.Path('/kaggle/working/phase4-v6-install-check'))
print(json.dumps(result))
if not result['passed']: raise RuntimeError('target installation check failed; retain result and logs')
'''
    notebook = {'nbformat': 4, 'nbformat_minor': 4,
        'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}},
        'cells': [{'cell_type': 'markdown', 'metadata': {}, 'source':
            '# Installation-only proposal — NOT AUTHORIZED FOR UPLOAD\n'
            'Separate fresh RTX PRO 6000 session. Fresh isolated venv, frozen offline wheels, '
            'dependency check, exact package versions, CUDA tensor smoke and cleanup. '
            'No model weights, game play, holdouts, pilot, or scored submission. '
            '900-second internal ceiling; provider time must be reconciled separately.'},
            {'cell_type': 'code', 'metadata': {}, 'execution_count': None,
             'outputs': [], 'source': code}]}
    metadata = {'id': 'daichongwei06/arc3-phase4-v6-install-repair-r2',
        'title': 'ARC3 Phase4 v6 Install Repair R2', 'code_file': 'profile.ipynb',
        'language': 'python', 'kernel_type': 'notebook', 'is_private': True,
        'enable_gpu': True, 'machine_shape': 'NvidiaRtxPro6000', 'enable_tpu': False,
        'enable_internet': False, 'competition_sources': ['arc-prize-2026-arc-agi-3'],
        'dataset_sources': ['driessmit1/arc3-vllm-h100-wheelhouse-v3'], 'model_sources': []}
    proposal = {'status': 'proposal_not_authorization_or_reservation',
        'scope': 'installation_check_only_separate_from_model_pilot',
        'attempts': 1, 'automatic_retries': 0, 'internal_seconds': 900,
        'proposed_reserved_seconds': 1800, 'authorized_seconds': 0,
        'provider_hard_stop_verified': False,
        'note': 'Reservation is accounting, not a provider-enforced cutoff. Reconcile actual usage, including failures.',
        'prescreen_credit_seconds': 0, 'pilot_authorized_seconds': 0}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, value in [('profile.ipynb', notebook), ('kernel-metadata.json', metadata),
                        ('budget-proposal.json', proposal)]:
        (output/name).write_text(json.dumps(value, indent=1), encoding='utf-8')
    lock = {'status': 'installation_probe_review_snapshot_not_execution_approval',
            'bindings': bindings, 'artifacts': {name: hashlib.sha256((output/name).read_bytes()).hexdigest()
                for name in ('profile.ipynb', 'kernel-metadata.json', 'budget-proposal.json')}}
    (output/'review-source-lock.json').write_text(json.dumps(lock, indent=2), encoding='utf-8')
    return lock


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output)))
