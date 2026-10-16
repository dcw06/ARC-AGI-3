"""Run a bound package, or replay collected outputs. No provider submission code."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

if __name__ == '__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    sub=cli.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run')
    run.add_argument('--packet',required=True)
    run.add_argument('--input-root',default='/kaggle/input')
    run.add_argument('--output',default='/kaggle/working/molmopoint-targeted448-v1')
    score=sub.add_parser('evaluate')
    score.add_argument('--preparation',required=True)
    score.add_argument('--worker',required=True)
    score.add_argument('--model',required=True)
    score.add_argument('--packet',required=True)
    score.add_argument('--output',required=True)
    score.add_argument('--provider-status',choices=['COMPLETE','ERROR'])
    score.add_argument('--cell-stdout',help='retained saved-run cell stdout, not an editor session')
    args=cli.parse_args()
    if args.command=='run':
        from research.molmopoint_identification_v1.supervisor import run
        run(args.packet,input_root=args.input_root,output=args.output)
    else:
        from research.molmopoint_identification_v1.evaluate import evaluate,validate_completion
        from research.molmopoint_identification_v1.inference import sha
        result=evaluate(args.preparation,args.worker,args.model,args.packet)
        if bool(args.provider_status)!=bool(args.cell_stdout):
            raise ValueError('provider status and saved cell stdout must be supplied together')
        if args.provider_status:
            validate_completion(Path(args.worker).parent,args.provider_status,
                Path(args.cell_stdout).read_text(encoding='utf-8'),
                sha((Path(args.packet)/'runtime/runtime-lock.json').read_bytes()))
            result['lifecycle_certified']=True
        with Path(args.output).open('x',encoding='utf-8') as stream:
            json.dump(result,stream,indent=2,sort_keys=True)
