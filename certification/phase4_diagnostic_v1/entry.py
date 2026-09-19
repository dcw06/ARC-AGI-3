"""First-cell lifecycle clock includes installation, pilot, evaluation and removal."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from certification.phase4_diagnostic_v1.live_probes import require_live_authority
from certification.phase4_diagnostic_v1.evidence import EvidenceStore


def main():
    require_live_authority()  # No imports of model/game libraries before authority.
    parser=argparse.ArgumentParser()
    parser.add_argument('--started',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    started=args.started
    if not 0<=time.monotonic()-started<900: raise TimeoutError('invalid first-cell clock')
    root=Path(__file__).resolve().parents[2]
    output=args.output
    output.mkdir(exist_ok=False)
    control=EvidenceStore(output,'control')
    manifest=json.loads((root/'reports/phase4_v2_offline_package.json').read_text())
    mount=Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3')
    candidates=[Path('/kaggle/input/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3'),
                Path('/kaggle/input/arc3-vllm-h100-wheelhouse-v3')]
    model=next(path for path in candidates if path.is_dir())
    from certification.phase4_diagnostic_v1.prepare import prepare
    error=None
    try:
        games=mount/'environment_files'  # Unused by diagnostic: no environment calls.
        with tempfile.TemporaryDirectory(prefix='p4-v13-dependencies-') as folder:
            pair=prepare(Path(folder),output,model,mount/'arc_agi_3_wheels',manifest,started)
            # Run orchestration/evaluation in the game interpreter. It owns
            # monitor and worker groups; the model bridge inherits worker PGID.
            code="""import sys,signal,time
def deadline(*_): raise TimeoutError('absolute pilot finalization deadline')
signal.signal(signal.SIGALRM,deadline)
remaining=float(sys.argv[3])+3297-time.monotonic()
if remaining<=0: raise TimeoutError('pilot clock exhausted before launch')
signal.setitimer(signal.ITIMER_REAL,remaining)
from certification.phase4_diagnostic_v1.pilot import run
report,result=run(sys.argv[1],sys.argv[2],mode='live',seconds=3300,reserve=300,
    started=float(sys.argv[3]),prepared=True,game_python=sys.argv[4],model_python=sys.argv[5])
raise SystemExit(0 if result['passed'] else 1)
"""
            # The pilot's own supervisor enforces the clock through group cleanup.
            environment={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV')}
            environment.update(MPLBACKEND='Agg',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',
                               MPLCONFIGDIR=str(Path(folder)/'control-matplotlib'))
            from certification.phase4_diagnostic_v1.dependencies import freeze,thaw
            try:
                freeze(folder)
                process=subprocess.run([pair['game'],'-c',code,str(output),str(games),
                    str(started),pair['game'],pair['model']],cwd=root,env=environment)
                if process.returncode: raise RuntimeError('pilot or independent evaluation failed')
            finally:
                thaw(folder)
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc)[:512]
    elapsed=time.monotonic()-started
    if elapsed>=3300: error=error or 'dependency removal exceeded first-cell deadline'
    if error:
        result_path=output/'evaluation/result.json'
        if result_path.exists():
            result=json.loads(result_path.read_text())
            result.update(passed=False,development_model_lifecycle_passed=False,
                          capacity_candidate=None,C_nominal=None,C_admit=None)
            result.setdefault('errors',[]).append(error)
            EvidenceStore(output,'evaluation').save('result.json',result)
    control.save('notebook-cost.json',{'elapsed_seconds':elapsed,'error':error,
        'dependency_trees_removed':not Path(folder).exists() if 'folder' in locals() else None,
        'provider_reconciliation_required':True,'phase4_complete':False})
    if error: raise RuntimeError(error)

if __name__=='__main__': main()
