"""Pre-transport tokenizer admission for a future reviewed model process."""
import importlib.metadata
import json

from certification.phase4_integrated_v2.tokenizer_binding import verify
from .contract import case_protocol


class TokenGuardedService:
    """Call once, return raw evidence to the runner for validation and retention.

    `transport` is injected; constructing this class never starts a model/GPU.
    The runner must durably retain the returned body and counts before checking
    parity, finish reason, or response schema. No retries are performed here.
    """

    def __init__(self, tokenizer_path, transport, *, tokenizer=None):
        self.protocol = case_protocol()
        versions = {name: importlib.metadata.version(name) for name in ('transformers', 'tokenizers', 'jinja2')}
        if versions != {'transformers': '4.57.6', 'tokenizers': '0.22.2', 'jinja2': '3.1.6'}:
            raise ValueError('pinned tokenizer version drift')
        verify(tokenizer_path)
        if tokenizer is None:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path), local_files_only=True,
                                                       trust_remote_code=False)
        self.tokenizer = tokenizer
        self.transport = transport

    def complete(self, request):
        protocol = self.protocol
        if (request.get('model') != protocol['model_id'] or request.get('temperature') != 0 or
                request.get('seed') != 0 or request.get('max_tokens') != 128 or
                request.get('chat_template_kwargs') != {'enable_thinking': False}):
            raise ValueError('model request binding')
        if len(json.dumps(request, separators=(',', ':')).encode()) > protocol['max_request_bytes']:
            raise ValueError('pre-transport request byte ceiling')
        tokens = self.tokenizer.apply_chat_template(request['messages'], tokenize=True,
                                                    add_generation_prompt=True, truncation=False,
                                                    **request['chat_template_kwargs'])
        if (type(tokens) is not list or not tokens or any(type(t) is not int for t in tokens) or
                len(tokens) > protocol['max_prompt_tokens_per_call'] or
                len(tokens) + request['max_tokens'] > protocol['max_context_tokens']):
            raise ValueError('pre-transport tokenizer/context ceiling')
        result = self.transport(request)
        # Do not reject count disagreement here: the outer runner first retains
        # the received body, hash, both observed counts and finish reason.
        return {'content': result.content, 'tokenizer_prompt_tokens': len(tokens),
                'server_prompt_tokens': result.prompt_tokens,
                'server_completion_tokens': result.completion_tokens,
                'finish_reason': result.finish_reason}
