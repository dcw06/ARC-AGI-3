import ast
import copy
from pathlib import Path
import unittest

from certification.phase4_v13.canary import valid_canary

ROOT = Path(__file__).resolve().parents[1]


class CanaryTests(unittest.TestCase):
    def setUp(self):
        self.audit = {'status': 'passed', 'action_contract': 'arc_action_v12',
            'server_prompt_tokens': 46, 'tokenizer_prompt_tokens': 46,
            'server_completion_tokens': 29, 'service_seconds': 23.744607003000056,
            'request_sha256': '06853cc44e570cebee4b4623655b73c43072ee040d025e87e47696b3e15fac38'}

    def test_real_receipt_and_boundaries(self):
        for count in (1, 8, 29, 128):
            with self.subTest(count=count):
                self.assertTrue(valid_canary({**self.audit, 'server_completion_tokens': count}))

    def test_rejects_missing_and_invalid_receipts(self):
        for value in (None, {}, [], True, 'passed'):
            self.assertFalse(valid_canary(value))
        for key in self.audit:
            value = self.audit.copy(); del value[key]
            self.assertFalse(valid_canary(value), key)
        invalid = {
            'status': ['attempted', 'failed', True],
            'action_contract': ['arc_action_v11', None],
            'server_prompt_tokens': [0, -1, True, 46.0, 65409],
            'tokenizer_prompt_tokens': [45, 46.0, True],
            'server_completion_tokens': [0, -1, 129, True, 29.0, '29'],
            'service_seconds': [-1, float('nan'), float('inf'), True, '1'],
            'request_sha256': ['', 'z'*64, 'a'*63, None],
        }
        for key, values in invalid.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    self.assertFalse(valid_canary({**self.audit, key: value}))

    def test_all_other_base_checks_unchanged(self):
        old = ast.parse((ROOT/'certification/phase4_v4/evaluate.py').read_text())
        new = ast.parse((ROOT/'certification/phase4_v13/base_evaluate.py').read_text())
        old_fn = next(n for n in old.body if isinstance(n, ast.FunctionDef))
        new_fn = next(n for n in new.body if isinstance(n, ast.FunctionDef))
        start = next(i for i,n in enumerate(old_fn.body) if isinstance(n,ast.Assign)
                     and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='canary')
        old_fn.body[start:start+2] = [copy.deepcopy(new_fn.body[start])]
        self.assertEqual(ast.dump(old_fn), ast.dump(new_fn))

    def test_monitor_capacity_checks_unchanged(self):
        old = ast.parse((ROOT/'certification/phase4_v12/evaluate.py').read_text())
        new = ast.parse((ROOT/'certification/phase4_v13/evaluate.py').read_text())
        functions = lambda tree: [ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)]
        self.assertEqual(functions(old), functions(new))


if __name__ == '__main__': unittest.main()
