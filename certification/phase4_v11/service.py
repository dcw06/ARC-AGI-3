"""One real model process shared by the 110-client queue; dynamic token audit."""
from dataclasses import replace
import hashlib
import importlib.metadata
import json
import threading
import time

from pathlib import Path
from certification.phase4_v11.live_probes import require_live_authority as authority
ROOT = Path(__file__).resolve().parents[2]


def audited_completion(tokenizer, request, complete, context_limit=65536):
    """Tokenize the exact real trajectory request without truncation or repair."""
    if any(not isinstance(m.get('content'), str) for m in request['messages']):
        raise ValueError('only frozen text-grid messages are supported')
    tokens = tokenizer.apply_chat_template(request['messages'], tokenize=True,
        add_generation_prompt=True, truncation=False, **request.get('chat_template_kwargs', {}))
    if not isinstance(tokens, list) or not tokens or any(type(t) is not int for t in tokens):
        raise ValueError('invalid tokenizer output')
    limit = request.get('max_tokens')
    if type(limit) is not int or not 0 < limit <= 128 or len(tokens) + limit > context_limit:
        raise ValueError('context/completion limit exceeded')
    begin = time.monotonic()
    result = complete(request)
    if (type(result.prompt_tokens) is not int or result.prompt_tokens != len(tokens)
            or type(result.completion_tokens) is not int or not 0 <= result.completion_tokens <= limit):
        raise ValueError('server/tokenizer token-count mismatch or missing usage')
    record = {'request_sha256': hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(),
              'tokenizer_prompt_tokens': len(tokens), 'server_prompt_tokens': result.prompt_tokens,
              'server_completion_tokens': result.completion_tokens,
              'service_seconds': time.monotonic() - begin}
    return result, record


class SharedModelService:
    def __init__(self, scratch, root=ROOT):
        self.root, self.scratch = root, scratch
        self.started = False
        self.audit_records = []
        self.lock = threading.Lock()
        self.service = None

    def start(self):
        authority(self.root)
        begin = time.monotonic()
        # This process exists only after the independent monitor releases the
        # owning game worker. Reuse the passed r5 model/CUDA/isolation contract.
        from certification.phase4_v6.target_install_probe_r5 import MODEL_CHECK
        exec(compile(MODEL_CHECK,'v11_monitored_model_readiness','exec'),{})
        from certification.phase4_v11.model_process import ModelService, load_operational_primary
        from certification.phase4_v11.model_artifact import verify_artifact
        self.primary = replace(load_operational_primary(self.root), scratch_log=Path('/dev/stdout'))
        self.artifact = verify_artifact(self.primary)
        if importlib.metadata.version('transformers').split('+')[0] != '4.57.6':
            raise ValueError('tokenizer version drift')
        from transformers import AutoTokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.primary.model_path),
            local_files_only=True, trust_remote_code=False)
        spec = json.loads(self.primary.launch_spec_path.read_text())['argv']
        self.context_limit = int(spec[spec.index('--max-model-len') + 1])
        if self.context_limit != 65536:
            raise ValueError('frozen context drift')
        owner = self
        self.canary_audit = None
        class SingleAuditedCanaryService(ModelService):
            def _completion_canary(self):
                # Wrap transport errors so the frozen readiness loop cannot retry
                # an inference canary under its health-check exception handler.
                if owner.canary_audit is not None:
                    raise RuntimeError('canary already attempted')
                owner.canary_audit = {'status': 'attempted'}
                try:
                    from certification.phase4_v11.model_transport import OpenAICompatibleCompletionClient
                    import requests
                    request = {'model': self.primary.binding.model_id,
                        'messages': [{'role': 'system', 'content': 'Reply with exactly OK.'},
                                     {'role': 'user', 'content': 'Ready?'}],
                        'temperature': 0, 'seed': 0, 'max_tokens': 8,
                        'chat_template_kwargs': {'enable_thinking': False}}
                    with requests.Session() as session:
                        client = OpenAICompatibleCompletionClient(self.primary.base_url,
                            session=session, timeout_seconds=self.primary.completion_canary_timeout_seconds)
                        result, audit = audited_completion(owner.tokenizer, request, client.complete, owner.context_limit)
                    if not result.content.strip():
                        raise ValueError('empty canary response')
                    owner.canary_audit = {'status': 'passed', **audit}
                except Exception as exc:
                    raise RuntimeError('single model canary failed') from exc
        self.service = SingleAuditedCanaryService(self.primary)
        self.service.start()  # Includes actual completion canary.
        self.startup_seconds = time.monotonic() - begin
        self.started = True

    def complete(self, request):
        if not self.started:
            raise RuntimeError('model not started')
        if (request.get('model') != self.primary.binding.model_id or request.get('seed') != 0
                or request.get('temperature') != 0 or request.get('max_tokens') != 128
                or request.get('chat_template_kwargs') != {'enable_thinking': False}):
            raise ValueError('frozen E1S-R request drift')
        from certification.phase4_v11.model_transport import OpenAICompatibleCompletionClient
        import requests
        with requests.Session() as session:
            client = OpenAICompatibleCompletionClient(self.primary.base_url, session=session,
                timeout_seconds=self.primary.request_timeout_seconds)
            result, record = audited_completion(self.tokenizer, request, client.complete, self.context_limit)
        with self.lock:
            self.audit_records.append(record)
        return result, record

    # The owning external supervisor terminates/verifies the whole process group,
    # including this model and descendants. Do not mistake Python thread exit for
    # server-side cancellation, or run the frozen service's 90-second close here.
