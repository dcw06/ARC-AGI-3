import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from certification.phase4_v10.pilot import run,ROOT
from certification.phase4_v10.build_notebook import build

class ReviewTests(unittest.TestCase):
    def test_final_acceptance_requires_cleanup_and_deadline(self):
        from certification.phase4_v10.finalize import finalize
        from certification.phase4_v10.evidence import EvidenceStore
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            EvidenceStore(root,'evaluation').save('result.json',{'passed':True})
            EvidenceStore(root,'control').save('notebook-cost.json',
                {'error':None,'dependency_trees_removed':False})
            with patch('certification.phase4_v10.finalize.time.monotonic',return_value=10),self.assertRaises(RuntimeError):
                finalize(root,0,True)
            EvidenceStore(root,'control').save('notebook-cost.json',
                {'error':None,'dependency_trees_removed':True})
            with patch('certification.phase4_v10.finalize.time.monotonic',return_value=10):
                self.assertTrue(finalize(root,0,True)['passed'])
            with patch('certification.phase4_v10.finalize.time.monotonic',return_value=27541),self.assertRaises(RuntimeError):
                finalize(root,0,True)

    def test_dependency_permissions_preserve_executables_and_external_symlinks(self):
        import stat
        from certification.phase4_v10.dependencies import freeze,thaw
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            outside=root/'base-python';outside.write_text('base');outside.chmod(0o755)
            for role in ('game','model'):
                tree=root/role/'venv';tree.mkdir(parents=True)
                (tree/'python').symlink_to(outside)
                (tree/'tool').write_text('tool');(tree/'tool').chmod(0o755)
            freeze(root)
            self.assertEqual(stat.S_IMODE(outside.stat().st_mode),0o755)
            self.assertEqual(stat.S_IMODE((root/'game/venv/tool').stat().st_mode),0o555)
            thaw(root)
            self.assertTrue((root/'game/venv').stat().st_mode & stat.S_IWUSR)

    def test_live_requires_new_authority_before_output_or_launch(self):
        with tempfile.TemporaryDirectory() as directory, patch('subprocess.Popen') as launch:
            output=Path(directory)/'out'
            with self.assertRaises(PermissionError):
                run(output,ROOT/'environment_files',mode='live',seconds=27540,reserve=600)
            launch.assert_not_called()
            self.assertFalse(output.exists())

    def test_review_notebook_stops_before_install_and_gpu_queries(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            lock=build(root/'notebook')
            metadata=json.loads((root/'notebook/kernel-metadata.json').read_text())
            self.assertFalse(metadata['enable_gpu'])
            self.assertFalse(metadata['enable_internet'])
            for name in ('bridge','model_host','model_process','model_transport','entry','prepare','authority'):
                self.assertIn('certification/phase4_v10/'+name+'.py',lock['bindings'])
            code=json.loads((root/'notebook/profile.ipynb').read_text())['cells'][1]['source']
            (root/'run.py').write_text(code)
            result=subprocess.run([sys.executable,'-I',str(root/'run.py')],capture_output=True,text=True,timeout=30)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('v10 requires approved source lock',result.stderr)

    def test_worker_and_monitor_faults_leave_no_owned_groups(self):
        for fault in ('worker','monitor','evidence','cancel'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as directory:
                report,result=run(Path(directory)/'out',ROOT/'reports/runs/phase4-v2-assets/environment_files',
                                  seconds=9,reserve=6,fault=fault)
                self.assertFalse(result['passed'])
                self.assertTrue(report['cleanup_verified'],report)
                self.assertTrue(report['scratch_removed'])
