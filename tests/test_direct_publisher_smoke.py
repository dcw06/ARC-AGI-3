"""Scoped gates, trusted installation and launch accounting; fixture evidence only."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from certification.direct_publisher_smoke_v1 import binding as B, install as I, launch as L, notebook as N
from certification.direct_publisher_smoke_v1 import host
from certification.direct_publisher_smoke_v1.rehearsal import fixture_bundle

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IMAGE = 'gcr.io/kaggle-private-byod/python@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461'


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + '\n').encode())


class FixtureRoot:
    """Everything here is fabricated in a temporary test root, never a real approval."""
    def __init__(self, test, kernel_id='fixture/direct-publisher-smoke'):
        self.root = Path(tempfile.mkdtemp(prefix='direct-publisher-gate-fixture-'))
        test.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / B.PACKAGE, self.root / B.PACKAGE, ignore=shutil.ignore_patterns('__pycache__'))
        self.protocol = copy.deepcopy(B.load_protocol())
        self.protocol['kernel_id'] = kernel_id
        put(self.root, B.PROTOCOL, self.protocol)
        N.build_review(self.root / 'notebooks/direct-publisher-smoke-v1-review-r1', root=self.root)
        self.lock = B.review_lock(self.root)
        dataset = {k: self.protocol['dataset'][k] for k in ('ref', 'version')}
        provider_name = 'private/fixture-provider.json'
        put(self.root, provider_name, {'authenticated_account': 'fixture',
                                     'dataset_attachments': [dict(dataset, attachment_confirmed=True)]})
        put(self.root, B.ACCOUNT, {'status': 'verified', 'scope': B.SCOPE, 'dataset': dataset,
                                  'consuming_account': 'fixture', 'verified_at': 'fixture-only',
                                  'provider_evidence': provider_name,
                                  'provider_evidence_sha256': self.sha(provider_name)})
        facts_name = 'private/fixture-assessment.json'
        put(self.root, facts_name, dict(consuming_account='fixture', dataset=dataset,
                                      **{k: 'fixture only, not a real use assessment' for k in (
                                          'licence_holder', 'recipients_and_roles', 'access_controls',
                                          'publication_intent', 'applicable_agreements',
                                          'output_and_payload_handling', 'licence_evidence')}))
        put(self.root, B.PERMISSION, {'status': 'approved', 'approval_kind': 'direct_consumption_permission',
                                     'scope': B.SCOPE, 'dataset': self.protocol['dataset'],
                                     'review_lock_sha256': self.sha(self.lock),
                                     'protocol_sha256': self.sha(B.PROTOCOL),
                                     'trusted_artifacts_sha256': self.protocol['bundle']['approved_manifest_sha256'],
                                     'requirements_lock_sha256': self.protocol['bundle']['requirements_lock_sha256'],
                                     'permission_outcome': 'permitted_for_reviewed_use', 'outstanding_conditions': [],
                                     'reviewer_response': 'fixture test only', 'reviewed_at': 'fixture-only',
                                     'use_assessment': facts_name, 'use_assessment_sha256': self.sha(facts_name)})
        put(self.root, B.BYTES, {'integrity_passed': True, 'wheel_bytes_verified': 174,
                                'dataset_ref': dataset['ref'], 'requested_version': dataset['version'],
                                'trusted_artifacts_sha256': self.protocol['bundle']['approved_manifest_sha256'],
                                'installation_requirements_sha256': self.protocol['bundle']['requirements_lock_sha256']})
        self.authorize()

    def sha(self, name):
        return B.sha256(self.root / name)

    def update(self, name, **fields):
        value = B.read_json(self.root, name)
        value.update(fields)
        put(self.root, name, value)

    def authorize(self):
        common = {'status': 'approved', 'scope': B.SCOPE, 'review_lock_sha256': self.sha(self.lock),
                  'user_response': 'fixture test only', 'approved_at': 'fixture-only',
                  'evidence_bindings': {n: self.sha(n) for n in B.evidence_names(self.root)}}
        put(self.root, B.SOURCE, dict(common, approval_kind='source'))
        put(self.root, B.COMPUTE, dict(common, approval_kind='compute',
                                      source_approval_sha256=self.sha(B.SOURCE),
                                      protocol_sha256=self.sha(B.PROTOCOL), dataset=self.protocol['dataset'],
                                      **{k: self.protocol['limits'][k] for k in B.COMPUTE_LIMITS}))
        execution = {'scope': B.SCOPE, 'attempt_id': 'dps-fixture0001', 'review_lock': self.lock,
                     'review_sha256': self.sha(self.lock), 'source_approval_sha256': self.sha(B.SOURCE),
                     'compute_approval_sha256': self.sha(B.COMPUTE)}
        put(self.root, B.EXECUTION, execution)
        execution_digest = hashlib.sha256(json.dumps(execution, sort_keys=True, indent=2).encode() + b'\n').hexdigest()
        put(self.root, B.RESERVATION, {'status': 'reserved', 'attempt_id': execution['attempt_id'],
                                      'execution_sha256': execution_digest, 'events': ['reserve']})
        put(self.root, B.CLAIM, {'status': 'claimed', 'attempt_id': execution['attempt_id'],
                                'execution_sha256': self.sha(B.EXECUTION),
                                'reservation_sha256': self.sha(B.RESERVATION), 'claimed_at': 'fixture-only'})


class GateTests(unittest.TestCase):
    def refused(self, root):
        with self.assertRaises(B.LiveRefused) as caught:
            B.require_live(root)
        return str(caught.exception)

    def test_checkout_refuses_before_any_effect(self):
        with patch('subprocess.Popen', side_effect=AssertionError('no spawn')):
            reasons = self.refused(ROOT)
        self.assertIn('kernel_id', reasons)
        self.assertIn('authorization', reasons)

    def test_complete_fixture_gate_and_launch_bind_all_private_evidence(self):
        fixture = FixtureRoot(self)
        _, execution = B.require_live(fixture.root)
        self.assertEqual(execution['attempt_id'], 'dps-fixture0001')
        artifacts = N.launch_artifacts(fixture.root)
        metadata = json.loads(artifacts['kernel-metadata.json'])
        self.assertEqual(metadata['id'], 'fixture/direct-publisher-smoke')
        self.assertTrue(metadata['enable_gpu'])
        self.assertEqual(metadata.get('docker_image'), EXPECTED_IMAGE)
        self.assertEqual(metadata.get('docker_image_pinning_type'), 'original')
        package_lock = json.loads(artifacts['launch-package-lock.json'])
        self.assertTrue(set(B.evidence_names(fixture.root)) <= set(package_lock['sidecars']))

    def test_distinct_kernel_slugs_have_distinct_launch_titles(self):
        titles = []
        for slug in ('arc3-direct-publisher-smoke-v1', 'arc3-direct-publisher-smoke-v2'):
            with self.subTest(slug=slug):
                fixture = FixtureRoot(self, kernel_id='fixture/' + slug)
                artifacts = N.launch_artifacts(fixture.root)
                metadata = json.loads(artifacts['kernel-metadata.json'])
                self.assertEqual(metadata['id'], 'fixture/' + slug)
                self.assertEqual(metadata['title'], slug)
                titles.append(metadata['title'])
        self.assertEqual(len(set(titles)), 2)

    def test_missing_sidecars_all_refuse(self):
        for name in (B.SOURCE, B.COMPUTE, B.ACCOUNT, B.PERMISSION, B.BYTES, B.EXECUTION, B.RESERVATION, B.CLAIM):
            with self.subTest(name=name):
                fixture = FixtureRoot(self)
                (fixture.root / name).unlink()
                self.refused(fixture.root)

    def test_scopes_versions_and_compute_limits_refuse(self):
        cases = ((B.SOURCE, {'scope': 'wheelhouse-r2-smoke-v1'}),
                 (B.COMPUTE, {'authorized_seconds': 7200}),
                 (B.COMPUTE, {'maximum_model_requests': 13}),
                 (B.ACCOUNT, {'consuming_account': 'another-fixture'}),
                 (B.ACCOUNT, {'dataset': {'ref': self.dataset_ref(), 'version': 2}}),
                 (B.PERMISSION, {'permission_outcome': 'pending'}),
                 (B.PERMISSION, {'outstanding_conditions': ['still pending']}),
                 (B.PERMISSION, {'requirements_lock_sha256': '0' * 64}),
                 (B.BYTES, {'wheel_bytes_verified': 0}),
                 (B.BYTES, {'integrity_passed': 1}),
                 (B.BYTES, {'requested_version': True}),
                 (B.BYTES, {'requested_version': 2}),
                 (B.BYTES, {'installation_requirements_sha256': '0' * 64}))
        for name, fields in cases:
            with self.subTest(name=name, fields=fields):
                fixture = FixtureRoot(self)
                fixture.update(name, **fields)
                self.refused(fixture.root)

    @staticmethod
    def dataset_ref():
        return B.load_protocol()['dataset']['ref']

    def test_provider_and_assessment_drift_refuse(self):
        for field, receipt in (('provider_evidence', B.ACCOUNT), ('use_assessment', B.PERMISSION)):
            fixture = FixtureRoot(self)
            target = B.read_json(fixture.root, receipt)[field]
            (fixture.root / target).write_bytes(b'{}\n')
            self.refused(fixture.root)

    def test_permission_label_alone_cannot_replace_facts(self):
        fixture = FixtureRoot(self)
        permission = B.read_json(fixture.root, B.PERMISSION)
        put(fixture.root, permission['use_assessment'], {'consuming_account': 'fixture'})
        fixture.update(B.PERMISSION, use_assessment_sha256=fixture.sha(permission['use_assessment']))
        fixture.authorize()
        self.assertIn('assessment lacks', self.refused(fixture.root))

    def test_provider_label_alone_cannot_confirm_attachment(self):
        fixture = FixtureRoot(self)
        receipt = B.read_json(fixture.root, B.ACCOUNT)
        put(fixture.root, receipt['provider_evidence'], {'authenticated_account': 'fixture', 'dataset_attachments': []})
        fixture.update(B.ACCOUNT, provider_evidence_sha256=fixture.sha(receipt['provider_evidence']))
        fixture.authorize()
        self.assertIn('exact attachment version', self.refused(fixture.root))

    def test_provider_confirmation_must_be_boolean_and_version_integer(self):
        for changed in ({'attachment_confirmed': 1}, {'version': True}):
            fixture = FixtureRoot(self)
            receipt = B.read_json(fixture.root, B.ACCOUNT)
            provider = B.read_json(fixture.root, receipt['provider_evidence'])
            provider['dataset_attachments'][0].update(changed)
            put(fixture.root, receipt['provider_evidence'], provider)
            fixture.update(B.ACCOUNT, provider_evidence_sha256=fixture.sha(receipt['provider_evidence']))
            fixture.authorize()
            self.assertIn('exact attachment version', self.refused(fixture.root))

    def test_source_and_input_drift_refuse(self):
        for name in ('server.py', 'preflight.py', 'trusted_manifest.json', 'trusted_requirements.lock'):
            fixture = FixtureRoot(self)
            path = fixture.root / B.PACKAGE / name
            path.write_bytes(path.read_bytes() + b'\n')
            self.assertIn('source drift', self.refused(fixture.root))

    def test_consume_only_once_within_session(self):
        fixture = FixtureRoot(self)
        working = fixture.root / 'working'
        working.mkdir()
        B.consume(fixture.root, working)
        with self.assertRaises(FileExistsError):
            B.consume(fixture.root, working)

    def test_consumed_reservation_and_bad_claim_refuse(self):
        for name, fields in ((B.RESERVATION, {'events': ['reserve', 'consume']}),
                             (B.CLAIM, {'reservation_sha256': '0' * 64})):
            fixture = FixtureRoot(self)
            fixture.update(name, **fields)
            self.refused(fixture.root)

    def test_invalid_protocol_limits_and_version_refuse(self):
        for section, key, value in (('limits', 'maximum_attempts', True),
                                    ('limits', 'maximum_model_requests', 13),
                                    ('limits', 'internal_seconds', 3000),
                                    ('dataset', 'version', True)):
            fixture = FixtureRoot(self)
            fixture.protocol[section][key] = value
            put(fixture.root, B.PROTOCOL, fixture.protocol)
            self.assertIn('protocol unreadable', self.refused(fixture.root))

    def test_wrong_review_scope_refuses(self):
        fixture = FixtureRoot(self)
        fixture.update(fixture.lock, scope='wheelhouse-r2-smoke-v1')
        self.assertIn('source-review scope', self.refused(fixture.root))

    def test_review_snapshot_is_gpu_disabled_and_contains_trusted_inputs(self):
        _, metadata, bindings, pending = N.review_notebook(ROOT)
        self.assertFalse(metadata['enable_gpu'])
        self.assertEqual(pending, ['kernel_id'])
        for name in ('preflight.py', 'trusted_manifest.json', 'trusted_requirements.lock'):
            self.assertIn(B.PACKAGE + '/' + name, bindings)

    def test_review_metadata_pins_compatible_image(self):
        _, metadata, _, _ = N.review_notebook(ROOT)
        self.assertEqual(metadata.get('docker_image'), EXPECTED_IMAGE)
        self.assertEqual(metadata.get('docker_image_pinning_type'), 'original')
        self.assertFalse(metadata['enable_gpu'])

    def test_missing_or_mutable_image_pin_refuses_review(self):
        cases = (None, {}, {'docker_image': EXPECTED_IMAGE},
                 {'docker_image': EXPECTED_IMAGE, 'docker_image_pinning_type': 'latest'},
                 {'docker_image': 'gcr.io/kaggle-private-byod/python:latest', 'docker_image_pinning_type': 'original'})
        for pin in cases:
            with self.subTest(pin=pin):
                fixture = FixtureRoot(self)
                fixture.protocol.pop('kaggle_image', None)
                if pin is not None:
                    fixture.protocol['kaggle_image'] = pin
                put(fixture.root, B.PROTOCOL, fixture.protocol)
                with self.assertRaisesRegex(ValueError, 'image pin required'):
                    N.review_notebook(fixture.root)

    def test_reviewed_image_pin_drift_refuses_launch(self):
        for changes in ({'docker_image': 'gcr.io/kaggle-private-byod/python@sha256:' + '0' * 64},
                        {'docker_image_pinning_type': 'latest'},
                        {'docker_image': None}):
            with self.subTest(changes=changes):
                fixture = FixtureRoot(self)
                metadata_name = str(Path(fixture.lock).parent / 'kernel-metadata.json')
                fixture.update(metadata_name, **changes)
                lock = B.read_json(fixture.root, fixture.lock)
                lock['artifacts']['kernel-metadata.json'] = fixture.sha(metadata_name)
                put(fixture.root, fixture.lock, lock)
                fixture.update(B.PERMISSION, review_lock_sha256=fixture.sha(fixture.lock))
                fixture.authorize()
                with self.assertRaisesRegex(ValueError, 'review image pin differs'):
                    N.launch_artifacts(fixture.root)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mount, self.inputs = self.root / 'mount', self.root / 'inputs'
        self.pins = fixture_bundle(self.mount, self.inputs)

    def test_flat_mount_has_no_r2_manifest_and_verifies_bytes(self):
        self.assertFalse((self.mount / 'bundle-manifest.json').exists())
        self.assertFalse((self.mount / 'wheels').exists())
        receipt = I.verify_bundle(self.mount, self.pins['dataset'], self.pins['bundle'], inputs=self.inputs)
        self.assertTrue(receipt['integrity_passed'])
        self.assertEqual(receipt['wheel_bytes_verified'], 2)

    def test_each_hash_chunk_obeys_combined_installation_deadline(self):
        def expired():
            raise TimeoutError('combined installation deadline')
        with self.assertRaisesRegex(TimeoutError, 'combined installation'):
            I.verify_bundle(self.mount, self.pins['dataset'], self.pins['bundle'], expired, inputs=self.inputs)

    def test_install_uses_flat_mount_and_trusted_hash_lock(self):
        calls = []
        report = {'versions': {'fixturea': '1.0'}, 'imports': {'fixturea': 'fixture'}}
        process = type('Process', (), {'returncode': 0, 'stdout': json.dumps(report), 'stderr': ''})()
        def command(argv, *args):
            calls.append(argv)
            return process
        with patch.object(I, '_run', side_effect=command):
            I.install(self.mount, self.root / 'venv', {'packages': {'fixturea': '1.0'}, 'imports': ['fixturea']},
                      time.monotonic() + 10, self.root / 'install.log',
                      requirements=self.inputs / 'trusted_requirements.lock')
        command = calls[1]
        self.assertIn('--require-hashes', command)
        self.assertIn('--no-index', command)
        self.assertEqual(command[command.index('--find-links') + 1], str(self.mount))
        self.assertEqual(command[command.index('-r') + 1], str(self.inputs / 'trusted_requirements.lock'))
        self.assertNotIn(str(self.mount / 'requirements.lock'), command)

    def test_ambiguous_dataset_mount_refused(self):
        (self.root / 'datasets/fixture/source').mkdir(parents=True)
        (self.root / 'source').mkdir()
        with self.assertRaisesRegex(host.HostMismatch, 'unambiguous mount'):
            host.dataset_mount('fixture/source', 1, base=self.root)


class DurableLaunchTests(unittest.TestCase):
    def test_existing_receipt_spends_attempt(self):
        fixture = FixtureRoot(self)
        put(fixture.root, B.RECEIPT, {'status': 'submission_uncertain'})
        with self.assertRaises(L.LaunchRefused):
            L.claim(fixture.root)

    def test_uncertain_submission_never_retries(self):
        fixture = FixtureRoot(self)
        folder = fixture.root / 'launch'
        L.write_package(fixture.root, folder)
        backend = type('Backend', (), {'push': lambda self, path: {'ref': 'fixture/direct-publisher-smoke'}})()
        receipt = L.submit(fixture.root, folder, backend)
        self.assertEqual(receipt['status'], 'submission_uncertain')
        with self.assertRaises(L.LaunchRefused):
            L.submit(fixture.root, folder, backend)

    def test_provider_response_requires_exact_kernel_and_valid_version(self):
        expected = 'fixture/direct-publisher-smoke'
        self.assertEqual(L.classify_response({'ref': expected, 'versionNumber': 1}, expected)[0], 'submitted')
        for response in ({'ref': 'fixture/other', 'versionNumber': 1}, {'ref': expected}, None):
            self.assertEqual(L.classify_response(response, expected)[0], 'submission_uncertain')
        self.assertEqual(L.classify_response({'invalidDatasetSources': ['fixture/source']}, expected)[0],
                         'submission_rejected')
