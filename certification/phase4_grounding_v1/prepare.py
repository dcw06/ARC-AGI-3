"""Prepare the verified interpreter pair and retain bounded install evidence."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import time
from certification.phase4_v6.target_install_probe import verify_wheelhouses
from certification.phase4_v6.target_install_probe_r3 import verify_torch_contract
from certification.phase4_v6.target_install_probe_r5 import install_pair, GAME_CHECK, ISOLATION_CHECK
from certification.phase4_grounding_v1.evidence import EvidenceStore


def prepare(root,output,model,game,manifest,started):
    root,output=Path(root),Path(output)
    deadline=started+450
    def check():
        if time.monotonic()>=deadline-10: raise TimeoutError('installation deadline')
    receipt={'passed':False,'scope':'verified_r5_split_install_for_v13','error':None}
    try:
        receipt['wheelhouses']=verify_wheelhouses(Path(model),Path(game),manifest,check)
        receipt['torch_contract']=verify_torch_contract(model)
        runners=install_pair(root,root/'install-evidence',model,game,deadline)
        runners['game'].execute('game_imports',[runners['game'].python,'-I','-c',GAME_CHECK])
        # No GPU activity before the pilot's independent monitor releases the
        # worker. CUDA readiness is established by r5 and rechecked by live startup.
        model_metadata=ISOLATION_CHECK+"""
assert {n:m.version(n) for n in ('torch','vllm','transformers','numpy')} == {
    'torch':'2.10.0','vllm':'0.19.0','transformers':'4.57.6','numpy':'2.2.6'}
assert importlib.util.find_spec('arcengine') is None
assert importlib.util.find_spec('arc_agi') is None
"""
        runners['model'].execute('model_metadata',[runners['model'].python,'-I','-c',model_metadata])
        check()
        receipt['passed']=True
        receipt['interpreters']={role:runner.python for role,runner in runners.items()}
        return receipt['interpreters']
    except Exception as exc:
        receipt['error']=type(exc).__name__+': '+str(exc)[:512]
        raise
    finally:
        receipt['elapsed_seconds']=time.monotonic()-started
        if (root/'install-evidence').exists():
            for role in ('game','model'):
                folder=root/'install-evidence'/role
                if folder.exists():
                    data={p.name:base64.b64encode(p.read_bytes()).decode()
                          for p in folder.iterdir() if p.is_file()}
                    packed=gzip.compress(json.dumps(data).encode())
                    EvidenceStore(output,'logs').save('install-'+role+'.json',
                        {'encoding':'gzip-base64-json','data':base64.b64encode(packed).decode()})
        EvidenceStore(output,'control').save('installation.json',receipt)
