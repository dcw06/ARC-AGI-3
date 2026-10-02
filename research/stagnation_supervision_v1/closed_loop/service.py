"""Request contracts and the GPU-disabled in-process service (hand-written; not derived).

`validate_policy_request` and `validate_reflection_request` are the exact request contracts a future model host must
enforce before transport. `LocalService` checks them and forwards to an injected CPU server (the fake server in
rehearsal). No model, GPU or network is used here; the live host is not part of this pass.
"""
import json

from research.stagnation_supervision_v1 import intervention as I
from research.stagnation_supervision_v1.closed_loop import bridge as B

MODEL_ID = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
MAX_REQUEST_BYTES = 262144
POLICY_MAX_TOKENS = 128
REQUEST_KEYS = {'model', 'messages', 'temperature', 'seed', 'max_tokens', 'chat_template_kwargs'}


def _settings(request, keys, max_tokens):
    if (type(request) is not dict or set(request) != keys or request['model'] != MODEL_ID
            or request['temperature'] != 0 or request['seed'] != 0 or request['max_tokens'] != max_tokens
            or request['chat_template_kwargs'] != {'enable_thinking': False}):
        raise ValueError('frozen model settings')
    messages = request['messages']
    if (type(messages) is not list or len(messages) != 2 or any(set(m) != {'role', 'content'} for m in messages)
            or [m['role'] for m in messages] != ['system', 'user']):
        raise ValueError('message envelope')
    if len(json.dumps(request, separators=(',', ':')).encode()) > MAX_REQUEST_BYTES:
        raise ValueError('request byte ceiling')
    return messages


def validate_policy_request(request):
    """The common baseline request, optionally with the suggestion block beside the observation."""
    from certification.phase4_transient_v2.action_contract import response_format
    from research.action_effect_history_v1.service import BASELINE_FIELDS
    from research.stagnation_supervision_v1.closed_loop.contract import SYSTEM_PROMPT
    messages = _settings(request, REQUEST_KEYS | {'response_format'}, POLICY_MAX_TOKENS)
    if messages[0]['content'] != SYSTEM_PROMPT:
        raise ValueError('frozen prompt')
    payload = json.loads(messages[1]['content'])
    if set(payload) not in ({'observation'}, {'observation', B.SUGGESTION_FIELD}):
        raise ValueError('payload envelope')
    if set(payload['observation']) != BASELINE_FIELDS:
        raise ValueError('observation fields')
    if B.SUGGESTION_FIELD in payload:
        block = payload[B.SUGGESTION_FIELD]
        if set(block) != set(B.SUGGESTION_KEYS) or B.suggestion_payload(block) != block:
            raise ValueError('suggestion block shape')
    if request['response_format'] != response_format(payload['observation']['legal_actions']):
        raise ValueError('legal-action schema')
    return 'with_suggestion' if B.SUGGESTION_FIELD in payload else 'without_suggestion'


def validate_reflection_request(request):
    messages = _settings(request, REQUEST_KEYS, B.REFLECTION_MAX_TOKENS)
    if messages[0]['content'] != B.REFLECTION_SYSTEM or not messages[1]['content'].startswith(I.PROMPT + '\n\nEvidence:\n'):
        raise ValueError('frozen reflection prompt')
    return 'reflection'


def kind(request):
    messages = request.get('messages') if isinstance(request, dict) else None
    return 'reflection' if messages and messages[0].get('content') == B.REFLECTION_SYSTEM else 'policy'


class LocalService:
    """Runner-facing service for CPU rehearsal: contract checks, then the injected server. Never a model."""

    def __init__(self, server):
        self.server = server
        self.requests = []

    def complete(self, request):
        (validate_reflection_request if kind(request) == 'reflection' else validate_policy_request)(request)
        self.requests.append(request)
        return self.server.complete(request)
