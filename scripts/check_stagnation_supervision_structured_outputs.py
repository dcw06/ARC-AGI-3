"""CPU-only, offline check that the verified runtime's structured-output path accepts and enforces Track 3's policy
response schemas (no model, no GPU, no network). Adapted from Track 1's check (lesson from Tracks 1 and 2).

Two steps, in two interpreters:
  python scripts/check_stagnation_supervision_structured_outputs.py dump --out SCHEMAS.json
      (any interpreter that imports this repository) writes the policy request schemas exactly as the frozen
      contract builds them (closed_loop/contract.policy_request -> action_contract.response_format) for the four
      games' initial legal-action sets and the startup canary, plus test answers with the study's own verdict;
  <python with vllm==0.19.0> scripts/check_stagnation_supervision_structured_outputs.py check --schemas SCHEMAS.json \
      --tokenizer <pinned tokenizer dir> --out RECEIPT.json
      runs vLLM's own request validation under the server's default structured-output configuration (backend
      `auto`, as in the verified argv), records the backend it selects, and tests whether that backend's compiled
      grammar admits the valid answers and rejects the invalid ones.

A rejected schema means every request using it is refused by the server. Reflection requests carry no response
schema (their output is parsed and validated by intervention.parse), so they are not part of this check.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def cases():
    move = {'action_id': 1, 'action_data': {}}
    return [
        ('simple action', {'action': move}),
        ('ACTION6 at the corner', {'action': {'action_id': 6, 'action_data': {'x': 63, 'y': 0}}}),
        ('ACTION6 at the origin', {'action': {'action_id': 6, 'action_data': {'x': 0, 'y': 0}}}),
        ('ACTION7', {'action': {'action_id': 7, 'action_data': {}}}),
        ('reset action 0', {'action': {'action_id': 0, 'action_data': {}}}),
        ('ACTION6 x out of range', {'action': {'action_id': 6, 'action_data': {'x': 64, 'y': 0}}}),
        ('ACTION6 missing y', {'action': {'action_id': 6, 'action_data': {'x': 1}}}),
        ('simple action with data', {'action': {'action_id': 1, 'action_data': {'x': 1}}}),
        ('extra key', {'action': move, 'note': 'x'}),
        ('boolean id', {'action': {'action_id': True, 'action_data': {}}}),
    ]


def dump(out):
    sys.path.insert(0, str(ROOT))
    from certification.phase4_transient_v2.action_contract import response_format, validate_action
    from research.stagnation_supervision_v1.closed_loop import model_service
    protocol = json.loads((ROOT / 'research/stagnation_supervision_v1/closed_loop/protocol.json').read_bytes())
    legal_sets = {c['game_id'].split('-', 1)[0]: c['initial_available_actions'] for c in protocol['cases']}
    legal_sets['canary'] = [6]
    canary = model_service.canary_request()['response_format']
    if canary != response_format([6]):
        raise ValueError('canary schema differs from the contract')
    schemas, rows = {}, []
    for name, legal in legal_sets.items():
        schemas[name] = response_format(legal)['json_schema']['schema']
        for label, answer in cases():
            try:
                validate_action(json.dumps(answer, separators=(',', ':')), legal)
                valid = True
            except (ValueError, KeyError, TypeError):
                valid = False
            rows.append({'schema': name, 'label': label, 'answer': answer, 'study_valid': valid})
    Path(out).write_text(json.dumps({'schemas': schemas, 'legal_sets': legal_sets, 'cases': rows}, indent=1) + '\n',
                         encoding='utf-8')
    print('schemas written:', out, len(schemas), 'schemas,', len(rows), 'cases')


def check(schemas_path, tokenizer_dir, out):
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    import importlib.metadata as md
    from transformers import AutoTokenizer
    from vllm.config import StructuredOutputsConfig
    from vllm.sampling_params import SamplingParams, StructuredOutputsParams
    data = json.loads(Path(schemas_path).read_text(encoding='utf-8'))
    tok = AutoTokenizer.from_pretrained(tokenizer_dir)
    config = StructuredOutputsConfig()
    receipt = {'schema': 'stagnation_supervision_structured_outputs_check_v1', 'gpu_used': False, 'model_calls': 0,
               'versions': {p: md.version(p) for p in ('vllm', 'xgrammar', 'llguidance', 'transformers')},
               'configured_backend': config.backend,
               'disable_any_whitespace': getattr(config, 'disable_any_whitespace', None),
               'schemas_input_sha256': hashlib.sha256(Path(schemas_path).read_bytes()).hexdigest(),
               'legal_sets': data['legal_sets'], 'schemas': {}}

    def accepts(backend, schema, text):
        if backend == 'guidance':
            import llguidance
            import llguidance.hf
            from vllm.v1.structured_output.backend_guidance import serialize_guidance_grammar
            from vllm.v1.structured_output.request import StructuredOutputOptions
            matcher = llguidance.LLMatcher(llguidance.hf.from_tokenizer(tok),
                                           serialize_guidance_grammar(StructuredOutputOptions.JSON, json.dumps(schema)))
            return bool(matcher.consume_tokens(tok.encode(text, add_special_tokens=False))) \
                and not matcher.is_error() and matcher.is_accepting()
        import xgrammar as xgr
        compiled = xgr.GrammarCompiler(xgr.TokenizerInfo.from_huggingface(tok)).compile_json_schema(
            json.dumps(schema), any_whitespace=not getattr(config, 'disable_any_whitespace', False))
        matcher = xgr.GrammarMatcher(compiled)
        if not all(matcher.accept_token(t) for t in tok.encode(text, add_special_tokens=False)):
            return False
        return any(matcher.accept_token(t) for t in matcher.stop_token_ids[:1]) and matcher.is_terminated()

    for name, schema in data['schemas'].items():
        params = SamplingParams(max_tokens=128, structured_outputs=StructuredOutputsParams(json=schema))
        entry = {'request_schema_sha256': hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()}
        try:
            params._validate_structured_outputs(config, tok)
            entry.update(validated=True, backend=params.structured_outputs._backend)
        except Exception as exc:
            entry.update(validated=False, backend=None, rejection=f'{type(exc).__name__}: {str(exc)[:300]}')
        receipt['schemas'][name] = entry
    results = []
    for row in data['cases']:
        entry = receipt['schemas'][row['schema']]
        if not entry['validated']:
            continue
        got = accepts(entry['backend'], data['schemas'][row['schema']], json.dumps(row['answer'], separators=(',', ':')))
        results.append({'schema': row['schema'], 'label': row['label'], 'decoder_admits': got,
                        'study_valid': row['study_valid'], 'agree': got == row['study_valid']})
    receipt['cases'] = results
    receipt['all_schemas_accepted'] = all(e['validated'] for e in receipt['schemas'].values())
    receipt['backends'] = sorted({str(e.get('backend')) for e in receipt['schemas'].values()})
    receipt['decoder_admits_a_study_invalid_answer'] = sorted(
        {f"{r['schema']}: {r['label']}" for r in results if r['decoder_admits'] and not r['study_valid']})
    receipt['decoder_rejects_a_study_valid_answer'] = sorted(
        {f"{r['schema']}: {r['label']}" for r in results if r['study_valid'] and not r['decoder_admits']})
    receipt['passed'] = receipt['all_schemas_accepted'] and not receipt['decoder_rejects_a_study_valid_answer']
    Path(out).write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ('versions', 'configured_backend', 'all_schemas_accepted', 'backends',
                                             'decoder_admits_a_study_invalid_answer',
                                             'decoder_rejects_a_study_valid_answer', 'passed')}, indent=1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    d = sub.add_parser('dump')
    d.add_argument('--out', required=True)
    c = sub.add_parser('check')
    c.add_argument('--schemas', required=True)
    c.add_argument('--tokenizer', required=True)
    c.add_argument('--out', required=True)
    args = parser.parse_args()
    if args.command == 'dump':
        dump(args.out)
    else:
        check(args.schemas, args.tokenizer, args.out)
