import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from research.object_discovery_boundaries_v1 import transport_check as C
from tests.archive_transport_fixture import build


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'inputs'
        self.inputs.mkdir()
        _, pin, original, _ = build(self.inputs / 'dataset')
        self.protocol = {'schema': 'semantic_transport_cpu_check_v1', 'scope': C.SCOPE,
            'dataset_ref': 'owner/dataset', 'dataset_version': 1,
            'transport_manifest_sha256': pin, 'original_manifest_sha256': original}
        self.authority = {'approved': True, 'owner_answer': 'Synthetic test only',
            'review_lock_sha256': '1' * 64, 'runtime_lock_sha256': '2' * 64,
            'protocol_sha256': C.digest(C.canonical(self.protocol)), 'scope': C.SCOPE,
            'claim_consumed': True, 'attempt_id': 'synthetic-not-a-provider-claim'}
        self.clock = [0.0]
        self.output = self.root / 'output'

    def run_check(self, **kwargs):
        return C.run(self.protocol, self.authority, input_root=self.inputs, output=self.output,
                     now=lambda: self.clock[0], use_alarm=False, **kwargs)

    def test_missing_authority_refuses_before_filesystem_access(self):
        with self.assertRaises(PermissionError):
            C.run(self.protocol, None, input_root=self.root / 'absent', output=self.output)
        self.assertFalse(self.output.exists())

    def test_only_cpu_scope_and_matching_protocol_are_accepted(self):
        for field, value in (('scope', dict(C.SCOPE, gpu=True)), ('protocol_sha256', '0' * 64),
                             ('claim_consumed', False)):
            authority = dict(self.authority, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                C.authority_check(self.protocol, authority)

    def test_restores_and_removes_temporary_originals_before_provisional_receipt(self):
        result = self.run_check()
        self.assertEqual(result['status'], 'provisional_complete')
        self.assertTrue(result['temporary_workspace_removed'])
        self.assertEqual(result['model_loads'], 0)
        self.assertFalse(result['gpu_runtime_validated'])
        witness = json.loads((self.output / 'completion-witness.json').read_bytes())
        self.assertEqual(witness['result_sha256'], C.digest((self.output / 'result.json').read_bytes()))
        self.assertFalse((self.output / 'transport-restore-tmp').exists())

    def test_interrupted_restoration_removes_temporary_workspace_and_fails(self):
        def interrupted(*args, **kwargs): raise KeyboardInterrupt()
        with patch.object(C, 'restore', side_effect=interrupted), self.assertRaises(RuntimeError):
            self.run_check()
        self.assertEqual(json.loads((self.output / 'result.json').read_bytes())['status'], 'failed')
        self.assertFalse((self.output / 'completion-witness.json').exists())
        self.assertFalse((self.output / 'transport-restore-tmp').exists())

    def test_cleanup_overrun_fails_without_completion_witness(self):
        def slow_remove(path):
            shutil.rmtree(path)
            self.clock[0] = 1101.0
        with self.assertRaises(TimeoutError): self.run_check(remove=slow_remove)
        # Once the final deadline expires, even failure-receipt writing stops.
        self.assertFalse((self.output / 'result.json').exists())
        self.assertFalse((self.output / 'completion-witness.json').exists())

    def test_receipt_write_overrun_cannot_produce_completion_witness(self):
        def late_write(path, raw):
            C.write(path, raw)
            self.clock[0] = 1100.1
        with self.assertRaises(TimeoutError): self.run_check(writer=late_write)
        self.assertFalse((self.output / 'completion-witness.json').exists())

    def test_witness_write_interruption_propagates_before_cell_marker(self):
        def interrupted_write(path, raw):
            C.write(path, raw)
            if Path(path).name == 'completion-witness.json': raise KeyboardInterrupt()
        with patch('builtins.print') as printed, self.assertRaises(KeyboardInterrupt):
            self.run_check(writer=interrupted_write)
        printed.assert_not_called()

    def test_witness_write_overrun_cannot_return_success(self):
        def late_write(path, raw):
            C.write(path, raw)
            if Path(path).name == 'completion-witness.json': self.clock[0] = 1100.1
        with patch('builtins.print') as printed, self.assertRaises(TimeoutError):
            self.run_check(writer=late_write)
        printed.assert_not_called()
        self.assertEqual(json.loads((self.output / 'result.json').read_bytes())['status'],
                         'provisional_complete')

    def test_deadline_crossed_while_printing_final_marker_still_fails(self):
        def late_marker(*args, **kwargs): self.clock[0] = 1100.1
        with patch('builtins.print', side_effect=late_marker), self.assertRaises(TimeoutError):
            self.run_check()
        # A valid witness and marker alone never establish a pass. The saved
        # provider run must COMPLETE rather than ERROR after this final check.
        self.assertTrue((self.output / 'completion-witness.json').exists())


@unittest.skipUnless(sys.platform == 'linux', 'real Linux ITIMER_REAL deadline checks')
class RealAlarms(unittest.TestCase):
    def probe(self, stage):
        # An isolated child keeps a broken timer from hanging the test process.
        code = r'''
import json, pathlib, signal, tempfile, time
from unittest.mock import patch
from research.object_discovery_boundaries_v1 import transport_check as C
from tests.archive_transport_fixture import build
with tempfile.TemporaryDirectory() as tmp:
    root = pathlib.Path(tmp); inputs = root / 'inputs'; inputs.mkdir()
    _, pin, original, _ = build(inputs / 'dataset')
    scope = dict(C.SCOPE, worker_seconds=.18,
                 cleanup_reserve_seconds=0 if STAGE == 'hard_work' else .10)
    protocol = dict(schema='semantic_transport_cpu_check_v1', scope=scope,
        dataset_ref='owner/dataset', dataset_version=1,
        transport_manifest_sha256=pin, original_manifest_sha256=original)
    authority = dict(approved=True, owner_answer='Synthetic local alarm regression',
        review_lock_sha256='1'*64, runtime_lock_sha256='2'*64,
        protocol_sha256=C.digest(C.canonical(protocol)), scope=scope,
        claim_consumed=True, attempt_id='synthetic-only')
    observations = {}
    def work(*args, **kwargs):
        if STAGE in ('work_timeout', 'hard_work'): time.sleep(.5)
        raise ValueError('synthetic work failure')
    def remove(path):
        observations['cleanup_timer'] = signal.getitimer(signal.ITIMER_REAL)[0]
        if STAGE != 'writer': time.sleep(.5)
        else: __import__('shutil').rmtree(path)
    def writer(path, raw):
        observations['writer_entered'] = True
        time.sleep(.5)
    started = time.monotonic()
    with patch.object(C, 'SCOPE', scope), patch.object(C, 'restore', side_effect=work):
        try: C.run(protocol, authority, input_root=inputs, output=root/'output',
                   remove=remove, writer=writer)
        except BaseException as error: observations['exception'] = type(error).__name__
    observations['elapsed'] = time.monotonic() - started
    observations['timer_after'] = signal.getitimer(signal.ITIMER_REAL)[0]
    observations['witness_exists'] = (root/'output/completion-witness.json').exists()
    print(json.dumps(observations))
'''
        result = subprocess.run([sys.executable, '-c', 'STAGE = ' + repr(stage) + '\n' + code],
                                capture_output=True, text=True, timeout=5, check=True)
        return json.loads(result.stdout)

    def test_work_alarm_reserves_cleanup_and_final_alarm_interrupts_stalled_cleanup(self):
        result = self.probe('work_timeout')
        self.assertGreater(result['cleanup_timer'], 0)
        self.assertEqual(result['exception'], 'LifecycleDeadline')
        self.assertLess(result['elapsed'], .40)
        self.assertNotIn('writer_entered', result)
        self.assertFalse(result['witness_exists'])
        self.assertEqual(result['timer_after'], 0)

    def test_early_failure_still_has_a_non_swallowable_cleanup_alarm(self):
        result = self.probe('early_failure')
        self.assertGreater(result['cleanup_timer'], 0)
        self.assertEqual(result['exception'], 'LifecycleDeadline')
        self.assertLess(result['elapsed'], .40)
        self.assertNotIn('writer_entered', result)

    def test_final_alarm_interrupts_evidence_write_after_failed_work(self):
        result = self.probe('writer')
        self.assertTrue(result['writer_entered'])
        self.assertEqual(result['exception'], 'LifecycleDeadline')
        self.assertLess(result['elapsed'], .40)
        self.assertFalse(result['witness_exists'])

    def test_final_deadline_during_work_does_not_begin_cleanup(self):
        result = self.probe('hard_work')
        self.assertEqual(result['exception'], 'LifecycleDeadline')
        self.assertNotIn('cleanup_timer', result)
        self.assertNotIn('writer_entered', result)
        self.assertLess(result['elapsed'], .40)


if __name__ == '__main__': unittest.main()
