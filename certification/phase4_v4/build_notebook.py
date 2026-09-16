"""Build a CPU-disabled-for-GPU, review-only private notebook; never upload."""
import base64
import json
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from certification.phase4_v4.authority import inventory, sha
from scripts.build_m0_profile_notebook import code_cell, markdown_cell, _install_cell
from scripts.build_e1_four_cell_notebook import _arc_install_cell


def build(root=ROOT):
    names = inventory(root)
    lock = {'schema_version': 1, 'status': 'review_snapshot_not_approved_execution',
            'bindings': {name: sha(root / name) for name in names}}
    files = {name: base64.b64encode((root / name).read_bytes()).decode() for name in names}
    ledger = 'certification/phase4_v4/compute_ledger.json'
    if json.loads((root / ledger).read_text())['authorized_seconds'] != 0:
        raise ValueError('review builder requires zero authorization; approved build needs separate review')
    files[ledger] = base64.b64encode((root / ledger).read_bytes()).decode()
    files['certification/phase4_v4/execution_lock.json'] = base64.b64encode(json.dumps(lock).encode()).decode()
    packed = base64.b64encode(zlib.compress(json.dumps(files).encode())).decode()
    install = _install_cell()['source'] + '\n' + _arc_install_cell()['source']
    source = f'''import base64, hashlib, json, os, pathlib, shutil, signal, subprocess, sys, tempfile, time, zlib
started = time.monotonic()
source = pathlib.Path(tempfile.mkdtemp(prefix='p4-v4-review-'))
output = pathlib.Path('/kaggle/working/phase4-development-v4')
output.mkdir(exist_ok=False)
receipt = {{'status':'blocked_or_failed','authorized_seconds':0,'provider_reconciliation_required':True,'phase4_complete':False}}
try:
    for name, payload in json.loads(zlib.decompress(base64.b64decode({packed!r}))).items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(payload))
    gate = "import sys; sys.path.insert(0,sys.argv[1]); from certification.phase4_v4.authority import authority; authority()"
    subprocess.run([sys.executable,'-S','-c',gate,str(source)],check=True,timeout=30)
    # Unreachable in the review build. Verify every selected environment/wheel
    # before installation or environment import; copy no unselected game files.
    manifest = json.loads((source/'reports/phase4_v2_offline_package.json').read_text())
    mount = pathlib.Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3')
    for name, info in manifest['files'].items():
        relative = name.replace('wheels/','arc_agi_3_wheels/',1) if name.startswith('wheels/') else name
        path = mount / relative
        if path.is_symlink() or path.stat().st_size != info['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != info['sha256']:
            raise ValueError('offline artifact mismatch: '+name)
        if name.startswith('environment_files/'):
            dest = source / name
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,dest)
    install = subprocess.Popen([sys.executable,'-c',{install!r}],start_new_session=True)
    try:
        install.wait(timeout=max(1,900-(time.monotonic()-started)))
        if install.returncode: raise RuntimeError('offline installation failed')
    finally:
        try: os.killpg(install.pid,signal.SIGKILL)
        except ProcessLookupError: pass
        install.wait(timeout=5)
    subprocess.run([sys.executable,str(source/'certification/phase4_v4/run_target.py'),
        '--environments',str(source/'environment_files'),'--output',str(output/'run'),
        '--started',str(started)],check=True)
    receipt['status']='worker_completed_pending_independent_evaluation'
finally:
    receipt['elapsed_since_first_cell_seconds']=time.monotonic()-started
    (output/'notebook-cost.json').write_text(json.dumps(receipt))
    shutil.rmtree(source)
'''
    notebook = {'nbformat': 4, 'nbformat_minor': 4,
        'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}},
        'cells': [markdown_cell('# v4 development lifecycle — REVIEW ONLY\nZero authorized compute. GPU disabled. Do not upload or run.\nNot the production one-scorecard/110-distinct-game certification.'), code_cell(source)]}
    metadata = {'id': 'daichongwei06/arc3-phase4-development-v4-review',
        'title': 'ARC3 Phase4 Development v4 REVIEW ONLY', 'code_file': 'profile.ipynb',
        'language': 'python', 'kernel_type': 'notebook', 'is_private': True,
        'enable_gpu': False, 'enable_tpu': False, 'enable_internet': False,
        'competition_sources': ['arc-prize-2026-arc-agi-3'],
        'dataset_sources': ['driessmit1/arc3-vllm-h100-wheelhouse-v3'],
        'model_sources': ['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1']}
    return notebook, metadata, lock


if __name__ == '__main__':
    destination = ROOT / 'notebooks/phase4-lifecycle-v4-review'
    destination.mkdir(parents=True, exist_ok=False)
    notebook, metadata, lock = build()
    for name, value in [('profile.ipynb', notebook), ('kernel-metadata.json', metadata), ('review-source-lock.json', lock)]:
        with (destination / name).open('x') as stream:
            json.dump(value, stream, indent=1)
    print('Built v4 review notebook with GPU disabled and zero authorization; nothing uploaded')
