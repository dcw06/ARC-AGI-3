import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from agent.e1_policy import CompletionResult
from certification.phase4_v4.authority import authority, ROOT
from certification.phase4_v4.service import audited_completion, SharedModelService
from certification.phase4_v4.evaluate import evaluate
from certification.phase4_v4.build_notebook import build
from tests import test_phase4_integration as fixtures


class ModelIntegrationTests(unittest.TestCase):
    def request(self):
        return {'messages': [{'role': 'user', 'content': 'grid'}], 'max_tokens': 128,
                'chat_template_kwargs': {'enable_thinking': False}}

    def test_live_token_parity_audited(self):
        tokenizer = Mock();tokenizer.apply_chat_template.return_value = [1, 2, 3]
        call = Mock(return_value=CompletionResult('ok', 3, 2))
        result, audit = audited_completion(tokenizer, self.request(), call)
        self.assertEqual(audit['server_prompt_tokens'], 3)
        self.assertEqual(audit['tokenizer_prompt_tokens'], 3)
        self.assertFalse(tokenizer.apply_chat_template.call_args.kwargs['truncation'])
        call.assert_called_once()

    def test_context_overflow_denies_inference(self):
        tokenizer = Mock();tokenizer.apply_chat_template.return_value = [1] * 65536
        call = Mock()
        with self.assertRaises(ValueError): audited_completion(tokenizer, self.request(), call)
        call.assert_not_called()

    def test_missing_or_mismatched_server_usage_rejected(self):
        tokenizer = Mock();tokenizer.apply_chat_template.return_value = [1, 2, 3]
        for result in (CompletionResult('ok'), CompletionResult('ok', 4, 1), CompletionResult('ok', 3, 129)):
            with self.assertRaises(ValueError):
                audited_completion(tokenizer, self.request(), Mock(return_value=result))

    def test_authority_and_start_fail_before_hardware(self):
        with self.assertRaises(PermissionError): authority()
        with patch('agent.production_policy.ModelService.start') as start:
            with self.assertRaises(PermissionError): SharedModelService(Path('/tmp')).start()
            start.assert_not_called()

    def test_bootstrap_gate_works_without_site_packages(self):
        result = subprocess.run([sys.executable, '-S', '-c',
            'from certification.phase4_v4.authority import authority; authority()'],
            cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PermissionError', result.stderr)
        self.assertNotIn('ModuleNotFoundError', result.stderr)

    def test_local_fixture_cannot_be_model_pass(self):
        report, rows = fixtures.EvaluatorTests().fixture()
        result = evaluate(report, rows)
        self.assertFalse(result['passed'])
        self.assertIn('actual model evidence missing', result['errors'])
        self.assertIn('GPU binding/telemetry missing', result['errors'])

    def test_complete_mocked_model_evidence_and_negative_mutations(self):
        report, rows = fixtures.EvaluatorTests().fixture()
        worker = report['worker'];worker['model_inference'] = True
        worker['model_startup_seconds'] = 1
        worker['model_artifact'] = {'tree_sha256': '052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627'}
        worker['canary_audit'] = {'status': 'passed', 'server_prompt_tokens': 3,
                                 'tokenizer_prompt_tokens': 3, 'server_completion_tokens': 1}
        worker['model_token_audit'] = []
        for index, request in enumerate(worker['requests']):
            request['request_sha256'] = str(index)
            worker['model_token_audit'].append({'request_sha256': str(index),
                'tokenizer_prompt_tokens': 3, 'server_prompt_tokens': 3, 'server_completion_tokens': 2})
        report.update(gpu_binding={'gpu_uuid': 'GPU-test', 'initial_telemetry': {'uuid': 'GPU-test', 'name': 'RTX PRO 6000'}},
            gpu_telemetry=[{'uuid': 'GPU-test', 'used_bytes': 1}], gpu_samples=1, peak_vram_bytes=1)
        self.assertTrue(evaluate(report, rows)['passed'])
        for mutate in (lambda r: r['worker'].update(model_token_audit=[]),
                       lambda r: r['gpu_telemetry'][0].update(uuid='different'),
                       lambda r: r['worker'].update(canary_audit=None)):
            bad = copy.deepcopy(report);mutate(bad)
            self.assertFalse(evaluate(bad, rows)['passed'])

    def test_review_notebook_cannot_authorize_gpu(self):
        notebook, metadata, lock = build()
        self.assertFalse(metadata['enable_gpu'])
        self.assertTrue(metadata['is_private'])
        self.assertFalse(metadata['enable_internet'])
        source = notebook['cells'][1]['source']
        if isinstance(source, list): source = ''.join(source)
        compile(source, 'review-notebook', 'exec')
        self.assertLess(source.index('subprocess.run([sys.executable,\'-S\''), source.index('install = subprocess.Popen'))
        self.assertIn('certification/phase4_v4/evaluate.py', lock['bindings'])

    def supervise_fake_gpu(self, error):
        from certification.phase4_v4.supervisor import supervise
        state = json.dumps({'status': 'complete', 'error': error})
        code = "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); (p/'model-ready').touch(); (p/'state.json').write_text(sys.argv[2]); time.sleep(.1)"
        prefix = 'certification.phase4_v4.supervisor.'
        with tempfile.TemporaryDirectory() as d, \
             patch(prefix+'authority', return_value={'attempt_id': 'mock-only'}), \
             patch(prefix+'bind_gpu', return_value={'gpu_uuid': 'GPU-test'}), \
             patch(prefix+'sample_gpu', return_value={'uuid': 'GPU-test', 'used_bytes': 1}), \
             patch(prefix+'gpu_pids', return_value=[]), \
             patch(prefix+'group_exists', return_value=False), \
             patch(prefix+'group_rss_bytes', return_value=1):
            return supervise(lambda scratch: [sys.executable, '-c', code, str(scratch), state],
                Path(d)/'output', seconds=3, reserve=1, grace=.1, interval=.02)

    def test_gpu_supervisor_retains_final_worker_error(self):
        result = self.supervise_fake_gpu('token parity failure')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('token parity', result['error'])
        self.assertTrue(result['cleanup_verified'])

    def test_gpu_supervisor_success_still_needs_evaluator(self):
        result = self.supervise_fake_gpu(None)
        self.assertEqual(result['status'], 'worker_completed_pending_independent_evaluation')
        self.assertGreater(result['gpu_samples'], 0)
        self.assertEqual(result['peak_vram_bytes'], 1)
        self.assertFalse(evaluate(result, [])['passed'])


if __name__ == '__main__': unittest.main()
