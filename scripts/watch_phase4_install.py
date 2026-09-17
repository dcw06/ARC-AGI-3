"""Read-only watch/download of the single already-consumed installation attempt."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
deadline = time.monotonic()+1800
while time.monotonic() < deadline:
    poll = subprocess.run([sys.executable, str(ROOT/'scripts/observe_phase4_install.py')],
                          capture_output=True, text=True, timeout=90)
    if poll.returncode:
        print('Read-only status observation failed; no launch retry.', flush=True)
        raise SystemExit(2)
    row = json.loads(poll.stdout)
    print(json.dumps({'observed_at': row['observed_at'], 'status': row['status'],
                      'failure_message': row['failure_message']}), flush=True)
    if row['status'].split('.')[-1] not in ('QUEUED', 'RUNNING'):
        destination = ROOT/'reports/runs/phase4-v6-install-20260917/output'
        download = subprocess.run([sys.executable, str(ROOT/'scripts/phase4_install_kaggle.py'),
            'kernels', 'output', row['kernel'], '-p', str(destination)],
            capture_output=True, text=True, timeout=120)
        print(download.stdout, flush=True)
        if download.returncode:
            print('Output download failed; session was not retried.', flush=True)
            raise SystemExit(3)
        for path in destination.rglob('result.json'):
            print('INSTALLATION_RESULT '+path.read_text(), flush=True)
        raise SystemExit(0)
    time.sleep(30)
print('Monitoring window ended; no new launch requested.', flush=True)
raise SystemExit(4)
