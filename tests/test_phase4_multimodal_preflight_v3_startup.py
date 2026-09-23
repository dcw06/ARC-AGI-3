"""CPU regressions for hash identity, bounded progress and killed startup logs."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class StartupTests(unittest.TestCase):
    def test_hash_identity_and_progress(self):
        from evaluation.m0_profile import inventory_artifact_tree as original
        from certification.phase4_multimodal_preflight_v3.model_artifact import inventory_artifact_tree
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'a').write_bytes(b'a'*(9*1024**2));(root/'z').write_bytes(b'z')
            rows=[]; ticks=iter(range(0,100,11))
            result=inventory_artifact_tree(root,clock=lambda:next(ticks),emit=lambda *a,**kw:rows.append((a,kw)))
            self.assertEqual(result,original(root))
            self.assertEqual(rows[-1][1]['bytes_read'],9*1024**2+1)
            self.assertEqual([r[1]['bytes_read'] for r in rows],sorted(r[1]['bytes_read'] for r in rows))
            self.assertTrue(any(r[0][1]=='progress' for r in rows))

    def test_deadline_and_unchanged_cases(self):
        from certification.phase4_multimodal_preflight_v3.startup import check_startup_deadline
        check_startup_deadline(899,False);check_startup_deadline(901,True)
        with self.assertRaises(TimeoutError):check_startup_deadline(901,False)
        root=Path(__file__).resolve().parents[1]/'certification'
        self.assertEqual((root/'phase4_multimodal_preflight_v1/cases.json').read_bytes(),
                         (root/'phase4_multimodal_preflight_v3/cases.json').read_bytes())

    def test_stage_error_marker(self):
        from certification.phase4_multimodal_preflight_v3.startup import stage
        with patch('builtins.print') as output:
            with self.assertRaises(ValueError):
                with stage('processor_load'):raise ValueError('fixture')
        records=[json.loads(call.args[0])['startup'] for call in output.call_args_list]
        self.assertEqual([r['event'] for r in records],['begin','error'])
        self.assertTrue(all('utc' in r and 'monotonic' in r for r in records))
        self.assertTrue(all(call.kwargs['flush'] for call in output.call_args_list))

    def test_supervisor_timeout_retains_markers_after_cleanup(self):
        from certification.phase4_multimodal_preflight_v3.pilot import run
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'output'
            report,result=run(output,Path(__file__).resolve().parents[1],mode='local',seconds=30,reserve=10,fault='startup_timeout')
            self.assertIn('model startup ceiling',report['error'])
            self.assertFalse(result['passed'])
            self.assertTrue(report['cleanup_verified']);self.assertTrue(report['scratch_removed'])
            logs='\n'.join(p.read_text() for p in (output/'logs').glob('*.json'))
            self.assertIn('artifact_hash',logs);self.assertIn('8388608',logs)
            self.assertFalse((output/'worker/model-ready.json').exists())
            self.assertFalse((output/'worker/state.json').exists())

if __name__=='__main__':unittest.main()
