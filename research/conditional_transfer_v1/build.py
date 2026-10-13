"""Offline package construction and byte-for-byte checks. No submission/launch API."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path

from research.evidence_memory_v1 import tokens
from . import (schema as S, fixtures as FX, writer as W, independent_keys as IK, score as SC,
               render as R, selection as SE, attribution as A, shortcuts as SH, protocol as P, replay as RP,
               dependencies as D)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'reports/conditional_transfer_v1/review_package'


def _json(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()


def _lines(rows):
    return gzip.compress((''.join(S.compact(r) + '\n' for r in rows)).encode(), mtime=0)


def _mean(rows, field):
    return sum(r[field] for r in rows) / len(rows) if rows else None


def summarize(rows):
    result = {}
    for ceiling in S.CEILINGS:
        for arm in S.ARMS:
            subset = [r for r in rows if r['ceiling'] == ceiling and r['arm'] == arm]
            transfers = [r for r in subset if r['task'] == 'transfer']
            risk = [r for r in transfers if r['full_source']['answer'] != 'supported_local']
            supported = [r for r in transfers if r['full_source']['answer'] == 'supported_local']
            counters = [r for r in subset if r['task'] in ('contradiction', 'update') and
                        r['full_source']['answer'] in ('present', 'narrow', 'retire')]
            claims = [r for r in transfers if json.loads(r['response'])['answer'] == 'supported_local']
            result[f'{ceiling}/{arm}'] = {
                'probes': len(subset), 'variants': len(transfers), 'validity': _mean(subset, 'valid'),
                'transfer_category_accuracy': _mean(transfers, 'end_to_end_category_correct'),
                'unsupported_transfer_numerator': sum(json.loads(r['response'])['answer'] == 'supported_local' for r in risk),
                'unsupported_transfer_denominator': len(risk),
                'unsupported_transfer_rate': sum(json.loads(r['response'])['answer'] == 'supported_local' for r in risk)/len(risk),
                'supported_reuse_coverage': sum(json.loads(r['response'])['answer'] == 'supported_local' for r in supported)/len(supported),
                'supported_claim_precision': sum(r['full_source']['answer'] == 'supported_local' for r in claims)/len(claims) if claims else None,
                'contradiction_update_category_accuracy': _mean(counters, 'end_to_end_category_correct'),
                'reference_precision_against_package': _mean(subset, 'reference_precision'),
                'reference_coverage_against_package': _mean(subset, 'reference_coverage'),
                'reference_precision_against_source': _mean(subset, 'source_reference_precision'),
                'reference_coverage_against_source': _mean(subset, 'source_reference_coverage'),
                'writer_category_losses': sum(r['writer_category_loss_or_distortion'] for r in subset),
                'writer_reference_losses': sum(r['writer_reference_loss_or_distortion'] for r in subset),
                'selection_category_losses': sum(r['selection_category_loss_or_distortion'] for r in subset),
                'selection_reference_losses': sum(r['selection_reference_loss_or_distortion'] for r in subset),
                'reader_errors': sum(r['reader_error'] for r in subset),
                'transfer_by_family': {f: _mean([r for r in transfers if r['family'] == f], 'end_to_end_category_correct') for f in FX.FAMILIES},
                'transfer_by_delay': {str(d): _mean([r for r in transfers if r['delay'] == d], 'end_to_end_category_correct') for d in FX.DELAYS}}
    return result


def artifacts(tokenizer=None):
    sources, inputs = D.source_hashes(ROOT), D.input_hashes(ROOT)
    t = tokenizer or tokens.Tokenizer()
    reference = D.verify_tokenizer_reference(t, ROOT, tokens.verify_against_ws3_audit)
    cases, keys, decisions, requests, aliases, costs = FX.generate(), [], [], {}, [], []
    shortcut_rows = defaultdict(list)
    full_answer_counts = defaultdict(Counter)
    update_count, base_faults = 0, 0
    for c in cases:
        RP.validate_case(c)
        facts, store = W.source_facts(c), W.write(c)
        audited = W.audit(c, store)
        if audited['faults']:
            raise ValueError('writer fidelity failure: ' + str(audited['faults']))
        base_faults += len(audited['faults'])
        update_count += len(facts)
        gold = IK.keys(c)
        keys.append({'scenario_id': c['scenario_id'], 'delay': c['delay'], 'keys': gold})
        for task in S.TASKS:
            if SC.judge(facts, c['proposed_rule'], c['target'], task) != gold[task]:
                raise ValueError('independent keys disagree')
            full_answer_counts[task][gold[task]['answer']] += 1
            diagnostic = R.request(c, task, R.raw_items(c))
            result = SC.scripted_reader(diagnostic)
            if not SC.score(result, task, gold[task], R.allowed_ids(diagnostic))['correct']:
                raise ValueError('full-source rendered reader differs from key')
            for name in SH.NAMES:
                out = SH.read(diagnostic, name)
                scored = SC.score(out, task, gold[task], R.allowed_ids(diagnostic))
                shortcut_rows[name].append({'scenario_id': c['scenario_id'], 'delay': c['delay'],
                    'task': task, 'family': c['family'], 'gold': gold[task]['answer'],
                    'answer': json.loads(out)['answer'], **scored})
        for cap in S.CEILINGS:
            for arm in S.ARMS:
                selected = SE.select(c, store, arm, cap, t)
                for task in S.TASKS:
                    request = R.request(c, task, selected['items'], selected['memory'])
                    prompt = t.chat_prompt_tokens(request['messages'])
                    if prompt > cap:
                        raise ValueError('final prompt exceeds cap')
                    out = SC.scripted_reader(request)
                    payload, visible = SC.parse_request(request)
                    package = SC.judge(visible, payload['rule'], payload['target'], task)
                    complete = SC.judge(W.flatten(store), c['proposed_rule'], c['target'], task)
                    result = A.evaluate(gold[task], complete, package, out, task, R.allowed_ids(request))
                    if result['reader_error']:
                        raise ValueError('scripted reader failed to interpret its actual package')
                    source_score = SC.score(out, task, gold[task], R.allowed_ids(request))
                    result.update(source_reference_precision=source_score['reference_precision'],
                                  source_reference_coverage=source_score['reference_coverage'])
                    key_completion = len(t.encode(S.compact(SC.canonical(gold[task]))))
                    package_completion = len(t.encode(out))
                    # Upper bound for a useful schema-conforming answer with <=8
                    # distinct resolved IDs. Arbitrarily long malicious strings
                    # remain invalid rather than being silently trimmed.
                    ids = sorted(R.allowed_ids(request), key=lambda x: -len(t.encode(S.compact(x))))[:8]
                    longest = max(len(t.encode(S.compact({'answer': a, 'evidence_ids': ids}))) for a in S.TASKS[task])
                    if max(key_completion, package_completion, longest) > S.OUTPUT_CAP:
                        raise ValueError('required or longest resolved completion exceeds cap')
                    identifier = RP.digest(request)
                    requests.setdefault(identifier, {'request_id': identifier, 'request': request})
                    alias = {'request_id': identifier, 'scenario_id': c['scenario_id'], 'delay': c['delay'],
                             'arm': arm, 'ceiling': cap, 'task': task}
                    aliases.append(alias)
                    costs.append({**alias, 'prompt_tokens': prompt, 'key_completion_tokens': key_completion,
                                  'scripted_completion_tokens': package_completion, 'resolved_completion_bound': longest,
                                  'selected_ids': sorted(R.allowed_ids(request)),
                                  'dropped_items': selected['dropped_items']})
                    decisions.append({**alias, 'family': c['family'], **result})
    # Check metadata never crosses the projection; visible outcomes/rule status
    # are legitimate inputs, unlike evaluator keys/family/group labels.
    forbidden = {'family', 'group', 'split', 'delay', 'evaluator_only', 'declared_category',
                 'keys', 'required_groups', 'eligible_ids', 'full_source', 'scenario_id'}
    def fields(value):
        if isinstance(value, dict):
            return set(value) | set().union(*(fields(v) for v in value.values()), set())
        if isinstance(value, list):
            return set().union(*(fields(v) for v in value), set())
        return set()
    for entry in requests.values():
        if fields(json.loads(entry['request']['messages'][1]['content'])) & forbidden:
            raise ValueError('hidden-key metadata leaked into reader request')
        # "contradiction" is also a declared task name; its presence is required,
        # not a fixture-family disclosure. Family metadata fields are forbidden.
        if any(f in S.compact(entry['request']) for f in FX.FAMILIES if f not in S.TASKS):
            raise ValueError('family label leaked into prompt')
    shortcut_summary = {}
    for name, rows in shortcut_rows.items():
        transfer = [r for r in rows if r['task'] == 'transfer']
        risk = [r for r in transfer if r['gold'] != 'supported_local']
        positive = [r for r in transfer if r['gold'] == 'supported_local']
        shortcut_summary[name] = {'category_accuracy': _mean(rows, 'category_correct'),
            'transfer_accuracy': _mean(transfer, 'category_correct'),
            'transfer_wrong_variants': sum(not r['category_correct'] for r in transfer),
            'unsupported_transfer_rate': sum(r['answer'] == 'supported_local' for r in risk)/len(risk),
            'supported_reuse_coverage': sum(r['answer'] == 'supported_local' for r in positive)/len(positive),
            'reference_precision': _mean(rows, 'reference_precision'),
            'reference_coverage': _mean(rows, 'reference_coverage'),
            'transfer_accuracy_by_family': {f: _mean([r for r in transfer if r['family'] == f], 'category_correct') for f in FX.FAMILIES}}
    strongest = max(SH.NAMES, key=lambda n: shortcut_summary[n]['transfer_accuracy'])
    wrong = {(r['scenario_id'], r['delay']) for r in shortcut_rows[strongest] if r['task'] == 'transfer' and not r['category_correct']}
    summary = {'label': 'CPU scripted construction, not model results', 'clusters': 48, 'variants': len(cases),
               'probes': len(decisions), 'writer_updates': update_count, 'writer_integrity_faults': base_faults,
               'full_source_answer_counts': {k: dict(v) for k, v in full_answer_counts.items()},
               'by_arm': summarize(decisions), 'shortcuts': shortcut_summary,
               'strongest_declared_transfer_shortcut': strongest,
               'strongest_shortcut_wrong_variants': len(wrong),
               'shortcut_resistant_transfer_accuracy': {f'{cap}/{arm}': _mean([r for r in decisions if
                    r['task'] == 'transfer' and r['ceiling'] == cap and r['arm'] == arm and
                    (r['scenario_id'], r['delay']) in wrong], 'end_to_end_category_correct')
                    for cap in S.CEILINGS for arm in S.ARMS}}
    unique = list(requests.values())
    schema_probes = [{'request_id': RP.digest(R.request(cases[0], task, [])),
                      'request': R.request(cases[0], task, [])} for task in S.TASKS]
    schema_probe_keys = [{'request_id': entry['request_id'], 'expected': json.loads(SC.scripted_reader(entry['request']))}
                         for entry in schema_probes]
    audit = {'tokenizer_sha256': tokens.PINNED, 'verified_against_existing_audit': reference['verified'],
             'reference_verification': reference,
             'probes': len(aliases), 'unique_requests': len(unique), 'duplicate_aliases': len(aliases)-len(unique),
             'duplicates_policy': 'execute unique digests once; retain aliases; cluster dependencies',
             'max_prompt_tokens': max(c['prompt_tokens'] for c in costs),
             'max_required_completion_tokens': max(c['key_completion_tokens'] for c in costs),
             'max_resolved_completion_bound': max(c['resolved_completion_bound'] for c in costs),
             'unique_prompt_token_sum': sum(t.chat_prompt_tokens(e['request']['messages']) for e in unique),
             'unique_completion_cap_sum': len(unique)*S.OUTPUT_CAP,
             'prepared_schema_probe_calls': len(schema_probes),
             'schema_probe_prompt_token_sum': sum(t.chat_prompt_tokens(e['request']['messages']) for e in schema_probes),
             'schema_probe_completion_cap_sum': len(schema_probes)*S.OUTPUT_CAP,
             'by_ceiling': {str(cap): {'probes': sum(c['ceiling'] == cap for c in costs),
                  'unique_requests': len({c['request_id'] for c in costs if c['ceiling'] == cap}),
                  'max_prompt_tokens': max(c['prompt_tokens'] for c in costs if c['ceiling'] == cap)} for cap in S.CEILINGS},
             'leakage_forbidden_fields_checked': sorted(forbidden), 'rows': costs}
    if D.source_hashes(ROOT) != sources or D.input_hashes(ROOT) != inputs:
        raise ValueError('source or reference inputs changed during construction')
    files = {'benchmark.json.gz': gzip.compress(S.compact(cases).encode(), mtime=0),
             'independent_keys.json': _json(keys), 'protocol.json': _json(P.specification()),
             'summary.json': _json(summary), 'token_audit.json': _json(audit),
             'requests.jsonl.gz': _lines(unique), 'request_aliases.jsonl.gz': _lines(aliases),
             'schema_probes.jsonl.gz': _lines(schema_probes), 'schema_probe_keys.json': _json(schema_probe_keys),
             'attribution.jsonl.gz': _lines(decisions),
             'shortcuts.jsonl.gz': _lines([{'shortcut': n, **r} for n, rows in shortcut_rows.items() for r in rows]),
             'source_hashes.json': _json(sources), 'input_hashes.json': _json(inputs)}
    files['manifest.json'] = _json({'version': S.VERSION, 'gpu_enabled': False, 'execution_authorized': False,
                                  'sha256': {k: hashlib.sha256(v).hexdigest() for k, v in sorted(files.items())}})
    return files, summary, audit


def build(path=DEFAULT, check=False):
    path = Path(path)
    if check:
        D.verify_bindings(path, ROOT)
    files, summary, audit = artifacts()
    if check:
        failures = [name for name, data in files.items() if not (path/name).is_file() or (path/name).read_bytes() != data]
        extras = {p.name for p in path.iterdir() if p.is_file()} - set(files)
        if failures or extras:
            raise ValueError('package differs: ' + str(failures + sorted(extras)))
    else:
        path.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (path/name).write_bytes(data)
    return {'verified': True, 'check': check, 'clusters': summary['clusters'],
            'variants': summary['variants'], 'probes': summary['probes'],
            'unique_requests': audit['unique_requests'], 'duplicate_aliases': audit['duplicate_aliases']}


def main():
    p = argparse.ArgumentParser(description='CPU-only conditional-transfer review package')
    p.add_argument('--output', type=Path, default=DEFAULT)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    print(S.compact(build(args.output, args.check)))


if __name__ == '__main__':
    main()
