"""Clean-checkout regression: no ignored reports/runs tree is supplied."""
import json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ArchiveRestoreTests(unittest.TestCase):
    def test_regenerates_without_ignored_environment(self):
        lock=json.loads((ROOT/'reports/phase4_closed_loop_v1_inspection/inspection-lock.json').read_bytes())
        names=set(lock['bindings'])|{
            'scripts/verify_phase4_inspection_recovery.py',
            'reports/phase4_closed_loop_v1_inspection/inspection-lock.json',
            'reports/phase4_closed_loop_v1_evidence_receipt.json',lock['input_archive'],
            'notebooks/phase4-closed-loop-v1-review-r1/review-source-lock.json',
            'reports/phase4_v2_offline_package.json','agent/representation.py',
            'certification/phase4_closed_loop_v1/contract.py','evidence/phase4-v2-development-offline.zip'}
        with tempfile.TemporaryDirectory() as folder:
            checkout=Path(folder)
            for name in names:
                target=checkout/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
            self.assertFalse((checkout/'reports/runs').exists())
            result=subprocess.run([sys.executable,'scripts/verify_phase4_inspection_recovery.py'],cwd=checkout,
                text=True,capture_output=True,timeout=180)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['verified_bindings'],13)
            self.assertFalse((checkout/'reports/runs').exists())

if __name__=='__main__':unittest.main()
