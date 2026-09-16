import json
import copy
from pathlib import Path
import sys
import tempfile
import unittest

from certification.phase4_v2.supervisor import supervise
from certification.phase4_v2.package import build, verify, sha
from certification.phase4_v2.evaluate import evaluate


class SupervisorTests(unittest.TestCase):
    def run_child(self, code, **limits):
        with tempfile.TemporaryDirectory() as folder:
            return supervise(lambda scratch: [sys.executable, '-c', code, str(scratch)],
                             Path(folder) / 'output', seconds=2, reserve=.5, grace=.1, **limits)

    def test_immediate_final_checkpoint_error_retained(self):
        r = self.run_child("import pathlib,sys; (pathlib.Path(sys.argv[1])/'state.json').write_text('{\"status\":\"complete\",\"error\":\"parity\"}')")
        self.assertEqual(r['status'], 'failed')
        self.assertEqual(r['worker']['error'], 'parity')
        self.assertTrue(r['scratch_removed'])

    def test_completed_worker_is_not_certification(self):
        r = self.run_child("import pathlib,sys; (pathlib.Path(sys.argv[1])/'state.json').write_text('{\"status\":\"complete\"}')")
        self.assertEqual(r['status'], 'worker_completed_pending_independent_evaluation')
        self.assertFalse(evaluate(r, [])['passed'])
        self.assertTrue(r['cleanup_verified'])

    def test_hung_worker_killed(self):
        r = self.run_child('import time; time.sleep(30)')
        self.assertEqual(r['status'], 'failed')
        self.assertTrue(r['cleanup_verified'])
        self.assertTrue(r['admission_canceled'])

    def test_final_disk_breach_rejected(self):
        r = self.run_child("import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/'large').write_bytes(b'x'*10000); (p/'state.json').write_text('{\"status\":\"complete\"}')", scratch_bytes=100)
        self.assertEqual(r['status'], 'failed')

    def test_missing_worker_fails(self):
        self.assertFalse(evaluate({}, [])['passed'])


class PackageTests(unittest.TestCase):
    def fixture(self, root):
        (root/'config').mkdir()
        (root/'config/e1_experiment_protocol.yaml').write_text(json.dumps({'development_game_seed_pairs':[{'game_id':'aa00-1234','seed':1}]}))
        folder=root/'env/aa00/1234';folder.mkdir(parents=True)
        (folder/'aa00.py').write_text('pass')
        (folder/'metadata.json').write_text('{}')
        wheels=root/'wheels';wheels.mkdir();(wheels/'fixture.whl').write_bytes(b'wheel fixture, not install evidence')

    def test_package_roundtrip_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root)
            result=build(root/'env',root/'wheels',root/'bundle.zip',root)
            self.assertFalse(result['dependency_resolution_verified'])
            self.assertEqual(len(verify(root/'bundle.zip',expected_sha256=result['archive_sha256'])['files']),3)
            with self.assertRaises(ValueError):
                verify(root/'bundle.zip',expected_sha256='0'*64)

    def test_missing_environment_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root)
            (root/'env/aa00/1234/metadata.json').unlink()
            with self.assertRaises(FileNotFoundError):
                build(root/'env',root/'wheels',root/'bundle.zip',root)


class EvaluatorTests(unittest.TestCase):
    def fixture(self):
        rows = [{'client_id': str(i), 'game_id': 'development', 'environment_seed': 1,
                 'request_seed': 0, 'max_actions': 80} for i in range(110)]
        clients = []
        for row in rows:
            clients.append({**row, 'error': None, 'client_closed': True, 'scorecard_id': row['client_id'],
                'scorecard_receipt': {'card_id': row['client_id']},
                'finalization_status': 'acknowledged_local_framework',
                'lifecycle_journal': [{'kind': k, 'status': 'acknowledged'} for k in ['scorecard_open', 'scorecard_close']],
                'client_journal': [{'kind': 'bootstrap_reset', 'status': 'acknowledged', 'transaction_id': 'b'},
                    {'kind': 'action', 'status': 'acknowledged', 'transaction_id': 'a',
                     'prepared_fields': {'action_id': 1, 'decision_id': 'd'}}],
                'dispatch_audit': [{'action_id': 1, 'action_data': {}, 'legal_actions': [1],
                                    'decision_id': 'd', 'outcome': 'acknowledged'}],
                'result': {'acknowledged_actions': 1, 'terminal_reason': 'win', 'policy_failures': 0,
                           'ambiguous_actions': 0, 'inference_queue_failures': 0,
                           'inference_transport_failures': 0, 'inference_requests': 1, 'inference_completions': 1}})
        report = {'status': 'worker_completed_pending_independent_evaluation', 'error': None,
            'cleanup_verified': True, 'scratch_removed': True, 'elapsed_seconds': 1,
            'peak_rss_bytes': 1, 'peak_scratch_bytes': 1, 'final_scratch_bytes': 1, 'cleanup_seconds': .1,
            'worker': {'clients': clients, 'queue': {'max_size': 110, 'max_age_seconds': 1},
                       'requests': [{'client_id': r['client_id'], 'service_seconds': .1} for r in rows]}}
        return report, rows

    def test_complete_inventory_passes_only_local_scope(self):
        report, rows = self.fixture()
        result = evaluate(report, rows)
        self.assertTrue(result['passed'], result)
        self.assertFalse(result['target_gpu_certified'])
        self.assertIsNone(result['C_admit'])

    def test_missing_duplicate_receipt_actions_and_resources_rejected(self):
        report, rows = self.fixture()
        mutations = [lambda r: r['worker']['clients'].pop(),
                     lambda r: r['worker']['clients'].append(r['worker']['clients'][0]),
                     lambda r: r['worker']['clients'][0].update(scorecard_receipt={}),
                     lambda r: r['worker']['clients'][0]['dispatch_audit'][0].update(legal_actions=[]),
                     lambda r: r.update(peak_rss_bytes=float('nan')),
                     lambda r: r['worker'].update(requests=[])]
        for mutation in mutations:
            value = copy.deepcopy(report);mutation(value)
            self.assertFalse(evaluate(value, rows)['passed'])


if __name__=='__main__': unittest.main()
