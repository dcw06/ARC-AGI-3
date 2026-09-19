"""Launch the frozen diagnostic v2 pilot once with a fresh separate reservation."""
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
    review=ROOT/'notebooks/phase4-action-diagnostic-v2-review-r1/review-source-lock.json'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(review)!='4c3cbe6204b310fcf1111604b7bccc7417f283220709619f02f62be4cb20d82c':
        raise PermissionError('unexpected diagnostic v2 source lock')
    lock=json.loads(review.read_text())
    for base,key in ((ROOT,'bindings'),(review.parent,'artifacts')):
        for name,expected in lock[key].items():
            if sha(base/name)!=expected: raise PermissionError('source drift: '+name)
    if args.verify_only:
        print('Frozen diagnostic v2 verified; no reservation or upload.');return
    claim=ROOT/'config/phase4_diagnostic_v2_r2_pilot_launch_claim.json'
    if claim.exists():
        print('R1 already claimed. No upload sent. Use scripts/observe_phase4_diagnostic_v2.py.');return
    for name in ('reports/phase4_diagnostic_v2_r2_compute_authorization.json',
                 'config/phase4_diagnostic_v2_r2_pilot_execution',
                 'config/phase4_diagnostic_v2_r2_pilot_compute_ledger.json',
                 'notebooks/phase4-diagnostic-v2-pilot-launch-ready-r2'):
        if (ROOT/name).exists(): raise SystemExit('Partial R1 preparation exists; inspect before resuming: '+name)
    def run(name,*arguments):
        subprocess.run([sys.executable,str(ROOT/'scripts'/name),*arguments],cwd=ROOT,check=True)
    run('authorize_phase4_diagnostic_v2.py','--authorize-and-launch')
    run('prepare_phase4_diagnostic_v2_launch.py','--output','notebooks/phase4-diagnostic-v2-pilot-launch-ready-r2',
        '--authority','config/phase4_diagnostic_v2_r2_pilot_execution')
    run('launch_phase4_diagnostic_v2_once.py','--verify-only')
    run('launch_phase4_diagnostic_v2_once.py')

if __name__=='__main__':main()
