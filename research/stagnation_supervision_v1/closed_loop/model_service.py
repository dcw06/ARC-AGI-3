# Derived from research/action_effect_history_v1/service.py by scripts/derive_stagnation_supervision_v1.py; edit the derivation, not this file.
"""Experiment-specific model-service contract (model interpreter) and runner-facing proxy (game interpreter).

Constructing these classes never starts a model or GPU; the transport is injected. Stage B's
12-call bridge contract does not apply here.
"""
import hashlib
import importlib.metadata
import json
import math

MODEL_ID = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
MAX_POLICY_CALLS = 1080  # the whole protocol (closed_loop/protocol.json); each session runs fewer
MAX_REFLECTION_CALLS = 64
MAX_PROMPT_TOKENS = 60000
CONTEXT_TOKENS = 65536
MAX_REQUEST_BYTES = 262144
MAX_COMPLETION_TOKENS = 128
BASELINE_FIELDS = {'current_grid', 'state', 'levels_completed', 'win_levels', 'legal_actions', 'previous_grid',
                   'recent_actions', 'recent_final_grids', 'history_compaction'}
HISTORY_KEYS = {'computed_by', 'scope', 'fields', 'omitted_entries', 'entries'}
ENTRY_KEYS = {'step', 'action_id', 'action_data', 'status', 'returned_frame_count', 'changed_cells_by_frame',
              'final_frame_changed', 'level_delta', 'reset'}


def request_hash(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()


def canary_request():
    from certification.phase4_transient_v2.action_contract import response_format
    return {'model': MODEL_ID, 'messages': [
        {'role': 'system', 'content': 'Return only one legal ACTION6 JSON object with integer x and y.'},
        {'role': 'user', 'content': 'Choose a valid display coordinate; return only the action JSON.'}],
        'temperature': 0, 'seed': 0, 'max_tokens': MAX_COMPLETION_TOKENS,
        'chat_template_kwargs': {'enable_thinking': False}, 'response_format': response_format([6])}


def validate_policy_request(request):
    """Exact frozen request contracts (policy or reflection); raises ValueError before any transport."""
    from research.stagnation_supervision_v1.closed_loop.service import (
        kind, validate_policy_request as policy, validate_reflection_request as reflection)
    return reflection(request) if kind(request) == 'reflection' else policy(request)


class SupervisionModelService:
    """One canary, then contract-checked policy and reflection calls within separate ceilings; raw evidence
    returned for retention."""

    def __init__(self, tokenizer_path, transport, *, tokenizer=None, retain_canary=None, check_versions=True):
        if check_versions:
            versions = {n: importlib.metadata.version(n) for n in ('transformers', 'tokenizers', 'jinja2')}
            if versions != {'transformers': '4.57.6', 'tokenizers': '0.22.2', 'jinja2': '3.1.6'}:
                raise ValueError('pinned tokenizer version drift')
        if tokenizer is None:
            from certification.phase4_integrated_v2.tokenizer_binding import verify
            verify(tokenizer_path)
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path), local_files_only=True,
                                                      trust_remote_code=False)
        self.tokenizer, self.transport = tokenizer, transport
        self.retain_canary = retain_canary or (lambda _record: None)
        self.calls = 0
        self.reflection_calls = 0
        self.canary_audit = None
        self.artifact = None
        self.startup_seconds = None

    def _admit(self, request):
        tokens = self.tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                                    truncation=False, **request['chat_template_kwargs'])
        if (type(tokens) is not list or not tokens or any(type(t) is not int for t in tokens)
                or len(tokens) > MAX_PROMPT_TOKENS or len(tokens) + request['max_tokens'] > CONTEXT_TOKENS):
            raise ValueError('pre-transport tokenizer/context ceiling')
        return len(tokens)

    def _call(self, request, prompt_tokens):
        result = self.transport(request)
        audit = {'request_sha256': request_hash(request), 'tokenizer_prompt_tokens': prompt_tokens,
                 'server_prompt_tokens': result.prompt_tokens, 'server_completion_tokens': result.completion_tokens,
                 'finish_reason': result.finish_reason}
        return result, audit

    def startup_canary(self):
        from certification.phase4_integrated_v2.response_evidence import ResponseValidationError, capture
        from certification.phase4_transient_v2.action_contract import validate_canary
        if self.canary_audit is not None:
            raise RuntimeError('startup canary already attempted')
        request = canary_request()
        self.canary_audit = {'status': 'attempted', 'request': request, 'request_sha256': request_hash(request)}
        self.retain_canary(dict(self.canary_audit))
        try:
            result, audit = self._call(request, self._admit(request))
            evidence = capture(result.content, audit)
            self.canary_audit.update(status='received', **evidence)
            self.retain_canary(dict(self.canary_audit))
            if (evidence['response_truncated'] or audit['tokenizer_prompt_tokens'] != audit['server_prompt_tokens']
                    or type(audit['server_completion_tokens']) is not int
                    or not 0 < audit['server_completion_tokens'] <= MAX_COMPLETION_TOKENS
                    or audit['finish_reason'] != 'stop'):
                raise ResponseValidationError('startup canary audit mismatch', evidence)
            validate_canary(result.content)
            self.canary_audit['status'] = 'passed'
            self.retain_canary(dict(self.canary_audit))
            return self.canary_audit
        except Exception as exc:
            self.canary_audit.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:256])
            self.retain_canary(dict(self.canary_audit))
            raise

    def complete(self, request):
        """Bridge entry point: returns (CompletionResult, audit). Count disagreement is judged by the runner."""
        from certification.phase4_integrated_v2.model_transport import CompletionResult
        if self.canary_audit is None or self.canary_audit['status'] != 'passed':
            raise RuntimeError('startup canary has not passed')
        from research.stagnation_supervision_v1.closed_loop.service import kind as request_kind
        if request_kind(request) == 'reflection':
            if self.reflection_calls >= MAX_REFLECTION_CALLS:
                raise ValueError('reflection call ceiling')
            self.reflection_calls += 1  # a failed call still consumes the allowance
        else:
            if self.calls >= MAX_POLICY_CALLS:
                raise ValueError('policy call ceiling')
            self.calls += 1  # a failed call still consumes the allowance
        validate_policy_request(request)
        result, audit = self._call(request, self._admit(request))
        return CompletionResult(content=result.content, prompt_tokens=result.prompt_tokens,
                                completion_tokens=result.completion_tokens,
                                finish_reason=result.finish_reason), audit


def validate_ready(ready, expected_artifact):
    """Independently verify the bridge's canary, artifact and startup ceiling (game interpreter)."""
    from certification.phase4_transient_v2.action_contract import validate_canary
    if not isinstance(ready, dict) or ready.get('artifact') != expected_artifact or not expected_artifact:
        raise ValueError('model bridge artifact binding')
    seconds = ready.get('startup_seconds')
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 <= seconds <= 900:
        raise ValueError('model bridge startup ceiling')
    canary = ready.get('canary_audit') or {}
    request = canary_request()
    if (canary.get('status') != 'passed' or canary.get('request') != request
            or canary.get('request_sha256') != request_hash(request)):
        raise ValueError('model bridge canary request/status')
    body = canary.get('response_content')
    raw = body.encode() if type(body) is str else b''
    audit = canary.get('audit') or {}
    if (type(body) is not str or canary.get('response_truncated') is not False or canary.get('response_bytes') != len(raw)
            or canary.get('response_sha256') != hashlib.sha256(raw).hexdigest()
            or audit.get('request_sha256') != request_hash(request)
            or type(audit.get('server_prompt_tokens')) is not int
            or type(audit.get('tokenizer_prompt_tokens')) is not int
            or not 0 < audit['server_prompt_tokens'] <= MAX_PROMPT_TOKENS
            or audit.get('server_prompt_tokens') != audit.get('tokenizer_prompt_tokens')
            or type(audit.get('server_completion_tokens')) is not int
            or not 0 < audit['server_completion_tokens'] <= MAX_COMPLETION_TOKENS
            or audit.get('finish_reason') != 'stop'):
        raise ValueError('model bridge canary evidence')
    validate_canary(body)
    return ready


class ProxyService:
    """Runner-facing adapter for a supervised ModelProxy (game interpreter)."""

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
