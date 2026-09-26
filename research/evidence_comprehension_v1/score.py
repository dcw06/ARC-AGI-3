"""Scoring and analysis for evidence comprehension v1 (revision 2).

Every response is first validated against the family's complete response schema by an independent
JSON Schema validator (length, numeric bounds, required and forbidden properties, enumerations).
Only a schema-valid response is scored semantically; integers must be real JSON integers, not
booleans or floats. Within the schema, lists are compared as sets and duplicates are recorded.

Analysis labels are operational: `criterion_met`, `below_accuracy_floor`, `inconclusive`,
`not_diagnostic` or `incomplete`. They describe this diagnostic's criterion only, never general
comprehension. A missing answer (no returned response) or a missing pass makes a result
`incomplete`; absence is never scored as success. The gate needs two identified passes. Question-level results are
clustered by context, so intervals are descriptive (a context-resampling bootstrap), and the gate
rests on point accuracy plus accuracy on questions where the family's most accurate shortcut answers
wrongly. A constant shortcut cannot pass: it would need 90% overall, which only a non-diagnostic
family (best shortcut >= 90%) allows.
"""
import json
import math
import random

from jsonschema import Draft202012Validator

from research.evidence_comprehension_v1.probes import GATE_CONDITION, MATCHED, response_schema

ACCURACY_FLOOR = 0.70
CRITERION = 0.90
MIN_SHORTCUT_DISAGREEMENT = 10
NON_DIAGNOSTIC = 0.90  # a family whose best shortcut reaches this is reported, never labelled
BOOTSTRAP_REPS = 2000
_VALIDATORS = {}


def _reject_constant(value):
    raise ValueError('non-finite number ' + value)


def _strict_integers(value):
    """JSON Schema accepts 6.0 as an integer; answers must use real integers (and never booleans)."""
    if isinstance(value, float):
        raise ValueError('float where an integer or string is required')
    if isinstance(value, dict):
        for item in value.values():
            _strict_integers(item)
    if isinstance(value, list):
        for item in value:
            _strict_integers(item)


def validate(family, content):
    """Parse and schema-validate one response; returns the answer or raises ValueError."""
    if family not in _VALIDATORS:
        _VALIDATORS[family] = Draft202012Validator(response_schema(family))
    value = json.loads(content, parse_constant=_reject_constant)
    errors = sorted(_VALIDATORS[family].iter_errors(value), key=lambda e: list(e.absolute_path))
    if errors:
        raise ValueError('schema: ' + errors[0].message[:100])
    _strict_integers(value)
    return value['answer']


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def correct(family, answer, key):
    if family in ('available_actions', 'coordinate_actions'):
        return set(answer) == set(key)
    if family == 'tried_unchanged':
        return {canonical(a) for a in answer} == {canonical(a) for a in key}
    return answer == key


def score(probe, content):
    try:
        answer = validate(probe['family'], content)
    except (ValueError, TypeError) as exc:  # json.JSONDecodeError is a ValueError
        return {'probe_id': probe['probe_id'], 'valid': False, 'correct': False, 'error': str(exc)[:120]}
    duplicate = isinstance(answer, list) and len({canonical(a) for a in answer}) != len(answer)
    return {'probe_id': probe['probe_id'], 'valid': True, 'correct': correct(probe['family'], answer, probe['key']),
            'duplicate_items': duplicate, 'answer': answer}


# ------------------------------------------------------------------ analysis

def label(accuracy, disagreement_n, disagreement_accuracy, best_shortcut=0.0):
    if best_shortcut >= NON_DIAGNOSTIC:
        return 'not_diagnostic'
    if accuracy is None:
        return 'inconclusive'
    if accuracy < ACCURACY_FLOOR:
        return 'below_accuracy_floor'
    if (accuracy >= CRITERION and disagreement_n >= MIN_SHORTCUT_DISAGREEMENT
            and disagreement_accuracy is not None and disagreement_accuracy >= CRITERION):
        return 'criterion_met'
    return 'inconclusive'


def context_bootstrap(outcomes, seed):
    """Descriptive 95% interval resampling whole contexts. `outcomes` maps context -> [0/1 per question]."""
    contexts = sorted(outcomes)
    if not contexts:
        return None
    rng = random.Random(seed)
    stats = []
    for _ in range(BOOTSTRAP_REPS):
        sample = [outcomes[rng.choice(contexts)] for _ in contexts]
        n = sum(len(s) for s in sample)
        stats.append(sum(sum(s) for s in sample) / n)
    stats.sort()
    return [round(stats[int(0.025 * BOOTSTRAP_REPS)], 4), round(stats[int(0.975 * BOOTSTRAP_REPS) - 1], 4)]


def best_shortcuts(probes):
    """(condition, family) -> (name, accuracy) of the most accurate shortcut; ties go to the first name."""
    best = {}
    for key, row in shortcut_baselines(probes).items():
        condition, family = key.split('/')
        ranked = sorted(row['shortcuts'].items(), key=lambda item: (-item[1], item[0]))
        best[(condition, family)] = ranked[0] if ranked else (None, 0.0)
    return best


def group_metrics(probes, outcome_of, seed, best):
    """Metrics for one group of probes. `outcome_of(probe)` returns 'correct', 'wrong' or 'missing' (no returned
    response). Any missing answer makes the group `incomplete`: absence is never scored as success or failure.
    `best` is the (name, accuracy) of this condition/family's most accurate shortcut."""
    n = len(probes)
    outcomes = [outcome_of(p) for p in probes]
    if any(o not in ('correct', 'wrong', 'missing') for o in outcomes):
        raise ValueError('unknown outcome')
    hits = [o == 'correct' for o in outcomes]
    missing = outcomes.count('missing')
    by_context = {}
    for p, hit in zip(probes, hits):
        by_context.setdefault(p['context_id'], []).append(int(hit))
    disagreement = [hit for p, hit in zip(probes, hits) if best[0] not in p['shortcuts_correct']]
    accuracy = round(sum(hits) / n, 4) if n else None
    dis_acc = round(sum(disagreement) / len(disagreement), 4) if disagreement else None
    return {'n': n, 'answered': n - missing, 'missing': missing, 'correct': sum(hits),
            'accuracy': accuracy, 'context_bootstrap_95': context_bootstrap(by_context, seed) if not missing else None,
            'contexts': len(by_context), 'contexts_all_correct': sum(all(v) for v in by_context.values()),
            'best_shortcut': best[0], 'best_shortcut_accuracy': best[1],
            'shortcut_disagreement_n': len(disagreement), 'shortcut_disagreement_accuracy': dis_acc,
            'label': 'incomplete' if missing or not n else label(accuracy, len(disagreement), dis_acc, best[1])}


PASS_IDS = ('pass_1', 'pass_2')


def analyze(probes, passes):
    """`passes` maps an identified pass ('pass_1', 'pass_2') to {probe_id: score row}; a row exists only for a
    returned response. The final gate requires both identified passes with every gated probe answered in each;
    otherwise it is `incomplete`. Single-pass results are diagnostics only. Invalid answers count as wrong."""
    if not isinstance(passes, dict) or set(passes) - set(PASS_IDS):
        raise ValueError('passes must be identified as ' + ', '.join(PASS_IDS))
    missing_passes = [p for p in PASS_IDS if p not in passes]

    def single(results):
        def outcome(p):
            row = results.get(p['probe_id'])
            return 'missing' if row is None else 'correct' if row.get('correct') is True else 'wrong'
        return outcome

    def joint(p):
        if missing_passes:
            return 'missing'
        rows = [passes[i].get(p['probe_id']) for i in PASS_IDS]
        if any(r is None for r in rows):
            return 'missing'
        return 'correct' if all(r.get('correct') is True for r in rows) else 'wrong'

    best = best_shortcuts(probes)
    groups = {}
    for p in probes:
        groups.setdefault((p['condition'], p['family']), []).append(p)
        for s in p['strata']:
            groups.setdefault((p['condition'], p['family'], s), []).append(p)
    report = {'passes_present': [i for i in PASS_IDS if i in passes], 'passes_missing': missing_passes,
              'single_pass_diagnostics': {}, 'both_correct': {}, 'agreement': {}, 'matched': {}}
    for index in report['passes_present']:
        results = passes[index]
        report['single_pass_diagnostics'][index] = {
            'answered': sum(p['probe_id'] in results for p in probes),
            'invalid': sum(results.get(p['probe_id'], {'valid': True}).get('valid') is False for p in probes),
            'groups': {'/'.join(k): group_metrics(v, single(results), f'{index}:{"/".join(k)}', best[k[:2]])
                       for k, v in sorted(groups.items())}}
    report['both_correct'] = {'/'.join(k): group_metrics(v, joint, 'both:' + '/'.join(k), best[k[:2]])
                              for k, v in sorted(groups.items())}
    for k, v in sorted(groups.items()):
        if len(k) != 2:
            continue
        row = {'n': len(v), 'valid_pairs': 0, 'identical_answers': 0, 'missing_pairs': 0, 'invalid_pairs': 0}
        for p in v:
            pair = [passes[i].get(p['probe_id']) if i in passes else None for i in PASS_IDS]
            if any(r is None for r in pair):
                row['missing_pairs'] += 1
            elif not all(r.get('valid') is True for r in pair):
                row['invalid_pairs'] += 1
            else:
                row['valid_pairs'] += 1
                row['identical_answers'] += canonical(pair[0]['answer']) == canonical(pair[1]['answer'])
        report['agreement']['/'.join(k)] = row
    report['gate'] = {k.split('/')[1]: m['label'] for k, m in report['both_correct'].items()
                      if k.startswith(GATE_CONDITION + '/') and k.count('/') == 1}
    gated = [p for p in probes if p['condition'] == GATE_CONDITION]
    report['gate_status'] = ('incomplete' if not gated or any(joint(p) == 'missing' for p in gated) else 'complete')
    by_id = {p['probe_id']: p for p in probes}
    for first, second in MATCHED:
        table = {}
        for p in probes:
            if p['condition'] != first:
                continue
            twin = by_id.get(p['probe_id'].replace(first + ':', second + ':', 1))
            if twin is None or twin['key'] != p['key']:
                raise ValueError('matched probe missing or keyed differently: ' + p['probe_id'])
            row = table.setdefault(p['family'], {'n': 0, 'both': 0, f'only_{first}': 0, f'only_{second}': 0,
                                                 'neither': 0, 'incomplete': 0})
            a, b = joint(p), joint(twin)
            row['n'] += 1
            if 'missing' in (a, b):
                row['incomplete'] += 1
            else:
                row['both' if a == b == 'correct' else f'only_{first}' if a == 'correct'
                    else f'only_{second}' if b == 'correct' else 'neither'] += 1
        report['matched'][f'{first}_vs_{second}'] = table
    return report


def shortcut_baselines(probes):
    """Accuracy each named shortcut would achieve, by condition and family."""
    table = {}
    for p in probes:
        names = table.setdefault(f"{p['condition']}/{p['family']}", {'n': 0, 'best_shortcut': None, 'shortcuts': {}})
        names['n'] += 1
        for name in p['shortcuts_correct']:
            names['shortcuts'][name] = names['shortcuts'].get(name, 0) + 1
    for row in table.values():
        rates = {k: round(v / row['n'], 4) for k, v in row['shortcuts'].items()}
        row['shortcuts'] = rates
        row['best_shortcut'] = max(rates.values(), default=0.0)
    return dict(sorted(table.items()))


def wilson(k, n, z=1.96):
    """Question-level interval, descriptive only (questions share contexts)."""
    if n == 0:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(centre - half, 4), round(centre + half, 4)]
