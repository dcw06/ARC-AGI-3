"""Six uncued whole-object inventories and deterministic pixel-mask proposals.

Derived from the verified cued worker; no model execution on import.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import signal
import socket
import time

from research.molmopoint_identification_v1.adapter import MODEL, REVISION, prepare_prompt_inputs
from .decoding import decode_inventory as decode_generation
from .prepare import requests_for, MAX_NEW_TOKENS
from .masks import seed_masks
from certification.phase4_multimodal_preflight_v3.images import grid_from_png
from research.object_identification_v1.mount_check import canonical

def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def metadata_value(value):
    """Preserve nested native arrays, including the list of subpatch mappings."""
    if hasattr(value,'tolist'):
        return metadata_value(value.tolist())
    if isinstance(value,(list,tuple)):
        return [metadata_value(v) for v in value]
    if isinstance(value,dict):
        return {k:metadata_value(v) for k,v in value.items()}
    if value is None or type(value) in (int,float,str,bool):
        return value
    raise ValueError('unexpected native metadata type')


def write(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


def attach_masks(detail, image_bytes, request):
    """Derive proposals exclusively from visible pixels and native predictions."""
    grid = grid_from_png(image_bytes, cell=7)
    pin = sha(canonical(grid))
    if pin != request['grid_sha256']:
        raise ValueError('pixel-tool grid differs from visible input')
    if type(detail.get('decode_valid')) is not bool:
        raise ValueError('explicit native decode validity required')
    detail['grid_sha256'] = pin
    detail['objects'] = seed_masks(grid, detail['points']) if detail['decode_valid'] else []
    return detail


def execute_cases(requests, generate, output, deadline, now=time.monotonic):
    """Durable admission precedes each call; raw results precede any decoding."""
    if len(requests) != 6 or [r['case_id'] for r in requests] != [f'board-{i:02d}' for i in range(1,7)]:
        raise ValueError('exactly six ordered cases required before any generation')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for index, request in enumerate(requests, 1):
        if now()+180 >= deadline:
            raise TimeoutError('not enough generation headroom')
        write(output/(request['case_id']+'-admission.json'), dict(
            call_number=index, request_sha256=sha(canonical(request)), request=request,
            admitted_at_monotonic=now()))
        until = min(deadline, now()+180)
        if now() >= deadline-180:
            raise TimeoutError('generation admission closed during evidence write')
        detail = generate(request, until)
        detail['case_finalized_at_monotonic']=now()
        write(output/(request['case_id']+'.json'), detail)
        if now() >= until:
            raise TimeoutError('generation/finalization exceeded its deadline')
    summary = dict(generation_requests=6, game_actions=0, scorecards=0,
                   model=MODEL, revision=REVISION, pretrained_weights_loaded=True,
                   execution_device='cuda', automatic_retries=0)
    write(output/'worker.json', summary)
    if now() >= deadline:
        raise TimeoutError('worker summary exceeded work deadline')
    return summary


def native_generate(model, processor, image, request, until, torch, stopping, raw_sink=None):
    """Publisher's full-image API, preserving raw IDs even for invalid points."""
    started = time.monotonic()
    inputs, metadata, logits = prepare_prompt_inputs(model, processor, image, request['prompt'])
    prompt_ids = inputs['input_ids'][0].tolist()
    inputs = {key:value.to('cuda:0') for key,value in inputs.items()}
    if time.monotonic() >= until:
        raise TimeoutError('preprocessing consumed generation budget')
    with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
        generated = model.generate(**inputs, logits_processor=logits, max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False, num_beams=1, return_dict_in_generate=True, output_scores=False,
            stopping_criteria=stopping)
    torch.cuda.synchronize()
    sequence = generated.sequences[0].tolist()
    if sequence[:len(prompt_ids)] != prompt_ids:
        raise ValueError('decoder-only output does not preserve the input prefix')
    ids = sequence[len(prompt_ids):]
    eos = model.generation_config.eos_token_id
    eos = [eos] if type(eos) is int else eos
    if not eos or any(type(v) is not int for v in eos):
        raise ValueError('invalid EOS contract')
    finish = 'stop' if ids and ids[-1] in eos else 'length' if len(ids) == MAX_NEW_TOKENS else 'interrupted'
    # Store raw data separately from decode validity. Bad localization never disappears.
    result = dict(request=request, request_sha256=sha(canonical(request)),
        generated_token_ids=ids, prompt_token_ids=prompt_ids, eos_token_ids=eos,
        prompt_tokens=len(prompt_ids), completion_tokens=len(ids), finish_reason=finish,
        raw_text_with_special_tokens=processor.post_process_image_text_to_text(
            [ids], skip_special_tokens=False, clean_up_tokenization_spaces=False)[0],
        metadata=metadata_value(metadata), decode_valid=False, points=[],
        generation_parameters={'max_new_tokens':MAX_NEW_TOKENS,'do_sample':False,'num_beams':1},
        generation_started_at_monotonic=started,call_deadline_monotonic=until,
        generated_at_monotonic=time.monotonic(),
        generation_seconds=time.monotonic()-started)
    if raw_sink is not None:
        raw_sink(result)
    try:
        result.update(decode_generation(model,processor,ids,metadata,(448,448),finish_reason=finish))
        result['decode_valid'] = True
    except Exception as exc:
        result['decode_error'] = type(exc).__name__+': '+str(exc)
    return result


def run(model_folder, inputs, output, expected_versions, work_deadline):
    """Supervisor has verified all model/wheel/input hashes before this import."""
    import torch
    from PIL import Image
    from transformers import AutoModelForImageTextToText, AutoProcessor, StoppingCriteria, StoppingCriteriaList

    actual = {re.sub('[-_.]+','-',d.metadata['Name']).lower():d.version
              for d in importlib.metadata.distributions()}
    if actual != expected_versions or actual.get('transformers') != '4.57.1' or torch.version.cuda != '12.8':
        raise ValueError('isolated installed runtime differs from the separate MolmoPoint lock')
    if torch.cuda.device_count() != 1 or 'RTX PRO 6000' not in torch.cuda.get_device_name(0):
        raise ValueError('expected exactly one RTX PRO 6000')
    requests = requests_for(inputs)
    attempted = []
    def refuse(*args,**kwargs):
        attempted.append(True)
        raise PermissionError('offline inference: network prohibited')
    old_connect, old_create = socket.socket.connect, socket.create_connection
    socket.socket.connect, socket.create_connection = refuse, refuse
    torch.manual_seed(0)
    torch.set_num_threads(2)
    def expired(*_):
        raise TimeoutError('model load or generation deadline reached')
    old_handler = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, max(.001,min(work_deadline,time.monotonic()+900)-time.monotonic()))
        processor = AutoProcessor.from_pretrained(str(model_folder),trust_remote_code=True,
            padding_side='left',local_files_only=True,use_fast=False)
        model = AutoModelForImageTextToText.from_pretrained(str(model_folder),trust_remote_code=True,
            local_files_only=True,torch_dtype=torch.bfloat16,low_cpu_mem_usage=True,
            attn_implementation='sdpa').eval().to('cuda:0')
        torch.cuda.synchronize()
        if (model.config.model_type != 'molmo_point' or
                any(p.device.type != 'cuda' or p.is_floating_point() and p.dtype != torch.bfloat16
                    for p in model.parameters())):
            raise ValueError('model identity, device or explicit BF16 differs')
        signal.setitimer(signal.ITIMER_REAL, 0)
        class Deadline(StoppingCriteria):
            def __init__(self, until):
                self.until = until
            def __call__(self,*args,**kwargs):
                return time.monotonic() >= self.until
        def generate(request, until):
            signal.setitimer(signal.ITIMER_REAL,max(.001,until-time.monotonic()))
            try:
                with Image.open(Path(inputs)/(request['case_id']+'.png')) as image:
                    if image.size != (448,448) or image.mode != 'RGB':
                        raise ValueError('plain448 RGB image required')
                    detail = native_generate(model,processor,image,request,until,torch,
                        StoppingCriteriaList([Deadline(until)]),
                        raw_sink=lambda row: write(Path(output)/(request['case_id']+'-raw.json'),row))
                    return attach_masks(detail,
                        (Path(inputs)/(request['case_id']+'.png')).read_bytes(), request)
            finally:
                signal.setitimer(signal.ITIMER_REAL,0)
        result = execute_cases(requests,generate,output,work_deadline)
        if attempted:
            raise ValueError('network was attempted')
        return result
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old_handler)
        socket.socket.connect, socket.create_connection = old_connect, old_create
