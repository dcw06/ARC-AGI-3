"""Exercise the actual unpacked target source with no Kaggle or GPU access."""
import ast
import base64
import json
import lzma
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagedImportTests(unittest.TestCase):
    def test_split_install_imports_from_notebook_payload_without_checkout(self):
        notebook = json.loads((ROOT / 'notebooks/phase4-grounded-action-v1-launch-r10/profile.ipynb').read_bytes())
        tree = ast.parse(notebook['cells'][1]['source'])
        decodes = [ast.literal_eval(node.args[0]) for node in ast.walk(tree)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and
                   node.func.attr == 'b85decode' and len(node.args) == 1]
        self.assertEqual(len(decodes), 1)
        payload = json.loads(lzma.decompress(base64.b85decode(decodes[0])))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, encoded in payload.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(base64.b64decode(encoded, validate=True))
            code = '''
import sys
sys.path.insert(0, sys.argv[1])
from certification.phase4_integrated_v2.prepare import prepare
from certification.phase4_v6.target_install_probe_r3 import TORCH_CONTRACT
from scripts.phase4_grounded_action_v1_launch import run_game_supervisor
from research.grounded_action_v1.target_supervisor import run_live
assert callable(prepare)
assert TORCH_CONTRACT['wheel']
assert callable(run_game_supervisor) and callable(run_live)
'''
            result = subprocess.run([sys.executable, '-I', '-c', code, str(root)],
                                    cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
