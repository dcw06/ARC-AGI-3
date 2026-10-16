"""Pure offline deployment guards; all approvals here are synthetic unit fixtures."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest

from research.object_discovery_boundaries_v1 import deployment as D
from research.object_identification_v1.mount_check import canonical
from research.object_discovery_boundaries_v1.supervisor import SCOPE


class DeploymentGuard(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        protocol = canonical({'scope': SCOPE, 'live_runs_enabled': True, 'source_bindings_confirmed': True, 'model':'allenai/MolmoPoint-8B', 'revision':'188130f961c8e0888a34e11121a1423c461a01ba'})
        runtime = canonical({'artifacts': {'protocol.json': D.digest(protocol)}})
        book = {'cells': [{'cell_type': 'code', 'id': 'launch-authority', 'source': ['AUTHORITY = None\n'],
                           'metadata': {}, 'execution_count': None, 'outputs': []},
                          {'cell_type': 'code', 'id': 'bootstrap', 'source': ['pass\n'],
                           'metadata': {}, 'execution_count': None, 'outputs': []}],
                'nbformat': 4, 'nbformat_minor': 5, 'metadata': {}}
        fields = {'slug': 'owner/fixture', 'new_title': 'Fixture', 'is_private': True,
            'enable_gpu': True, 'enable_tpu': False, 'enable_internet': False,
            'machine_shape': 'NvidiaRtxPro6000', 'session_timeout_seconds': 3600,
            'dataset_data_sources': ['owner/source/1'], 'model_data_sources': [],
            'kernel_data_sources': [], 'competition_data_sources': [], 'language': 'python',
            'kernel_type': 'notebook', 'docker_image': 'fixture@sha256:pinned',
            'docker_image_pinning_type': 'original'}
        files = {'runtime/protocol.json': protocol, 'runtime/runtime-lock.json': runtime,
                 'profile.ipynb': canonical(book), 'launch-spec.json': canonical({'save_fields': fields})}
        for name, raw in files.items():
            path = self.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        (self.root/'review-lock.json').write_bytes(canonical({'artifacts': {n: D.digest(v) for n, v in files.items()}}))
        self.fields = fields
        self.authority = self.make_authority(runtime)

    def make_authority(self, runtime):
        pin = D.verify_review(self.root)
        amendment = b'synthetic time-policy amendment; not a real user approval'
        policy = {'review_lock_sha256': pin, 'approved': True, 'accepted_provider_overhead': True,
            'session_timeout_seconds': 3600, 'worker_seconds': 3300, 'provider_full_job_cap_verified': False,
            'owner_amendment_sha256': D.digest(amendment)}
        use = {'review_lock_sha256': pin, 'approved': True, 'owner_answer': 'synthetic only', 'model':'allenai/MolmoPoint-8B', 'revision':'188130f961c8e0888a34e11121a1423c461a01ba'}
        source = {'review_lock_sha256': pin, 'approved': True, 'owner_answer': 'synthetic only',
            'scope_evidence_sha256': {'time_policy': D.digest(canonical(policy)), 'scoped_use': D.digest(canonical(use))}}
        compute = {'review_lock_sha256': pin, 'approved': True, 'owner_answer': 'synthetic only',
            'scope': SCOPE, 'source_approval_sha256': D.digest(canonical(source))}
        claim = {'review_lock_sha256': pin, 'consumed': True, 'attempt_id': 'synthetic-attempt',
            'authorization_sha256': D.digest(canonical(compute))}
        blobs = [amendment, canonical(source), canonical(compute)]
        return {'review_lock_sha256': pin, 'runtime_lock_sha256': D.digest(runtime),
            'time_policy': policy, 'scoped_use': use, 'source_approval': source,
            'compute_authorization': compute, 'launch_claim': claim,
            'retained_evidence': {D.digest(raw): 'authority/'+D.digest(raw)+'.json' for raw in blobs},
            'evidence_blobs': {D.digest(raw): base64.b64encode(raw).decode() for raw in blobs}}

    def test_seal_changes_only_the_declared_authority_data(self):
        book = D.seal(self.root, self.authority)
        self.assertTrue(D.verify_sealed(self.root, book, self.authority))
        original = json.loads((self.root/'profile.ipynb').read_bytes())
        self.assertIsNone(D.authority_from(original))
        book['cells'][1]['source'] = ['print("changed program")\n']
        with self.assertRaisesRegex(ValueError, 'outside'):
            D.verify_sealed(self.root, book, self.authority)

    def test_unapproved_or_unconsumed_claim_cannot_seal(self):
        with self.assertRaises(ValueError):
            D.seal(self.root, None)
        changed = copy.deepcopy(self.authority)
        changed['launch_claim']['consumed'] = False
        with self.assertRaises(ValueError):
            D.seal(self.root, changed)

    def test_authority_cell_cannot_contain_executable_instructions(self):
        book = json.loads((self.root/'profile.ipynb').read_bytes())
        for source in ('AUTHORITY = None\nprint("side effect")', 'AUTHORITY = __import__("os")',
                       'OTHER = {}', 'AUTHORITY = "approval"'):
            book['cells'][0]['source'] = [source]
            with self.subTest(source=source), self.assertRaises((ValueError, SyntaxError)):
                D.authority_from(book)

    def test_runtime_or_retained_evidence_mutation_refuses(self):
        changed = copy.deepcopy(self.authority)
        first = next(iter(changed['evidence_blobs']))
        changed['evidence_blobs'][first] = base64.b64encode(b'changed').decode()
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            D.seal(self.root, changed)
        (self.root/'runtime/protocol.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'artifact differs'):
            D.seal(self.root, self.authority)

    def test_actual_save_must_match_exact_gpu_budget_sources_and_code(self):
        book = D.seal(self.root, self.authority)
        body = dict(self.fields, kernel_execution_type='SAVE_AND_RUN_ALL', text=json.dumps(book))
        self.assertTrue(D.validate_save(body, self.root, self.authority))
        for delta in ({'machine_shape': 'NvidiaTeslaT4'}, {'enable_internet': True},
                      {'enable_tpu': True}, {'is_private': False}, {'session_timeout_seconds': 3601},
                      {'session_timeout_seconds': True}, {'dataset_data_sources': []},
                      {'kernel_execution_type': True}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                D.validate_save(dict(body, **delta), self.root, self.authority)

    def test_unapproved_exact_bootstrap_refuses_before_imports_or_extraction(self):
        namespace = {'AUTHORITY': None}
        with self.assertRaisesRegex(SystemExit, 'APPROVAL REQUIRED'):
            exec(compile(D.bootstrap(b'{}'), '<bootstrap>', 'exec'), namespace)
        self.assertNotIn('base64', namespace)


if __name__ == '__main__':
    unittest.main()
