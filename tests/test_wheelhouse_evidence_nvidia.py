"""Evidence items 1 and 2 (offline): the CUTLASS binaries pack and the shared NVIDIA deployment assessment are
re-checked against their retained sources; conclusions stay scoped to what was checked."""
import hashlib
import json
import unittest
from pathlib import Path

from scripts import evidence_nvidia_deployment as D

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'reports/wheelhouse_evidence'


def load(name):
    return json.loads((EVIDENCE / f'{name}.json').read_text(encoding='utf-8'))


def retained_ok(record):
    return hashlib.sha256((EVIDENCE / record['file']).read_bytes()).hexdigest() == record['sha256']


class CutlassPack(unittest.TestCase):
    def setUp(self):
        self.pack = load('cutlass_binaries')

    def test_conclusion_is_scoped(self):
        finding = self.pack['finding']
        self.assertEqual(finding['conclusion'], 'No applicable binary redistribution grant identified')
        self.assertIn('not a finding that no permission exists anywhere', finding['scope_of_conclusion'])
        self.assertTrue(finding['not_checked'])
        self.assertIn('status', self.pack)

    def test_exact_refs_checked_and_retained(self):
        refs = self.pack['licence_texts']['eula_by_ref']
        self.assertEqual(sorted(refs), sorted(['v4.2.0', 'v4.2.1', 'v4.3.0', 'v4.3.5', 'v4.4.0', 'v4.4.2', 'v4.5.0',
                                               'main']))
        for record in refs.values():
            self.assertTrue(retained_ok(record))
        self.assertTrue(retained_ok(self.pack['licence_texts']['licence_page']))

    def test_compiled_files_and_header_identified(self):
        base = self.pack['wheels'][0]
        self.assertTrue(base['artifact'].startswith('nvidia_cutlass_dsl_libs_base-4.5.0.dev0'))
        names = sorted(Path(c['path']).name for c in base['files']['compiled'])
        self.assertEqual(names, ['_cutlass_ir.cpython-312-x86_64-linux-gnu.so', 'libcuda_dialect_runtime_static.a',
                                 'libcute_dsl_runtime.so'])
        self.assertEqual([Path(h['path']).name for h in base['files']['header_source_non_python']],
                         ['CuteDSLRuntime.h'])


class DeploymentAssessment(unittest.TestCase):
    def setUp(self):
        self.pack = load('nvidia_deployment_assessment')
        self.products = {p['distribution']: p for p in self.pack['products']}

    def test_scope_is_thirteen_rows_with_reasons_for_exclusions(self):
        self.assertEqual(self.pack['scope']['rows'], 13)
        self.assertEqual(set(self.products), set(D.CUDA_EULA_WHEELS) | set(D.SEPARATE_SLA))
        self.assertIn('cuda_python, cuda_bindings', self.pack['scope']['excluded_with_reason'])

    def test_deployment_facts_are_sourced_and_gaps_are_owner_inputs(self):
        deployment = self.pack['deployment']
        self.assertTrue(all(f['source'] for f in deployment['recorded_facts']))
        joined = ' '.join(deployment['owner_inputs_required']).lower()
        for topic in ('own the r2 dataset', 'access', 'published', 'agreement with nvidia'):
            self.assertIn(topic, joined)

    def test_product_specific_findings(self):
        self.assertEqual(self.products['nvidia_nvshmem_cu12']['file_coverage']['not_named_in_primary'], [])
        self.assertIn('supplement', ' '.join(self.products['nvidia_nvshmem_cu12']['questions']))
        cudnn, cusparselt = self.products['nvidia_cudnn_cu12'], self.products['nvidia_cusparselt_cu12']
        self.assertGreater(cudnn['bundled_vs_primary']['difference_count'], 0)
        self.assertIn('NOT release-specific', cusparselt['primary_source_basis'])
        self.assertIn('Evidence gap', ' '.join(cusparselt['questions']))
        for product in (cudnn, cusparselt):
            self.assertTrue(retained_ok(product['primary_source']))
        self.assertEqual(sorted(self.products['nvidia_cusolver_cu12']['file_coverage']['not_named_in_primary']),
                         ['libcusolverMg.so.11'])

    def test_comparison_helpers(self):
        self.assertTrue(D.label_only('1 ii iv a'))
        self.assertFalse(D.label_only('third party'))
        page = 'nav menu skip a b c d e f g h body words end x y z q r s t u footer'.split()
        bundled = 'a b c d e f g h body words end x y z q r s t u'.split()
        self.assertEqual(D.agreement_body(bundled, page), bundled)


if __name__ == '__main__':
    unittest.main()
