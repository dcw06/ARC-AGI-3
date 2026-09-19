"""CPU-only diagnostic lifecycle; no install, model inference, or GPU access."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from certification.phase4_closed_loop_v1.pilot import run

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report,result=run(args.output,ROOT,mode='local',seconds=120,reserve=10)
    print(json.dumps({'passed':result['passed'],'errors':result['errors'],
        'requests_started':report.get('worker',{}).get('requests_started'),
        'elapsed_seconds':report['elapsed_seconds'],'model_inference':False,
        'cleanup_verified':report['cleanup_verified'],'scratch_removed':report['scratch_removed']}))
    raise SystemExit(0 if result['passed'] else 1)
