"""Synthetic CPU review locks; never calls Kaggle or supplies live authority."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import build_semantic_transport_check as B
from tests.archive_transport_fixture import build


class Builder(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        data, transport, original, _ = build(self.root / 'input')
        self.protocol = {'schema': 'semantic_transport_cpu_check_v1', 'scope': B.SCOPE,
            'dataset_ref': 'owner/dataset', 'dataset_version': 1, 'notebook_ref': 'owner/transport-check',
            'docker_image': 'gcr.io/kaggle-private-byod/python@sha256:' + '3' * 64,
            'transport_manifest_sha256': transport, 'original_manifest_sha256': original}
        files = [{'name': 'transport-manifest.json', 'bytes': (self.root / 'input/transport-manifest.json').stat().st_size,
                  'sha256': transport, 'pass': True}]
        files += [{'name': part['name'], 'bytes': part['stored_bytes'], 'sha256': part['sha256'], 'pass': True}
                  for row in data['originals'] for part in row['chunks']]
        self.provider = {'verified': True, 'ref': 'owner/dataset', 'private': True, 'collaborators': 0,
            'version': 1, 'manifest_sha256': transport, 'all_21_remote_file_hashes_match': True,
            'all_12_reconstructed_original_hashes_match': True, 'files': files,
            'originals': [dict(name=row['name'], bytes=row['bytes'], sha256=row['sha256'], **{'pass': True})
                          for row in data['originals']]}

    def build(self, name='packet'):
        (self.root / 'protocol.json').write_bytes(B.canonical(self.protocol))
        (self.root / 'provider.json').write_bytes(B.canonical(self.provider))
        return B.build(self.root / 'protocol.json', self.root / 'input/transport-manifest.json',
                       self.root / 'provider.json', self.root / name)

    def test_reproducible_review_and_disabled_notebook_refusal(self):
        first, second = self.build('a'), self.build('b')
        self.assertEqual(first['review_lock_sha256'], second['review_lock_sha256'])
        book = json.loads((self.root / 'a/profile.ipynb').read_bytes())
        self.assertIsNone(B.authority_from(book))
        with patch.object(Path, 'mkdir', side_effect=AssertionError('filesystem touched')):
            with self.assertRaisesRegex(SystemExit, 'APPROVAL REQUIRED'):
                exec(''.join(book['cells'][-1]['source']), {'AUTHORITY': None})
        metadata = json.loads((self.root / 'a/kernel-metadata.json').read_bytes())
        self.assertFalse(metadata['enable_gpu'])
        self.assertFalse(metadata['enable_tpu'])
        self.assertFalse(metadata['enable_internet'])
        self.assertEqual(metadata['dataset_sources'], ['owner/dataset/1'])

    def test_unverified_shared_or_changed_hash_evidence_refuses(self):
        for name in ('verified', 'collaborators', 'hash'):
            with self.subTest(name=name):
                old = json.loads(B.canonical(self.provider))
                if name == 'verified': self.provider['verified'] = False
                if name == 'collaborators': self.provider['collaborators'] = 1
                if name == 'hash': self.provider['files'][0]['sha256'] = '0' * 64
                with self.assertRaises(ValueError): self.build(name)
                self.provider = old

    def test_mutable_image_or_gpu_scope_refuses(self):
        image = self.protocol['docker_image']
        self.protocol['docker_image'] = 'latest'
        with self.assertRaises(ValueError): self.build('mutable')
        self.protocol['docker_image'] = image
        self.protocol['scope'] = dict(B.SCOPE, gpu=True)
        with self.assertRaises(ValueError): self.build('gpu')

    def test_review_artifact_drift_and_nonliteral_authority_refuse(self):
        self.build()
        (self.root / 'packet/review.md').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'artifact differs'):
            B.verify_review(self.root / 'packet')
        book = json.loads((self.root / 'packet/profile.ipynb').read_bytes())
        book['cells'][0]['source'] = ['AUTHORITY = dict()\n']
        with self.assertRaises(ValueError): B.authority_from(book)

    def test_actual_cpu_request_refuses_changed_accelerator_timeout_or_source(self):
        result = self.build()
        authority = {'approved': True, 'owner_answer': 'Synthetic fixture, never live authority',
            'review_lock_sha256': result['review_lock_sha256'], 'runtime_lock_sha256': result['runtime_lock_sha256'],
            'scope': B.SCOPE, 'protocol_sha256': B.digest(B.canonical(self.protocol)),
            'claim_consumed': True, 'attempt_id': 'synthetic'}
        book = B.seal(self.root / 'packet', authority)
        spec = json.loads((self.root / 'packet/launch-spec.json').read_bytes())
        body = dict(spec['save_fields'], text=json.dumps(book), kernel_execution_type='SAVE_AND_RUN_ALL')
        self.assertTrue(B.validate_save(body, self.root / 'packet', authority))
        for changed in ({'enable_gpu': True}, {'enable_internet': True},
                        {'session_timeout_seconds': 3600}, {'machine_shape': 'NvidiaRtxPro6000'},
                        {'dataset_data_sources': []}, {'kernel_execution_type': True},
                        {'text': json.dumps(dict(book, cells=[]))}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                B.validate_save(dict(body, **changed), self.root / 'packet', authority)


if __name__ == '__main__': unittest.main()
