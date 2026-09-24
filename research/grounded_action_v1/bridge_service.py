"""Stage B adapter for the bounded historical Unix model bridge.

No server, GPU, or model is started by this module. The injected transport
returns a CompletionResult; received evidence crosses the bridge even when
token parity or deadline validation subsequently fails.
"""
from certification.phase4_integrated_v2.bridge import request_hash
from certification.phase4_integrated_v2.model_transport import CompletionResult
from certification.phase4_integrated_v2.response_evidence import ResponseValidationError, capture
from certification.phase4_transient_v2.action_contract import response_format, validate_canary
from .model_service import TokenGuardedService


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
        request = {'model': self.guard.protocol['model_id'], 'messages': [
            {'role': 'system', 'content': 'Return only one legal ACTION6 JSON object with integer x and y.'},
            {'role': 'user', 'content': 'Choose a valid display coordinate; return only the action JSON.'}],
            'temperature': 0, 'seed': 0, 'max_tokens': 128,
            'chat_template_kwargs': {'enable_thinking': False},
            'response_format': response_format([6])}
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

    def complete(self, request):
        result = self.proxy.complete(request)
        audit = self.proxy.audit_records[-1]
        return {'content': result.content,
                'tokenizer_prompt_tokens': audit['tokenizer_prompt_tokens'],
                'server_prompt_tokens': audit['server_prompt_tokens'],
                'server_completion_tokens': audit['server_completion_tokens'],
                'finish_reason': audit['finish_reason']}
