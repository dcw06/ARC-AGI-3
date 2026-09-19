import copy
import json
import math
from pathlib import Path
import unittest

from certification.phase4_diagnostic_v2.evaluate import evaluate as previous
from certification.phase4_diagnostic_v2.telemetry import read_telemetry
from certification.phase4_diagnostic_v4.evaluate import evaluate, valid_request_window

ROOT=Path(__file__).resolve().parents[1]

def load_report(folder):
    report=json.loads((folder/'control/outer.json').read_text())
    report['worker']=json.loads((folder/'worker/state.json').read_text())
    report['gpu_telemetry']=read_telemetry(folder/'monitor')['samples']
    return report

class DeadlineTests(unittest.TestCase):
    def test_reassociation_roundoff(self):
        self.assertTrue(valid_request_window(797.5437325989999,817.539367565,1997.5437325990001,3300,True))

    def test_real_overruns_and_nonfinite_rejected(self):
        for args in ((797,818,1997+1e-9,3300,True),
                     (1800,1810,math.nextafter(3000,math.inf),3300,True),
                     (1,1201,1201,3300,True), (1,1202,1201,3300,True),
                     (2,1,100,3300,True), (-1,1,100,3300,True),
                     (True,2,100,3300,True), (1,2,math.nan,3300,True),
                     (1,2,math.inf,3300,True)):
            with self.subTest(args=args): self.assertFalse(valid_request_window(*args))

    def test_archived_target_replay_and_negative_controls(self):
        import tempfile,zipfile
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(ROOT/'evidence/phase4-diagnostic-v2-r2-failed-v1.zip') as z:
                z.extractall(tmp)
            report=load_report(Path(tmp)/'phase4-action-diagnostic-v2')
        self.assertEqual(previous(report)['errors'],['request window'])
        self.assertTrue(evaluate(report)['passed'])
        mutations=[('independent_gpu_cleanup_verified',False),('gpu_cleanup_verified',False),
                   ('cleanup_verified',False),('scratch_removed',False)]
        for key,value in mutations:
            changed=copy.deepcopy(report);changed[key]=value
            with self.subTest(key=key):self.assertFalse(evaluate(changed)['passed'])
        for key,value in [('request_window_cutoff_seconds',1997.543732599+1e-6),
                          ('ended_seconds',1997.5437325990001),('requests_started',44)]:
            changed=copy.deepcopy(report);changed['worker'][key]=value
            with self.subTest(key=key):self.assertFalse(evaluate(changed)['passed'])
        changed=copy.deepcopy(report)
        changed['worker']['cases'][0]['audit']['server_prompt_tokens']+=1
        self.assertFalse(evaluate(changed)['passed'])

if __name__=='__main__': unittest.main()
