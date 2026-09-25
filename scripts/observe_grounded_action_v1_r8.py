"""Record read-only Kaggle status and quota for the one-shot Stage B R8 attempt."""
from datetime import datetime, timezone
import json
import os

from scripts.phase4_install_kaggle import environment, ROOT


def observe():
    launch = json.loads((ROOT / 'reports/perception_stage_b_r8_launch.json').read_bytes())
    if launch.get('attempt_consumed') is not True or launch.get('provider_version') != 1:
        raise ValueError('Stage B R8 launch receipt is not an accepted attempt')
    url = launch['url']
    if url != 'https://www.kaggle.com/code/daichongwei06/arc3-grounded-action-v1-r8':
        raise ValueError('unexpected Stage B R8 provider URL')
    env = environment()
    for key in ('KAGGLE_API_TOKEN', 'KAGGLE_USERNAME', 'KAGGLE_KEY'):
        if env.get(key):
            os.environ[key] = env[key]
    import requests
    original = requests.Session.send

    def send(session, request, **kwargs):
        kwargs['timeout'] = (10, 30)
        kwargs['allow_redirects'] = False
        return original(session, request, **kwargs)

    requests.Session.send = send
    from kaggle import api
    status = api.kernels_status(url.split('/code/', 1)[1])
    row = {'observed_at': datetime.now(timezone.utc).isoformat(),
           'attempt_id': launch['attempt_id'], 'url': url,
           'provider_version': launch['provider_version'],
           'status': str(status.status),
           'failure_message': (status.failure_message or '')[:1000]}
    try:
        quota = api.quota_view().gpu_quota
        row['gpu_quota_seconds'] = {key: getattr(quota, key).total_seconds()
                                    for key in ('time_used', 'time_reserved',
                                                'total_time_allowed')}
    except Exception as exc:
        row['quota_error'] = type(exc).__name__
    folder = ROOT / 'reports/runs/phase4-grounded-action-v1-r8'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'provider-observations.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, sort_keys=True) + '\n')
    return row


if __name__ == '__main__':
    print(json.dumps(observe(), sort_keys=True))
