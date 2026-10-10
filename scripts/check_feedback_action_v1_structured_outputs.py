"""CPU-only, offline check that the verified runtime's structured-output path accepts and enforces Track 1's response
schemas (no model, no GPU, no network).

Two steps, in two interpreters:
  python scripts/check_feedback_action_v1_structured_outputs.py dump --out SCHEMAS.json
      (any interpreter that imports this repository) writes the request schemas exactly as the adapter and the owner
      gate build them: the baseline action schema and the candidate schema under both free-text options (gate A:
      `current`, committed; `ascii_only`, recommended), for the legal-action sets of the three games and the canary,
      plus test answers with the study's own validity verdict on each;
  <python with vllm==0.19.0> scripts/check_feedback_action_v1_structured_outputs.py check --schemas SCHEMAS.json \
      --tokenizer <pinned tokenizer dir> --out RECEIPT.json
      runs vLLM's own request validation under the server's default structured-output configuration (backend
      `auto`, as in the verified argv), records the backend it selects, and tests whether that backend's compiled
      grammar admits the valid answers and rejects the invalid ones.

A rejected schema means every request using it is refused by the server. The token audit
(research/feedback_action_v1/token_audit.json) compiled these schemas with xgrammar directly; this check adds vLLM's
backend selection, which falls back from xgrammar to guidance for schemas xgrammar does not support.

Receipt r1 (prepared before the owner decisions) and r2 (after them: free_text_format = ascii_only, recorded in
owner_gates.json) cover both options; r2 also records the effective option and the owner-gate record's hash.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LEGAL_SETS = {'canary': [6], 's5i5_coordinate_only': [6], 'ls20_directional': [1, 2, 3, 4],
              'sk48_mixed': [1, 2, 3, 4, 6, 7]}
ASCII_TEXT = 'Clicking the top-left cell toggles the region (T3); a different result would mean the toggle is local.'


def block(hypothesis=ASCII_TEXT, if_different=ASCII_TEXT, supporting=None, region=None, ref='T3'):
    return {'hypothesis': hypothesis, 'status': 'new',
            'supporting': supporting if supporting is not None else [{'ref': ref, 'claim': 'final_frame_differs'}],
            'conflicting': [], 'prediction': {'visual_effect': 'final_frame_differs', 'level_completed': False,
                                              'changed_region_xyxy': region},
            'if_different': if_different}


def cases():
    """(label, answer, study-valid under current, study-valid under ascii_only). The decoder is expected to admit an
    answer exactly when the study counts it valid, except where noted in `decoder_note`."""
    move = {'action_id': 1, 'action_data': {}}
    click = {'action_id': 6, 'action_data': {'x': 63, 'y': 0}}
    return {
        'baseline': [
            ('simple action', {'action': move}),
            ('ACTION6 at the corner', {'action': click}),
            ('illegal action id 5', {'action': {'action_id': 5, 'action_data': {}}}),
            ('ACTION6 x out of range', {'action': {'action_id': 6, 'action_data': {'x': 64, 'y': 0}}}),
            ('simple action with data', {'action': {'action_id': 1, 'action_data': {'x': 1}}}),
            ('extra key', {'action': move, 'note': 'x'}),
        ],
        'candidate': [
            ('ASCII text, one citation', {'hypothesis_test': block(), 'action': move}),
            ('region of four cells', {'hypothesis_test': block(region=[0, 0, 63, 63]), 'action': click}),
            ('text at 240 ASCII characters', {'hypothesis_test': block(hypothesis='a' * 240), 'action': move}),
            ('text at 241 characters', {'hypothesis_test': block(hypothesis='a' * 241), 'action': move}),
            ('non-ASCII text (CJK)', {'hypothesis_test': block(hypothesis='点击左上角会切换区域'), 'action': move}),
            ('non-ASCII text (accented Latin)', {'hypothesis_test': block(if_different='naïve résumé'), 'action': move}),
            ('four citations', {'hypothesis_test': block(supporting=[{'ref': f'T{i}', 'claim': 'indeterminate'}
                                                                     for i in range(4)]), 'action': move}),
            ('five citations', {'hypothesis_test': block(supporting=[{'ref': f'T{i}', 'claim': 'indeterminate'}
                                                                     for i in range(5)]), 'action': move}),
            ('bad citation ref', {'hypothesis_test': block(ref='X3'), 'action': move}),
            ('region of three cells', {'hypothesis_test': block(region=[0, 0, 63]), 'action': move}),
            ('missing hypothesis_test', {'action': move}),
            ('illegal action id 5', {'hypothesis_test': block(), 'action': {'action_id': 5, 'action_data': {}}}),
        ],
    }


def study_valid(name, answer, legal, ascii_only):
    """The study's own verdict: the action contract, then (candidate) the procedure block's schema and gate A."""
    sys.path.insert(0, str(ROOT))
    from certification.phase4_transient_v2.action_contract import validate_action
    from research.feedback_action_v1 import adapter as AD
    from research.feedback_action_v1.live import owner_gates as G
    text = json.dumps(answer, separators=(',', ':'))
    if name == 'baseline':
        try:
            validate_action(text, legal)
            return True
        except (ValueError, KeyError, TypeError):
            return False
    if set(answer) != {'hypothesis_test', 'action'}:
        return False
    try:
        validate_action(json.dumps({'action': answer['action']}), legal)
    except (ValueError, KeyError, TypeError):
        return False
    import jsonschema
    try:
        jsonschema.validate(answer['hypothesis_test'], AD.HYPOTHESIS_TEST)
    except jsonschema.ValidationError:
        return False
    if ascii_only:
        import re
        if any(not re.fullmatch(G.ASCII_PATTERN, answer['hypothesis_test'][f]) for f in G.FREE_TEXT):
            return False
    return True


def dump(out):
    sys.path.insert(0, str(ROOT))
    from certification.phase4_transient_v2.action_contract import response_format
    from research.feedback_action_v1.live import owner_gates as G
    gated = {'free_text_format': {'decision': 'ascii_only', 'committed': 'current'},
             'f5_early_abort': {'decision': None, 'committed': 'running_rate_from_first_dispatch'}}
    schemas, rows = {}, []
    for game, legal in LEGAL_SETS.items():
        schemas[f'baseline/{game}'] = response_format(legal)['json_schema']['schema']
        if game != 'canary':
            schemas[f'candidate_current/{game}'] = G.candidate_response_format(legal, None)['json_schema']['schema']
            schemas[f'candidate_ascii_only/{game}'] = G.candidate_response_format(legal, gated)['json_schema']['schema']
    committed = {**gated, 'free_text_format': {'decision': None, 'committed': 'current'}}
    for game, legal in LEGAL_SETS.items():  # the two options as the gate builds them, whatever is recorded
        if game != 'canary':
            schemas[f'candidate_current/{game}'] = G.candidate_response_format(legal, committed)['json_schema']['schema']
    effective = G.decision('free_text_format')
    assert all(G.candidate_response_format(legal)['json_schema']['schema'] == schemas[f'candidate_{effective}/{g}']
               for g, legal in LEGAL_SETS.items() if g != 'canary'), 'the effective schema is one of the two checked'
    for name, answers in cases().items():
        for label, answer in answers:
            for game, legal in LEGAL_SETS.items():
                if game == 'canary' and name == 'candidate':
                    continue
                options = ['baseline'] if name == 'baseline' else ['candidate_current', 'candidate_ascii_only']
                for option in options:
                    rows.append({'schema': f'{option}/{game}', 'label': label, 'answer': answer,
                                 'study_valid': study_valid(name, answer, legal, option == 'candidate_ascii_only')})
    Path(out).write_text(json.dumps({'schemas': schemas, 'cases': rows, 'effective_free_text_format': effective,
                                     'owner_gates_sha256': hashlib.sha256(G.GATES.read_bytes()).hexdigest()},
                                    indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
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
    receipt = {'schema': 'feedback_action_v1_structured_outputs_check_v2', 'gpu_used': False, 'model_calls': 0,
               'versions': {p: md.version(p) for p in ('vllm', 'xgrammar', 'llguidance', 'transformers')},
               'configured_backend': config.backend,
               'disable_any_whitespace': getattr(config, 'disable_any_whitespace', None),
               'effective_free_text_format': data.get('effective_free_text_format'),
               'owner_gates_sha256': data.get('owner_gates_sha256'), 'schemas': {}}

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
        params = SamplingParams(max_tokens=640, structured_outputs=StructuredOutputsParams(json=schema))
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
        got = accepts(entry['backend'], data['schemas'][row['schema']],
                      json.dumps(row['answer'], separators=(',', ':'), ensure_ascii=False))
        results.append({'schema': row['schema'], 'label': row['label'], 'decoder_admits': got,
                        'study_valid': row['study_valid'], 'agree': got == row['study_valid']})
    receipt['cases'] = results
    receipt['all_schemas_accepted'] = all(e['validated'] for e in receipt['schemas'].values())
    receipt['backends'] = sorted({str(e.get('backend')) for e in receipt['schemas'].values()})
    receipt['decoder_admits_a_study_invalid_answer'] = sorted(
        {f"{r['schema'].split('/')[0]}: {r['label']}" for r in results if r['decoder_admits'] and not r['study_valid']})
    receipt['decoder_rejects_a_study_valid_answer'] = sorted(
        {f"{r['schema'].split('/')[0]}: {r['label']}" for r in results if r['study_valid'] and not r['decoder_admits']})
    receipt['passed'] = (receipt['all_schemas_accepted'] and not receipt['decoder_rejects_a_study_valid_answer'])
    Path(out).write_text(json.dumps(receipt, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ('versions', 'configured_backend', 'all_schemas_accepted', 'backends',
                                             'decoder_admits_a_study_invalid_answer',
                                             'decoder_rejects_a_study_valid_answer', 'passed')}, indent=1,
                     ensure_ascii=False))
    print(json.dumps({n: {k: e.get(k) for k in ('validated', 'backend', 'rejection')}
                      for n, e in receipt['schemas'].items()}, indent=1))


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
