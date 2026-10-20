"""Provider-echo mutation checks; no provider or actual launch authority."""
from copy import deepcopy
import json
import unittest

from research.initial_geometry_assistance_v1.geometry import digest
from research.action_effect_choice_live_v1.live_package import normalized
from research.action_effect_choice_live_v1.live_runtime import SCOPE, check_authority
from research.action_effect_choice_live_v1.live_operator import validate_saved


class ProbeOperatorChecks(unittest.TestCase):
    @staticmethod
    def fixture():
        pin = 'a'*64
        proofs = {kind: {'kind': kind, 'approved': True, 'review_lock_sha256': pin,
                         'scope': SCOPE, 'account': 'daichongwei06',
                         'owner_statement': 'SYNTHETIC UNIT TEST ONLY; NO REAL APPROVAL'}
                  for kind in ('source_approval', 'use_permission', 'compute_authorization')}
        authority = {'review_lock_sha256': pin, 'scope': SCOPE, 'account': 'daichongwei06',
                     'proofs': proofs, **{kind: digest(record) for kind, record in proofs.items()},
                     'attempt_id': 'unit-test', 'reservation': 'unit-test', 'claim': 'unit-test'}
        book = {'cells': [
            {'cell_type': 'code', 'id': 'launch-authority', 'source': 'AUTHORITY = '+repr(authority)+'\n',
             'outputs': [], 'execution_count': None},
            {'cell_type': 'markdown', 'id': 'scope', 'source': 'SYNTHETIC TEST'},
            {'cell_type': 'code', 'id': 'runner', 'source': 'REVIEW_LOCK_SHA256 = '+repr(pin)+'\npass',
             'outputs': [], 'execution_count': None}]}
        expected = {'slug': 'daichongwei06/unit-test', 'is_private': True, 'enable_gpu': True,
                    'enable_tpu': False, 'enable_internet': False, 'machine_shape': 'NvidiaRtxPro6000',
                    'docker_image': 'immutable-test-image', 'dataset_data_sources': ['owner/wheels/1', 'owner/model/1'],
                    'competition_data_sources': ['competition'], 'kernel_data_sources': [], 'model_data_sources': []}
        metadata = {k: v for k, v in expected.items() if k != 'slug'}
        metadata.update(ref=expected['slug'], current_version_number=2, session_timeout_seconds=3600)
        lock = {'save_fields': expected, 'notebook_template_sha256': digest(normalized(book))}
        return pin, authority, lock, {'metadata': metadata, 'source': book}

    def test_actual_provider_echo_binds_privacy_image_shape_and_mounts(self):
        pin, authority, lock, snapshot = self.fixture()
        self.assertEqual(validate_saved(snapshot, lock, pin, 2)['authority'], authority)
        for key, value in [('is_private', False), ('enable_internet', True), ('enable_tpu', True),
                           ('machine_shape', 'NvidiaTeslaT4'), ('docker_image', 'other-image'),
                           ('dataset_data_sources', ['owner/other/1']), ('session_timeout_seconds', 3601),
                           ('current_version_number', 3)]:
            with self.subTest(key=key):
                mutated = deepcopy(snapshot)
                mutated['metadata'][key] = value
                with self.assertRaises(ValueError):
                    validate_saved(mutated, lock, pin, 2)

    def test_provider_source_change_is_not_approval(self):
        pin, _, lock, snapshot = self.fixture()
        snapshot['source']['cells'][2]['source'] += '\nprint("changed")'
        with self.assertRaises(ValueError):
            validate_saved(snapshot, lock, pin, 2)

    def test_old_attempt_scope_cannot_cover_sixteen_scorecards(self):
        pin, authority, _, _ = self.fixture()
        check_authority(authority, pin)
        authority['scope'] = dict(SCOPE, local_scorecards=12)
        with self.assertRaises(PermissionError):
            check_authority(authority, pin)

    def test_provider_missing_echo_is_not_claimed_verified(self):
        pin, _, lock, snapshot = self.fixture()
        del snapshot['metadata']['session_timeout_seconds']
        snapshot['metadata']['dataset_data_sources'] = ['owner/wheels', 'owner/model']
        receipt = validate_saved(snapshot, lock, pin, 2)
        self.assertFalse(receipt['provider_timeout_echoed'])
        self.assertFalse(receipt['provider_dataset_version_labels_echoed'])
        self.assertFalse(receipt['actual_GPU_allocation_verified'])
