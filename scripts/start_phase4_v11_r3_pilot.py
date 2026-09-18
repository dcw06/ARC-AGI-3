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
    review=ROOT/'notebooks/phase4-lifecycle-v11-review-r1/review-source-lock.json'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(review)!='ef3e387d2df10e14aff9951fedb930bfce49e627f77c51cbea63ed04708e26eb':
        raise PermissionError('unexpected v11 source lock')
    lock=json.loads(review.read_text())
    for base,key in ((ROOT,'bindings'),(review.parent,'artifacts')):
        for name,expected in lock[key].items():
            if sha(base/name)!=expected: raise PermissionError('source drift: '+name)
    if args.verify_only:
        print('Frozen v11 verified; no reservation or upload.');return
    claim=ROOT/'config/phase4_v11_r3_pilot_launch_claim.json'
    if claim.exists():
        print('R3 already claimed. No upload sent. Use scripts/observe_phase4_v11_r3_pilot.py.');return
    for name in ('reports/phase4_v11_r3_compute_authorization.json',
                 'config/phase4_v11_r3_pilot_execution',
                 'config/phase4_v11_r3_pilot_compute_ledger.json',
                 'notebooks/phase4-v11-pilot-launch-ready-r3'):
        if (ROOT/name).exists(): raise SystemExit('Partial R3 preparation exists; inspect before resuming: '+name)
    def run(name,*arguments):
        subprocess.run([sys.executable,str(ROOT/'scripts'/name),*arguments],cwd=ROOT,check=True)
    run('authorize_phase4_v11_r3_pilot.py','--authorize-and-launch')
    run('prepare_phase4_v11_r3_launch.py','--output','notebooks/phase4-v11-pilot-launch-ready-r3',
        '--authority','config/phase4_v11_r3_pilot_execution')
    run('launch_phase4_v11_r3_pilot_once.py','--verify-only')
    run('launch_phase4_v11_r3_pilot_once.py')

if __name__=='__main__':main()
