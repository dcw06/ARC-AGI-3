"""The actual model host must import without game-only distributions."""
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ModelImportBoundaryTests(unittest.TestCase):
    def test_first_cell_import_without_game_packages(self):
        code = '''
import importlib.abc, sys
class ExcludeGamePackages(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('arcengine', 'arc_agi'):
            raise ModuleNotFoundError('game-only dependency imported: ' + fullname)
sys.meta_path.insert(0, ExcludeGamePackages())
sys.path.insert(0, sys.argv[1])
from scripts.phase4_grounded_action_v1_launch import run, run_game_supervisor
assert not any(name.split('.')[0] in ('arcengine', 'arc_agi') for name in sys.modules)
'''
        result = subprocess.run([sys.executable, '-I', '-c', code, str(ROOT)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_host_import_with_arcengine_and_arc_agi_excluded(self):
        code = '''
import importlib.abc, sys
class ExcludeGamePackages(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('arcengine', 'arc_agi'):
            raise ModuleNotFoundError('game-only dependency imported: ' + fullname)
sys.meta_path.insert(0, ExcludeGamePackages())
sys.path.insert(0, sys.argv[1])
from research.grounded_action_v1.target_host import pinned_model_factory, serve_host
from research.grounded_action_v1.bridge_service import canary_request
from research.grounded_action_v1.model_service import TokenGuardedService
assert canary_request()['max_tokens'] == 128
assert not any(name.split('.')[0] in ('arcengine', 'arc_agi') for name in sys.modules)
'''
        result = subprocess.run([sys.executable, '-I', '-c', code, str(ROOT)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
