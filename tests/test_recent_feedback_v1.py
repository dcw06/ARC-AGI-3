"""Causal input boundary and independent summary/replay regressions, CPU only."""
from copy import deepcopy
import json
import unittest

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import request_for
from research.recent_feedback_v1.audit import audit_episode, baseline_request
from research.recent_feedback_v1.episodes import episode
from research.recent_feedback_v1.interface import SUMMARY_BYTE_LIMIT, recent_summary, request_for_variant


def observation():
    return {'grid': [[0]*64 for _ in range(64)], 'state': 'NOT_FINISHED',
            'levels_completed': 0, 'legal_actions': [1, 6]}


def fixture():
    obs = observation()
    return {'case_id': 'synthetic', 'game_id': 'synthetic', 'grid': obs['grid'],
            'grid_sha256': digest(obs['grid']), 'geometry': {'reviewed': []}}


def body(history=None, current=None):
    history = history or []
    return request_for(observation(), [], current or observation(), history, len(history), 'fixture')


def transition(step=0, after=None):
    return {'step': step, 'before': observation(), 'after': after or observation(),
            'action': {'action_id': 6, 'action_data': {'x': 7, 'y': 9}},
            'predicted_visible_change': 'unknown'}


class Engine:
    def bootstrap(self): return observation()
    def dispatch(self, action): return observation()
    def close(self):
        return {'closed': True, 'local_scorecard_opened': True, 'local_scorecard_closed': True, 'online_calls': 0}


class RecentFeedbackChecks(unittest.TestCase):
    def test_baseline_request_is_unchanged_and_not_mutated(self):
        original = body([transition()])
        prior = deepcopy(original)
        self.assertEqual(request_for_variant(original, 'recent_raw'), original)
        request_for_variant(original, 'recent_summary')
        self.assertEqual(original, prior)

    def test_summary_adds_only_one_text_part_and_preserves_all_request_settings(self):
        original = body([transition()])
        enriched = request_for_variant(original, 'recent_summary')
        summary = enriched['messages'][1]['content'].pop()
        self.assertEqual(enriched, original)
        self.assertLessEqual(len(summary['text'].encode()), SUMMARY_BYTE_LIMIT)
        self.assertEqual(summary['type'], 'text')

    def test_first_step_never_invents_feedback(self):
        self.assertEqual(recent_summary(body())['transitions'], [])

    def test_exact_unchanged_grid_is_reported_without_usefulness_label(self):
        row = recent_summary(body([transition()]))['transitions'][0]
        self.assertEqual(row['changed_cell_count'], 0)
        self.assertIsNone(row['changed_bbox_xyxy_inclusive'])
        self.assertTrue(row['before_grid_equals_current'])
        self.assertTrue(row['after_grid_equals_current'])
        self.assertEqual(set(row), {'historical_step', 'action', 'before_state', 'after_state',
            'after_levels_completed', 'changed_cell_count', 'changed_bbox_xyxy_inclusive',
            'before_grid_equals_current', 'after_grid_equals_current'})

    def test_disconnected_changes_have_inclusive_bounds_without_object_claim(self):
        after = observation()
        after['grid'][8][4], after['grid'][63][61] = 1, 2
        raw = body([transition(after=after)], current=after)
        row = recent_summary(raw)['transitions'][0]
        self.assertEqual(row['changed_cell_count'], 2)
        self.assertEqual(row['changed_bbox_xyxy_inclusive'], [4, 8, 61, 63])
        self.assertFalse(row['before_grid_equals_current'])
        self.assertTrue(row['after_grid_equals_current'])
        self.assertEqual(baseline_request(request_for_variant(raw, 'recent_summary'), 'recent_summary'), raw)

    def test_ui_corner_change_is_counted_without_progress_inference(self):
        after = observation()
        after['grid'][63][63] = 1
        row = recent_summary(body([transition(after=after)], after))['transitions'][0]
        self.assertEqual((row['changed_cell_count'], row['changed_bbox_xyxy_inclusive']), (1, [63, 63, 63, 63]))

    def test_only_last_two_displayed_transitions_enter_summary(self):
        history = [transition(i) for i in range(4)]
        expected = recent_summary(body(history))
        history[0]['after']['grid'][0][0] = 5
        history[1]['before']['grid'][0][0] = 5
        self.assertEqual(recent_summary(body(history)), expected)
        self.assertEqual([r['historical_step'] for r in expected['transitions']], [2, 3])

    def test_undisplayed_legal_controls_and_prediction_do_not_leak(self):
        h = transition()
        expected = recent_summary(body([h]))
        h['before']['legal_actions'], h['after']['legal_actions'] = [6], [1]
        h['predicted_visible_change'] = 'yes'
        h['private_function_label'] = 'must never leak'
        self.assertEqual(recent_summary(body([h])), expected)

    def test_independent_audit_refuses_false_count_bounds_state_and_extra_fields(self):
        raw = body([transition()])
        for field, value in [('changed_cell_count', 1), ('changed_bbox_xyxy_inclusive', [0, 0, 1, 1]),
                             ('before_grid_equals_current', False), ('after_state', 'WIN'),
                             ('recommended_action', 6), ('after_levels_completed', 1)]:
            enriched = request_for_variant(raw, 'recent_summary')
            part = enriched['messages'][1]['content'][-1]
            data = json.loads(part['text'])
            data['transitions'][0][field] = value
            part['text'] = json.dumps(data, sort_keys=True, separators=(',', ':'))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'independently checked'):
                baseline_request(enriched, 'recent_summary')

    def test_missing_summary_future_step_and_external_image_refuse(self):
        with self.assertRaises((ValueError, KeyError)):
            baseline_request(body([transition()]), 'recent_summary')
        wrong = body([transition()])
        meta = json.loads(wrong['messages'][1]['content'][3]['text'])
        meta['historical_step'] = 1
        wrong['messages'][1]['content'][3]['text'] = json.dumps(meta)
        with self.assertRaises(ValueError):
            recent_summary(wrong)
        wrong = body()
        wrong['messages'][1]['content'][-1]['image_url']['url'] = 'https://example.invalid/image.png'
        with self.assertRaisesRegex(ValueError, 'embedded'):
            recent_summary(wrong)

    def run_episode(self, variant, *, response=None, engine=None):
        events, calls = [], []
        def complete(request):
            calls.append(deepcopy(request))
            return response or '{"action_id":6,"action_data":{"x":7,"y":9},"predicted_visible_change":"unknown"}'
        episode(fixture(), variant, engine or Engine(), complete, events.append,
                model='fixture', deadline=10, cap=3, now=lambda: 0)
        return events, calls

    def test_both_variants_journal_exact_sent_request_and_keep_same_geometry(self):
        for variant in ('recent_raw', 'recent_summary'):
            events, calls = self.run_episode(variant)
            self.assertEqual([e['body'] for e in events if e['kind'] == 'request'], calls)
            self.assertEqual(events[0]['arm'], variant)
            result = audit_episode(fixture(), variant, events, model='fixture', cap=3, replay_engine=Engine())
            self.assertTrue(result['engine_replayed'])
            self.assertEqual(result['dispatches'], 3)
            self.assertEqual(result['arm'], variant)

    def test_invalid_answer_stops_without_repair_or_extra_call(self):
        events, calls = self.run_episode('recent_summary', response='invalid')
        self.assertEqual(len(calls), 1)
        self.assertEqual(events[-1]['stop_reason'], 'invalid_answer')
        result = audit_episode(fixture(), 'recent_summary', events, model='fixture', cap=3)
        self.assertEqual(result['dispatches'], 0)

    def test_mutated_system_prompt_with_rehashed_request_still_refuses(self):
        events, calls = self.run_episode('recent_summary')
        event = next(e for e in events if e['kind'] == 'request')
        event['body']['messages'][0]['content'] = 'changed'
        event['request_sha256'] = digest(event['body'])
        with self.assertRaisesRegex(ValueError, 'frozen request'):
            audit_episode(fixture(), 'recent_summary', events, model='fixture', cap=3)

    def test_mislabelled_arm_refuses(self):
        events, calls = self.run_episode('recent_summary')
        events[-1]['arm'] = 'recent_raw'
        with self.assertRaisesRegex(ValueError, 'variant binding'):
            audit_episode(fixture(), 'recent_summary', events, model='fixture', cap=3)


if __name__ == '__main__':
    unittest.main()
