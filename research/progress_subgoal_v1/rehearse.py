"""CPU rehearsals with scripted answers for progress_subgoal_v1 (DRAFT; no model, no network, no GPU).

The decision-shaped `coverage_dryrun` build stands in for the evaluation partition (which does not exist until the
freeze). Every scripted response passes through the same text path a model response would: it is written to an
append-only JSON-lines log, read back by score.load_log, and scored. Invalid outputs are retained in the report.

Rehearsals use the two primary arms (protocol v1). Also: workload and runtime estimates for the two-arm design, the
optional three-arm design and development. Prompt tokens are calibrated on the WS3 exact token audit
(reports/ws3_questionnaire_token_audit.json, read-only) as characters per token; runtime uses the per-call fit to
evidence_comprehension_v3's measured calls recorded in that audit. Estimates only: the exact tokenizer audit is a
freeze requirement.

Usage: python -m research.progress_subgoal_v1.rehearse [--write]
"""
import argparse
import hashlib
import json
from pathlib import Path

from research.progress_subgoal_v1 import questions as Q, score as SC

OUTPUT = Path(__file__).with_name('rehearsal_results.json')
PARTITION = 'coverage_dryrun'
ROOT = Path(__file__).resolve().parents[2]
OVER_CLAIM_SHORTCUTS = ('change_or_subgoal_as_progress', 'over_claim', 'change_means_useful', 'consistency_as_cause',
                        'consistent_trials_as_strengthened', 'any_returned_frame_counts', 'never_uncertain')


def answer(value):
    return json.dumps({'answer': value}, separators=(',', ':'))


def _hit(probe, salt, rate):
    return int(hashlib.sha256(f"{salt}:{probe['probe_id']}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < rate


POLICIES = {
    # the key everywhere
    'oracle': lambda p, i: answer(p['key']),
    # every predeclared over-claiming shortcut that the family has, otherwise the key
    'over_claimer': lambda p, i: answer(next((p['shortcut_answers'][n] for n in OVER_CLAIM_SHORTCUTS
                                              if n in p['shortcut_answers']), p['key'])),
    # always the uncertain answer where the family has one (the avoidance strategy)
    'always_uncertain': lambda p, i: answer(Q.UNCERTAIN.get(p['family'], p['key'])),
    # nothing parses
    'invalid_text': lambda p, i: 'I think the answer is probably yes.',
    # schema faults: an extra field, an answer outside the enumeration, NaN, a list
    'schema_faults': lambda p, i: [json.dumps({'answer': p['key'], 'why': 'x'}), answer('maybe'), '{"answer": NaN}',
                                   '["supported"]'][int(hashlib.sha256(p['probe_id'].encode()).hexdigest(), 16) % 4],
    # the key, with 3% of responses invalid (deterministically chosen) in pass 2 only
    'oracle_3pct_invalid_pass2': lambda p, i: '```json' if i == 'pass_2' and _hit(p, 'inv', 0.03) else answer(p['key']),
    # malformed output on exactly the over-claim gates' member questions, the key elsewhere (revision r1): must not
    # look safe; it fails the gate-member validity criterion
    'gate_questions_invalid': lambda p, i: ('I cannot determine that.' if any(Q.gate_member(g, p) for g in
                                                                              Q.OVER_CLAIM_GATES) else answer(p['key'])),
    # the treatment-difference rehearsal: computed answers the key, safeguard hedges (raw over-claims, if built)
    'condition_contrast': lambda p, i: POLICIES[{'raw_evidence': 'over_claimer', 'raw_plus_computed_record': 'oracle',
                                                 'raw_plus_computed_record_plus_safeguard': 'always_uncertain'}[
                                                     p['condition']]](p, i),
}


def write_log(value, policy, drop=()):
    """The append-only log text for one scripted run, in schedule order. `drop` skips (pass, probe_id) entries."""
    by_id = {p['probe_id']: p for p in value['probes']}
    lines = []
    for block in value['schedule']:
        for pid in block['probe_ids']:
            if (block['pass'], pid) in drop:
                continue
            lines.append(json.dumps({'pass': block['pass'], 'probe_id': pid,
                                     'content': POLICIES[policy](by_id[pid], block['pass'])}, sort_keys=True))
    return ''.join(line + '\n' for line in lines)


def summary(report):
    """The parts of a report a reviewer checks first."""
    out = {'readiness': {c: r['status'] for c, r in report['readiness'].items()}, 'completeness': report['completeness'],
           'gates': {c: {g: [row['status'], row['over_claim_contexts'], row['denominator_contexts']]
                         for g, row in gates.items()} for c, gates in report['over_claims'].items()},
           'validity': {c: {k: [v[k]['status'], v[k]['invalid'], v[k]['responses']]
                            for k in ('all_responses', 'gate_member_responses')} for c, v in report['validity'].items()},
           'readiness_problems': {c: r.get('problems', [r.get('reason')])[:4] for c, r in report['readiness'].items()},
           'uncertainty': {c: [u['uncertain_keyed']['recall'], u['definite_keyed']['over_hedge_rate']]
                           for c, u in report['uncertainty'].items()},
           'labels': {c: {f: m['label'] for f, m in fams.items()} for c, fams in report['families'].items()},
           'subgoal': {c: [s['success_detection']['accuracy'], s['abandonment_after_disconfirmation']['accuracy'],
                           s['abandonment_after_disconfirmation']['persisted_with_continue']]
                       for c, s in report['subgoal'].items()},
           'invalid_counts': {c: r['count'] for c, r in report['invalid'].items()},
           'findings': {k: {kk: vv for kk, vv in v.items() if kk in ('improved', 'regressed')}
                        for k, v in report['findings'].items()}}
    return out


def run():
    value = Q.build(PARTITION)
    probes = value['probes']
    results = {'version': Q.VERSION, 'partition': PARTITION, 'note': 'scripted answers only; no model was called',
               'scoring_revision': 'r2: over-claim gates read valid answers only; invalid output counts as incorrect '
                                   f'and against validity (overall <= {SC.INVALID_RATE_CAP}, gate-member <= '
                                   f'{SC.GATE_MEMBER_INVALID_RATE_CAP}); false "no progress" is a readiness gate '
                                   f"(floor {Q.GATE_FLOORS['false_no_progress']} contexts)",
               'coverage': Q.coverage(probes, PARTITION, strict=False), 'runs': {}}
    retained = {}
    for policy in POLICIES:
        text = write_log(value, policy)
        passes, log = SC.load_log(text, probes)
        report = SC.analyze(probes, passes, PARTITION, recovered=log['recovered'])
        results['runs'][policy] = {'log_sha256': hashlib.sha256(text.encode()).hexdigest(), 'log': log,
                                   **summary(report)}
        if policy in ('invalid_text', 'schema_faults', 'oracle_3pct_invalid_pass2', 'gate_questions_invalid'):
            retained[policy] = report['invalid'][Q.CONDITIONS[0]]['retained'][:5]
        if policy == 'oracle':
            # rescoring the retained log reproduces the report exactly
            again = SC.analyze(probes, SC.load_log(text, probes)[0], PARTITION)
            results['runs'][policy]['rescore_identical'] = again == report
            # an interrupted final append: recovered, never eligible
            cut = text[:-40]
            p2, log2 = SC.load_log(cut, probes)
            results['runs']['oracle_interrupted_append'] = {'log': log2, **summary(
                SC.analyze(probes, p2, PARTITION, recovered=log2['recovered']))}
            # one gate question missing from pass 2: incomplete
            gate_probe = next(p for p in probes if Q.gate_member('false_progress', p))
            p3, _ = SC.load_log(write_log(value, 'oracle', drop={('pass_2', gate_probe['probe_id'])}), probes)
            results['runs']['oracle_missing_one_gate_answer'] = summary(SC.analyze(probes, p3, PARTITION))
            # a malformed line before the end refuses the whole log
            lines = text.split('\n')
            lines[5] = lines[5][:-3]
            try:
                SC.load_log('\n'.join(lines), probes)
                results['runs']['corrupt_middle_line'] = 'accepted (unexpected)'
            except ValueError as exc:
                results['runs']['corrupt_middle_line'] = f'refused: {exc}'[:120]
    results['retained_invalid_examples'] = retained
    results['workload_estimate'] = workload(value)
    return results


def _phases(v, ratio):
    """[(phase, [estimated prompt tokens per scheduled call])] in schedule order."""
    by_id = {p['probe_id']: p for p in v['probes']}
    size = {}
    out = []
    for block in v['schedule']:
        tokens = []
        for pid in block['probe_ids']:
            if pid not in size:
                size[pid] = len(json.dumps(Q.build_request(v, by_id[pid])['messages'])) / ratio
            tokens.append(size[pid])
        out.append((f"{block['partition']}/{block['pass']}", tokens))
    return out


def workload(value):
    """Calls, estimated prompt tokens and runtime scenarios for the evaluation-shaped design (two primary arms), the
    optional three-arm design, and development (two arms, one pass). Runtime uses the per-call least-squares fit to
    evidence_comprehension_v3's measured cache-disabled calls and WS3's overhead method (worse of v2 and v3 per
    component; allowances), both read from reports/ws3_questionnaire_token_audit.json. Estimates, not guarantees."""
    ratio = chars_per_token()
    audit = json.loads((ROOT / 'reports/ws3_questionnaire_token_audit.json').read_text(encoding='utf-8'))
    fit, scen = audit['measurements'], audit['runtime_scenarios']
    completion = min(32, 2 * max(r['key_completion_tokens'] for r in audit['requests']))  # WS3's key x 2 slack
    per_call = lambda t: (fit['fit_seconds_per_call'] + fit['fit_seconds_per_prompt_token'] * t  # noqa: E731
                          + fit['fit_seconds_per_completion_token'] * completion)
    designs = {'primary_two_arms': (value, _phases(value, ratio)),
               'optional_three_arms': (None, _phases(Q.build(PARTITION, conditions=Q.ALL_CONDITIONS), ratio)),
               'development_two_arms': (None, _phases(Q.build('development'), ratio))}
    est = {'chars_per_token_calibration': ratio, 'completion_tokens_assumed': completion,
           'fit_source': fit['source'], 'fit_calls': fit['calls'],
           'fit': {k: fit[k] for k in ('fit_seconds_per_call', 'fit_seconds_per_prompt_token',
                                       'fit_seconds_per_completion_token')},
           'overhead_measured_seconds': scen['first_cell_overhead_measured_seconds'],
           'overhead_allowance_seconds': scen['first_cell_overhead_allowance_seconds'],
           'admission_cutoff_seconds': scen['admission_cutoff_seconds'], 'designs': {}}
    for name, (_, phases) in designs.items():
        tokens = [t for _, ts in phases for t in ts]
        row = {'calls': len(tokens), 'estimated_prompt_tokens': round(sum(tokens)),
               'estimated_mean_prompt_tokens': round(sum(tokens) / len(tokens)),
               'estimated_largest_prompt_tokens': round(max(tokens)),
               'question_seconds_at_fit': round(sum(per_call(t) for t in tokens)), 'scenarios': {}}
        if name != 'development_two_arms':
            for label, overhead, factor in (('measured_overhead_fit_rates', 'overhead_measured_seconds', 1.0),
                                            ('allowance_overhead_fit_rates', 'overhead_allowance_seconds', 1.0),
                                            ('allowance_overhead_two_times_slower', 'overhead_allowance_seconds', 2.0)):
                o = est[overhead]
                elapsed = o['installation'] + o['model_startup'] + o['other_pre_question']
                s = {'questions_start_seconds': round(elapsed)}
                for phase, ts in phases:
                    elapsed += factor * sum(per_call(t) for t in ts)
                    s[phase + '_ends_at_seconds'] = round(elapsed)
                s['decision_fits_admission_cutoff'] = elapsed <= est['admission_cutoff_seconds']
                row['scenarios'][label] = s
        est['designs'][name] = row
    est['note'] = ('estimate: prompt tokens = characters / (characters per token measured on WS3 development requests '
                   'with the pinned tokenizer); runtime = v3 fit, measured on shorter prompts (mean about 740 tokens), '
                   'so per-token cost is extrapolated. The exact tokenizer audit is required before freeze.')
    return est


def chars_per_token():
    """Characters per token over the WS3 development requests, using WS3's exact audit (read-only)."""
    from research.transition_evidence_v1 import questionnaire as WQ
    audit = json.loads((ROOT / 'reports/ws3_questionnaire_token_audit.json').read_text(encoding='utf-8'))
    cases = {c['case_id']: c for c in WQ.cases('development')}
    chars = tokens = 0
    for row in audit['requests']:
        if row['partition'] != 'development':
            continue
        cid = row['probe_id'].split(':')[2]
        family_arg = row['probe_id'].split(':')[3:]
        case = cases[cid]
        arg = family_arg[1] if len(family_arg) > 1 else None
        view = WQ.present(case['raw'], case['record'], row['condition'])
        probe = {'family': family_arg[0], 'question': WQ.question_text(family_arg[0], arg)}
        chars += len(json.dumps(WQ.build_request(view, probe)['messages']))
        tokens += row['prompt_tokens']
    return round(chars / tokens, 4)


def encode(value):
    return (json.dumps(value, indent=1, sort_keys=True) + '\n').encode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    out = encode(run())
    if parser.parse_args().write:
        OUTPUT.write_bytes(out)
    print(hashlib.sha256(out).hexdigest(), len(out))
