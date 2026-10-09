"""progress_subgoal_v1 runtime2: derivation, runtime bindings, frozen experiment checks and the live gate (CPU only).

Nothing here contacts a provider, uses a GPU or creates an approval, reservation or claim in the checkout; the gated
fixture below is fabricated in a temporary directory only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from certification.direct_publisher_smoke_v1.accounting import Clock, Ledger, RequestRefused
from research.progress_subgoal_v1_runtime2 import binding as B, notebook as N, questionnaire as QN
from research.progress_subgoal_v1_runtime2 import runtime_controls as C
from scripts import build_progress_subgoal_v1_runtime2 as BUILD

ROOT = Path(__file__).resolve().parents[1]
BASIS_ENV = 'PSV1R2_BASIS'  # a directory with the 5a21dd3 basis files (git archive); optional


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def copy_sources(root):
    for name in N.source_names(ROOT):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())


def gated_fixture(root):
    """Fabricated authority in a disposable directory; never a real approval or reservation (reference pattern)."""
    def put(name, value):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + '\n').encode())

    def digest(name):
        return B.sha256(root / name)
    copy_sources(root)
    for name in N.REVIEW_DOCUMENTS:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes((ROOT / name).read_bytes())
    protocol = B.load_protocol(ROOT)
    protocol['kernel_id'] = 'fixture/psv1r2'
    protocol['model'].update(kaggle_source='fixture/psv1r2-model/1', mounted_path='/kaggle/input/psv1r2-model')
    put(B.PROTOCOL, protocol)
    N.build_review(root / 'notebooks/progress-subgoal-v1-runtime2-review-r5', root=root)
    lock = B.review_lock(root)
    dataset = {k: protocol['dataset'][k] for k in ('ref', 'version')}
    provider, facts = 'private/fixture-provider.json', 'private/fixture-assessment.json'
    put(provider, {'authenticated_account': 'fixture', 'dataset_attachments': [dict(dataset, attachment_confirmed=True)]})
    put(B.ACCOUNT, {'status': 'verified', 'scope': B.SCOPE, 'dataset': dataset, 'consuming_account': 'fixture',
                    'verified_at': 'fixture-only', 'provider_evidence': provider, 'provider_evidence_sha256': digest(provider)})
    put(facts, {'consuming_account': 'fixture', 'dataset': dataset, **{k: 'fabricated fixture only' for k in (
        'licence_holder', 'recipients_and_roles', 'access_controls', 'publication_intent', 'applicable_agreements',
        'output_and_payload_handling', 'licence_evidence')}})
    put(B.PERMISSION, {'status': 'approved', 'approval_kind': 'direct_consumption_permission', 'scope': B.SCOPE,
        'dataset': protocol['dataset'], 'review_lock_sha256': digest(lock), 'protocol_sha256': digest(B.PROTOCOL),
        'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
        'requirements_lock_sha256': protocol['bundle']['requirements_lock_sha256'],
        'permission_outcome': 'permitted_for_reviewed_use', 'outstanding_conditions': [],
        'reviewer_response': 'fabricated fixture only', 'reviewed_at': 'fixture-only',
        'use_assessment': facts, 'use_assessment_sha256': digest(facts)})
    put(B.BYTES, {'integrity_passed': True, 'wheel_bytes_verified': 174, 'dataset_ref': dataset['ref'],
                  'requested_version': 1, 'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
                  'installation_requirements_sha256': protocol['bundle']['requirements_lock_sha256']})
    common = {'status': 'approved', 'scope': B.SCOPE, 'review_lock_sha256': digest(lock), 'approved_at': 'fixture-only',
              'user_response': 'fabricated fixture only', 'evidence_bindings': {n: digest(n) for n in B.evidence_names(root)}}
    put(B.SOURCE, dict(common, approval_kind='source'))
    put(B.COMPUTE, dict(common, approval_kind='compute', source_approval_sha256=digest(B.SOURCE),
        protocol_sha256=digest(B.PROTOCOL), dataset=protocol['dataset'],
        **{k: protocol['limits'][k] for k in B.COMPUTE_LIMITS}))
    execution = {'scope': B.SCOPE, 'attempt_id': 'psv1r2-fixture0001', 'review_lock': lock, 'review_sha256': digest(lock),
                 'source_approval_sha256': digest(B.SOURCE), 'compute_approval_sha256': digest(B.COMPUTE)}
    put(B.EXECUTION, execution)
    put(B.RESERVATION, {'status': 'reserved', 'attempt_id': execution['attempt_id'],
                        'execution_sha256': hashlib.sha256(json.dumps(execution, sort_keys=True, indent=2).encode()
                                                           + b'\n').hexdigest(), 'events': ['reserve']})
    put(B.CLAIM, {'status': 'claimed', 'attempt_id': execution['attempt_id'], 'execution_sha256': digest(B.EXECUTION),
                  'reservation_sha256': digest(B.RESERVATION), 'claimed_at': 'fixture-only'})
    return put


class Derivation(unittest.TestCase):
    def test_copied_controller_derived_outputs_and_records_match(self):
        self.assertEqual(BUILD.check(ROOT), [])

    def test_controller_is_byte_identical_to_the_verified_runtime(self):
        for name, digest in BUILD.SMOKE_SHA256.items():
            self.assertEqual(sha(ROOT / name), digest, name)
        derivation = json.loads((ROOT / BUILD.NEW / 'derivation.json').read_bytes())
        self.assertEqual(derivation['controller_copied_unchanged'], BUILD.SMOKE_SHA256)
        self.assertEqual(derivation['basis_commit'], '5a21dd3')
        self.assertFalse(derivation['scientific_configuration_changed'])

    def test_experiment_sources_are_unchanged_from_review_r4(self):
        derivation = json.loads((ROOT / BUILD.NEW / 'derivation.json').read_bytes())
        self.assertTrue(derivation['experiment_sources_equal_r4_hashes'])
        r4 = json.loads((ROOT / BUILD.SUPERSEDED_LOCK).read_bytes())['bindings']
        for name in C.EXPERIMENT_SOURCES:
            if name in r4:
                self.assertEqual(sha(ROOT / name), r4[name], name)
        self.assertEqual(sorted(set(C.EXPERIMENT_SOURCES) - set(r4)), ['research/progress_subgoal_v1/decision_rules.json'])
        self.assertEqual(sha(ROOT / 'research/progress_subgoal_v1/decision_rules.json'), C.DECISION_RULES_SHA256)

    def test_experiment_source_closure_is_recomputed_exactly(self):
        self.assertEqual(tuple(BUILD.experiment_sources(ROOT)), C.EXPERIMENT_SOURCES)

    def test_superseded_review_r4_is_untouched(self):
        self.assertEqual(sha(ROOT / BUILD.SUPERSEDED_LOCK), BUILD.SUPERSEDED_LOCK_SHA256)
        lock = json.loads((ROOT / BUILD.SUPERSEDED_LOCK).read_bytes())
        for name, digest in lock['artifacts'].items():
            self.assertEqual(sha(ROOT / 'notebooks/progress-subgoal-v1-review-r4' / name), digest, name)

    @unittest.skipUnless(os.environ.get(BASIS_ENV), 'set PSV1R2_BASIS to the 5a21dd3 basis directory')
    def test_derivation_reproduces_byte_for_byte_from_the_basis(self):
        basis = Path(os.environ[BASIS_ENV])
        for name, data in BUILD.build(ROOT, basis).items():
            self.assertEqual((ROOT / name).read_bytes(), data, name)
        for name, data in BUILD.records(ROOT, basis).items():
            self.assertEqual((ROOT / name).read_bytes(), data, name)


class RuntimeBindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = B.load_protocol(ROOT)

    def test_verified_wheel_dataset_and_trusted_installation_inputs(self):
        p = self.protocol
        self.assertEqual(p['dataset'], {'ref': 'driessmit1/arc3-vllm-h100-wheelhouse-v3', 'version': 1,
            'publisher_metadata_sha256': {
                'README.md': 'd2e8da6d36c243198882e6cb68d60d7121d8aa9642e55d7fcc384bc4d087b631',
                'SHA256SUMS': '805388efb6bf7f0a248f2bb70798188737077545159fe0e475aee4d44843c901',
                'requirements.lock': 'bb3e30ac5e327456e3915b807da960203c20bc1aa352204e39f66d5618a6bcb0'}})
        self.assertEqual(p['bundle'], {'approved_manifest_sha256': '3691cb8854df4d8ff10e42ca9957fddb9a8ae0362064e7b31b3205891af0d546',
                                       'requirements_lock_sha256': 'ba80d35062245421daf1cae65474281952cc0c44fb46e11cf7f68d0ece496406',
                                       'wheel_count': 174})
        self.assertEqual(sha(ROOT / BUILD.NEW / 'trusted_requirements.lock'), p['bundle']['requirements_lock_sha256'])
        manifest = json.loads((ROOT / BUILD.NEW / 'trusted_manifest.json').read_bytes())
        self.assertEqual(manifest['artifact_count'], 174)
        self.assertEqual(manifest['manifest_sha256'], p['bundle']['approved_manifest_sha256'])

    def test_dataset_backed_pinned_model_with_private_placeholders(self):
        model = self.protocol['model']
        self.assertEqual((model['model_id'], model['revision'], model['source_kind'], model['tree_sha256']),
                         ('Qwen/Qwen3-VL-30B-A3B-Instruct-FP8', 'd9748a51ae66354c4dad665aab2c71f26cf2c8cd', 'dataset',
                          'b480ad92cda91474084c795d2ff64b07a6c477909b22d2784d24abf8fb4ef7df'))
        self.assertEqual(model['kaggle_source'], 'REPLACE_WITH_MODEL_OWNER/REPLACE_WITH_MODEL_DATASET/1')
        self.assertEqual(model['mounted_path'], 'REPLACE_WITH_VERIFIED_MODEL_MOUNT')
        self.assertEqual(B.unresolved(self.protocol), ['kernel_id', 'model.kaggle_source', 'model.mounted_path'])

    def test_image_runtime_competition_and_server(self):
        p = self.protocol
        self.assertEqual(p['kaggle_image'], {'docker_image': 'gcr.io/kaggle-private-byod/python@sha256:'
                                             '37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461',
                                             'docker_image_pinning_type': 'original'})
        self.assertEqual((p['runtime']['python'], p['runtime']['packages'], p['runtime']['torch_cuda_build'],
                          p['runtime']['gpu_count'], p['runtime']['gpu_name_contains']),
                         ('3.12', {'numpy': '2.2.6', 'torch': '2.10.0', 'transformers': '4.57.6', 'vllm': '0.19.0'},
                          '12.8', 1, 'RTX PRO 6000'))
        self.assertEqual(p['competition']['ref'], 'arc-prize-2026-arc-agi-3')
        argv = p['server']['argv']
        self.assertEqual(argv.count('--no-enable-prefix-caching'), 1)
        self.assertNotIn('--enable-prefix-caching', argv)
        self.assertEqual(p['server']['served_model_name'], 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8')

    def test_limits_are_the_frozen_package_limits(self):
        rules = json.loads((ROOT / C.DECISION_RULES).read_bytes())['package_limits']
        limits = self.protocol['limits']
        self.assertEqual((limits['authorized_seconds'], limits['internal_seconds'], limits['admission_cutoff_seconds'],
                          limits['cleanup_reserve_seconds'], limits['maximum_attempts'], limits['automatic_retries']),
                         (rules['maximum_reservation_seconds_per_session'], rules['internal_seconds'],
                          rules['admission_cutoff_seconds'], rules['cleanup_reserve_seconds'], rules['maximum_attempts'],
                          rules['automatic_retries']))
        self.assertEqual((limits['environment_actions'], limits['scorecards']), (0, 0))

    def test_request_plan_and_cap(self):
        requests = self.protocol['requests']
        self.assertEqual(self.protocol['limits']['maximum_model_requests'], 6613)
        self.assertEqual(sum(r.get('max_issues', 1) for r in requests), 6613)
        questionnaire = [r for r in requests if r['kind'] == QN.KIND]
        self.assertEqual([r['id'] for r in questionnaire], [QN.request_id(n) for n in range(5852)])
        self.assertTrue(all(r['timeout_seconds'] == 60 and r['path'] == '/v1/chat/completions' for r in questionnaire))
        idle = [r for r in requests if r['kind'] == QN.IDLE_KIND]
        self.assertEqual(idle, [{'id': 'QIDLE', 'kind': QN.IDLE_KIND, 'method': 'GET', 'path': '/metrics',
                                 'timeout_seconds': 1, 'max_issues': 750}])
        others = [r['id'] for r in requests if r['kind'] not in (QN.KIND, QN.IDLE_KIND)]
        self.assertEqual(others, list(C.RUNTIME_PROBES))
        clock = Clock(self.protocol['limits'], 0, now=lambda: 1)
        ledger = Ledger(requests, 6613, clock)
        for item in requests:
            for _ in range(item.get('max_issues', 1)):
                ledger.admit(item['id'])
        self.assertEqual(len(ledger.entries), 6613)
        for name in ('Q00000', 'QIDLE', 'NOT_PLANNED'):
            with self.assertRaises(RequestRefused):
                ledger.admit(name)

    def test_drift_in_any_frozen_setting_is_refused(self):
        changes = [lambda p: p['experiment'].update(max_tokens=64),
                   lambda p: p['experiment'].update(scheduled_calls=5851),
                   lambda p: p['experiment'].update(probe_set_sha256='0' * 64),
                   lambda p: p['experiment']['call_timing'].update(timeout_seconds=30),
                   lambda p: p['experiment'].update(arms=['raw_evidence', 'raw_plus_computed_record']),
                   lambda p: p['limits'].update(admission_cutoff_seconds=3120),
                   lambda p: p['limits'].update(internal_seconds=3420),
                   lambda p: p['limits'].update(maximum_model_requests=6614),
                   lambda p: p['server']['argv'].__setitem__(p['server']['argv'].index('--no-enable-prefix-caching'),
                                                             '--enable-prefix-caching'),
                   lambda p: p['requests'].pop(7),
                   lambda p: p['requests'][7].update(timeout_seconds=120),
                   lambda p: p['server'].update(served_model_name='other')]
        for change in changes:
            protocol = copy.deepcopy(self.protocol)
            change(protocol)
            with self.assertRaises((ValueError, KeyError)):
                C.validate_protocol(ROOT, protocol)

    def test_token_audit_must_bind_the_actual_requests(self):
        audit = QN.token_audit(ROOT)
        self.assertTrue(audit['passed'])
        self.assertEqual(len(audit['prompt_tokens']), 5852)
        self.assertLessEqual(max(audit['prompt_tokens']) + 32, 65536)
        tampered = dict(audit, prompt_tokens=audit['prompt_tokens'][:-1])
        with patch.object(QN, 'token_audit', return_value=tampered):
            with self.assertRaisesRegex(ValueError, 'token audit'):
                C.validate_protocol(ROOT, self.protocol)
        with patch.object(QN, 'token_audit', return_value=dict(audit, request_digest='0' * 64)):
            with self.assertRaisesRegex(ValueError, 'token audit'):
                C.validate_protocol(ROOT, self.protocol)

    def test_cache_config_missing_enabled_or_conflicting_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'server.log'
            for text in ['', 'enable_prefix_caching=True', "enable_prefix_caching=False\nenable_prefix_caching': True"]:
                p.write_text(text)
                with self.assertRaises(ValueError):
                    C.verify_cache_disabled(p)
            p.write_text("enable_prefix_caching': False\nenable_prefix_caching=False")
            self.assertTrue(C.verify_cache_disabled(p)['disabled'])


class LiveGate(unittest.TestCase):
    def test_this_checkout_refuses_before_any_effect(self):
        with self.assertRaises(B.LiveRefused) as caught:
            B.require_live(ROOT)
        reasons = ' '.join(caught.exception.reasons)
        self.assertIn('unresolved placeholders: kernel_id, model.kaggle_source, model.mounted_path', reasons)
        self.assertIn('authorization:', reasons)
        with tempfile.TemporaryDirectory() as working:
            with self.assertRaises(B.LiveRefused):
                B.consume(ROOT, working)
            self.assertEqual(list(Path(working).iterdir()), [])
        with self.assertRaises(B.LiveRefused):
            N.launch_artifacts(ROOT)

    def test_no_authority_record_exists_in_the_checkout(self):
        for name in (B.SOURCE, B.COMPUTE, B.EXECUTION, B.RESERVATION, B.CLAIM, B.RECEIPT, B.ACCOUNT, B.PERMISSION,
                     B.BYTES, 'reports/progress_subgoal_v1_source_approval.json',
                     'reports/progress_subgoal_v1_compute_authorization.json',
                     'research/progress_subgoal_v1/execution_lock.json', 'research/progress_subgoal_v1/reservation.json'):
            self.assertFalse((ROOT / name).exists(), name)

    def test_live_questionnaire_refuses_non_frozen_timing(self):
        protocol = copy.deepcopy(B.load_protocol(ROOT))
        protocol['experiment']['call_timing']['timeout_seconds'] = 2.0
        with self.assertRaises(PermissionError):
            QN.call_timing(protocol, 'live')
        self.assertEqual(QN.call_timing(B.load_protocol(ROOT), 'live'), QN.frozen_timing())

    def test_complete_new_scope_gate_and_notebook_binding_in_fabricated_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gated_fixture(root)
            protocol, execution = B.require_live(root)
            self.assertEqual(execution['attempt_id'], 'psv1r2-fixture0001')
            artifacts = N.launch_artifacts(root)
            metadata = json.loads(artifacts['kernel-metadata.json'])
            self.assertTrue(metadata['enable_gpu'])  # artifacts only; nothing is submitted or run
            self.assertEqual(metadata['machine_shape'], 'NvidiaRtxPro6000')
            self.assertEqual(metadata['dataset_sources'], ['driessmit1/arc3-vllm-h100-wheelhouse-v3/1',
                                                           'fixture/psv1r2-model/1'])
            self.assertEqual(metadata['model_sources'], [])
            self.assertEqual(metadata['competition_sources'], ['arc-prize-2026-arc-agi-3'])
            self.assertEqual(metadata['docker_image'], protocol['kaggle_image']['docker_image'])
            notebook = json.loads(artifacts['profile.ipynb'])
            self.assertIn('research.progress_subgoal_v1_runtime2.run', notebook['cells'][1]['source'])
            working = root / 'working'
            working.mkdir()
            B.consume(root, working)
            with self.assertRaises(FileExistsError):
                B.consume(root, working)

    def test_other_scope_or_changed_limits_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            put = gated_fixture(root)
            compute = B.read_json(root, B.COMPUTE)
            for fields in ({'scope': 'progress-subgoal-v1'}, {'scope': 'control-interface-action-selection-v2'},
                           {'maximum_model_requests': 131}, {'admission_cutoff_seconds': 3120}):
                put(B.COMPUTE, {**compute, **fields})
                with self.assertRaises(B.LiveRefused):
                    B.require_live(root)

    def test_source_drift_and_missing_bindings_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            copy_sources(root)
            for name in N.REVIEW_DOCUMENTS:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes((ROOT / name).read_bytes())
            lock = N.build_review(root / 'notebooks/progress-subgoal-v1-runtime2-review-r5', root=root)
            name = B.review_lock(root)
            B.check_sources(root, name)
            for target in ('research/progress_subgoal_v1/questions.py', 'research/progress_subgoal_v1/probes.json',
                           'certification/direct_publisher_smoke_v1/install.py'):
                original = (root / target).read_bytes()
                (root / target).write_bytes(original + b'\n')
                with self.assertRaisesRegex(ValueError, 'source drift'):
                    B.check_sources(root, name)
                (root / target).write_bytes(original)
            path = root / name
            reduced = dict(lock, bindings={k: v for k, v in lock['bindings'].items()
                                           if k != 'research/progress_subgoal_v1/score.py'})
            reduced['bindings'].pop('certification/direct_publisher_smoke_v1/proposal.json')
            path.write_text(json.dumps(reduced))
            with self.assertRaisesRegex(ValueError, 'reviewed sources incomplete'):
                B.check_sources(root, name)

    def test_uncertain_submission_is_consumed_and_cannot_be_retried(self):
        from research.progress_subgoal_v1_runtime2 import launch as L

        class Backend:
            calls = 0

            def push(self, folder):
                self.calls += 1
                raise TimeoutError('simulated uncertain response')
        artifacts = {'kernel-metadata.json': b'{"id":"fixture/psv1r2"}',
                     'launch-package-lock.json': b'{"attempt_id":"psv1r2-fixture0001"}'}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package = root / 'launch'
            package.mkdir()
            for name, data in artifacts.items():
                (package / name).write_bytes(data)
            backend = Backend()
            with patch.object(L, 'launch_artifacts', return_value=artifacts):
                with self.assertRaises(TimeoutError):
                    L.submit(root, package, backend)
                receipt = json.loads((root / B.RECEIPT).read_bytes())
                self.assertEqual(receipt['status'], 'submission_uncertain')
                with self.assertRaises(L.LaunchRefused):
                    L.submit(root, package, backend)
            self.assertEqual(backend.calls, 1)


if __name__ == '__main__':
    unittest.main()
