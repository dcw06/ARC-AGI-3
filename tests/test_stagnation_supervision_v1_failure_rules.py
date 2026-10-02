"""CPU-only online stopping and approved-session binding regressions."""
import copy
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

from research.stagnation_supervision_v1 import thresholds as S
from research.stagnation_supervision_v1.closed_loop import bridge as B, evaluate as E, fake_server as F
from research.stagnation_supervision_v1.closed_loop import runner as R, service as SVC
from tests.test_stagnation_supervision_v1_closed_loop import ScriptedAdapter


def run_case(schedule, *, faults=(), trigger=None, adapter_factory=None, actions=40):
    adapter = ScriptedAdapter('scripted-0000')
    case = {'game_id': 'scripted-0000', 'environment_seed': 0, 'initial_available_actions': [1, 2, 6],
            'initial_canonical_hash': adapter.obs(full_reset=True).canonical_hash, 'win_levels': 8}
    spec = {**R.protocol(), 'cases': [case], 'schedule': schedule,
            'limits': {**R.protocol()['limits'], 'actions_per_episode': actions}}
    trigger = trigger or S.load()
    with tempfile.TemporaryDirectory() as tmp:
        report = R.run(Path(tmp) / 'run', SVC.LocalService(F.FakeModelServer(faults)),
                       adapter_factory or (lambda g, arm, eid: ScriptedAdapter(g)), spec=spec,
                       supervision_factory=B.supervision_factory(spec, trigger,
                                                                 token_counter=B.fixture_token_counter()),
                       deadline_seconds=3000)
        evaluation = E.evaluate_output(Path(tmp) / 'run', spec, trigger)
    return report, evaluation, spec, trigger


def pair(name, order):
    return {'pair_id': name, 'block': 1, 'game_id': 'scripted-0000', 'order': order}


class FailureRules(unittest.TestCase):
    def test_authority_grants_only_the_selected_session(self):
        from research.stagnation_supervision_v1.closed_loop import authority as A
        review = {'status': 'reviewed_launch_source', 'scope': A.SCOPE, 'bindings': {}}
        source = {'status': 'approved', 'scope': A.SCOPE, 'approval_kind': 'source',
                  'review_lock_sha256': 'lock', 'user_response': 'yes'}
        compute = {'status': 'approved', 'scope': A.SCOPE, 'approval_kind': 'compute',
                   'review_lock_sha256': 'lock', 'user_response': 'yes',
                   'source_approval_sha256': 'sourcehash',
                   'sessions': {'1': copy.deepcopy(A.SESSION_LIMITS['1'])}}
        execution = {'scope': A.SCOPE, 'review_lock_sha256': 'lock',
                     'source_approval_sha256': 'sourcehash',
                     'compute_authorization_sha256': 'computehash',
                     'attempt_id': 'ssv1-12345678', 'session': '1'}
        reservation = {'status': 'reserved', 'attempt_id': execution['attempt_id'],
                       'seconds': A.SESSION_LIMITS['1']['authorized_seconds'],
                       'execution_sha256': 'executionhash', 'events': ['reserve']}
        rows = {A.REVIEW: review, A.SOURCE: source, A.COMPUTE: compute,
                A.EXECUTION: execution, A.RESERVATION: reservation}
        hashes = {Path(A.REVIEW).name: 'lock', Path(A.SOURCE).name: 'sourcehash',
                  Path(A.COMPUTE).name: 'computehash', Path(A.EXECUTION).name: 'executionhash'}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(A, 'LIVE_DISABLED', False), mock.patch.object(
                A, 'REQUIRED_SOURCE', set()), mock.patch.object(
                A, '_read', side_effect=lambda _root, relative: rows[relative]), mock.patch.object(
                A, '_sha', side_effect=lambda path: hashes[Path(path).name]):
            self.assertEqual(A.require(tmp), execution)
            compute['sessions']['2'] = copy.deepcopy(A.SESSION_LIMITS['2'])
            with self.assertRaises(PermissionError):
                A.require(tmp)  # a grant for both sessions is not one-attempt authorization
            compute['sessions'] = {'2': compute['sessions']['2']}
            with self.assertRaises(PermissionError):
                A.require(tmp)  # wrong session

    def test_rolling_reflection_invalid_rate_stops_arms_but_allows_continuation(self):
        schedule = [pair(f's{i}', ['periodic', 'continuation']) for i in range(1, 6)]
        report, evaluation, spec, trigger = run_case(schedule, faults=('reflection_invalid',))
        self.assertEqual(report['status'], 'failure_rule_stopped')
        self.assertEqual(report['failure_rule'], {'rule': 'reflection_interface', 'attempted': 10,
                                                  'invalid_outputs': 10})
        periodic = [e for e in report['episodes'] if e['arm'] == 'periodic']
        self.assertEqual(len(periodic), 4)
        self.assertEqual((periodic[-1]['status'], periodic[-1]['stop_reason']),
                         ('failure_rule_stopped', 'reflection_interface_stop'))
        continuation = [e for e in report['episodes'] if e['arm'] == 'continuation']
        self.assertEqual(len(continuation), 5)
        self.assertTrue(all(e['status'] == 'complete' and len(e['steps']) == 40 for e in continuation))
        self.assertEqual(report['pairs'][-1]['skipped_arms'],
                         [{'arm': 'periodic', 'reason': 'reflection_interface_stop'}])
        self.assertFalse(evaluation['technically_complete'])
        self.assertFalse(evaluation['problems'], evaluation['problems'])
        forged = copy.deepcopy(report)
        forged['status'] = 'complete'
        forged['failure_rule'] = None
        self.assertTrue(any('reflection interface stop' in p for p in
                            E.evaluate_report(forged, spec, trigger)['problems']))

    def test_dispatch_failure_aborts_before_any_later_call_and_closes_adapter(self):
        from research.stagnation_supervision_v1.closed_loop.runner import DispatchRejected

        class Reject(ScriptedAdapter):
            def dispatch(self, action, before):
                raise DispatchRejected('rejected')

        created = []
        def factory(game, arm, episode):
            obj = Reject(game)
            created.append(obj)
            return obj

        report, evaluation, spec, trigger = run_case([pair('s1', ['continuation', 'periodic']),
                                                       pair('s2', ['triggered'])], adapter_factory=factory)
        self.assertEqual(report['status'], 'failure_rule_stopped')
        self.assertEqual(report['failure_rule'], {'rule': 'dispatch_reliability',
                                                  'failed_or_unknown': 1, 'dispatches': 1})
        self.assertEqual((report['calls'], report['dispatches'], len(report['episodes'])), (1, 1, 1))
        self.assertEqual(report['episodes'][0]['cleanup'], {'closed': True})
        self.assertEqual(len(report['episodes'][0]['supervision']['events']), 1)  # detector sees failed dispatch
        self.assertEqual(report['pairs'][1]['status'], 'not_started')
        self.assertFalse(evaluation['technically_complete'])
        self.assertFalse(evaluation['problems'], evaluation['problems'])
        forged = copy.deepcopy(report)
        forged['status'] = 'complete'
        self.assertTrue(any('dispatch reliability stop' in p for p in
                            E.evaluate_report(forged, spec, trigger)['problems']))

    def test_no_detector_firings_on_full_horizon_stops_before_next_arm(self):
        trigger = copy.deepcopy(S.load())
        trigger['params'] = {name: None for name in trigger['params']}
        schedule = [pair('b1-ar25', ['continuation', 'periodic']), pair('s2', ['triggered'])]
        report, evaluation, spec, _ = run_case(schedule, trigger=trigger)
        self.assertEqual(report['status'], 'failure_rule_stopped')
        self.assertEqual(report['failure_rule'], {'rule': 'zero_detector_firings',
                                                  'episode_id': 'b1-ar25-continuation'})
        self.assertEqual(len(report['episodes']), 1)
        self.assertEqual(report['episodes'][0]['stop_reason'], 'action_cap')
        self.assertEqual(report['episodes'][0]['cleanup'], {'closed': True})
        self.assertFalse(evaluation['technically_complete'])
        self.assertFalse(evaluation['problems'], evaluation['problems'])

    def test_zero_firings_after_terminal_episode_also_stops(self):
        trigger = copy.deepcopy(S.load())
        trigger['params'] = {name: None for name in trigger['params']}
        schedule = [pair('b1-ar25', ['continuation', 'periodic'])]
        adapter = lambda g, arm, eid: ScriptedAdapter(g, event='game_over', at=2)
        report, evaluation, _, _ = run_case(schedule, trigger=trigger, adapter_factory=adapter)
        self.assertEqual(report['status'], 'failure_rule_stopped')
        self.assertEqual((report['episodes'][0]['stop_reason'], len(report['episodes'][0]['steps'])), ('game_over', 3))
        self.assertEqual(len(report['episodes']), 1)
        self.assertFalse(evaluation['problems'], evaluation['problems'])

    def test_short_rehearsal_does_not_claim_full_horizon_precondition(self):
        trigger = copy.deepcopy(S.load())
        trigger['params'] = {name: None for name in trigger['params']}
        report, evaluation, _, _ = run_case([pair('b1-ar25', ['continuation'])], trigger=trigger, actions=4)
        self.assertEqual(report['status'], 'complete')
        self.assertIs(report['full_protocol_proof'], False)
        self.assertTrue(evaluation['technically_complete'], evaluation['problems'])

    def test_live_session_mismatch_rejected_before_claim_or_spawn(self):
        from scripts import stagnation_supervision_v1_launch as launch
        from research.stagnation_supervision_v1.closed_loop import supervisor, worker
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with mock.patch('research.stagnation_supervision_v1.closed_loop.authority.require',
                            return_value={'session': '1'}), mock.patch(
                                'research.stagnation_supervision_v1.closed_loop.authority.consume_runtime') as consume:
                with self.assertRaisesRegex(PermissionError, 'launch session'):
                    launch.run(folder / 'output', folder, started=time.monotonic(), root=folder,
                               mode='live', session='2')
                consume.assert_not_called()
                self.assertFalse((folder / 'output').exists())
            with mock.patch.object(supervisor, 'gate', return_value={'session': '1'}), mock.patch.object(
                    supervisor.subprocess, 'Popen') as spawn:
                with self.assertRaisesRegex(PermissionError, 'supervisor session'):
                    supervisor.run(folder / 'output', folder, 'game', 'model', 'games',
                                   started=time.monotonic(), mode='live', session='2')
                spawn.assert_not_called()
            with mock.patch.object(worker, 'gate', return_value={'session': '1'}), mock.patch.object(
                    worker.subprocess, 'Popen') as spawn:
                with self.assertRaisesRegex(PermissionError, 'worker session'):
                    worker.run_worker(folder / 'output', folder, 'games', 'model',
                                      deadline=time.monotonic() + 30, mode='live', session='2')
                spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
