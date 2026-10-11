"""The independent session evaluator (research/feedback_action_v1/live_evaluation.py): replay of retained evidence,
reconstruction of carried statements and their citations, online recomputation of F2a and F5, failure rules and
the two-session pooling (CPU; scripted model; real offline engine and synthetic boundaries)."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from research.feedback_action_v1 import live_evaluation as LE
from research.feedback_action_v1.live import policy as P, runner as R
from research.feedback_action_v1.live.engine import DevelopmentAdapter
from research.feedback_action_v1.live.fake_server import FakeServer
from tests.test_feedback_action_v1_dispatch import SyntheticAdapter


def real_session(session, mode='normal', invalid_calls=()):
    from research.grounded_action_v1.engine import restore_game_mount
    with tempfile.TemporaryDirectory() as tmp:
        games = restore_game_mount(Path(tmp) / 'games')
        report = R.run(Path(tmp) / 'run', FakeServer(mode, invalid_calls), lambda g, a, e: DevelopmentAdapter(
            g, a, e, games, Path(tmp) / 'rec'), spec=P.session_spec(session))
        return R.load(Path(tmp) / 'run'), report


def synthetic_session(mode, faults=None, invalid_calls=(), spec_change=None):
    """One synthetic pair run as session 1 would be, evaluated against a spec rebuilt the same way."""
    game = f'syn-{mode}'
    spec = P.session_spec(1)
    spec['cases'] = [{'game_id': game, 'environment_seed': 0, 'initial_available_actions': [1, 2], 'win_levels': 2,
                      'initial_canonical_hash': SyntheticAdapter(game, mode).bootstrap().canonical_hash}]
    spec['schedule'] = [{'block': 1, 'pair_id': game, 'game_id': game, 'order': ['baseline', 'candidate']}]
    if spec_change:
        spec_change(spec)
    counter = [0]
    with tempfile.TemporaryDirectory() as tmp:
        R.run(Path(tmp) / 'run', FakeServer(invalid_calls=invalid_calls),
              lambda g, a, e: SyntheticAdapter(g, mode, faults, counter), spec=spec)
        return R.load(Path(tmp) / 'run'), spec


class SyntheticSpec:
    """Evaluate synthetic runs against their own spec (the synthetic game is not a frozen case)."""

    def __init__(self, spec):
        self.spec = spec

    def __enter__(self):
        self.original = LE.effective_spec
        LE.effective_spec = lambda session, root=LE.ROOT: (copy.deepcopy(self.spec), self.original(1, root)[1])
        self.holdout = LE.holdout_identifiers
        LE.holdout_identifiers = lambda root=LE.ROOT: (self.holdout(root)[0],
                                                       self.holdout(root)[1] | {c['game_id'] for c in self.spec['cases']})
        return self

    def __exit__(self, *exc):
        LE.effective_spec, LE.holdout_identifiers = self.original, self.holdout


class RealEngineSession(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run1, _ = real_session(1)

    def test_clean_session_replays_and_permits_session_two(self):
        value = LE.evaluate_session(self.run1, session=1, mode='rehearsal')
        self.assertTrue(value['replay_passed'], value['problems'])
        self.assertEqual(value['technical_validity'], 'technically_complete')
        self.assertEqual(value['stop_rules_fired'], [])
        self.assertTrue(value['session_2_permitted'])
        self.assertEqual(value['carried_statements']['mismatched'], 0)
        self.assertEqual(value['carried_statements']['checked'], 72)  # every candidate call, first ones included
        self.assertEqual(len(value['episodes']), 6)
        self.assertEqual(set(value['cost_by_arm']), {'baseline', 'candidate'})
        rates = value['episodes'][1]['metrics']['rates']
        self.assertIn(rates['citation_supply']['status'], ('defined', 'not_applicable'))

    def test_session_two_is_never_permitted_by_session_two(self):
        self.assertFalse(LE.evaluate_session(self.run1, session=2, mode='rehearsal')['session_2_permitted'])

    def test_tampered_carried_statement_is_detected(self):
        run = copy.deepcopy(self.run1)
        episode = next(e for e in run['episodes'] if e['arm'] == 'candidate')
        call = episode['calls'][5]
        user = json.loads(call['request']['messages'][1]['content'])
        self.assertTrue(user['previous_model_statement']['available'])
        user['previous_model_statement']['hypothesis'] = 'an invented earlier belief'
        call['request']['messages'][1]['content'] = json.dumps(user, sort_keys=True, separators=(',', ':'))
        call['request_sha256'] = LE.canonical_digest(call['request'])  # a consistent forgery
        value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertEqual(value['carried_statements']['mismatched'], 1)
        self.assertFalse(value['replay_passed'])
        self.assertTrue(value['failure_rules']['F1_technically_incomplete'])

    def test_forged_response_bytes_and_token_audit_are_integrity_failures(self):
        run = copy.deepcopy(self.run1)
        run['episodes'][0]['calls'][3]['response'] += ' '
        value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertTrue(value['failure_rules']['F4_integrity'])
        self.assertFalse(value['session_2_permitted'])
        run = copy.deepcopy(self.run1)
        run['episodes'][0]['calls'][3]['server_prompt_tokens'] += 1
        self.assertTrue(LE.evaluate_session(run, session=1, mode='rehearsal')['failure_rules']['F4_integrity'])

    def test_forged_success_with_a_missing_episode_is_incomplete(self):
        run = copy.deepcopy(self.run1)
        run['episodes'].pop()
        value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertEqual(value['technical_validity'], 'technically_incomplete')

    def test_forged_transition_fails_replay(self):
        run = copy.deepcopy(self.run1)
        step = run['episodes'][0]['steps'][4]
        step['raw_transition']['outcome']['after']['frames'][-1][0][0] ^= 1
        value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertFalse(value['replay_passed'])

    def test_holdout_identifier_in_a_request_fires_f3(self):
        run = copy.deepcopy(self.run1)
        holdout = sorted(LE.holdout_identifiers()[0])[0]
        run['episodes'][2]['calls'][0]['response'] = run['episodes'][2]['calls'][0]['response'] + holdout
        value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertTrue(value['failure_rules']['F3_holdout_identifier'])
        self.assertIn(holdout, value['holdout_identifiers_found'])

    def test_a_different_effective_spec_is_detected(self):
        run = copy.deepcopy(self.run1)
        run['protocol_sha256'] = '0' * 64
        self.assertIn('the run did not use the reviewed effective session spec',
                      LE.evaluate_session(run, session=1, mode='rehearsal')['problems'])


class DecisionCap(unittest.TestCase):
    def test_decision_cap_after_the_f2a_window_counts_for_f2b_without_abort(self):
        """Nine invalid outputs in the candidate arm's second episode (calls 50-58 of the session, after that arm's
        first 24 calls): the episode stops at the 32-call cap, the schedule continues, F2a does not fire."""
        run, _ = real_session(1, invalid_calls=range(50, 59))
        self.assertEqual(run['status'], 'complete')
        capped = [e for e in run['episodes'] if e['stop_reason'] == 'decision_cap']
        self.assertEqual([(e['episode_id'], len(e['calls']), len(e['steps'])) for e in capped],
                         [('b1-ls20-candidate', 32, 23)])
        value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertTrue(value['replay_passed'], value['problems'])
        self.assertEqual(value['failure_rules']['F2b_decision_cap_episodes_by_arm'], {'baseline': 0, 'candidate': 1})
        self.assertFalse(value['failure_rules']['F2a_invalid_outputs'])
        self.assertEqual(value['technical_validity'], 'technically_complete')


class SyntheticBoundariesAndAborts(unittest.TestCase):
    def test_cleared_statements_at_level_boundaries_reconstruct(self):
        run, spec = synthetic_session('level')
        with SyntheticSpec(spec):
            value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertTrue(value['replay_passed'], value['problems'])
        self.assertEqual(value['carried_statements']['mismatched'], 0)
        candidate = next(e for e in run['episodes'] if e['arm'] == 'candidate')
        sent = [json.loads(c['request']['messages'][1]['content'])['previous_model_statement'] for c in candidate['calls']]
        self.assertEqual(sent[3]['reason'], LE.REASON_CLEARED)

    def test_f5_abort_recomputed_online(self):
        # The frozen rule (gate B: floor 10): two failures within the first dispatches abort.
        run, spec = synthetic_session('reset', faults={3: 'reject', 5: 'unknown'})
        with SyntheticSpec(spec):
            value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertEqual(run['status'], 'aborted')
        self.assertEqual(value['online_abort_recomputed'], run['abort'])
        self.assertTrue(value['failure_rules']['F5_dispatch_failures'])
        self.assertFalse(value['session_2_permitted'])

    def test_f5_committed_rule_recomputed_online(self):
        # r0's rule without the floor, kept as the reference the owner's decision amends.
        def committed(spec):
            spec['limits']['session_abort'].pop('dispatch_denominator_floor', None)
        run, spec = synthetic_session('reset', faults={9: 'reject'}, spec_change=committed)
        self.assertEqual((run['status'], run['abort']['denominator_floor']), ('aborted', 0))
        with SyntheticSpec(spec):
            value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertEqual(value['online_abort_recomputed'], run['abort'])
        self.assertTrue(value['failure_rules']['F5_dispatch_failures'])

    def test_f5_floor_option_recomputed_online(self):
        def floor(spec):
            spec['limits']['session_abort']['dispatch_denominator_floor'] = 10
        run, spec = synthetic_session('reset', faults={9: 'reject'}, spec_change=floor)
        self.assertIsNone(run['abort'])  # a single failure never aborts under the floor option
        with SyntheticSpec(spec):
            value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertFalse(value['failure_rules']['F5_dispatch_failures'])
        run, spec = synthetic_session('reset', faults={9: 'reject', 19: 'unknown'}, spec_change=floor)
        self.assertEqual((run['abort']['dispatch_failures'], run['abort']['dispatched']), (2, 19))
        with SyntheticSpec(spec):
            self.assertEqual(LE.evaluate_session(run, session=1, mode='rehearsal')['online_abort_recomputed'],
                             run['abort'])

    def test_f2a_abort_recomputed_online(self):
        run, spec = synthetic_session('reset', invalid_calls=range(1, 8))
        with SyntheticSpec(spec):
            value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertEqual(run['abort']['rule'], 'F2a_invalid_outputs')
        self.assertEqual(value['online_abort_recomputed'], run['abort'])
        self.assertTrue(value['failure_rules']['F2a_invalid_outputs'])

    def test_deadline_crossed_mid_pair_is_f6_and_incomplete(self):
        """A scripted clock (5 s per reading) crosses the run deadline inside the first admitted pair."""
        game = 'syn-reset'
        spec = P.session_spec(1)
        spec['cases'] = [{'game_id': game, 'environment_seed': 0, 'initial_available_actions': [1, 2],
                          'win_levels': 2, 'initial_canonical_hash': SyntheticAdapter(game, 'reset').bootstrap().canonical_hash}]
        spec['schedule'] = [{'block': 1, 'pair_id': game, 'game_id': game, 'order': ['baseline', 'candidate']}]
        ticks = [0.0]

        def clock():
            ticks[0] += 5.0
            return ticks[0]
        with tempfile.TemporaryDirectory() as tmp:
            report = R.run(Path(tmp) / 'run', FakeServer(), lambda g, a, e: SyntheticAdapter(g, 'reset'), spec=spec,
                           deadline_seconds=700, clock=clock)
            run = R.load(Path(tmp) / 'run')
        self.assertEqual((report['status'], report['pairs'][0]['status']), ('deadline_exceeded', 'interrupted'))
        self.assertEqual(run['episodes'][-1]['status'], 'interrupted')
        with SyntheticSpec(spec):
            value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertTrue(value['failure_rules']['F6_deadline_or_cancellation'])
        self.assertEqual(value['technical_validity'], 'technically_incomplete')
        self.assertFalse(value['session_2_permitted'])

    def test_a_removed_abort_record_is_detected(self):
        run, spec = synthetic_session('reset', faults={3: 'reject', 5: 'unknown'})
        run = copy.deepcopy(run)
        run['abort'], run['status'] = None, 'complete'
        with SyntheticSpec(spec):
            value = LE.evaluate_session(run, session=1, mode='rehearsal')
        self.assertIn('session-abort record differs from the online recomputation', value['problems'])


class LiveModeSourceLock(unittest.TestCase):
    """Review P2 (Track 1): in live mode the evaluator enforces the launch gate's source-lock rules. Each of the
    review's reproductions leaves the session not technically complete and never permits session 2."""

    @classmethod
    def setUpClass(cls):
        from research.feedback_action_v1.live import binding as B
        cls.B = B
        cls.lock_name = B.review_lock(LE.ROOT)
        cls.session_run, cls.spec = synthetic_session('reset')

    def evaluate(self, root):
        with SyntheticSpec(self.spec):
            return LE.evaluate_session(self.session_run, session=1, mode='live', root=root)

    def copy_root(self, tmp):
        import shutil
        root = Path(tmp)
        lock = json.loads((LE.ROOT / self.lock_name).read_bytes())
        folder = str(Path(self.lock_name).parent)
        artifacts = [f'{folder}/{name}' for name in lock['artifacts']]
        for name in (self.lock_name, *artifacts, LE.HOLDOUT_LEDGER, *lock['bindings'], *lock['review_documents']):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(LE.ROOT / name, root / name)
        return root, lock

    def tamper(self, change):
        with tempfile.TemporaryDirectory() as tmp:
            root, lock = self.copy_root(tmp)
            change(root, lock)
            (root / self.lock_name).write_text(json.dumps(lock, indent=1, sort_keys=True) + '\n')
            return self.evaluate(root)

    def assert_refused(self, value):
        self.assertIsNone(value['review_lock_verified'])
        self.assertTrue(any(p.startswith('review lock not verified') for p in value['problems']), value['problems'])
        self.assertFalse(value['replay_passed'])
        self.assertNotEqual(value['technical_validity'], 'technically_complete')
        self.assertFalse(value['session_2_permitted'])

    def test_the_reviewed_checkout_is_verified_and_permits_session_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, _ = self.copy_root(tmp)
            value = self.evaluate(root)
        self.assertEqual(value['review_lock_verified']['review_lock'], self.lock_name)
        self.assertTrue(value['session_2_permitted'], value['problems'])

    def test_a_removed_policy_binding_with_changed_source_is_refused(self):
        policy = 'research/feedback_action_v1/live/policy.py'

        def change(root, lock):
            del lock['bindings'][policy]
            (root / policy).write_bytes((root / policy).read_bytes() + b'\n# changed after review\n')
        self.assert_refused(self.tamper(change))

    def test_a_deleted_source_and_its_binding_are_refused(self):
        # Review P2 (second): delete live/policy.py and its lock entry; the inventory must not shrink with them.
        policy = 'research/feedback_action_v1/live/policy.py'

        def change(root, lock):
            del lock['bindings'][policy]
            (root / policy).unlink()
        self.assert_refused(self.tamper(change))

    def test_empty_runtime_bindings_are_refused(self):
        self.assert_refused(self.tamper(lambda root, lock: lock.update(bindings={})))

    def test_a_wrong_scope_is_refused(self):
        self.assert_refused(self.tamper(lambda root, lock: lock.update(scope='some-other-study')))

    def test_a_gpu_enabled_lock_is_refused(self):
        self.assert_refused(self.tamper(lambda root, lock: lock.update(gpu_enabled=True)))

    def test_a_missing_review_document_is_refused(self):
        self.assert_refused(self.tamper(lambda root, lock: lock['review_documents'].pop(
            'research/feedback_action_v1/live_evaluation.py')))


class TwoSessions(unittest.TestCase):
    def test_pooling_applies_section_9(self):
        run1, _ = real_session(1)
        run2, _ = real_session(2)
        first = LE.evaluate_session(run1, session=1, mode='rehearsal')
        second = LE.evaluate_session(run2, session=2, mode='rehearsal')
        pooled = LE.evaluate_sessions(first, second, [run1, run2])
        self.assertTrue(pooled['technically_valid_both_sessions'])
        self.assertEqual(pooled['solving']['claim'], 'no_solving_claim')  # no level is completed in 24 actions
        self.assertEqual(set(pooled['F2b_inconclusive_reliability'].values()), {False})
        self.assertEqual(len(pooled['pooled_rates_by_game_and_arm']), 6)
        self.assertIn('not evidence of reliable grounding', pooled['exploratory_thresholds']['note'])


if __name__ == '__main__':
    unittest.main()
