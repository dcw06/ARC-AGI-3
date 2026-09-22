"""One real model process for sequential diagnostic cases; exact token audit."""
from dataclasses import replace
import hashlib
import importlib.metadata
import json
import threading
import time

from pathlib import Path
from certification.phase4_coordinates_v2.live_probes import require_live_authority as authority
ROOT = Path(__file__).resolve().parents[2]


def audited_completion(tokenizer, request, complete, context_limit=65536, retain=None):
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
    if max(len(json.dumps(request).encode()),len(json.dumps(request,separators=(',',':')).encode()))>65536:raise ValueError('payload limit')
    begin = time.monotonic()
    result = complete(request)
    record = {'request_sha256': hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(),
              'tokenizer_prompt_tokens': len(tokens), 'server_prompt_tokens': result.prompt_tokens,
              'server_completion_tokens': result.completion_tokens,
              'service_seconds': time.monotonic() - begin}
    from certification.phase4_coordinates_v2.response_evidence import capture,emit,ResponseValidationError
    evidence=capture(result.content,record)
    emit(evidence)
    if retain is not None:retain(evidence)
    if evidence['response_truncated']:
        raise ResponseValidationError('response evidence ceiling',evidence)
    if (type(result.prompt_tokens) is not int or result.prompt_tokens != len(tokens)
            or type(result.completion_tokens) is not int or not 0 <= result.completion_tokens <= limit):
        raise ResponseValidationError('server/tokenizer token-count mismatch or missing usage',evidence)
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
        exec(compile(MODEL_CHECK,'v13_monitored_model_readiness','exec'),{})
        from certification.phase4_coordinates_v2.model_process import ModelService, load_operational_primary
        from certification.phase4_coordinates_v2.model_artifact import verify_artifact
        self.primary = replace(load_operational_primary(self.root), scratch_log=Path('/dev/stdout'),
            request_timeout_seconds=120, completion_canary_timeout_seconds=120,
            readiness_timeout_seconds=900, hard_seconds=1980, finalization_reserve_seconds=300, queue_capacity=1, queue_workers=1)
        self.artifact = verify_artifact(self.primary)
        if importlib.metadata.version('transformers').split('+')[0] != '4.57.6':
            raise ValueError('tokenizer version drift')
        from certification.phase4_coordinates_v2.tokenizer_binding import verify
        verify(self.primary.model_path)
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
                    from certification.phase4_coordinates_v2.model_transport import OpenAICompatibleCompletionClient
                    import requests
                    from certification.phase4_coordinates_v2.action_contract import response_format, validate_canary
                    from certification.phase4_coordinates_v2.cases import canary_request
                    request = canary_request(self.primary.binding.model_id)
                    with requests.Session() as session:
                        client = OpenAICompatibleCompletionClient(self.primary.base_url,
                            session=session, timeout_seconds=self.primary.completion_canary_timeout_seconds)
                        def retain(evidence):
                            owner.canary_audit={'status':'received','request':request,
                                'action_contract':'arc_action_v12',**evidence['audit'],
                                **{k:v for k,v in evidence.items() if k!='audit'}}
                            print(json.dumps({'diagnostic_startup_canary':owner.canary_audit}),flush=True)
                        result, audit = audited_completion(owner.tokenizer, request, client.complete, owner.context_limit,retain=retain)
                    raw=result.content.encode()
                    owner.canary_audit={'status':'received','request':request,'action_contract':'arc_action_v12',
                        'response_content':raw[:8192].decode('utf-8',errors='replace'),
                        'response_bytes':len(raw),'response_truncated':len(raw)>8192,
                        'response_sha256':hashlib.sha256(raw).hexdigest(),**audit}
                    print(json.dumps({'diagnostic_startup_canary':owner.canary_audit}),flush=True)
                    if len(raw)>8192:raise ValueError('canary evidence ceiling')
                    validate_canary(result.content)
                    owner.canary_audit['status']='passed'
                except Exception as exc:
                    owner.canary_audit.update(status='failed',error=type(exc).__name__+': '+str(exc)[:512])
                    print(json.dumps({'diagnostic_startup_canary':owner.canary_audit}),flush=True)
                    raise RuntimeError('single model canary failed') from exc
        self.service = SingleAuditedCanaryService(self.primary)
        self.diagnostic_calls=0
        self.service.start()  # Includes exactly one actual completion canary.
        self.startup_seconds = time.monotonic() - begin
        self.started = True

    def complete(self, request):
        from certification.phase4_coordinates_v2.cases import load_cases, request_hash
        ordered=load_cases()
        if self.diagnostic_calls>=56 or request_hash(request)!=ordered[self.diagnostic_calls]['request_sha256']:
            raise ValueError('diagnostic request count/allowlist exceeded')
        self.diagnostic_calls+=1
        if not self.started:
            raise RuntimeError('model not started')
        if (request.get('model') != self.primary.binding.model_id or request.get('seed') != 0
                or request.get('temperature') != 0 or request.get('max_tokens') != 128
                or request.get('chat_template_kwargs') != {'enable_thinking': False}):
            raise ValueError('frozen E1S-R request drift')
        from certification.phase4_coordinates_v2.model_transport import OpenAICompatibleCompletionClient
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
