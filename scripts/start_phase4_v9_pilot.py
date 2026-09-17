"""Explicitly approve, reserve, package and submit one frozen v9 GPU attempt."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
EXPECTED='f8211f06a0a45efc137ffbeabeb1b218535c913eccbbb15e485f6c5276d4a3f3'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--verify-only',action='store_true')
    group.add_argument('--authorize-and-launch',action='store_true',
        help='Approve the frozen v9 snapshot and one private offline eight-hour GPU reservation; no retry.')
    args=parser.parse_args()
    review=ROOT/'notebooks/phase4-lifecycle-v9-review-r1/review-source-lock.json'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(review)!=EXPECTED: raise PermissionError('unexpected review lock')
    lock=json.loads(review.read_text())
    for base,key in ((ROOT,'bindings'),(review.parent,'artifacts')):
        for name,expected in lock[key].items():
            if sha(base/name)!=expected: raise PermissionError('snapshot drift: '+name)
    if args.verify_only:
        print('Frozen v9 source and notebook hashes verified. No reservation or upload.')
        return
    claim=ROOT/'config/phase4_v9_pilot_launch_claim.json'
    receipt=ROOT/'reports/phase4_v9_pilot_launch.json'
    if claim.exists() or receipt.exists():
        print('The v9 attempt has already been claimed. No new upload was sent.')
        if receipt.exists():
            previous=json.loads(receipt.read_text())
            print('Recorded submission: '+str(previous.get('url','unknown')))
            print('Recorded outcome: '+str(previous.get('status','unknown')))
            if previous.get('error'): print('The recorded submission has an error; inspect the receipt.')
        print('Monitor with: '+sys.executable+' scripts/observe_phase4_v9_pilot.py')
        return
    existing=[str(ROOT/name) for name in (
        'reports/phase4_v9_source_approval.json',
        'reports/phase4_v9_compute_authorization.json',
        'config/phase4_v9_pilot_execution',
        'config/phase4_v9_pilot_compute_ledger.json',
        'notebooks/phase4-v9-pilot-launch-ready-r1') if (ROOT/name).exists()]
    if existing:
        raise SystemExit('Partial v9 preparation exists; inspect before resuming. No upload sent.\n'+'\n'.join(existing))
    def run(script,*arguments):
        subprocess.run([sys.executable,str(ROOT/'scripts'/script),*arguments],cwd=ROOT,check=True)
    # Every preparation uses exclusive creation. On partial failure, stop for
    # inspection; never silently overwrite authority or retry an upload.
    run('authorize_phase4_v9_pilot.py','--authorize-and-launch')
    run('prepare_phase4_v9_launch.py','--output','notebooks/phase4-v9-pilot-launch-ready-r1',
        '--authority','config/phase4_v9_pilot_execution')
    run('launch_phase4_v9_pilot_once.py','--verify-only')
    run('launch_phase4_v9_pilot_once.py')


if __name__=='__main__': main()
