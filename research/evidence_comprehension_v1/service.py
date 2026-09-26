"""Questionnaire model service (model interpreter) and runner-facing proxy (worker interpreter).

The host-side service accepts only requests whose hash belongs to the frozen probe set, admits
each by the pinned tokenizer, and enforces a total per-call deadline through the cancellable
transport. After a timeout it must observe the server idle through the server's own metrics;
otherwise it refuses every later call. After the canary and after every answer it re-checks that
prefix caching is disabled. Server-configuration and cancellation evidence are retained by the
host for the worker and the independent evaluator.

Constructing these classes never starts a model or GPU; transport and metrics are injected.
"""
import json
import math

from research.action_effect_history_v1.service import (CONTEXT_TOKENS, MAX_COMPLETION_TOKENS as CANARY_MAX_TOKENS,
                                                       MAX_PROMPT_TOKENS, canary_request, request_hash)

MAX_CANARIES = 1


class CallCancelled(TimeoutError):
    """The call reached its deadline; the connection was closed. The message carries the idle verdict."""


class ServerNotIdle(RuntimeError):
    """After a cancellation the server did not become idle: no further call may run."""


class ServerConfigViolation(RuntimeError):
    """Prefix caching could not be shown to be disabled."""


def frozen_requests():
    """{request_sha256: (probe_id, family)} for every frozen probe; the only requests the host will serve."""
    from research.evidence_comprehension_v1.probes import build_request, load_frozen
    frozen, digest = load_frozen()
    contexts = {c['context_id']: c for c in frozen['contexts']}
    allowed = {}
    for probe in frozen['probes']:
        allowed[request_hash(build_request(contexts[probe['context_id']], probe))] = (probe['probe_id'], probe['family'])
    return allowed, digest, 2 * len(frozen['probes'])


class QuestionnaireService:
    def __init__(self, tokenizer, transport, *, metrics, verify_idle, retain_canary=None, retain_server=None,
                 retain_cancellation=None, verify_seconds=15):
        from research.evidence_comprehension_v1.transport import prefix_caching_evidence
        self.tokenizer, self.transport = tokenizer, transport
        self.metrics, self.verify_idle = metrics, verify_idle
        self._cache_evidence = prefix_caching_evidence
        self.retain_canary = retain_canary or (lambda _r: None)
        self.retain_server = retain_server or (lambda _r: None)
        self.retain_cancellation = retain_cancellation or (lambda _r: None)
        self.verify_seconds = verify_seconds
        self.allowed, self.probe_set_sha256, self.max_calls = frozen_requests()
        self.calls, self.cancellations = 0, []
        self.canary_audit = self.server_config = None
        self.broken = None
        self.artifact = None
        self.startup_seconds = None
        self.launch = {}

    def _admit(self, request):
        tokens = self.tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                                    truncation=False, **request['chat_template_kwargs'])
        if (type(tokens) is not list or not tokens or any(type(t) is not int for t in tokens)
                or len(tokens) > MAX_PROMPT_TOKENS or len(tokens) + request['max_tokens'] > CONTEXT_TOKENS):
            raise ValueError('pre-transport tokenizer/context ceiling')
        return len(tokens)

    def _audit(self, request, prompt_tokens, result):
        return {'request_sha256': request_hash(request), 'tokenizer_prompt_tokens': prompt_tokens,
                'server_prompt_tokens': result.prompt_tokens, 'server_completion_tokens': result.completion_tokens,
                'finish_reason': result.finish_reason}

    def _check_cache(self, stage):
        evidence = {'stage': stage, **self._cache_evidence(self.metrics())}
        if not evidence['prefix_caching_disabled_verified']:
            self.broken = 'prefix caching not verified disabled at ' + stage
            self.server_config = {**(self.server_config or {}), 'violation': evidence}
            self.retain_server(self.server_config)
            raise ServerConfigViolation(self.broken)
        return evidence

    def startup_canary(self):
        from certification.phase4_integrated_v2.response_evidence import ResponseValidationError, capture
        from certification.phase4_transient_v2.action_contract import validate_canary
        if self.canary_audit is not None:
            raise RuntimeError('startup canary already attempted')
        request = canary_request()
        self.canary_audit = {'status': 'attempted', 'request': request, 'request_sha256': request_hash(request)}
        self.retain_canary(dict(self.canary_audit))
        try:
            prompt_tokens = self._admit(request)
            result = self.transport(request)
            audit = self._audit(request, prompt_tokens, result)
            evidence = capture(result.content, audit)
            self.canary_audit.update(status='received', **evidence)
            self.retain_canary(dict(self.canary_audit))
            if (evidence['response_truncated'] or audit['tokenizer_prompt_tokens'] != audit['server_prompt_tokens']
                    or type(audit['server_completion_tokens']) is not int
                    or not 0 < audit['server_completion_tokens'] <= CANARY_MAX_TOKENS
                    or audit['finish_reason'] != 'stop'):
                raise ResponseValidationError('startup canary audit mismatch', evidence)
            validate_canary(result.content)
            self.canary_audit['status'] = 'passed'
            self.retain_canary(dict(self.canary_audit))
        except Exception as exc:
            self.canary_audit.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:256])
            self.retain_canary(dict(self.canary_audit))
            raise
        # The canary's prompt must be visible in the server's counters with no prefix-cache query.
        self.server_config = {'launch': self.launch, 'probe_set_sha256': self.probe_set_sha256,
                              'after_canary': self._check_cache('after_canary'), 'violation': None}
        self.retain_server(self.server_config)
        return self.canary_audit

    def complete(self, request):
        from certification.phase4_integrated_v2.model_transport import CompletionResult
        from research.evidence_comprehension_v1.transport import CallTimedOut
        if self.canary_audit is None or self.canary_audit['status'] != 'passed' or self.server_config is None:
            raise RuntimeError('startup canary and server verification have not passed')
        if self.broken:
            raise ServerNotIdle('service stopped: ' + self.broken)
        if self.calls >= self.max_calls:
            raise ValueError(f'questionnaire call ceiling ({self.max_calls})')
        digest = request_hash(request)
        if digest not in self.allowed:
            raise ValueError('request not in the frozen probe set')
        self.calls += 1  # a failed call still consumes the allowance
        prompt_tokens = self._admit(request)
        try:
            result = self.transport(request)
        except CallTimedOut as exc:
            idle = self.verify_idle(self.verify_seconds)
            record = {'call': self.calls, 'request_sha256': digest, 'probe_id': self.allowed[digest][0],
                      'error': str(exc)[:200], 'idle_verification': idle}
            self.cancellations.append(record)
            self.retain_cancellation(list(self.cancellations))
            if not idle.get('idle'):
                self.broken = 'server did not become idle after a cancelled call'
                raise ServerNotIdle(self.broken) from exc
            raise CallCancelled(json.dumps({'server_idle': True, 'aborted_total': idle.get('aborted_total')})) from exc
        self._check_cache(f'after_call_{self.calls}')
        audit = self._audit(request, prompt_tokens, result)
        return CompletionResult(content=result.content, prompt_tokens=result.prompt_tokens,
                                completion_tokens=result.completion_tokens, finish_reason=result.finish_reason), audit


def validate_ready(ready, expected_artifact):
    """Independently verify the bridge's canary, artifact and startup ceiling (worker interpreter)."""
    from research.action_effect_history_v1.service import validate_ready as verify_canary_and_artifact
    return verify_canary_and_artifact(ready, expected_artifact)


def validate_server_config(config, mode, probe_set_sha256):
    """The host's retained server evidence: caching disabled after the canary, and (live) the launch flags."""
    if not isinstance(config, dict) or config.get('violation') is not None:
        raise ValueError('server configuration violation')
    if config.get('probe_set_sha256') != probe_set_sha256:
        raise ValueError('host serves a different probe set')
    after = config.get('after_canary') or {}
    if after.get('prefix_caching_disabled_verified') is not True or not after.get('prompt_tokens_total'):
        raise ValueError('prefix caching not verified disabled after the canary')
    launch = config.get('launch') or {}
    if mode == 'live':
        argv = launch.get('argv')
        if (not isinstance(argv, list) or '--no-enable-prefix-caching' not in argv
                or '--enable-prefix-caching' in argv):
            raise ValueError('live launch flags do not disable prefix caching')
    elif launch.get('rehearsal_fake_server') is not True:
        raise ValueError('rehearsal server evidence')
    return config


class ProxyService:
    """Worker-facing adapter for a supervised ModelProxy."""

    def __init__(self, proxy):
        self.proxy = proxy

    def connect_ready(self, *, expected_artifact):
        if self.proxy.started:
            raise RuntimeError('model bridge already admitted')
        ready = self.proxy.call({'op': 'ready'})
        validate_ready(ready, expected_artifact)
        self.proxy.artifact, self.proxy.canary_audit = ready['artifact'], ready['canary_audit']
        self.proxy.startup_seconds, self.proxy.started = ready['startup_seconds'], True
        return ready

    def complete(self, request):
        result = self.proxy.complete(request)
        audit = self.proxy.audit_records[-1]
        return {'content': result.content, 'tokenizer_prompt_tokens': audit['tokenizer_prompt_tokens'],
                'server_prompt_tokens': audit['server_prompt_tokens'],
                'server_completion_tokens': audit['server_completion_tokens'], 'finish_reason': audit['finish_reason']}


def finite_seconds(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0
