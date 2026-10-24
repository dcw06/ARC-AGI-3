"""Single-attempt HTTP in an owned process, with a parent-side absolute deadline.

No retries or redirects. A timeout does not prove the provider cancelled work.
Only complete atomic result files from a cleanly exited worker are accepted.
"""
import http.client
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import tempfile
import time
from urllib.parse import urlsplit

RESPONSE_BYTES = 8 * 1024 * 1024


class TransportFailure(RuntimeError):
    pass


def _worker(url, method, headers, body, timeout, destination):
    connection = None
    try:
        parsed = urlsplit(url)
        cls = http.client.HTTPSConnection if parsed.scheme == 'https' else http.client.HTTPConnection
        connection = cls(parsed.hostname, parsed.port, timeout=timeout)
        connection.request(method, parsed.path or '/', body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read(RESPONSE_BYTES + 1)
        if len(raw) > RESPONSE_BYTES:
            raise ValueError('response cap')
        result = {'status': response.status, 'body': raw.decode('utf-8'), 'headers': response.getheaders()}
    except Exception as exc:
        # Do not retain headers, credentials, provider error bodies or exception text.
        result = {'error': type(exc).__name__}
    finally:
        if connection is not None:
            connection.close()
    temporary = Path(destination + '.partial')
    with temporary.open('x', encoding='utf-8') as stream:
        os.chmod(temporary, 0o600)
        json.dump(result, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, destination)


def request_once(url, method, headers, body, timeout, *, worker=_worker):
    if timeout <= 0:
        raise TransportFailure('no request time remains')
    folder = Path(tempfile.mkdtemp(prefix='claude-arc-http-'))
    os.chmod(folder, 0o700)
    process = multiprocessing.get_context('spawn').Process(
        target=worker, args=(url, method, headers, body, timeout, str(folder / 'result.json')))
    started = time.monotonic()
    try:
        # A local process object is retained even if interruption occurs during start.
        # Blocking SIGINT during start prevents losing the started worker's ownership.
        import signal
        protected = {signal.SIGINT, signal.SIGTERM}
        previous = signal.pthread_sigmask(signal.SIG_BLOCK, protected) if hasattr(signal, 'pthread_sigmask') else None
        try:
            process.start()
        finally:
            if previous is not None:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous)
        process.join(max(0, timeout - (time.monotonic() - started)))
        if process.is_alive() or process.exitcode != 0 or time.monotonic() - started >= timeout:
            raise TransportFailure('HTTP worker failed or exceeded its absolute deadline; outcome uncertain')
        result = json.loads((folder / 'result.json').read_bytes())
        if 'error' in result:
            raise TransportFailure('HTTP worker failed: ' + result['error'])
        return result
    finally:
        import signal
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM}) if hasattr(signal, 'pthread_sigmask') else None
        try:
            if process.pid is not None:
                if process.is_alive():
                    process.kill()
                process.join(5)
                if process.is_alive():
                    raise TransportFailure('worker termination unconfirmed; temporary evidence preserved')
        finally:
            try:
                if process.pid is None or not process.is_alive():
                    shutil.rmtree(folder)
            finally:
                if mask is not None:
                    signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def json_request(url, body, headers, timeout, transport=request_once):
    encoded = json.dumps(body, separators=(',', ':'), allow_nan=False).encode()
    result = transport(url, 'POST', {**headers, 'Content-Type': 'application/json'}, encoded, timeout)
    if result['status'] != 200:
        raise TransportFailure('provider HTTP ' + str(result['status']) + '; no retry')
    from .config import strict_json
    value = strict_json(result['body'])
    if not isinstance(value, dict):
        raise TransportFailure('provider response must be an object')
    return value
