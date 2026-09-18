"""Explicit one-shot replacement; preserve the original ambiguous attempt."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    flags=parser.add_mutually_exclusive_group(required=True)
    flags.add_argument('--verify-only',action='store_true')
    flags.add_argument('--authorize-and-launch',action='store_true')
    args=parser.parse_args()
    review=ROOT/'notebooks/phase4-lifecycle-v12-review-r1/review-source-lock.json'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(review)!='c9123cab5b4409f4333bb01a4cda091a4f920e79fa70a30810375814e9b35542':
        raise PermissionError('unexpected v12 source lock')
    lock=json.loads(review.read_text())
    for base,key in ((ROOT,'bindings'),(review.parent,'artifacts')):
        for name,expected in lock[key].items():
            if sha(base/name)!=expected: raise PermissionError('source drift: '+name)
    if args.verify_only:
        print('Frozen v12 verified; no reservation or upload.');return
    claim=ROOT/'config/phase4_v12_pilot_launch_claim.json'
    if claim.exists():
        print('R1 already claimed. No upload sent. Use scripts/observe_phase4_v12_pilot.py.');return
    for name in ('reports/phase4_v12_compute_authorization.json',
                 'config/phase4_v12_pilot_execution',
                 'config/phase4_v12_pilot_compute_ledger.json',
                 'notebooks/phase4-v12-pilot-launch-ready-r1'):
        if (ROOT/name).exists(): raise SystemExit('Partial R1 preparation exists; inspect before resuming: '+name)
    def run(name,*arguments):
        subprocess.run([sys.executable,str(ROOT/'scripts'/name),*arguments],cwd=ROOT,check=True)
    run('authorize_phase4_v12_pilot.py','--authorize-and-launch')
    run('prepare_phase4_v12_launch.py','--output','notebooks/phase4-v12-pilot-launch-ready-r1',
        '--authority','config/phase4_v12_pilot_execution')
    run('launch_phase4_v12_pilot_once.py','--verify-only')
    run('launch_phase4_v12_pilot_once.py')

if __name__=='__main__':main()
