import ast
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from certification.phase4_v6 import target_install_probe_r3 as probe
from certification.phase4_v6.build_install_probe_r3 import build


class RepairedProbeTests(unittest.TestCase):
    def test_embedded_source_imports_in_an_isolated_process(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            build(root/'proposal')
            notebook = json.loads((root/'proposal/profile.ipynb').read_text())
            prefix = notebook['cells'][1]['source'].split('candidates=', 1)[0]
            script = root/'check.py'
            script.write_text(prefix + "\ntry:\n"
                "    from certification.phase4_v6.target_install_probe_r3 import TORCH_CONTRACT\n"
                "    assert TORCH_CONTRACT['distribution_version']=='2.10.0'\n"
                "    assert TORCH_CONTRACT['runtime_build']['cuda']=='12.8'\n"
                "finally:\n    import shutil\n    shutil.rmtree(source_root)\n")
            result = subprocess.run([sys.executable, '-I', str(script)],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_repaired_path_shares_deadline_checks_cuda_and_cleans_scratch(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(probe.platform, 'system', return_value='Linux'), \
             patch.object(probe.platform, 'machine', return_value='x86_64'), \
             patch.object(probe.sys, 'version_info', (3, 12)), \
             patch.object(probe, 'verify_wheelhouses', return_value={}), \
             patch.object(probe, 'verify_torch_contract', return_value={}), \
             patch.object(probe.subprocess, 'check_output', return_value=''), \
             patch('certification.phase4_v6.clean_environment.CleanEnvironment') as cls:
            result = probe.run(Path(folder), Path(folder), {}, Path(folder)/'out')
            self.assertTrue(result['passed'])
            self.assertTrue(result['scratch_removed'])
            self.assertLessEqual(cls.call_args.kwargs['seconds'], 900)
            runner = cls.return_value
            runner.bootstrap.assert_called_once()
            self.assertEqual(runner.install.call_count, 2)
            self.assertIn('torch==2.10.0', runner.install.call_args_list[0].args[2])
            runner.check.assert_called_once()
            self.assertEqual(runner.execute.call_args.args[0], 'runtime_cuda_and_isolation')
            self.assertFalse(result['model_loaded'])

    def test_failure_cannot_pass_and_still_removes_scratch(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(probe.platform, 'system', return_value='Linux'), \
             patch.object(probe.platform, 'machine', return_value='x86_64'), \
             patch.object(probe.sys, 'version_info', (3, 12)), \
             patch.object(probe, 'verify_wheelhouses', return_value={}), \
             patch.object(probe, 'verify_torch_contract', return_value={}), \
             patch('certification.phase4_v6.clean_environment.CleanEnvironment') as cls:
            cls.return_value.bootstrap.side_effect = RuntimeError('named bootstrap failure')
            result = probe.run(Path(folder), Path(folder), {}, Path(folder)/'out')
            self.assertFalse(result['passed'])
            self.assertIn('named bootstrap failure', result['error'])
            self.assertFalse(cls.call_args.args[0].exists())
            cls.return_value.install.assert_not_called()

    def test_notebook_embeds_repair_and_frozen_original_dependency(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'notebook'
            lock = build(output)
            self.assertIn('certification/phase4_v6/clean_environment.py', lock['bindings'])
            self.assertIn('certification/phase4_v6/target_install_probe.py', lock['bindings'])
            notebook = json.loads((output/'profile.ipynb').read_text())
            code = notebook['cells'][1]['source']
            ast.parse(code)
            self.assertIn('from certification.phase4_v6.target_install_probe_r3 import run', code)
            metadata = json.loads((output/'kernel-metadata.json').read_text())
            self.assertFalse(metadata['enable_internet'])
            self.assertEqual(metadata['model_sources'], [])
