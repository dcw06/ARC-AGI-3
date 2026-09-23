"""Retain read-only status and account quota observations for the consumed attempt."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
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

launch = json.loads((ROOT/'reports/phase4_multimodal_preflight_v2_pilot_launch.json').read_text())
kernel = launch.get('url','https://www.kaggle.com/code/daichongwei06/arc3-phase4-multimodal-preflight-v2-r1').split('/code/', 1)[1]
row = {'observed_at': datetime.now(timezone.utc).isoformat(),
       'kernel': kernel, 'provider_version': launch.get('provider_version')}
status = api.kernels_status(kernel)
row['status'] = str(status.status)
row['failure_message'] = status.failure_message
try:
    quota = api.quota_view()
    row['account_quota'] = json.loads(quota.to_json())
    row['gpu_quota_seconds'] = {
        key: getattr(quota.gpu_quota, key).total_seconds()
        for key in ('time_used', 'time_reserved', 'total_time_allowed')}
except Exception as exc:
    row['quota_error'] = type(exc).__name__
folder = ROOT/'reports/runs/phase4-multimodal-preflight-v2-r1-pilot'
folder.mkdir(parents=True, exist_ok=True)
with (folder/'provider-observations.jsonl').open('a', encoding='utf-8') as stream:
    stream.write(json.dumps(row)+'\n')
print(json.dumps(row))
