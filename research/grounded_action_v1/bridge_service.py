"""Stage B adapter for the bounded historical Unix model bridge.

No server, GPU, or model is started by this module. The injected transport
returns a CompletionResult; received evidence crosses the bridge even when
token parity or deadline validation subsequently fails.
"""
import hashlib
import math

from certification.phase4_integrated_v2.bridge import request_hash
from certification.phase4_integrated_v2.model_transport import CompletionResult
from certification.phase4_integrated_v2.response_evidence import ResponseValidationError, capture
from certification.phase4_transient_v2.action_contract import response_format, validate_canary
from .contract import case_protocol
from .model_service import TokenGuardedService


def canary_request():
    return {'model': case_protocol()['model_id'], 'messages': [
        {'role': 'system', 'content': 'Return only one legal ACTION6 JSON object with integer x and y.'},
        {'role': 'user', 'content': 'Choose a valid display coordinate; return only the action JSON.'}],
        'temperature': 0, 'seed': 0, 'max_tokens': 128,
        'chat_template_kwargs': {'enable_thinking': False},
        'response_format': response_format([6])}


def validate_ready(ready, expected_artifact):
    """Independently verify the bridge's canary, artifact and startup ceiling."""
    if (not isinstance(ready, dict) or not isinstance(expected_artifact, dict) or
            not expected_artifact or ready.get('artifact') != expected_artifact):
        raise ValueError('model bridge artifact binding')
    seconds = ready.get('startup_seconds')
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 <= seconds <= 900:
        raise ValueError('model bridge startup ceiling')
    canary = ready.get('canary_audit')
    if not isinstance(canary, dict) or canary.get('status') != 'passed':
        raise ValueError('model bridge canary status')
    request = canary_request()
    request_digest = request_hash(request)
    if (canary.get('request') != request or
            request_hash(canary['request']) != request_digest or
            canary.get('request_sha256') != request_digest):
        raise ValueError('model bridge canary request')
    body = canary.get('response_content')
    if type(body) is not str or type(canary.get('response_truncated')) is not bool or canary['response_truncated']:
        raise ValueError('model bridge canary body')
    raw = body.encode('utf-8')
    if (type(canary.get('response_bytes')) is not int or canary['response_bytes'] != len(raw) or
            len(raw) > 32768 or canary.get('response_sha256') != hashlib.sha256(raw).hexdigest()):
        raise ValueError('model bridge canary response hash')
    audit = canary.get('audit')
    if not isinstance(audit, dict) or audit.get('request_sha256') != request_digest:
        raise ValueError('model bridge canary audit request')
    prompt, observed, completion = (audit.get('tokenizer_prompt_tokens'),
                                    audit.get('server_prompt_tokens'), audit.get('server_completion_tokens'))
    if (type(prompt) is not int or type(observed) is not int or prompt != observed or
            not 0 < prompt <= 60000 or type(completion) is not int or not 0 < completion <= 128):
        raise ValueError('model bridge canary token parity')
    if audit.get('finish_reason') != 'stop':
        raise ValueError('model bridge canary finish reason')
    try:
        validate_canary(body)
    except (ValueError, TypeError) as exc:
        raise ValueError('model bridge canary action') from exc
    return ready


class BridgeService:
    def __init__(self, tokenizer_path, transport, *, tokenizer=None, retain_canary=None):
        self.guard = TokenGuardedService(tokenizer_path, transport, tokenizer=tokenizer)
        self.calls = 0
        self.canary_audit = None
        self.retain_canary = retain_canary or (lambda _record: None)

    def _retain_canary(self):
        # A target host supplies a durable, bounded writer here. Retain after
        # receipt and before any token or schema validation can fail.
        self.retain_canary(dict(self.canary_audit))

    def startup_canary(self):
        """One model call before study admission; retain raw evidence first."""
        if self.canary_audit is not None:
            raise RuntimeError('startup canary already attempted')
        request = canary_request()
        self.canary_audit = {'status': 'attempted', 'request': request,
                             'request_sha256': request_hash(request)}
        self._retain_canary()
        try:
            result = self.guard.complete(request)
            audit = {'request_sha256': request_hash(request),
                     'tokenizer_prompt_tokens': result['tokenizer_prompt_tokens'],
                     'server_prompt_tokens': result['server_prompt_tokens'],
                     'server_completion_tokens': result['server_completion_tokens'],
                     'finish_reason': result['finish_reason']}
            evidence = capture(result['content'], audit)
            self.canary_audit.update(status='received', **evidence)
            self._retain_canary()
            if (evidence['response_truncated'] or
                    result['tokenizer_prompt_tokens'] != result['server_prompt_tokens'] or
                    type(result['server_completion_tokens']) is not int or
                    not 0 < result['server_completion_tokens'] <= 128 or
                    result['finish_reason'] != 'stop'):
                raise ResponseValidationError('startup canary audit mismatch', evidence)
            validate_canary(result['content'])
            self.canary_audit['status'] = 'passed'
            self._retain_canary()
            return self.canary_audit
        except Exception as exc:
            self.canary_audit['status'] = 'failed'
            self.canary_audit['error'] = type(exc).__name__ + ': ' + str(exc)[:256]
            self._retain_canary()
            raise

    def complete(self, request):
        if self.canary_audit is None or self.canary_audit['status'] != 'passed':
            raise RuntimeError('startup canary has not passed')
        if self.calls >= 12:
            raise ValueError('Stage B inference ceiling')
        self.calls += 1  # A failed transport still consumes the attempt.
        result = self.guard.complete(request)
        audit = {'request_sha256': request_hash(request),
                 'tokenizer_prompt_tokens': result['tokenizer_prompt_tokens'],
                 'server_prompt_tokens': result['server_prompt_tokens'],
                 'server_completion_tokens': result['server_completion_tokens'],
                 'finish_reason': result['finish_reason']}
        completion = CompletionResult(content=result['content'],
                                      prompt_tokens=result['server_prompt_tokens'],
                                      completion_tokens=result['server_completion_tokens'],
                                      finish_reason=result['finish_reason'])
        return completion, audit


class ProxyService:
    """Runner-facing adapter for a supervised, already started ModelProxy."""

    def __init__(self, proxy):
        self.proxy = proxy

    def connect_ready(self, *, expected_artifact):
        """Admit calls only after the server's real ready reply is checked."""
        if self.proxy.started:
            raise RuntimeError('model bridge already admitted')
        ready = self.proxy.call({'op': 'ready'})
        validate_ready(ready, expected_artifact)
        self.proxy.artifact = ready.get('artifact')
        self.proxy.canary_audit = ready['canary_audit']
        self.proxy.startup_seconds = ready['startup_seconds']
        self.proxy.started = True
        return ready

    def complete(self, request):
        result = self.proxy.complete(request)
        audit = self.proxy.audit_records[-1]
        return {'content': result.content,
                'tokenizer_prompt_tokens': audit['tokenizer_prompt_tokens'],
                'server_prompt_tokens': audit['server_prompt_tokens'],
                'server_completion_tokens': audit['server_completion_tokens'],
                'finish_reason': audit['finish_reason']}
