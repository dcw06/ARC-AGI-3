"""Unit checks of the licence-evidence extraction rules (no wheel needed)."""
import json
import unittest
from pathlib import Path

from scripts import extract_wheelhouse_licenses as X

ROOT = Path(__file__).resolve().parents[1]


class Rules(unittest.TestCase):
    def test_licence_members(self):
        for name in ('pkg-1.0.dist-info/LICENSE', 'pkg-1.0.dist-info/licenses/COPYING.md', 'pkg/NOTICE.txt',
                     'nvidia/License.txt', 'pkg-1.0.dist-info/LICENSE-3RD-PARTY.txt', 'pkg/third_party_notices'):
            self.assertTrue(X.is_licence_member(name), name)
        for name in ('pkg/licensed_module.py', 'pkg/__init__.py', 'pkg-1.0.dist-info/METADATA', 'pkg/'):
            self.assertFalse(X.is_licence_member(name), name)

    def test_families(self):
        self.assertEqual(X.families('Permission is hereby granted, free of charge, to any person'), ['MIT'])
        self.assertIn('Apache-2.0', X.families('Apache License\n Version 2.0, January 2004'))
        self.assertEqual(X.families('GNU LESSER GENERAL PUBLIC LICENSE'), ['LGPL'])
        self.assertEqual(X.families('NVIDIA ... SOFTWARE LICENSE AGREEMENT'), ['NVIDIA-proprietary'])
        self.assertEqual(X.families('no recognisable licence here'), [])

    def test_unsafe_archive_paths_are_refused(self):
        with self.assertRaises(X.ExtractError):
            X.safe_target(Path('/tmp/texts'), 'w.whl', '../../etc/passwd')

    def test_declared_copyleft_regex_has_real_word_boundaries(self):
        source = (ROOT / 'scripts/extract_wheelhouse_licenses.py').read_text(encoding='utf-8')
        self.assertNotIn('\x08', source)
        self.assertIn(r"r'\b(L?GPL|MPL)\b", source)

    def test_committed_evidence_flags(self):
        path = X.INDEX_JSON
        if not path.exists():
            self.skipTest('no committed evidence')
        rows = {r['distribution']: r for r in json.loads(path.read_text(encoding='utf-8'))['wheels']}
        self.assertEqual(len(rows), 174)
        for name in ('certifi', 'tqdm', 'pycountry'):
            self.assertIn('declared_copyleft', rows[name]['flags'], name)
        for name in ('nvidia_cublas_cu12', 'cuda_python', 'cuda_bindings', 'nvidia_nccl_cu12', 'nvidia_nvtx_cu12'):
            self.assertIn('proprietary_terms_present', rows[name]['flags'], name)


if __name__ == '__main__':
    unittest.main()
