import json
import tempfile
import unittest
from pathlib import Path
from research.ls20_discovery_mac import EvidenceMemory
from research.ls20_discovery_mac.memory import normalize_observation
from research.ls20_discovery_mac.object_effects import object_effects, transition_effects
from research.ls20_discovery_mac.models import fit, predict, plan, state_key
from research.ls20_discovery_mac.prospective import execute, verify


def obs(position=0, width=5):
    return dict(grid=[[2 if c == position else 0 for c in range(width)]],
                state='NOT_FINISHED', levels_completed=0, legal_actions=[1, 2])


def act(n=1):
    return dict(action_id=n, action_data={})


def append(memory, position, n=1):
    memory.append(act(n), dict(status='acknowledged', post=obs(position)))


def trained():
    m = EvidenceMemory('toy', obs())
    for _ in range(2):
        for n, p in [(1, 1), (1, 0), (2, 2), (2, 0)]:
            append(m, p, n)
    return m


def goal(position=2):
    return dict(kind='supplied_diagnostic_goal', state_key=state_key(normalize_observation(obs(position))))


class ObjectTests(unittest.TestCase):
    def test_literal_displacement(self):
        e = object_effects([[2, 0, 0]], [[0, 0, 2]])
        c = next(x for x in e['candidates'] if x['appearance']['color'] == 2)
        self.assertEqual(c['displacement'], [0, 2])
        self.assertEqual(c['kind'], 'translation_candidate')
        self.assertTrue(c['unique_within_candidates'])

    def test_static_duplicates_not_motion(self):
        e = object_effects([[2, 0, 2]], [[2, 0, 2]])
        self.assertFalse(any(c['kind'] == 'translation_candidate' for c in e['candidates']))
        self.assertTrue(any(not c['unique_within_candidates'] for c in e['candidates']))

    def test_merge_split_is_ambiguous(self):
        e = object_effects([[2, 0, 2]], [[2, 2, 2]])
        self.assertTrue(all(not c['unique_within_candidates'] for c in e['candidates']))

    def test_recolor_is_unmatched(self):
        e = object_effects([[2, 0]], [[7, 0]])
        self.assertIn('before:r0', e['unmatched_before'])
        self.assertIn('after:r0', e['unmatched_after'])

    def test_comotion_is_only_group_hypothesis(self):
        e = object_effects([[2, 0, 7, 0, 0]], [[0, 2, 0, 7, 0]])
        self.assertTrue(any(g['before_region_ids'] == ['before:r0', 'before:r2']
                            and g['status'] == 'tentative_group' for g in e['co_motion_groups']))

    def test_palette_permutation(self):
        a, b = [[2, 0, 7, 0, 0]], [[0, 2, 0, 7, 0]]
        e = object_effects(a, b)
        f = object_effects([[15-v for v in row] for row in a], [[15-v for v in row] for row in b])
        self.assertEqual(e['co_motion_groups'], f['co_motion_groups'])
        self.assertEqual(e['adjacency_changes'], f['adjacency_changes'])

    def test_transient_frames_retained(self):
        m = EvidenceMemory('toy', obs())
        post = normalize_observation(obs())
        post['frames'] = [obs(1)['grid'], obs()['grid']]
        m.append(act(), dict(status='acknowledged', post=post))
        self.assertEqual(len(transition_effects(m.snapshot())['records']), 2)

    def test_boundary_not_movement(self):
        m = EvidenceMemory('toy', obs())
        post = obs(1)
        post['levels_completed'] = 1
        m.append(act(), dict(status='acknowledged', post=post))
        self.assertEqual(transition_effects(m.snapshot())['records'][0]['effect']['status'], 'segment_boundary')


class ModelTests(unittest.TestCase):
    def test_two_step_plan_executes_only_first_prefix(self):
        m = EvidenceMemory('toy', obs())
        for _ in range(2):
            append(m, 1, 1)
            append(m, 2, 1)
            append(m, 0, 2)
        p = plan(m.snapshot(), goal())
        self.assertEqual(p['actions'], [act(1), act(1)])
        self.assertEqual(p['execute_prefix_length'], 1)
        self.assertEqual(plan(m.snapshot(), goal(), horizon=1)['status'], 'request_probe')
        self.assertEqual(plan(m.snapshot(), goal(), max_expansions=1)['status'], 'budget_exhausted')

    def test_schema_rejects_fabricated_goal_kind(self):
        from jsonschema import Draft202012Validator
        schema = json.loads((Path(__file__).parents[1]/'research/ls20_discovery_mac/m2_schema.json').read_text())
        validator = Draft202012Validator(schema)
        m = trained()
        validator.validate(predict(m.snapshot(), act(2)))
        p = plan(m.snapshot(), goal())
        validator.validate(p)
        p['objective']['kind'] = 'discovered_winning_condition'
        self.assertTrue(list(validator.iter_errors(p)))
    def test_insufficient_evidence_abstains(self):
        m = EvidenceMemory('toy', obs())
        self.assertEqual(predict(m.snapshot(), act())['status'], 'unknown')
        append(m, 1)
        append(m, 0)
        self.assertEqual(predict(m.snapshot(), act())['status'], 'unknown')

    def test_supported_prediction_and_shortest_plan(self):
        m = trained()
        self.assertEqual(predict(m.snapshot(), act(2))['predicted_state'], goal()['state_key'])
        p = plan(m.snapshot(), goal())
        self.assertEqual(p['actions'], [act(2)])
        self.assertEqual(p['execute_prefix_length'], 1)

    def test_planning_never_mutates_observed_memory(self):
        m = trained()
        before = m.snapshot()
        plan(before, goal())
        fit(before)
        self.assertEqual(m.snapshot(), before)

    def test_contradiction_retires_edge_permanently(self):
        m = trained()
        append(m, 0, 2)
        self.assertEqual(predict(m.snapshot(), act(2))['status'], 'unknown')
        self.assertEqual(plan(m.snapshot(), goal())['status'], 'request_probe')
        for _ in range(3):
            append(m, 2, 2)
            append(m, 0, 2)
        self.assertEqual(predict(m.snapshot(), act(2))['status'], 'unknown')
        self.assertTrue(any(e['status'] == 'contradicted' and len(e['outcomes']) == 2 for e in fit(m.snapshot())['edges']))

    def test_translation_forecast_at_unseen_position(self):
        m = EvidenceMemory('toy', obs(0, 8))
        for p in (1, 2):
            m.append(act(), dict(status='acknowledged', post=obs(p, 8)))
        prediction = predict(m.snapshot(), act())
        self.assertEqual(prediction['status'], 'unknown') # exact state not seen
        self.assertTrue(any(p['displacement'] == [0, 1] for p in prediction['object_predictions']))

    def test_bounds_and_unknown_goal(self):
        m = trained()
        self.assertEqual(plan(m.snapshot(), goal(), horizon=0)['actions'], [])
        self.assertEqual(plan(m.snapshot(), goal(4))['status'], 'request_probe')
        with self.assertRaises(ValueError):
            plan(m.snapshot(), goal(), max_expansions=True)

    def test_wrong_action_contract_rejected(self):
        m = trained()
        for a in ({'action_id': True, 'action_data': {}}, {'action_id': 1, 'action_data': {'x': 1, 'y': 1}}):
            with self.assertRaises(ValueError):
                predict(m.snapshot(), a)

    def test_new_level_invalidates_all_models(self):
        m = trained()
        post = obs(1)
        post['levels_completed'] = 1
        m.append(act(), dict(status='acknowledged', post=post))
        self.assertEqual(fit(m.snapshot())['edges'], [])


class ProtocolTests(unittest.TestCase):
    def test_post_state_from_other_episode_rejected(self):
        from research.ls20_discovery_mac.memory import digest
        with tempfile.TemporaryDirectory() as root:
            first, second = Path(root)/'first', Path(root)/'second'
            for name, directory in [('first', first), ('second', second)]:
                m = EvidenceMemory(name, obs())
                execute(m, act(), lambda a: dict(status='acknowledged', post=obs(1)), directory)
            wrong = json.loads((second/'step-0000.result.json').read_text())
            forecast = json.loads((first/'step-0000.prediction.json').read_text())['prediction']
            wrong['result']['prediction_sha256'] = digest(forecast)
            (first/'step-0000.result.json').write_text(json.dumps(wrong))
            (first/'step-0000.memory.json').write_bytes((second/'step-0000.memory.json').read_bytes())
            with self.assertRaisesRegex(ValueError, 'does not extend'):
                verify(first)
    def test_callback_action_mutation_does_not_rewrite_evidence(self):
        m = trained()
        with tempfile.TemporaryDirectory() as root:
            def callback(a):
                a['action_id'] = 1
                return dict(status='acknowledged', post=obs(2))
            execute(m, act(2), callback, root)
            self.assertEqual(m.snapshot()['transitions'][-1]['action'], act(2))
            verify(root)

    def test_malformed_outcome_suspends_and_replays(self):
        m = trained()
        with tempfile.TemporaryDirectory() as root:
            execute(m, act(2), lambda a: None, root)
            self.assertTrue(m.snapshot()['suspended'])
            verify(root)

    def test_failed_dispatch_is_not_counterexample(self):
        m = trained()
        with tempfile.TemporaryDirectory() as root:
            r = execute(m, act(2), lambda a: dict(status='dispatch_failed', error='not delivered'), root)
            self.assertFalse(r['scored'])
            self.assertEqual(predict(m.snapshot(), act(2))['status'], 'supported_prediction')
            verify(root)

    def test_future_prediction_tampering_rejected(self):
        m = trained()
        with tempfile.TemporaryDirectory() as root:
            execute(m, act(2), lambda a: dict(status='acknowledged', post=obs(2)), root)
            path = Path(root)/'step-0008.prediction.json'
            value = json.loads(path.read_text())
            value['prediction']['predicted_state'] = goal(1)['state_key']
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                verify(root)
    def test_sealed_before_dispatch_and_exact_replay(self):
        m = trained()
        with tempfile.TemporaryDirectory() as root:
            def dispatch(a):
                self.assertTrue((Path(root)/'step-0008.prediction.json').is_file())
                self.assertEqual(len(m.snapshot()['transitions']), 8)
                return dict(status='acknowledged', post=obs(2))
            result = execute(m, act(2), dispatch, root, planned=plan(m.snapshot(), goal()))
            self.assertTrue(result['correct'])
            self.assertEqual(verify(root), {'verified_steps': 1})

    def test_counterexample_invalidates_plan(self):
        m = trained()
        with tempfile.TemporaryDirectory() as root:
            r = execute(m, act(2), lambda a: dict(status='acknowledged', post=obs(0)), root,
                        planned=plan(m.snapshot(), goal()))
            self.assertTrue(r['plan_invalidated'])
            self.assertEqual(r['next_action'], 'request_probe')
            self.assertEqual(plan(m.snapshot(), goal())['status'], 'request_probe')
            verify(root)

    def test_stale_plan_never_dispatches(self):
        m = trained()
        p = plan(m.snapshot(), goal())
        append(m, 1)
        with tempfile.TemporaryDirectory() as root, self.assertRaises(ValueError):
            execute(m, act(2), lambda a: self.fail('must not dispatch'), root, planned=p)

    def test_crash_seal_blocks_retry(self):
        m = trained()
        with tempfile.TemporaryDirectory() as root:
            (Path(root)/'step-0008.prediction.json').write_text('{}')
            with self.assertRaises(FileExistsError):
                execute(m, act(2), lambda a: self.fail('must not dispatch'), root)

    def test_exception_suspends(self):
        m = trained()
        with tempfile.TemporaryDirectory() as root:
            def dispatch(a):
                raise TimeoutError()
            self.assertEqual(execute(m, act(2), dispatch, root)['next_action'], 'stop')
            self.assertTrue(m.snapshot()['suspended'])
            verify(root)
            with self.assertRaises(ValueError):
                plan(m.snapshot(), goal())

    def test_tampered_score_rejected(self):
        m = trained()
        with tempfile.TemporaryDirectory() as root:
            execute(m, act(2), lambda a: dict(status='acknowledged', post=obs(2)), root)
            path = Path(root)/'step-0008.result.json'
            value = json.loads(path.read_text())
            value['result']['correct'] = False
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                verify(root)


if __name__ == '__main__':
    unittest.main()
