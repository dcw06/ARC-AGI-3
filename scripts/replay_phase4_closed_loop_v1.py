"""Replay downloaded closed-loop target evidence without model or game execution."""
import argparse,json
from pathlib import Path
from certification.phase4_closed_loop_v1.replay import replay
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=replay(args.output)
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
