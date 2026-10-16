"""Synthetic operator regressions: no real authority, network, model or claim."""
import ast
import base64
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from research.object_discovery_boundaries_v1 import deployment as D, operations as G
from research.object_discovery_boundaries_v1.operator import Operator
from research.object_discovery_boundaries_v1.supervisor import SCOPE
from tests import test_object_boundary_deployment as fixtures

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['research/object_discovery_boundaries_v1/'+name+'.py' for name in ('operations', 'operator', 'kaggle_operator')]


class Fixture:
    def __init__(self, case):
        self.fx = fixtures.DeploymentGuard()
        self.fx.setUp()
        case.addCleanup(self.fx.doCleanups)
        self.temp = tempfile.TemporaryDirectory()
        case.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.p = base/'package'
        self.p.mkdir()
        self.a = base/'approval'
        self.a.mkdir()
        self.fields = dict(self.fx.fields, competition_data_sources=['competition'])
        self.datasets = [{'kind': kind, 'ref': 'owner/'+kind, 'version': 1, 'files': [
            {'name': 'f'+str(i), 'bytes': i, 'sha256': 'a'*64} for i in range(count)]}
            for kind, count in [('model', 34), ('inputs', 9), ('wheelhouse', 177)]]
        protocol = {'scope': SCOPE, 'live_runs_enabled': True, 'source_bindings_confirmed': True, 'model':'allenai/MolmoPoint-8B', 'revision':'188130f961c8e0888a34e11121a1423c461a01ba', 'datasets': self.datasets}
        G.put(self.p/'runtime/protocol.json', protocol)
        G.put(self.p/'runtime/runtime-lock.json', {'artifacts': {'protocol.json': D.digest(G.canonical(protocol))}})
        G.put(self.p/'profile.ipynb', G.load(self.fx.root/'profile.ipynb'))
        G.put(self.p/'launch-spec.json', {'save_fields': self.fields})
        G.put(self.p/'kernel-metadata.json', {'id': self.fields['slug']})
        G.put(self.p/'review-evidence/known-owner-notebook.json', {'target': 'owner/known'})
        files = {p.relative_to(self.p).as_posix(): D.digest(p.read_bytes()) for p in self.p.rglob('*') if p.is_file()}
        G.put(self.p/'review-lock.json', {'artifacts': files,
              'source_sha256': {'research/object_discovery_boundaries_v1/deployment.py': D.digest((ROOT/'research/object_discovery_boundaries_v1/deployment.py').read_bytes())},
              'builder_sha256': D.digest((ROOT/'scripts/build_object_boundary_live.py').read_bytes())})
        self.pin = D.verify_review(self.p)
        self.fx.root = self.p
        authority = self.fx.make_authority((self.p/'runtime/runtime-lock.json').read_bytes())
        blobs = authority.pop('evidence_blobs')
        for pin, name in authority['retained_evidence'].items():
            path = self.a/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(blobs[pin]))
        authority['launch_claim'] = None
        G.put(self.a/'prepared_approval_records_not_launch_authority.json', authority)
        G.put(self.a/'reservation.json', {'reservation_id': 'SYNTHETIC-ONLY', 'review_lock_sha256': self.pin,
                                         'consumed': False, 'scope': SCOPE})
        G.put(self.a/'record-manifest.json', {p.relative_to(self.a).as_posix(): D.digest(p.read_bytes()) for p in self.a.rglob('*') if p.is_file()})
        self.auth = base/'authorization.json'
        G.put(self.auth, {'approved': True, 'owner_answer': 'SYNTHETIC UNIT TEST ONLY', 'scope': SCOPE, 'review_lock_sha256': self.pin})
        self.lock = base/'operator-lock.json'
        G.put(self.lock, {'review_lock_sha256': self.pin, 'operator_source_sha256': {name: D.digest((ROOT/name).read_bytes()) for name in SOURCES}})
        self.op = self.operator()
        self.backend = FakeBackend(self.op)

    def operator(self):
        return Operator(self.p, self.a, self.auth, self.pin, ROOT, self.lock)

    def preflight(self):
        path = self.op.preflight(self.backend)
        if G.load(path)['status'] != 'passed':
            raise AssertionError(G.load(path))
        return path


def serializer(package, book):
    body = dict(G.load(Path(package)/'launch-spec.json')['save_fields'], text=json.dumps(book), kernel_execution_type='SAVE_AND_RUN_ALL')
    body = {key: value for key, value in body.items() if value != []}
    return body, body


class FakeBackend:
    def __init__(self, op):
        self.op, self.events, self.mutation, self.failure = op, [], None, None

    def account(self):
        return 'owner'

    def quota(self):
        return {'total_time_allowed': 10000, 'time_used': 0, 'time_reserved': 0}

    def own_kernels(self, owner):
        return {'owner/known'}

    def dataset(self, item):
        return {'ref': item['ref'], 'version': item['version'], 'private': True, 'ready': True, 'collaborators': 0}, {
            row['name']: row['bytes'] for row in item['files']}

    def save(self, body):
        self.op.before_send(body, G.canonical(body))
        self.events.append('SaveKernel')
        self.body = body
        if self.failure:
            raise TimeoutError('synthetic ambiguous send')
        return {'ref': '/code/owner/fixture', 'url': 'https://example.invalid/unit-test', 'version': 1,
                'error': False, 'invalid_sources': {}}

    def saved(self, target):
        self.events.append('GetKernel')
        spec = G.load(self.op.package/'launch-spec.json')['save_fields']
        meta = dict(spec, ref=spec['slug'], current_version_number=1)
        meta.pop('session_timeout_seconds')  # SDK does not expose this echo.
        if self.mutation:
            meta.update(self.mutation)
        return {'metadata': meta, 'source': self.body['text']}


class OperationalGuards(unittest.TestCase):
    def setUp(self):
        self.f = Fixture(self)

    def prepared(self):
        pre = self.f.preflight()
        book, request, body = self.f.op.prepare(pre, serializer)
        return pre, book, request, body

    def test_sdk_style_empty_lists_are_accepted_but_alternatives_are_not(self):
        _, _, _, body = self.prepared()
        self.assertTrue(G.validate_request(body, self.f.p, self.f.op.authority))
        for delta in ({'kernel_data_sources': ['other/notebook']}, {'model_data_sources': ['other/model']},
                      {'competition_data_sources': []}, {'dataset_data_sources': None}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                G.validate_request(dict(body, **delta), self.f.p, self.f.op.authority)

    @unittest.skipUnless(importlib.util.find_spec('kagglesdk'), 'installed SDK integration requires Linux operator interpreter')
    def test_actual_installed_sdk_serialization(self):
        from research.object_discovery_boundaries_v1.kaggle_operator import serialize
        pre = self.f.preflight()
        _, _, body = self.f.op.prepare(pre, serialize)
        self.assertNotIn('kernelDataSources', body)
        self.assertNotIn('modelDataSources', body)
        self.assertTrue(G.validate_request(body, self.f.p, self.f.op.authority))

    def test_target_id_and_unknown_fields_and_aliases_refuse(self):
        _, _, _, body = self.prepared()
        for delta in ({'id': 12345}, {'id': 0}, {'priority': 1}, {'categoryIds': ['other']},
                      {'isPrivate': True}, {'other_selector': 'x'}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                G.validate_request(dict(body, **delta), self.f.p, self.f.op.authority)

    def test_preflight_mutation_at_send_refuses_before_forwarding(self):
        pre, _, _, body = self.prepared()
        op = self.f.op
        op.records.consume(op.reservation, op.authority['launch_claim'])
        changed = G.load(pre)
        changed.update(status='failed_stop_no_retry', review_lock_sha256='wrong', checked_at_utc=G.stamp())
        pre.write_bytes(G.canonical(changed))
        with self.assertRaisesRegex(ValueError, 'preflight bytes'):
            op.before_send(body, G.canonical(body))
        self.assertFalse((op.records.slot(op.reservation['reservation_id'])/'send.json').exists())

    def test_preflight_status_lock_identity_freshness_checks(self):
        pre = self.f.preflight()
        data = G.load(pre)
        for delta in ({'status': 'failed'}, {'review_lock_sha256': 'wrong'}, {'reservation_id': 'wrong'},
                      {'target': 'wrong'}, {'checks': {}}, {'provider_writes': 1},
                      {'checked_at_utc': (datetime.now(timezone.utc)-timedelta(seconds=301)).isoformat()},
                      {'checked_at_utc': (datetime.now(timezone.utc)+timedelta(seconds=30)).isoformat()}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                G.validate_preflight(G.canonical(dict(data, **delta)), self.f.pin, 'SYNTHETIC-ONLY', 'owner/fixture')

    def test_global_claim_blocks_other_operator_revision(self):
        _, _, _, _ = self.prepared()
        op = self.f.op
        op.records.consume(op.reservation, op.authority['launch_claim'])
        with self.assertRaisesRegex(ValueError, 'consumed'):
            self.f.operator().verify_local()

    def test_legacy_consumption_and_uncertain_partial_claim_refuse(self):
        op = self.f.op
        legacy = op.records.root/'gpu-execution-attempt9-r1'
        G.put(legacy/'launch-claim.json', {'attempt_id': 'SYNTHETIC-ONLY', 'consumed': True})
        with self.assertRaisesRegex(ValueError, 'legacy'):
            op.verify_local()
        # Different reservation: an interrupted mkdir/write is uncertain, never unspent.
        slot = op.records.slot('PARTIAL-SYNTHETIC')
        slot.mkdir()
        with self.assertRaisesRegex(ValueError, 'uncertain'):
            op.records.ensure_unspent({'reservation_id': 'PARTIAL-SYNTHETIC', 'consumed': False})

    def test_atomic_competing_claims_have_one_winner(self):
        self.prepared()
        op = self.f.op
        def consume(_):
            try:
                op.records.consume(op.reservation, op.authority['launch_claim'])
                return True
            except (ValueError, FileExistsError):
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(consume, range(2))), 1)

    def test_failed_preflight_is_preserved_when_refreshed(self):
        self.f.backend.own_kernels = lambda _: {'owner/known', 'owner/fixture'}
        first = self.f.op.preflight(self.f.backend)
        before = first.read_bytes()
        self.assertEqual(G.load(first)['status'], 'failed_stop_no_retry')
        self.f.backend.own_kernels = lambda _: {'owner/known'}
        second = self.f.preflight()
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), before)
        self.f.op.verify_local()  # Still unconsumed.

    def test_inventory_diagnostics_and_null_metadata_hashes(self):
        item = {'kind': 'wheelhouse', 'files': [
            {'name': 'README.md', 'bytes': None, 'sha256': 'a'*64}, {'name': 'wheel', 'bytes': 42, 'sha256': 'b'*64}]}
        self.assertTrue(G.inventory_check(item, {'README.md': 645, 'wheel': 42})['passed'])
        result = G.inventory_check(item, {'README.md': 645, 'wheel': 43, 'extra': 1})
        self.assertFalse(result['passed'])
        self.assertEqual(result['size_mismatches'], ['wheel'])
        self.assertEqual(result['extra'], ['extra'])
        with self.assertRaises(ValueError):
            G.inventory_check(item, {'README.md': True, 'wheel': 42})

    def test_success_requires_post_save_readback(self):
        receipt = self.f.op.launch(self.f.backend, self.f.preflight(), serializer)
        self.assertEqual(self.f.backend.events, ['SaveKernel', 'GetKernel'])
        result = G.load(receipt)
        self.assertTrue(result['provider_saved_package_verified'])
        self.assertFalse(result['provider_session_timeout_echoed'])
        self.assertFalse(result['actual_GPU_allocation_verified'])
        with self.assertRaises(ValueError):
            self.f.op.verify_local()

    def test_readback_mismatch_fails_without_retry(self):
        self.f.backend.mutation = {'machine_shape': 'NvidiaTeslaT4'}
        receipt = self.f.op.launch(self.f.backend, self.f.preflight(), serializer)
        self.assertFalse(G.load(receipt)['provider_saved_package_verified'])
        self.assertEqual(self.f.backend.events.count('SaveKernel'), 1)
        self.assertIn('saved setting differs', G.load(receipt)['reason'])

    def test_uncertain_send_is_not_retried(self):
        self.f.backend.failure = True
        receipt = self.f.op.launch(self.f.backend, self.f.preflight(), serializer)
        self.assertEqual(G.load(receipt)['save_calls_forwarded'], 1)
        self.assertEqual(self.f.backend.events, ['SaveKernel'])
        with self.assertRaises(ValueError):
            self.f.operator().verify_local()

    def test_sdk_validation_failure_spends_no_claim(self):
        def bad_serializer(package, book):
            request, body = serializer(package, book)
            return request, dict(body, id=123)
        receipt = self.f.op.launch(self.f.backend, self.f.preflight(), bad_serializer)
        self.assertFalse(G.load(receipt)['provider_saved_package_verified'])
        self.assertEqual(self.f.backend.events, [])
        self.f.op.verify_local()

    def test_two_transports_cannot_forward_same_claim(self):
        _, _, _, body = self.prepared()
        op = self.f.op
        op.records.consume(op.reservation, op.authority['launch_claim'])
        op.before_send(body, G.canonical(body))
        op.save_forwarded = False  # Even resetting process-local state cannot erase the stable send marker.
        with self.assertRaises(FileExistsError):
            op.before_send(body, G.canonical(body))

    def test_request_and_readback_privacy_image_and_program_mutations(self):
        _, book, _, body = self.prepared()
        metadata = dict(self.f.fields, ref='owner/fixture', current_version_number=1)
        snapshot = {'metadata': metadata, 'source': json.dumps(book)}
        for delta in ({'is_private': False}, {'enable_internet': True}, {'enable_tpu': True},
                      {'docker_image': 'wrong'}, {'current_version_number': 2}, {'dataset_data_sources': ['wrong']},
                      {'session_timeout_seconds': 3601}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                G.validate_saved(dict(snapshot, metadata=dict(metadata, **delta)), book, self.f.p, self.f.op.authority, 1)
        changed = copy.deepcopy(book)
        changed['cells'][1]['source'] = ['different_program()\n']
        with self.assertRaises(ValueError):
            G.validate_saved(dict(snapshot, source=json.dumps(changed)), book, self.f.p, self.f.op.authority, 1)

    def test_operator_guards_are_not_removed_by_optimization(self):
        for name in SOURCES:
            self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(ast.parse((ROOT/name).read_text()))))
        with self.assertRaises(ValueError):
            G.require(False, 'refuse')

    @unittest.skipUnless(importlib.util.find_spec('requests'), 'operator transport requires its installed requests dependency')
    def test_read_only_transport_refuses_save_and_disables_retries(self):
        import requests
        from research.object_discovery_boundaries_v1.kaggle_operator import Backend
        backend = Backend.__new__(Backend)
        backend.operator, backend.allow_save = self.f.op, False
        sent = []
        backend.original = lambda *args, **kwargs: (sent.append(kwargs) or type('Response', (), {'status_code': 200})())
        for url in ('https://www.kaggle.com/api/v1/SaveKernel', 'https://example.invalid/IntrospectToken',
                    'http://www.kaggle.com/api/v1/IntrospectToken', 'https://www.kaggle.com/api/v1/DeleteKernel'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                backend.send(requests.Session(), requests.Request('POST', url, json={}).prepare())
        self.assertEqual(sent, [])
        session = requests.Session()
        backend.send(session, requests.Request('POST', 'https://www.kaggle.com/api/v1/IntrospectToken', json={}).prepare())
        self.assertFalse(sent[0]['allow_redirects'])
        self.assertEqual(sent[0]['timeout'], (15, 60))
        self.assertTrue(all(adapter.max_retries.total == 0 for adapter in session.adapters.values()))

    def test_missing_provider_version_labels_are_recorded_as_missing(self):
        _, book, _, _ = self.prepared()
        metadata = dict(self.f.fields, ref='owner/fixture', current_version_number=1,
                        dataset_data_sources=['owner/source'])
        snapshot = {'metadata': metadata, 'source': json.dumps(book)}
        result = G.validate_saved(snapshot, book, self.f.p, self.f.op.authority, 1)
        self.assertFalse(result['provider_dataset_version_labels_echoed'])
        metadata['dataset_data_sources'] = ['owner/source/2']
        with self.assertRaises(ValueError):
            G.validate_saved(snapshot, book, self.f.p, self.f.op.authority, 1)

    def test_owner_catalogue_deduplicates_rows_and_requires_last_page(self):
        from types import SimpleNamespace
        from research.object_discovery_boundaries_v1.kaggle_operator import Backend
        backend = Backend.__new__(Backend)
        pages = []
        def listing(**kwargs):
            pages.append(kwargs['page'])
            return [SimpleNamespace(ref='/code/owner/known')]*2 if kwargs['page'] == 1 else []
        backend.api = SimpleNamespace(kernels_list=listing)
        self.assertEqual(backend.own_kernels('owner'), {'owner/known'})
        self.assertEqual(pages, [1, 2])
        backend.api = SimpleNamespace(kernels_list=lambda **kwargs: [SimpleNamespace(ref='owner/known')])
        with self.assertRaisesRegex(ValueError, 'pagination incomplete'):
            backend.own_kernels('owner')


if __name__ == '__main__':
    unittest.main()
