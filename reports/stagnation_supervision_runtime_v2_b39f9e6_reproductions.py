"""Independent prelaunch review regressions: CPU only, never a provider or live model call."""
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from research.stagnation_supervision_runtime_v2 import pooled as P, report as R, selfreview as SR
from tests import test_ssv_runtime_v2_r2_gaps as fixtures
label_population, SPEC = fixtures.label_population, fixtures.SPEC


class ReportingRegressions(unittest.TestCase):
    def target(self, complete=True):
        return {'technically_complete': complete, 'target_accepted': complete, 'lifecycle_verified': complete,
                'problems': [] if complete else ['lifecycle failed'],
                'trajectory': {'technically_complete': True, 'realised_cost': {'calls': 1}}}

    def test_failed_lifecycle_withholds_outcomes(self):
        with mock.patch('research.stagnation_supervision_runtime_v2.target_evaluate.evaluate_target',
                        return_value=self.target(False)):
            value = R.study_report('/nonexistent', {}, mode='rehearsal')
        self.assertFalse(value['technically_complete'])
        self.assertIsNone(value['endpoints'])
        self.assertIsNotNone(value['endpoints_withheld_reason'])

    def test_failed_checkout_withholds_outcomes(self):
        with mock.patch('research.stagnation_supervision_runtime_v2.target_evaluate.evaluate_target',
                        return_value=self.target()), mock.patch.object(R, 'checkout_review_lock',
                        return_value=({'verified': False}, ['source drift'])):
            value = R.study_report('/nonexistent', {}, mode='live')
        self.assertFalse(value['technically_complete'])
        self.assertIsNone(value['endpoints'])

    def test_live_checkout_verification_cannot_be_disabled(self):
        with mock.patch('research.stagnation_supervision_runtime_v2.target_evaluate.evaluate_target',
                        return_value=self.target()):
            with self.assertRaises((ValueError, PermissionError)):
                R.study_report('/nonexistent', {}, mode='live', verify_checkout=False)

    def test_live_trigger_override_refused_before_reading_runs(self):
        changed = copy.deepcopy(SPEC)
        changed['review_override'] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'record.json'
            record = {'technically_complete': False, 'target_accepted': False}
            path.write_text(json.dumps(record))
            with mock.patch.object(R, 'study_report', return_value=record):
                with self.assertRaisesRegex((ValueError, PermissionError), 'frozen|override'):
                    P.evaluate_sessions({'1': tmp, '2': tmp}, {'1': path, '2': path},
                        annotations='/nonexistent', annotations_sha256='0'*64, mode='live', trigger_spec=changed)

    def test_reflection_changes_invalidate_annotation_sample(self):
        a = label_population()
        b = copy.deepcopy(a)
        b[0]['first_tests'][0] = {'action_id': 2, 'action_data': {}}
        b[0]['reflections'] = [{'response': 'changed reflection'}]
        # Identical frames and actions; the sample must still bind the changed reflection.
        self.assertNotEqual(P.inputs_digest(a), P.inputs_digest(b))

    def test_supplied_hash_does_not_establish_prior_annotation_commitment(self):
        eps = label_population()
        sample = SR.draw(SR.candidates(eps, SPEC, 40), inputs=P.inputs_digest(eps))
        annotations = SR.template(sample)
        for name, rows in annotations['annotations'].items():
            for row in rows:
                for field in SR.FIELDS[sample['strata'][name]['kind']]:
                    row[field] = 'unclear'
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            paths = {}
            record = {'technically_complete': True, 'target_accepted': True}
            for s in ('1', '2'):
                paths[s] = folder / (s+'.json')
                paths[s].write_text(json.dumps(record))
            ann = folder / 'annotations.json'
            ann.write_text(json.dumps(annotations))
            execution = folder / 'execution.json'
            execution.write_text(json.dumps({'session1_evaluation': {'sha256': P.sha256_file(paths['1'])}}))
            with mock.patch.object(R, 'study_report', return_value=record), \
                 mock.patch('research.stagnation_supervision_v1.closed_loop.bridge.session_spec',
                            return_value={'limits': {'actions_per_episode': 40}}), \
                 mock.patch.object(P, 'session_episodes', side_effect=[eps, []]), \
                 mock.patch.object(P, 'compute', return_value={'comparison': True}):
                value = P.evaluate_sessions({'1': folder, '2': folder}, paths, annotations=ann,
                    annotations_sha256=P.sha256_file(ann), session2_execution=execution)
            self.assertIsNone(value['pooled'])
            self.assertTrue(any('commit' in p for p in value['problems']))


@unittest.skipUnless(sys.platform == 'linux', 'real process ownership and connected evidence')
class InnerOwnershipRegressions(unittest.TestCase):
    def exercise(self, role):
        from research.stagnation_supervision_runtime_v2 import supervisor as S
        children = []
        def spawn(argv, **kwargs):
            # Before the fix each child detaches immediately. After the fix the bootstrap
            # remains in its parent's group until its per-child receipt is durable.
            if '--owned-exec' in argv:
                split = argv.index('--')
                argv = argv[:split+1] + [sys.executable, '-c', 'import time; time.sleep(60)']
            else:
                argv = [sys.executable, '-c', 'import time; time.sleep(60)']
            child = subprocess.Popen(argv, **kwargs)
            children.append(child)
            if len(children) == (1 if role == 'worker' else 2):
                os.kill(os.getpid(), signal.SIGINT)
            return child
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(S, 'gate', return_value={}):
            output = Path(tmp) / 'out'
            try:
                try:
                    S.run(output, Path(tmp), sys.executable, sys.executable, Path(tmp),
                          started=time.monotonic(), mode='rehearsal', internal_seconds=600,
                          session='1', spawn=spawn)
                except KeyboardInterrupt:
                    pass
                self.assertTrue(children)
                self.assertTrue(all(p.poll() is not None for p in children), 'real child escaped startup cleanup')
            finally:
                for p in children:
                    if p.poll() is None:
                        try:
                            os.killpg(p.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            p.kill()
                    p.wait(timeout=5)
                    if p.stdout:
                        p.stdout.close()

    def test_worker_interruption_before_assignment(self):
        self.exercise('worker')

    def test_monitor_interruption_before_assignment(self):
        self.exercise('monitor')


@unittest.skipUnless(sys.platform == 'linux', 'connected retained lifecycle fixture')
class InstallationRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.PooledRehearsal.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.PooledRehearsal.tearDownClass()

    def test_missing_or_failed_installation_receipt_is_not_complete(self):
        from research.stagnation_supervision_runtime_v2.target_evaluate import evaluate_target
        from certification.phase4_integrated_v2.evidence import EvidenceStore
        import shutil
        for install in (None, {'passed': False, 'error': 'installation failed'}):
            with self.subTest(installation=install), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'out'
                shutil.copytree(fixtures.PooledRehearsal.outputs['1'], output)
                store = EvidenceStore(output, 'control')
                first = json.loads((output/'control/notebook-cost.json').read_bytes())
                first.update(installation='staged_rehearsal', dependency_trees_removed=True)
                store.save('notebook-cost.json', first)
                if install is not None:
                    store.save('installation.json', install)
                value = evaluate_target(output, fixtures.PooledRehearsal.specs['1'], mode='rehearsal',
                                        session='1', internal_seconds=1500)
                self.assertFalse(value['technically_complete'])
                self.assertTrue(any('install' in p for p in value['problems']))


if __name__ == '__main__':
    unittest.main()
