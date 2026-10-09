"""The study phase's model service on the verified runtime (hand-written adapter).

It keeps the reviewed per-call contract of research/evidence_comprehension_v1/service.py (QuestionnaireService), which
the WS3/Track 2 runner was written against, and changes only how the server is reached: every HTTP request goes
through the verified runtime's counted client (certification/direct_publisher_smoke_v1/client.py), so the request
ledger, its cap and the admission cutoff govern the study exactly as they govern every other request. Per call:
- only requests whose hash belongs to the frozen set are served, and at most the scheduled number of them;
- admission uses the pinned tokenizer's prompt count from the session's token audit (the offline `transformers`
  count, with pure-Python parity) against the reviewed ceilings, as the reviewed service admitted by tokenizer;
- inference has an absolute deadline (+timeout). After an answer, the server's own counters must show prefix caching
  disabled by +timeout+teardown+verify (the evaluator recomputes the verdict and the counter advance). After a
  timeout the verified client has closed the connection (client cancellation) and the server must be observed idle,
  nothing running or waiting, by the same deadline; otherwise the service stops;
- token parity: the server's prompt-token count must equal the audited count, as the reviewed bridge required;
- the runner sees errors as 'Type: message', as the reviewed bridge reported them, and a reply after the call's whole
  bound is rejected, as the reviewed proxy rejected late replies.
Constructing the service starts nothing; the counted client and the clock are injected.
"""
import json
import time

from certification.direct_publisher_smoke_v1.client import Client, RequestFailed
from research.evidence_comprehension_v1.transport import (MAX_METRICS_BYTES, METRICS_READ_SECONDS, cache_verdict,
                                                          idle_verdict, metric_total, parse_metrics, server_load)
from research.evidence_memory_v1.successor import plan as PL

STARTUP_CACHE_CHECK_SECONDS = 15  # research/evidence_comprehension_v1/service.py, unchanged


class CallCancelled(TimeoutError):
    """The call reached its deadline, was torn down, and the server was observed idle in time."""


class ServerNotIdle(RuntimeError):
    """After a cancellation the server was not observed idle in time: no further call may run."""


class ServerConfigViolation(RuntimeError):
    """Prefix caching could not be shown to be disabled in time."""


class TokenParityViolation(RuntimeError):
    """The server counted a different prompt than the pinned tokenizer's audited count."""


class StudyCallError(RuntimeError):
    """What the runner sees: 'Type: message', as the reviewed bridge formatted service errors."""


class CountedClient(Client):
    """The verified client, sharing its ledger and clock, with an optional caller deadline: each request ends by the
    earlier of the verified deadline (its planned timeout, never past the admission cutoff) and the caller's."""

    def __init__(self, client):
        super().__init__(client.host, client.port, client.ledger, client.clock, client.served)
        self.until = None

    def _deadline(self, item):
        own = super()._deadline(item)
        return own if self.until is None else min(own, self.until)

    def call_by(self, request_id, body, deadline):
        self.until = deadline
        try:
            return self.call(request_id, body)
        finally:
            self.until = None


def parse_completion(status, raw):
    """(content, prompt tokens, completion tokens, finish reason), as the reviewed transport parsed a reply."""
    if status != 200:
        raise ConnectionError(f'model server returned HTTP {status}')
    value = json.loads(raw)
    choice = value['choices'][0]
    content = choice['message']['content']
    if not isinstance(content, str):
        raise ValueError('model server returned no text content')
    usage = value.get('usage') or {}
    return content, usage.get('prompt_tokens'), usage.get('completion_tokens'), choice.get('finish_reason')


class StudyService:
    def __init__(self, client, frozen, probe_set_sha256, audit_counts, *, mode, launch, retain_server=None,
                 retain_cancellation=None, clock=time.monotonic, sleep=time.sleep):
        timing = PL.timing(mode)
        self.timeout, self.teardown, self.verify_seconds = timing['timeout'], timing['teardown'], timing['verify']
        self.client = CountedClient(client)
        self.clock, self.sleep = clock, sleep
        self.retain_server = retain_server or (lambda _r: None)
        self.retain_cancellation = retain_cancellation or (lambda _r: None)
        probes = {p['probe_id']: p for p in frozen['probes']}
        scheduled = PL.scheduled_requests(frozen)
        self.allowed = {PL.request_sha256(request): (probe_id, probes[probe_id]['family'])
                        for _, _, probe_id, request in scheduled}
        missing = set(self.allowed) - set(audit_counts)
        if missing:
            raise ValueError(f'{len(missing)} frozen requests have no audited prompt count')
        self.audit, self.probe_set_sha256, self.max_calls = dict(audit_counts), probe_set_sha256, len(scheduled)
        self.launch = launch
        self.calls, self.cancellations = 0, []
        self.server_config = None
        self.broken = None

    def _metrics(self, request_id, deadline):
        """One counted metrics read that finishes by the earlier of `deadline` and METRICS_READ_SECONDS from now."""
        status, raw = self.client.call_by(request_id, None, min(deadline, self.clock() + METRICS_READ_SECONDS))
        if status != 200:
            raise ConnectionError('metrics endpoint unavailable')
        if len(raw) > MAX_METRICS_BYTES:
            raise ValueError('metrics exceed the byte ceiling')
        return parse_metrics(raw.decode('utf-8', 'replace'))

    def _check_cache(self, stage, request_id, deadline, started):
        """Read the counters by `deadline` and recompute the verdict; any failure or lateness is a violation."""
        try:
            values = self._metrics(request_id, deadline)
            observed = self.clock()
            if observed > deadline:
                raise TimeoutError('cache check completed after its deadline')
            counters = {'prompt_tokens_total': metric_total(values, 'vllm:prompt_tokens_total'),
                        'prefix_cache_queries_total': metric_total(values, 'vllm:prefix_cache_queries_total'),
                        'prefix_cache_hits_total': metric_total(values, 'vllm:prefix_cache_hits_total')}
            evidence = {'stage': stage, **counters, 'observed_after_seconds': round(observed - started, 6),
                        'deadline_after_seconds': round(deadline - started, 6)}
            ok = cache_verdict(counters)
        except Exception as exc:
            evidence, ok = {'stage': stage, 'error': type(exc).__name__ + ': ' + str(exc)[:160]}, False
        evidence['prefix_caching_disabled_verified'] = ok
        if not ok:
            self.broken = 'prefix caching not verified disabled at ' + stage
            self.server_config = {**(self.server_config or {}), 'violation': evidence}
            self.retain_server(self.server_config)
            raise ServerConfigViolation(self.broken)
        return evidence

    def startup_check(self):
        """Prefix caching verified from the counters after the startup canary and probes, before any study call."""
        if self.server_config is not None:
            raise RuntimeError('startup cache check already attempted')
        started = self.clock()
        self.server_config = {'launch': self.launch, 'probe_set_sha256': self.probe_set_sha256, 'violation': None,
                              'timeout_seconds': self.timeout, 'teardown_seconds': self.teardown,
                              'verify_seconds': self.verify_seconds}
        self.server_config['after_canary'] = self._check_cache('after_canary', 'K0000',
                                                               started + STARTUP_CACHE_CHECK_SECONDS, started)
        self.retain_server(self.server_config)
        return self.server_config

    def _verify_idle(self, n, deadline):
        """research/evidence_comprehension_v1/transport.verify_idle over counted reads (V{n}); never raises."""
        started = self.clock()
        window = deadline - started
        last, error = None, None
        while True:
            if self.clock() >= deadline:
                break
            try:
                values = self._metrics(f'V{n:05d}', deadline)
                observed = self.clock()
                if observed > deadline:
                    error = 'observation completed after the deadline'
                    break
                last, error = server_load(values), None
                if last['running'] == 0 and last['waiting'] == 0:
                    record = {'idle': True, 'waited_seconds': round(observed - started, 3),
                              'window_seconds': round(window, 3), **last}
                    record['idle'] = idle_verdict(record, window)
                    return record
            except Exception as exc:
                error = type(exc).__name__ + ': ' + str(exc)[:120]
            pause = min(PL.IDLE_POLL_SECONDS, deadline - self.clock())
            if pause > 0:
                self.sleep(pause)
        return {'idle': False, 'waited_seconds': round(self.clock() - started, 3), 'window_seconds': round(window, 3),
                **(last or {'running': None, 'waiting': None, 'aborted_total': None}), 'error': error}

    def _complete(self, request):
        if self.server_config is None or not (self.server_config.get('after_canary') or {}).get(
                'prefix_caching_disabled_verified'):
            raise RuntimeError('startup canary and server verification have not passed')
        if self.broken:
            raise ServerNotIdle('service stopped: ' + self.broken)
        if self.calls >= self.max_calls:
            raise ValueError(f'questionnaire call ceiling ({self.max_calls})')
        digest = PL.request_sha256(request)
        if digest not in self.allowed:
            raise ValueError('request not in the frozen probe set')
        n = self.calls
        self.calls += 1  # a failed call still consumes the allowance
        prompt_tokens = self.audit[digest]
        if prompt_tokens > PL.PROMPT_TOKEN_CEILING or prompt_tokens + request['max_tokens'] > PL.CONTEXT_TOKENS:
            raise ValueError('pre-transport tokenizer/context ceiling')
        started = self.clock()
        inference_deadline = started + self.timeout
        verify_deadline = inference_deadline + self.teardown + self.verify_seconds
        try:
            status, raw = self.client.call_by(f'Q{n:05d}', request, inference_deadline)
        except RequestFailed as exc:
            if self.clock() < inference_deadline:
                raise  # failed before its deadline: a transport failure, not a timeout
            torn_down = self.clock()  # the verified client shut the socket at the deadline and closed it
            idle = self._verify_idle(n, verify_deadline)
            ended = self.clock()
            window = verify_deadline - torn_down
            verdict = (idle_verdict(idle, window) and ended <= verify_deadline
                       and torn_down <= inference_deadline + self.teardown)
            record = {'call': self.calls, 'request_sha256': digest, 'probe_id': self.allowed[digest][0],
                      'error': str(exc)[:200], 'idle_verification': idle,
                      'timing': {'torn_down_after_seconds': round(torn_down - started, 6),
                                 'ended_after_seconds': round(ended - started, 6),
                                 'inference_deadline_after_seconds': self.timeout,
                                 'verify_deadline_after_seconds': round(verify_deadline - started, 6)},
                      'idle': verdict}
            self.cancellations.append(record)
            self.retain_cancellation(list(self.cancellations))
            if not verdict:
                self.broken = 'server not observed idle in time after a cancelled call'
                raise ServerNotIdle(self.broken) from exc
            raise CallCancelled(json.dumps({'server_idle': True, 'aborted_total': idle.get('aborted_total')})) from exc
        answered = self.clock()
        content, server_prompt, server_completion, finish = parse_completion(status, raw)
        cache = self._check_cache(f'after_call_{self.calls}', f'M{n:05d}', verify_deadline, started)
        result = {'content': content, 'tokenizer_prompt_tokens': prompt_tokens, 'server_prompt_tokens': server_prompt,
                  'server_completion_tokens': server_completion, 'finish_reason': finish, 'cache_check': cache,
                  'host_timing': {'answered_after_seconds': round(answered - started, 6),
                                  'returned_after_seconds': round(self.clock() - started, 6)}}
        if server_prompt != prompt_tokens:
            raise TokenParityViolation(f'token audit mismatch: pinned tokenizer {prompt_tokens}, server {server_prompt}')
        return result

    def complete(self, request, deadline=None):
        """One call for the runner; with `deadline` (absolute), a reply after it is rejected."""
        try:
            result = self._complete(request)
        except Exception as exc:
            raise StudyCallError(type(exc).__name__ + ': ' + str(exc)[:512]) from exc
        if deadline is not None and self.clock() >= deadline:
            raise StudyCallError('TimeoutError: reply expired after the call bound')
        return result
