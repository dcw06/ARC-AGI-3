import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from certification.phase4_v13.game_assets import stage_games
from certification.phase4_v2.package import verify_environment_mount


class GameAssetsTests(unittest.TestCase):
    def fixture(self, root):
        mount=root/'mount'; mount.mkdir()
        (mount/'game.py').write_bytes(b'frozen')
        manifest={'files':{'environment_files/game.py':{
            'bytes':6,'sha256':hashlib.sha256(b'frozen').hexdigest()}}}
        return mount, manifest

    def test_extra_game_never_copied(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); mount,manifest=self.fixture(root)
            (mount/'unrelated.py').write_text('do not load')
            with self.assertRaises(ValueError): verify_environment_mount(mount,manifest)
            staged=stage_games(mount,root/'staged',manifest)
            self.assertEqual([p.name for p in staged.iterdir()],['game.py'])
            verify_environment_mount(staged,manifest)

    def test_missing_and_modified_expected_files_fail(self):
        for value in (None,b'broken',b'wrong size'):
            with self.subTest(value=value),tempfile.TemporaryDirectory() as temp:
                root=Path(temp); mount,manifest=self.fixture(root)
                (mount/'game.py').unlink()
                if value is not None: (mount/'game.py').write_bytes(value)
                with self.assertRaisesRegex(ValueError,'game'):
                    stage_games(mount,root/'staged',manifest)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); mount,manifest=self.fixture(root)
            outside=root/'outside'; (mount/'game.py').rename(outside)
            (mount/'game.py').symlink_to(outside)
            with self.assertRaisesRegex(ValueError,'symlink'):
                stage_games(mount,root/'staged',manifest)

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); mount,manifest=self.fixture(root)
            manifest['files']['environment_files/../escape']=manifest['files']['environment_files/game.py']
            with self.assertRaisesRegex(ValueError,'unsafe'):
                stage_games(mount,root/'staged',manifest)
            self.assertFalse((root/'escape').exists())

    def test_real_frozen_manifest_with_extra_directory(self):
        repo=Path(__file__).resolve().parents[1]
        manifest=json.loads((repo/'reports/phase4_v2_offline_package.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            shutil.copytree(repo/'reports/runs/phase4-v2-assets/environment_files',root/'mount')
            (root/'mount/unrelated').mkdir()
            (root/'mount/unrelated/extra.py').write_text('not selected')
            staged=stage_games(root/'mount',root/'staged',manifest)
            self.assertEqual(len(list(staged.rglob('*.py'))),15)
            verify_environment_mount(staged,manifest)
