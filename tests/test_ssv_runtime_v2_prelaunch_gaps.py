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
        # The amendment-S2 draw, exactly as evaluate_sessions redraws it, so only the commitment is missing.
        sample = SR.sample_for(eps, SPEC, 40, inputs=P.inputs_digest(eps))
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
            self.assertEqual(value['problems'], ['self-review (amendment S1): ValueError: prior private annotation '
                                                 'commitment required'])


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

    def test_supervisor_death_during_each_child_registration_is_recoverable(self):
        from research.stagnation_supervision_runtime_v2 import launch as L
        # Kill the actual supervisor after the bootstrap's durable per-child record,
        # before the parent's registered state is persisted. Outer cleanup must find
        # every detached child but refuse to certify the incomplete parent journal.
        script = r'''
import os, signal, subprocess, sys, time
from certification.phase4_integrated_v2.evidence import EvidenceStore
from research.stagnation_supervision_runtime_v2.ownership import ChildOwners
output, stop_role = sys.argv[1:]
original = EvidenceStore.save
def save(self, name, value, **kwargs):
    if name == 'ownership.json' and value['children'][stop_role]['state'] == 'registered':
        os.kill(os.getpid(), signal.SIGKILL)
    return original(self, name, value, **kwargs)
EvidenceStore.save = save
owners = ChildOwners(output, time.monotonic(), '0'*64)
owners.save()
for role in ('worker', 'monitor'):
    owners.start(role, [sys.executable, '-c', 'import time; time.sleep(60)'],
                 spawn=subprocess.Popen, cwd=os.getcwd(), env=dict(os.environ), pass_fds=())
'''
        for role in ('worker', 'monitor'):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp)
                def spawn(_argv, **kwargs):
                    return subprocess.Popen([sys.executable, '-c', script, str(output), role], **kwargs)
                with self.assertRaises(RuntimeError):
                    L.run_supervisor(output, output, sys.executable, sys.executable, output,
                        started=time.monotonic(), mode='rehearsal', internal_seconds=60,
                        session='1', spawn=spawn)
                receipt = json.loads((output / 'control/first-cell-supervisor-cleanup.json').read_bytes())
                self.assertFalse(receipt['groups_absent'])
                self.assertFalse(receipt['child_ownership_verified'])
                for name in ('worker', 'monitor'):
                    path = output / ('control/ownership-' + name + '.json')
                    if path.exists():
                        self.assertTrue(L._group_exited(json.loads(path.read_bytes())['pgid']))

    def test_inner_logging_start_interruption_still_cleans_owned_child(self):
        from research.stagnation_supervision_runtime_v2 import supervisor as S
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(S, 'gate', return_value={}), \
                mock.patch.object(S.threading.Thread, 'start', side_effect=KeyboardInterrupt('logging startup')):
            output = Path(tmp) / 'out'
            value = S.run(output, Path(tmp), sys.executable, sys.executable, Path(tmp),
                          started=time.monotonic(), mode='rehearsal', internal_seconds=600, session='1')
            self.assertEqual(value['status'], 'failed')
            self.assertTrue(value['process_groups_exited'])
            from research.stagnation_supervision_runtime_v2.launch import _group_exited
            owned = json.loads((output/'control/ownership.json').read_bytes())
            self.assertTrue(_group_exited(owned['worker_pgid']))


class AnnotationCommitmentRegressions(unittest.TestCase):
    def test_immutable_private_commit_binds_sample_and_annotations(self):
        sample = SR.draw(SR.candidates(label_population(), SPEC, 40))
        record = SR.template(sample)
        for name, rows in record['annotations'].items():
            for row in rows:
                for field in SR.FIELDS[sample['strata'][name]['kind']]:
                    row[field] = 'unclear'
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            sam, ann, receipt = folder/'sample.json', folder/'annotations.json', folder/'commitment.json'
            sam.write_text(json.dumps(sample))
            ann.write_text(json.dumps(record))
            env = {'GIT_AUTHOR_NAME': 'CPU fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
                   'GIT_COMMITTER_NAME': 'CPU fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
            with mock.patch.dict(os.environ, env):
                committed = SR.commit_annotations(folder/'private-review', receipt, sam, ann)
            SR.verify_commitment(receipt, sample, ann, P.sha256_file(ann))
            changed_sample = copy.deepcopy(sample)
            changed_sample['inputs'] = {'changed_evidence': True}
            with self.assertRaisesRegex(ValueError, 'exact evidence'):
                SR.verify_commitment(receipt, changed_sample, ann, P.sha256_file(ann))
            ann.write_text(ann.read_text() + '\n')
            with self.assertRaisesRegex(ValueError, 'exact evidence'):
                SR.verify_commitment(receipt, sample, ann, P.sha256_file(ann))
            fake = json.loads(receipt.read_bytes())
            fake.update(commit='0'*40, annotations_sha256=P.sha256_file(ann))
            receipt.write_text(json.dumps(fake))
            with self.assertRaisesRegex(ValueError, 'unavailable|invalid'):
                SR.verify_commitment(receipt, sample, ann, P.sha256_file(ann))


@unittest.skipUnless(sys.platform == 'linux', 'POSIX installer evidence')
class InstallerReceiptChecks(unittest.TestCase):
    def fixture(self, output):
        import base64, gzip
        from research.stagnation_supervision_runtime_v2 import installation_evidence as IE
        from research.stagnation_supervision_runtime_v2.publisher_install import PACKAGE_CHECK
        from certification.phase4_integrated_v2.evidence import EvidenceStore
        protocol = json.loads((IE.ROOT/'research/stagnation_supervision_runtime_v2/protocol.json').read_bytes())
        receipt = {'passed': True, 'error': None, 'scope': 'runtime_v2_split_install',
                   'runtime_binding': protocol['scope'], 'first_cell_monotonic': 10., 'elapsed_seconds': 5.,
                   'installation_seconds': 450, 'override': False, 'evidence_class': 'first_cell',
                   'runtime_identity': {k: protocol[k] for k in ('dataset', 'bundle', 'runtime')},
                   'competition_manifest_sha256': protocol['competition']['manifest_sha256'], 'game_wheels': 31,
                   'model_bundle': {'integrity_passed': True, 'wheel_bytes_verified': 174,
                       'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
                       'installation_requirements_sha256': protocol['bundle']['requirements_lock_sha256'],
                       'dataset_ref': protocol['dataset']['ref'], 'requested_version': protocol['dataset']['version']},
                   'torch_contract': json.loads((IE.ROOT/'reports/phase4_torch_wheel_inspection.json').read_bytes()),
                   'interpreters': {r: '/tmp/synthetic/'+r+'/venv/bin/python' for r in ('game', 'model')},
                   'installer_evidence_sha256': {}}
        wheels = json.loads((IE.ROOT/'reports/phase4_v2_offline_package.json').read_bytes())['files']
        plan = {'install': [{'download_info': {'url': 'file:///synthetic/'+Path(n).name,
                           'archive_info': {'hashes': {'sha256': row['sha256']}}}}
                           for n, row in wheels.items() if n.startswith('wheels/')]}
        for role, phases in (('model', IE.MODEL_PHASES), ('game', IE.GAME_PHASES)):
            imports = protocol['runtime']['model']['imports'] if role == 'model' else ['arc_agi', 'arcengine', 'numpy']
            receipt[role+'_install'] = {'versions': protocol['runtime'][role]['packages'],
                'imports': {n: '/tmp/synthetic/'+role+'/venv/lib/python3.12/site-packages/'+n+'/__init__.py' for n in imports}}
            if role == 'model':
                receipt[role+'_install']['torch_cuda_build'] = protocol['runtime']['model']['torch_cuda_build']
            commands = [{'phase': p, 'pgid': 100+i, 'ownership': 'registered', 'groups_absent': True, 'error': None,
                         'interrupted': [], 'returncode': 0, 'argv': ['python', p]} for i, p in enumerate(phases)]
            commands[1 if role == 'model' else 5]['argv'] = ['python', '--no-index', '--no-cache-dir',
                '--only-binary=:all:', '--require-hashes', '-r', '/synthetic/trusted_requirements.lock']
            commands[3 if role == 'model' else 9]['argv'] = [receipt['interpreters'][role], '-I', '-c', PACKAGE_CHECK,
                json.dumps({**protocol['runtime'][role], 'imports': imports})]
            receipt[role+'_process_cleanup'] = {'groups_absent': True, 'error': None, 'interrupted': [],
                                                'groups': len(phases), 'commands': commands}
            stages = [{'stage': p, 'passed': True, 'error': None, 'started_seconds': 0., 'ended_seconds': 1.} for p in phases]
            probe_stdout = json.dumps(receipt[role+'_install']).encode() + b'\n'
            logs = {'install.log': probe_stdout} if role == 'model' else {
                'stages.json': json.dumps(stages).encode(), 'stages.log': probe_stdout,
                'resolution.json': json.dumps(plan).encode(), 'install_game.json': json.dumps(plan).encode()}
            packed = gzip.compress(json.dumps({n: base64.b64encode(raw).decode() for n, raw in logs.items()}).encode())
            receipt['installer_evidence_sha256'][role] = hashlib.sha256(packed).hexdigest()
            EvidenceStore(output, 'logs').save('install-'+role+'.json', {
                'encoding': 'gzip-base64-json', 'data': base64.b64encode(packed).decode()})
        EvidenceStore(output, 'control').save('installation.json', receipt)
        return receipt

    def test_successful_installation_and_each_inconsistency(self):
        from research.stagnation_supervision_runtime_v2 import installation_evidence as IE
        from certification.phase4_integrated_v2.evidence import EvidenceStore
        first = {'installation': 'target', 'first_cell_monotonic': 10.}
        outer = {'worker_released_seconds': 20.}
        changes = [lambda v: v.update(passed=False), lambda v: v.update(elapsed_seconds=451),
                   lambda v: v['model_bundle'].update(wheel_bytes_verified=173),
                   lambda v: v['runtime_identity']['runtime']['model']['packages'].update(vllm='changed'),
                   lambda v: v['game_process_cleanup']['commands'][0].update(groups_absent=False),
                   lambda v: v['model_process_cleanup']['commands'][0].update(ownership='uncertain'),
                   lambda v: v['installer_evidence_sha256'].update(model='0'*64),
                   lambda v: v['game_install']['versions'].update(numpy='changed')]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            original = self.fixture(output)
            self.assertTrue(IE.validate_installation(output, first, outer, mode='live')['verified'])
            for i, change in enumerate(changes):
                with self.subTest(mutation=i):
                    value = copy.deepcopy(original)
                    change(value)
                    EvidenceStore(output, 'control').save('installation.json', value)
                    with self.assertRaisesRegex(ValueError, 'installation evidence'):
                        IE.validate_installation(output, first, outer, mode='live')

    def test_changed_installer_stdout_with_updated_hash_is_refused(self):
        import base64, gzip
        from research.stagnation_supervision_runtime_v2 import installation_evidence as IE
        from certification.phase4_integrated_v2.evidence import EvidenceStore
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            receipt = self.fixture(output)
            packed = gzip.compress(json.dumps({'install.log': base64.b64encode(b'{"versions":{}}\n').decode()}).encode())
            receipt['installer_evidence_sha256']['model'] = hashlib.sha256(packed).hexdigest()
            EvidenceStore(output, 'logs').save('install-model.json', {
                'encoding': 'gzip-base64-json', 'data': base64.b64encode(packed).decode()})
            EvidenceStore(output, 'control').save('installation.json', receipt)
            with self.assertRaisesRegex(ValueError, 'retained stdout'):
                IE.validate_installation(output, {'installation': 'target', 'first_cell_monotonic': 10.},
                                         {'worker_released_seconds': 20.}, mode='live')


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
