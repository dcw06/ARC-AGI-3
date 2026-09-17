"""Launch only the explicitly authorized, hash-bound installation probe once."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from phase4_install_kaggle import environment

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'notebooks/phase4-v6-install-check-proposal-r5'
LEDGER = ROOT/'config/phase4_v6_install_r5_compute_ledger.json'
LOCK = ROOT/'config/phase4_v6_install_r5_execution_lock.json'
ATTEMPT = 'p4-v6-install-r5-20260917T121119Z'
MARKER = ROOT/'config/phase4_v6_install_r5_launch_claim.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    temporary = path.with_suffix('.writing')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def validate():
    ledger = json.loads(LEDGER.read_text())
    lock = json.loads(LOCK.read_text())
    if ledger['authorized_seconds'] != 1800 or ledger['maximum_attempts'] != 1:
        raise PermissionError('installation authority mismatch')
    reservations = [e for e in ledger['events'] if e['kind'] == 'reserve']
    if len(reservations) != 1 or reservations[0]['execution_lock_sha256'] != sha(LOCK):
        raise PermissionError('reservation lock mismatch')
    if (reservations[0]['attempt_id'] != ATTEMPT or reservations[0]['seconds'] != 1800
            or lock['attempt_id'] != ATTEMPT or lock['model_pilot_authorized']):
        raise PermissionError('attempt/scope mismatch')
    if MARKER.exists() or any(e.get('attempt_consumed') for e in ledger['events']):
        raise PermissionError('attempt already claimed; no retry authorized')
    review_path = ROOT/lock['review_lock']
    if sha(review_path) != lock['review_lock_sha256']:
        raise PermissionError('review lock drift')
    review = json.loads(review_path.read_text())
    for name, expected in review['bindings'].items():
        if sha(ROOT/name) != expected:
            raise PermissionError('reviewed source drift: '+name)
    for name, expected in review['artifacts'].items():
        if sha(FOLDER/name) != expected:
            raise PermissionError('reviewed artifact drift: '+name)
    metadata = json.loads((FOLDER/'kernel-metadata.json').read_text())
    if (metadata['id'] != lock['kernel_id'] or not metadata['is_private']
            or metadata['enable_internet'] or metadata['model_sources']
            or metadata['machine_shape'] != 'NvidiaRtxPro6000'):
        raise PermissionError('installation metadata scope mismatch')
    return ledger, lock


def main():
    ledger, lock = validate()
    if sys.argv[1:] == ['--verify-only']:
        print('INSTALLATION_LAUNCH_BINDINGS_VERIFIED attempt_unconsumed=true')
        return
    if sys.argv[1:]:
        raise ValueError('unexpected arguments')
    env = environment()
    for key in ('KAGGLE_API_TOKEN', 'KAGGLE_USERNAME', 'KAGGLE_KEY'):
        if env.get(key):
            os.environ[key] = env[key]
    # Bound each HTTP request. Default requests adapters have zero retries;
    # explicitly disable redirects to prevent an ambiguous repeated POST.
    import requests
    original_send = requests.Session.send
    def send(self, request, **kwargs):
        kwargs['timeout'] = (10, 60)
        kwargs['allow_redirects'] = False
        return original_send(self, request, **kwargs)
    requests.Session.send = send
    from kaggle import api
    # Authentication happens before claiming the attempt. No mutation above.
    ledger, lock = validate()
    event = {'kind': 'launch_request_started', 'attempt_id': ATTEMPT,
             'recorded_at': now(), 'attempt_consumed': True,
             'execution_lock_sha256': sha(LOCK), 'charged_or_reserved_seconds': 1800,
             'provider_timeout_requested_seconds': 1800, 'automatic_retries': 0}
    with MARKER.open('x', encoding='utf-8') as stream:
        json.dump(event, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    ledger['events'].append(event)
    write(LEDGER, ledger)
    receipt = {'attempt_id': ATTEMPT, 'recorded_at': now(), 'attempt_consumed': True,
               'exact_provider_billed_seconds': None, 'automatic_retry_authorized': False}
    try:
        response = api.kernels_push(str(FOLDER), timeout='1800', acc='NvidiaRtxPro6000')
        receipt.update(status='provider_response_received', error=response.error,
                       url=response.url, provider_version=response.version_number)
        for field in ('invalid_dataset_sources', 'invalid_competition_sources',
                      'invalid_kernel_sources'):
            receipt[field] = getattr(response, field, None)
    except Exception as exc:
        message = str(exc)
        for key in ('KAGGLE_API_TOKEN', 'KAGGLE_KEY'):
            if env.get(key):
                message = message.replace(env[key], '[REDACTED]')
        receipt.update(status='launch_outcome_unknown_no_retry',
                       error=type(exc).__name__+': '+message[:1000])
    receipt['response_received_at'] = now()
    write(ROOT/'reports/phase4_v6_install_r5_launch.json', receipt)
    ledger['events'].append({'kind': 'launch_receipt', 'attempt_id': ATTEMPT,
        'reference': 'reports/phase4_v6_install_r5_launch.json',
        'status': receipt['status'], 'attempt_consumed': True,
        'charged_or_reserved_seconds': 1800, 'released_seconds': 0})
    write(LEDGER, ledger)
    print(json.dumps(receipt))
    if receipt.get('error'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
