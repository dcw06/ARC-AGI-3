"""Model-server transport and metrics with absolute deadlines, and server-side cancellation evidence.

Every network operation here takes an absolute deadline on the caller's monotonic clock and is
bounded by it as a whole, not per socket read: the exchange runs on a helper thread and, when the
deadline passes, the caller shuts the socket down and closes it (teardown waits at most
TEARDOWN_SECONDS for the helper, which is a daemon). This applies to inference calls and to every
metrics read.

vLLM 0.19.0's `/v1/chat/completions` route is wrapped in `with_cancellation`, so a client disconnect
cancels the handler and aborts the engine request. That is not assumed: after every timeout the
caller must observe the server idle through its own Prometheus metrics (`vllm:num_requests_running`
and `vllm:num_requests_waiting` both zero) by an absolute deadline. An observation that completes
after the deadline is rejected.

Prefix caching is verified from the same metrics. With caching disabled, vLLM's KV-cache manager
returns before recording any prefix-cache query, so `vllm:prefix_cache_queries_total` stays zero
while `vllm:prompt_tokens_total` grows; with caching enabled, every prompt adds queries. The verdict
is always recomputed from the counters (`cache_verdict`), never carried as a bare flag.
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
TEARDOWN_SECONDS = 1.0       # upper bound on waiting for the helper after shutting a socket down
METRICS_READ_SECONDS = 5.0   # no single metrics read may take longer, even when more time remains


class CallTimedOut(TimeoutError):
    """The call reached its absolute deadline; the connection was shut down and closed."""


class MetricsTimedOut(TimeoutError):
    """A metrics read did not complete by its absolute deadline."""


def _endpoint(base_url):
    parts = urlsplit(base_url)
    if parts.scheme != 'http' or parts.hostname not in ('127.0.0.1', 'localhost') or not parts.port:
        raise ValueError('model server must be a local http endpoint with an explicit port')
    return parts.hostname, parts.port


def _finite(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return value


def bounded_exchange(base_url, method, path, body, deadline, *, limit, clock=time.monotonic, expired=CallTimedOut):
    """One HTTP exchange that finishes, or is torn down, by the absolute `deadline`. Returns (status, raw)."""
    _finite(deadline, 'deadline')
    host, port = _endpoint(base_url)
    remaining = deadline - clock()
    if remaining <= 0:
        raise expired('deadline already passed')
    # The socket's own timeout is longer than the remaining time, so the deadline below always acts first.
    connection = http.client.HTTPConnection(host, port, timeout=remaining + 10)
    outcome = {}

    def exchange():
        try:
            headers = {'Connection': 'close'}
            if body is not None:
                headers['Content-Type'] = 'application/json'
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            outcome['value'] = (response.status, response.read(limit + 1))
        except BaseException as exc:  # reported to the caller unless the deadline already passed
            outcome['error'] = exc

    helper = threading.Thread(target=exchange, daemon=True)
    helper.start()
    helper.join(max(0.0, deadline - clock()))
    if helper.is_alive() or clock() > deadline:
        sock = connection.sock
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        connection.close()
        helper.join(TEARDOWN_SECONDS)
        raise expired(f'{method} {path} did not complete by its absolute deadline; connection closed')
    connection.close()
    if 'error' in outcome:
        raise ConnectionError(type(outcome['error']).__name__ + ': ' + str(outcome['error'])[:200])
    status, raw = outcome['value']
    if len(raw) > limit:
        raise ValueError('response exceeds the byte ceiling')
    return status, raw


class CancellableTransport:
    """transport(request, deadline=None) -> result; raises CallTimedOut after closing the connection.

    The effective deadline is the earlier of `timeout_seconds` from the call's start and the caller's
    absolute `deadline`."""

    def __init__(self, base_url, timeout_seconds, *, clock=time.monotonic):
        if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError('timeout must be a positive finite number')
        _endpoint(base_url)
        self.base_url, self.timeout, self.clock = base_url, timeout_seconds, clock

    def __call__(self, request, deadline=None):
        started = self.clock()
        limit = started + self.timeout if deadline is None else min(started + self.timeout, _finite(deadline, 'deadline'))
        body = json.dumps(request, separators=(',', ':')).encode()
        status, raw = bounded_exchange(self.base_url, 'POST', '/v1/chat/completions', body, limit,
                                       limit=MAX_RESPONSE_BYTES, clock=self.clock)
        if status != 200:
            raise ConnectionError(f'model server returned HTTP {status}')
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
    """Prometheus text exposition -> {'name{labels}': value}; comments, malformed and non-finite lines are ignored."""
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


def read_metrics(base_url, deadline, *, clock=time.monotonic):
    """Read /metrics, finishing by the earlier of `deadline` and METRICS_READ_SECONDS from now."""
    limit = min(_finite(deadline, 'deadline'), clock() + METRICS_READ_SECONDS)
    status, raw = bounded_exchange(base_url, 'GET', '/metrics', None, limit, limit=MAX_METRICS_BYTES, clock=clock,
                                   expired=MetricsTimedOut)
    if status != 200:
        raise ConnectionError('metrics endpoint unavailable')
    return parse_metrics(raw.decode('utf-8', 'replace'))


def server_load(values):
    running = metric_total(values, 'vllm:num_requests_running')
    waiting = metric_total(values, 'vllm:num_requests_waiting')
    aborted = sum(v for k, v in values.items()
                  if k.startswith('vllm:request_success_total{') and 'finished_reason="abort"' in k)
    return {'running': running, 'waiting': waiting, 'aborted_total': aborted}


def idle_verdict(record, window_seconds):
    """Recompute an idle verdict from its measurements: zero running and waiting, observed within the window."""
    try:
        waited = _finite(record.get('waited_seconds'), 'waited')
        running, waiting = record.get('running'), record.get('waiting')
        return (running == 0 and waiting == 0 and type(running) in (int, float) and type(waiting) in (int, float)
                and 0 <= waited <= window_seconds)
    except (ValueError, AttributeError):
        return False


def verify_idle(base_url, deadline, *, clock=time.monotonic, sleep=time.sleep, reader=read_metrics):
    """Poll the server's metrics until it reports nothing running or waiting, by the absolute `deadline`.

    Returns evidence and never raises. An observation completing after the deadline is rejected."""
    started = clock()
    window = deadline - started
    last, error = None, None
    while True:
        now = clock()
        if now >= deadline:
            break
        try:
            values = reader(base_url, deadline, clock=clock)
            observed = clock()
            if observed > deadline:
                error = 'observation completed after the deadline'
                break
            last, error = server_load(values), None
            if last['running'] == 0 and last['waiting'] == 0:
                record = {'idle': True, 'waited_seconds': round(observed - started, 3), 'window_seconds': round(window, 3),
                          **last}
                record['idle'] = idle_verdict(record, window)
                return record
        except Exception as exc:
            error = type(exc).__name__ + ': ' + str(exc)[:120]
        pause = min(0.25, deadline - clock())
        if pause > 0:
            sleep(pause)
    return {'idle': False, 'waited_seconds': round(clock() - started, 3), 'window_seconds': round(window, 3),
            **(last or {'running': None, 'waiting': None, 'aborted_total': None}), 'error': error}


def cache_verdict(counters):
    """Prefix caching verified disabled, recomputed from counters: prompts processed, no prefix-cache query or hit."""
    try:
        prompt = counters.get('prompt_tokens_total')
        queries = counters.get('prefix_cache_queries_total')
        hits = counters.get('prefix_cache_hits_total')
        for value in (prompt, queries) + (() if hits is None else (hits,)):
            if type(value) not in (int, float) or type(value) is bool or not math.isfinite(value) or value < 0:
                return False
        return prompt > 0 and queries == 0 and (hits is None or hits == 0)
    except AttributeError:
        return False


def prefix_caching_evidence(values):
    counters = {'prompt_tokens_total': metric_total(values, 'vllm:prompt_tokens_total'),
                'prefix_cache_queries_total': metric_total(values, 'vllm:prefix_cache_queries_total'),
                'prefix_cache_hits_total': metric_total(values, 'vllm:prefix_cache_hits_total')}
    return {**counters, 'prefix_caching_disabled_verified': cache_verdict(counters)}
