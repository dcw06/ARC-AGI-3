"""Offline scope, isolation and late/interrupted finalization regressions."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from research.object_identification_v1 import install_check as I, runtime as R


class CPUInstallationChecks(unittest.TestCase):
    def test_requirement_directives_or_missing_hash_cannot_enter_install(self):
        for raw in (b'--index-url https://example.invalid\n', b'timm==1.0.20\n',
                    b'timm>=1 --hash=sha256:'+b'a'*64):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                I.requirement_pins(raw)
        root = Path(__file__).resolve().parents[1]
        original = (root/'certification/direct_publisher_smoke_v1/trusted_requirements.lock').read_bytes()
        supplemental = (root/'research/object_identification_v1/runtime_requirements_extra.lock').read_bytes()
        self.assertEqual(len(I.requirement_pins(original)), 174)
        self.assertEqual(len(I.requirement_pins(original+b'\n'+supplemental)), 175)

    def test_install_targets_fresh_interpreter_and_both_offline_mounts(self):
        commands = I.install_commands('/host/python', '/temp/venv', '/mounted/wheels',
                                      '/mounted/inputs', '/reviewed/requirements.lock')
        create, install, check = [argv for _, argv in commands]
        self.assertIn('--without-pip', create)
        self.assertNotIn('--system-site-packages', create)
        self.assertEqual(install[:5], ['/host/python', '-m', 'pip', '--python',
                                       str(Path('/temp/venv')/'bin/python')])
        for arg in ('--no-index', '--no-cache-dir', '--require-hashes', '--only-binary=:all:',
                    '/mounted/wheels', '/mounted/inputs'):
            self.assertIn(arg, install)
        self.assertEqual(check[:5], install[:5])

    def test_cuda_wheel_requires_explicit_cpu_mode_and_refuses_initialized_cuda(self):
        torch = SimpleNamespace(version=SimpleNamespace(cuda='12.8'),
                                cuda=SimpleNamespace(is_initialized=lambda: False))
        with self.assertRaisesRegex(ValueError, 'CPU-only'):
            R.require_cpu_execution(torch)
        with patch.dict(os.environ, CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void'):
            R.require_cpu_execution(torch, True)
            with patch.dict(os.environ, CUDA_VISIBLE_DEVICES='0'):
                with self.assertRaisesRegex(ValueError, 'hidden GPU'):
                    R.require_cpu_execution(torch, True)
            torch.cuda.is_initialized = lambda: True
            with self.assertRaisesRegex(ValueError, 'initialized'):
                R.require_cpu_execution(torch, True)

    def candidate(self):
        return {'status': 'checks_passed_pending_provider_completion', 'manifest_sha256': 'm',
                'datasets': {kind: {'files_checked': count, 'all_sha256_matched': True}
                             for kind, count in [('model', 27), ('inputs', 12), ('publisher_wheels', 177)]},
                'cleanup': {'groups_absent': True, 'error': None, 'interrupted': []},
                'temporary_environment_removed': True, 'installed_distributions': 175,
                'rehearsal': {'all_175_distribution_versions_matched': True,
                              'execution_device': 'cpu', 'cuda_initialized': False,
                              'torch_cuda_build': '12.8', 'network_attempts': 0,
                              'pretrained_weights_loaded': False},
                'pretrained_weights_loaded': False, 'model_requests': 0, 'game_actions': 0}

    def test_late_receipt_write_never_creates_completion_witness(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'result.json'
            with patch.object(I.time, 'monotonic', side_effect=[59.9, 60.1]):
                with self.assertRaisesRegex(TimeoutError, 'evidence write'):
                    I.finalize(self.candidate(), path, 0, 60)
            self.assertEqual(json.loads(path.read_bytes())['status'],
                             'checks_passed_pending_provider_completion')
            self.assertFalse(path.with_name('completion-witness.json').exists())

    def test_interruption_after_candidate_is_not_independently_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'result.json'
            with patch.object(I.time, 'monotonic', side_effect=[59.9, KeyboardInterrupt()]):
                with self.assertRaises(KeyboardInterrupt):
                    I.finalize(self.candidate(), path, 0, 60)
            self.assertTrue(path.exists())
            self.assertFalse(path.with_name('completion-witness.json').exists())
            raw = path.read_bytes()
            witness = I.canonical({'result_sha256': hashlib.sha256(raw).hexdigest(),
                                  'elapsed_after_receipt_write_seconds': 59.9})
            with self.assertRaises(ValueError):
                I.validate_completion(raw, witness, 'ERROR', '', 'm')

    def test_collector_rejects_late_stale_or_provider_incomplete_evidence(self):
        raw = I.canonical(self.candidate())
        def witness(elapsed):
            return I.canonical({'result_sha256': hashlib.sha256(raw).hexdigest(),
                                'elapsed_after_receipt_write_seconds': elapsed})
        good = witness(10)
        marker = 'CPU_INSTALL_CHECK_RETURNED '+hashlib.sha256(good).hexdigest()
        self.assertTrue(I.validate_completion(raw, good, 'COMPLETE', marker, 'm'))
        for status, output, manifest in [('ERROR', marker, 'm'), ('RUNNING', marker, 'm'),
                                         ('COMPLETE', '', 'm'), ('COMPLETE', marker, 'other')]:
            with self.subTest(status=status, output=output, manifest=manifest), self.assertRaises(ValueError):
                I.validate_completion(raw, good, status, output, manifest)
        for elapsed in (True, -1, 1700, float('inf'), float('nan')):
            bad = witness(elapsed)
            with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
                I.validate_completion(raw, bad, 'COMPLETE',
                    'CPU_INSTALL_CHECK_RETURNED '+hashlib.sha256(bad).hexdigest(), 'm')
        altered = json.loads(raw)
        altered['cleanup']['groups_absent'] = False
        with self.assertRaises(ValueError):
            I.validate_completion(I.canonical(altered), good, 'COMPLETE', marker, 'm')


if __name__ == '__main__':
    unittest.main()
