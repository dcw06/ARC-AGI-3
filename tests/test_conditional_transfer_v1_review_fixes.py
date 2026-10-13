"""Regressions for the three 97c4c3c review findings; synthetic/offline only."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.conditional_transfer_v1 import attribution as A, build as B, dependencies as D
from research.conditional_transfer_v1 import fixtures as FX, score as SC, schema as S, writer as W


def put(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode() if isinstance(data, str) else data)


class TokenizerReference(unittest.TestCase):
    def test_mismatch_or_incomplete_check_stops_construction(self):
        count = len(json.loads((B.ROOT / D.REFERENCE_AUDIT).read_bytes())['requests'])
        for result in ((count, [{'bad': True}]), (0, []), (count - 1, []),
                       (count + 1, []), (True, []), (count, None)):
            with self.subTest(result=result), \
                    patch.object(B.tokens, 'verify_against_ws3_audit', return_value=result), \
                    patch.object(B.FX, 'generate', side_effect=AssertionError('must refuse before construction')):
                with self.assertRaisesRegex(ValueError, 'tokenizer reference verification failed'):
                    B.artifacts(tokenizer=object())

    def test_failed_check_writes_no_package(self):
        count = len(json.loads((B.ROOT / D.REFERENCE_AUDIT).read_bytes())['requests'])
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(B.tokens, 'Tokenizer', return_value=object()), \
                patch.object(B.tokens, 'verify_against_ws3_audit', return_value=(count, [{'bad': True}])):
            destination = Path(tmp) / 'package'
            with self.assertRaises(ValueError):
                B.build(destination)
            self.assertFalse(destination.exists())

    def test_verified_receipt_binds_exact_coverage_and_reference_bytes(self):
        rows = json.loads((B.ROOT / D.REFERENCE_AUDIT).read_bytes())['requests']
        receipt = D.verify_tokenizer_reference(object(), B.ROOT, lambda t: (len(rows), []))
        self.assertTrue(receipt['verified'])
        self.assertEqual(receipt['checked'], receipt['expected'])
        self.assertEqual(receipt['mismatches'], 0)
        self.assertEqual(len(receipt['reference_audit_sha256']), 64)

    def test_empty_duplicate_or_changed_reference_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rows in ([], [{'probe_id': 'a'}, {'probe_id': 'a'}], [{'probe_id': ''}]):
                put(root, D.REFERENCE_AUDIT, json.dumps({'requests': rows}))
                with self.assertRaisesRegex(ValueError, 'missing or duplicate'):
                    D.verify_tokenizer_reference(object(), root, lambda t: (len(rows), []))
            put(root, D.REFERENCE_AUDIT, json.dumps({'requests': [{'probe_id': 'a'}]}))
            def changed(t):
                put(root, D.REFERENCE_AUDIT, json.dumps({'requests': [{'probe_id': 'b'}]}))
                return 1, []
            with self.assertRaisesRegex(ValueError, 'changed during verification'):
                D.verify_tokenizer_reference(object(), root, changed)


class Attribution(unittest.TestCase):
    def test_category_reference_and_combined_losses_are_independent_at_each_stage(self):
        base = {'answer': 'supported_local', 'required_groups': [['a']], 'eligible_ids': ['a']}
        for stage in ('writer', 'selection'):
            for category, references in ((False, False), (True, False), (False, True), (True, True)):
                altered = copy.deepcopy(base)
                if category:
                    altered['answer'] = 'contradicted'
                if references:
                    altered.update(required_groups=[['b']], eligible_ids=['b'])
                store, package = (altered, altered) if stage == 'writer' else (base, altered)
                result = A.evaluate(base, store, package, S.compact(SC.canonical(package)),
                                    'transfer', {'a', 'b'}, category or references)
                with self.subTest(stage=stage, category=category, references=references):
                    self.assertEqual(result[stage + '_category_loss_or_distortion'], category)
                    self.assertEqual(result[stage + '_reference_loss_or_distortion'], references)
                    self.assertFalse(result['reader_error'])
                    self.assertEqual(result['writer_store_loss_or_distortion'],
                                     (category or references) if stage == 'writer' else False)

    def test_real_category_only_distortion_keeps_reference_flag_clear(self):
        case = FX.build('appearance_match', 0)
        facts = W.source_facts(case)
        truth = SC.judge(facts, case['proposed_rule'], case['target'], 'target_support')
        altered = copy.deepcopy(facts)
        for fact in altered:
            if fact['id'] in truth['eligible_ids']:
                fact['visual'] = 'no_observed_change'
        store = SC.judge(altered, case['proposed_rule'], case['target'], 'target_support')
        result = A.evaluate(truth, store, store, S.compact(SC.canonical(store)), 'target_support',
                            {fact['id'] for fact in facts}, True)
        self.assertTrue(result['writer_category_loss_or_distortion'])
        self.assertFalse(result['writer_reference_loss_or_distortion'])

    def test_reference_alternative_order_is_not_loss(self):
        left = {'answer': 'records', 'required_groups': [['a', 'b'], ['c']], 'eligible_ids': ['a', 'b', 'c']}
        right = {'answer': 'records', 'required_groups': [['c'], ['b', 'a']], 'eligible_ids': ['c', 'a', 'b']}
        self.assertEqual(A.reference_requirements(left), A.reference_requirements(right))


class DependencyBindings(unittest.TestCase):
    def fixture(self, root):
        put(root, 'research/conditional_transfer_v1/__init__.py', '')
        put(root, 'research/conditional_transfer_v1/build.py',
            'def helper():\n    from research.transition_evidence_v2 import vocabulary\n')
        put(root, 'research/transition_evidence_v2/__init__.py', '')
        put(root, 'research/transition_evidence_v2/vocabulary.py',
            'from research.transition_evidence_v1 import vocabulary as V\nACTION_VOCABULARY = tuple(range(8))\n')
        put(root, 'research/transition_evidence_v1/vocabulary.py', 'VERSION = "fixture"\n')
        put(root, D.REFERENCE_AUDIT, '{"requests":[]}')
        put(root, 'reports/conditional_transfer_v1/protocol.md', 'Synthetic test protocol\n')
        for number, name in enumerate(D.ARCHIVE_LOCKS):
            put(root, name, json.dumps({'archive': 'evidence/test-' + str(number) + '.zip'}))
            put(root, 'evidence/test-' + str(number) + '.zip', b'synthetic archive bytes')
        package = root / 'package'
        put(package, 'source_hashes.json', json.dumps(D.source_hashes(root)))
        put(package, 'input_hashes.json', json.dumps(D.input_hashes(root)))
        return package

    def test_import_closure_includes_transitive_local_and_relative_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            put(root, 'research/conditional_transfer_v1/relative.py',
                'from . import build\nfrom ..transition_evidence_v2.vocabulary import ACTION_VOCABULARY\n')
            paths = D.source_paths(root)
            for name in ('research/transition_evidence_v2/vocabulary.py',
                         'research/transition_evidence_v1/vocabulary.py',
                         'research/transition_evidence_v2/__init__.py',
                         'research/conditional_transfer_v1/relative.py'):
                self.assertIn(name, paths)

    def test_changed_dependency_or_input_refuses_before_reconstruction(self):
        for name in ('research/transition_evidence_v2/vocabulary.py', D.REFERENCE_AUDIT,
                     D.ARCHIVE_LOCKS[0], 'evidence/test-0.zip', 'reports/conditional_transfer_v1/protocol.md'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                package = self.fixture(root)
                D.verify_bindings(package, root)
                if name == D.ARCHIVE_LOCKS[0]:
                    put(root, name, json.dumps({'archive': 'evidence/test-1.zip'}))
                else:
                    put(root, name, (root / name).read_bytes() + b'\n# changed\n')
                with self.assertRaisesRegex(ValueError, 'dependency bindings differ'):
                    D.verify_bindings(package, root)

    def test_omitted_binding_is_not_accepted(self):
        for filename in ('source_hashes.json', 'input_hashes.json'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                package = self.fixture(root)
                table = json.loads((package / filename).read_bytes())
                table.pop(next(iter(table)))
                put(package, filename, json.dumps(table))
                with self.assertRaises(ValueError):
                    D.verify_bindings(package, root)

    def test_unsafe_archive_dependency_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            put(root, D.ARCHIVE_LOCKS[0], '{"archive":"../outside.zip"}')
            with self.assertRaisesRegex(ValueError, 'unsafe dependency path'):
                D.input_hashes(root)

    def test_build_check_runs_identity_guard_before_artifacts(self):
        with patch.object(D, 'verify_bindings', side_effect=ValueError('binding mismatch')) as guard, \
                patch.object(B, 'artifacts', side_effect=AssertionError('must not construct')):
            with self.assertRaisesRegex(ValueError, 'binding mismatch'):
                B.build(Path('synthetic-package'), check=True)
        guard.assert_called_once()


if __name__ == '__main__':
    unittest.main()
