"""Evidence comprehension v2 (revision 1): frozen question set, dual keys, isolated conditions, decision rules."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from research.action_effect_v1.records import effect_record
from research.evidence_comprehension_v1 import probes as V1
from research.evidence_comprehension_v2 import independent, probes as P, representation as R, trajectories as T
from research.evidence_comprehension_v2.score import analyze, score, track_verdict, validate
from scripts import build_evidence_comprehension_v2 as B

ROOT = Path(__file__).resolve().parents[1]
FROZEN = json.loads(B.OUTPUT.read_bytes())
CONTEXTS = {c['context_id']: c for c in FROZEN['contexts']}
PROBES = FROZEN['probes']
BY_PAIR = {}
for _p in PROBES:
    BY_PAIR.setdefault(_p['pair_id'], {})[_p['condition']] = _p


def request(probe):
    return P.build_request(CONTEXTS[probe['context_id']], probe)


def user(probe):
    return json.loads(request(probe)['messages'][1]['content'])


def wrong_answer(probe):
    key = probe['key']
    schema = P.ANSWER_SCHEMAS[probe['family']]
    if 'enum' in schema:
        return next(v for v in schema['enum'] if v != key)
    if probe['family'] in ('recall_action',):
        return 'not_shown'
    if probe['family'] == 'tried_unchanged':
        return [{'action_id': 0, 'action_data': {}}]
    return [0] if key != [0] else []


def answers(probes, wrong=lambda p: False):
    return {p['probe_id']: score(p, json.dumps({'answer': wrong_answer(p) if wrong(p) else p['key']})) for p in probes}


def both_passes(probes, wrong=lambda p: False):
    rows = answers(probes, wrong)
    return {'pass_1': rows, 'pass_2': dict(rows)}


class QuestionSet(unittest.TestCase):
    def test_frozen_files_match_a_fresh_build(self):
        for path, raw in B.outputs(B.build()).items():
            self.assertEqual(raw, path.read_bytes(), path.name)

    def test_every_key_matches_the_independent_derivation(self):
        from scripts.build_evidence_comprehension_v1 import archived_episodes
        _, episodes = archived_episodes()
        rows = {}
        for probe in PROBES:
            context = CONTEXTS[probe['context_id']]
            source = context['source_context']
            if source not in rows:
                if context['source'] == 'synthetic':
                    trajectory = independent.resolve(FROZEN['trajectories'][source], FROZEN['frames'])
                    rows[source] = independent.window(independent.synthetic_rows(trajectory))[0]
                else:
                    p = context['provenance']
                    rows[source] = independent.window(independent.archived_rows(episodes[p['episode_id']], p['decision']))[0]
            check = independent.answer(rows[source], context['observation']['legal_actions'], probe['family'], probe['arg'])
            self.assertTrue(P.same_answer(probe['family'], check, probe['key']), probe['probe_id'])

    def test_independent_keys_import_nothing(self):
        tree = ast.parse((ROOT / 'research/evidence_comprehension_v2/independent.py').read_text(encoding='utf-8'))
        self.assertEqual([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))], [])

    def test_every_key_is_schema_valid(self):
        for probe in PROBES:
            self.assertEqual(validate(probe['family'], json.dumps({'answer': probe['key']})), probe['key'])

    def test_every_request_is_unique(self):
        hashes = [hashlib.sha256(json.dumps(request(p), sort_keys=True).encode()).hexdigest() for p in PROBES]
        self.assertEqual(len(hashes), len(set(hashes)))

    def test_partitions_are_disjoint_and_trajectories_stay_together(self):
        partition_of = {}
        for p in PROBES:
            self.assertEqual(partition_of.setdefault(p['source_context'], p['partition']), p['partition'])
        observations = {}
        for c in FROZEN['contexts']:
            if c['condition'] == 'baseline':
                text = json.dumps(c['observation'], sort_keys=True)
                self.assertNotIn(text, observations, c['context_id'])
                observations[text] = c['partition']
        self.assertEqual(set(T.PARTITIONS), {'withheld', 'development'})
        self.assertNotEqual(*[seed for seed, _ in T.PARTITIONS.values()])

    def test_withheld_coverage_meets_the_frozen_minimums(self):
        B.check_coverage(PROBES)
        withheld = [p for p in PROBES if p['partition'] == 'withheld']
        for tag in ('six_not_legal_six_in_history', 'six_legal', 'empty_history', 'neighbouring_click',
                    'not_shown', 'not_observed', 'entry:changed_then_returned', 'entry:dispatch_failed',
                    'entry:outcome_unknown', 'template:level_boundary', 'template:reset_boundary'):
            self.assertTrue(any(tag in p['strata'] for p in withheld), tag)

    def test_schedule_covers_the_repetition_policy_with_withheld_first(self):
        seen = {}
        for phase in FROZEN['schedule']:
            for pid in phase['probe_ids']:
                seen[pid] = seen.get(pid, 0) + 1
        for p in PROBES:
            self.assertEqual(seen[p['probe_id']], P.PASSES[p['partition']], p['probe_id'])
        phases = [(s['partition'], s['pass']) for s in FROZEN['schedule']]
        self.assertEqual(phases[:2], [('withheld', 'pass_1'), ('withheld', 'pass_2')])
        self.assertEqual(FROZEN['schedule'][1]['probe_ids'], list(reversed(FROZEN['schedule'][0]['probe_ids'])))


class BaselineFreeze(unittest.TestCase):
    def test_v1_baseline_files_are_unchanged(self):
        record = json.loads(B.BASELINE.read_bytes())
        for path, digest in record['files'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path)

    def test_baseline_binds_the_protocol_and_lock_the_v1_launch_used(self):
        record = json.loads(B.BASELINE.read_bytes())
        lock_raw = (ROOT / record['review_lock']).read_bytes()
        self.assertEqual(hashlib.sha256(lock_raw).hexdigest(), record['review_lock_sha256'])
        lock = json.loads(lock_raw)
        launch = json.loads((ROOT / record['launch_package_lock']).read_bytes())
        self.assertEqual(launch['review_lock_sha256'], record['review_lock_sha256'])
        protocol = record['protocol']['path']
        self.assertEqual(protocol, 'reports/evidence_comprehension_v1_protocol.md')
        self.assertEqual(lock['review_documents'][protocol], record['files'][protocol])
        self.assertIn(protocol, record['files_matching_review_lock_bindings'])
        self.assertNotIn('reports/evidence_comprehension_v1_protocol_r4.md', record['files'])
        bound = {**lock['bindings'], **lock['review_documents']}
        for path in record['files_matching_review_lock_bindings']:
            self.assertEqual(bound[path], record['files'][path], path)

    def test_baseline_prompt_is_the_frozen_v1_prompt(self):
        v1 = json.loads(B.V1_PROBES.read_bytes())
        self.assertEqual(P.BASE_PROMPT, v1['system_prompt'])
        self.assertEqual(FROZEN['v1_probe_set_sha256'], hashlib.sha256(B.V1_PROBES.read_bytes()).hexdigest())


class Isolation(unittest.TestCase):
    """Conditions differ from the baseline only by their registered intervention."""

    def test_control_candidate_changes_only_the_system_prompt_by_the_instruction(self):
        self.assertEqual(P.CONTROL_PROMPT.replace(' ' + P.CONTROL_INSTRUCTION, '', 1), P.BASE_PROMPT)
        self.assertNotEqual(P.CONTROL_PROMPT, P.BASE_PROMPT)
        pairs = [v for v in BY_PAIR.values() if 'control_candidate' in v]
        self.assertTrue(pairs)
        for pair in pairs:
            base, cand = request(pair['baseline']), request(pair['control_candidate'])
            self.assertEqual(cand['messages'][0]['content'], P.CONTROL_PROMPT)
            self.assertEqual(base['messages'][0]['content'], P.BASE_PROMPT)
            base['messages'][0] = cand['messages'][0]
            self.assertEqual(base, cand)

    def test_history_candidate_changes_only_the_history_field_with_equivalent_entries(self):
        pairs = [v for v in BY_PAIR.values() if 'history_candidate' in v]
        self.assertTrue(pairs)
        for pair in pairs:
            base, cand = request(pair['baseline']), request(pair['history_candidate'])
            self.assertEqual(base['messages'][0], cand['messages'][0])
            ub, uc = json.loads(base['messages'][1]['content']), json.loads(cand['messages'][1]['content'])
            hb, hc = ub['observation'].pop('action_effect_history'), uc['observation'].pop('action_effect_history')
            self.assertEqual(ub, uc)
            self.assertEqual([R.denormalize_entry(e) for e in hc['entries']], hb['entries'])
            self.assertEqual(hc['omitted_entries'], hb['omitted_entries'])
            base['messages'][1] = cand['messages'][1]
            self.assertEqual(base, cand)

    def test_each_track_asks_only_its_families(self):
        for p in PROBES:
            self.assertIn(P.CONDITIONS[p['condition']], (None, p['track']))
            if p['condition'] != 'baseline':
                self.assertIn('baseline', BY_PAIR[p['pair_id']])
                self.assertEqual(BY_PAIR[p['pair_id']]['baseline']['question'], p['question'])
                self.assertEqual(BY_PAIR[p['pair_id']]['baseline']['key'], p['key'])

    def test_interventions_carry_no_game_specific_content_or_recommendation(self):
        import re
        words = set(re.findall(r'[a-z0-9]+', (P.CONTROL_INSTRUCTION + json.dumps(R.CANDIDATE_DESCRIPTION)).lower()))
        for word in ('ar25', 's5i5', 'wa30', 'cd82', 'should', 'recommend', 'try', 'avoid', 'best', 'choose', 'click'):
            self.assertNotIn(word, words)


class RequestContent(unittest.TestCase):
    def test_requests_carry_only_the_observation_and_the_question(self):
        allowed = {'legal_actions', 'levels_completed', 'win_levels', 'state', 'recent_actions', 'action_effect_history',
                   'history_compaction'}
        for p in PROBES:
            payload = user(p)
            self.assertEqual(set(payload), {'observation', 'question'})
            self.assertLessEqual(set(payload['observation']), allowed)
            self.assertEqual(payload['question'], P.question_text(p['family'], p['arg']))
            content = request(p)['messages'][1]['content']
            for leak in ('"key"', 'shortcuts_correct', '"strata"', '"events"', '"template"', 'trajectory', 'withheld',
                         'development', 'pair_id', 'current_grid'):
                self.assertNotIn(leak, content)

    def test_observations_are_rebuilt_from_past_events_only(self):
        for source, packed in FROZEN['trajectories'].items():
            trajectory = independent.resolve(packed, FROZEN['frames'])
            context = CONTEXTS[f"{trajectory['partition']}:baseline:{source}"]
            self.assertEqual(T.observation(trajectory), context['observation'])

    def test_decoding_settings_are_fixed(self):
        for p in PROBES[:50]:
            r = request(p)
            self.assertEqual((r['model'], r['temperature'], r['seed'], r['max_tokens']),
                             (P.MODEL, 0, 0, P.MAX_TOKENS[p['family']]))
            self.assertEqual(r['chat_template_kwargs'], {'enable_thinking': False})


class Evidence(unittest.TestCase):
    def test_failed_or_unknown_dispatches_never_become_no_effect(self):
        for p in PROBES:
            entries = {e['step']: e for e in json.loads(json.dumps(
                CONTEXTS[f"{p['partition']}:baseline:{p['source_context']}"]['observation']))['action_effect_history']['entries']}
            unobserved = {s for s, e in entries.items() if e['status'] != 'acknowledged'}
            if isinstance(p['arg'], int) and p['arg'] in unobserved:
                if p['family'] in ('any_change', 'final_equals_pre'):
                    self.assertEqual(p['key'], 'not_observed', p['probe_id'])
                if p['family'] == 'outcome_class':
                    self.assertIn(p['key'], ('dispatch_failed', 'outcome_unknown'))
            if p['family'] == 'qualifying_steps':
                self.assertFalse(set(p['key']) & unobserved, p['probe_id'])
        for c in FROZEN['contexts']:
            if c['condition'] == 'history_candidate':
                for e in c['observation']['action_effect_history']['entries']:
                    self.assertNotIn(None, e.values())
                    if e['dispatch'] != R.DISPATCH['acknowledged']:
                        self.assertEqual((e['returned_frames'], e['final_frame']), (R.NONE_OBSERVED, R.NOT_OBSERVED))

    def test_reset_and_level_boundaries_hide_earlier_entries(self):
        checked = 0
        for source, packed in FROZEN['trajectories'].items():
            trajectory = independent.resolve(packed, FROZEN['frames'])
            boundaries = [i for i, e in enumerate(trajectory['events']) if e['kind'] in ('level_up', 'reset')]
            if not boundaries:
                continue
            checked += 1
            shown = CONTEXTS[f"{trajectory['partition']}:baseline:{source}"]['observation']['action_effect_history']
            self.assertTrue(all(e['step'] > boundaries[-1] for e in shown['entries']), source)
            for p in (q for q in PROBES if q['source_context'] == source and isinstance(q['arg'], int)):
                if p['arg'] <= boundaries[-1]:
                    self.assertEqual(p['key'], 'not_shown', p['probe_id'])
        self.assertGreaterEqual(checked, 20)
        pre_boundary = [p for p in PROBES if 'template:level_boundary' in p['strata'] and p['key'] == 'not_shown']
        self.assertTrue(pre_boundary)

    def test_a_level_change_starts_a_new_segment_in_both_derivations(self):
        base = [[0] * 8 for _ in range(8)]
        steps = [({'action_id': 1, 'action_data': {}}, 'no_change'), ({'action_id': 2, 'action_data': {}}, 'level_up'),
                 ({'action_id': 1, 'action_data': {}}, 'no_change')]
        import random
        t = {'context_id': 'x', 'legal_actions': [1, 2], **T.run(random.Random(0), base, steps)}
        shown = T.observation(t)['action_effect_history']['entries']
        self.assertEqual([e['step'] for e in shown], [2])
        self.assertEqual([r['step'] for r in independent.window(independent.synthetic_rows(t))[0]], [2])
        self.assertEqual(P.primary_key(T.observation(t), 'tried_unchanged'), [{'action_id': 1, 'action_data': {}}])

    def test_representation_round_trips_including_dimension_changes(self):
        pre = {'frames': [[[0, 1], [1, 0]]], 'levels_completed': 0}
        records = [effect_record(pre, {'action_id': 5, 'action_data': {}}, {'status': 'acknowledged', 'post': {
            'frames': [[[0]], [[0, 1], [1, 0]]], 'levels_completed': 0}}),
            effect_record(pre, {'action_id': 5, 'action_data': {}}, {'status': 'outcome_unknown', 'reason': 'timeout'})]
        from research.action_effect_v1.records import policy_view
        for i, record in enumerate(records):
            entry = {'step': i, **policy_view(record)}
            self.assertEqual(R.denormalize_entry(R.normalize_entry(entry)), entry)
        self.assertEqual(R.normalize_entry({'step': 0, **policy_view(records[0])})['returned_frames'],
                         [R.DIMENSIONS, R.SAME])
        with self.assertRaises(ValueError):
            R.normalize_entry({'step': 0, **policy_view(records[1]), 'final_frame_changed': False})


class Scoring(unittest.TestCase):
    WITHHELD = [p for p in PROBES if p['partition'] == 'withheld']

    def test_schema_validation_rejects_malformed_answers(self):
        probe = next(p for p in PROBES if p['family'] == 'qualifying_steps')
        for content in ('{"answer":[1,2,3,4,5,6,7,8,9]}', '{"answer":[1.0]}', '{"answer":[true]}', '{"answer":[64]}',
                        '{"answer":[1],"x":1}', 'not json', '{"answer":NaN}'):
            self.assertFalse(score(probe, content)['valid'], content)
        probe = next(p for p in PROBES if p['family'] == 'action6_legal')
        self.assertFalse(score(probe, '{"answer":"maybe"}')['valid'])

    def test_all_correct_is_baseline_meets_criterion_not_an_improvement(self):
        report = analyze(PROBES, both_passes(PROBES))
        self.assertEqual(report['withheld_status'], 'complete')
        self.assertEqual(report['verdicts'], {'control': 'baseline_meets_criterion', 'history': 'baseline_meets_criterion'})

    def test_missing_evidence_can_never_pass(self):
        full = both_passes(PROBES)
        one_missing = copy.deepcopy(full)
        del one_missing['pass_2'][self.WITHHELD[0]['probe_id']]
        for passes in ({}, {'pass_1': full['pass_1']}, {'pass_2': full['pass_2']}, {'pass_1': {}, 'pass_2': {}},
                       one_missing):
            report = analyze(PROBES, passes)
            self.assertEqual(report['withheld_status'], 'incomplete')
            self.assertIn('incomplete', report['verdicts'].values())
        interrupted = {'pass_1': full['pass_1'], 'pass_2': {k: v for i, (k, v) in enumerate(full['pass_2'].items())
                                                             if i < len(full['pass_2']) // 2}}
        self.assertEqual(analyze(PROBES, interrupted)['withheld_status'], 'incomplete')
        with self.assertRaises(ValueError):
            analyze(PROBES, {'pass_3': full['pass_1']})

    def test_candidate_fixing_every_baseline_target_error_is_a_clear_improvement(self):
        def wrong(p):
            return p['condition'] == 'baseline' and p['role'] == 'target' and p['track'] == 'control' and p['key'] == []
        report = analyze(PROBES, both_passes(PROBES, wrong))
        self.assertEqual(report['verdicts']['control'], 'candidate_clear_improvement')
        self.assertEqual(report['verdicts']['history'], 'baseline_meets_criterion')

    def test_a_component_regression_blocks_promotion(self):
        def wrong(p):
            return ((p['condition'] == 'baseline' and p['family'] == 'legal_coordinate_actions' and p['key'] == [])
                    or (p['condition'] == 'control_candidate' and p['family'] == 'legal_actions'))
        self.assertEqual(analyze(PROBES, both_passes(PROBES, wrong))['verdicts']['control'], 'mixed')

    def test_improvement_below_criterion_and_no_improvement(self):
        def partial(p):  # baseline wrong on every empty-key target; candidate still wrong on a third of them
            if p['family'] != 'legal_coordinate_actions' or p['key'] != []:
                return False
            return p['condition'] == 'baseline' or int(hashlib.sha256(p['pair_id'].encode()).hexdigest(), 16) % 3 == 0
        self.assertEqual(analyze(PROBES, both_passes(PROBES, partial))['verdicts']['control'], 'improved_below_criterion')

        def both(p):
            return p['family'] == 'tried_unchanged'
        self.assertEqual(analyze(PROBES, both_passes(PROBES, both))['verdicts']['history'], 'no_clear_improvement')

    def test_a_disagreement_between_passes_counts_as_wrong(self):
        passes = both_passes(PROBES)
        target = next(p for p in self.WITHHELD if p['family'] == 'tried_unchanged' and p['condition'] == 'baseline')
        passes['pass_2'][target['probe_id']] = score(target, json.dumps({'answer': wrong_answer(target)}))
        report = analyze(PROBES, passes)
        row = report['families']['withheld']['baseline']['tried_unchanged']
        self.assertEqual(row['correct'], row['n'] - 1)

    def test_verdict_refuses_absent_families(self):
        self.assertEqual(track_verdict('control', {}, {}), 'incomplete')


class Schemas(unittest.TestCase):
    def test_response_schemas_are_valid_and_strict(self):
        for family in P.FAMILIES:
            schema = P.response_schema(family)
            Draft202012Validator.check_schema(schema)
            self.assertFalse(schema['additionalProperties'])

    def test_v1_answer_schemas_are_reused_unchanged_for_v1_families(self):
        for family in ('tried_unchanged', 'outcome_class', 'observed_effect'):
            self.assertEqual(P.ANSWER_SCHEMAS[family], V1.ANSWER_SCHEMAS[family])

    def test_frame_since_step_states_that_stayed_same_compares_final_frames_only(self):
        for p in (q for q in PROBES if q['family'] == 'frame_since_step'):
            self.assertIn('compares final returned frames only', p['question'])

    def test_budget_separates_overhead_allowances_from_the_cleanup_reserve(self):
        audit = json.loads((ROOT / 'reports/evidence_comprehension_v2_token_audit.json').read_bytes())
        runtime = audit['runtime_scenarios']
        self.assertEqual(set(runtime['first_cell_overhead_allowance_seconds']),
                         {'installation', 'model_startup', 'other_pre_question', 'post_question_finalization'})
        self.assertEqual(runtime['admission_cutoff_seconds'] + runtime['cleanup_reserve_seconds'], 3300)
        for name, row in runtime['scenarios'].items():
            self.assertGreater(row['pre_question_seconds'], 500, name)
            self.assertEqual(row['first_cell_fits_before_cleanup_reserve'],
                             row['first_cell_end_seconds'] <= runtime['admission_cutoff_seconds'])

    def test_max_tokens_cover_the_longest_valid_answer(self):
        audit = json.loads((ROOT / 'reports/evidence_comprehension_v2_token_audit.json').read_bytes())
        self.assertTrue(all(row['cap_covers_longest_answer'] for row in audit['max_tokens_check'].values()))
        self.assertEqual(len(audit['requests']), len(PROBES))
        self.assertTrue(all(row['within_limits'] for row in audit['requests']))


if __name__ == '__main__':
    unittest.main()
