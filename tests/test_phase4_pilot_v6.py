import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from certification.phase4_v6.pilot import run, ROOT

ENVIRONMENTS=ROOT/'reports/runs/phase4-v2-assets/environment_files'


class PilotTests(unittest.TestCase):
    def test_live_gate_precedes_output_or_processes(self):
        with tempfile.TemporaryDirectory() as directory, patch('subprocess.Popen') as launch:
            output=Path(directory)/'output'
            with self.assertRaises(PermissionError): run(output,ENVIRONMENTS,mode='live')
            self.assertFalse(output.exists()); launch.assert_not_called()

    def test_normal_real_110_development_lifecycles(self):
        with tempfile.TemporaryDirectory() as directory:
            report,result=run(Path(directory)/'output',ENVIRONMENTS)
            self.assertTrue(result['passed'], (report.get('error'),result))
            self.assertEqual(len(report['worker']['clients']),110)
            self.assertFalse(report['worker']['model_inference'])
            self.assertFalse(result['phase4_complete'])
            self.assertGreater(report['monitor_ended_seconds'], report['worker_stopped_seconds'])
            self.assertTrue(report['cleanup_verified'])
            self.assertEqual(len(report['worker']['requests']),len(report['worker']['request_timeline']))

    def test_failures_and_cancellation_are_retained(self):
        for fault in ('monitor','worker','evidence','cancel'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                output=Path(directory)/'output'
                report,result=run(output,ENVIRONMENTS,seconds=9,reserve=6,fault=fault)
                self.assertFalse(result['passed'])
                self.assertEqual(report['status'],'failed')
                self.assertTrue(report['cleanup_verified'],report)
                self.assertEqual(json.loads((output/'control/outer.json').read_text())['status'],'failed')
                if fault=='monitor': self.assertFalse(report['worker_released'])
                if fault=='cancel': self.assertTrue(report['admission_canceled'])
