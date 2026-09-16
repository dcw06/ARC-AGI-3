import ast
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

from certification.phase4_v6.build_notebook import build


class PackageTests(unittest.TestCase):
    def test_installation_gate_precedes_package_changes(self):
        from certification.phase4_v6.install import install
        with tempfile.TemporaryDirectory() as folder, patch('subprocess.Popen') as launch:
            with self.assertRaises(PermissionError): install('raise AssertionError()',Path(folder)/'output',0)
            launch.assert_not_called()
            self.assertFalse((Path(folder)/'output').exists())

    def test_embedded_source_and_stdlib_gate(self):
        notebook,metadata,lock=build()
        self.assertFalse(metadata['enable_gpu']);self.assertFalse(metadata['enable_internet'])
        self.assertTrue(metadata['is_private'])
        code=notebook['cells'][1]['source'];tree=ast.parse(code)
        self.assertLess(code.index("'-S'"),code.index('install('))
        self.assertLess(code.index('        install('),code.index('from certification.phase4_v6.pilot import run'))
        packed=next(node.args[0].value for node in ast.walk(tree)
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
            and node.func.attr=='b64decode' and isinstance(node.args[0],ast.Constant))
        files=json.loads(zlib.decompress(base64.b64decode(packed)))
        self.assertEqual(set(files),set(lock['bindings']))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name,payload in files.items():
                data=base64.b64decode(payload)
                self.assertEqual(hashlib.sha256(data).hexdigest(),lock['bindings'][name])
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            r=subprocess.run([sys.executable,'-S','-c',
                'from certification.phase4_v6.live_probes import require_live_authority; require_live_authority()'],
                cwd=root,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('PermissionError',r.stderr)
            self.assertNotIn('ModuleNotFoundError',r.stderr)
