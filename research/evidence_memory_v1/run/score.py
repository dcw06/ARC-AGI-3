"""Scoring and session-level TECHNICAL validation for the Stage 1 run (hand-written adapter).

`score(probe, response)` scores one retained answer: the response schema first (readers.validate_response), then the
flags of protocol.score. The independent evaluator calls it per answer and keeps the rows internal.

`analyze(probes, passes)` is what the evaluator reports for ONE session. It is technical only:
- completeness: `complete` only if every scheduled pass-1 probe and every scheduled repeat probe was answered (a
  timed-out or missing call leaves it `incomplete`; a truncated answer counts as answered and invalid);
- counts: scheduled, answered and schema-valid answers per pass, and, for EVERY pass (pass 1 and the repeat), the
  invalid answers per arm with their denominators, rates and the invalid-output rule (at most 2% per arm); a session
  is valid only if every pass meets it;
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
    by_id = {p['probe_id']: p for p in frozen['probes']}
    invalid = {}
    for block in frozen['schedule']:  # the registered rule applies to every pass, the repeat included
        pass_rows = rows.get(block['pass'], [])
        arms = {}
        for arm in ARMS:
            scheduled_arm = sum(by_id[i]['arm'] == arm for i in block['probe_ids'])
            if not scheduled_arm:
                continue
            answered_arm = sum(r['arm'] == arm for r in pass_rows)
            bad = sum(r['arm'] == arm and not r['valid'] for r in pass_rows)
            arms[arm] = {'scheduled': scheduled_arm, 'answered': answered_arm, 'invalid': bad,
                         'invalid_rate': round(bad / answered_arm, 4) if answered_arm else None,
                         'rule_met': bool(answered_arm) and bad <= INVALID_RATE_MAX * answered_arm}
        invalid[block['pass']] = {'by_arm': arms, 'rule_met': all(a['rule_met'] for a in arms.values())}
    invalid_ok = all(p['rule_met'] for p in invalid.values())
    complete = all(a['answered'] == a['scheduled'] for a in answers.values())
    status = ('incomplete' if not complete else
              'session_technically_valid' if invalid_ok else 'session_technically_invalid_outputs')
    return {'completeness': {'withheld': 'complete' if complete else 'incomplete'}, 'answers': answers,
            'invalid_by_pass': invalid, 'invalid_rule': f'at most {INVALID_RATE_MAX:.0%} invalid per arm in every pass',
            'invalid_rule_met': invalid_ok, 'technical_status': status,
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
