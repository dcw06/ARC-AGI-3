"""Independent request/token replay; imports no model library until explicitly invoked."""
import json
import math
from pathlib import Path

from .inference import digest, prompt_for, requests_for, completion
from .mount_check import canonical
from .runtime import verify_model_code


def audit(worker, requests, rebuild, decode):
    worker = Path(worker)
    calls = [json.loads(row) for row in (worker/'calls.jsonl').read_bytes().splitlines()]
    responses = [json.loads(row) for row in (worker/'responses.jsonl').read_bytes().splitlines()]
    if len(calls) != 6 or len(responses) != 6 or len(requests) != 6:
        raise ValueError('six calls and responses required, no duplicates or omissions')
    for index, (request, call, response) in enumerate(zip(requests, calls, responses), 1):
        case = request['case_id']
        detail = json.loads((worker/(case+'.json')).read_bytes())
        pin = digest(canonical(request))
        rendered, ids, eos = rebuild(request['prompt'])
        expected_response = {'case_id': case, 'model': request['model'],
            'model_revision': request['model_revision'], 'request_sha256': pin,
            **{key: detail[key] for key in ('content', 'finish_reason')}}
        if (type(call['call_number']) is not int or call['call_number'] != index or call['case_id'] != case or call['request_sha256'] != pin
                or canonical(response) != canonical(expected_response)
                or canonical(detail['request']) != canonical(request) or detail['request_sha256'] != pin
                or detail['rendered_prompt'] != rendered or canonical(detail['prompt_token_ids']) != canonical(ids)
                or type(detail['prompt_tokens']) is not int or detail['prompt_tokens'] != len(ids)
                or detail['eos_token_id'] != eos or detail['image_context_tokens'] != 256
                or detail['image_sha256'] != request['image_sha256']
                or canonical(detail['generation_parameters']) != canonical({
                    'max_new_tokens': 4096, 'do_sample': False, 'num_beams': 1})):
            raise ValueError('frozen request/template/observation mismatch: '+case)
        decoded = decode(detail['generated_token_ids'], eos)
        for key, value in decoded.items():
            if canonical(detail[key]) != canonical(value):
                raise ValueError('generated-token/decode mismatch: '+case)
        duration = detail['generation_seconds']
        if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 < duration < 180:
            raise ValueError('generation duration outside frozen limit')
    summary = json.loads((worker/'worker.json').read_bytes())
    if (summary['generation_requests'] != 6 or summary['study_requests'] != 6
            or summary['game_actions'] != 0 or summary['network_attempts'] != 0
            or summary['pretrained_weights_loaded'] is not True or summary['execution_device'] != 'cuda'):
        raise ValueError('worker summary does not match six-case scope')
    return {'request_and_token_replay_passed': True, 'calls_replayed': 6,
            'identification_accuracy_not_assessed_by_replay': True}


def replay(worker, inputs, model_folder):
    """Reconstruct metadata/tokenization from pinned code without loading weights."""
    import os
    import socket
    os.environ.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1', MPLBACKEND='Agg')
    connections = []
    def refuse(*a, **k):
        connections.append(True)
        raise PermissionError('independent replay is offline')
    previous = socket.socket.connect, socket.create_connection
    socket.socket.connect = socket.create_connection = refuse
    try:
        verify_model_code(model_folder)
        import torch
        from transformers import AutoConfig, AutoTokenizer
        from transformers.dynamic_module_utils import get_class_from_dynamic_module
        if torch.cuda.is_initialized():
            raise ValueError('replay must not initialize CUDA')
        config = AutoConfig.from_pretrained(str(model_folder), trust_remote_code=True, local_files_only=True)
        tokenizer = AutoTokenizer.from_pretrained(str(model_folder), trust_remote_code=True,
            local_files_only=True, fix_mistral_regex=False)
        cls = get_class_from_dynamic_module('modeling_internvl_chat.InternVLChatModel',
                                            str(model_folder), local_files_only=True)
        import importlib
        factory = importlib.import_module(cls.__module__).get_conv_template
        meta = type('ReviewedPromptMetadata', (), {'__module__': cls.__module__})()
        meta.template = config.template
        meta.system_message = factory(meta.template).system_message
        meta.num_image_token = int(((config.force_image_size or config.vision_config.image_size)
                                  // config.vision_config.patch_size)**2 * config.downsample_ratio**2)
        def rebuild(prompt):
            rendered, eos, _ = prompt_for(meta, tokenizer, prompt)
            ids = tokenizer(rendered, return_tensors='pt')['input_ids'][0].tolist()
            return rendered, ids, eos
        result = audit(worker, requests_for(inputs), rebuild,
                       lambda ids, eos: completion(tokenizer, ids, eos))
        if connections or torch.cuda.is_initialized():
            raise ValueError('replay attempted network or GPU use')
        return result
    finally:
        socket.socket.connect, socket.create_connection = previous
