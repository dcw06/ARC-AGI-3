"""One real model process; mount inventory, mounted-processor token audit, classified probe failures."""
from dataclasses import replace
from certification.phase4_multimodal_preflight_v2.startup import stage, MODEL_STARTUP_SECONDS
import hashlib
import importlib.metadata
import io
import json
import threading
import time

from pathlib import Path
from certification.phase4_multimodal_preflight_v2.live_probes import require_live_authority as authority
ROOT = Path(__file__).resolve().parents[2]
PINNED_PROCESSOR = {'preprocessor_config.json': '6a970fd06f30e6943b3e2c14d5d3b42d49b06cf99b99103d56689bef462d90f8',
                    'video_preprocessor_config.json': 'e203bc065dfcd75226838b8e937d624bec8f0eb6ef6630a397e9a675f2873ea6'}
PAYLOAD_LIMIT = 262144
IMAGE_PAD = '<|image_pad|>'


def request_hash(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()


def mount_inventory(path, small=2 * 1024**2):
    """Every mounted file name and size; hashes only for small files (configs, templates)."""
    path = Path(path); files = []
    for item in sorted(path.rglob('*')):
        if item.is_symlink(): raise ValueError('symlink in model mount')
        if item.is_file():
            size = item.stat().st_size; row = {'path': item.relative_to(path).as_posix(), 'bytes': size}
            if size <= small: row['sha256'] = hashlib.sha256(item.read_bytes()).hexdigest()
            files.append(row)
    names = {f['path']: f for f in files}
    processor = {name: {'present': name in names, 'sha256': names.get(name, {}).get('sha256'),
                        'matches_pinned': names.get(name, {}).get('sha256') == digest}
                 for name, digest in PINNED_PROCESSOR.items()}
    return {'file_count': len(files), 'files': files, 'processor_files': processor}


def load_processor(model_path, inventory):
    """Dependency check only: failures are recorded and classified, never raised here."""
    status = {'available': False, 'error': None, 'versions': {}}
    missing = [n for n, v in inventory['processor_files'].items() if n == 'preprocessor_config.json' and not v['present']]
    if missing:
        status['error'] = 'missing mounted file: ' + missing[0]; return None, status
    try:
        for name in ('transformers', 'pillow', 'torch', 'torchvision'):
            try: status['versions'][name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError: status['versions'][name] = None
        from PIL import Image  # noqa: F401
        from transformers import AutoProcessor
        processor = AutoProcessor.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
        status['processor_class'] = type(processor).__name__
        status['image_processor_class'] = type(processor.image_processor).__name__
        status['merge_size'] = getattr(processor.image_processor, 'merge_size', None)
        status['available'] = True
        return processor, status
    except Exception as exc:
        status['error'] = type(exc).__name__ + ': ' + str(exc)[:512]
        return None, status


def expected_prompt(tokenizer, processor, request):
    """Expected server prompt tokens by two independent methods; retains processed image geometry."""
    from certification.phase4_multimodal_preflight_v2.cases import image_part
    kwargs = request.get('chat_template_kwargs', {})
    ids = tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                        truncation=False, **kwargs)
    if not isinstance(ids, list) or not ids or any(type(t) is not int for t in ids):
        raise ValueError('invalid tokenizer output')
    raw = image_part(request)
    record = {'template_tokens': len(ids)}
    if raw is None:
        record['expected_prompt_tokens'] = len(ids); return record
    pad = tokenizer.convert_tokens_to_ids(IMAGE_PAD)
    if ids.count(pad) != 1: raise ValueError('expected exactly one image placeholder')
    from PIL import Image
    image = Image.open(io.BytesIO(raw)); image.load(); image = image.convert('RGB')
    text = tokenizer.apply_chat_template(request['messages'], tokenize=False, add_generation_prompt=True, **kwargs)
    full = processor(text=[text], images=[image], return_tensors='np')
    thw = [int(v) for v in full['image_grid_thw'][0]]
    merge = int(processor.image_processor.merge_size); patch = int(processor.image_processor.patch_size)
    image_tokens = thw[0] * thw[1] * thw[2] // (merge * merge)
    manual = len(ids) - 1 + image_tokens
    record.update(input_width=image.width, input_height=image.height, image_grid_thw=thw,
                  processed_height=thw[1] * patch, processed_width=thw[2] * patch,
                  image_tokens_processor=image_tokens, processor_full_prompt_tokens=int(len(full['input_ids'][0])),
                  manual_prompt_tokens=manual)
    if record['processor_full_prompt_tokens'] != manual:
        raise ValueError('processor methods disagree: full %d manual %d' % (record['processor_full_prompt_tokens'], manual))
    record['expected_prompt_tokens'] = manual
    return record


def classified(kind, message, content='', **audit):
    from certification.phase4_multimodal_preflight_v2.response_evidence import ResponseValidationError, capture
    return ResponseValidationError(message, capture(content, {'failure_kind': kind, **audit}))


def audited_probe(tokenizer, processor, request, complete, context_limit=65536, frozen=None, retain=None):
    """Probe call with the mounted processor's expected count; every failure is classified and retained."""
    from certification.phase4_multimodal_preflight_v2.cases import image_part
    from certification.phase4_multimodal_preflight_v2.model_transport import ServerRejectedError
    from certification.phase4_multimodal_preflight_v2.response_evidence import capture, emit
    digest = request_hash(request); has_image = image_part(request) is not None
    if has_image and processor is None:
        raise classified('dependency_missing', 'mounted processor unavailable; image request not sent', request_sha256=digest)
    if max(len(json.dumps(request).encode()), len(json.dumps(request, separators=(',', ':')).encode())) > PAYLOAD_LIMIT:
        raise ValueError('payload limit')
    try: expected = expected_prompt(tokenizer, processor, request)
    except ValueError as exc:
        raise classified('token_accounting_mismatch', 'offline expectation failed: ' + str(exc)[:256], request_sha256=digest) from exc
    limit = request.get('max_tokens')
    if type(limit) is not int or not 0 < limit <= 128 or expected['expected_prompt_tokens'] + limit > context_limit:
        raise ValueError('context/completion limit exceeded')
    begin = time.monotonic()
    try: result = complete(request)
    except ServerRejectedError as exc:
        kind = 'image_rejected_by_server' if has_image else 'server_rejected'
        raise classified(kind, str(exc), exc.body, request_sha256=digest, http_status=exc.status,
                         tokenizer_prompt_tokens=expected['expected_prompt_tokens'], expectation=expected) from exc
    record = {'request_sha256': digest, 'tokenizer_prompt_tokens': expected['expected_prompt_tokens'],
              'server_prompt_tokens': result.prompt_tokens, 'server_completion_tokens': result.completion_tokens,
              'finish_reason': result.finish_reason, 'service_seconds': time.monotonic() - begin,
              'expectation': expected, 'frozen_local_expected_prompt_tokens': frozen}
    evidence = capture(result.content, record); emit(evidence)
    if retain is not None: retain(evidence)
    from certification.phase4_multimodal_preflight_v2.response_evidence import ResponseValidationError
    if evidence['response_truncated']:
        raise ResponseValidationError('response evidence ceiling', evidence)
    if (type(result.prompt_tokens) is not int or result.prompt_tokens != expected['expected_prompt_tokens']
            or type(result.completion_tokens) is not int or not 0 <= result.completion_tokens <= limit):
        evidence['audit']['failure_kind'] = 'token_accounting_mismatch'
        raise ResponseValidationError('server/processor token-count mismatch or missing usage', evidence)
    return result, record


def audited_completion(tokenizer, request, complete, context_limit=65536, retain=None):
    """Text-only startup canary path (frozen request), now retaining finish_reason."""
    if any(not isinstance(m.get('content'), str) for m in request['messages']):
        raise ValueError('canary must be text-only')
    tokens = tokenizer.apply_chat_template(request['messages'], tokenize=True,
        add_generation_prompt=True, truncation=False, **request.get('chat_template_kwargs', {}))
    limit = request.get('max_tokens')
    if type(limit) is not int or not 0 < limit <= 128 or len(tokens) + limit > context_limit:
        raise ValueError('context/completion limit exceeded')
    begin = time.monotonic()
    result = complete(request)
    record = {'request_sha256': request_hash(request), 'tokenizer_prompt_tokens': len(tokens),
              'server_prompt_tokens': result.prompt_tokens, 'server_completion_tokens': result.completion_tokens,
              'finish_reason': getattr(result, 'finish_reason', None), 'service_seconds': time.monotonic() - begin}
    from certification.phase4_multimodal_preflight_v2.response_evidence import capture, emit, ResponseValidationError
    evidence = capture(result.content, record); emit(evidence)
    if retain is not None: retain(evidence)
    if evidence['response_truncated']: raise ResponseValidationError('response evidence ceiling', evidence)
    if (type(result.prompt_tokens) is not int or result.prompt_tokens != len(tokens)
            or type(result.completion_tokens) is not int or not 0 <= result.completion_tokens <= limit):
        raise ResponseValidationError('server/tokenizer token-count mismatch or missing usage', evidence)
    return result, record


class SharedModelService:
    def __init__(self, scratch, root=ROOT):
        self.root, self.scratch = root, scratch
        self.started = False
        self.audit_records = []
        self.lock = threading.Lock()
        self.service = None
        self.processor = None
        self.preflight = {}

    def start(self):
        with stage('authority'):
            authority(self.root)
        begin = time.monotonic()
        with stage('runtime_check'):
            from certification.phase4_v6.target_install_probe_r5 import MODEL_CHECK
            exec(compile(MODEL_CHECK, 'v13_monitored_model_readiness', 'exec'), {})
        from certification.phase4_multimodal_preflight_v2.model_process import ModelService, load_operational_primary
        from certification.phase4_multimodal_preflight_v2.model_artifact import verify_artifact
        self.primary = replace(load_operational_primary(self.root), scratch_log=Path('/dev/stdout'),
            request_timeout_seconds=120, completion_canary_timeout_seconds=120,
            readiness_timeout_seconds=MODEL_STARTUP_SECONDS, hard_seconds=1680, finalization_reserve_seconds=300, queue_capacity=1, queue_workers=1)
        with stage('artifact_hash'):
            self.artifact = verify_artifact(self.primary)
        with stage('tokenizer_verification'):
            if importlib.metadata.version('transformers').split('+')[0] != '4.57.6':
                raise ValueError('tokenizer version drift')
            from certification.phase4_multimodal_preflight_v2.tokenizer_binding import verify
            verify(self.primary.model_path)
        with stage('mount_inventory'):
            inventory = mount_inventory(self.primary.model_path)
        with stage('processor_load'):
            self.processor, processor_status = load_processor(self.primary.model_path, inventory)
        self.preflight = {'mount_inventory': inventory, 'processor': processor_status}
        print(json.dumps({'multimodal_preflight_mount': {'file_count': inventory['file_count'],
            'processor_files': inventory['processor_files'], 'processor': processor_status}}), flush=True)
        with stage('tokenizer_load'):
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
                if owner.canary_audit is not None:
                    raise RuntimeError('canary already attempted')
                owner.canary_audit = {'status': 'attempted'}
                try:
                    from certification.phase4_multimodal_preflight_v2.model_transport import OpenAICompatibleCompletionClient
                    import requests
                    from certification.phase4_multimodal_preflight_v2.action_contract import validate_canary
                    from certification.phase4_multimodal_preflight_v2.cases import canary_request
                    request = canary_request(self.primary.binding.model_id)
                    with requests.Session() as session:
                        client = OpenAICompatibleCompletionClient(self.primary.base_url,
                            session=session, timeout_seconds=self.primary.completion_canary_timeout_seconds)
                        def retain(evidence):
                            owner.canary_audit = {'status': 'received', 'request': request,
                                'action_contract': 'arc_action_v12', **evidence['audit'],
                                **{k: v for k, v in evidence.items() if k != 'audit'}}
                        result, audit = audited_completion(owner.tokenizer, request, client.complete, owner.context_limit, retain=retain)
                    raw = result.content.encode()
                    owner.canary_audit = {'status': 'received', 'request': request, 'action_contract': 'arc_action_v12',
                        'response_content': raw[:8192].decode('utf-8', errors='replace'),
                        'response_bytes': len(raw), 'response_truncated': len(raw) > 8192,
                        'response_sha256': hashlib.sha256(raw).hexdigest(), **audit}
                    print(json.dumps({'diagnostic_startup_canary': owner.canary_audit}), flush=True)
                    if len(raw) > 8192: raise ValueError('canary evidence ceiling')
                    validate_canary(result.content)
                    owner.canary_audit['status'] = 'passed'
                except Exception as exc:
                    owner.canary_audit.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:512])
                    print(json.dumps({'diagnostic_startup_canary': owner.canary_audit}), flush=True)
                    raise RuntimeError('single model canary failed') from exc
        self.service = SingleAuditedCanaryService(self.primary)
        self.probe_calls = 0
        self.service.start()  # Includes exactly one actual text completion canary.
        self.startup_seconds = time.monotonic() - begin
        self.started = True

    def complete(self, request):
        from certification.phase4_multimodal_preflight_v2.cases import load_cases
        ordered = load_cases()
        if self.probe_calls >= len(ordered) or request_hash(request) != ordered[self.probe_calls]['request_sha256']:
            raise ValueError('probe request count/allowlist exceeded')
        frozen = ordered[self.probe_calls].get('frozen_local_expectation', {}).get('expected_prompt_tokens')
        self.probe_calls += 1
        if not self.started:
            raise RuntimeError('model not started')
        if (request.get('model') != self.primary.binding.model_id or request.get('seed') != 0
                or request.get('temperature') != 0 or request.get('max_tokens') != 64
                or request.get('chat_template_kwargs') != {'enable_thinking': False}):
            raise ValueError('frozen probe request drift')
        from certification.phase4_multimodal_preflight_v2.model_transport import OpenAICompatibleCompletionClient
        import requests
        with requests.Session() as session:
            client = OpenAICompatibleCompletionClient(self.primary.base_url, session=session,
                timeout_seconds=self.primary.request_timeout_seconds)
            result, record = audited_probe(self.tokenizer, self.processor, request, client.complete,
                                           self.context_limit, frozen=frozen)
        with self.lock:
            self.audit_records.append(record)
        return result, record
