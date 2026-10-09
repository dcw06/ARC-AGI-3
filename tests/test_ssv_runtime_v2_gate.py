"""Track 3 runtime v2 live gate, launch packaging, launch accounting and provider-receipt validation.

Synthetic authority trees live only in temporary directories; nothing here creates a real approval, reservation,
claim or receipt, submits a notebook or contacts a provider."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.stagnation_supervision_runtime_v2 import authority as A, launch_tooling as LT, provider_preflight as PP
from research.stagnation_supervision_runtime_v2.notebook import launch_artifacts
from tests import ssv_runtime_v2_fixtures as FX

ROOT = A.ROOT


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ThisCheckout(unittest.TestCase):
    def test_live_gate_refuses_with_every_reason(self):
        with self.assertRaises(A.LiveRefused) as caught:
            A.require_live(ROOT)
        reasons = ' '.join(caught.exception.reasons)
        self.assertIn('unresolved placeholders: kernel_ids.1, kernel_ids.2, model.kaggle_source, model.mounted_path', reasons)
        # With the r1 review snapshot committed, the gate passes source binding and stops at the absent decisions.
        self.assertTrue('no review source lock' in reasons or 'source_approval.json' in reasons, reasons)

    def test_no_authority_record_exists_in_the_repository(self):
        records = ROOT / A.RECORDS
        self.assertFalse(records.exists())
        for name in (A.SOURCE, A.COMPUTE, A.LAUNCH, A.EXECUTION, A.RESERVATION, A.CLAIM, A.RECEIPT, A.ACCOUNT,
                     A.PERMISSION, A.BYTES, A.MODEL):
            self.assertFalse((ROOT / name).exists(), name)

    def test_every_launch_step_refuses_here(self):
        with self.assertRaises(A.LiveRefused):
            launch_artifacts(ROOT)
        with self.assertRaises(LT.LaunchRefused):
            LT.claim(ROOT)

        class Backend:
            pushed = 0

            def push(self, folder):
                Backend.pushed += 1
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LT.LaunchRefused):
                LT.write_package(ROOT, Path(tmp) / 'package')
            with self.assertRaises(LT.LaunchRefused):
                LT.submit(ROOT, Path(tmp), Backend(), [])
        self.assertEqual(Backend.pushed, 0)
        self.assertFalse((ROOT / A.RECEIPT).exists())

    def test_process_gates_refuse_before_any_side_effect(self):
        from research.stagnation_supervision_runtime_v2 import resources, supervisor, worker
        with self.assertRaises(PermissionError):
            worker.gate('live')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PermissionError):
                resources.LiveProbes(1, tmp)
            with self.assertRaises(PermissionError):
                supervisor.run(Path(tmp) / 'out', tmp, '/bin/false', '/bin/true', tmp, started=0.0, mode='live', session='1')
            self.assertFalse((Path(tmp) / 'out').exists())


class SyntheticAuthority(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = FX.authority_tree(Path(self.temp.name) / 'root')

    def rewrite(self, name, **changes):
        path = self.root / name
        value = json.loads(path.read_bytes())
        value.update(changes)
        path.write_text(json.dumps(value), encoding='utf-8')

    def test_complete_bound_records_pass_and_the_package_is_built(self):
        protocol, execution = A.require_live(self.root)
        self.assertEqual((execution['attempt_id'], execution['session']), (FX.ATTEMPT, '1'))
        artifacts = launch_artifacts(self.root)
        metadata = json.loads(artifacts['kernel-metadata.json'])
        self.assertEqual(metadata['id'], FX.OWNER + '/arc3-ssv1-runtime-v2-session-1')
        self.assertLessEqual(len(metadata['id'].split('/')[1]), 50)
        self.assertIs(metadata['enable_gpu'], True)
        self.assertIs(metadata['enable_internet'], False)
        self.assertEqual(metadata['machine_shape'], 'NvidiaRtxPro6000')
        self.assertEqual(metadata['dataset_sources'], ['driessmit1/arc3-vllm-h100-wheelhouse-v3/1', FX.MODEL])
        self.assertEqual(metadata['model_sources'], [])
        self.assertEqual(metadata['competition_sources'], ['arc-prize-2026-arc-agi-3'])
        self.assertEqual(metadata['docker_image'], protocol['kaggle_image']['docker_image'])
        code = json.loads(artifacts['profile.ipynb'])['cells'][1]['source']
        self.assertEqual(code.count("SESSION = '1'\n"), 1)
        self.assertIn('authority sidecar drift', code)
        self.assertLess(len(artifacts['profile.ipynb']), 900000)
        lock = json.loads(artifacts['launch-package-lock.json'])
        self.assertEqual(lock['attempt_id'], FX.ATTEMPT)
        self.assertIn(A.CLAIM, lock['sidecars'])

    def test_each_missing_or_mismatched_condition_refuses(self):
        cases = (
            (A.SOURCE, {'explicit_confirmation': False}),
            (A.SOURCE, {'provenance': {**FX.provenance('launch')}}),  # same answer as the launch decision
            (A.COMPUTE, {'sessions': {'1': {**A.SESSION_LIMITS['1'], 'maximum_policy_calls': 601}}}),
            (A.COMPUTE, {'sessions': {'1': A.SESSION_LIMITS['1'], '2': A.SESSION_LIMITS['2']}}),
            (A.COMPUTE, {'consumed_attempts_acknowledged': []}),
            (A.LAUNCH, {'automatic_retries': 1}),
            (A.LAUNCH, {'maximum_submissions': 2}),
            (A.EXECUTION, {'attempt_id': 'ssv1-r5-session1-reservation-001'}),
            (A.RESERVATION, {'status': 'consumed'}),
            (A.RESERVATION, {'events': ['reserve', 'launch']}),
            (A.ACCOUNT, {'consuming_account': 'someone-else'}),
            (A.PERMISSION, {'outstanding_conditions': ['licence review']}),
            (A.BYTES, {'wheel_bytes_verified': 173}),
            (A.MODEL, {'tree_sha256': '0' * 64}),
            (A.CLAIM, {'attempt_id': 'ssv1rt2-another-0002'}),
        )
        for name, change in cases:
            with self.subTest(name=name, change=sorted(change)):
                original = (self.root / name).read_bytes()
                self.rewrite(name, **change)
                try:
                    with self.assertRaises(A.LiveRefused):
                        A.require_live(self.root)
                finally:
                    (self.root / name).write_bytes(original)
        A.require_live(self.root)  # restored

    def test_source_and_science_drift_refuse(self):
        for name in ('research/stagnation_supervision_runtime_v2/prepare.py',
                     'research/stagnation_supervision_v1/trigger_spec.json'):
            with self.subTest(name):
                path = self.root / name
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                try:
                    with self.assertRaises(A.LiveRefused):
                        A.require_live(self.root)
                finally:
                    path.write_bytes(original)

    def test_claim_is_exclusive_and_any_receipt_spends_the_attempt(self):
        (self.root / A.CLAIM).unlink()
        with self.assertRaises(A.LiveRefused):
            A.require_live(self.root)
        self.assertEqual(LT.claim(self.root), FX.ATTEMPT)
        with self.assertRaises(LT.LaunchRefused):
            LT.claim(self.root)
        (self.root / A.RECEIPT).write_text(json.dumps({'status': 'submission_rejected'}), encoding='utf-8')
        with self.assertRaises(LT.LaunchRefused):
            LT.write_package(self.root, Path(self.temp.name) / 'package')

    def test_submission_requires_fresh_receipts_before_any_push(self):
        folder = Path(self.temp.name) / 'package'
        LT.write_package(self.root, folder)
        pushes = []

        class Backend:
            def push(self, path):
                pushes.append(path)
                return {'ref': '/code/' + FX.OWNER + '/arc3-ssv1-runtime-v2-session-1', 'versionNumber': 1,
                        'url': 'https://www.kaggle.com/code/x', 'invalidDatasetSources': ['driessmit1/arc3-vllm-h100-wheelhouse-v3/1']}
        with self.assertRaises(PermissionError):
            LT.submit(self.root, folder, Backend(), [])
        self.assertEqual(pushes, [])
        self.assertFalse((self.root / A.RECEIPT).exists())
        now = datetime.now(timezone.utc)
        records = receipts(json.loads((self.root / A.PROTOCOL).read_bytes()), self.root, now)
        final = LT.submit(self.root, folder, Backend(), records, clock=now)
        self.assertEqual(final['status'], 'submission_rejected')  # HTTP 200 with an invalid source is a rejection
        self.assertEqual(len(pushes), 1)
        with self.assertRaises(LT.LaunchRefused):
            LT.submit(self.root, folder, Backend(), records, clock=now)
        self.assertEqual(len(pushes), 1)


def receipts(protocol, root, now, *, status=200, age=10, outside=False):
    plan = PP.plan(protocol)
    rows = []
    for (kind, reference), calls in plan.items():
        items = []
        for endpoint, request in calls:
            if endpoint.endswith('ListDatasetFiles'):
                names = sorted(PP.allowed_names(protocol, root, reference))[:3]
                body = {'files': [{'name': 'not-bound.whl' if outside else n} for n in names]}
            elif endpoint.endswith('ListDataFiles'):
                body = {'files': [{'name': 'arc_agi_3_wheels/arc_agi-0.9.8-py3-none-any.whl'}]}
            elif kind == 'competition_sources':
                body = {'ref': reference}
            else:
                body = {'ref': reference.rsplit('/', 1)[0]}
            raw = json.dumps(body).encode()
            items.append({'endpoint': endpoint, 'request': request, 'http_status': status,
                          'observed_at_utc': (now - timedelta(seconds=age)).isoformat(),
                          'response_base64': base64.b64encode(raw).decode(),
                          'response_sha256': hashlib.sha256(raw).hexdigest(), 'truncated': False})
        rows.append({'kind': kind, 'reference': reference, 'calls': items})
    return rows


class ProviderReceipts(unittest.TestCase):
    def test_plan_refuses_unresolved_private_model_binding(self):
        with self.assertRaises(PermissionError):
            PP.plan(json.loads((ROOT / A.PROTOCOL).read_bytes()))

    def test_fresh_identity_bound_receipts_pass_and_every_defect_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = FX.authority_tree(Path(tmp) / 'root')
            protocol = json.loads((root / A.PROTOCOL).read_bytes())
            folder = Path(tmp) / 'package'
            LT.write_package(root, folder)
            now = datetime.now(timezone.utc)
            self.assertEqual(len(PP.validate(folder, receipts(protocol, root, now), protocol, root, now)), 3)
            for bad in (dict(status=403), dict(age=400), dict(outside=True)):
                with self.subTest(**bad), self.assertRaises((PermissionError, ValueError)):
                    PP.validate(folder, receipts(protocol, root, now, **bad), protocol, root, now)
            with self.assertRaises(PermissionError):
                PP.validate(folder, receipts(protocol, root, now)[:2], protocol, root, now)


class ResponseClassification(unittest.TestCase):
    def test_the_archived_r6_response_shape_is_a_rejection(self):
        r6 = {'ref': '/code/daichongwei06/arc3-stagnation-supervision-v1-authorization-r6', 'versionNumber': 1,
              'url': 'https://www.kaggle.com/code/daichongwei06/arc3-stagnation-supervision-v1-authorization-r6',
              'invalidDatasetSources': ['driessmit1/arc3-vllm-h100-wheelhouse-v3'], 'invalidModelSources': []}
        status, findings = LT.classify_response(r6, 'daichongwei06/arc3-stagnation-supervision-v1-authorization-r6')
        self.assertEqual(status, 'submission_rejected')
        self.assertTrue(any('invalidDatasetSources' in f for f in findings))
        for key in LT.REJECTED:
            self.assertEqual(LT.classify_response({**r6, 'invalidDatasetSources': [], key: ['x']}, 'a/b')[0],
                             'submission_rejected')

    def test_only_an_unambiguous_confirmation_is_submitted(self):
        ok = {'ref': '/code/owner/slug', 'versionNumber': 3, 'invalidDatasetSources': []}
        self.assertEqual(LT.classify_response(ok, 'owner/slug')[0], 'submitted')
        self.assertEqual(LT.classify_response({**ok, 'versionNumber': None}, 'owner/slug')[0], 'submission_uncertain')
        self.assertEqual(LT.classify_response({**ok, 'ref': '/code/owner/other'}, 'owner/slug')[0], 'submission_uncertain')
        self.assertEqual(LT.classify_response({**ok, 'error': 'x'}, 'owner/slug')[0], 'submission_rejected')
        self.assertEqual(LT.classify_response('not a mapping', 'owner/slug')[0], 'submission_uncertain')


if __name__ == '__main__':
    unittest.main()
