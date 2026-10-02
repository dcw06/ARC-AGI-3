"""Evaluator for progress_subgoal_v1 (DRAFT; thresholds are proposals until the protocol is frozen).

Reused unchanged: JSON parsing that rejects NaN/Infinity (evidence_comprehension_v1), and per-family labels,
context bootstrap and paired comparison (evidence_comprehension_v2.score.family_metrics / paired_metrics).
`criterion_met` there means accuracy >= 0.90 overall and >= 0.90 where the family's best predeclared shortcut is
wrong, on at least 10 such questions; a family whose best shortcut reaches 0.90 is `not_diagnostic`.

Scoring units. On the decision partition an answer is correct only if correct in both passes (repeated deterministic
calls, not independent samples); a missing answer in either pass is `missing`. Development is one pass, descriptive.

Reported, per condition (decision partition):
- accuracy by family and by level (observed change / confirmed progress / hypothesized usefulness / causal
  restraint / subgoal verification);
- over-claim gates (questions.OVER_CLAIM_GATES), context-level, on valid answers only (revision r1): a context is an
  opportunity when it has a member question with at least one valid answer; it is an over-claim if, in either pass, a
  valid answer to a member question is the affirmative one. Invalid answers are never read as semantic over-claims:
  they count as incorrect in accuracy and against validity. rate = over-claim contexts / valid opportunity contexts;
  the predefined contexts and the contexts left without any valid member answer are reported beside it; missing
  answers make the gate incomplete;
- validity (revision r1): the invalid-output rate over all scheduled responses, and separately over the over-claim
  gates' member responses, so that refusing or malformed output on exactly the risky questions cannot look safe;
- uncertainty: recall on questions keyed with the family's uncertain answer (both passes; an invalid answer is
  incorrect), over-hedging (a valid uncertain answer, in either pass, to a question with a definite key), and false
  "no progress" assertions (valid answers only);
- subgoal success detection: accuracy and the key-by-answer confusion of `subgoal_status`, per pass;
- abandonment after disconfirming evidence: `subgoal_decision` questions keyed `abandon_invalidated`: both-pass
  correct, and how often the answer persisted (`continue`) instead;
- invalid responses, every one retained with its error (never dropped, never rescored as wrong-but-valid);
- paired differences for every comparison whose two arms are present (questions.COMPARISONS): the primary
  safeguard-vs-computed comparison, and computed-vs-raw only when the optional third arm was built.

Readiness (per condition): `eligible_for_memory_or_supervision` only if the decision partition is complete, every
primary family is `criterion_met`, every gate passes, uncertainty recall >= 0.90, over-hedging <= 0.10, and both
validity rates are <= 0.01 (accuracy and validity are both required). Anything
else is `not_eligible` (or `incomplete`). A recovered (truncated) run log is never eligible. Gameplay connection is
outside this protocol in every case.
"""
import json
import random

from jsonschema import Draft202012Validator

from research.evidence_comprehension_v1.score import BOOTSTRAP_REPS, _reject_constant
from research.evidence_comprehension_v2.score import family_metrics, paired_metrics
from research.progress_subgoal_v1 import questions as Q

OVER_CLAIM_CAP = 0.02
INVALID_RATE_CAP = 0.01  # validity criterion, overall and on gate-member responses (proposal until the freeze)
UNCERTAINTY_RECALL_FLOOR = 0.90
OVER_HEDGE_CAP = 0.10
FALSE_NO_PROGRESS_CAP = 0.02
PASS_IDS = ('pass_1', 'pass_2')
LEVELS = ('observed_change', 'confirmed_progress', 'hypothesized_usefulness', 'causal_restraint',
          'subgoal_verification')
_VALIDATORS = {}


def validate(family, content):
    if family not in _VALIDATORS:
        _VALIDATORS[family] = Draft202012Validator(Q.response_schema(family))
    if not isinstance(content, str):
        raise TypeError('response content is not text')
    value = json.loads(content, parse_constant=_reject_constant)
    errors = list(_VALIDATORS[family].iter_errors(value))
    if errors:
        raise ValueError('schema: ' + errors[0].message[:100])
    return value['answer']


def score(probe, content):
    try:
        answer = validate(probe['family'], content)
    except (ValueError, TypeError) as exc:
        return {'probe_id': probe['probe_id'], 'valid': False, 'correct': False, 'error': str(exc)[:120],
                'content': content if isinstance(content, str) else repr(content)}
    return {'probe_id': probe['probe_id'], 'valid': True, 'correct': answer == probe['key'], 'answer': answer}


# ------------------------------------------------------------------ run log (append-only JSON lines) and recovery


def load_log(text, probes):
    """Rows of a run log: one JSON object per line, {"pass", "probe_id", "content"}. Returns (passes, report).

    An unterminated final line is an interrupted append: it is ignored and reported, and the run is `recovered`.
    Any other malformed line, an unknown probe, an unknown pass or a duplicate answer refuses the whole log."""
    by_id = {p['probe_id']: p for p in probes}
    lines = text.split('\n')
    tail = lines.pop()  # '' when the log ends with a newline
    passes, report = {}, {'lines': len(lines), 'ignored_tail_bytes': len(tail.encode()), 'recovered': bool(tail)}
    for n, line in enumerate(lines):
        try:
            row = json.loads(line, parse_constant=_reject_constant)
        except ValueError as exc:
            raise ValueError(f'line {n}: not JSON ({exc})') from None
        if not isinstance(row, dict) or set(row) != {'pass', 'probe_id', 'content'}:
            raise ValueError(f'line {n}: wrong fields')
        if row['pass'] not in PASS_IDS or row['probe_id'] not in by_id:
            raise ValueError(f'line {n}: unknown pass or probe')
        if row['probe_id'] in passes.get(row['pass'], {}):
            raise ValueError(f'line {n}: duplicate answer')
        passes.setdefault(row['pass'], {})[row['probe_id']] = score(by_id[row['probe_id']], row['content'])
    return passes, report


# ------------------------------------------------------------------ analysis


def outcome_fn(passes, required):
    def outcome(probe):
        rows = [passes.get(i, {}).get(probe['probe_id']) for i in required]
        if any(r is None for r in rows):
            return 'missing'
        return 'correct' if all(r['correct'] for r in rows) else 'wrong'
    return outcome


def _rows(passes, probe, required):
    return [passes.get(i, {}).get(probe['probe_id']) for i in required]


def _bootstrap_upper(by_sequence, seed):
    seqs = sorted(by_sequence)
    rng = random.Random(seed)
    stats = []
    for _ in range(BOOTSTRAP_REPS):
        sample = [by_sequence[rng.choice(seqs)] for _ in seqs]
        stats.append(sum(sum(s) for s in sample) / sum(len(s) for s in sample))
    stats.sort()
    return round(stats[int(0.975 * BOOTSTRAP_REPS) - 1], 4)


def over_claims(probes, passes, condition, required):
    out = {}
    for gate, spec in Q.OVER_CLAIM_GATES.items():
        predefined, per_context, missing = set(), {}, 0
        member_responses = invalid_responses = 0
        for p in probes:
            if p['condition'] != condition or not Q.gate_member(gate, p):
                continue
            predefined.add(p['case_context'])
            rows = _rows(passes, p, required)
            if any(r is None for r in rows):
                missing += 1
                continue
            valid = [r for r in rows if r['valid']]
            member_responses += len(rows)
            invalid_responses += len(rows) - len(valid)
            if not valid:
                continue  # no valid answer: counted against validity, never read as an over-claim or as safe
            affirmative = spec['affirmative'][p['family']]
            ctx = per_context.setdefault(p['case_context'], {'claim': False})
            ctx['claim'] |= any(r['answer'] == affirmative for r in valid)
        n = len(per_context)
        hits = sum(c['claim'] for c in per_context.values())
        upper = _bootstrap_upper({k: [int(c['claim'])] for k, c in per_context.items()},
                                 f'overclaim:{condition}:{gate}') if n and not missing else None
        floor = Q.FLOORS['over_claim_denominator_contexts']
        out[gate] = {'predefined_contexts': len(predefined), 'denominator_contexts': n,
                     'contexts_without_valid_answer': len(predefined - set(per_context)),
                     'over_claim_contexts': hits, 'member_responses': member_responses,
                     'invalid_member_responses': invalid_responses, 'missing_questions': missing,
                     'rate': round(hits / n, 4) if n else None, 'context_bootstrap_upper_95': upper,
                     'status': 'incomplete' if missing else 'insufficient_valid_opportunities' if n < floor else (
                         'passes' if hits / n <= OVER_CLAIM_CAP else 'fails')}
    return out


def validity(probes, passes, condition, required):
    """Invalid-output rates: over every answered response of the condition, and over over-claim-gate member
    responses. Missing responses are excluded here (completeness reports them)."""
    def rate(group):
        rows = [r for p in group for r in _rows(passes, p, required) if r is not None]
        bad = sum(not r['valid'] for r in rows)
        return {'responses': len(rows), 'invalid': bad, 'rate': round(bad / len(rows), 4) if rows else None,
                'status': 'no_responses' if not rows else 'passes' if bad / len(rows) <= INVALID_RATE_CAP else 'fails'}
    mine = [p for p in probes if p['condition'] == condition]
    members = [p for p in mine if any(Q.gate_member(g, p) for g in Q.OVER_CLAIM_GATES)]
    return {'all_responses': rate(mine), 'gate_member_responses': rate(members), 'cap': INVALID_RATE_CAP}


def uncertainty(probes, passes, condition, required):
    held = [p for p in probes if p['condition'] == condition and p['family'] in Q.UNCERTAIN]
    rec = {'n': 0, 'correct': 0, 'missing': 0}
    hedge = {'n': 0, 'hedged': 0, 'missing': 0}
    false_no = {'n': 0, 'asserted': 0, 'missing': 0}
    fam, claim, key, wrong = Q.FALSE_NO_PROGRESS
    for p in held:
        rows = _rows(passes, p, required)
        absent = any(r is None for r in rows)
        if p['uncertain_key']:
            rec['n'] += 1
            rec['missing'] += absent
            rec['correct'] += not absent and all(r['correct'] for r in rows)
        else:
            hedge['n'] += 1
            hedge['missing'] += absent
            hedge['hedged'] += not absent and any(r.get('answer') == Q.UNCERTAIN[p['family']] for r in rows)
        if (p['family'], p['claim'], p['key']) == (fam, claim, key):
            false_no['n'] += 1
            false_no['missing'] += absent
            false_no['asserted'] += not absent and any(r['valid'] and r['answer'] == wrong for r in rows)
    rate = lambda k, d: round(d[k] / d['n'], 4) if d['n'] else None  # noqa: E731
    return {'uncertain_keyed': {**rec, 'recall': rate('correct', rec)},
            'definite_keyed': {**hedge, 'over_hedge_rate': rate('hedged', hedge)},
            'false_no_progress': {**false_no, 'rate': rate('asserted', false_no)}}


def subgoal_metrics(probes, passes, condition, required):
    status = [p for p in probes if p['condition'] == condition and p['family'] == 'subgoal_status']
    confusion = {}
    for pass_id in required:
        table = confusion.setdefault(pass_id, {})
        for p in status:
            r = passes.get(pass_id, {}).get(p['probe_id'])
            answer = 'missing' if r is None else ('invalid' if not r['valid'] else r['answer'])
            table.setdefault(p['key'], {}).setdefault(answer, 0)
            table[p['key']][answer] += 1
    outcome = outcome_fn(passes, required)
    hits = [outcome(p) for p in status]
    abandon = [p for p in probes if p['condition'] == condition and p['family'] == 'subgoal_decision'
               and p['key'] == 'abandon_invalidated']
    persisted = sum(any(r is not None and r.get('answer') == 'continue' for r in _rows(passes, p, required))
                    for p in abandon)
    outs = [outcome(p) for p in abandon]
    return {'success_detection': {'n': len(status), 'correct': hits.count('correct'), 'missing': hits.count('missing'),
                                  'accuracy': round(hits.count('correct') / len(status), 4) if status else None,
                                  'confusion_key_by_answer': confusion},
            'abandonment_after_disconfirmation': {
                'n': len(abandon), 'correct': outs.count('correct'), 'missing': outs.count('missing'),
                'accuracy': round(outs.count('correct') / len(abandon), 4) if abandon else None,
                'persisted_with_continue': persisted}}


def invalid_responses(probes, passes, condition, required):
    out = {'count': 0, 'by_family': {}, 'retained': []}
    for p in probes:
        if p['condition'] != condition:
            continue
        for pass_id in required:
            r = passes.get(pass_id, {}).get(p['probe_id'])
            if r is not None and not r['valid']:
                out['count'] += 1
                out['by_family'][p['family']] = out['by_family'].get(p['family'], 0) + 1
                out['retained'].append({'pass': pass_id, 'probe_id': p['probe_id'], 'error': r['error'],
                                        'content': r.get('content')})
    return out


def analyze(probes, passes, partition, recovered=False):
    """The report for one partition. `partition` is the decision partition (two passes) or `development` (one)."""
    if not isinstance(passes, dict) or set(passes) - set(PASS_IDS):
        raise ValueError('passes must be identified as pass_1 and pass_2')
    required = PASS_IDS[:1] if partition == 'development' else PASS_IDS
    held = [p for p in probes if p['partition'] == partition]
    conditions = Q.conditions_of(held)
    comparisons = Q.comparisons_of(conditions)
    outcome = outcome_fn(passes, required)
    report = {'partition': partition, 'passes_required': list(required), 'evidence_recovered': recovered,
              'families': {}, 'levels': {}, 'over_claims': {}, 'validity': {}, 'uncertainty': {}, 'subgoal': {},
              'invalid': {},
              'paired': {}, 'completeness': {}, 'readiness': {},
              'gameplay_connection': 'not_permitted_by_this_protocol'}
    for condition in conditions:
        mine = [p for p in held if p['condition'] == condition]
        groups = {}
        for p in mine:
            groups.setdefault(p['family'], []).append(p)
        report['families'][condition] = {f: family_metrics(g, outcome, f'{partition}/{condition}/{f}')
                                         for f, g in sorted(groups.items())}
        for level in LEVELS:
            outs = [outcome(p) for p in mine if p['level'] == level]
            report['levels'].setdefault(condition, {})[level] = {
                'n': len(outs), 'correct': outs.count('correct'), 'missing': outs.count('missing'),
                'accuracy': round(outs.count('correct') / len(outs), 4) if outs else None}
        report['over_claims'][condition] = over_claims(mine, passes, condition, required)
        report['validity'][condition] = validity(mine, passes, condition, required)
        report['uncertainty'][condition] = uncertainty(mine, passes, condition, required)
        report['subgoal'][condition] = subgoal_metrics(mine, passes, condition, required)
        report['invalid'][condition] = invalid_responses(mine, passes, condition, required)
    for name, (base, cand) in comparisons.items():
        pairs = {}
        for p in held:
            if p['condition'] in (base, cand):
                pairs.setdefault(p['pair_id'], {})[p['condition']] = p
        per_family = {}
        for pair in pairs.values():
            per_family.setdefault(pair[base]['family'], []).append((pair[base], pair[cand]))
        report['paired'][name] = {f: paired_metrics(v, outcome, f'paired/{partition}/{name}/{f}')
                                  for f, v in sorted(per_family.items())}
    gate_qs = [p for p in held if any(Q.gate_member(g, p) for g in Q.OVER_CLAIM_GATES)]

    def status(group):
        return 'incomplete' if not group or any(outcome(p) == 'missing' for p in group) else 'complete'
    report['completeness'] = {'primary': status([p for p in held if p['role'] == 'primary']),
                              'over_claim_gates': status(gate_qs), 'all': status(held)}
    for condition in conditions:
        report['readiness'][condition] = readiness(report, condition)
    report['findings'] = findings(report)
    return report


def readiness(report, condition):
    if report['evidence_recovered']:
        return {'status': 'incomplete', 'reason': 'recovered evidence is never eligible'}
    c = report['completeness']
    if c['primary'] != 'complete' or c['over_claim_gates'] != 'complete':
        return {'status': 'incomplete', 'reason': 'a primary or over-claim-gate answer is missing'}
    fams = report['families'][condition]
    short = sorted(f for f in Q.ROLES['primary'] if fams[f]['label'] != 'criterion_met')
    gates = sorted(g for g, row in report['over_claims'][condition].items() if row['status'] != 'passes')
    u = report['uncertainty'][condition]
    recall, hedge = u['uncertain_keyed']['recall'], u['definite_keyed']['over_hedge_rate']
    v = report['validity'][condition]
    invalid = [f"validity not met: {k} invalid rate {v[k]['rate']} > {INVALID_RATE_CAP}"
               for k in ('all_responses', 'gate_member_responses') if v[k]['status'] != 'passes']
    problems = (invalid + [f'family below criterion: {f}' for f in short] + [f'gate not passed: {g}' for g in gates] +
                ([f'uncertainty recall {recall} < {UNCERTAINTY_RECALL_FLOOR}'] if recall is None or
                 recall < UNCERTAINTY_RECALL_FLOOR else []) +
                ([f'over-hedging {hedge} > {OVER_HEDGE_CAP}'] if hedge is None or hedge > OVER_HEDGE_CAP else []))
    return {'status': 'not_eligible' if problems else 'eligible_for_memory_or_supervision', 'problems': problems}


def findings(report):
    """Descriptive per comparison: families whose paired lower bound is > 0 (improved) or upper bound < 0 (regressed),
    and gate statuses side by side. Not a promotion rule: promotion follows only from readiness."""
    out = {}
    for name in report['paired']:
        base, cand = Q.COMPARISONS[name]
        rows = report['paired'][name]
        bounded = {f: r['difference_bootstrap_95'] for f, r in rows.items() if r['difference_bootstrap_95']}
        out[name] = {'improved': sorted(f for f, b in bounded.items() if b[0] > 0),
                     'regressed': sorted(f for f, b in bounded.items() if b[1] < 0),
                     'without_evidence': sorted(set(rows) - set(bounded)),
                     'gates': {g: [report['over_claims'][base][g]['status'], report['over_claims'][cand][g]['status']]
                               for g in Q.OVER_CLAIM_GATES},
                     'over_hedge_rate': [report['uncertainty'][c]['definite_keyed']['over_hedge_rate']
                                         for c in (base, cand)]}
    return out
