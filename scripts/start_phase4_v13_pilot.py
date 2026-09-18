"""Launch the frozen v13 pilot once with a fresh separate reservation."""
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
    review=ROOT/'notebooks/phase4-lifecycle-v13-review-r1/review-source-lock.json'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(review)!='b7acedd48bb452debf7a0a1fa0ecc04f96126b2976745cdd301b3d4177bc0e05':
        raise PermissionError('unexpected v13 source lock')
    lock=json.loads(review.read_text())
    for base,key in ((ROOT,'bindings'),(review.parent,'artifacts')):
        for name,expected in lock[key].items():
            if sha(base/name)!=expected: raise PermissionError('source drift: '+name)
    if args.verify_only:
        print('Frozen v13 verified; no reservation or upload.');return
    claim=ROOT/'config/phase4_v13_pilot_launch_claim.json'
    if claim.exists():
        print('R1 already claimed. No upload sent. Use scripts/observe_phase4_v13_pilot.py.');return
    for name in ('reports/phase4_v13_compute_authorization.json',
                 'config/phase4_v13_pilot_execution',
                 'config/phase4_v13_pilot_compute_ledger.json',
                 'notebooks/phase4-v13-pilot-launch-ready-r1'):
        if (ROOT/name).exists(): raise SystemExit('Partial R1 preparation exists; inspect before resuming: '+name)
    def run(name,*arguments):
        subprocess.run([sys.executable,str(ROOT/'scripts'/name),*arguments],cwd=ROOT,check=True)
    run('authorize_phase4_v13_pilot.py','--authorize-and-launch')
    run('prepare_phase4_v13_launch.py','--output','notebooks/phase4-v13-pilot-launch-ready-r1',
        '--authority','config/phase4_v13_pilot_execution')
    run('launch_phase4_v13_pilot_once.py','--verify-only')
    run('launch_phase4_v13_pilot_once.py')

if __name__=='__main__':main()
