"""Model-server transport with a total per-call deadline and server-side cancellation evidence.

`requests` timeouts bound each socket read, not the whole call. This transport enforces a total
deadline: the response is read on a helper thread, and when the deadline passes the main thread
shuts the socket down and closes it. vLLM 0.19.0's `/v1/chat/completions` route is wrapped in
`with_cancellation`, so a client disconnect cancels the handler and aborts the engine request.
That is not assumed here: after every timeout the caller must observe the server idle through its
own Prometheus metrics (`vllm:num_requests_running` and `vllm:num_requests_waiting` both zero).

Prefix caching is verified from the same metrics. With caching disabled, vLLM's KV-cache manager
returns before recording any prefix-cache query, so `vllm:prefix_cache_queries_total` stays zero
while `vllm:prompt_tokens_total` grows; with caching enabled, every prompt adds queries.
"""
import http.client
import json
import math
import socket
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit

MAX_RESPONSE_BYTES = 1024 * 1024
MAX_METRICS_BYTES = 4 * 1024 * 1024


class CallTimedOut(TimeoutError):
    """The call reached its total deadline; the connection was shut down and closed."""


def _endpoint(base_url):
    parts = urlsplit(base_url)
    if parts.scheme != 'http' or parts.hostname not in ('127.0.0.1', 'localhost') or not parts.port:
        raise ValueError('model server must be a local http endpoint with an explicit port')
    return parts.hostname, parts.port


class CancellableTransport:
    """transport(request) -> result namespace; raises CallTimedOut after closing the connection."""

    def __init__(self, base_url, timeout_seconds, *, clock=time.monotonic):
        if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError('timeout must be a positive finite number')
        self.host, self.port = _endpoint(base_url)
        self.timeout, self.clock = timeout_seconds, clock

    def __call__(self, request):
        body = json.dumps(request, separators=(',', ':')).encode()
        started = self.clock()
        # The socket's own timeout is longer than the total deadline, so the deadline below always acts first.
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout + 10)
        outcome = {}

        def read():
            try:
                connection.request('POST', '/v1/chat/completions', body=body,
                                   headers={'Content-Type': 'application/json', 'Connection': 'close'})
                response = connection.getresponse()
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                outcome['value'] = (response.status, raw)
            except BaseException as exc:  # reported to the caller unless the call already timed out
                outcome['error'] = exc

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        reader.join(self.timeout)
        if reader.is_alive():
            sock = connection.sock
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            connection.close()
            reader.join(5)
            raise CallTimedOut(f'total call deadline of {self.timeout} s reached; connection closed')
        connection.close()
        if 'error' in outcome:
            raise ConnectionError(type(outcome['error']).__name__ + ': ' + str(outcome['error'])[:200])
        status, raw = outcome['value']
        if status != 200:
            raise ConnectionError(f'model server returned HTTP {status}')
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError('model server response exceeds the byte ceiling')
        value = json.loads(raw)
        choice = value['choices'][0]
        content = choice['message']['content']
        if not isinstance(content, str):
            raise ValueError('model server returned no text content')
        usage = value.get('usage') or {}
        return SimpleNamespace(content=content, prompt_tokens=usage.get('prompt_tokens'),
                               completion_tokens=usage.get('completion_tokens'),
                               finish_reason=choice.get('finish_reason'), elapsed_seconds=self.clock() - started)


def parse_metrics(text):
    """Prometheus text exposition -> {'name{labels}': value}; comments and malformed lines are ignored."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, _, rest = line.rpartition(' ')
        if not key:
            continue
        try:
            value = float(rest)
        except ValueError:
            continue
        if math.isfinite(value):
            values[key.strip()] = value
    return values


def metric_total(values, name):
    """Sum of a metric over all label sets, or None when the metric is absent."""
    found = [v for k, v in values.items() if k == name or k.startswith(name + '{')]
    return sum(found) if found else None


def read_metrics(base_url, timeout=5):
    host, port = _endpoint(base_url)
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        connection.request('GET', '/metrics', headers={'Connection': 'close'})
        response = connection.getresponse()
        raw = response.read(MAX_METRICS_BYTES + 1)
    finally:
        connection.close()
    if response.status != 200 or len(raw) > MAX_METRICS_BYTES:
        raise ConnectionError('metrics endpoint unavailable or oversized')
    return parse_metrics(raw.decode('utf-8', 'replace'))


def server_load(values):
    running = metric_total(values, 'vllm:num_requests_running')
    waiting = metric_total(values, 'vllm:num_requests_waiting')
    aborted = sum(v for k, v in values.items()
                  if k.startswith('vllm:request_success_total{') and 'finished_reason="abort"' in k)
    return {'running': running, 'waiting': waiting, 'aborted_total': aborted}


def verify_idle(base_url, within_seconds, *, clock=time.monotonic, sleep=time.sleep, reader=read_metrics):
    """Poll the server's own metrics until no request is running or waiting. Returns evidence; never raises."""
    started = clock()
    last, error = None, None
    while True:
        try:
            last = server_load(reader(base_url))
            error = None
            if last['running'] is not None and last['waiting'] is not None and last['running'] == last['waiting'] == 0:
                return {'idle': True, 'waited_seconds': round(clock() - started, 3), **last}
        except Exception as exc:
            error = type(exc).__name__ + ': ' + str(exc)[:120]
        if clock() - started >= within_seconds:
            return {'idle': False, 'waited_seconds': round(clock() - started, 3), **(last or {}), 'error': error}
        sleep(0.25)


def prefix_caching_evidence(values):
    """Positive evidence that prefix caching is disabled: prompts were processed and no prefix-cache query ran."""
    prompt_tokens = metric_total(values, 'vllm:prompt_tokens_total')
    queries = metric_total(values, 'vllm:prefix_cache_queries_total')
    hits = metric_total(values, 'vllm:prefix_cache_hits_total')
    return {'prompt_tokens_total': prompt_tokens, 'prefix_cache_queries_total': queries,
            'prefix_cache_hits_total': hits,
            'prefix_caching_disabled_verified': (prompt_tokens is not None and prompt_tokens > 0
                                                 and queries is not None and queries == 0
                                                 and (hits is None or hits == 0))}
