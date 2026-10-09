"""Connected-path CPU rehearsals of one session: first cell -> supervisor -> worker -> monitor -> model host -> bridge
-> runner -> real offline engine -> independent evaluation (scripted model; no GPU).

Interpreters default to the test interpreter. FA1_REHEARSAL_GAME_PYTHON / FA1_REHEARSAL_MODEL_PYTHON (the installed
game and model interpreters), FA1_REHEARSAL_TOKENIZER (pinned tokenizer) and FA1_REHEARSAL_GRAMMAR=1 (pinned
guided-decoding grammar, model interpreter) make the same tests run on the successor runtime's interpreter pair.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.rehearse_feedback_action_v1 import rehearse
from scripts.evaluate_feedback_action_v1 import evaluate_output

BASE = Path.home() / 'fa1-rehearsal-tests'
SECONDS = 2400


def run_fault(fault, seconds=SECONDS, session=1):
    BASE.mkdir(exist_ok=True)
    receipt, output = rehearse(fault, seconds, tempfile.mkdtemp(dir=BASE), session=session)
    outer = json.loads((output / 'control/outer.json').read_bytes())
    return receipt, output, outer


class ConnectedRehearsals(unittest.TestCase):
    def assert_cleaned(self, outer, output):
        self.assertTrue(outer['process_groups_exited'], outer.get('error'))
        self.assertTrue(outer['independent_gpu_cleanup_verified'])
        self.assertTrue(outer['scratch_removed'])
        first = json.loads((output / 'control/first-cell-supervisor-cleanup.json').read_bytes())
        self.assertEqual(first['errors'], [])
        self.assertTrue(all(v is True for v in first['groups'].values()))

    def test_normal_session_and_unchanged_instrumentation(self):
        receipt, output, outer = run_fault('none')
        self.assertEqual(receipt['study_status'], 'study_complete_pending_independent_evaluation', outer['error'])
        self.assert_cleaned(outer, output)
        value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=SECONDS)
        self.assertTrue(value['technically_complete'], value['lifecycle_errors'])
        evaluation = value['evaluation']
        self.assertEqual((evaluation['session'], evaluation['technical_validity']), (1, 'technically_complete'))
        self.assertEqual(evaluation['carried_statements']['mismatched'], 0)
        self.assertTrue(evaluation['session_2_permitted'])
        transport = json.loads((output / 'worker/rehearsal-transport.json').read_bytes())
        self.assertEqual(transport['policy_calls'], 144)
        if os.environ.get('FA1_REHEARSAL_GRAMMAR') == '1':  # every completion accepted by the pinned grammar
            self.assertEqual((transport['grammar_checked'], transport['grammar_accepted']), (145, 145))
        # The same scripted model in-process, without supervisor, bridge or monitor: identical requests and actions.
        from research.feedback_action_v1.live import runner
        from research.feedback_action_v1.live.engine import DevelopmentAdapter
        from research.feedback_action_v1.live.fake_server import FakeServer
        from research.feedback_action_v1.live.policy import session_spec
        from research.grounded_action_v1.engine import restore_game_mount
        with tempfile.TemporaryDirectory(dir=BASE) as tmp:  # token counts may differ (tokenizer); bytes may not
            games = restore_game_mount(Path(tmp) / 'games')
            direct = runner.run(Path(tmp) / 'run', FakeServer(), lambda g, a, e: DevelopmentAdapter(
                g, a, e, games, Path(tmp) / 'rec'), spec=session_spec(1))
        connected = runner.load(output / 'worker/run')
        shape = lambda rep: [(e['episode_id'], [c['request_sha256'] for c in e['calls']],
                              [c['response'] for c in e['calls']], [s['action'] for s in e['steps']])
                             for e in rep['episodes']]
        self.assertEqual(shape(connected), shape(direct))

    def test_session_two_runs_its_own_block(self):
        receipt, output, outer = run_fault('none', session=2)
        self.assertEqual((receipt['session'], outer['session']), (2, 2))
        value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=SECONDS)
        self.assertTrue(value['technically_complete'], value['lifecycle_errors'])
        self.assertEqual([e['episode_id'] for e in value['evaluation']['episodes']],
                         ['b2-s5i5-candidate', 'b2-s5i5-baseline', 'b2-ls20-baseline', 'b2-ls20-candidate',
                          'b2-sk48-candidate', 'b2-sk48-baseline'])
        self.assertFalse(value['evaluation']['session_2_permitted'])  # only session 1 can permit session 2

    def test_failures_clean_up_and_keep_honest_evidence(self):
        cases = {  # fault: (run status, study status)
            'model_startup': (None, 'failed'),
            'transport': ('technical_failure', 'failed'),
            'monitor_exit': (None, 'failed'),
            'cancel': ('canceled', 'failed'),
            'storage': (None, 'failed'),
            'surviving_child': ('complete', 'study_complete_pending_independent_evaluation'),
            'truncated_candidate': ('complete', 'study_complete_pending_independent_evaluation'),
            'always_invalid': ('aborted', 'failed'),        # F2a: the 7th invalid output of the first arm
            'dispatch_failed': ('aborted', 'failed'),       # F5 as committed: 1 failure in the first 9 dispatches
            'dispatch_unknown': ('aborted', 'failed'),
        }
        for fault, (run_status, study) in cases.items():
            with self.subTest(fault=fault):
                receipt, output, outer = run_fault(fault)
                self.assertEqual(receipt['study_status'], study, outer['error'])
                self.assert_cleaned(outer, output)
                value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=SECONDS)
                if study == 'failed':
                    self.assertFalse(value['technically_complete'])
                if run_status is not None:
                    self.assertTrue(value['run_evidence']['verified'], value['run_evidence'])
                    self.assertEqual(value['run_evidence']['run_status'], run_status)
                if fault == 'storage':
                    self.assertFalse(value['run_evidence']['verified'])  # the interrupted checkpoint is detected
                if fault == 'surviving_child':
                    left = subprocess.run(['pgrep', '-f', 'time.sleep\\(600\\)'], capture_output=True, text=True)
                    self.assertEqual(left.stdout.strip(), '')
                if fault == 'truncated_candidate':
                    rules = value['evaluation']['failure_rules']
                    self.assertFalse(rules['F2a_invalid_outputs'])
                    invalid = [c for e in value['evaluation']['episodes'] for c in [e]
                               if e['arm'] == 'candidate' and e['metrics']['invalid_actions']]
                    self.assertTrue(invalid)  # the truncation is an invalid output of the candidate arm
                if fault in ('always_invalid', 'dispatch_failed', 'dispatch_unknown'):
                    evaluation = value['evaluation']
                    self.assertEqual(evaluation['online_abort_recomputed']['rule'],
                                     'F2a_invalid_outputs' if fault == 'always_invalid' else 'F5_dispatch_failures')
                    self.assertFalse(evaluation['session_2_permitted'])

    def test_admission_cutoff_admits_no_pair_without_the_frozen_allowance(self):
        """A lifecycle too short for one pair's 600 s allowance: nothing is played, every pair is recorded as not
        admitted, the run is incomplete and cleanup still completes. (A deadline crossed mid-pair is exercised with
        a scripted clock in tests/test_feedback_action_v1_live_evaluation.py.)"""
        receipt, output, outer = run_fault('none', seconds=420)
        self.assertEqual(receipt['study_status'], 'failed')
        self.assert_cleaned(outer, output)
        value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=420)
        self.assertFalse(value['technically_complete'])
        self.assertEqual(value['run_evidence']['run_status'], 'incomplete')
        from research.feedback_action_v1.live import runner
        run = runner.load(output / 'worker/run')
        self.assertEqual({p['status'] for p in run['pairs']}, {'not_admitted'})
        self.assertEqual((run['calls'], run['dispatches'], run['episodes']), (0, 0, []))


if __name__ == '__main__':
    unittest.main()
