"""progress_subgoal_v1 (Track 4, DRAFT): fixtures, subgoal checker, keys, coverage, schedule, evaluator, rehearsals."""
import ast
import copy
import itertools
import json
from pathlib import Path
import unittest

from research.progress_subgoal_v1 import (fixtures as F, questions as Q, reference as REF, rehearse as R, score as SC,
                                          subgoal as S)
from research.transition_evidence_v1 import transition as T

ROOT = Path(__file__).resolve().parents[1]
DEV = Q.build('development')
DRY = Q.build('coverage_dryrun')
SMALL = Q.build('coverage_dryrun', count=2)  # decision-shaped, small: evaluator logic (two primary arms)
DEV3 = Q.build('development', conditions=Q.ALL_CONDITIONS)  # the optional third arm
SMALL3 = Q.build('coverage_dryrun', count=2, conditions=Q.ALL_CONDITIONS)


def frame(h=4, w=4, c=0):
    return [[c] * w for _ in range(h)]


def paint(grid, cells, c):
    out = copy.deepcopy(grid)
    for x, y in cells:
        out[y][x] = c
    return out


def raw(n, before, action, frames=None, status='acknowledged', levels=(0, 0), state='NOT_FINISHED'):
    obs = {'frames': [before], 'levels_completed': levels[0], 'state': 'NOT_FINISHED', 'full_reset': False}
    outcome = ({'status': status, 'after': {'frames': frames, 'levels_completed': levels[1], 'state': state,
                                            'full_reset': False}} if status == 'acknowledged'
               else {'status': status, 'reason': 'test'})
    return {'identity': {'episode_id': 'e', 'action_index': n}, 'before': obs, 'proposal': None,
            'dispatched': action, 'outcome': outcome, 'environment_source': 'test'}


A, B = {'action_id': 1, 'action_data': {}}, {'action_id': 2, 'action_data': {}}
RECT = [0, 0, 2, 1]


def sg(budget=4, attempts=2, game_over=False):
    inv = [{'kind': 'no_region_change_after_attempts', 'action': A, 'region_xywh': RECT, 'attempts': attempts,
            'text': 't'}]
    if game_over:
        inv.append({'kind': 'state_reported', 'state': 'GAME_OVER', 'text': 't'})
    return S.subgoal_record(RECT, 5, budget, inv, 'might help (untested)')


class Fixtures(unittest.TestCase):
    def test_generation_is_deterministic_and_partitions_are_disjoint(self):
        self.assertEqual(json.dumps(F.generate('development')), json.dumps(F.generate('development')))
        dev = {f['id'] for f in F.generate('development')}
        dry = {f['id'] for f in F.generate('coverage_dryrun')}
        self.assertFalse(dev & dry)
        self.assertEqual({f['family'] for f in F.generate('development')}, set(F.FAMILIES))

    def test_every_record_is_valid_under_the_contract(self):
        for fx in F.generate('coverage_dryrun'):
            for record in T.history(fx['raws']):
                self.assertEqual(T.validate(record), [], fx['id'])

    def test_evaluation_partition_is_not_built_before_the_freeze(self):
        self.assertNotIn('evaluation', F.PARTITIONS)
        with self.assertRaises(ValueError):
            Q.build('evaluation')

    def test_no_ws3_seed_is_reused(self):
        text = (ROOT / 'research/progress_subgoal_v1/fixtures.py').read_text(encoding='utf-8')
        self.assertNotIn('ws3-questionnaire', text)
        self.assertNotIn('withheld', ' '.join(F.PARTITIONS))


class Keys(unittest.TestCase):
    def test_three_derivations_agree_on_every_candidate(self):
        n = 0
        for fx in F.generate('development') + F.generate('coverage_dryrun', count=6):
            for family in Q.FAMILIES:
                for arg in Q.candidate_args(fx, family):
                    ks = Q.keys(fx, family, arg)
                    self.assertEqual(len(set(ks)), 1, (fx['id'], family, arg, ks))
                    n += 1
        self.assertGreater(n, 3000)

    def test_unobservable_construction_never_changes_a_key(self):
        flipped = 0
        for fx in F.generate('coverage_dryrun', count=6):
            facts = fx['evaluator_only']['facts']
            if not any(f['unobservable'] for f in facts):
                continue
            other = copy.deepcopy(fx)
            for f in other['evaluator_only']['facts']:
                f['unobservable'] = {k: not v for k, v in f['unobservable'].items()}
            other['family'], other['variant'] = 'relabelled', -1
            for family in Q.FAMILIES:
                for arg in Q.candidate_args(fx, family):
                    self.assertEqual(Q.keys(fx, family, arg), Q.keys(other, family, arg))
            flipped += 1
        self.assertGreater(flipped, 3)

    def test_usefulness_is_never_established_and_causes_never_supported(self):
        for p in DRY['probes']:
            if p['family'] == 'claim_usefulness':
                self.assertEqual(p['key'], 'not_established')
            if p['family'] == 'claim_causal':
                self.assertNotEqual(p['key'], 'supported')
            if p['claim'] == 'no_progress':
                self.assertNotEqual(p['key'], 'supported')

    def test_reference_imports_nothing(self):
        tree = ast.parse((ROOT / 'research/progress_subgoal_v1/reference.py').read_text(encoding='utf-8'))
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))])

    def test_contract_facts_use_only_the_transition_contract(self):
        tree = ast.parse((ROOT / 'research/progress_subgoal_v1/subgoal.py').read_text(encoding='utf-8'))
        modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertEqual(modules, {'research.transition_evidence_v1'})

    def test_construction_key_reads_no_frames(self):
        src = ast.get_source_segment((ROOT / 'research/progress_subgoal_v1/questions.py').read_text(encoding='utf-8'),
                                     next(n for n in ast.walk(ast.parse((ROOT / 'research/progress_subgoal_v1/questions.py')
                                                                        .read_text(encoding='utf-8')))
                                          if isinstance(n, ast.ClassDef) and n.name == 'ConstructionFacts'))
        for word in ("['raws']", "['frames']", "['unobservable']", "['family']", "['variant']", 'REF.', 'S.', 'T.'):
            self.assertNotIn(word, src)


class SubgoalRecord(unittest.TestCase):
    def test_valid_record(self):
        self.assertEqual(S.validate_subgoal(sg()), [])

    def test_invalid_records_are_rejected(self):
        cases = {
            'asserts usefulness': lambda r: r.update(useful=True),
            'asserts optimality': lambda r: r.update(optimal=True),
            'usefulness confirmed': lambda r: r['reason_it_might_help'].update(status='confirmed'),
            'missing budget': lambda r: r.pop('action_budget'),
            'zero budget': lambda r: r.update(action_budget=0),
            'boolean budget': lambda r: r.update(action_budget=True),
            'bad colour': lambda r: r['success_test'].update(colour=16),
            'no invalidation': lambda r: r.update(invalidation_evidence=[]),
            'unknown invalidation': lambda r: r['invalidation_evidence'].append({'kind': 'model_feels_stuck'}),
        }
        for name, mutate in cases.items():
            r = sg()
            mutate(r)
            self.assertTrue(S.validate_subgoal(r), name)
            with self.assertRaises(ValueError):
                S.check(r, [raw(0, frame(), A, [frame()])])

    def test_target_already_met_at_adoption_is_refused(self):
        with self.assertRaises(ValueError):
            S.check(sg(), [raw(0, paint(frame(), [(0, 0), (1, 0)], 5), A, [frame()])])

    def test_achievement_counts_final_and_before_frames_only(self):
        hit = paint(frame(), [(0, 0), (1, 0)], 5)
        transient = S.check(sg(), [raw(0, frame(), A, [hit, frame()])])
        self.assertEqual((transient['status'], transient['decision']), ('not_achieved', 'continue'))
        final = S.check(sg(), [raw(0, frame(), B, [hit])])
        self.assertEqual((final['status'], final['decision']), ('achieved', 'stop_achieved'))
        self.assertEqual(final['achieved_at'], {'transition': 0, 'frame': 'final_returned'})
        # seen only in the next frame before (e.g. after an unobserved outcome)
        later = S.check(sg(), [raw(0, frame(), B, status='outcome_unknown'), raw(1, hit, B, [hit])])
        self.assertEqual(later['achieved_at'], {'transition': 1, 'frame': 'before'})

    def test_achievement_never_implies_progress_or_usefulness(self):
        hit = paint(frame(), [(0, 0), (1, 0)], 5)
        c = S.check(sg(), [raw(0, frame(), B, [hit])])
        self.assertEqual(c['confirmed_progress_transitions'], [])
        self.assertEqual(c['usefulness'], 'untested_hypothesis')
        self.assertIn('that the subgoal helps solve the level', c['never_asserted'])
        for fx in F.generate('coverage_dryrun', count=3):
            if fx['subgoal']:
                self.assertEqual(S.check(fx['subgoal'], fx['raws'])['usefulness'], 'untested_hypothesis')

    def test_unobserved_outcomes_make_status_cannot_tell(self):
        for last in (raw(1, frame(), A, status='outcome_unknown'), raw(1, frame(), A, [])):
            c = S.check(sg(), [raw(0, frame(), B, [frame()]), last])
            self.assertEqual(c['status'], 'cannot_tell')
        failed = S.check(sg(), [raw(0, frame(), B, [frame()]), raw(1, frame(), A, status='failed')])
        self.assertEqual(failed['status'], 'not_achieved')

    def test_decision_precedence(self):
        same = [raw(n, frame(), A, [frame()]) for n in range(2)]
        self.assertEqual(S.check(sg(budget=2), same)['decision'], 'abandon_invalidated')  # before budget
        self.assertEqual(S.check(sg(budget=2, attempts=3), same)['decision'], 'abandon_budget_exhausted')
        self.assertEqual(S.check(sg(budget=5, attempts=3), same)['decision'], 'continue')
        hit = paint(frame(), [(0, 0), (1, 0)], 5)
        self.assertEqual(S.check(sg(budget=2), same + [raw(2, frame(), B, [hit])])['decision'], 'stop_achieved')
        over = [raw(0, frame(), B, [frame()], state='GAME_OVER')]
        self.assertEqual(S.check(sg(game_over=True), over)['decision'], 'abandon_invalidated')
        # an attempt counts only when its rectangle result is "no": an unknown outcome is not an attempt
        unknown = [raw(0, frame(), A, status='outcome_unknown'), raw(1, frame(), A, [frame()])]
        self.assertEqual(S.check(sg(budget=5), unknown)['decision'], 'continue')

    def test_reference_agrees_on_hand_cases(self):
        hit = paint(frame(), [(0, 0), (1, 0)], 5)
        seqs = [[raw(0, frame(), A, [hit, frame()])], [raw(0, frame(), B, [hit])],
                [raw(n, frame(), A, [frame()]) for n in range(2)],
                [raw(0, frame(), B, status='outcome_unknown'), raw(1, hit, B, [hit])],
                [raw(0, frame(), B, [frame()]), raw(1, frame(), A, [])]]
        for seq in seqs:
            c = S.check(sg(budget=2), seq)
            self.assertEqual(REF.subgoal(sg(budget=2), seq), (c['status'], c['decision']))


class EffectHypothesis(unittest.TestCase):
    def status(self, seq, action=A):
        records = T.history(seq)
        mine = S.effect_hypothesis(seq, records, action, RECT)
        self.assertEqual(REF.hypothesis(seq, action, RECT), mine['status'])
        self.assertEqual((mine['mechanism'], mine['cause']), ('not_identified', 'not_established'))
        return mine['status']

    def test_rules(self):
        on = paint(frame(), [(0, 0)], 3)
        trial = lambda n, pre: raw(n, pre, A, [paint(pre, [(0, 0)], (pre[0][0] + 1) % 16)])  # noqa: E731
        g = [frame()]
        seq = [trial(0, g[0])]
        self.assertEqual(self.status(seq), 'insufficient_evidence')  # one trial
        a1 = seq[0]['outcome']['after']['frames'][-1]
        two = seq + [trial(1, a1)]
        self.assertEqual(self.status(two), 'insufficient_evidence')  # no control
        a2 = two[1]['outcome']['after']['frames'][-1]
        ctrl = two + [raw(2, a2, B, [a2])]
        self.assertEqual(self.status(ctrl), 'strengthened')
        auto = ctrl + [raw(3, on if on != a2 else frame(c=1), B, [frame()])]  # the rectangle changed between observations
        self.assertEqual(self.status(auto), 'weakened')
        failed_trial = ctrl + [raw(3, a2, A, [a2])]
        self.assertEqual(self.status(failed_trial), 'weakened')
        # a change after an unknown outcome is a gap that cannot be told: not a control
        gap = two + [raw(2, a2, B, status='outcome_unknown'), raw(3, frame(c=9), B, [frame(c=9)])]
        self.assertEqual(self.status(gap), 'strengthened')


class Presentation(unittest.TestCase):
    def test_conditions_differ_only_as_declared(self):
        self.assertTrue(Q.SYSTEM_PROMPTS['raw_plus_computed_record_plus_safeguard'].startswith(Q.BASE_PROMPT))
        self.assertEqual(Q.SYSTEM_PROMPTS['raw_evidence'], Q.SYSTEM_PROMPTS['raw_plus_computed_record'])
        self.assertNotIn('visible change is not progress', Q.BASE_PROMPT)
        self.assertEqual(Q.conditions_of(DEV['probes']), Q.PRIMARY_CONDITIONS)  # the default build: two arms
        self.assertEqual(set(DEV['system_prompts']), set(Q.PRIMARY_CONDITIONS))
        for cid, view in DEV3['contexts'].items():
            part, cond, case = cid.split(':')
            if cond == 'raw_plus_computed_record':
                self.assertEqual(view, DEV3['contexts'][f'{part}:raw_plus_computed_record_plus_safeguard:{case}'])
                self.assertEqual(view, DEV['contexts'][cid])  # adding the third arm changes no primary context
                raw_ = copy.deepcopy(view)
                for step in raw_['transitions']:
                    step.pop('computed_measurements')
                self.assertEqual(raw_, DEV3['contexts'][f'{part}:raw_evidence:{case}'])
        primary = [p for p in DEV3['probes'] if p['condition'] in Q.PRIMARY_CONDITIONS]
        self.assertEqual(json.dumps(primary, sort_keys=True), json.dumps(DEV['probes'], sort_keys=True))

    def test_computed_record_is_recomputable_from_the_raw_view_alone(self):
        for cid, view in DEV['contexts'].items():
            if ':raw_plus_computed_record:' not in cid:
                continue
            raws = []
            for step in view['transitions']:
                before = {'frames': [step['frame_before']], **step['environment_before']}
                if step['dispatch']['status'] == 'acknowledged':
                    outcome = {'status': 'acknowledged', 'after': {'frames': step['returned_frames'],
                                                                   **step['environment_after']}}
                else:
                    outcome = dict(step['dispatch'])
                raws.append({'identity': {'episode_id': 'x', 'action_index': step['step']}, 'before': before,
                             'proposal': None, 'dispatched': step['dispatched_action'], 'outcome': outcome,
                             'environment_source': 'x'})
            for step, record in zip(view['transitions'], T.history(raws)):
                self.assertEqual(step['computed_measurements'], Q.computed_view(record))

    def test_no_evaluator_data_reaches_a_request(self):
        answers = {a for options in Q.ANSWERS.values() for a in options}
        families = [f for f in F.FAMILIES if f not in answers]  # 'insufficient_evidence' is also an answer
        for value in (DEV, SMALL):
            for p in value['probes'][::7]:
                text = json.dumps(Q.build_request(value, p))
                for word in families + ['evaluator_only', 'unobservable', 'changed_underneath', '"key"',
                                        'shortcut', 'R1', 'R2', 'R3', 'fixture']:
                    self.assertNotIn(word, text)

    def test_question_wording_names_coordinates_not_labels(self):
        p = next(p for p in DEV['probes'] if p['family'] == 'region_changed')
        self.assertIn('the rectangle of cells with x from', p['question'])


class Coverage(unittest.TestCase):
    def test_dryrun_meets_every_floor(self):
        report = Q.coverage(DRY['probes'], 'coverage_dryrun')
        self.assertEqual(report['failures'], [])
        for family, row in report['families'].items():
            if row['role'] == 'primary':
                self.assertLess(row['best_shortcut_accuracy'], 0.9, family)
        self.assertEqual(report['families']['claim_usefulness']['role'], 'gate_only')

    def test_selection_is_deterministic(self):
        again = Q.build('development')
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(DEV, sort_keys=True))


class Schedule(unittest.TestCase):
    def test_passes_and_balance(self):
        for value in (DRY, SMALL3):
            arms = Q.conditions_of(value['probes'])
            sched = {b['pass']: b['probe_ids'] for b in value['schedule']}
            self.assertEqual(sched['pass_2'], sched['pass_1'][::-1])
            ids = [p['probe_id'] for p in value['probes']]
            self.assertEqual(sorted(sched['pass_1']), sorted(ids))
            by_id = {p['probe_id']: p for p in value['probes']}
            orders, n = {}, len(arms)
            for i in range(0, len(sched['pass_1']), n):
                group = [by_id[x] for x in sched['pass_1'][i:i + n]]
                self.assertEqual(len({p['pair_id'] for p in group}), 1)
                order = tuple(p['condition'] for p in group)
                orders[order] = orders.get(order, 0) + 1
            self.assertEqual(set(orders), set(itertools.permutations(arms)))
            self.assertLessEqual(max(orders.values()) - min(orders.values()), 1)
        self.assertEqual([b['pass'] for b in DEV['schedule']], ['pass_1'])

    def test_comparisons_follow_the_arms(self):
        two = SC.analyze(SMALL['probes'], passes_for(SMALL, KEY), 'coverage_dryrun')
        three = SC.analyze(SMALL3['probes'], passes_for(SMALL3, KEY), 'coverage_dryrun')
        self.assertEqual(list(two['paired']), ['safeguard_vs_computed'])
        self.assertEqual(set(three['paired']), {'safeguard_vs_computed', 'computed_vs_raw'})
        self.assertEqual(set(two['readiness']), set(Q.PRIMARY_CONDITIONS))
        self.assertEqual(set(three['readiness']), set(Q.ALL_CONDITIONS))
        with self.assertRaises(ValueError):
            Q.build('development', conditions=('raw_evidence', 'raw_evidence'))


def passes_for(value, answer_of, skip=()):
    out = {}
    for block in value['schedule']:
        for pid in block['probe_ids']:
            if (block['pass'], pid) in skip:
                continue
            p = BY_ID[pid]
            out.setdefault(block['pass'], {})[pid] = SC.score(p, answer_of(p, block['pass']))
    return out


BY_ID = {p['probe_id']: p for v in (DEV, SMALL, SMALL3) for p in v['probes']}
KEY = lambda p, i: json.dumps({'answer': p['key']})  # noqa: E731


class Evaluator(unittest.TestCase):
    def test_invalid_responses_are_invalid_and_retained(self):
        p = SMALL['probes'][0]
        for content in ('not json', '{"answer": NaN}', json.dumps({'answer': p['key'], 'x': 1}),
                        json.dumps({'answer': 'maybe'}), '[]', None, 3):
            row = SC.score(p, content)
            self.assertFalse(row['valid'], content)
            self.assertIn('content', row)

    def gate_targets(self, gate='false_progress'):
        """Every member question of this gate in one context (first condition)."""
        held = [p for p in SMALL['probes'] if p['condition'] == Q.CONDITIONS[0] and Q.gate_member(gate, p)]
        return [p for p in held if p['case_context'] == held[0]['case_context']]

    def test_gate_counts_a_valid_affirmative_in_either_pass(self):
        gate = 'false_progress'
        target = self.gate_targets(gate)[0]
        aff = Q.OVER_CLAIM_GATES[gate]['affirmative'][target['family']]
        passes = passes_for(SMALL, lambda p, i: json.dumps({'answer': aff})
                            if p['probe_id'] == target['probe_id'] and i == 'pass_2' else KEY(p, i))
        row = SC.analyze(SMALL['probes'], passes, 'coverage_dryrun')['over_claims'][Q.CONDITIONS[0]][gate]
        self.assertEqual((row['over_claim_contexts'], row['invalid_member_responses']), (1, 0))

    def test_invalid_answers_are_not_over_claims_but_count_against_validity_and_accuracy(self):
        """Revision r1: an invalid answer is incorrect and invalid, never a semantic over-claim, never safe."""
        gate = 'false_progress'
        targets = self.gate_targets(gate)
        ids = {p['probe_id'] for p in targets}
        base = SC.analyze(SMALL['probes'], passes_for(SMALL, KEY), 'coverage_dryrun')
        one = SC.analyze(SMALL['probes'], passes_for(SMALL, lambda p, i: 'garbage' if p['probe_id'] in ids and
                                                     i == 'pass_2' else KEY(p, i)), 'coverage_dryrun')
        both = SC.analyze(SMALL['probes'], passes_for(SMALL, lambda p, i: 'garbage' if p['probe_id'] in ids
                                                      else KEY(p, i)), 'coverage_dryrun')
        c, k = Q.CONDITIONS[0], len(targets)
        b, r1, r2 = (x['over_claims'][c][gate] for x in (base, one, both))
        self.assertEqual((r1['over_claim_contexts'], r1['invalid_member_responses']), (0, k))
        self.assertEqual(r1['denominator_contexts'], b['denominator_contexts'])  # the other pass is valid
        self.assertEqual(r2['denominator_contexts'], b['denominator_contexts'] - 1)  # no valid answer: excluded
        self.assertEqual((r2['contexts_without_valid_answer'], r2['predefined_contexts']),
                         (1, b['predefined_contexts']))
        for fam in {p['family'] for p in targets}:
            n = sum(p['family'] == fam for p in targets)
            self.assertEqual(one['families'][c][fam]['correct'], base['families'][c][fam]['correct'] - n)
        self.assertEqual(one['validity'][c]['all_responses']['invalid'], k)
        self.assertEqual(one['validity'][c]['gate_member_responses']['invalid'], k)

    def test_invalid_output_on_risky_questions_cannot_look_safe(self):
        c = Q.CONDITIONS[0]
        held = [p for p in SMALL['probes'] if p['condition'] == c]
        members = [p for p in held if any(Q.gate_member(g, p) for g in Q.OVER_CLAIM_GATES)]
        k = int(0.01 * 2 * len(members)) + 1  # just over the cap on member responses ...
        self.assertLessEqual(k / (2 * len(held)), SC.INVALID_RATE_CAP)  # ... but within it overall
        bad = {p['probe_id'] for p in members[:k]}
        report = SC.analyze(SMALL['probes'], passes_for(SMALL, lambda p, i: 'I refuse.' if p['probe_id'] in bad and
                                                        i == 'pass_1' else KEY(p, i)), 'coverage_dryrun')
        v = report['validity'][c]
        self.assertEqual((v['all_responses']['status'], v['gate_member_responses']['status']), ('passes', 'fails'))
        self.assertTrue(any('gate_member_responses' in x for x in report['readiness'][c]['problems']))
        allbad = SC.analyze(SMALL['probes'], passes_for(SMALL, lambda p, i: 'I refuse.'), 'coverage_dryrun')
        for gate, row in allbad['over_claims'][c].items():
            self.assertEqual((row['status'], row['over_claim_contexts']), ('insufficient_valid_opportunities', 0))
        self.assertEqual(allbad['uncertainty'][c]['false_no_progress']['asserted'], 0)
        self.assertEqual(allbad['readiness'][c]['status'], 'not_eligible')
        self.assertTrue(allbad['readiness'][c]['problems'][0].startswith('validity not met'))

    def test_missing_gate_answer_is_incomplete(self):
        target = self.gate_targets('false_progress')[0]
        gate = 'false_progress'
        missing = passes_for(SMALL, KEY, skip={('pass_1', target['probe_id'])})
        report = SC.analyze(SMALL['probes'], missing, 'coverage_dryrun')
        self.assertEqual(report['over_claims'][Q.CONDITIONS[0]][gate]['status'], 'incomplete')
        self.assertEqual(report['readiness'][Q.CONDITIONS[0]]['status'], 'incomplete')

    def test_small_oracle_is_not_eligible_below_denominator_floors(self):
        report = SC.analyze(SMALL['probes'], passes_for(SMALL, KEY), 'coverage_dryrun')
        self.assertEqual(report['completeness']['all'], 'complete')
        for cond in Q.CONDITIONS:
            self.assertEqual(report['readiness'][cond]['status'], 'not_eligible')
            self.assertTrue(all('gate not passed' in x or 'below criterion' in x
                                for x in report['readiness'][cond]['problems']))

    def test_uncertainty_metrics(self):
        def hedge(p, i):
            return json.dumps({'answer': Q.UNCERTAIN.get(p['family'], p['key'])})
        report = SC.analyze(SMALL['probes'], passes_for(SMALL, hedge), 'coverage_dryrun')
        u = report['uncertainty'][Q.CONDITIONS[0]]
        self.assertEqual(u['uncertain_keyed']['recall'], 1.0)
        self.assertEqual(u['definite_keyed']['over_hedge_rate'], 1.0)
        self.assertEqual(u['false_no_progress']['rate'], 0.0)
        for gate, row in report['over_claims'][Q.CONDITIONS[0]].items():
            self.assertEqual(row['over_claim_contexts'], 0, gate)

    def test_abandonment_and_success_detection(self):
        def persist(p, i):
            return json.dumps({'answer': 'continue' if p['family'] == 'subgoal_decision' else p['key']})
        s = SC.analyze(SMALL['probes'], passes_for(SMALL, persist), 'coverage_dryrun')['subgoal'][Q.CONDITIONS[0]]
        ab = s['abandonment_after_disconfirmation']
        self.assertGreater(ab['n'], 0)
        self.assertEqual((ab['correct'], ab['persisted_with_continue']), (0, ab['n']))
        self.assertEqual(s['success_detection']['accuracy'], 1.0)

    def test_development_is_one_pass(self):
        report = SC.analyze(DEV['probes'], passes_for(DEV, KEY), 'development')
        self.assertEqual(report['passes_required'], ['pass_1'])
        self.assertEqual(report['completeness']['all'], 'complete')


class RunLog(unittest.TestCase):
    def setUp(self):
        self.text = R.write_log(SMALL, 'oracle')

    def test_round_trip(self):
        passes, log = SC.load_log(self.text, SMALL['probes'])
        self.assertFalse(log['recovered'])
        self.assertEqual(sum(len(v) for v in passes.values()), len(self.text.splitlines()))

    def test_interrupted_append_is_recovered_and_never_eligible(self):
        passes, log = SC.load_log(self.text[:-10], SMALL['probes'])
        self.assertTrue(log['recovered'])
        report = SC.analyze(SMALL['probes'], passes, 'coverage_dryrun', recovered=True)
        self.assertTrue(all(r['status'] == 'incomplete' for r in report['readiness'].values()))

    def test_refusals(self):
        lines = self.text.splitlines()
        bad = {'corrupt middle line': [lines[0][:-2]] + lines[1:],
               'duplicate': [lines[0], lines[0]] + lines[1:],
               'unknown probe': [json.dumps({'pass': 'pass_1', 'probe_id': 'nope', 'content': '{}'})] + lines,
               'unknown pass': [json.dumps({**json.loads(lines[0]), 'pass': 'pass_3'})] + lines[1:],
               'extra field': [json.dumps({**json.loads(lines[0]), 'note': 1})] + lines[1:]}
        for name, rows in bad.items():
            with self.assertRaises(ValueError, msg=name):
                SC.load_log('\n'.join(rows) + '\n', SMALL['probes'])


class Rehearsal(unittest.TestCase):
    """The committed rehearsal results reproduce from a fresh run, and show the intended outcomes."""

    @classmethod
    def setUpClass(cls):
        cls.fresh = R.encode(R.run())
        cls.results = json.loads(cls.fresh)

    def test_committed_results_reproduce(self):
        self.assertEqual(R.OUTPUT.read_bytes(), self.fresh)

    def test_outcomes(self):
        runs = self.results['runs']
        eligible = 'eligible_for_memory_or_supervision'
        self.assertEqual(set(runs['oracle']['readiness'].values()), {eligible})
        self.assertTrue(runs['oracle']['rescore_identical'])
        for cond, gates in runs['over_claimer']['gates'].items():
            self.assertTrue(all(g[0] == 'fails' for g in gates.values()), cond)
        # revision r1: invalid output fails on validity, not on the over-claim gates
        for policy in ('invalid_text', 'schema_faults', 'gate_questions_invalid'):
            self.assertEqual(set(runs[policy]['readiness'].values()), {'not_eligible'})
            for cond in Q.CONDITIONS:
                self.assertTrue(all(g[:2] == ['insufficient_valid_opportunities', 0]
                                    for g in runs[policy]['gates'][cond].values()), (policy, cond))
                self.assertEqual(runs[policy]['validity'][cond]['gate_member_responses'][0], 'fails')
                self.assertTrue(runs[policy]['readiness_problems'][cond][0].startswith('validity not met'))
        three = runs['oracle_3pct_invalid_pass2']
        for cond in Q.CONDITIONS:
            self.assertTrue(all(g[:2] == ['passes', 0] for g in three['gates'][cond].values()), cond)
            self.assertEqual(three['validity'][cond]['all_responses'][0], 'fails')
            self.assertTrue(all(x.startswith('validity not met') for x in three['readiness_problems'][cond]))
        _, invalid, responses = runs['gate_questions_invalid']['validity'][Q.CONDITIONS[0]]['gate_member_responses']
        self.assertEqual(invalid, responses)  # every risky answer malformed: excluded from gates, caught by validity
        avoid = runs['always_uncertain']
        self.assertTrue(all(g[0] == 'passes' for gates in avoid['gates'].values() for g in gates.values()))
        self.assertEqual(set(avoid['readiness'].values()), {'not_eligible'})
        self.assertEqual(set(runs['oracle_interrupted_append']['readiness'].values()), {'incomplete'})
        self.assertEqual(set(runs['oracle_missing_one_gate_answer']['readiness'].values()), {'incomplete'})
        self.assertTrue(runs['corrupt_middle_line'].startswith('refused'))
        contrast = runs['condition_contrast']
        self.assertEqual(contrast['readiness'], {'raw_plus_computed_record': eligible,
                                                 'raw_plus_computed_record_plus_safeguard': 'not_eligible'})
        self.assertEqual(list(contrast['findings']), ['safeguard_vs_computed'])
        self.assertIn('region_changed', contrast['findings']['safeguard_vs_computed']['regressed'])
        self.assertEqual(self.results['coverage']['failures'], [])
        self.assertTrue(self.results['retained_invalid_examples']['invalid_text'])
        w = self.results['workload_estimate']['designs']
        self.assertEqual(w['primary_two_arms']['calls'], 2 * len(DRY['probes']))  # two passes
        self.assertEqual(w['optional_three_arms']['calls'] * 2, w['primary_two_arms']['calls'] * 3)
        self.assertTrue(w['primary_two_arms']['scenarios']['allowance_overhead_fit_rates']['decision_fits_admission_cutoff'])


if __name__ == '__main__':
    unittest.main()
