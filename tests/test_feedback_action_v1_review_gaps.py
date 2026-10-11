"""Regressions for the six edc9566 prelaunch findings; CPU fixtures only."""
import copy
from contextlib import nullcontext
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts import feedback_action_v1_launch as launch


@unittest.skipUnless(sys.platform == 'linux', 'real POSIX process-group ownership')
class StartupOwnership(unittest.TestCase):
    def exercise(self, point):
        child = None
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)

            def spawn(*args, **kwargs):
                nonlocal child
                child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                                         start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                if point == 'before_assignment':
                    os.kill(os.getpid(), signal.SIGINT)
                elif point == 'uncertain':
                    raise KeyboardInterrupt('spawn returned no ownership handle')
                elif point == 'registration':
                    class Handle:
                        signaled = False

                        @property
                        def pid(self):
                            if not self.signaled:
                                self.signaled = True
                                os.kill(os.getpid(), signal.SIGINT)
                            return child.pid

                        def __getattr__(self, name):
                            return getattr(child, name)
                    return Handle()
                return child

            def interrupted_start(_thread):
                raise KeyboardInterrupt('thread startup')

            try:
                with patch.object(launch.threading.Thread, 'start', interrupted_start) if point == 'thread' else nullcontext():
                    with self.assertRaises(KeyboardInterrupt):
                        launch.run_supervisor(output, output, sys.executable, sys.executable, output,
                                              started=time.monotonic(), mode='rehearsal', internal_seconds=60,
                                              session=1, spawn=spawn)
                receipt = output / 'control/first-cell-supervisor-cleanup.json'
                self.assertTrue(receipt.is_file(), 'startup interruption must retain a cleanup receipt')
                value = json.loads(receipt.read_bytes())
                if point == 'uncertain':
                    self.assertIs(value['groups_absent'], False)
                    self.assertEqual(value['ownership'], 'uncertain')
                else:
                    self.assertIsNotNone(child.poll(), 'owned supervisor survived interruption')
                    self.assertTrue(value['groups_absent'])
            finally:
                if child is not None:
                    if child.poll() is None:
                        os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
                    child.stdout.close()

    def test_thread_start_interruption_cleans_real_child(self):
        self.exercise('thread')

    def test_signal_before_assignment_is_deferred_until_registration(self):
        self.exercise('before_assignment')

    def test_uncertain_spawn_never_claims_group_absence(self):
        self.exercise('uncertain')

    def test_signal_before_group_registration_cleans_real_child(self):
        self.exercise('registration')


class FinalDeadline(unittest.TestCase):
    def test_source_removal_is_charged_before_passing_verdict(self):
        clock = [59.9]

        def remove():
            clock[0] = 60.1

        with tempfile.TemporaryDirectory() as tmp, patch.object(launch.time, 'monotonic', lambda: clock[0]), patch.object(
                launch, 'run_supervisor', return_value={
                    'status': 'study_complete_pending_independent_evaluation', 'first_cell_cleanup_verified': True}), patch(
                'research.feedback_action_v1.live.authority.rehearsal_gate'):
            result = launch.run(Path(tmp) / 'output', tmp, started=0, mode='rehearsal', internal_seconds=60,
                                source_cleanup=remove)
            self.assertIsNotNone(result['error'])
            self.assertTrue(result['extracted_source_removed'])

    def test_evidence_write_crossing_deadline_fails(self):
        clock = [59.9]
        original = launch.EvidenceStore.save

        def save(store, name, value):
            original(store, name, value)
            if name == 'notebook-cost.json':
                clock[0] = 60.1

        with tempfile.TemporaryDirectory() as tmp, patch.object(launch.time, 'monotonic', lambda: clock[0]), patch.object(
                launch.EvidenceStore, 'save', save), patch.object(launch, 'run_supervisor', return_value={
                    'status': 'study_complete_pending_independent_evaluation', 'first_cell_cleanup_verified': True}), patch(
                'research.feedback_action_v1.live.authority.rehearsal_gate'):
            result = launch.run(Path(tmp) / 'output', tmp, started=0, mode='rehearsal', internal_seconds=60)
            self.assertIsNotNone(result['error'], 'final evidence write crossed the deadline')
            self.assertGreaterEqual(result['elapsed_seconds'], 60)
            saved = json.loads((Path(tmp) / 'output/control/notebook-cost.json').read_bytes())
            self.assertIsNotNone(saved['error'])


class CanaryBounds(unittest.TestCase):
    def test_independent_canary_enforces_types_and_frozen_caps(self):
        from research.feedback_action_v1.live.fake_server import FakeServer
        from research.feedback_action_v1.live.service import validate_ready
        good = {'artifact': {'test': 'cpu'}, 'startup_seconds': 1,
                'canary_audit': FakeServer().service.canary_audit}
        validate_ready(good, good['artifact'])
        mutations = [{'server_completion_tokens': n} for n in (129, 0, True, -1, 1.0)] + [
            {'server_prompt_tokens': -1, 'tokenizer_prompt_tokens': -1},
            {'server_prompt_tokens': 60001, 'tokenizer_prompt_tokens': 60001},
            {'server_prompt_tokens': 1, 'tokenizer_prompt_tokens': True}]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(good)
                bad['canary_audit']['audit'].update(mutation)
                with self.assertRaises(ValueError):
                    validate_ready(bad, good['artifact'])


class PooledInputBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_feedback_action_v1_live_evaluation import real_session
        from research.feedback_action_v1 import live_evaluation as LE
        cls.runs = [real_session(n)[0] for n in (1, 2)]
        cls.evaluations = [LE.evaluate_session(run, session=n, mode='rehearsal')
                           for n, run in enumerate(cls.runs, 1)]

    def test_stale_successful_evaluation_cannot_certify_altered_run(self):
        from research.feedback_action_v1 import live_evaluation as LE
        runs = copy.deepcopy(self.runs)
        runs[0]['episodes'][0]['calls'][0]['response'] += ' '
        with self.assertRaises(ValueError):
            LE.evaluate_sessions(*self.evaluations, runs)

    def test_forged_evaluation_metrics_cannot_be_pooled(self):
        from research.feedback_action_v1 import live_evaluation as LE
        evaluations = copy.deepcopy(self.evaluations)
        evaluations[0]['episodes'][0]['metrics']['levels_completed'] = 999
        with self.assertRaises(ValueError):
            LE.evaluate_sessions(*evaluations, self.runs)


class ReplayEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_feedback_action_v1_live_evaluation import synthetic_session
        cls.fixture, cls.spec = synthetic_session('reset')

    def evaluate(self, run):
        from research.feedback_action_v1 import live_evaluation as LE
        from tests.test_feedback_action_v1_live_evaluation import SyntheticSpec
        with SyntheticSpec(self.spec):
            return LE.evaluate_session(run, session=1, mode='rehearsal')

    def refused(self, run):
        value = self.evaluate(run)
        self.assertFalse(value['replay_passed'], value['problems'])
        self.assertNotEqual(value['technical_validity'], 'technically_complete')
        self.assertFalse(value['session_2_permitted'])

    def test_rehashed_contract_and_observation_mutations_are_rejected(self):
        from research.feedback_action_v1 import live_evaluation as LE
        self.assertTrue(self.evaluate(self.fixture)['replay_passed'])
        for field in ('system', 'model', 'schema', 'role', 'grid', 'legal', 'history'):
            with self.subTest(field=field):
                run = copy.deepcopy(self.fixture)
                call = run['episodes'][0]['calls'][0]
                request = call['request']
                user = json.loads(request['messages'][1]['content'])
                if field == 'system':
                    request['messages'][0]['content'] += ' changed'
                elif field == 'model':
                    request['model'] = 'another-model'
                elif field == 'schema':
                    request['response_format']['json_schema']['schema'] = {'type': 'object'}
                elif field == 'role':
                    request['messages'][1]['role'] = 'assistant'
                elif field == 'grid':
                    user['observation']['current_grid'][0][0] ^= 1
                elif field == 'legal':
                    user['observation']['legal_actions'].append(3)
                else:
                    user['observation']['history_compaction']['total_transitions'] = 999
                request['messages'][1]['content'] = json.dumps(user, sort_keys=True, separators=(',', ':'))
                call['request_sha256'] = LE.canonical_digest(request)
                self.refused(run)

    def test_terminal_final_pair_and_aggregate_forgeries_are_rejected(self):
        for field in ('stop', 'final', 'pair', 'calls', 'dispatches', 'prompt_tokens', 'completion_tokens'):
            with self.subTest(field=field):
                run = copy.deepcopy(self.fixture)
                if field == 'stop':
                    run['episodes'][0]['stop_reason'] = 'win'
                elif field == 'final':
                    run['episodes'][0]['final']['levels_completed'] += 1
                elif field == 'pair':
                    run['pairs'][0]['status'] = 'not_admitted'
                else:
                    run[field] = 0
                self.refused(run)


if __name__ == '__main__':
    unittest.main()
