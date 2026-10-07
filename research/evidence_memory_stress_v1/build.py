"""Build reproducible CPU stress evidence and inert model request drafts.

Run with --check to verify all committed outputs in memory without writing.
There is no transport, authorization, reservation, launch or GPU path here.
"""
import argparse
import hashlib
import json
from pathlib import Path

from research.evidence_memory_v1 import fidelity as F, protocol as P, render as R, schema as S
from research.evidence_memory_v1 import tokens as TK, writers as W
from . import fixtures as FX, diagnostics as D

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'reports/evidence_memory_stress_v1'


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def contexts(case, tokenizer):
    # The writer sees transitions only; it cannot consult fixture labels or keys.
    run = W.run_writer(W.Faithful(), {'records': case['records']})
    measure = lambda text: len(tokenizer.encode(text))
    package, contents = P.arm_contents(case, run['memory'], measure)
    full_memory = R.memory_text(run['memory']['entries'])
    index = S.index(case['records'])
    # Original renderings use different hash prefix lengths. Reject collisions.
    prefixes = {}
    for info in index.values():
        prefix = info['state'][:8]
        if prefix in prefixes and prefixes[prefix] != info['state']:
            raise ValueError('ambiguous rendered state prefix')
        prefixes[prefix] = info['state']
    for arm in P.ARMS:
        if measure(contents[arm][0]) > package['budget']:
            raise ValueError('common token ceiling exceeded')
    return run, package, contents, full_memory


def analyze(case, tokenizer):
    run, package, contents, full_memory = contexts(case, tokenizer)
    expected = case['evaluator_only']['expected']
    writer = F.evaluate(case['records'], run['memory'], expected)
    requests, answers, rows = [], [], []
    for n, labeled in enumerate(expected['questions']):
        q = {k: v for k, v in labeled.items() if k != 'expected_answer'}
        truth = case['evaluator_only']['keys'][n]
        independently_derived = ({'values': F.gold(case['records'], q)} if q['kind'] == 'recall'
                                 else D.hypothesis_gold(case['records'], q))
        if truth != independently_derived:
            raise ValueError('construction key disagrees with independent evaluator')
        if D.text_truth(contents[P.REFERENCE][0], q) != truth:
            raise ValueError('full-history rendering lost construction evidence')
        for arm in P.ARMS:
            text, content = contents[arm]
            selected = D.text_truth(text, q)
            if q['kind'] == 'recall' and selected != {'values': P.package_truth(arm, content, q)}:
                raise ValueError('rendered reader disagrees with existing package oracle')
            full_store = D.text_truth(full_memory if arm == 'memory' else contents[P.REFERENCE][0], q)
            output = json.dumps(selected)
            scored = D.attribution(truth, full_store, selected, output, q, F.faulty(writer) if arm == 'memory' else False)
            kept_steps = ({ref['action_index'] for e in content for ref in e['evidence'] + e['counterevidence']}
                          if arm == 'memory' else {r['identity']['action_index'] for r in content})
            relevant = case['evaluator_only']['relevant_steps_by_question'][n]
            row = {'case': case['id'], 'family': case['family'], 'delay': case['delay'],
                   'question_index': n, 'kind': q['kind'], 'arm': arm,
                   'truth': truth, 'full_store_truth': full_store, 'package_truth': selected,
                   'budget_tokens': package['budget'], 'evidence_tokens': len(tokenizer.encode(text)),
                   'missing_relevant_steps': sorted(set(relevant) - kept_steps), **scored}
            rows.append(row)
            request = D.request(text, q)
            request_id = f'request-{len(requests):04d}'  # global opaque ID assigned below
            requests.append({'request_id': request_id, 'request': request,
                             'prompt_tokens': tokenizer.chat_prompt_tokens(request['messages'])})
            answers.append({'request_id': request_id, 'case': case['id'], 'family': case['family'],
                            'arm': arm, 'question': q, 'truth': truth, 'package_truth': selected})
    # Negative writer control verifies that the independent fidelity checker detects fabrication.
    bad = W.run_writer(W.Overclaiming(), {'records': case['records']})
    bad_report = F.evaluate(case['records'], bad['memory'], expected)
    return {'case': case['id'], 'writer_fidelity': writer, 'writer_log': run['log'],
            'negative_writer_fault_ids': sorted(F.faulty(bad_report)),
            'budget_tokens': package['budget'],
            'arm_tokens': {a: len(tokenizer.encode(contents[a][0])) for a in P.ARMS},
            'memory_unbounded_tokens': len(tokenizer.encode(full_memory)),
            'memory_dropped_entries': package['memory']['dropped']}, rows, requests, answers


def table(rows, field):
    out = []
    for value in sorted({r[field] for r in rows}):
        for arm in P.ARMS:
            group = [r for r in rows if r[field] == value and r['arm'] == arm]
            out.append({'group': value, 'arm': arm, 'questions': len(group),
                        'correct': sum(r['correct_truth'] for r in group),
                        'store_loss': sum(r['writer_store_loss_or_distortion'] for r in group),
                        'selection_loss': sum(r['selection_loss_or_distortion'] for r in group),
                        'reader_errors': sum(r['reader_error'] for r in group)})
    return out


def report(summary):
    lines = ['# Track 2 evidence preservation stress results', '',
             'Development diagnostics using deterministic writers and scripted readers on synthetic transitions. '
             'These results measure evidence availability and component checks, not model memory or game solving.', '',
             '## Construction and scoring', '',
             f"{summary['cases']} continuous cases cover eight families, two seeded constructions each, and distractor "
             'delays of 0, 8 and 24 transitions. The extra hypothesis-pending family checks that repeated support '
             'remains a hypothesis before the contradiction family supplies a later correction.', '',
             'The existing Track 2 faithful writer, independent fidelity checker, Stage 1 factual scorer, '
             'state-keyed retrieval and renderings are reused unchanged. Construction answer keys are explicitly '
             'declared and verified against the independent evaluator. The additional hypothesis-status task is '
             'scored separately; it does not alter the original Stage 1 endpoint.', '',
             'Recent history defines the common token ceiling using its last six transitions. Structured memory '
             'and retrieved records must fit that same ceiling; their actual token counts can be lower. Selection '
             'uses current state and recency, never the question. All prompt counts use the four hash-verified '
             'pinned tokenizer assets. Full history and unbounded memory are diagnostic references only.', '',
             'Scripted readers parse the actual rendered evidence, not hidden records or answer keys. Factual '
             'answers also agree with the existing package oracle. Retired entries, hypotheses and indeterminate '
             'dispatches cannot become exact-state factual observations.', '',
             '## Factual recall and hypothesis diagnosis', '',
             'These tasks are separate endpoints. The family and delay tables below combine them only as '
             'descriptive counts; they do not define an advancement criterion.', '',
             '| Task | Arm | Correct / questions | Selection loss | Reader errors |',
             '| --- | --- | --- | --- | --- |']
    for row in summary['by_kind']:
        lines.append(f"| {row['group']} | {row['arm']} | {row['correct']}/{row['questions']} | "
                     f"{row['selection_loss']} | {row['reader_errors']} |")
    lines += ['',
             '## Results by family', '',
             '| Family | Arm | Correct / questions | Writer store loss | Selection loss | Reader errors |',
             '| --- | --- | --- | --- | --- | --- |']
    for row in summary['by_family']:
        lines.append(f"| {row['group']} | {row['arm']} | {row['correct']}/{row['questions']} | "
                     f"{row['store_loss']} | {row['selection_loss']} | {row['reader_errors']} |")
    lines += ['', '## Results by distractor delay', '',
              '| Delay | Arm | Correct / questions | Writer store loss | Selection loss | Reader errors |',
              '| --- | --- | --- | --- | --- | --- |']
    for row in summary['by_delay']:
        lines.append(f"| {row['group']} | {row['arm']} | {row['correct']}/{row['questions']} | "
                     f"{row['store_loss']} | {row['selection_loss']} | {row['reader_errors']} |")
    lines += ['', '## Where essential evidence is lost', '',
              'The per-question rows in `results.json` name missing relevant steps and compare full-history truth, '
              'full-store truth and selected-package truth. A missing step alone is not an answer failure: '
              'another retained observation or a corrected hypothesis may provide the same information.', '',
              'Recent history drops earlier observations once they leave the six-transition window. Current-state '
              'retrieval can recover earlier current-state records, but prioritizes them over evidence about a '
              'different historical state. Memory selection prioritizes current-state observations ahead of '
              'level hypotheses, so a corrected hypothesis or non-current observation may remain intact in '
              'the full store yet be omitted under the token ceiling. Selection stops at the first priority '
              'item that cannot fit, as the original protocol specifies.', '',
              'For example, in `development-contradicted_hypothesis-0-d8`, both memory and retrieved-record '
              'packages retain step 0 but omit steps 1 and 2. Step 2 is the counterexample. The full-history '
              'and full-store verdict is contradicted, while the selected text supports only hypothesis_only. '
              'The reader therefore loses the correction despite a faithful writer. In '
              '`development-buried_evidence-0-d24`, the per-question step trace distinguishes retrieval of '
              'current-state evidence from loss of evidence about the historical non-current state.', '',
              'Failed and unknown dispatches provide no visual fact. Their raw records retain distinct dispatch '
              'statuses, while the faithful memory store writes no factual observation for either. Correctly '
              'answering no_evidence does not prove that the memory retained the distinction between rejection '
              'and an uncertain outcome; this task does not score recall of dispatch-status metadata.', '',
              'A temporary change is keyed as changed_then_returned, never no_observed_change. Reset retires '
              'segment conclusions while preserving historical exact-state observations. Level numbers remain '
              'part of the key even when the frame is identical across a level boundary.', '',
              '## Attribution and controls', '',
              'Writer fidelity is audited before selection. Writer-store loss or distortion is measured using '
              'the unbounded memory answer; integrity faults are recorded independently. Selection loss means '
              'the selected text supports a different answer from its full source. Reader error means the output '
              'does not match the evidence actually supplied. These flags can coexist. An incorrect full-history '
              'answer alone never identifies the failing component.', '',
              f"Faithful stores passing the original fidelity evaluator: {summary['faithful_stores']}/{summary['cases']}. "
              f"Writer runs with rejected or invalid operations: {summary['writer_log_cases']}. "
              f"Overclaiming negative-control stores with detected integrity faults: {summary['negative_writer_detected']}. "
              'Tests also isolate a lossy writer, bad selection and a deliberately wrong reader, including '
              'simultaneous store and reader errors.', '',
              '## Leakage and request preparation', '',
              'Fixture labels, construction logs, expected answers and component diagnoses stay outside requests. '
              'Requests contain only the unchanged prompt frame, rendered selected evidence and the question. '
              'Question wording and response limits are identical across arms. Requests have opaque IDs, and '
              'truth/package keys live in the evaluator-only sidecar. Leakage tests poison evaluator metadata '
              'and confirm that the resulting requests do not change.', '',
              f"`requests.jsonl` contains {summary['requests']} inert request drafts. The manifest binds their hash, "
              'fixture and evaluator-key hashes, source hashes, model revision and tokenizer hashes. '
              'No submission, network client, authorization or GPU execution path is included. These exposed '
              'development cases are not eligible as fresh evaluation cases for a future confirmatory run.', '',
              '## Reproduction', '',
              '```bash', 'python -m research.evidence_memory_stress_v1.build --check',
              'python -m unittest -v tests.test_evidence_memory_stress_v1', '```', '',
              'The builder verifies every retained output in memory with `--check`. Omitting that flag '
              'regenerates only this additive development package. Original notebooks, locks, approvals, '
              'reservations and historical evidence remain unchanged.', '']
    return '\n'.join(lines).encode()


def artifacts(tokenizer=None):
    tokenizer = tokenizer or TK.Tokenizer()
    cases = FX.generate()
    audits, rows, requests, keys = [], [], [], []
    for case in cases:
        audit, rs, reqs, ks = analyze(case, tokenizer)
        audits.append(audit)
        rows += rs
        for req, key in zip(reqs, ks):
            rid = f'request-{len(requests):05d}'
            req['request_id'] = key['request_id'] = rid
            requests.append(req)
            keys.append(key)
    summary = {'cases': len(cases), 'requests': len(requests), 'by_family': table(rows, 'family'),
               'by_delay': table(rows, 'delay'), 'by_kind': table(rows, 'kind'),
               'faithful_stores': sum(a['writer_fidelity']['faithful'] for a in audits),
               'writer_log_cases': sum(bool(a['writer_log']) for a in audits),
               'negative_writer_detected': sum(bool(a['negative_writer_fault_ids']) for a in audits),
               'token_budget_range': [min(a['budget_tokens'] for a in audits), max(a['budget_tokens'] for a in audits)],
               'all_selected_tokens_within_ceiling': True}
    outputs = {'fixtures.json': encode({'partition': 'development', 'seed': FX.SEED, 'cases': cases}),
               'results.json': encode({'summary': summary, 'writer_audits': audits, 'rows': rows}),
               'requests.jsonl': b''.join((json.dumps(r, sort_keys=True) + '\n').encode() for r in requests),
               'evaluator_keys.json': encode({'evaluator_only': True, 'keys': keys}), 'report.md': report(summary)}
    source_paths = list((ROOT / 'research/evidence_memory_stress_v1').glob('*.py')) + [
        ROOT / ('research/evidence_memory_v1/' + name + '.py') for name in
        ('fidelity', 'protocol', 'readers', 'render', 'schema', 'stage1', 'tokens', 'trajectories', 'writers')]
    source_paths += list((ROOT / 'research/transition_evidence_v1').glob('*.py'))
    source_paths += list((ROOT / 'research/transition_evidence_v2').glob('*.py'))
    source_paths += [ROOT / 'tests/test_evidence_memory_stress_v1.py',
                     ROOT / 'reports/evidence_memory_v1_protocol_v2.md']
    outputs['manifest.json'] = encode({'version': 'evidence_memory_stress_v1', 'partition': 'development',
        'gpu_launch_authorized': False, 'model_calls': 0,
        'base_revision': '107d8b44b6ebb7c4ea81f4972a65e64990cf638c',
        'model': 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8',
        'model_revision': 'd9748a51ae66354c4dad665aab2c71f26cf2c8cd', 'tokenizer_sha256': TK.PINNED,
        'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in outputs.items()},
        'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_paths)},
        'common_budget': 'pinned tokenizer count of the last six rendered transitions',
        'request_count': len(requests), 'evaluator_keys_sent_to_model': False})
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = artifacts()
    if not args.check:
        DEST.mkdir(parents=True, exist_ok=True)
    for name, raw in outputs.items():
        if args.check:
            if (DEST / name).read_bytes() != raw:
                raise SystemExit('development artifact differs: ' + name)
        else:
            (DEST / name).write_bytes(raw)
    print('Verified' if args.check else 'Wrote', len(outputs), 'development artifacts:', DEST)


if __name__ == '__main__':
    main()
