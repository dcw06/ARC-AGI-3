"""Compare the two locked agent roles against the original frames, case by case.

Role 1 named uncertainties and the past actions that address them. Role 2 read the rendered pack.
This script checks what can be checked mechanically:
  - every action role 1 cites exists at or before the decision;
  - for uncertainties about what completed a level, which cited actions really are level-completing ones;
  - whether the pack's records are among role 1's cited actions and whether the pack holds a whole
    sufficient group (ignoring the two recent actions, which are already in the decision-time input);
  - for each sufficient group role 1 listed, the size of a B version 2 pack holding its older records.
Judgements that need reading are made in the report, not here.

Usage: agent_review_compare.py <events.jsonl> <cases_frozen.json> <agent_review_dir>
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import formats_v2 as F, records  # noqa: E402
from complete_evidence_v1.opus_count import OpusCounter  # noqa: E402

ALLOWANCE = 2048


def numbers(value):
    out = set()
    if isinstance(value, bool):
        return out
    if isinstance(value, int):
        out.add(value)
    elif isinstance(value, str):
        out.update(int(m) for m in re.findall(r'\ba?0*(\d{1,3})\b', value))
    elif isinstance(value, list):
        for v in value:
            out |= numbers(v)
    return out


def main(events_path, cases_path, review_dir):
    review = Path(review_dir)
    frozen = {c['case']: c for c in json.loads(Path(cases_path).read_text())['cases']}
    key = json.loads((review / 'sealed/key_from_frames.json').read_text())
    scores = json.loads((review / 'role2_scores.json').read_text())
    games = {k.split('-')[0]: v for k, v in records.load_run(events_path).items()}
    counter = OpusCounter()
    out = {}
    for name, truth in key.items():
        case = frozen[name]
        recs = games[case['game']]['records']
        decision = case['decision_after_actions']
        current = recs[decision - 1]['response_frames'][-1]
        level_ups = {r['event_seq'] for r in recs[:decision] if r['level_after'] > r['level_observed']}
        recent = {decision - 1, decision}
        pack = [r['action_number'] for r in truth['records']]
        one = json.loads((review / 'submissions/role1' / ('%s_stage1.json' % name)).read_text())
        two = json.loads((review / 'submissions/role1' / ('%s_stage2.json' % name)).read_text())
        text = {u['id']: u['uncertainty'] for u in one['uncertainties']}
        rows = []
        for pu in two['per_uncertainty']:
            cited = set()
            for o in pu.get('observations', []):
                cited |= numbers(o.get('action'))
            groups = [sorted(numbers(g)) for g in pu.get('sufficient_groups', []) if numbers(g)]
            bad = sorted(a for a in cited | {a for g in groups for a in g} if a < 0 or a > decision)
            about_level = bool(re.search(r'complet', text.get(pu['id'], ''), re.I))
            group_sizes = []
            for g in groups:
                older = [a for a in g if 1 <= a <= decision and a not in recent]
                if not older or len(older) > 8:
                    group_sizes.append({'group': g, 'older_records': older, 'pack_tokens': None,
                                        'note': 'only recent actions' if not older else 'more than 8 records, not rendered'})
                    continue
                chosen = [recs[a - 1] for a in older]
                texts = [F.m_ref2(r, current) for r in chosen]
                tokens = counter.count(F.pack_b2(case['game'], chosen[0]['trajectory_id'], decision, chosen, texts),
                                       'agent review %s %s group %s' % (name, pu['id'], '-'.join(map(str, older))))
                group_sizes.append({'group': g, 'older_records': older, 'pack_tokens': tokens, 'fits_2048': tokens <= ALLOWANCE})
            fitting = [g for g in group_sizes if g.get('fits_2048')]
            rows.append({
                'id': pu['id'], 'uncertainty': text.get(pu['id'], ''), 'older_evidence_found_by_role1': pu.get('older_evidence_found'),
                'cited_actions': sorted(cited), 'sufficient_groups': groups, 'cited_actions_out_of_range': bad,
                'about_level_completion': about_level,
                'cited_actions_that_completed_a_level': sorted(cited & level_ups) if about_level else None,
                'pack_records_cited': [a for a in pack if a in cited],
                'pack_holds_a_whole_sufficient_group': any(set(a for a in g if a not in recent) <= set(pack) and
                                                           any(a not in recent for a in g) for g in groups),
                'pack_records_in_some_group': [a for a in pack if any(a in g for g in groups)],
                'groups_rendered_as_B2': group_sizes,
                'smallest_fitting_group': min(fitting, key=lambda g: g['pack_tokens']) if fitting else None,
                'what_the_evidence_supports': pu.get('what_the_evidence_supports', ''), 'limits': pu.get('limits', '')})
        s = scores[name]
        out[name] = {'game': case['game'], 'type': case['type'], 'decision': decision, 'pack_records': pack,
                     'pack_opus_tokens': truth['pack_opus_tokens'], 'pack_fits_2048': truth['pack_fits_2048'],
                     'level_completing_actions_in_history': sorted(level_ups),
                     'role2_checks': '%d/%d' % (s['correct'], s['checks']), 'role2_wrong': s['wrong'],
                     'role2_cannot_determine': s['cannot_determine'], 'uncertainties': rows,
                     'pack_relevant_to': [r['id'] for r in rows if r['pack_records_cited']],
                     'pack_complete_for': [r['id'] for r in rows if r['pack_holds_a_whole_sufficient_group']],
                     'role1_coverage': two.get('coverage'), 'role1_needs_no_record_can_meet': two.get('needs_no_past_record_can_meet', '')}
    (review / 'comparison.json').write_text(json.dumps(out, indent=1))
    for name, c in out.items():
        print('\n%s %s %s | pack %s %s tok fits=%s | role2 %s | relevant to %s | complete for %s' % (
            name, c['game'], c['type'], c['pack_records'], c['pack_opus_tokens'], c['pack_fits_2048'], c['role2_checks'],
            c['pack_relevant_to'], c['pack_complete_for']))
        for r in c['uncertainties']:
            small = r['smallest_fitting_group']
            print('  %s found=%s out_of_range=%s level_actions=%s | smallest fitting group: %s' % (
                r['id'], r['older_evidence_found_by_role1'], r['cited_actions_out_of_range'],
                r['cited_actions_that_completed_a_level'],
                '%s %d tok' % (small['older_records'], small['pack_tokens']) if small else
                [(g['older_records'], g['pack_tokens']) for g in r['groups_rendered_as_B2']][:3]))


if __name__ == '__main__':
    main(*sys.argv[1:4])
