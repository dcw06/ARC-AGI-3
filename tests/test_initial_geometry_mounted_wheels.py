"""Mounted dependency and small-notebook regressions; no provider or GPU calls."""
import ast
import base64
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from research.initial_geometry_assistance_v1.engine import verify_game_environment
from research.initial_geometry_assistance_v1.game_wheels import (
    GAME_WHEEL_SOURCE, mounted_game_wheels, verify_mounted_game)
from research.initial_geometry_assistance_v1.geometry import canonical
from research.initial_geometry_assistance_v1.live_io import sha
from research.initial_geometry_assistance_v1.live_operator import check_request_size, MAX_SAVE_BODY_BYTES
from research.initial_geometry_assistance_v1.live_package import build, MAX_NOTEBOOK_BYTES


class MountedWheelChecks(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.game = self.root/'game'
        self.base = self.root/'input'
        self.competition = self.base/'competitions'/GAME_WHEEL_SOURCE['competition']
        self.wheels = self.competition/GAME_WHEEL_SOURCE['directory']
        self.wheels.mkdir(parents=True)
        self.game.mkdir()
        members = {}
        for i in range(31):
            name, raw = f'fixture{i}-1.0-py3-none-any.whl', f'wheel {i}'.encode()
            (self.wheels/name).write_bytes(raw)
            members['wheels/'+name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        (self.game/'environment_files/g/v').mkdir(parents=True)
        raw = b'game = 1\n'
        (self.game/'environment_files/g/v/g.py').write_bytes(raw)
        members['environment_files/g/v/g.py'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        (self.game/'game_requirements.lock').write_bytes(b'fixture==1.0\n')
        (self.game/'receipt.json').write_bytes(canonical({'verified_members': members,
            'requirements_sha256': sha(self.game/'game_requirements.lock')}))
        self.pin = sha(self.game/'receipt.json')

    def verify(self, **kwargs):
        return verify_mounted_game(self.game, self.pin, GAME_WHEEL_SOURCE, base=self.base, **kwargs)

    def test_separate_readonly_mount_preserves_original_receipt(self):
        path, receipt = self.verify()
        self.assertEqual(path, self.wheels)
        self.assertEqual(receipt['wheel_count'], 31)
        self.assertEqual(receipt['game_environment_receipt_sha256'], self.pin)
        self.assertFalse((self.game/'wheels').exists())

    def test_both_provider_layouts_work_but_not_together(self):
        alternate = self.base/GAME_WHEEL_SOURCE['competition']
        self.competition.rename(alternate)
        self.assertEqual(mounted_game_wheels(GAME_WHEEL_SOURCE, base=self.base),
                         alternate/GAME_WHEEL_SOURCE['directory'])
        self.competition.mkdir()
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            self.verify()

    def test_missing_mount_and_changed_source_refuse(self):
        with self.assertRaises(ValueError):
            mounted_game_wheels(GAME_WHEEL_SOURCE, base=self.root/'absent')
        for key in GAME_WHEEL_SOURCE:
            bad = dict(GAME_WHEEL_SOURCE, **{key: 'different'})
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_mounted_game(self.game, self.pin, bad, base=self.base)

    def test_wrong_same_size_wheel_refuses(self):
        wheel = next(self.wheels.iterdir())
        wheel.write_bytes(b'x'*wheel.stat().st_size)
        with self.assertRaisesRegex(ValueError, 'game environment differs'):
            self.verify()

    def test_missing_or_extra_wheel_refuses(self):
        path = next(self.wheels.iterdir())
        raw = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.verify()
        path.write_bytes(raw)
        (self.wheels/'unexpected.whl').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.verify()

    @unittest.skipUnless(sys.platform == 'linux', 'requires Linux symlink support')
    def test_symlink_wheel_and_mount_refuse(self):
        path = next(self.wheels.iterdir())
        outside = self.root/'outside.whl'
        path.rename(outside)
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            self.verify()
        path.unlink()
        outside.rename(path)
        real = self.competition/'elsewhere'
        self.wheels.rename(real)
        self.wheels.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            self.verify()

    def test_deadline_checked_during_hashing(self):
        checks = []
        def expired():
            checks.append(True)
            if len(checks) == 3:
                raise TimeoutError('test deadline')
        with self.assertRaises(TimeoutError):
            self.verify(check=expired)
        self.assertEqual(len(checks), 3)

    def test_game_changes_still_refuse_with_external_wheels(self):
        (self.game/'environment_files/g/v/g.py').write_bytes(b'changed game')
        with self.assertRaisesRegex(ValueError, 'game environment differs'):
            self.verify()

    def test_serialized_request_budget(self):
        self.assertEqual(check_request_size(b'x'*MAX_SAVE_BODY_BYTES), MAX_SAVE_BODY_BYTES)
        with self.assertRaisesRegex(ValueError, 'size budget'):
            check_request_size(b'x'*(MAX_SAVE_BODY_BYTES+1))

    def test_preflight_rejects_changed_competition_wheel_inventory(self):
        from research.initial_geometry_assistance_v1.live_operator import preflight
        root = Path(__file__).resolve().parents[1]
        trusted = json.loads((root/'certification/direct_publisher_smoke_v1/trusted_manifest.json').read_bytes())
        publisher = {row['filename']: row['size'] for row in trusted['artifacts']}
        review = self.root/'preflight-review'
        (review/'scope-review').mkdir(parents=True)
        (review/'scope-review/model-dataset-inventory.json').write_bytes(canonical({'files': []}))
        runtime = {'dataset': {'ref': 'test/wheels', 'publisher_metadata_sha256': {}},
                   'model': {'kaggle_source': 'test/model/1'}, 'game_wheel_source': GAME_WHEEL_SOURCE}
        (review/'runtime.json').write_bytes(canonical(runtime))
        members = json.loads((self.game/'receipt.json').read_bytes())['verified_members']
        lock = {'kernel_id': 'test/notebook', 'game_wheels': {n.split('/', 1)[1]: info
                for n, info in members.items() if n.startswith('wheels/')}}
        class ReadOnlyProvider:
            def account(self): return 'daichongwei06'
            def quota(self): return {'total_time_allowed': 7200, 'time_used': 0, 'time_reserved': 0}
            def own_kernels(self, owner): return set()
            def dataset(self, ref, version, private=False):
                return ({'ref': ref, 'version': version, 'private': True, 'ready': True, 'collaborators': 0},
                        {} if private else publisher)
            def competition_files(self, ref):
                return {GAME_WHEEL_SOURCE['directory']+'/'+n: info['bytes'] for n, info in lock['game_wheels'].items()}
        provider = ReadOnlyProvider()
        with patch('research.initial_geometry_assistance_v1.live_operator.verify_review', return_value=(lock, self.pin)):
            good = preflight(review, root, provider, self.root/'good-preflight.json')
            self.assertIsNone(good['error'])
            self.assertTrue(good['checks']['competition_game_wheels'])
            provider.competition_files = lambda ref: {}
            bad = preflight(review, root, provider, self.root/'bad-preflight.json')
        self.assertFalse(bad['checks']['competition_game_wheels'])
        self.assertIn('competition wheel', bad['error'])

    def test_sealed_package_omits_wheels_but_keeps_receipt_and_pins(self):
        # Build using synthetic test inputs and real source modules. No model,
        # provider, private authority or compute is needed by package sealing.
        source = Path(__file__).resolve().parents[1]
        inputs, scope = self.root/'inputs', self.root/'scope'
        inputs.mkdir()
        scope.mkdir()
        (inputs/'manifest.json').write_bytes(canonical({'automatic_replay_sources_sha256': {}, 'files': {}}))
        (scope/'test-only.md').write_text('SYNTHETIC SCOPE; NOT APPROVAL')
        shutil.copytree(self.wheels, self.game/'wheels')
        runtime = {'input_manifest_sha256': sha(inputs/'manifest.json'), 'game_receipt_sha256': self.pin,
                   'game_wheel_source': deepcopy(GAME_WHEEL_SOURCE), 'kernel_id': 'test/small-package',
                   'kaggle_image': {'docker_image': 'test/image@sha256:fixture'},
                   'dataset': {'ref': 'test/wheels', 'version': 1}, 'model': {'kaggle_source': 'test/model/1'}}
        output = self.root/'review'
        with patch('research.initial_geometry_assistance_v1.live_package.verify_inputs'):
            receipt = build(source, inputs, runtime['input_manifest_sha256'], self.game, self.pin,
                            runtime, output, scope_review=scope)
        lock = json.loads((output/'review-lock.json').read_bytes())
        self.assertEqual(len(lock['game_wheels']), 31)
        self.assertFalse(any(n.startswith('game/wheels/') for n in lock['payload_files']))
        self.assertEqual(lock['payload_files']['game/receipt.json'], self.pin)
        self.assertIn('game/game_requirements.lock', lock['payload_files'])
        self.assertLess((output/'review.ipynb').stat().st_size, MAX_NOTEBOOK_BYTES)
        book = json.loads((output/'review.ipynb').read_bytes())
        tree = ast.parse(book['cells'][2]['source'])
        item = next(n for n in tree.body if isinstance(n, ast.Assign) and
                    isinstance(n.targets[0], ast.Name) and n.targets[0].id == '_raw')
        raw = base64.b64decode(ast.literal_eval(item.value.args[0]), validate=True)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), lock['payload_sha256'])
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertFalse(any(n.startswith('game/wheels/') for n in archive.namelist()))
        self.assertLess(receipt['payload_bytes'], 300_000)


if __name__ == '__main__':
    unittest.main()
