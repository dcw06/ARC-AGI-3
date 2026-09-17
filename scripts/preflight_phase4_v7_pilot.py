"""Read-only provider preflight for the separately authorized repaired probe."""
import json
import os
from datetime import datetime, timezone
from phase4_install_kaggle import environment, ROOT

env = environment()
for key in ('KAGGLE_API_TOKEN', 'KAGGLE_USERNAME', 'KAGGLE_KEY'):
    if env.get(key):
        os.environ[key] = env[key]
import requests
original = requests.Session.send
def send(self, request, **kwargs):
    kwargs['timeout'] = (10, 30)
    return original(self, request, **kwargs)
requests.Session.send = send
from kaggle import api

quota = api.quota_view()
seconds = {key: getattr(quota.gpu_quota, key).total_seconds()
           for key in ('time_used', 'time_reserved', 'total_time_allowed')}
previous = api.kernels_status('daichongwei06/arc3-phase4-v6-install-repair-r5')
result = {'recorded_at': datetime.now(timezone.utc).isoformat(),
          'gpu_quota_seconds': seconds, 'previous_attempt_status': str(previous.status),
          'reservation_seconds': 28800, 'provider_hard_stop_verified': False}
result['passed'] = ('COMPLETE' in result['previous_attempt_status'].upper()
                    and seconds['total_time_allowed']-seconds['time_used']-seconds['time_reserved'] >= 28800)
path = ROOT/'reports/phase4_v7_pilot_preflight.json'
with path.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
raise SystemExit(0 if result['passed'] else 1)
