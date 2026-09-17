"""Retain one CPU development pilot and compare requests/actions with v3 archive."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import zipfile

from certification.phase4_v10.pilot import run, ROOT
from certification.phase4_v10.evidence import EvidenceStore


def signature(worker):
    requests=defaultdict(list)
    for row in worker['requests']: requests[row['client_id']].append(row['request_sha256'])
    actions={row['client_id']: [(a['action_id'],a['action_data'],a.get('post_state'),a.get('post_hash'))
                              for a in row['dispatch_audit']] for row in worker['clients']}
    return dict(requests),actions


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    report,result=run(args.output,ROOT/'reports/runs/phase4-v2-assets/environment_files')
    if not result['passed'] or 'worker' not in report:
        summary={'scope':'local_actual_development_scripted_model_injected_GPU',
            'passed':False, 'error':report.get('error'),
            'evaluation_errors':result.get('errors', []),
            'historical_v3_evaluation':result.get('historical_v3_evaluation'),
            'local_cpu_smoke_seconds':result.get('local_cpu_smoke_seconds'),
            'elapsed_seconds':report['elapsed_seconds'],
            'cleanup_verified':report.get('cleanup_verified', False),
            'request_invariance':None, 'action_invariance':None,
            'model_inference':False, 'phase4_complete':False, 'authorized_seconds':0}
        EvidenceStore(args.output,'evaluation').save('local-summary.json',summary)
        print(json.dumps(summary))
        return 1
    archive=ROOT/'evidence/phase4-v3-terminal-lifecycle-evidence-portable.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!='b50632d597290cf28f8e4735c5232172685e2b38c470d2c8e496a29f192074b0':
        raise ValueError('historical comparison archive drift')
    with zipfile.ZipFile(archive) as z:
        historical=json.loads(z.read('run/worker.json'))
    old_requests,old_actions=signature(historical)
    new_requests,new_actions=signature(report['worker'])
    summary={'scope':'local_actual_development_scripted_model_injected_GPU',
        'passed':result['passed'], 'clients':len(report['worker']['clients']),
        'historical_v3_evaluation':result.get('historical_v3_evaluation'),
        'local_cpu_smoke_seconds':result.get('local_cpu_smoke_seconds'),
        'requests':len(report['worker']['requests']), 'elapsed_seconds':report['elapsed_seconds'],
        'request_invariance':old_requests==new_requests,'action_invariance':old_actions==new_actions,
        'historical_comparison':'v3 archived scripted run; not a randomized performance comparison',
        'model_inference':False,'phase4_complete':False,'authorized_seconds':0}
    EvidenceStore(args.output,'evaluation').save('local-summary.json',summary)
    print(json.dumps(summary))
    return 0 if summary['passed'] and summary['request_invariance'] and summary['action_invariance'] else 1


if __name__=='__main__':
    raise SystemExit(main())
