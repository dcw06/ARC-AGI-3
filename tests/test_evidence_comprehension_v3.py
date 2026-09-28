"""Evidence comprehension v3 (revision 1): question set, independent keys, interventions, counterfactuals, rules."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest

from research.evidence_comprehension_v2 import representation as R2, trajectories as T
from research.evidence_comprehension_v3 import independent as I, probes as P, representation as R
from research.evidence_comprehension_v3.score import analyze, score
from scripts import build_evidence_comprehension_v3 as B

ROOT = Path(__file__).resolve().parents[1]
FROZEN = json.loads(B.OUTPUT.read_bytes())
CONTEXTS = {c['context_id']: c for c in FROZEN['contexts']}
PROBES = FROZEN['probes']
BY_PAIR = {}
for _p in PROBES:
    BY_PAIR.setdefault(_p['pair_id'], {})[_p['role']] = _p


def request(p):
    return P.build_request(CONTEXTS[p['context_id']], p)


def trajectory(key):
    return I.resolve(FROZEN['trajectories'][key], FROZEN['frames'])


def wrong(p):
    schema = P.V2.ANSWER_SCHEMAS[p['family']]
    if 'enum' in schema:
        return next(v for v in schema['enum'] if v != p['key'])
    if p['family'] == 'tried_unchanged':
        return [{'action_id': 0, 'action_data': {}}]
    return [0] if p['key'] != [0] else []


def passes(bad=lambda p: False, drop=()):
    rows = {p['probe_id']: score(p, json.dumps({'answer': wrong(p) if bad(p) else p['key']}))
            for p in PROBES if p['probe_id'] not in drop}
    return {'pass_1': rows, 'pass_2': dict(rows)}


class QuestionSet(unittest.TestCase):
    def test_frozen_files_match_a_fresh_build(self):
        for path, raw in B.outputs(B.build()).items():
            self.assertEqual(raw, path.read_bytes(), path.name)

    def test_every_key_matches_the_independent_derivation(self):
        from scripts.build_evidence_comprehension_v1 import archived_episodes
        _, episodes = archived_episodes()
        shown = {}
        for p in PROBES:
            c = CONTEXTS[p['context_id']]
            name = p['source_context'] + (':counterfactual' if p['variant'] == 'counterfactual' else '')
            if name not in shown:
                if c['source'] == 'archived_live_request_without_grids':
                    rows = I.archived_rows(episodes[c['provenance']['episode_id']], c['provenance']['decision'])
                else:
                    rows = I.synthetic_rows(trajectory(name))
                shown[name] = I.window(rows)[0]
            legal = CONTEXTS[p['context_id']]['observation']['legal_actions']
            self.assertTrue(P.V2.same_answer(p['family'], I.answer(shown[name], legal, p['family'], p['arg']), p['key']),
                            p['probe_id'])

    def test_independent_keys_import_only_the_import_free_v2_module(self):
        for name, allowed in (('research/evidence_comprehension_v3/independent.py',
                               {'research.evidence_comprehension_v2'}),
                              ('research/evidence_comprehension_v2/independent.py', set())):
            tree = ast.parse((ROOT / name).read_text(encoding='utf-8'))
            found = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            found |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
            self.assertEqual(found, allowed, name)

    def test_every_request_is_unique_and_observations_are_fresh(self):
        digests = [hashlib.sha256(json.dumps(request(p), sort_keys=True).encode()).hexdigest() for p in PROBES]
        self.assertEqual(len(digests), len(set(digests)))
        prior = B.prior_observations()
        for c in FROZEN['contexts']:
            if c['condition'] == 'A0_intersect' and c['source'] != 'archived_live_request_without_grids':
                self.assertNotIn(json.dumps(c['observation'], sort_keys=True, separators=(',', ':')), prior)

    def test_schedule_covers_the_repetition_policy_with_withheld_first(self):
        counts = {}
        for block in FROZEN['schedule']:
            for pid in block['probe_ids']:
                counts[pid] = counts.get(pid, 0) + 1
        for p in PROBES:
            self.assertEqual(counts[p['probe_id']], P.PASSES[p['partition']])
        self.assertEqual([(b['partition'], b['pass']) for b in FROZEN['schedule'][:2]],
                         [('withheld', 'pass_1'), ('withheld', 'pass_2')])
        self.assertEqual(FROZEN['schedule'][1]['probe_ids'], FROZEN['schedule'][0]['probe_ids'][::-1])

    def test_coverage_meets_the_frozen_minimums(self):
        B.check_coverage(PROBES)


class Interventions(unittest.TestCase):
    def test_each_candidate_differs_from_its_reference_only_by_its_addition(self):
        for pair in BY_PAIR.values():
            ref, cand = request(pair['reference']), request(pair['candidate'])
            self.assertEqual(ref['messages'][0], cand['messages'][0])
            ro = json.loads(ref['messages'][1]['content'])['observation']
            co = json.loads(cand['messages'][1]['content'])['observation']
            if pair['reference']['track'] == 'control':
                self.assertEqual({k: v for k, v in co.items() if k != R.CONTROL_FIELD}, ro)
                self.assertEqual(co[R.CONTROL_FIELD], R.control_metadata(ro['legal_actions']))
            else:
                self.assertEqual(R.strip_tool_fields(co), ro)
            ref['messages'][1] = cand['messages'][1]
            self.assertEqual(ref, cand)

    def test_prompts_are_v2s_frozen_prompts(self):
        self.assertEqual(P.system_prompt('A0_intersect'), P.V2.CONTROL_PROMPT)
        self.assertEqual(P.system_prompt('B0_normalized_history'), P.V2.BASE_PROMPT)

    def test_computed_control_metadata_never_depends_on_history(self):
        for c in FROZEN['contexts']:
            if c['condition'] == 'A1_computed_control_metadata':
                self.assertEqual(c['observation'][R.CONTROL_FIELD], R.control_metadata(c['observation']['legal_actions']))

    def test_tool_never_turns_uncertainty_into_certainty(self):
        allowed_prefixes = ('not delivered', 'its own outcome is unknown', 'its own final returned frame differed',
                            'later step ', 'acknowledged; final returned frame same')
        for c in FROZEN['contexts']:
            if c['condition'] != 'B1_tool_eligibility':
                continue
            text = json.dumps(c['observation']).lower()
            for phrase in ('not on the still-current frame', 'frame is different', 'frame has changed since'):
                self.assertNotIn(phrase, text)
            for e in c['observation']['action_effect_history']['entries']:
                self.assertIn(e[R.TOOL_RULE], (R.ELIGIBLE, R.NOT_ELIGIBLE))
                self.assertTrue(e[R.TOOL_REASON].startswith(allowed_prefixes), e[R.TOOL_REASON])
        self.assertIn('does not establish that the current frame differs', R.TOOL_DESCRIPTION)

    def test_tool_precedence(self):
        def entry(step, status, final=False, counts=(0,)):
            ack = status == 'acknowledged'
            return {'step': step, 'action_id': 1, 'action_data': {}, 'status': status,
                    'returned_frame_count': len(counts) if ack else None,
                    'changed_cells_by_frame': list(counts) if ack else None,
                    'final_frame_changed': final if ack else None, 'level_delta': 0 if ack else None,
                    'reset': False if ack else None}
        entries = [entry(0, 'acknowledged'), entry(1, 'dispatch_failed'), entry(2, 'acknowledged', counts=(4, 0)),
                   entry(3, 'outcome_unknown'), entry(4, 'acknowledged', True, (5,)), entry(5, 'acknowledged')]
        rows = R.eligibility(entries)
        self.assertEqual(rows[0], (R.NOT_ELIGIBLE, 'later step 3 had an unknown outcome'))  # earliest blocker wins
        self.assertEqual(rows[1][1], 'not delivered: the dispatch failed')  # own status before any later entry
        self.assertEqual(rows[2], (R.NOT_ELIGIBLE, 'later step 3 had an unknown outcome'))  # transient: own final same
        self.assertEqual(rows[3][1], 'its own outcome is unknown')
        self.assertEqual(rows[4][1], 'its own final returned frame differed from the frame before it')
        self.assertEqual(rows[5][0], R.ELIGIBLE)
        eligible = [e['step'] for e, (rule, _) in zip(entries, rows) if rule == R.ELIGIBLE]
        self.assertEqual(eligible, [e['step'] for e in P.V2.qualifying(entries)])  # v2's frozen rule, exactly


class Counterfactuals(unittest.TestCase):
    def test_counterfactual_histories_are_consistent_labelled_and_matched(self):
        variants = [k for k in FROZEN['trajectories'] if k.endswith(':counterfactual')]
        self.assertGreaterEqual(len(variants), 40)
        for key in variants:
            original, variant = trajectory(key.split(':')[0]), trajectory(key)
            self.assertEqual(variant['source'], 'synthetic_counterfactual_history')
            errors = []
            B.check_counterfactual(original, variant, errors)
            self.assertEqual(errors, [], key)
            o = CONTEXTS[f"{original['partition']}:A0_intersect:original:{original['context_id']}"]['observation']
            v = CONTEXTS[f"{original['partition']}:A0_intersect:counterfactual:{original['context_id']}"]['observation']
            self.assertEqual(v, T.observation(variant))
            self.assertTrue(any(e['action_id'] == 6 for e in o['action_effect_history']['entries']))
            self.assertFalse(any(e['action_id'] == 6 for e in v['action_effect_history']['entries']))
            self.assertNotEqual(v['recent_actions'], [6])

    def test_matched_variants_share_questions_keys_and_original_context(self):
        pairs = {}
        for p in PROBES:
            pairs.setdefault(p['variant_pair_id'], {})[p['variant']] = p
        matched = [v for v in pairs.values() if 'counterfactual' in v]
        self.assertTrue(matched)
        for v in matched:
            o, c = v['original'], v['counterfactual']
            self.assertEqual((o['question'], o['key'], o['source_context']), (c['question'], c['key'], c['source_context']))
            self.assertEqual(o['track'], 'control')


class RequestContent(unittest.TestCase):
    def test_requests_carry_only_the_observation_and_question(self):
        for p in PROBES:
            payload = json.loads(request(p)['messages'][1]['content'])
            self.assertEqual(set(payload), {'observation', 'question'})
            content = request(p)['messages'][1]['content']
            for leak in ('"key"', 'shortcuts_correct', '"strata"', '"events"', 'counterfactual', 'withheld',
                         'variant', 'current_grid', 'replacement_action'):
                self.assertNotIn(leak, content)


class Scoring(unittest.TestCase):
    def test_all_correct_is_reference_meets_criterion(self):
        report = analyze(PROBES, passes())
        self.assertEqual(report['completeness']['primary'], {'control': 'complete', 'history': 'complete'})
        self.assertEqual(report['completeness']['secondary_history_alteration'], 'complete')
        self.assertEqual(report['completeness']['whole_schedule'], 'complete')
        self.assertEqual(report['verdicts'], {'control': 'baseline_meets_criterion',
                                              'history': 'baseline_meets_criterion_tool_assisted'})

    def test_missing_answers_can_never_pass(self):
        first = next(p['probe_id'] for p in PROBES if p['partition'] == 'withheld' and p['variant'] == 'original')
        for value in ({}, {'pass_1': passes()['pass_1']}, passes(drop=(first,))):
            report = analyze(PROBES, value)
            self.assertEqual(report['completeness']['withheld_schedule'], 'incomplete')
            self.assertIn('incomplete', ''.join(report['verdicts'].values()))


class Completeness(unittest.TestCase):
    """Review of b9ac66f: primary, secondary and schedule completeness are separate, and stated."""

    @staticmethod
    def improving(p):  # the reference misses every target the candidate gets right
        return (p['role'] == 'reference' and p['family_role'] == 'target' and p['variant'] == 'original'
                and (p['key'] == [] or p['family'] == 'tried_unchanged'))

    def run_missing(self, select, pass_id):
        value = passes(self.improving)
        target = next(p for p in PROBES if select(p))
        del value[pass_id][target['probe_id']]
        return analyze(PROBES, value)

    def test_missing_original_answer_in_either_pass_makes_only_that_track_incomplete(self):
        for track, other in (('control', 'history'), ('history', 'control')):
            for pass_id in ('pass_1', 'pass_2'):
                with self.subTest(track=track, pass_id=pass_id):
                    report = self.run_missing(lambda p: (p['partition'] == 'withheld' and p['variant'] == 'original'
                                                         and p['track'] == track), pass_id)
                    c = report['completeness']
                    self.assertEqual(c['primary'][track], 'incomplete')
                    self.assertEqual(c['primary'][other], 'complete')
                    self.assertTrue(report['verdicts'][track].startswith('incomplete'))
                    self.assertTrue(report['verdicts'][other].startswith('candidate_clear_improvement'))
                    self.assertEqual((c['withheld_schedule'], c['whole_schedule']), ('incomplete', 'incomplete'))

    def test_missing_original_in_an_altered_context_also_leaves_the_secondary_incomplete(self):
        cf = {p['source_context'] for p in PROBES if p['variant'] == 'counterfactual' and p['partition'] == 'withheld'}
        report = self.run_missing(lambda p: (p['partition'] == 'withheld' and p['variant'] == 'original'
                                             and p['track'] == 'control' and p['source_context'] in cf), 'pass_2')
        self.assertEqual(report['completeness']['secondary_history_alteration'], 'incomplete')
        self.assertEqual(report['verdicts']['control'], 'incomplete')

    def test_missing_counterfactual_answer_in_either_pass_leaves_promotion_to_the_primary(self):
        for pass_id in ('pass_1', 'pass_2'):
            with self.subTest(pass_id=pass_id):
                report = self.run_missing(lambda p: p['partition'] == 'withheld' and p['variant'] == 'counterfactual',
                                          pass_id)
                c = report['completeness']
                self.assertEqual(c['primary'], {'control': 'complete', 'history': 'complete'})
                self.assertEqual(c['secondary_history_alteration'], 'incomplete')
                self.assertEqual((c['withheld_schedule'], c['whole_schedule']), ('incomplete', 'incomplete'))
                self.assertEqual(report['verdicts'], {'control': 'candidate_clear_improvement',
                                                      'history': 'candidate_clear_improvement_tool_assisted'})
                self.assertIn('non-gating', c['policy'])

    def test_missing_development_answer_affects_only_the_whole_schedule(self):
        value = passes()
        dev = next(p['probe_id'] for p in PROBES if p['partition'] == 'development')
        del value['pass_1'][dev]
        c = analyze(PROBES, value)['completeness']
        self.assertEqual((c['primary'], c['secondary_history_alteration'], c['withheld_schedule'], c['whole_schedule']),
                         ({'control': 'complete', 'history': 'complete'}, 'complete', 'complete', 'incomplete'))

    def test_candidates_fixing_reference_errors_are_clear_improvements(self):
        def bad(p):
            return (p['role'] == 'reference' and p['family_role'] == 'target' and p['variant'] == 'original'
                    and (p['key'] == [] or p['family'] == 'tried_unchanged'))
        report = analyze(PROBES, passes(bad))
        self.assertEqual(report['verdicts'], {'control': 'candidate_clear_improvement',
                                              'history': 'candidate_clear_improvement_tool_assisted'})

    def test_history_alteration_is_reported_but_never_gates(self):
        def bad(p):
            return p['variant'] == 'counterfactual'
        report = analyze(PROBES, passes(bad))
        self.assertEqual(report['verdicts']['control'], 'baseline_meets_criterion')
        row = report['history_alteration']['withheld']['A0_intersect']['legal_coordinate_actions']
        self.assertEqual((row['regressions'], row['improvements']), (row['n'], 0))

    def test_matched_variants_are_resampled_together(self):
        for p in PROBES:
            if p['variant'] == 'counterfactual':
                self.assertIn(f":{p['source_context']}", p['context_id'])


if __name__ == '__main__':
    unittest.main()
