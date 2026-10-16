"""Pinned offline InternVL generation contract; importing this module never loads weights."""
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import signal
import socket
import time

from .mount_check import canonical
from .probe import MODEL, MODEL_REVISION, PROMPT, MAX_OUTPUT_TOKENS, strict_load
from .runtime import prepare_pixels, verify_model_code


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def requests_for(inputs):
    """Reconstruct every request independently of the mounted request file."""
    inputs = Path(inputs)
    actual = [strict_load(raw) for raw in (inputs/'requests.jsonl').read_bytes().splitlines()]
    expected = []
    for index in range(1, 7):
        case = f'board-{index:02d}'
        image = inputs/(case+'.png')
        expected.append({'case_id': case, 'image': 'inputs/'+case+'.png',
                         'image_sha256': digest(image.read_bytes()), 'prompt': PROMPT,
                         'model': MODEL, 'model_revision': MODEL_REVISION,
                         'max_tokens': MAX_OUTPUT_TOKENS, 'temperature': 0, 'stream': False})
    if canonical(actual) != canonical(expected):
        raise ValueError('mounted requests differ from the frozen six-case contract')
    return expected


def prompt_for(model, tokenizer, prompt):
    """Publisher's pinned single-image template, without chat()'s output trimming."""
    module = importlib.import_module(type(model).__module__)
    template = module.get_conv_template(model.template)
    template.system_message = model.system_message
    template.append_message(template.roles[0], '<image>\n'+prompt)
    template.append_message(template.roles[1], None)
    rendered = template.get_prompt()
    if rendered.count('<image>') != 1:
        raise ValueError('ambiguous image placeholder')
    rendered = rendered.replace('<image>', '<img>'+'<IMG_CONTEXT>'*model.num_image_token+'</img>', 1)
    eos = tokenizer.convert_tokens_to_ids(template.sep.strip())
    context = tokenizer.convert_tokens_to_ids('<IMG_CONTEXT>')
    if (type(eos) is not int or type(context) is not int or eos == context
            or min(eos, context) < 0 or max(eos, context) >= len(tokenizer)
            or tokenizer.unk_token_id in (eos, context)):
        raise ValueError('invalid frozen template special tokens')
    model.img_context_token_id = context
    return rendered, eos, context


def completion(tokenizer, ids, eos):
    """Keep generated tokens and both decodings; never strip/repair model JSON."""
    if (not ids or len(ids) > MAX_OUTPUT_TOKENS
            or any(type(token) is not int or not 0 <= token < len(tokenizer) for token in ids)):
        raise ValueError('invalid generation token evidence')
    if ids[-1] != eos and len(ids) != MAX_OUTPUT_TOKENS:
        raise ValueError('unexplained early generation stop')
    return {'generated_token_ids': ids, 'completion_tokens': len(ids),
            'content': tokenizer.decode(ids, skip_special_tokens=True),
            'raw_text_with_special_tokens': tokenizer.decode(ids, skip_special_tokens=False),
            'finish_reason': 'stop' if ids[-1] == eos else 'length'}


def execute_cases(requests, generate, output, deadline, now=time.monotonic):
    """Write a durable admission before EACH of six calls; no repair or retries."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with (output/'calls.jsonl').open('xb') as journal, (output/'responses.jsonl').open('xb') as responses:
        for index, request in enumerate(requests, 1):
            if now()+180 >= deadline:
                raise TimeoutError('insufficient admission headroom for next generation')
            if index > 6:
                raise ValueError('generation-request cap exceeded')
            request_hash = digest(canonical(request))
            admitted = {'call_number': index, 'case_id': request['case_id'],
                        'request_sha256': request_hash, 'admitted_at_monotonic': now()}
            journal.write(canonical(admitted))
            journal.flush()
            os.fsync(journal.fileno())
            until = now()+180
            if until >= deadline:
                raise TimeoutError('admission closed during journal finalization')
            detail = generate(request, until)
            if now() >= deadline:
                raise TimeoutError('generation returned after work deadline')
            # The scorer's strict response shape remains unchanged. Detailed raw
            # tokens, template and usage are retained separately for replay.
            response = {key: detail[key] for key in ('content', 'finish_reason')}
            response.update(case_id=request['case_id'], model=MODEL, model_revision=MODEL_REVISION,
                            request_sha256=request_hash)
            responses.write(canonical(response))
            responses.flush()
            os.fsync(responses.fileno())
            with (output/(request['case_id']+'.json')).open('xb') as stream:
                stream.write(canonical({'request': request, 'request_sha256': request_hash, **detail}))
    if len(requests) != 6:
        raise ValueError('six planned requests required')
    return {'generation_requests': 6, 'study_requests': 6, 'game_actions': 0}


def run(model_folder, inputs, output, expected_versions, work_deadline):
    """Called only by the future authorized supervisor in the isolated interpreter."""
    import torch
    from transformers import AutoModel, AutoTokenizer, StoppingCriteria, StoppingCriteriaList

    verify_model_code(model_folder)
    actual = {re.sub('[-_.]+', '-', dist.metadata['Name']).lower(): dist.version
              for dist in importlib.metadata.distributions()}
    if actual != expected_versions or torch.version.cuda != '12.8':
        raise ValueError('isolated 175-package runtime differs from the validated installation')
    if torch.cuda.device_count() != 1 or 'RTX PRO 6000' not in torch.cuda.get_device_name(0):
        raise ValueError('expected exactly one RTX PRO 6000')
    connections = []
    def refuse(*args, **kwargs):
        connections.append(True)
        raise PermissionError('inference is offline')
    old_connect, old_create = socket.socket.connect, socket.create_connection
    socket.socket.connect = refuse
    socket.create_connection = refuse
    try:
        requests = requests_for(inputs)
        torch.manual_seed(0)
        torch.set_num_threads(2)
        load_deadline = min(work_deadline, time.monotonic()+900)
        def expired(*_):
            raise TimeoutError('model load or generation deadline reached')
        old_handler = signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, load_deadline-time.monotonic()))
        try:
            tokenizer = AutoTokenizer.from_pretrained(str(model_folder), local_files_only=True,
                trust_remote_code=True, fix_mistral_regex=False)
            model = AutoModel.from_pretrained(str(model_folder), local_files_only=True,
                trust_remote_code=True, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True,
                use_flash_attn=False).eval().to('cuda:0')
            if any(p.device.type != 'cuda' for p in model.parameters()) or model.num_image_token != 256:
                raise ValueError('model device or single-tile vision contract mismatch')
            torch.cuda.synchronize()
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)

        class Deadline(StoppingCriteria):
            def __init__(self, until):
                self.until = until
            def __call__(self, input_ids, scores, **kwargs):
                return time.monotonic() >= self.until

        def generate(request, until):
            started = time.monotonic()
            old_handler = signal.signal(signal.SIGALRM, expired)
            signal.setitimer(signal.ITIMER_REAL, max(0.001, until-started))
            try:
                rendered, eos, context = prompt_for(model, tokenizer, request['prompt'])
                encoded = tokenizer(rendered, return_tensors='pt')
                ids, mask = encoded['input_ids'].to('cuda:0'), encoded['attention_mask'].to('cuda:0')
                if int((ids == context).sum()) != 256:
                    raise ValueError('image-token count mismatch')
                pixels, _ = prepare_pixels(Path(inputs)/(request['case_id']+'.png'), torch.bfloat16)
                if time.monotonic() >= until:
                    raise TimeoutError('generation admission closed during preprocessing')
                with torch.inference_mode():
                    generated = model.generate(pixel_values=pixels.to('cuda:0'), input_ids=ids,
                        attention_mask=mask, max_new_tokens=MAX_OUTPUT_TOKENS, do_sample=False,
                        num_beams=1, eos_token_id=eos, pad_token_id=eos,
                        return_dict_in_generate=True, output_scores=False,
                        stopping_criteria=StoppingCriteriaList([Deadline(until)]))
                torch.cuda.synchronize()
                if time.monotonic() >= until:
                    raise TimeoutError('generation deadline reached')
                detail = completion(tokenizer, generated.sequences[0].tolist(), eos)
                detail.update(rendered_prompt=rendered, prompt_token_ids=ids[0].tolist(),
                              prompt_tokens=ids.shape[-1], image_context_tokens=256,
                              eos_token_id=eos, generation_seconds=time.monotonic()-started,
                              started_at_monotonic=started, returned_at_monotonic=time.monotonic(),
                              generation_parameters={'max_new_tokens': MAX_OUTPUT_TOKENS,
                                  'do_sample': False, 'num_beams': 1},
                              image_sha256=request['image_sha256'])
                return detail
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_handler)
        result = execute_cases(requests, generate, output, work_deadline)
        if connections:
            raise ValueError('a network call was attempted')
        result.update(model=MODEL, revision=MODEL_REVISION, network_attempts=0,
                      pretrained_weights_loaded=True, execution_device='cuda',
                      torch_cuda_build=torch.version.cuda,
                      model_class=type(model).__name__, tokenizer_class=type(tokenizer).__name__)
        with (Path(output)/'worker.json').open('xb') as stream:
            stream.write(canonical(result))
        return result
    finally:
        socket.socket.connect, socket.create_connection = old_connect, old_create
