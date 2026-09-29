"""Scoring and decision rules for the WS3 transition questionnaire (DRAFT r2; frozen only with the protocol).

Reused unchanged from Workstream 1 (research/evidence_comprehension_v2/score.py):
- per-family labels (`criterion_met` requires accuracy >= 0.90 and >= 0.90 where the best predeclared shortcut is
  wrong, on at least 10 such questions);
- both-correct scoring over two identified withheld passes; development and transfer are scored on pass 1 only;
- the context bootstrap: whole sequences are resampled, so questions on one transition are never treated as
  independent;
- the 0.05 regression tolerance.

Added here:
- **Over-claim gates** (context-level):
  - rate = contexts with an over-claim ÷ denominator contexts;
  - a context enters the denominator when it has a question whose key is not affirmative for that claim type (see
    questionnaire.OVER_CLAIM_GATES);
  - it counts as an over-claim if, in either pass, such a question received the affirmative answer or an invalid
    response (so avoidance cannot help);
  - a missing answer makes the gate incomplete;
  - the cap is 0.02 on at least 100 contexts. It is a benchmark criterion, not a guarantee about the underlying
    error probability.
- **Completeness** (revision r2.1, review of 93142fc): primary questions and over-claim-gate questions are required for
  any verdict; missing regression-check answers withhold promotion and are never read as "no regression"; development
  and transfer never change the verdict (COMPLETENESS_POLICY).
- **Verdict** (suffix `_tool_assisted`; the first rule that applies decides):
  1. `incomplete`;
  2. `reference_meets_criterion` when the reference already meets the criterion on every primary family and passes
     both gates (there is no demonstrated need to promote the candidate);
  3. `candidate_clear_improvement` (or `candidate_improvement_unconfirmed_checks_incomplete` when a regression check
     lacks evidence) when the candidate meets the criterion on every primary family and passes both
     gates, every primary family where the reference falls short improves (paired lower bound > 0), and no family
     regresses;
  4. `mixed`;
  5. `improved_below_criterion`;
  6. `no_clear_improvement`.
"""
import json
import random

from jsonschema import Draft202012Validator

from research.evidence_comprehension_v2.score import (BOOTSTRAP_REPS, REGRESSION_TOLERANCE, family_metrics,
                                                      outcome_fn, paired_metrics)
from research.evidence_comprehension_v1.score import _reject_constant
from research.transition_evidence_v1 import questionnaire as Q

OVER_CLAIM_CAP = 0.02
PASS_IDS = ('pass_1', 'pass_2')
REFERENCE, CANDIDATE = Q.CONDITIONS
_VALIDATORS = {}


def validate(family, content):
    if family not in _VALIDATORS:
        _VALIDATORS[family] = Draft202012Validator(Q.response_schema(family))
    value = json.loads(content, parse_constant=_reject_constant)
    errors = list(_VALIDATORS[family].iter_errors(value))
    if errors:
        raise ValueError('schema: ' + errors[0].message[:100])
    return value['answer']


def score(probe, content):
    try:
        answer = validate(probe['family'], content)
    except (ValueError, TypeError) as exc:
        return {'probe_id': probe['probe_id'], 'valid': False, 'correct': False, 'error': str(exc)[:120]}
    return {'probe_id': probe['probe_id'], 'valid': True, 'correct': answer == probe['key'], 'answer': answer}


def over_claims(probes, passes, condition):
    """{gate: {...}} for one condition on the withheld partition."""
    out = {}
    for gate, members in Q.OVER_CLAIM_GATES.items():
        per_context, missing = {}, False
        for p in probes:
            if p['partition'] != 'withheld' or p['condition'] != condition or (p['family'], p['key']) not in members:
                continue
            rows = [passes.get(i, {}).get(p['probe_id']) for i in PASS_IDS]
            if any(r is None for r in rows):
                missing = True
                continue
            claimed = any(not r['valid'] or r.get('answer') == Q.AFFIRMATIVE[p['family']] for r in rows)
            ctx = per_context.setdefault(p['case_context'], {'sequence': p['source_context'], 'claim': False,
                                                            'kinds': set()})
            ctx['claim'] |= claimed
            ctx['kinds'].add(p['key'])
        n = len(per_context)
        hits = sum(c['claim'] for c in per_context.values())
        by_sequence = {}
        for c in per_context.values():
            by_sequence.setdefault(c['sequence'], []).append(int(c['claim']))
        upper = None
        if by_sequence and not missing:
            rng = random.Random(f'overclaim:{condition}:{gate}')
            seqs = sorted(by_sequence)
            stats = []
            for _ in range(BOOTSTRAP_REPS):
                sample = [by_sequence[rng.choice(seqs)] for _ in seqs]
                total = sum(len(s) for s in sample)
                stats.append(sum(sum(s) for s in sample) / total)
            stats.sort()
            upper = round(stats[int(0.975 * BOOTSTRAP_REPS) - 1], 4)
        row = {'denominator_contexts': n, 'over_claim_contexts': hits,
               'rate': round(hits / n, 4) if n else None, 'context_bootstrap_upper_95': upper,
               'status': 'incomplete' if missing or not n else (
                   'passes' if n >= Q.FLOORS['over_claim_denominator_contexts'] and hits / n <= OVER_CLAIM_CAP
                   else 'fails')}
        if gate == 'unsupported_causal_claim':  # unsupported (not established) versus disproven (contradicted)
            for kind in ('not_established', 'contradicted'):
                sub = [c for c in per_context.values() if kind in c['kinds']]
                row[kind] = {'contexts': len(sub), 'over_claim_contexts': sum(c['claim'] for c in sub)}
        out[gate] = row
    return out


def analyze(probes, passes):
    if not isinstance(passes, dict) or set(passes) - set(PASS_IDS):
        raise ValueError('passes must be identified as pass_1 and pass_2')
    outcomes = {part: outcome_fn(passes, part) for part in ('withheld', 'development', 'transfer')}
    report = {'families': {}, 'per_pass': {}, 'extraction_split': {}, 'paired': {}, 'agreement': {},
              'over_claims': {}, 'completeness': {}}
    groups = {}
    for p in probes:
        groups.setdefault((p['partition'], p['condition'], p['family']), []).append(p)
    for (part, cond, fam), group in sorted(groups.items()):
        report['families'].setdefault(part, {}).setdefault(cond, {})[fam] = family_metrics(
            group, outcomes[part], f'{part}/{cond}/{fam}')
        if part == 'withheld':
            for pass_id in PASS_IDS:
                single = lambda p, i=pass_id: ('missing' if passes.get(i, {}).get(p['probe_id']) is None else  # noqa: E731
                                               'correct' if passes[i][p['probe_id']]['correct'] else 'wrong')
                m = family_metrics(group, single, f'{pass_id}/{cond}/{fam}')
                report['per_pass'].setdefault(pass_id, {}).setdefault(cond, {})[fam] = {
                    k: m[k] for k in ('n', 'missing', 'correct', 'accuracy')}
            row = {'n': len(group), 'valid_pairs': 0, 'identical_answers': 0, 'invalid_pairs': 0, 'missing_pairs': 0}
            for p in group:
                pair = [passes.get(i, {}).get(p['probe_id']) for i in PASS_IDS]
                if any(r is None for r in pair):
                    row['missing_pairs'] += 1
                elif not all(r.get('valid') is True for r in pair):
                    row['invalid_pairs'] += 1  # an invalid response has no answer to agree with
                else:
                    row['valid_pairs'] += 1
                    row['identical_answers'] += pair[0]['answer'] == pair[1]['answer']
            report['agreement'].setdefault(cond, {})[fam] = row
    for part in ('withheld', 'development', 'transfer'):
        pairs = {}
        for p in probes:
            if p['partition'] == part:
                pairs.setdefault(p['pair_id'], {})[p['condition']] = p
        per_family = {}
        for pair in pairs.values():
            if REFERENCE in pair and CANDIDATE in pair:
                per_family.setdefault(pair[REFERENCE]['family'], []).append((pair[REFERENCE], pair[CANDIDATE]))
        report['paired'][part] = {f: paired_metrics(v, outcomes[part], f'paired/{part}/{f}')
                                  for f, v in sorted(per_family.items())}
    for cond in Q.CONDITIONS:
        held = [p for p in probes if p['partition'] == 'withheld' and p['condition'] == cond]
        for label, flag in (('extraction_under_candidate', True), ('combination_or_rejection', False)):
            sub = [p for p in held if p['extraction_under_candidate'] is flag]
            hits = [outcomes['withheld'](p) for p in sub]
            report['extraction_split'].setdefault(cond, {})[label] = {
                'n': len(sub), 'correct': hits.count('correct'), 'missing': hits.count('missing')}
        report['over_claims'][cond] = over_claims(probes, passes, cond)
    held = [p for p in probes if p['partition'] == 'withheld']
    gate_members = {pair for members in Q.OVER_CLAIM_GATES.values() for pair in members}

    def status(group):
        return 'incomplete' if not group or any(outcomes['withheld'](p) == 'missing' for p in group) else 'complete'
    report['completeness'] = {
        'primary': status([p for p in held if p['role'] == 'primary']),
        'over_claim_gates': status([p for p in held if (p['family'], p['key']) in gate_members]),
        'checks': status([p for p in held if p['role'] != 'primary']),
        'withheld': status(held),
        'whole_schedule': 'incomplete' if any(outcomes[p['partition']](p) == 'missing' for p in probes) else 'complete',
        'policy': COMPLETENESS_POLICY}
    report['verdict'] = verdict(report) + '_tool_assisted'
    return report


COMPLETENESS_POLICY = (
    'Required for any verdict: every withheld primary question and every withheld over-claim-gate question, in both '
    'conditions and both passes. Gate questions include check-family questions (level_completion_reported keyed no or '
    'not_observed); a missing one makes the verdict incomplete. Other check-family questions are regression evidence: '
    'a family with any missing answer has no regression evidence, is never read as showing no regression, and '
    'withholds promotion (candidate_improvement_unconfirmed_checks_incomplete). Development and transfer answers never '
    'change the verdict.')


def verdict(report):
    c = report['completeness']
    if c['primary'] != 'complete' or c['over_claim_gates'] != 'complete':
        return 'incomplete'
    fams = report['families']['withheld']
    paired = report['paired']['withheld']
    primary = Q.ROLES['primary']
    gates = report['over_claims']
    if any(g['status'] == 'incomplete' for cond in Q.CONDITIONS for g in gates[cond].values()):
        return 'incomplete'
    evidenced = {f for f, row in paired.items() if not row['incomplete'] and row['difference_bootstrap_95']}
    without_evidence = sorted(set(paired) - evidenced)
    report['families_without_regression_evidence'] = without_evidence
    lower = {f: paired[f]['difference_bootstrap_95'][0] for f in evidenced}
    upper = {f: paired[f]['difference_bootstrap_95'][1] for f in evidenced}
    regressed = [f for f in evidenced if upper[f] < 0 or fams[CANDIDATE][f]['accuracy']
                 < fams[REFERENCE][f]['accuracy'] - REGRESSION_TOLERANCE]
    improved = [f for f in primary if lower[f] > 0]
    ref_met = all(fams[REFERENCE][f]['label'] == 'criterion_met' for f in primary)
    cand_met = all(fams[CANDIDATE][f]['label'] == 'criterion_met' for f in primary)
    ref_gates = all(g['status'] == 'passes' for g in gates[REFERENCE].values())
    cand_gates = all(g['status'] == 'passes' for g in gates[CANDIDATE].values())
    if ref_met and ref_gates:
        return 'reference_meets_criterion'
    if (cand_met and cand_gates and not regressed
            and all(fams[REFERENCE][f]['label'] == 'criterion_met' or lower[f] > 0 for f in primary)):
        return 'candidate_improvement_unconfirmed_checks_incomplete' if without_evidence else 'candidate_clear_improvement'
    if improved and regressed:
        return 'mixed'
    if improved:
        return 'improved_below_criterion'
    return 'no_clear_improvement'
