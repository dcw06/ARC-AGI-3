"""Stagnation supervision v1 (Track 3): connected-path CPU rehearsal through the derived process stack.

launcher -> supervisor -> worker -> model host -> bridge -> runner, with the scripted rehearsal transport, the offline
development engine and injected GPU probes; then the independent evaluator on the retained evidence. Rehearsal-only
overrides shorten it to one game group and 12 actions per episode. No model, no GPU."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from research.stagnation_supervision_v1.closed_loop import bridge as B, evaluate as EV
from research.stagnation_supervision_v1.closed_loop.resources import independent_cleanup

SHORT = {'SSV_REHEARSAL_GROUPS': 'b1-ar25', 'SSV_REHEARSAL_ACTIONS': '12'}


def connected(fault='none', *, seconds=1500, actions=12, admission_seconds=None, details=False):
    from scripts.rehearse_stagnation_supervision_v1 import rehearse
    short = {**SHORT, 'SSV_REHEARSAL_ACTIONS': str(actions)}
    if admission_seconds is not None:
        short['SSV_REHEARSAL_GROUP_ADMISSION_SECONDS'] = str(admission_seconds)
    with mock.patch.dict(os.environ, short):
        receipt, output = rehearse(fault, seconds, tempfile.mkdtemp(prefix='ssv-connected-'), session='1')
        spec = B.session_run_spec('1', 'rehearsal')
        evaluation = EV.evaluate_output(output / 'worker/run', spec)
    outer = json.loads((output / 'control/outer.json').read_bytes())
    host_path = output / 'worker/host-status.json'
    host = json.loads(host_path.read_bytes()) if host_path.is_file() else None
    if not details:
        return receipt, outer, host, evaluation

    def record(relative):
        path = output / relative
        return json.loads(path.read_bytes()) if path.is_file() else None

    return receipt, outer, host, evaluation, {
        'files': {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()},
        'gpu_cleanup': record('control/gpu-cleanup.json'),
        'first_cell_cleanup': record('control/first-cell-supervisor-cleanup.json'),
        'model_process': record('worker/model-process.json'),
        'worker_failure': record('worker/failure.json'),
        'worker_result': record('worker/worker-result.json'),
        'monitor_failure': record('monitor/failure.json'),
        'canary': record('worker/canary.json'),
        'run': record('worker/run/run.json'),
    }


class Connected(unittest.TestCase):
    def assert_owned_cleanup(self, receipt, outer, detail):
        self.assertTrue(receipt['first_cell_cleanup_verified'], receipt.get('error'))
        self.assertTrue(outer['process_groups_exited'], outer.get('error'))
        self.assertTrue(outer['independent_gpu_cleanup_verified'], outer.get('cleanup_error'))
        self.assertTrue(outer['scratch_removed'])
        self.assertTrue(detail['gpu_cleanup']['gpu_cleanup_verified'])
        self.assertEqual(detail['gpu_cleanup']['remaining_gpu_pids'], 0)
        self.assertTrue(all(v is True for v in detail['first_cell_cleanup']['groups'].values()))

    def test_normal_completion_cleanup_and_independent_replay(self):
        receipt, outer, host, evaluation = connected()
        self.assertEqual((receipt['error'], receipt['study_status']),
                         (None, 'study_complete_pending_independent_evaluation'))
        self.assertTrue(receipt['first_cell_cleanup_verified'])
        self.assertTrue(outer['process_groups_exited'] and outer['independent_gpu_cleanup_verified'])
        self.assertEqual(outer['run_evidence']['episodes'], 3)
        self.assertEqual(evaluation['problems'], [])
        self.assertTrue(evaluation['technically_complete'])
        reflections = sum(a['calls'] for a in evaluation['realised_cost']['by_arm'].values())
        self.assertEqual((host['policy_calls'], host['reflection_calls']), (36, reflections))
        self.assertEqual(evaluation['realised_cost']['by_arm']['continuation']['calls'], 0)

    def test_invalid_reflections_through_the_host_are_retained_and_replay_cleanly(self):
        receipt, outer, host, evaluation = connected('reflection_invalid')
        self.assertEqual(receipt['study_status'], 'study_complete_pending_independent_evaluation')
        self.assertEqual(evaluation['problems'], [])
        cost = evaluation['realised_cost']['by_arm']['triggered']
        self.assertEqual((cost['valid'], cost['invalid']), (0, cost['calls']))

    def test_a_transport_failure_is_honest_and_cleaned_up(self):
        receipt, outer, host, evaluation = connected('transport')
        self.assertNotEqual(receipt['study_status'], 'study_complete_pending_independent_evaluation')
        self.assertTrue(receipt['first_cell_cleanup_verified'])
        self.assertFalse(evaluation['technically_complete'])

    def test_rehearsal_fault_matrix_retains_failure_without_a_retry(self):
        for fault, seconds, actions, admission_seconds in (
            ('model_startup', 1500, 12, None),
            ('monitor_exit', 1500, 12, None),
            ('storage', 1500, 12, None),
            ('cancel', 1500, 40, None),
            ('slow', 340, 12, None),
            ('surviving_child', 1500, 12, None),
        ):
            with self.subTest(fault=fault):
                receipt, outer, host, evaluation, detail = connected(
                    fault, seconds=seconds, actions=actions, admission_seconds=admission_seconds, details=True)
                self.assertEqual(outer['fault'], fault)
                self.assert_owned_cleanup(receipt, outer, detail)
                if fault == 'surviving_child':
                    # A SIGTERM-resistant descendant is a cleanup stressor; the owner must
                    # escalate, remove it, and leave a usable completed run.
                    self.assertEqual(receipt['study_status'], 'study_complete_pending_independent_evaluation')
                    self.assertTrue(evaluation['technically_complete'], evaluation['problems'])
                    self.assertIsNotNone(detail['model_process'])
                    continue
                self.assertNotEqual(receipt['study_status'], 'study_complete_pending_independent_evaluation')
                self.assertNotEqual(outer['status'], 'study_complete_pending_independent_evaluation')
                self.assertFalse(evaluation['technically_complete'])
                self.assertIn('control/outer.json', detail['files'])
                self.assertIn('control/gpu-cleanup.json', detail['files'])
                if fault not in ('monitor_exit',):
                    self.assertIsNotNone(detail['model_process'])
                if fault in ('storage', 'cancel', 'slow'):
                    self.assertIsNotNone(detail['run'])  # partial run evidence survives
                if fault == 'model_startup':
                    self.assertIsNotNone(host)
                    self.assertEqual(host['status'], 'failed')
                if fault == 'monitor_exit':
                    self.assertIn('monitor', (outer.get('error') or '').lower())
                if fault == 'storage':
                    self.assertEqual(detail['worker_result']['run_status'], 'technical_failure')
                if fault == 'cancel':
                    self.assertIn(detail['run']['status'], ('canceled', 'deadline_exceeded'))
                if fault == 'slow':
                    # With the frozen 800-second pair admission rule, a 340-second
                    # session cannot admit play. This verifies admission rejection,
                    # not the slow transport or a mid-run deadline.
                    self.assertEqual(detail['run']['status'], 'incomplete')
                    self.assertEqual(detail['run']['pairs'][0]['status'], 'not_admitted')
                    self.assertEqual(host['policy_calls'], 0)

    def test_slow_transport_hits_the_external_deadline_after_admission(self):
        # This override is available only in rehearsal. It lets actual slow
        # requests enter a short session; the live 800-second rule is unchanged.
        receipt, outer, host, evaluation, detail = connected(
            'slow', seconds=340, admission_seconds=1, details=True)
        self.assertNotEqual(receipt['study_status'], 'study_complete_pending_independent_evaluation')
        self.assertFalse(evaluation['technically_complete'])
        self.assert_owned_cleanup(receipt, outer, detail)
        self.assertIsNotNone(detail['run'])
        self.assertGreater(host['policy_calls'], 0)
        self.assertIn('admission cutoff reserves cleanup', outer['error'])
        self.assertIn((detail['run']['status'], detail['run']['error']),
                      (('deadline_exceeded', 'run deadline enforced'),
                       ('technical_failure', 'model transport')))
        self.assertGreater(detail['run']['calls'], 0)

    def test_reflection_length_is_a_charged_invalid_reflection_not_lifecycle_failure(self):
        receipt, outer, host, evaluation, detail = connected('reflection_length', details=True)
        self.assertEqual(receipt['study_status'], 'study_complete_pending_independent_evaluation')
        self.assertTrue(evaluation['technically_complete'], evaluation['problems'])
        self.assertEqual(evaluation['problems'], [])
        self.assert_owned_cleanup(receipt, outer, detail)
        cost = evaluation['realised_cost']['by_arm']
        self.assertGreater(cost['periodic']['calls'] + cost['triggered']['calls'], 0)
        self.assertEqual(cost['periodic']['valid'] + cost['triggered']['valid'], 0)


class IndependentCleanup(unittest.TestCase):
    def test_cleanup_receipt_rejects_survivors_wrong_gpu_and_expired_deadline(self):
        class FakeProbes:
            evidence_class = 'rehearsal_injected_gpu_not_target_evidence'

            def __init__(self, uuid='GPU-TEST', pids=()):
                self.uuid, self.pids = uuid, list(pids)

            def sample(self, _expected):
                return {'uuid': self.uuid}

            def gpu_pids(self):
                return self.pids

        for label, probes, groups_absent, now in (
            ('surviving_group', FakeProbes(), False, 0),
            ('unexpected_gpu', FakeProbes(uuid='GPU-OTHER'), True, 0),
            ('remaining_gpu_pid', FakeProbes(pids=(1234,)), True, 0),
            ('deadline_expired', FakeProbes(), True, 2),
        ):
            with self.subTest(case=label):
                receipt = independent_cleanup(probes, expected_uuid='GPU-TEST', groups_absent=groups_absent,
                                              deadline=1, clock=lambda: now)
                self.assertFalse(receipt['gpu_cleanup_verified'])
                self.assertTrue(receipt['error'])

        clean = independent_cleanup(FakeProbes(), expected_uuid='GPU-TEST', groups_absent=True,
                                    deadline=1, clock=lambda: 0)
        self.assertTrue(clean['gpu_cleanup_verified'])
        self.assertEqual(clean['remaining_gpu_pids'], 0)


if __name__ == '__main__':
    unittest.main()
