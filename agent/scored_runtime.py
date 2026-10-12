"""Bounded scored-submission runtime. No provider upload/submission capability."""
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

def entry(root, started):
    root = Path(root)
    spec = json.loads((root/'config/scored_submission_v1.json').read_bytes())
    if not os.environ.get('KAGGLE_IS_COMPETITION_RERUN'):
        # The ordinary saved version is an upload/validation artifact, never a model/GPU run.
        import pandas as pd
        pd.DataFrame([['1_0','1',True,1]],columns=['row_id','game_id','end_of_game','score']).to_parquet(
            '/kaggle/working/submission.parquet',index=False)
        return {'mode':'ordinary_version_placeholder_only', 'gpu_started':False}
    if spec.get('source_approved') is not True:
        raise PermissionError('the exact scored package has not been approved')
    if (spec['authorized_seconds'],spec['internal_seconds'],spec['study_cutoff_seconds']) != (3600,3300,3000):
        raise ValueError('scored runtime deadline drift')
    from research.stagnation_supervision_runtime_v2.publisher_process import ModelServer, defer_startup_signals
    from research.stagnation_supervision_runtime_v2.publisher_install import InstallationProcesses
    from research.stagnation_supervision_runtime_v2.prepare import prepare
    from research.stagnation_supervision_runtime_v2.model_binding import model_section
    from certification.phase4_integrated_v2.model_artifact import verify_artifact
    from certification.phase4_integrated_v2.model_process import load_operational_primary
    import requests

    def cutoff(signum, frame):
        raise TimeoutError('scored lifecycle deadline')
    old_handlers = {s:signal.getsignal(s) for s in (signal.SIGALRM,signal.SIGINT,signal.SIGTERM)}
    for signum in old_handlers:
        signal.signal(signum,cutoff)
    signal.setitimer(signal.ITIMER_REAL,max(.01,started+spec['internal_seconds']-time.monotonic()))
    working = Path('/kaggle/working')
    marker = working/('.'+spec['attempt_id']+'.scored-consumed')
    with marker.open('x') as stream:
        stream.write('consumed before any install or GPU access\n')
    scratch = Path(tempfile.mkdtemp(prefix='arc3-scored-dependencies-'))
    model = game = None
    owner = InstallationProcesses(1,2)
    receipt = {'passed':False,'error':None,'policy':'E1S-R','budget_limited':True,'gpu_started':False}
    try:
        owner._adopt_descendants()
        def check():
            if time.monotonic() >= started+3300:
                raise TimeoutError('scored lifecycle deadline')
        hardware = subprocess.run(['nvidia-smi','--query-gpu=name','--format=csv,noheader'],
                                    capture_output=True,text=True,timeout=10,check=True).stdout.splitlines()
        if len(hardware) != 1 or 'RTX PRO 6000' not in hardware[0]:
            raise ValueError('scored attempt requires exactly one RTX PRO 6000')
        receipt['hardware'] = hardware[0]
        competition = Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3')
        if not competition.exists():
            competition = Path('/kaggle/input/arc-prize-2026-arc-agi-3')
        proto = json.loads((root/'research/stagnation_supervision_runtime_v2/protocol.json').read_bytes())
        wheels = Path('/kaggle/input/datasets')/proto['dataset']['ref']
        if not wheels.is_dir():
            wheels = Path('/kaggle/input')/proto['dataset']['ref'].split('/')[1]
        manifest = json.loads((root/proto['competition']['manifest']).read_bytes())
        interpreters = prepare(scratch,scratch/'evidence',wheels,competition/'arc_agi_3_wheels',manifest,
                               started,root=root)
        check()
        section = model_section(root)
        primary = replace(load_operational_primary(root),model_path=Path(section['mounted_path']),
                          model_tree_sha256=section['tree_sha256'])
        if verify_artifact(primary) != {k:section[k] for k in ('tree_sha256','file_count','bytes')}:
            raise ValueError('mounted model bytes differ from the reviewed snapshot')
        server = proto['server']
        from research.stagnation_supervision_runtime_v2.publisher_process import argv_for
        argv = argv_for(server,interpreters['model'],section['mounted_path'],8000)
        model = ModelServer(argv,{**server.get('env',{}),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
                                  'MPLBACKEND':'Agg'},scratch/'model.log','127.0.0.1',8000)
        model.start()
        receipt['gpu_started'] = True
        model.wait_ready(min(started+3000,time.monotonic()+900))
        response = requests.post('http://127.0.0.1:8000/v1/chat/completions',json={
            'model':section['model_id'],'messages':[{'role':'user','content':'Reply exactly OK.'}],
            'temperature':0,'seed':0,'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False}},
            timeout=min(120,max(.01,started+3000-time.monotonic())),allow_redirects=False)
        response.raise_for_status()
        value = response.json()
        tokens = value['usage']['completion_tokens']
        if type(tokens) is not int or not 0 < tokens <= 128 or not value['choices'][0]['message']['content'].strip():
            raise ValueError('startup canary failed')
        env = dict(os.environ, PYTHONPATH=str(root), CUDA_VISIBLE_DEVICES='', MPLBACKEND='Agg')
        game = ModelServer([interpreters['game'],'-B','-m','agent.scored_worker',str(root),str(started),
                            str(scratch/'performance.json')],env,scratch/'worker.log','127.0.0.1',0)
        game.start()
        while game.process.poll() is None:
            check()
            time.sleep(.1)
        if game.process.returncode:
            raise RuntimeError('scored worker failed; no successful agent result claimed')
        receipt['performance'] = json.loads((scratch/'performance.json').read_bytes())
        artifact = working/'submission.parquet'
        if not artifact.is_file() or artifact.stat().st_size <= 0:
            raise ValueError('competition gateway did not produce submission.parquet')
    except BaseException as exc:
        receipt['error'] = type(exc).__name__+': '+str(exc)[:300]
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        cleanup = []
        # Handled interrupts cannot skip later cleanup phases. The server owners retain uncertainty.
        try:
            with defer_startup_signals():
                for group in (game,model):
                    if group is not None:
                        cleanup.append(group.stop(started+3300,1,3))
                receipt['groups_absent'] = all(row['groups_absent'] for row in cleanup)
                try:
                    gpu = subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],
                                          capture_output=True,text=True,timeout=10)
                    receipt['gpu_cleanup_verified'] = gpu.returncode == 0 and not gpu.stdout.strip()
                except BaseException as exc:
                    receipt['gpu_cleanup_verified'] = False
                    receipt['error'] = receipt['error'] or type(exc).__name__+': GPU cleanup check failed'
                try:
                    installation_cleanup = owner.stop(time.monotonic()+10)
                    if not installation_cleanup['groups_absent'] or installation_cleanup['error']:
                        receipt['error'] = receipt['error'] or 'subreaper/process cleanup not verified'
                finally:
                    try:
                        shutil.rmtree(scratch)
                        if not root.name.startswith('arc3-scored-source-'):
                            raise ValueError('scored source removal requires its extraction prefix')
                        shutil.rmtree(root)
                        receipt['source_and_dependencies_removed'] = True
                    except BaseException as exc:
                        receipt['source_and_dependencies_removed'] = False
                        receipt['error'] = receipt['error'] or type(exc).__name__+': source/dependency removal failed'
                certify(working,receipt,started,defer_startup_signals)
        except BaseException as exc:
            receipt['passed'] = False
            receipt['error'] = receipt['error'] or type(exc).__name__+': finalization interrupted'
            (working/'scored-finalization-pending.json').write_text('{"failed":true}\n')
            (working/'scored-lifecycle.json').write_text(json.dumps(receipt,sort_keys=True)+'\n')
        finally:
            for signum,handler in old_handlers.items():
                signal.signal(signum,handler)
    if not receipt['passed']:
        raise RuntimeError(json.dumps(receipt))
    return receipt

def certify(working, receipt, started, protect):
    """A late/interrupting evidence write leaves a durable refusal barrier."""
    pending = working/'scored-finalization-pending.json'
    destination = working/'scored-lifecycle.json'
    pending.write_text('{"finalizing":true}\n')
    receipt['elapsed_seconds'] = time.monotonic()-started
    receipt['passed'] = (receipt['error'] is None and receipt.get('groups_absent') is True
                         and receipt.get('gpu_cleanup_verified') is True
                         and receipt.get('source_and_dependencies_removed') is True
                         and receipt['elapsed_seconds'] < 3300)
    destination.write_text(json.dumps(receipt,sort_keys=True)+'\n')
    with protect():
        receipt['elapsed_seconds'] = time.monotonic()-started
        if receipt['elapsed_seconds'] >= 3300:
            receipt['passed'] = False
            receipt['error'] = receipt['error'] or 'deadline exceeded during final evidence write'
            destination.write_text(json.dumps(receipt,sort_keys=True)+'\n')
            return
        if not receipt['passed']:
            return
        pending.unlink()
        if time.monotonic()-started >= 3300:
            pending.write_text('{"failed":true}\n')
            receipt['passed'] = False
            receipt['error'] = 'deadline exceeded during finalization barrier removal'
            destination.write_text(json.dumps(receipt,sort_keys=True)+'\n')
