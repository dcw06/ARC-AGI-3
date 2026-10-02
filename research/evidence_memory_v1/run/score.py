"""Scoring and analysis for the Stage 1 run (hand-written adapter over research/evidence_memory_v1/protocol.py).

`score(probe, response)` scores one retained answer: the response schema first (readers.validate_response), then
truth-relative and package-relative correctness, unsupported assertions and abstention (protocol.score).
`analyze(probes, passes)` is called by the independent evaluator with the scored pass-1 and pass-2 answers:
- completeness: `complete` only if every scheduled pass-1 probe and every scheduled repeat probe was answered (a
  timed-out or missing call leaves it `incomplete`; a truncated answer counts as answered and invalid);
- when complete: protocol.analyze_rows on pass 1 (primary endpoint, the two contrasts, the availability-restricted
  representation contrast, diagnostics, bootstrap) and the verdict from protocol.conclusions;
- when incomplete: verdict `incomplete`, with descriptive metrics over complete groups only;
- stability: identical answers on the repeat (response stability, never additional independent samples).
"""
from research.evidence_memory_v1 import protocol as P

ROW_FIELDS = ('arm', 'family', 'group', 'delay', 'evidence', 'kind', 'control', 'trajectory', 'truth', 'package')
DEFAULTS = {'valid': False, 'correct_truth': False, 'correct_package': False, 'unsupported': False,
            'abstained': False}


def score(probe, response):
    flags = P.score(response, probe['question'], probe['truth'], probe['package'])
    return {'probe_id': probe['probe_id'], **flags, 'correct': flags['correct_truth']}


def _row(probe, scored):
    row = {**DEFAULTS, **scored, **{k: probe[k] for k in ROW_FIELDS}, 'question': probe['question_index']}
    row.setdefault('answer', 'invalid:' + str(scored.get('error')))
    return row


def analyze(probes, passes, resamples=P.BOOTSTRAP_RESAMPLES):
    from research.evidence_memory_v1.run.probes import load_frozen
    frozen, _ = load_frozen()
    by_id = {p['probe_id']: p for p in probes}
    scheduled = {block['pass']: block['probe_ids'] for block in frozen['schedule']}
    rows = {pass_id: [_row(by_id[i], passes.get(pass_id, {})[i]) for i in ids if i in passes.get(pass_id, {})]
            for pass_id, ids in scheduled.items()}
    answers = {pass_id: {'scheduled': len(ids), 'scored': len(rows[pass_id]),
                         'valid': sum(r['valid'] for r in rows[pass_id]),
                         'correct': sum(r['correct_truth'] for r in rows[pass_id])}
               for pass_id, ids in scheduled.items()}
    complete = all(a['scored'] == a['scheduled'] for a in answers.values())
    first = rows.get('pass_1', [])
    by_arm = {arm: [r for r in first if r['arm'] == arm] for arm in P.ARMS + (P.REFERENCE,)}
    result = {'completeness': {'withheld': 'complete' if complete else 'incomplete'}, 'answers': answers,
              'case_source': frozen['case_source'], 'session': frozen['session'],
              'stability': P.stability(first, rows.get('pass_2', []))}
    if complete:
        result['analysis'] = P.analyze_rows(by_arm, resamples=resamples)
        result['verdict'] = result['analysis']['conclusions']['verdict']
    else:
        per_group = {}
        for p in probes:
            per_group.setdefault((p['family'], p['group']), set()).add(p['probe_id'])
        answered = {r['trajectory'] + '/' + r['arm'] + f"/q{r['question']}" for r in first}
        whole = {g for g, ids in per_group.items() if ids <= answered}
        result['descriptive_complete_groups'] = {
            'groups': len(whole),
            'metrics': {arm: P.metrics([r for r in rows_ if (r['family'], r['group']) in whole])
                        for arm, rows_ in by_arm.items()}}
        result['verdict'] = 'incomplete'
    return result
