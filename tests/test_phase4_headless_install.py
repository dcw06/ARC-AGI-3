import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from certification.phase4_v6 import target_install_probe_r5 as probe


class SplitInstallTests(unittest.TestCase):
    def test_notebook_backend_is_overridden_and_config_stays_in_scratch(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ', {
            'MPLBACKEND':'module://matplotlib_inline.backend_inline', 'MPLCONFIGDIR':'/outside'}):
            root=Path(directory)
            runner=probe.CleanEnvironment(root,root/'evidence')
            self.assertEqual(runner.env['MPLBACKEND'],'Agg')
            self.assertTrue(Path(runner.env['MPLCONFIGDIR']).is_relative_to(root.resolve()))

    def test_notebook_embeds_split_probe_and_imports_in_isolated_process(self):
        import subprocess
        import sys
        from certification.phase4_v6.build_install_probe_r5 import build
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = build(root/'proposal')
            self.assertIn('certification/phase4_v6/target_install_probe_r5.py',lock['bindings'])
            notebook=json.loads((root/'proposal/profile.ipynb').read_text())
            prefix=notebook['cells'][1]['source'].split('candidates=',1)[0]
            script=root/'check.py'
            script.write_text(prefix+"\ntry:\n"
                "    assert run.__module__ == 'certification.phase4_v6.target_install_probe_r5'\n"
                "finally:\n    import shutil\n    shutil.rmtree(source_root)\n")
            result=subprocess.run([sys.executable,'-I',str(script)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_resolve_both_before_install_and_use_distinct_environments(self):
        events = []
        runners = []
        def factory(scratch, output, **kwargs):
            runner = MagicMock()
            runner.env = {}
            runner.output = output
            runner.pip.return_value = ['pip']
            runner.execute.side_effect = lambda *args: events.append(('resolve', scratch.name))
            runner.install.side_effect = lambda *args: events.append(('install', scratch.name, args[2]))
            runners.append(runner)
            return runner
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, 'CleanEnvironment', side_effect=factory):
            root = Path(directory)
            deadline = time.monotonic()+900
            probe.install_pair(root, root/'out', root/'model-wheels', root/'game-wheels', deadline)
            self.assertEqual([row[0] for row in events], ['resolve','resolve','install','install'])
            self.assertIn('numpy==2.2.6', events[2][2])
            self.assertIn('numpy==2.4.4', events[3][2])
            self.assertEqual([r.deadline for r in runners], [deadline,deadline])
            self.assertEqual(runners[1].env['CUDA_VISIBLE_DEVICES'], '')

    def test_resolution_failure_prevents_all_installs(self):
        first, second = MagicMock(), MagicMock()
        first.pip.return_value = second.pip.return_value = ['pip']
        second.execute.side_effect = RuntimeError('dependency conflict')
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, 'CleanEnvironment', side_effect=[first,second]):
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, 'dependency conflict'):
                probe.install_pair(root,root/'out',root,root,time.monotonic()+900)
            first.install.assert_not_called()
            second.install.assert_not_called()

    def test_expired_deadline_prevents_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(probe, 'CleanEnvironment') as factory:
            root = Path(directory)
            with self.assertRaises(TimeoutError):
                probe.install_pair(root,root/'out',root,root,time.monotonic()-1)
            factory.assert_not_called()

    def test_failure_records_cleanup_and_never_claims_cuda_pass(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(probe.platform,'system',return_value='Linux'), \
             patch.object(probe.platform,'machine',return_value='x86_64'), \
             patch.object(probe.sys,'version_info',(3,12)), \
             patch.object(probe,'verify_wheelhouses',return_value={}), \
             patch.object(probe,'verify_torch_contract',return_value={}), \
             patch.object(probe,'install_pair',side_effect=RuntimeError('resolution failed')), \
             patch.object(probe.subprocess,'check_output',return_value=''):
            root = Path(directory)
            result = probe.run(root,root,{},root/'out')
            self.assertFalse(result['passed'])
            self.assertTrue(result['scratch_removed'])
            self.assertTrue(result['gpu_cleanup_verified'])
            self.assertIn('resolution failed',result['error'])
            self.assertEqual(json.loads((root/'out/result.json').read_text()),result)

    def test_leftover_gpu_process_rejects_otherwise_successful_run(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(probe.platform,'system',return_value='Linux'), \
             patch.object(probe.platform,'machine',return_value='x86_64'), \
             patch.object(probe.sys,'version_info',(3,12)), \
             patch.object(probe,'verify_wheelhouses',return_value={}), \
             patch.object(probe,'verify_torch_contract',return_value={}), \
             patch.object(probe,'install_pair',return_value={'model':MagicMock(),'game':MagicMock()}), \
             patch.object(probe.subprocess,'check_output',return_value='1234'):
            root = Path(directory)
            result = probe.run(root,root,{},root/'out')
            self.assertFalse(result['passed'])
            self.assertFalse(result['gpu_cleanup_verified'])
