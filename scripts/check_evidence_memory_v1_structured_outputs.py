"""CPU-only, offline check that the verified runtime's structured-output path accepts and enforces Track 2's response
schemas (no model, no GPU, no network).

Two steps, in two interpreters:
  python scripts/check_evidence_memory_v1_structured_outputs.py dump --out SCHEMAS.json
      (any interpreter that imports this repository) writes the request schemas exactly as stage1 builds them, plus a
      Track 4 control schema that the verified runtime has already decoded live, and the test answers with the
      scorer's verdict on each (readers.validate_response, the protocol's validity rule);
  <python with vllm==0.19.0> scripts/check_evidence_memory_v1_structured_outputs.py check --schemas SCHEMAS.json \
      --tokenizer <pinned tokenizer dir> --out RECEIPT.json
      runs vLLM's own request validation under the server's default structured-output configuration (backend
      `auto`, as in the verified argv), records the backend it selects, and tests whether that backend's compiled
      grammar accepts valid answers and rejects invalid ones.

A rejected schema means every request using it is refused by the server: the session would stop at its first such
call as a transport failure.

Receipt r2 (protocol v2 frozen, section 2). The recall decoding schema no longer carries `uniqueItems`, which r1 found
refused. The decoder is therefore expected to ADMIT two answers the protocol counts invalid (duplicate values, and
"no_evidence" with another value); the scorer rejects both, so they are retained, counted invalid and never correct.
The receipt passes only if both Track 2 schemas are accepted, the decoder admits and rejects exactly as expected,
every valid answer passes decoder and scorer, and the scorer rejects every invalid answer the decoder admits.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


CANDIDATES = [{'action_id': 1, 'action_data': {'x': 3}}, {'action_id': 2, 'action_data': {}}]


def cases(values):
    """{schema: [(label, answer, decoder admits it, the protocol counts it valid)]}. Since r2 the decoder admits
    duplicate values and "no_evidence" with another value; the scorer rejects both. None: no Track 2 scorer."""
    v = values
    return {
        'recall': [('valid single', {'values': [v[0]]}, True, True),
                   ('valid two', {'values': [v[0], v[1]]}, True, True),
                   ('valid no_evidence alone', {'values': ['no_evidence']}, True, True),
                   ('duplicate', {'values': [v[0], v[0]]}, True, False),
                   ('no_evidence with another value', {'values': ['no_evidence', v[0]]}, True, False),
                   ('empty list', {'values': []}, False, False),
                   ('not in enum', {'values': ['zzz-not-a-value']}, False, False),
                   ('extra key', {'values': [v[0]], 'x': 1}, False, False),
                   ('missing values', {}, False, False)],
        'decision': [('valid', {'choice': CANDIDATES[0]}, True, True),
                     ('valid empty data', {'choice': CANDIDATES[1]}, True, True),
                     ('string in data', {'choice': {'action_id': 1, 'action_data': {'x': 'a'}}}, False, False),
                     ('float id', {'choice': {'action_id': 1.5, 'action_data': {}}}, False, False),
                     ('missing data', {'choice': {'action_id': 1}}, False, False)],
        'control_flat_string_enum': [('valid', {'answer': 'supported'}, True, None),
                                     ('not in enum', {'answer': 'x'}, False, None)],
    }


def dump(out):
    sys.path.insert(0, str(ROOT))
    from research.evidence_memory_v1 import readers as RD, stage1 as S
    value = {'recall': S.response_schema('recall'), 'decision': S.response_schema('decision'),
             'recall_values': list(S.RECALL_VALUES),
             'control_flat_string_enum': {'type': 'object', 'properties': {'answer': {
                 'type': 'string', 'enum': ['supported', 'contradicted', 'not_established']}},
                 'required': ['answer'], 'additionalProperties': False}, 'cases': {}}
    questions = {'recall': {'kind': 'recall'}, 'decision': {'kind': 'decision', 'candidates': CANDIDATES}}
    for name, rows in cases(value['recall_values']).items():
        value['cases'][name] = []
        for label, answer, decoder, valid in rows:
            scorer = None
            if name in questions:
                try:
                    RD.validate_response(json.dumps(answer, separators=(',', ':')), questions[name])
                    scorer = True
                except RD.ResponseError:
                    scorer = False
            value['cases'][name].append({'label': label, 'answer': answer, 'decoder_expected': decoder,
                                         'answer_valid': valid, 'scorer_valid': scorer})
    Path(out).write_text(json.dumps(value, indent=1) + '\n', encoding='utf-8')
    print('schemas written:', out)


def check(schemas_path, tokenizer_dir, out):
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    import importlib.metadata as md
    from transformers import AutoTokenizer
    from vllm.config import StructuredOutputsConfig
    from vllm.sampling_params import SamplingParams, StructuredOutputsParams
    data = json.loads(Path(schemas_path).read_text(encoding='utf-8'))
    tok = AutoTokenizer.from_pretrained(tokenizer_dir)
    config = StructuredOutputsConfig()
    receipt = {'schema': 'evidence_memory_v1_structured_outputs_check_v2', 'gpu_used': False, 'model_calls': 0,
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
        if not all(matcher.accept_token(t) for t in tok.encode(text, add_special_tokens=False)):
            return False
        # a complete answer: the grammar must also accept a stop token there and terminate
        return any(matcher.accept_token(t) for t in matcher.stop_token_ids[:1]) and matcher.is_terminated()

    for name in ('recall', 'decision', 'control_flat_string_enum'):
        params = SamplingParams(max_tokens=64, structured_outputs=StructuredOutputsParams(json=data[name]))
        entry = {'request_schema': data[name], 'request_schema_sha256': __import__('hashlib').sha256(
            json.dumps(data[name], sort_keys=True).encode()).hexdigest()}
        try:
            params._validate_structured_outputs(config, tok)
            entry.update(validated=True, backend=params.structured_outputs._backend)
        except Exception as exc:
            entry.update(validated=False, backend=None, rejection=f'{type(exc).__name__}: {str(exc)[:300]}')
        if entry['validated']:
            entry['enforcement'] = {}
            for row in data['cases'][name]:
                got = accepts(entry['backend'], data[name], json.dumps(row['answer'], separators=(',', ':')))
                if row['answer_valid'] is None:
                    outcome = 'control (no Track 2 scorer)'
                elif not got:
                    outcome = 'rejected by the decoder'
                elif row['scorer_valid']:
                    outcome = 'valid: admitted by the decoder and the scorer'
                else:
                    outcome = 'admitted by the decoder, rejected by the scorer: retained, counted invalid, never correct'
                entry['enforcement'][row['label']] = {
                    'answer': row['answer'], 'decoder_expected': row['decoder_expected'], 'decoder_accepted': got,
                    'decoder_as_expected': got == row['decoder_expected'], 'answer_valid': row['answer_valid'],
                    'scorer_valid': row['scorer_valid'],
                    'scorer_as_expected': row['answer_valid'] is None or row['scorer_valid'] == row['answer_valid'],
                    'outcome': outcome}
            rows = entry['enforcement'].values()
            entry['enforces_as_expected'] = all(r['decoder_as_expected'] and r['scorer_as_expected'] for r in rows)
        receipt['schemas'][name] = entry
    track2 = [receipt['schemas'][n] for n in ('recall', 'decision')]
    rows = [r for e in track2 for r in (e.get('enforcement') or {}).values()]
    receipt['all_track2_schemas_accepted'] = all(e['validated'] for e in track2)
    receipt['decoder_and_scorer_as_expected'] = all(e.get('enforces_as_expected') is True
                                                    for e in receipt['schemas'].values())
    receipt['every_valid_answer_admitted_and_scored_valid'] = bool(rows) and all(
        r['decoder_accepted'] and r['scorer_valid'] for r in rows if r['answer_valid'])
    receipt['scorer_rejects_every_invalid_answer_the_decoder_admits'] = bool(rows) and all(
        r['scorer_valid'] is False for r in rows if r['decoder_accepted'] and not r['answer_valid'])
    receipt['decoder_admitted_invalid_answers'] = sorted(
        f"{n}: {label}" for n in ('recall', 'decision')
        for label, r in (receipt['schemas'][n].get('enforcement') or {}).items()
        if r['decoder_accepted'] and not r['answer_valid'])
    receipt['passed'] = (receipt['all_track2_schemas_accepted'] and receipt['decoder_and_scorer_as_expected']
                         and receipt['every_valid_answer_admitted_and_scored_valid']
                         and receipt['scorer_rejects_every_invalid_answer_the_decoder_admits'])
    Path(out).write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({**{n: {k: e.get(k) for k in ('validated', 'backend', 'rejection', 'enforces_as_expected')}
                         for n, e in receipt['schemas'].items()},
                      **{k: receipt[k] for k in ('all_track2_schemas_accepted', 'decoder_admitted_invalid_answers',
                                                 'scorer_rejects_every_invalid_answer_the_decoder_admits', 'passed')}},
                     indent=1))


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
