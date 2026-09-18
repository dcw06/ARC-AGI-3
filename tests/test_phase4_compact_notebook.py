import ast
import base64
import json
import lzma
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib
from scripts.compact_phase4_notebook import compact

ROOT=Path(__file__).resolve().parents[1]


class CompactTests(unittest.TestCase):
    def notebook(self):
        return json.loads((ROOT/'notebooks/phase4-lifecycle-v11-review-r1/profile.ipynb').read_text())

    def payload(self,code):
        return next(n.value for n in ast.walk(ast.parse(code)) if isinstance(n,ast.Assign)
                    and any(isinstance(t,ast.Name) and t.id=='payload' for t in n.targets))

    def test_exact_payload_and_wrapper_preserved(self):
        before=self.notebook();after=compact(before)
        old=before['cells'][1]['source'];new=after['cells'][1]['source']
        old_node=self.payload(old);new_node=self.payload(new)
        original=zlib.decompress(base64.b64decode(old_node.args[0].args[0].args[0].value))
        restored=lzma.decompress(base64.b85decode(new_node.args[0].args[0].args[0].value))
        self.assertEqual(original,restored)
        self.assertEqual(old.replace(ast.get_source_segment(old,old_node),'PAYLOAD'),
                         new.replace(ast.get_source_segment(new,new_node),'PAYLOAD'))
        self.assertLess(len(json.dumps(after,indent=1).encode()),900000)

    def test_review_still_stops_at_authority(self):
        code=compact(self.notebook())['cells'][1]['source']
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'review.py';path.write_text(code)
            result=subprocess.run([sys.executable,'-I',str(path)],capture_output=True,text=True,timeout=30)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('v11 requires approved source lock',result.stderr)

    def test_size_guard_rejects_before_output(self):
        with patch('scripts.compact_phase4_notebook.MAX_NOTEBOOK_BYTES',100):
            with self.assertRaisesRegex(ValueError,'upload guard'):compact(self.notebook())
