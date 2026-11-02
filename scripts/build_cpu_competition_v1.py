"""Build the new private CPU notebook; no authentication, upload or submission."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.feedback_probe_v1.source_closure import source_inventory


def raw_json(value):
    return (json.dumps(value,sort_keys=True,indent=1)+'\n').encode()


def build(output, kernel):
    if not kernel.startswith('daichongwei06/') or kernel.count('/') != 1:
        raise ValueError('wrong account binding')
    entries=['research/cpu_competition_v1/supervisor.py','research/cpu_competition_v1/runtime.py',
        'research/cpu_competition_v1/wheels.json','research/cpu_competition_v1/requirements.lock',
        'research/ls20_overfit_v1/policy_seed0.json','tests/test_cpu_competition_v1.py',
        'tests/test_cpu_competition_packaging_v1.py','tests/test_ls20_overfit_v1.py']
    inventory=source_inventory(ROOT,entries)
    payload={name:base64.b64encode((ROOT/name).read_bytes()).decode() for name in inventory}
    code=f'''import base64, hashlib, json, os, pathlib, shutil, sys, tempfile
rerun = os.environ.get('KAGGLE_IS_COMPETITION_RERUN', '').lower()
if rerun not in ('', '0', 'false', '1', 'true'):
    raise RuntimeError('unknown competition phase')
scored = rerun in ('1', 'true')
working = pathlib.Path('/kaggle/working')
working.mkdir(exist_ok=True)
submission = working/'submission.parquet'
if scored and submission.exists():
    submission.unlink() # Remove validation placeholder; only gateway creates scored data.
source = pathlib.Path(tempfile.mkdtemp(prefix='arc3-cpu-source-'))
try:
    payload = {payload!r}
    pins = {inventory!r}
    for name, text in payload.items():
        data = base64.b64decode(text, validate=True)
        if hashlib.sha256(data).hexdigest() != pins[name]:
            raise ValueError('embedded CPU source changed')
        target = source/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    sys.path.insert(0,str(source))
    from research.cpu_competition_v1.supervisor import entry
    candidates = [pathlib.Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels'),
                  pathlib.Path('/kaggle/input/arc-prize-2026-arc-agi-3/arc_agi_3_wheels')]
    available = [p for p in candidates if p.is_dir()]
    if len(available) != 1:
        raise RuntimeError('exact competition CPU wheel mount missing or ambiguous')
    def finish(completed):
        try:
            if completed:
                if scored:
                    if not submission.is_file() or submission.stat().st_size == 0:
                        raise RuntimeError('gateway did not create submission.parquet')
                else:
                    import pandas as pd
                    pd.DataFrame([['1_0','1',True,1]],columns=['row_id','game_id','end_of_game','score']).to_parquet(submission,index=False)
                    print('Validation only: no game calls; placeholder is not a leaderboard score.',flush=True)
        finally:
            shutil.rmtree(source)
    entry(source,available[0],scored=scored,finalize=finish)
finally:
    if source.exists():
        shutil.rmtree(source)
'''
    compile(code,'CPU notebook','exec')
    book=dict(nbformat=4,nbformat_minor=4,metadata=dict(kernelspec=dict(name='python3',language='python',display_name='Python 3'),
        kaggle=dict(accelerator='none',isInternetEnabled=False,isGpuEnabled=False,language='python',sourceType='notebook')),
        cells=[dict(cell_type='markdown',metadata={},source='# ARC3 CPU submission: E0 baseline with exact ls20 demonstration memory\n\nUnseen games use the existing deterministic E0 baseline. The public ls20 specialization does not establish hidden-game performance. No model or GPU.'),
               dict(cell_type='code',metadata={},source=code,execution_count=None,outputs=[])])
    metadata=dict(id=kernel,title='ARC3 CPU LS20 E0 Submission V1',code_file='submission.ipynb',
        language='python',kernel_type='notebook',is_private=True,enable_gpu=False,enable_tpu=False,
        enable_internet=False,dataset_sources=[],model_sources=[],kernel_sources=[],
        competition_sources=['arc-prize-2026-arc-agi-3'],
        docker_image='gcr.io/kaggle-private-byod/python@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461',
        docker_image_pinning_type='original')
    artifacts={'submission.ipynb':book,'kernel-metadata.json':metadata}
    lock=dict(schema='cpu_competition_v1_review',source_hashes=inventory,
        artifact_hashes={name:hashlib.sha256(raw_json(value)).hexdigest() for name,value in artifacts.items()},
        account='daichongwei06',kernel=kernel,scoped_use='Private account-only CPU notebook and outputs; no new external dataset or model attachment.',
        requested_session_timeout_seconds=3600,software_lifecycle_seconds=3300,
        maximum_games=110,maximum_actions_per_general_game=80,maximum_fitted_actions=151,
        maximum_scored_submissions=1,automatic_retries=0,model_generations=0,GPU_jobs=0)
    output.mkdir(parents=True,exist_ok=False)
    for name,value in {**artifacts,'review-lock.json':lock}.items():
        (output/name).write_bytes(raw_json(value))
    print(json.dumps(dict(review_lock_sha256=hashlib.sha256(raw_json(lock)).hexdigest(),
        source_files=len(inventory),notebook_sha256=lock['artifact_hashes']['submission.ipynb'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--kernel',required=True)
    args=parser.parse_args()
    build(args.output,args.kernel)
