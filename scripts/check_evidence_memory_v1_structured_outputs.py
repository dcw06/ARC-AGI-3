"""CPU-only, offline check that the verified runtime's structured-output path accepts and enforces Track 2's response
schemas (no model, no GPU, no network).

Two steps, in two interpreters:
  python scripts/check_evidence_memory_v1_structured_outputs.py dump --out SCHEMAS.json
      (any interpreter that imports this repository) writes the request schemas exactly as stage1 builds them, plus a
      Track 4 control schema that the verified runtime has already decoded live;
  <python with vllm==0.19.0> scripts/check_evidence_memory_v1_structured_outputs.py check --schemas SCHEMAS.json \
      --tokenizer <pinned tokenizer dir> --out RECEIPT.json
      runs vLLM's own request validation under the server's default structured-output configuration (backend
      `auto`, as in the verified argv), records the backend it selects, and tests whether that backend's compiled
      grammar accepts valid answers and rejects invalid ones.

A rejected schema means every request using it is refused by the server: the session would stop at its first such
call as a transport failure.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def dump(out):
    sys.path.insert(0, str(ROOT))
    from research.evidence_memory_v1 import stage1 as S
    value = {'recall': S.response_schema('recall'), 'decision': S.response_schema('decision'),
             'recall_values': list(S.RECALL_VALUES),
             'control_flat_string_enum': {'type': 'object', 'properties': {'answer': {
                 'type': 'string', 'enum': ['supported', 'contradicted', 'not_established']}},
                 'required': ['answer'], 'additionalProperties': False}}
    Path(out).write_text(json.dumps(value, indent=1) + '\n', encoding='utf-8')
    print('schemas written:', out)


def cases(values):
    v = values
    return {
        'recall': [('valid single', {'values': [v[0]]}, True), ('valid two', {'values': [v[0], v[1]]}, True),
                   ('duplicate', {'values': [v[0], v[0]]}, False), ('empty list', {'values': []}, False),
                   ('not in enum', {'values': ['zzz-not-a-value']}, False),
                   ('extra key', {'values': [v[0]], 'x': 1}, False)],
        'decision': [('valid', {'choice': {'action_id': 1, 'action_data': {'x': 3}}}, True),
                     ('valid empty data', {'choice': {'action_id': 2, 'action_data': {}}}, True),
                     ('string in data', {'choice': {'action_id': 1, 'action_data': {'x': 'a'}}}, False),
                     ('float id', {'choice': {'action_id': 1.5, 'action_data': {}}}, False),
                     ('missing data', {'choice': {'action_id': 1}}, False)],
        'control_flat_string_enum': [('valid', {'answer': 'supported'}, True), ('not in enum', {'answer': 'x'}, False)],
    }


def check(schemas_path, tokenizer_dir, out):
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    import importlib.metadata as md
    from transformers import AutoTokenizer
    from vllm.config import StructuredOutputsConfig
    from vllm.sampling_params import SamplingParams, StructuredOutputsParams
    data = json.loads(Path(schemas_path).read_text(encoding='utf-8'))
    tok = AutoTokenizer.from_pretrained(tokenizer_dir)
    config = StructuredOutputsConfig()
    receipt = {'schema': 'evidence_memory_v1_structured_outputs_check_v1', 'gpu_used': False, 'model_calls': 0,
               'versions': {p: md.version(p) for p in ('vllm', 'xgrammar', 'llguidance', 'transformers')},
               'configured_backend': config.backend, 'schemas': {}}

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
        compiled = xgr.GrammarCompiler(xgr.TokenizerInfo.from_huggingface(tok)).compile_json_schema(json.dumps(schema))
        matcher = xgr.GrammarMatcher(compiled)
        return all(matcher.accept_token(t) for t in tok.encode(text, add_special_tokens=False))

    for name, rows in cases(data['recall_values']).items():
        params = SamplingParams(max_tokens=64, structured_outputs=StructuredOutputsParams(json=data[name]))
        entry = {'request_schema_sha256': __import__('hashlib').sha256(
            json.dumps(data[name], sort_keys=True).encode()).hexdigest()}
        try:
            params._validate_structured_outputs(config, tok)
            entry.update(validated=True, backend=params.structured_outputs._backend)
        except Exception as exc:
            entry.update(validated=False, backend=None, rejection=f'{type(exc).__name__}: {str(exc)[:300]}')
        if entry['validated']:
            entry['enforcement'] = {}
            for label, value, expected in rows:
                got = accepts(entry['backend'], data[name], json.dumps(value, separators=(',', ':')))
                entry['enforcement'][label] = {'expected': expected, 'accepted': got, 'as_expected': got == expected}
            entry['enforces_as_expected'] = all(r['as_expected'] for r in entry['enforcement'].values())
        receipt['schemas'][name] = entry
    receipt['all_track2_schemas_accepted'] = all(receipt['schemas'][n]['validated'] for n in ('recall', 'decision'))
    Path(out).write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({n: {k: e.get(k) for k in ('validated', 'backend', 'rejection', 'enforces_as_expected')}
                      for n, e in receipt['schemas'].items()}, indent=1))


def main():
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


if __name__ == '__main__':
    main()
