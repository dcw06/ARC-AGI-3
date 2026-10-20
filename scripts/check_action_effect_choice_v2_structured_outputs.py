"""CPU-only pinned-vLLM request and grammar admission check, without model weights.

Use the installed vLLM 0.19.0 interpreter and the retained local tokenizer. This
checks canonical serializations of every semantic answer, not every JSON spelling.
The host parser remains authoritative, including duplicate-key rejection.
"""
import argparse
from copy import deepcopy
import hashlib
import importlib.metadata as md
import itertools
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.action_effect_choice_v2.interface import response_schema, parse_choice, EFFECTS
from research.action_effect_choice_v2.preparation import verify
from research.initial_geometry_assistance_v1.live_io import sha, write_new


def answers(index):
    for a, b, choice, observed, check in itertools.product(
            EFFECTS, EFFECTS, ('A', 'B'),
            ('not_applicable',) if index == 0 else ('yes', 'no', 'unknown'),
            ('not_applicable',) if index == 0 else ('matched', 'mismatched', 'unknown')):
        yield {'candidate_predictions': {'A': a, 'B': b}, 'selected_candidate': choice,
               'observed_previous_change': observed, 'previous_prediction_check': check}


def invalid_texts(index):
    value = next(answers(index))
    mutations = []
    for item in (0, '0', True, None, [], {}, 'yes'):
        changed = deepcopy(value); changed['candidate_predictions']['A'] = item
        mutations.append(changed)
    for key in value:
        changed = deepcopy(value); del changed[key]; mutations.append(changed)
    for key in ('selected_candidate', 'observed_previous_change', 'previous_prediction_check'):
        for item in (0, True, None, [], 'invalid'):
            changed = deepcopy(value); changed[key] = item; mutations.append(changed)
    changed = deepcopy(value); changed['extra'] = 1; mutations.append(changed)
    changed = deepcopy(value); changed['candidate_predictions']['C'] = 'none'; mutations.append(changed)
    for key, item in (('observed_previous_change', 'yes' if index == 0 else 'not_applicable'),
                      ('previous_prediction_check', 'matched' if index == 0 else 'not_applicable')):
        changed = deepcopy(value); changed[key] = item; mutations.append(changed)
    values = [json.dumps(item, separators=(',', ':')) for item in mutations]
    raw = json.dumps(value, separators=(',', ':'))
    values += [raw[:-1], raw+'garbage', '```json\n'+raw+'\n```',
               raw[:-1]+',"selected_candidate":"B"}']
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--input-pin', required=True)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--request-audit', type=Path, required=True,
                        help='CPU rehearsal requests, including reached and hypothetical second phases')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.environ.update(CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void',
                      HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    interfaces = {line.split(':')[0].strip() for line in Path('/proc/net/dev').read_text().splitlines()[2:] if ':' in line}
    if sys.platform != 'linux' or interfaces != {'lo'}:
        raise ValueError('offline loopback-only Linux namespace required')
    manifest = verify(args.inputs, args.input_pin)
    if md.version('vllm') != '0.19.0' or md.version('transformers') != '4.57.6':
        raise ValueError('pinned native runtime differs')
    import torch
    from transformers import AutoTokenizer
    from vllm.config import StructuredOutputsConfig
    from vllm.sampling_params import SamplingParams, StructuredOutputsParams
    from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest
    if torch.cuda.is_initialized(): raise ValueError('GPU initialized in CPU check')
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
    config = StructuredOutputsConfig()
    entries = []
    for index in (0, 1):
        schema = response_schema(index)
        params = SamplingParams(max_tokens=256, structured_outputs=StructuredOutputsParams(json=schema))
        params._validate_structured_outputs(config, tokenizer)
        backend = params.structured_outputs._backend
        if backend == 'xgrammar':
            import xgrammar as xgr
            compiled = xgr.GrammarCompiler(xgr.TokenizerInfo.from_huggingface(tokenizer)).compile_json_schema(json.dumps(schema))
            def admits(text):
                matcher = xgr.GrammarMatcher(compiled)
                if not all(matcher.accept_token(token) for token in tokenizer.encode(text, add_special_tokens=False)):
                    return False
                return any(matcher.accept_token(token) for token in matcher.stop_token_ids[:1]) and matcher.is_terminated()
        elif backend == 'guidance':
            import llguidance
            import llguidance.hf
            from vllm.v1.structured_output.backend_guidance import serialize_guidance_grammar
            from vllm.v1.structured_output.request import StructuredOutputOptions
            grammar = serialize_guidance_grammar(StructuredOutputOptions.JSON, json.dumps(schema))
            info = llguidance.hf.from_tokenizer(tokenizer)
            def admits(text):
                matcher = llguidance.LLMatcher(info, grammar)
                return bool(matcher.consume_tokens(tokenizer.encode(text, add_special_tokens=False))) and not matcher.is_error() and matcher.is_accepting()
        else: raise ValueError('unexamined selected backend: '+str(backend))
        valid = 0
        for value in answers(index):
            text = json.dumps(value, separators=(',', ':'))
            parse_choice(text, first=index == 0)
            if not admits(text): raise ValueError('canonical valid answer refused by native decoder')
            valid += 1
        invalid = 0
        for text in invalid_texts(index):
            try: parse_choice(text, first=index == 0)
            except ValueError: pass
            else: raise ValueError('adversarial fixture unexpectedly valid')
            if admits(text): raise ValueError('native decoder admitted adversarial answer')
            invalid += 1
        entries.append({'study_decision_index': index, 'backend': backend,
                        'schema_sha256': hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(),
                        'canonical_valid_answers_admitted': valid, 'invalid_answers_rejected': invalid})
    bodies = []
    for name in manifest['files_sha256']:
        if not name.startswith('model-inputs/'): continue
        bodies.append(json.loads((args.inputs/name).read_bytes()))
    bodies.extend(row['body'] for row in json.loads(args.request_audit.read_bytes()))
    requests = 0
    phases = set()
    for body in bodies:
        request = ChatCompletionRequest.model_validate(body)
        # Validate the actual request wrapper, not just a detached JSON schema.
        if (request.response_format.type != 'json_schema' or
                request.response_format.json_schema.json_schema != body['response_format']['json_schema']['schema'] or
                request.response_format.json_schema.strict is not True):
            raise ValueError('vLLM request wrapper changed the supplied constraints')
        sampling = request.to_sampling_params(max_tokens=body['max_tokens'], default_sampling_params={})
        sampling._validate_structured_outputs(config, tokenizer)
        if sampling.structured_outputs.json != body['response_format']['json_schema']['schema']:
            raise ValueError('request-to-sampling conversion changed the schema')
        phases.add(json.loads(body['messages'][1]['content'][-1]['text'])['study_phase']['study_decision_index'])
        requests += 1
    if phases != {0, 1}: raise ValueError('both actual request phases must be checked')
    if torch.cuda.is_initialized(): raise ValueError('GPU initialized in CPU check')
    verify(args.inputs, args.input_pin)
    receipt = {'passed': True, 'input_manifest_sha256': args.input_pin,
               'versions': {name: md.version(name) for name in ('vllm', 'torch', 'transformers', 'xgrammar', 'llguidance', 'jsonschema')},
               'configured_backend': config.backend, 'phases': entries, 'request_wrappers_and_sampling_checked': requests,
               'CPU_request_audit_sha256': sha(args.request_audit),
               'tokenizer_files_sha256': {p.relative_to(args.tokenizer).as_posix(): sha(p) for p in sorted(args.tokenizer.rglob('*')) if p.is_file()},
               'GPU_initialized': False, 'model_generations': 0, 'provider_writes': 0,
               'qualification': 'CPU request/grammar compatibility only. Does not establish real server decoding, GPU setup, forecast accuracy or improved gameplay.'}
    write_new(args.output, receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__': main()
