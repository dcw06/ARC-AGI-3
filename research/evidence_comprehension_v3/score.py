"""Scoring and frozen decision rules for evidence comprehension v3 (revision 2).

Validation, per-family labels, both-correct scoring over two identified withheld passes, the context-resampling
bootstrap and the 0.05 regression tolerance are v2's, imported unchanged. The verdict order is v2's:
incomplete; baseline_meets_criterion (here: the reference meets the criterion); candidate_clear_improvement;
mixed; improved_below_criterion; no_clear_improvement. Track B's verdicts carry the suffix `_tool_assisted`.

Only original-variant withheld questions enter a verdict. The matched synthetic counterfactual histories give a
secondary, non-gating comparison per control condition (`history_alteration`): original against counterfactual on
the same questions, with improvements meaning the answer was right only after ACTION6 left the history. Matched
variants are resampled together by their original context.

Completeness has three separate levels (revision 2, review of b9ac66f):
- primary, per track: every withheld original-variant question of the track answered in both passes. A track's
  verdict is decided only by its own primary questions; an incomplete primary makes that verdict `incomplete`.
- secondary: every withheld history-alteration pair (original and counterfactual, both passes) answered.
- schedule: every scheduled question answered as the repetition policy requires (withheld twice; development and
  transfer once), and, separately, the withheld partition alone.
Policy: the history alteration is non-gating. A complete primary result may therefore support promotion when the
secondary comparison is incomplete; the report states the secondary status, and an incomplete secondary
comparison is reported as incomplete, never as evidence for or against history interference.
"""
from research.evidence_comprehension_v2.score import (PASS_IDS, REGRESSION_TOLERANCE, family_metrics,  # noqa: F401
                                                      outcome_fn, paired_metrics, score, validate)
from research.evidence_comprehension_v3.probes import GATE_PARTITION, PASSES, TRACKS


def track_verdict(track, families, paired):
    spec = TRACKS[track]
    names = (*spec['components'], *spec['targets'])
    targets = spec['targets']
    ref, cand = spec['reference'], spec['candidate']

    def verdict():
        if any(f not in families.get(c, {}) or f not in paired for c in (ref, cand) for f in names):
            return 'incomplete'
        base = {f: families[ref][f] for f in names}
        new = {f: families[cand][f] for f in names}
        if any(m['label'] == 'incomplete' for m in (*base.values(), *new.values())) or any(
                paired[f]['incomplete'] for f in names):
            return 'incomplete'
        lower = {f: paired[f]['difference_bootstrap_95'][0] for f in names}
        upper = {f: paired[f]['difference_bootstrap_95'][1] for f in names}
        regressed = [f for f in names if upper[f] < 0 or new[f]['accuracy'] < base[f]['accuracy'] - REGRESSION_TOLERANCE]
        improved = [f for f in targets if lower[f] > 0]
        if all(base[f]['label'] == 'criterion_met' for f in targets):
            return 'baseline_meets_criterion'
        if (all(new[f]['label'] == 'criterion_met' for f in targets) and not regressed
                and all(base[f]['label'] == 'criterion_met' or lower[f] > 0 for f in targets)):
            return 'candidate_clear_improvement'
        if improved and regressed:
            return 'mixed'
        if improved:
            return 'improved_below_criterion'
        return 'no_clear_improvement'
    return verdict() + spec['suffix']


def analyze(probes, passes):
    if not isinstance(passes, dict) or set(passes) - set(PASS_IDS):
        raise ValueError('passes must be identified as ' + ', '.join(PASS_IDS))
    outcomes = {part: outcome_fn(passes, part) for part in PASSES}
    report = {'passes_present': [i for i in PASS_IDS if i in passes], 'families': {}, 'strata': {}, 'paired': {},
              'history_alteration': {}, 'agreement': {}, 'verdicts': {}}
    groups, strata = {}, {}
    for p in probes:
        groups.setdefault((p['partition'], p['variant'], p['condition'], p['family']), []).append(p)
        for s in p['strata']:
            strata.setdefault((p['partition'], p['variant'], p['condition'], p['family'], s), []).append(p)
    for (part, variant, cond, fam), group in sorted(groups.items()):
        report['families'].setdefault(part, {}).setdefault(variant, {}).setdefault(cond, {})[fam] = family_metrics(
            group, outcomes[part], f'{part}/{variant}/{cond}/{fam}')
    for (part, variant, cond, fam, s), group in sorted(strata.items()):
        m = family_metrics(group, outcomes[part], f'{part}/{variant}/{cond}/{fam}/{s}')
        report['strata'][f'{part}/{variant}/{cond}/{fam}/{s}'] = {k: m[k] for k in ('n', 'missing', 'correct', 'accuracy')}
    by_pair, by_variant = {}, {}
    for p in probes:
        by_pair.setdefault(p['pair_id'], {})[p['role']] = p
        by_variant.setdefault(p['variant_pair_id'], {})[p['variant']] = p
    for part in PASSES:
        for track in TRACKS:
            per_family = {}
            for pair in by_pair.values():
                ref = pair.get('reference')
                if ref and ref['partition'] == part and ref['track'] == track and ref['variant'] == 'original':
                    per_family.setdefault(ref['family'], []).append((ref, pair['candidate']))
            report['paired'].setdefault(part, {})[track] = {
                f: paired_metrics(v, outcomes[part], f'paired/{part}/{track}/{f}') for f, v in sorted(per_family.items())}
        per_condition = {}
        for pair in by_variant.values():
            if 'counterfactual' in pair and pair['original']['partition'] == part:
                o = pair['original']
                per_condition.setdefault(o['condition'], {}).setdefault(o['family'], []).append((o, pair['counterfactual']))
        report['history_alteration'][part] = {
            cond: {f: paired_metrics(v, outcomes[part], f'alteration/{part}/{cond}/{f}') for f, v in sorted(fams.items())}
            for cond, fams in sorted(per_condition.items())}
    for (part, variant, cond, fam), group in sorted(groups.items()):
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
                row['identical_answers'] += pair[0].get('answer') == pair[1].get('answer')
        report['agreement'][f'{part}/{variant}/{cond}/{fam}'] = row
    gate = report['families'].get(GATE_PARTITION, {}).get('original', {})
    for track in TRACKS:
        report['verdicts'][track] = track_verdict(track, gate, report['paired'].get(GATE_PARTITION, {}).get(track, {}))
    report['completeness'] = completeness(probes, outcomes)
    return report


def completeness(probes, outcomes):
    def status(group):
        return 'incomplete' if not group or any(outcomes[p['partition']](p) == 'missing' for p in group) else 'complete'
    withheld = [p for p in probes if p['partition'] == GATE_PARTITION]
    paired_sources = {p['source_context'] for p in withheld if p['variant'] == 'counterfactual'}
    secondary = [p for p in withheld if p['track'] == 'control' and p['source_context'] in paired_sources]
    return {'primary': {track: status([p for p in withheld if p['track'] == track and p['variant'] == 'original'])
                        for track in TRACKS},
            'secondary_history_alteration': status(secondary),
            'withheld_schedule': status(withheld),
            'whole_schedule': status(probes),
            'policy': 'verdicts depend only on primary completeness; the history alteration is non-gating'}
