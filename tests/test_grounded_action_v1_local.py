"""Stage B local contract and independent replay regressions (no GPU/game)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research.grounded_action_v1.contract import audit_request, parse_policy
from research.grounded_action_v1 import contract as grounded_contract
from research.grounded_action_v1.local import ScriptedAdapter, ScriptedService, run
from research.grounded_action_v1.replay import evaluate, replay_file
from research.grounded_action_v1.model_service import TokenGuardedService


class GroundedActionLocalTests(unittest.TestCase):
    def test_target_case_binding_without_embedded_development_archive(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            for name in ('reports/perception_stage_b_v1_case_protocol.json',
                         'reports/phase4_v2_offline_package.json',
                         'reports/integrated_case_v1/initial_observation.json',
                         'reports/integrated_case_v1/geometry_reference.json',
                         'reports/phase4_transient_v2_protocol.json',
                         'certification/phase4_integrated_v2/tokenizer_manifest.json'):
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((root / name).read_bytes())
            with patch.object(grounded_contract, 'ROOT', target):
                self.assertEqual(grounded_contract.case_protocol()['game_id'], 'ar25-0c556536')
                manifest = target / 'reports/phase4_v2_offline_package.json'
                value = json.loads(manifest.read_bytes())
                value['archive_sha256'] = '0' * 64
                manifest.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, 'archive manifest drift'):
                    grounded_contract.case_protocol()

    def execute(self, service_mode='normal', adapter_mode='normal', *, clock=None, deadline_seconds=30):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / 'run.json'
        result = run(path, ScriptedService(service_mode),
                     lambda arm: ScriptedAdapter(arm, adapter_mode), deadline_seconds=deadline_seconds,
                     **({'clock': clock} if clock else {}))
        self.assertEqual(json.loads(path.read_bytes()), result)
        return result, path

    def test_complete_pair_and_transient_frame(self):
        result, path = self.execute()
        score = replay_file(path)
        self.assertEqual((score['calls'], score['dispatches']), (12, 4))
        self.assertEqual(score['episodes'][0]['outcomes'][0]['changed_frames'], [0])
        self.assertTrue(score['episodes'][1]['outcomes'][0]['target_hit'])
        self.assertFalse(score['episodes'][1]['outcomes'][0]['reviewer_visible_object_contact'])
        self.assertEqual([ep['level_delta'] for ep in score['episodes']], [0, 0])
        self.assertEqual(result['episodes'][0]['steps'][0]['after']['frames'][-1],
                         result['episodes'][0]['steps'][0]['before']['frames'][-1])

    def test_wrong_target_retained_as_process_failure(self):
        result, _ = self.execute('wrong_target')
        score = evaluate(result)
        self.assertFalse(score['episodes'][1]['outcomes'][0]['target_hit'])

    def test_valid_incorrect_feedback_remains_scored_outcome(self):
        result, _ = self.execute('wrong_feedback')
        score = evaluate(result)
        self.assertEqual(score['status'], 'valid_local_scripted_pair')
        self.assertFalse(score['episodes'][0]['outcomes'][0]['feedback_exact'])
        self.assertFalse(score['episodes'][0]['outcomes'][0]['feedback_assessment_exact'])

    def test_opposite_prediction_requires_opposite_feedback_assessment(self):
        normal, _ = self.execute()
        opposite, _ = self.execute('opposite_prediction')
        for report, expected in ((normal, 'supported'), (opposite, 'contradicted')):
            step = report['episodes'][0]['steps'][0]
            feedback_request = report['episodes'][0]['calls'][step['feedback_call']]['request']
            payload = json.loads(feedback_request['messages'][1]['content'])
            self.assertEqual(payload['committed_prediction'], step['prediction'])
            self.assertEqual(step['feedback']['assessment'], expected)
            self.assertTrue(evaluate(report)['episodes'][0]['outcomes'][0]['feedback_assessment_exact'])
        self.assertEqual(normal['episodes'][0]['steps'][0]['after'], opposite['episodes'][0]['steps'][0]['after'])
        with self.assertRaisesRegex(ValueError, 'committed prediction'):
            audit_request('feedback', normal['episodes'][0]['steps'][0]['after'],
                          normal['episodes'][0]['steps'][0]['action'],
                          before=normal['episodes'][0]['steps'][0]['before'])

    def test_seven_frame_feedback_fails_closed_without_dropping_frames(self):
        result, _ = self.execute()
        step = result['episodes'][0]['steps'][0]
        after = copy.deepcopy(step['after'])
        after['frames'] = [after['frames'][-1]] * 7
        self.assertEqual(len(after['frames']), 7)
        with self.assertRaisesRegex(ValueError, 'feedback frame admission'):
            audit_request('feedback', after, step['action'], before=step['before'],
                          prediction=step['prediction'])

    def test_candidate_request_changes_only_instruction_and_schema(self):
        result, _ = self.execute()
        a = result['episodes'][0]['calls'][0]['request']
        b = result['episodes'][1]['calls'][0]['request']
        self.assertEqual(a['messages'][1], b['messages'][1])
        self.assertEqual({k: v for k, v in a.items() if k not in ('messages', 'response_format')},
                         {k: v for k, v in b.items() if k not in ('messages', 'response_format')})
        for ep in result['episodes']:
            policy = ep['calls'][3]['request']['messages'][1]['content']
            self.assertNotIn('assessment', policy)
            self.assertNotIn('prediction', policy)

    def test_invalid_target_and_partial_response_censor_pair(self):
        for mode in ('missing_target', 'partial'):
            with self.subTest(mode=mode):
                result, _ = self.execute(mode)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['episodes'][1]['steps'], [])
                received = result['episodes'][1]['calls'][0]
                self.assertIn('response', received)
                self.assertIn('response_sha256', received)
                self.assertIn('server_prompt_tokens', received)
                self.assertIn('finish_reason', received)
                with self.assertRaisesRegex(ValueError, 'incomplete pair'):
                    evaluate(result)

    def test_token_mismatch_retained_before_rejection(self):
        result, _ = self.execute('mismatch')
        row = result['episodes'][1]['calls'][0]
        self.assertEqual(result['status'], 'failed')
        self.assertEqual((row['tokenizer_prompt_tokens'], row['server_prompt_tokens']), (10, 11))
        self.assertIn('response', row)
        self.assertEqual(result['episodes'][1]['steps'], [])

    def test_oversized_response_is_bounded_and_censors_pair(self):
        result, _ = self.execute('oversize')
        row = result['episodes'][1]['calls'][0]
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(row['response_truncated'])
        self.assertGreater(row['response_bytes'], 32768)
        self.assertLessEqual(len(row['response'].encode()), 32771)
        self.assertEqual(result['episodes'][1]['steps'], [])

    def test_transport_and_unknown_dispatch_do_not_retry(self):
        result, _ = self.execute('transport')
        self.assertEqual(result['episodes'][1]['calls'][0]['status'], 'failed')
        self.assertEqual(result['episodes'][1]['steps'], [])
        result, _ = self.execute(adapter_mode='unknown_dispatch')
        self.assertEqual(result['dispatches'], 1)
        self.assertEqual(result['episodes'][0]['steps'][0]['status'], 'dispatch_entered')

    def test_cleanup_failure_censors_result(self):
        result, _ = self.execute(adapter_mode='cleanup_failure')
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['episodes'][0]['cleanup']['closed'])
        with self.assertRaisesRegex(ValueError, 'incomplete pair'):
            evaluate(result)

    def test_deadline_stops_without_dispatch(self):
        ticks = iter(range(100))
        result, _ = self.execute(clock=lambda: next(ticks), deadline_seconds=2)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['dispatches'], 0)

    def test_independent_replay_rejects_tampering(self):
        result, _ = self.execute()
        variants = []
        incomplete = copy.deepcopy(result)
        incomplete['episodes'].pop()
        variants.append(incomplete)
        backdated = copy.deepcopy(result)
        backdated['episodes'][0]['calls'][1]['started_at'] = -1
        variants.append(backdated)
        wrong_action = copy.deepcopy(result)
        wrong_action['episodes'][0]['steps'][0]['action']['action_data']['x'] = 1
        variants.append(wrong_action)
        missing_frame = copy.deepcopy(result)
        missing_frame['episodes'][0]['steps'][0]['after']['frames'].pop(0)
        variants.append(missing_frame)
        count_drift = copy.deepcopy(result)
        count_drift['episodes'][0]['calls'][0]['server_prompt_tokens'] += 1
        variants.append(count_drift)
        uncleared = copy.deepcopy(result)
        uncleared['episodes'][1]['cleanup']['closed'] = False
        variants.append(uncleared)
        for variant in variants:
            with self.subTest(kind=variants.index(variant)):
                with self.assertRaises((ValueError, KeyError)):
                    evaluate(variant)

    def test_policy_rejects_coordinate_swap_bounds_and_duplicate_key(self):
        grid = [[0] * 4 for _ in range(3)]
        action = {'action': {'action_id': 6, 'action_data': {'x': 3, 'y': 2}},
                  'target': {'kind': 'cell', 'box': [3, 2, 3, 2]}}
        self.assertEqual(parse_policy(json.dumps(action), 'target', [6], grid), action)
        swapped = copy.deepcopy(action)
        swapped['target']['box'] = [2, 3, 2, 3]
        with self.assertRaisesRegex(ValueError, 'target bounds'):
            parse_policy(json.dumps(swapped), 'target', [6], grid)
        with self.assertRaises(ValueError):
            parse_policy('{"action":{},"action":{}}', 'target', [6], grid)

    def test_model_preflight_rejects_context_before_transport(self):
        result, _ = self.execute()
        request = result['episodes'][0]['calls'][0]['request']
        calls = []

        class Tokenizer:
            count = 10

            def apply_chat_template(self, *_args, **_kwargs):
                return [1] * self.count

        tokenizer = Tokenizer()

        def transport(value):
            calls.append(value)
            return SimpleNamespace(content='{"action":{"action_id":1,"action_data":{}}}',
                                   prompt_tokens=11, completion_tokens=16, finish_reason='stop')

        with patch('research.grounded_action_v1.model_service.verify'), \
                patch('research.grounded_action_v1.model_service.importlib.metadata.version',
                      side_effect=lambda name: {'transformers': '4.57.6', 'tokenizers': '0.22.2',
                                                'jinja2': '3.1.6'}[name]):
            service = TokenGuardedService('unused', transport, tokenizer=tokenizer)
            tokenizer.count = 65536
            with self.assertRaisesRegex(ValueError, 'pre-transport tokenizer'):
                service.complete(request)
            self.assertEqual(calls, [])
            tokenizer.count = 10
            received = service.complete(request)
            self.assertEqual((received['tokenizer_prompt_tokens'], received['server_prompt_tokens']), (10, 11))
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
