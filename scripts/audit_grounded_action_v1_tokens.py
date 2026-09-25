"""Audit exact offline-engine requests and adaptive frame stress with pinned tokenizer."""
import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VERSION = {'transformers': '4.57.6', 'tokenizers': '0.22.2', 'jinja2': '3.1.6'}


def count(tokenizer, request):
    tokens = tokenizer.apply_chat_template(request['messages'], tokenize=True,
                                           add_generation_prompt=True, truncation=False,
                                           **request['chat_template_kwargs'])
    size = len(json.dumps(request, separators=(',', ':')).encode())
    return {'prompt_tokens': len(tokens), 'completion_cap': request['max_tokens'], 'request_bytes': size,
            'admissible': len(tokens) <= 60000 and len(tokens) + request['max_tokens'] <= 65536 and size <= 196608}


def run(record, folder, output):
    from transformers import AutoTokenizer
    from certification.phase4_integrated_v2.tokenizer_binding import verify
    from research.grounded_action_v1.contract import feedback_grid
    versions = {k: importlib.metadata.version(k) for k in VERSION}
    if versions != VERSION:
        raise ValueError('tokenizer environment drift')
    verify(folder)
    tokenizer = AutoTokenizer.from_pretrained(str(folder), local_files_only=True, trust_remote_code=False)
    evidence = json.loads(Path(record).read_bytes())
    if evidence['status'] != 'complete' or len(evidence['episodes']) != 2:
        raise ValueError('incomplete CPU evidence')
    rows = []
    for episode in evidence['episodes']:
        for index, call in enumerate(episode['calls']):
            request = call['request']
            row = {'arm': episode['arm'], 'call_index': index, 'stage': call['stage'],
                   'request_sha256': hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                   **count(tokenizer, request)}
            if row['request_sha256'] != call['request_sha256'] or not row['admissible']:
                raise ValueError('exact request limit/hash')
            rows.append(row)
    initial = json.loads((ROOT / 'reports/integrated_case_v1/initial_observation.json').read_bytes())
    frame = feedback_grid(initial['frames'][-1])
    stress = []
    # The feedback request carries one pre-action frame and all returned frames
    # in the exact lossless hex-row format admitted by the live contract.
    for episode in evidence['episodes']:
        sample = next(c['request'] for c in episode['calls'] if c['stage'] == 'feedback')
        for count_frames in range(1, 9):
            request = copy.deepcopy(sample)
            payload = json.loads(request['messages'][1]['content'])
            payload['before']['frames'] = [frame]
            payload['observation']['frames'] = [frame] * count_frames
            request['messages'][1]['content'] = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            stress.append({'arm': episode['arm'], 'returned_frames': count_frames, **count(tokenizer, request)})
    dense = [''.join('0123456789abcdef'[(x + 7 * y) % 16] for x in range(64))
             for y in range(64)]
    for episode in evidence['episodes']:
        sample = next(c['request'] for c in episode['calls'] if c['stage'] == 'feedback')
        request = copy.deepcopy(sample)
        payload = json.loads(request['messages'][1]['content'])
        payload['before']['frames'] = [dense]
        payload['observation']['frames'] = [dense] * 8
        request['messages'][1]['content'] = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        stress.append({'arm': episode['arm'], 'returned_frames': 8, 'pattern': 'dense_hex', **count(tokenizer, request)})
    examples = {
        'control': {'action': {'action_id': 6, 'action_data': {'x': 63, 'y': 63}}},
        'target': {'action': {'action_id': 6, 'action_data': {'x': 63, 'y': 63}},
                   'target': {'kind': 'box', 'box': [0, 0, 63, 63]}},
        'prediction': {'prediction': 'no_change'},
        'feedback': {'assessment': 'contradicted', 'changed_frames': list(range(8))},
    }
    output_rows = []
    for stage, response in examples.items():
        for serialization, indent in (('compact', None), ('pretty', 2)):
            body = json.dumps(response, indent=indent, separators=(',', ':') if indent is None else None)
            used = len(tokenizer.encode(body, add_special_tokens=False))
            output_rows.append({'stage': stage, 'serialization': serialization,
                                'tokens_plus_end': used + 1, 'cap': 128, 'fits': used + 1 <= 128})
    report = {'scope': 'pinned_tokenizer_cpu_audit_no_model_calls', 'versions': versions,
              'tokenizer_manifest_sha256': hashlib.sha256((ROOT / 'certification/phase4_integrated_v2/tokenizer_manifest.json').read_bytes()).hexdigest(),
              'source_record_sha256': hashlib.sha256(Path(record).read_bytes()).hexdigest(),
              'exact_requests': rows, 'feedback_frame_stress': stress, 'bounded_response_examples': output_rows,
              'limits': {'context': 65536, 'prompt_per_call': 60000, 'request_bytes': 196608,
                         'completion_per_call': 128, 'calls': 12, 'generated_total': 1536},
              'model_calls': 0, 'gpu_runs': 0,
              'caveat': 'Stress copies the retained initial frame or a dense hexadecimal pattern; actual requests can tokenize differently. Every live request is re-tokenized and rejected before transport if over limit.'}
    Path(output).write_bytes((json.dumps(report, indent=2) + '\n').encode())
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.record, args.tokenizer, args.output)
    print(json.dumps({'exact_requests': len(result['exact_requests']),
                      'max_prompt_tokens': max(r['prompt_tokens'] for r in result['exact_requests']),
                      'max_admissible_feedback_frames': max(r['returned_frames'] for r in result['feedback_frame_stress'] if r['admissible']),
                      'all_response_examples_fit': all(r['fits'] for r in result['bounded_response_examples'])}))
