import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from certification.phase4_v12.monitor_diagnostics import collect, failure_receipt
from certification.phase4_v12.monitor import RAM, SCRATCH, VRAM
from certification.phase4_v12.cleanup_probe import check_cleanup, inspect_gpu


class MonitorRepairTests(unittest.TestCase):
    def collect(self, *, delay=0, memory=1, disk=1, used=1):
        clock=[10.0];context={}
        def sample(*_):
            clock[0]+=delay
            return {'uuid':'GPU-test','name':'RTX PRO 6000','used_bytes':used,'total_bytes':96*1024**3}
        try:
            result=collect(sample,lambda _:memory,lambda:disk,'GPU-test',1,0,10,context,
                           clock=lambda:clock[0])
            return result,context
        except Exception as exc:
            return exc,context

    def test_delayed_gpu_retains_exact_rejected_measurement(self):
        error,context=self.collect(delay=1.1)
        self.assertIsInstance(error,ValueError)
        self.assertEqual(context['violations'],['sampling_gap_seconds'])
        self.assertAlmostEqual(context['probe_seconds']['gpu'],1.1)
        self.assertEqual(context['rss_bytes'],1)
        receipt=failure_receipt(error,context)
        self.assertLess(len(json.dumps(receipt).encode()),2048)
        self.assertFalse(receipt['rejected_measurement_is_valid_telemetry'])

    def test_resource_limits_identified_without_relaxation(self):
        for kw,key in [({'memory':RAM+1},'rss_bytes'),({'disk':SCRATCH+1},'scratch_bytes'),
                       ({'used':VRAM+1},'vram_bytes')]:
            with self.subTest(key=key):
                error,context=self.collect(**kw)
                self.assertIsInstance(error,ValueError)
                self.assertIn(key,context['violations'])
        result,_=self.collect(memory=RAM,disk=SCRATCH,used=VRAM,delay=1)
        self.assertIsInstance(result,dict)

    def test_probe_exception_keeps_phase_and_duration(self):
        context={}
        def timeout(*_): raise TimeoutError('probe timeout')
        with self.assertRaises(TimeoutError):
            collect(timeout,None,None,'GPU-test',1,0,0,context,clock=lambda:1)
        self.assertEqual(context['phase'],'gpu')
        self.assertIn('gpu',context['probe_seconds'])

    def test_telemetry_retention_failure_has_reserved_receipt(self):
        from types import SimpleNamespace
        from certification.phase4_v12.pilot_child import monitor
        from certification.phase4_v12.evidence import EvidenceStore
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            args=SimpleNamespace(mode='local',output=root/'out',worker_pid=1,scratch=root,
                started=__import__('time').monotonic(),fault='none',nonce='test')
            with patch('certification.phase4_v12.telemetry.TelemetryWriter.save',side_effect=ValueError('retention failed')):
                with self.assertRaisesRegex(RuntimeError,'retention failed'): monitor(args)
            receipt=json.loads((root/'out/monitor/failure.json').read_text())
            self.assertEqual(receipt['diagnostics']['phase'],'telemetry_writer_health')
            self.assertFalse((root/'out/monitor/ready.json').exists())
            self.assertLess((root/'out/monitor/failure.json').stat().st_size,2048)

    def test_independent_cleanup_unknown_timeout_remaining_and_late(self):
        def empty(*_): return {'gpu_uuid':'GPU-test','remaining_process_count':0}
        args=dict(deadline=5,expected_uuid='GPU-test',groups_absent=True,clock=lambda:1)
        self.assertTrue(check_cleanup(**args,query=empty)['gpu_cleanup_verified'])
        def timeout(*_): raise subprocess.TimeoutExpired('nvidia-smi',2)
        for query in (timeout,lambda *_:{'remaining_process_count':1}):
            self.assertFalse(check_cleanup(**args,query=query)['gpu_cleanup_verified'])
        self.assertFalse(check_cleanup(**{**args,'groups_absent':False},query=empty)['gpu_cleanup_verified'])
        self.assertFalse(check_cleanup(**{**args,'deadline':1},query=empty)['gpu_cleanup_verified'])
        times=iter([1,6,6])
        self.assertFalse(check_cleanup(**{**args,'clock':lambda:next(times)},query=empty)['gpu_cleanup_verified'])

    def test_gpu_identity_failure_never_means_empty(self):
        with patch('certification.phase4_v12.live_probes.require_live_authority'), \
             patch('certification.phase4_v12.cleanup_probe.subprocess.run',return_value=SimpleResult('GPU-wrong, RTX PRO 6000')):
            with self.assertRaisesRegex(ValueError,'identity'):
                inspect_gpu(__import__('time').monotonic()+4,'GPU-test')

    def test_cleanup_query_failures_and_empty_inventory(self):
        for output,verified in [('',True),('GPU-test, 123',False),('N/A',False)]:
            with self.subTest(output=output), \
                 patch('certification.phase4_v12.live_probes.require_live_authority'), \
                 patch('certification.phase4_v12.cleanup_probe.subprocess.run',
                       side_effect=[SimpleResult('GPU-test, RTX PRO 6000'),SimpleResult(output)]):
                receipt=check_cleanup(deadline=__import__('time').monotonic()+4,
                    expected_uuid='GPU-test',groups_absent=True)
                self.assertEqual(receipt['gpu_cleanup_verified'],verified)

    def test_monitor_death_still_checks_cleanup_and_cannot_pass(self):
        from certification.phase4_v12.pilot import run
        def independent(**kwargs):
            return check_cleanup(**kwargs,query=lambda *_:{'gpu_uuid':'GPU-test','remaining_process_count':0})
        with tempfile.TemporaryDirectory() as temp, \
             patch('certification.phase4_v12.pilot.require_live_authority'), \
             patch('certification.phase4_v12.cleanup_probe.check_cleanup',side_effect=independent) as checked:
            # Child authority remains closed, so the monitor dies without GPU access.
            report,result=run(Path(temp)/'out',Path(temp),mode='live',seconds=27540,reserve=600,
                              game_python=sys.executable,model_python=sys.executable+'-unused')
            checked.assert_called_once()
            self.assertTrue(report['cleanup_verified'])
            self.assertTrue(report['independent_gpu_cleanup_verified'])
            self.assertFalse(result['passed'])
            receipt=json.loads((Path(temp)/'out/control/gpu-cleanup.json').read_text())
            self.assertFalse(receipt['monitoring_coverage_restored'])


class SimpleResult:
    def __init__(self,stdout): self.stdout=stdout
