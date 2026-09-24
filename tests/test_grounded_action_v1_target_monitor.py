"""Stage B monitor readiness and bounded failure receipts, without GPU use."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from certification.phase4_integrated_v2.monitor import VRAM
from research.grounded_action_v1.target_monitor import observe


class FakeProbes:
    def __init__(self, _pid, _scratch):
        self.fixture = {'uuid': 'GPU-INJECTED', 'name': 'RTX PRO 6000 fixture',
                        'used_bytes': 1, 'total_bytes': 96 * 1024**3}

    def bind(self):
        return {'gpu_uuid': self.fixture['uuid'], 'initial_telemetry': self.fixture,
                'max_used_vram_bytes': VRAM}

    def sample(self, _uuid):
        return self.fixture

    def rss(self, _pid):
        return 1

    def scratch_bytes(self):
        return 1


class TargetMonitorTests(unittest.TestCase):
    def test_ready_requires_durable_sample_and_clean_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            control = root / 'control'
            control.mkdir()
            results = []
            thread = threading.Thread(target=lambda: results.append(observe(
                123, root, root, started=time.monotonic(), deadline=time.monotonic() + 6,
                stop=control / 'stop.json', nonce='fixture',
                probes_factory=FakeProbes, interval=.05)))
            thread.start()
            try:
                until = time.monotonic() + 3
                while not (root / 'monitor/ready.json').exists() and time.monotonic() < until:
                    time.sleep(.01)
                self.assertTrue((root / 'monitor/ready.json').exists())
                ready = json.loads((root / 'monitor/ready.json').read_bytes())
                self.assertEqual(ready['scope'], 'stage_b_injected_review_monitor')
                self.assertTrue((root / 'monitor/telemetry.json').exists())
                (control / 'monitor-ready-ack.json').write_text('{}')
                (control / 'stop.json').write_text('{}')
            finally:
                thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(results[0]['status'], 'injected_monitor_completed')

    def test_rejected_sample_retains_failure(self):
        class BadProbes(FakeProbes):
            def sample(self, _uuid):
                raise ValueError('rejected fixture sample')

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = observe(123, root, root, started=time.monotonic(),
                             deadline=time.monotonic() + 3, stop=root / 'stop',
                             nonce='fixture', probes_factory=BadProbes)
            self.assertEqual(result['status'], 'failed')
            receipt = json.loads((root / 'monitor/failure.json').read_bytes())
            self.assertIn('rejected fixture sample', receipt['error'])
            self.assertFalse((root / 'monitor/ready.json').exists())


if __name__ == '__main__':
    unittest.main()
