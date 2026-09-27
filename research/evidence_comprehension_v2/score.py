"""Scoring, paired comparison and frozen decision rules for evidence comprehension v2 (revision 1).

Validation and per-family labels reuse the frozen v1 rules unchanged: an independent JSON Schema validator
(Draft 2020-12, real integers only), then set comparison for set-valued answers. Labels are operational:
`criterion_met` (accuracy >= 0.90, at least 10 questions where the family's best shortcut is wrong, and
>= 0.90 on those), `below_accuracy_floor` (< 0.70), `not_diagnostic` (best shortcut >= 0.90),
`inconclusive`, or `incomplete`.

Scoring units:
- withheld partition (the decision): an answer is correct only if correct in both identified passes; a
  missing answer in either pass makes the family `incomplete`. The two passes are repeated deterministic
  calls, not independent samples; uncertainty is context-level (whole trajectories are resampled).
- development and transfer partitions: pass 1 only, descriptive, never part of a decision.

Paired comparison (per track, per family, same questions): improvements (baseline wrong, candidate right),
regressions (the reverse), and a context-resampling bootstrap interval for the accuracy difference.

Track verdicts are computed only from the withheld partition, in this order:
1. `incomplete`: any withheld question of the track lacks an answer in any pass under either condition.
2. `baseline_meets_criterion`: the baseline meets the criterion on every target family (the candidate's own
   labels are still reported; it is not needed to meet the criterion).
3. `candidate_clear_improvement`: the candidate meets the criterion on every target family; on every target
   where the baseline does not, the difference's lower bound is > 0; and no family of the track regresses
   (difference upper bound < 0, or candidate accuracy more than 0.05 below the baseline).
4. `mixed`: some target family's lower bound is > 0 while some family of the track regresses.
5. `improved_below_criterion`: some target family's lower bound is > 0 and no family regresses.
6. `no_clear_improvement`: anything else.
A result that is not `candidate_clear_improvement` never promotes the candidate.
"""
import json
import random

from jsonschema import Draft202012Validator

from research.evidence_comprehension_v1.score import (BOOTSTRAP_REPS, canonical, context_bootstrap, label,
                                                      _reject_constant, _strict_integers)
from research.evidence_comprehension_v2.probes import (CONDITIONS, GATE_PARTITION, PASSES, SET_FAMILIES, TRACKS,
                                                       response_schema)

REGRESSION_TOLERANCE = 0.05
PASS_IDS = ('pass_1', 'pass_2')
_VALIDATORS = {}


def validate(family, content):
    if family not in _VALIDATORS:
        _VALIDATORS[family] = Draft202012Validator(response_schema(family))
    value = json.loads(content, parse_constant=_reject_constant)
    errors = sorted(_VALIDATORS[family].iter_errors(value), key=lambda e: list(e.absolute_path))
    if errors:
        raise ValueError('schema: ' + errors[0].message[:100])
    _strict_integers(value)
    return value['answer']


def correct(family, answer, key):
    if family in SET_FAMILIES:
        return set(answer) == set(key)
    if family == 'tried_unchanged':
        return {canonical(a) for a in answer} == {canonical(a) for a in key}
    return answer == key


def score(probe, content):
    try:
        answer = validate(probe['family'], content)
    except (ValueError, TypeError) as exc:
        return {'probe_id': probe['probe_id'], 'valid': False, 'correct': False, 'error': str(exc)[:120]}
    duplicate = isinstance(answer, list) and len({canonical(a) for a in answer}) != len(answer)
    return {'probe_id': probe['probe_id'], 'valid': True, 'correct': correct(probe['family'], answer, probe['key']),
            'duplicate_items': duplicate, 'answer': answer}


# ------------------------------------------------------------------ outcomes

def outcome_fn(passes, partition):
    """'correct' / 'wrong' / 'missing' for one probe under this partition's repetition policy."""
    required = PASS_IDS[:PASSES[partition]]

    def outcome(probe):
        rows = [passes.get(i, {}).get(probe['probe_id']) for i in required]
        if any(r is None for r in rows):
            return 'missing'
        return 'correct' if all(r.get('correct') is True for r in rows) else 'wrong'
    return outcome


def best_shortcut(probes):
    counts = {}
    for p in probes:
        for name in p['shortcuts_correct']:
            counts[name] = counts.get(name, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return (ranked[0][0], round(ranked[0][1] / len(probes), 4)) if ranked else (None, 0.0)


def family_metrics(probes, outcome, seed):
    best = best_shortcut(probes)
    outcomes = [outcome(p) for p in probes]
    missing = outcomes.count('missing')
    hits = [o == 'correct' for o in outcomes]
    by_context = {}
    for p, hit in zip(probes, hits):
        by_context.setdefault(p['source_context'], []).append(int(hit))
    disagreement = [h for p, h in zip(probes, hits) if best[0] not in p['shortcuts_correct']]
    n = len(probes)
    accuracy = round(sum(hits) / n, 4) if n else None
    dis_acc = round(sum(disagreement) / len(disagreement), 4) if disagreement else None
    return {'n': n, 'answered': n - missing, 'missing': missing, 'correct': sum(hits), 'accuracy': accuracy,
            'contexts': len(by_context), 'contexts_all_correct': sum(all(v) for v in by_context.values()),
            'context_bootstrap_95': context_bootstrap(by_context, seed) if n and not missing else None,
            'best_shortcut': best[0], 'best_shortcut_accuracy': best[1],
            'shortcut_disagreement_n': len(disagreement), 'shortcut_disagreement_accuracy': dis_acc,
            'label': 'incomplete' if missing or not n else label(accuracy, len(disagreement), dis_acc, best[1])}


def paired_metrics(pairs, outcome, seed):
    """`pairs` is a list of (baseline probe, candidate probe) asking the same question about the same context."""
    counts = {'n': len(pairs), 'both': 0, 'improvements': 0, 'regressions': 0, 'neither': 0, 'incomplete': 0}
    by_context = {}
    for b, c in pairs:
        ob, oc = outcome(b), outcome(c)
        if 'missing' in (ob, oc):
            counts['incomplete'] += 1
            continue
        key = ('both' if ob == oc == 'correct' else 'improvements' if oc == 'correct'
               else 'regressions' if ob == 'correct' else 'neither')
        counts[key] += 1
        by_context.setdefault(b['source_context'], []).append((int(ob == 'correct'), int(oc == 'correct')))
    if counts['incomplete'] or not pairs:
        return {**counts, 'difference': None, 'difference_bootstrap_95': None}
    total = sum(len(v) for v in by_context.values())
    difference = sum(c - b for v in by_context.values() for b, c in v) / total
    contexts = sorted(by_context)
    rng = random.Random(seed)
    stats = []
    for _ in range(BOOTSTRAP_REPS):
        sample = [by_context[rng.choice(contexts)] for _ in contexts]
        n = sum(len(v) for v in sample)
        stats.append(sum(c - b for v in sample for b, c in v) / n)
    stats.sort()
    return {**counts, 'difference': round(difference, 4),
            'difference_bootstrap_95': [round(stats[int(0.025 * BOOTSTRAP_REPS)], 4),
                                        round(stats[int(0.975 * BOOTSTRAP_REPS) - 1], 4)]}


def track_verdict(track, families, paired):
    """Frozen decision for one track from withheld-partition family metrics and paired metrics."""
    names = (*TRACKS[track]['components'], *TRACKS[track]['targets'])
    targets = TRACKS[track]['targets']
    candidate = [c for c, t in CONDITIONS.items() if t == track][0]
    if any(f not in families.get(c, {}) or f not in paired for c in ('baseline', candidate) for f in names):
        return 'incomplete'
    base = {f: families['baseline'][f] for f in names}
    cand = {f: families[candidate][f] for f in names}
    if any(m['label'] == 'incomplete' for m in (*base.values(), *cand.values())) or any(
            paired[f]['incomplete'] for f in names):
        return 'incomplete'
    lower = {f: paired[f]['difference_bootstrap_95'][0] for f in names}
    upper = {f: paired[f]['difference_bootstrap_95'][1] for f in names}
    regressed = [f for f in names if upper[f] < 0 or cand[f]['accuracy'] < base[f]['accuracy'] - REGRESSION_TOLERANCE]
    improved = [f for f in targets if lower[f] > 0]
    if all(base[f]['label'] == 'criterion_met' for f in targets):
        return 'baseline_meets_criterion'
    if (all(cand[f]['label'] == 'criterion_met' for f in targets) and not regressed
            and all(base[f]['label'] == 'criterion_met' or lower[f] > 0 for f in targets)):
        return 'candidate_clear_improvement'
    if improved and regressed:
        return 'mixed'
    if improved:
        return 'improved_below_criterion'
    return 'no_clear_improvement'


def analyze(probes, passes):
    """`passes` maps 'pass_1' / 'pass_2' to {probe_id: score row}; a row exists only for a returned response."""
    if not isinstance(passes, dict) or set(passes) - set(PASS_IDS):
        raise ValueError('passes must be identified as ' + ', '.join(PASS_IDS))
    report = {'passes_present': [i for i in PASS_IDS if i in passes], 'families': {}, 'strata': {}, 'paired': {},
              'agreement': {}, 'verdicts': {}}
    groups, strata = {}, {}
    for p in probes:
        groups.setdefault((p['partition'], p['condition'], p['family']), []).append(p)
        for s in p['strata']:
            strata.setdefault((p['partition'], p['condition'], p['family'], s), []).append(p)
    outcomes = {part: outcome_fn(passes, part) for part in PASSES}
    for (part, cond, fam), group in sorted(groups.items()):
        report['families'].setdefault(part, {}).setdefault(cond, {})[fam] = family_metrics(
            group, outcomes[part], f'{part}/{cond}/{fam}')
    for (part, cond, fam, s), group in sorted(strata.items()):
        m = family_metrics(group, outcomes[part], f'{part}/{cond}/{fam}/{s}')
        report['strata'][f'{part}/{cond}/{fam}/{s}'] = {k: m[k] for k in ('n', 'missing', 'correct', 'accuracy')}
    by_pair = {}
    for p in probes:
        by_pair.setdefault(p['pair_id'], {})[p['condition']] = p
    for part in PASSES:
        for track in TRACKS:
            candidate = [c for c, t in CONDITIONS.items() if t == track][0]
            per_family = {}
            for pair in by_pair.values():
                if candidate in pair and pair['baseline']['partition'] == part:
                    per_family.setdefault(pair['baseline']['family'], []).append((pair['baseline'], pair[candidate]))
            report['paired'].setdefault(part, {})[track] = {
                f: paired_metrics(v, outcomes[part], f'paired/{part}/{track}/{f}') for f, v in sorted(per_family.items())}
    for (part, cond, fam), group in sorted(groups.items()):
        if PASSES[part] < 2:
            continue
        row = {'n': len(group), 'valid_pairs': 0, 'identical_answers': 0, 'missing_pairs': 0, 'invalid_pairs': 0}
        for p in group:
            pair = [passes.get(i, {}).get(p['probe_id']) for i in PASS_IDS]
            if any(r is None for r in pair):
                row['missing_pairs'] += 1
            elif not all(r.get('valid') is True for r in pair):
                row['invalid_pairs'] += 1
            else:
                row['valid_pairs'] += 1
                row['identical_answers'] += canonical(pair[0]['answer']) == canonical(pair[1]['answer'])
        report['agreement'][f'{part}/{cond}/{fam}'] = row
    gate = report['families'].get(GATE_PARTITION, {})
    for track in TRACKS:
        report['verdicts'][track] = track_verdict(track, gate, report['paired'][GATE_PARTITION][track])
    gated = [p for p in probes if p['partition'] == GATE_PARTITION]
    report['withheld_status'] = ('incomplete' if not gated or any(outcomes[GATE_PARTITION](p) == 'missing' for p in gated)
                                 else 'complete')
    return report
