"""Evidence comprehension v1 (revision 2): frozen probe set, dual keys, requests, scoring and analysis.

The `R1Finding*` classes are regressions for the review of r1 at 064bb9a.
"""
import ast
import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from research.action_effect_history_v1.contract import SYSTEM_PROMPT as LIVE_PROMPT
from research.evidence_comprehension_v1 import independent, probes as P
from research.evidence_comprehension_v1.score import analyze, best_shortcuts, score, validate
from scripts import build_evidence_comprehension_v1 as B

ROOT = Path(__file__).resolve().parents[1]
FROZEN = json.loads(B.OUTPUT.read_bytes())
CONTEXTS = {c['context_id']: c for c in FROZEN['contexts']}
PROBES = FROZEN['probes']


def oracle(probes, wrong=()):
    """Score rows answering every key, except probes whose id is in `wrong` (answered with a valid wrong answer)."""
    rows = {}
    for p in probes:
        answer = p['key']
        if p['probe_id'] in wrong:
            answer = {'available_actions': [0], 'coordinate_actions': [0], 'recall_action': 'not_shown' if answer != 'not_shown'
                      else {'action_id': 0, 'action_data': {}}, 'outcome_class': 'not_shown' if answer != 'not_shown'
                      else 'dispatch_failed', 'observed_effect': 'not_observed' if answer != 'not_observed' else
                      'dispatch_failed', 'tried_unchanged': [{'action_id': 0, 'action_data': {}}]}[p['family']]
        rows[p['probe_id']] = score(p, json.dumps({'answer': answer}))
    return rows


class ProbeSet(unittest.TestCase):
    def test_frozen_file_matches_a_fresh_build(self):
        self.assertEqual(B.encode(B.build()), B.OUTPUT.read_bytes())

    def test_every_key_matches_the_independent_derivation(self):
        _, episodes = B.archived_episodes()
        for probe in PROBES:
            context = CONTEXTS[probe['context_id']]
            if 'trajectory' in context:
                entries, _ = independent.synthetic_entries(context['trajectory'])
            else:
                entries, _ = independent.archived_entries(episodes[context['provenance']['episode_id']],
                                                          context['provenance']['decision'])
            self.assertEqual(independent.answer(entries, context['observation']['legal_actions'], probe['family'],
                                                probe['arg']), probe['key'], probe['probe_id'])

    def test_independent_keys_import_nothing(self):
        tree = ast.parse((ROOT / 'research/evidence_comprehension_v1/independent.py').read_text(encoding='utf-8'))
        self.assertEqual([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))], [])

    def test_archived_contexts_are_the_exact_live_observations(self):
        _, episodes = B.archived_episodes()
        for context in (c for c in FROZEN['contexts'] if c['condition'] == 'archived_with_grids'):
            p = context['provenance']
            call = episodes[p['episode_id']]['calls'][p['call_index']]
            self.assertEqual(call['request_sha256'], p['request_sha256'])
            self.assertEqual(json.loads(call['request']['messages'][1]['content'])['observation'], context['observation'])

    def test_requests_carry_only_the_observation_and_question(self):
        for probe in PROBES:
            request = P.build_request(CONTEXTS[probe['context_id']], probe)
            user = json.loads(request['messages'][1]['content'])
            self.assertEqual(set(user), {'observation', 'question'})
            self.assertNotIn('"events"', request['messages'][1]['content'])
            self.assertEqual((request['temperature'], request['seed']), (0, 0))

    def test_every_key_is_valid_under_an_independent_schema_validator(self):
        for probe in PROBES:
            validator = Draft202012Validator(P.response_format(probe['family'])['json_schema']['schema'])
            self.assertEqual(list(validator.iter_errors({'answer': probe['key']})), [], probe['probe_id'])

    def test_gated_coverage_minimums(self):
        counts = json.loads(B.SUMMARY.read_bytes())['counts']
        for label in ('acknowledged_no_change', 'changed_then_returned', 'dispatch_failed', 'final_frame_changed',
                      'outcome_unknown', 'not_shown'):
            self.assertGreaterEqual(counts.get(f'evidence_only/outcome_class/key={label}', 0), 9, label)
        for family in P.FAMILIES:
            self.assertGreaterEqual(counts.get(f'evidence_only/{family}/best_shortcut_wrong', 0), 10, family)
        self.assertGreaterEqual(counts.get('evidence_only/observed_effect/near_miss_click', 0), 10)


class R1Finding1Prompt(unittest.TestCase):
    def test_prompt_is_a_questionnaire_not_a_policy_decision(self):
        self.assertNotIn(P.LIVE_CHOICE_IMPERATIVE, P.SYSTEM_PROMPT)
        self.assertIn(P.LIVE_CHOICE_IMPERATIVE, LIVE_PROMPT)  # the departure is from the live prompt
        self.assertNotIn('choose exactly one', P.SYSTEM_PROMPT)
        self.assertIn('not a policy decision', P.SYSTEM_PROMPT)
        for span in (P.LIVE_ARGUMENT_RULES, P.LIVE_EFFECT_NOTE):  # factual rules kept verbatim
            self.assertIn(span, LIVE_PROMPT)
            self.assertIn(span, P.SYSTEM_PROMPT)
        self.assertEqual(FROZEN['system_prompt'], P.SYSTEM_PROMPT)


class R1Finding2SchemaValidation(unittest.TestCase):
    ids = next(p for p in PROBES if p['family'] == 'available_actions')
    recall = next(p for p in PROBES if p['family'] == 'recall_action' and p['key'] != 'not_shown')
    tried = next(p for p in PROBES if p['family'] == 'tried_unchanged')
    outcome = next(p for p in PROBES if p['family'] == 'outcome_class')

    def invalid(self, probe, answer_json):
        row = score(probe, answer_json)
        self.assertFalse(row['valid'], answer_json)
        self.assertFalse(row['correct'], answer_json)

    def test_reviewer_case_nine_copies_is_invalid(self):
        self.invalid(next(p for p in PROBES if p['family'] == 'coordinate_actions' and p['key'] == [6]),
                     '{"answer":[6,6,6,6,6,6,6,6,6]}')

    def test_length_and_numeric_bounds(self):
        for text in ('{"answer":[1,2,3,4,5,6,7,1,2]}', '{"answer":[8]}', '{"answer":[-1]}', '{"answer":[true]}',
                     '{"answer":[6.0]}', '{"answer":[1.5]}', '{"answer":"1"}', '{"answer":null}'):
            self.invalid(self.ids, text)
        action = {'action_id': 1, 'action_data': {}}
        self.invalid(self.tried, json.dumps({'answer': [action] * 9}))

    def test_malformed_action_objects(self):
        for bad in ({'action_id': 8, 'action_data': {}}, {'action_id': -1, 'action_data': {}},
                    {'action_id': 6, 'action_data': {'x': 64, 'y': 0}}, {'action_id': 6, 'action_data': {'x': 0, 'y': -1}},
                    {'action_id': 6, 'action_data': {'x': '3', 'y': 4}}, {'action_id': 6, 'action_data': {'x': 3.5, 'y': 4}},
                    {'action_id': 6, 'action_data': {'x': 3, 'z': 4}}, {'action_id': 6}, {'action_data': {}},
                    {'action_id': 1, 'action_data': {}, 'extra': 1}, {'action_id': True, 'action_data': {}},
                    {'action_id': 6.0, 'action_data': {'x': 1, 'y': 1}}, [6, 1, 1]):
            with self.subTest(bad=bad):
                self.invalid(self.recall, json.dumps({'answer': bad}))
                self.invalid(self.tried, json.dumps({'answer': [bad]}))

    def test_envelope_and_labels(self):
        for text in ('not json', '[]', '{}', '{"answer":"final_frame_changed","why":"x"}', '{"answer":"maybe"}',
                     '{"answer":NaN}', '{"Answer":"not_shown"}'):
            self.invalid(self.outcome, text)

    def test_duplicates_within_the_schema_are_valid_and_recorded(self):
        probe = next(p for p in PROBES if p['family'] == 'available_actions' and len(p['key']) > 1)
        row = score(probe, json.dumps({'answer': list(reversed(probe['key'])) + probe['key'][:1]}))
        self.assertTrue(row['valid'] and row['correct'] and row['duplicate_items'])
        self.assertEqual(validate('tried_unchanged', '{"answer": []}'), [])


class R1Finding3Continuity(unittest.TestCase):
    def trajectories(self):
        return [c['trajectory'] for c in FROZEN['contexts'] if 'trajectory' in c]

    def test_every_synthetic_trajectory_is_continuous(self):
        for t in self.trajectories():
            self.assertEqual(P.continuity_errors(t), [], t['context_id'])
            independent.check_continuity(t)

    def test_discontinuous_trajectories_are_detected_by_both_checks(self):
        # r1 combined independent fixture pre/post frames, so an acknowledged result need not be the next
        # starting frame. Reproduce that defect after an acknowledged event and after a failed dispatch.
        import random
        for kind in ('no_change', 'final_change', 'transient', 'dispatch_failed'):
            t = next(t for t in self.trajectories()
                     if any(e['kind'] == kind for e in t['events'][:-1]))
            i = next(i for i, e in enumerate(t['events'][:-1]) if e['kind'] == kind)
            broken = copy.deepcopy(t)
            broken['events'][i + 1]['pre'] = P.encode_frame(P.mutate(random.Random(0),
                                                                      P.decode_frame(broken['events'][i + 1]['pre'])))
            with self.subTest(kind=kind):
                self.assertTrue(P.continuity_errors(broken))
                with self.assertRaises(ValueError):
                    independent.check_continuity(broken)

    def test_failed_dispatch_never_changes_the_current_frame(self):
        for t in self.trajectories():
            for i, event in enumerate(t['events']):
                if event['kind'] == 'dispatch_failed':
                    following = t['events'][i + 1]['pre'] if i + 1 < len(t['events']) else t['final']
                    self.assertEqual(event['pre'], following)


class R1Finding4OperationalLabels(unittest.TestCase):
    gate = [p for p in PROBES if p['condition'] == P.GATE_CONDITION]

    def test_labels_are_operational(self):
        report = analyze(PROBES, {'pass_1': oracle(PROBES), 'pass_2': oracle(PROBES)})
        labels = {m['label'] for m in report['both_correct'].values()}
        self.assertLessEqual(labels, {'criterion_met', 'below_accuracy_floor', 'inconclusive', 'not_diagnostic',
                                      'incomplete'})
        self.assertEqual(set(report['gate'].values()), {'criterion_met'})
        family = report['both_correct']['evidence_only/outcome_class']
        for key in ('context_bootstrap_95', 'contexts', 'contexts_all_correct', 'best_shortcut',
                    'shortcut_disagreement_n', 'shortcut_disagreement_accuracy'):
            self.assertIn(key, family)
        self.assertEqual(family['contexts_all_correct'], family['contexts'])

    def test_best_shortcut_responder_cannot_meet_the_criterion(self):
        best = best_shortcuts(self.gate)
        wrong = {p['probe_id'] for p in self.gate if best[(p['condition'], p['family'])][0] not in p['shortcuts_correct']}
        report = analyze(self.gate, {'pass_1': oracle(self.gate, wrong), 'pass_2': oracle(self.gate, wrong)})
        self.assertNotIn('criterion_met', report['gate'].values())

    def test_accuracy_bands(self):
        probes = [p for p in self.gate if p['family'] == 'recall_action']
        best = best_shortcuts(probes)[('evidence_only', 'recall_action')][0]
        hard = [p for p in probes if best not in p['shortcuts_correct']]
        easy = [p for p in probes if best in p['shortcuts_correct']]
        # 20% wrong on shortcut-disagreement questions only: overall >= 0.90 may hold, but the criterion fails.
        wrong = {p['probe_id'] for p in hard[: len(hard) // 5 + 1]}
        self.assertEqual(analyze(probes, {'pass_1': oracle(probes, wrong), 'pass_2': oracle(probes, wrong)})['gate']['recall_action'], 'inconclusive')
        wrong = {p['probe_id'] for p in (easy + hard)[: int(len(probes) * 0.4)]}
        self.assertEqual(analyze(probes, {'pass_1': oracle(probes, wrong), 'pass_2': oracle(probes, wrong)})['gate']['recall_action'], 'below_accuracy_floor')

    def test_two_passes_report_agreement_and_both_correct(self):
        first = oracle(self.gate)
        flipped = {self.gate[0]['probe_id']}
        report = analyze(self.gate, {'pass_1': first, 'pass_2': oracle(self.gate, flipped)})
        family = f"evidence_only/{self.gate[0]['family']}"
        self.assertEqual(report['agreement'][family]['identical_answers'], report['agreement'][family]['n'] - 1)
        self.assertEqual(report['both_correct'][family]['correct'],
                         report['single_pass_diagnostics']['pass_1']['groups'][family]['correct'] - 1)


class R1Finding5MatchedGrids(unittest.TestCase):
    def test_every_grid_question_has_a_matched_no_grid_twin(self):
        with_grids = [p for p in PROBES if p['condition'] == 'archived_with_grids']
        by_id = {p['probe_id']: p for p in PROBES}
        self.assertTrue(with_grids)
        for p in with_grids:
            twin = by_id[p['probe_id'].replace('archived_with_grids:', 'archived_without_grids:', 1)]
            for field in ('family', 'arg', 'question', 'key', 'source_context'):
                self.assertEqual(p[field], twin[field])
            full = CONTEXTS[p['context_id']]['observation']
            bare = CONTEXTS[twin['context_id']]['observation']
            self.assertEqual(set(full) - set(bare), set(P.GRID_FIELDS))
            self.assertEqual({k: v for k, v in full.items() if k not in P.GRID_FIELDS}, bare)

    def test_matched_table_is_reported(self):
        report = analyze(PROBES, {'pass_1': oracle(PROBES), 'pass_2': oracle(PROBES)})
        table = report['matched']['archived_with_grids_vs_archived_without_grids']
        self.assertTrue(all(row['both'] == row['n'] for row in table.values()))


class R1Finding6LegacyDescription(unittest.TestCase):
    def test_dimension_changes_never_enter_the_gate(self):
        for p in PROBES:
            if p['condition'] == P.GATE_CONDITION:
                self.assertNotIn('dimension_change_in_history', p['strata'], p['probe_id'])
        legacy = [p for p in PROBES if p['condition'] == 'legacy_description']
        self.assertTrue(legacy and all('dimension_change_in_history' in p['strata'] for p in legacy))

    def test_corrected_twin_differs_only_in_the_description_text(self):
        by_id = {p['probe_id']: p for p in PROBES}
        for p in (p for p in PROBES if p['condition'] == 'legacy_description'):
            twin = by_id[p['probe_id'].replace('legacy_description:', 'corrected_description:', 1)]
            self.assertEqual((p['question'], p['key']), (twin['question'], twin['key']))
            a = copy.deepcopy(CONTEXTS[p['context_id']]['observation'])
            b = copy.deepcopy(CONTEXTS[twin['context_id']]['observation'])
            self.assertNotEqual(a['action_effect_history']['fields'], b['action_effect_history']['fields'])
            self.assertEqual(b['action_effect_history']['fields'], P.CORRECTED_FIELDS_TEXT)
            a['action_effect_history'].pop('fields')
            b['action_effect_history'].pop('fields')
            self.assertEqual(a, b)

    def test_gate_ignores_the_legacy_group(self):
        legacy = {p['probe_id'] for p in PROBES if p['condition'] == 'legacy_description'}
        report = analyze(PROBES, {'pass_1': oracle(PROBES, legacy), 'pass_2': oracle(PROBES, legacy)})
        self.assertEqual(set(report['gate'].values()), {'criterion_met'})


class R2Finding1MissingEvidence(unittest.TestCase):
    """Review of r2 at 1a6bf29: absent passes or answers must never pass the gate."""
    gate = [p for p in PROBES if p['condition'] == P.GATE_CONDITION]

    def test_zero_passes_is_incomplete(self):
        report = analyze(self.gate, {})
        self.assertEqual(set(report['gate'].values()), {'incomplete'})
        self.assertEqual(report['gate_status'], 'incomplete')
        self.assertEqual(report['passes_missing'], ['pass_1', 'pass_2'])
        coordinate = report['both_correct']['evidence_only/coordinate_actions']
        self.assertEqual((coordinate['correct'], coordinate['missing']), (0, coordinate['n']))

    def test_one_perfect_pass_is_incomplete_but_diagnosed(self):
        for present in ('pass_1', 'pass_2'):
            report = analyze(self.gate, {present: oracle(self.gate)})
            self.assertEqual(set(report['gate'].values()), {'incomplete'}, present)
            self.assertEqual(report['gate_status'], 'incomplete')
            diagnostics = report['single_pass_diagnostics'][present]['groups']
            self.assertEqual(diagnostics['evidence_only/coordinate_actions']['label'], 'criterion_met')

    def test_two_empty_passes_have_no_agreement(self):
        report = analyze(self.gate, {'pass_1': {}, 'pass_2': {}})
        self.assertEqual(set(report['gate'].values()), {'incomplete'})
        row = report['agreement']['evidence_only/coordinate_actions']
        self.assertEqual((row['valid_pairs'], row['identical_answers'], row['missing_pairs']), (0, 0, row['n']))

    def test_interrupted_second_pass_is_incomplete(self):
        first = oracle(self.gate)
        # Pass 2 runs in reverse order; interrupted after 60% of its calls, the earliest probes stay unanswered.
        answered = self.gate[::-1][: int(len(self.gate) * 0.6)]
        report = analyze(self.gate, {'pass_1': first, 'pass_2': oracle(answered)})
        self.assertEqual(report['gate_status'], 'incomplete')
        unanswered = {p['family'] for p in self.gate if p not in answered}
        self.assertTrue(unanswered)
        for family in unanswered:
            self.assertEqual(report['gate'][family], 'incomplete', family)

    def test_interrupted_first_pass_is_incomplete(self):
        answered = self.gate[: len(self.gate) // 3]
        report = analyze(self.gate, {'pass_1': oracle(answered)})
        self.assertEqual(report['gate_status'], 'incomplete')
        self.assertEqual(set(report['gate'].values()), {'incomplete'})

    def test_single_missing_answer_blocks_its_family(self):
        rows = oracle(self.gate)
        victim = next(p for p in self.gate if p['family'] == 'tried_unchanged')
        second = dict(rows)
        del second[victim['probe_id']]
        report = analyze(self.gate, {'pass_1': rows, 'pass_2': second})
        self.assertEqual(report['gate']['tried_unchanged'], 'incomplete')
        self.assertEqual(report['gate_status'], 'incomplete')
        self.assertEqual({v for f, v in report['gate'].items() if f != 'tried_unchanged'}, {'criterion_met'})

    def test_invalid_pairs_are_counted_apart_from_agreement(self):
        rows = oracle(self.gate)
        probe = next(p for p in self.gate if p['family'] == 'outcome_class')
        second = dict(rows)
        second[probe['probe_id']] = score(probe, 'not json')
        report = analyze(self.gate, {'pass_1': rows, 'pass_2': second})
        row = report['agreement']['evidence_only/outcome_class']
        self.assertEqual((row['invalid_pairs'], row['valid_pairs'], row['identical_answers'], row['missing_pairs']),
                         (1, row['n'] - 1, row['n'] - 1, 0))
        self.assertEqual(report['gate_status'], 'complete')  # an invalid answer is answered, and scored wrong
        self.assertEqual(report['both_correct']['evidence_only/outcome_class']['correct'], row['n'] - 1)

    def test_unidentified_passes_are_rejected(self):
        for bad in ([oracle(self.gate), oracle(self.gate)], {'pass_3': {}}, {'1': {}}):
            with self.assertRaises(ValueError):
                analyze(self.gate, bad)


if __name__ == '__main__':
    unittest.main()
