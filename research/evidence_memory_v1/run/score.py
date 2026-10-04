"""Scoring and session-level TECHNICAL validation for the Stage 1 run (hand-written adapter).

`score(probe, response)` scores one retained answer: the response schema first (readers.validate_response), then the
flags of protocol.score. The independent evaluator calls it per answer and keeps the rows internal.

`analyze(probes, passes)` is what the evaluator reports for ONE session. It is technical only:
- completeness: `complete` only if every scheduled pass-1 probe and every scheduled repeat probe was answered (a
  timed-out or missing call leaves it `incomplete`; a truncated answer counts as answered and invalid);
- counts: scheduled, answered and schema-valid answers per pass, and invalid answers per arm with the invalid-output
  rule (at most 2% per arm);
- a SHA-256 over the retained answers (probe id and canonical answer or invalid marker), so any change to a retained
  response is visible without exposing whether it was right;
- a technical status: `incomplete`, `session_technically_invalid_outputs` or `session_technically_valid`.

It never reports accuracy, contrasts, forgetting, abstention, stability or a verdict. Scientific results exist only
in run/final.py, which requires both sessions bound to the frozen package and technically valid, and pools them.
"""
import hashlib
import json

from research.evidence_memory_v1 import protocol as P

ROW_FIELDS = ('arm', 'family', 'group', 'delay', 'evidence', 'kind', 'control', 'trajectory', 'truth', 'package')
DEFAULTS = {'valid': False, 'correct_truth': False, 'correct_package': False, 'unsupported': False,
            'abstained': False}
INVALID_RATE_MAX = 0.02  # protocol v2 section 10: invalid outputs at most 2% per arm
ARMS = P.ARMS + (P.REFERENCE,)


def score(probe, response):
    flags = P.score(response, probe['question'], probe['truth'], probe['package'])
    return {'probe_id': probe['probe_id'], **flags, 'correct': flags['correct_truth']}


def row(probe, scored):
    """The analysis row for one scored answer (truncated answers arrive without flags and are invalid)."""
    out = {**DEFAULTS, **scored, **{k: probe[k] for k in ROW_FIELDS}, 'question': probe['question_index']}
    out.setdefault('answer', 'invalid:' + str(scored.get('error')))
    return out


def rows_by_pass(frozen, passes):
    by_id = {p['probe_id']: p for p in frozen['probes']}
    return {block['pass']: [row(by_id[i], passes[block['pass']][i]) for i in block['probe_ids']
                            if i in passes.get(block['pass'], {})]
            for block in frozen['schedule']}


def technical(frozen, passes):
    """Session-level technical summary; no outcome-bearing number."""
    rows = rows_by_pass(frozen, passes)
    scheduled = {block['pass']: len(block['probe_ids']) for block in frozen['schedule']}
    answers = {}
    for pass_id, rs in rows.items():
        digest = hashlib.sha256(json.dumps(sorted([r['probe_id'], r['answer']] for r in rs),
                                           separators=(',', ':')).encode()).hexdigest()
        answers[pass_id] = {'scheduled': scheduled[pass_id], 'answered': len(rs),
                            'schema_valid': sum(r['valid'] for r in rs), 'responses_sha256': digest}
    first = rows.get('pass_1', [])
    invalid = {arm: {'answered': sum(r['arm'] == arm for r in first),
                     'invalid': sum(r['arm'] == arm and not r['valid'] for r in first)} for arm in ARMS}
    invalid_ok = all(v['answered'] and v['invalid'] <= INVALID_RATE_MAX * v['answered'] for v in invalid.values())
    complete = all(a['answered'] == a['scheduled'] for a in answers.values())
    status = ('incomplete' if not complete else
              'session_technically_valid' if invalid_ok else 'session_technically_invalid_outputs')
    return {'completeness': {'withheld': 'complete' if complete else 'incomplete'}, 'answers': answers,
            'invalid_by_arm': invalid, 'invalid_rule_met': invalid_ok, 'technical_status': status,
            'session': frozen['session'], 'case_source': frozen['case_source'],
            'seed_sha256': frozen['seed_sha256'],
            'outcomes': 'withheld: scientific results only from run/final.py on both technically valid sessions'}


def analyze(probes, passes):
    """The evaluator's per-session report: technical only. `verdict` carries the technical status."""
    from research.evidence_memory_v1.run.probes import load_frozen
    frozen, _ = load_frozen()
    if {p['probe_id'] for p in probes} != {p['probe_id'] for p in frozen['probes']}:
        raise ValueError('probes differ from the frozen set')
    result = technical(frozen, passes)
    result['verdict'] = result['technical_status']
    return result
