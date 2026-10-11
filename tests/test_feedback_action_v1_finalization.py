"""Interrupted certification regressions (CPU evidence; no model/GPU/provider)."""
import json
import os
from pathlib import Path
import signal
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts import feedback_action_v1_launch as launch


class FinalizationInterruption(unittest.TestCase):
    def exercise(self, fault, *, copy_evidence=None):
        clock = [419.9]
        original = launch.EvidenceStore.save
        injected = False

        def save(store, name, value, **kwargs):
            nonlocal injected
            if injected and fault == 'storage_failure':
                raise OSError('failure recording unavailable')
            result = original(store, name, value, **kwargs)
            if name == 'notebook-cost.json' and value.get('lifecycle_finalized') is True and not injected:
                injected = True
                clock[0] = 420.1
                if fault == 'signal':
                    os.kill(os.getpid(), signal.SIGINT)
                elif fault == 'system_exit':
                    raise SystemExit('after certification replace')
                else:
                    raise KeyboardInterrupt('after certification replace')
            return result

        def supervisor(output, *args, **kwargs):
            if copy_evidence is not None:
                shutil.copytree(copy_evidence, output, dirs_exist_ok=True)
                outer_path = output / 'control/outer.json'
                outer = json.loads(outer_path.read_bytes())
                outer.update(internal_seconds=420, admission_cutoff_seconds=120)
                original(launch.EvidenceStore(output, 'control'), 'outer.json', outer)
            return {'status': 'study_complete_pending_independent_evaluation',
                    'first_cell_cleanup_verified': True}

        with tempfile.TemporaryDirectory() as tmp, patch.object(launch.time, 'monotonic', lambda: clock[0]), patch.object(
                launch.EvidenceStore, 'save', save), patch.object(launch, 'run_supervisor', supervisor), patch(
                'research.feedback_action_v1.live.authority.rehearsal_gate'):
            output = Path(tmp) / 'output'
            try:
                result = launch.run(output, tmp, started=0, mode='rehearsal', internal_seconds=420,
                                    source_cleanup=lambda: None)
            except BaseException:
                result = None
            cost_path = output / 'control/notebook-cost.json'
            saved = json.loads(cost_path.read_bytes()) if cost_path.exists() else {}
            pending = (output / 'control/finalization-pending.json').exists()
            self.assertTrue(injected)
            if result is not None:
                self.assertIsNotNone(result['error'])
            if copy_evidence is not None:
                from scripts.evaluate_feedback_action_v1 import evaluate_output
                value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=420)
                self.assertTrue(value['run_evidence']['verified'], value['run_evidence'])
                self.assertFalse(value['technically_complete'], value)
                self.assertFalse(value['evaluation']['session_2_permitted'])
                if pending:
                    # Independently isolate the barrier check: even an otherwise passing
                    # receipt must not override the unresolved transaction marker.
                    apparently_passing = dict(saved, lifecycle_finalized=True, error=None,
                                              elapsed_seconds=419.9, finalization_guard_version=1)
                    original(launch.EvidenceStore(output, 'control'), 'notebook-cost.json', apparently_passing)
                    value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=420)
                    self.assertFalse(value['technically_complete'], value)
                    self.assertFalse(value['evaluation']['session_2_permitted'])
            self.assertTrue(pending or saved.get('error') is not None or saved.get('lifecycle_finalized') is not True,
                            'interrupted over-budget certification retained a passing receipt')

    def test_barrier_removal_crossing_deadline_revokes_certification(self):
        clock = [419.9]
        original = Path.unlink

        def unlink(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if path.name == 'finalization-pending.json':
                clock[0] = 420.1
            return result

        with tempfile.TemporaryDirectory() as tmp, patch.object(launch.time, 'monotonic', lambda: clock[0]), patch.object(
                Path, 'unlink', unlink), patch.object(launch, 'run_supervisor', return_value={
                    'status': 'study_complete_pending_independent_evaluation', 'first_cell_cleanup_verified': True}), patch(
                'research.feedback_action_v1.live.authority.rehearsal_gate'):
            output = Path(tmp) / 'output'
            result = launch.run(output, tmp, started=0, mode='rehearsal', internal_seconds=420)
            self.assertIsNotNone(result['error'])
            self.assertFalse(result['lifecycle_finalized'])
            self.assertTrue((output / 'control/finalization-pending.json').exists())

    def test_keyboard_interrupt_after_certification_write(self):
        self.exercise('interrupt')

    def test_system_exit_after_certification_write(self):
        self.exercise('system_exit')

    def test_failed_emergency_write_keeps_pending_barrier(self):
        self.exercise('storage_failure')

    @unittest.skipUnless(os.name == 'posix', 'Python-handled POSIX signal')
    def test_signal_after_certification_write(self):
        self.exercise('signal')


class ConnectedFinalization(unittest.TestCase):
    def test_interrupted_connected_evidence_cannot_permit_session_two(self):
        from tests.test_feedback_action_v1_connected import run_fault
        from scripts.evaluate_feedback_action_v1 import evaluate_output
        receipt, output, _ = run_fault('none')
        valid = evaluate_output(output, mode='rehearsal', rehearsal_seconds=2400)
        self.assertTrue(valid['technically_complete'], valid['lifecycle_errors'])
        self.assertTrue(valid['evaluation']['session_2_permitted'])
        # Keep all real offline-engine calls/transitions and supervisor/monitor receipts;
        # interrupt only the first cell's final certification, as in the review reproduction.
        FinalizationInterruption().exercise('interrupt', copy_evidence=output)


if __name__ == '__main__':
    unittest.main()
