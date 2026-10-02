"""Accelerated full-duration monitoring with real bounded chunk persistence/replay."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from certification.phase4_integrated_v2.telemetry import TelemetryWriter, read_telemetry, MAX_SAMPLES
from certification.phase4_integrated_v2.evidence import LIMITS
from research.stagnation_supervision_v1.closed_loop import monitor

class Capacity(unittest.TestCase):
    def test_full_duration_both_sessions_and_evidence_size(self):
        for duration in (5100, 4500):
            with self.subTest(duration=duration), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); (root / 'control').mkdir(); stop = root / 'control/stop.json'
                now = [0.0]
                def sleep(seconds):
                    self.assertEqual(seconds, .5)
                    now[0] += seconds
                    if now[0] >= duration - .5:
                        stop.touch()
                class Probes:
                    def __init__(self, *args): pass
                    def bind(self):
                        from research.stagnation_supervision_v1.closed_loop.resources import RehearsalProbes
                        self.fixture = RehearsalProbes.FIXTURE
                        from certification.phase4_integrated_v2.monitor import VRAM
                        return {'gpu_uuid': self.fixture['uuid'], 'max_used_vram_bytes': VRAM,
                                'initial_telemetry': self.fixture}
                    def sample(self, uuid): return self.fixture
                    def rss(self, pid): return int(now[0] * 1000)
                    def scratch_bytes(self): return int(now[0] * 777)
                    def gpu_pids(self): return []
                # The virtual clock exercises every sampler iteration. Batch durable
                # checkpoints to avoid simulating 5100 seconds of disk timing; actual
                # async writer/backlog and durability are tested by connected rehearsals.
                class Writer:
                    def __init__(self, store, ready, **kwargs):
                        self.writer = TelemetryWriter(store); self.samples = []
                    def health(self): return {}
                    def submit(self, record, meta):
                        self.samples.append(record)
                        if len(self.samples) % 1024 == 0:
                            self.writer.save({**meta, 'samples': self.samples})
                    def finish(self, meta, deadline):
                        self.writer.save({**meta, 'samples': self.samples})
                with patch.object(monitor, 'probes_for', return_value=Probes), patch.object(monitor, 'AsyncTelemetry', Writer):
                    result = monitor.observe(1, root, root, started=0, deadline=duration,
                        stop=stop, nonce='capacity', mode='rehearsal', clock=lambda: now[0], sleep=sleep)
                self.assertEqual(result['status'], 'monitor_completed', result)
                retained = read_telemetry(root / 'monitor')
                self.assertEqual(len(retained['samples']), duration * 2)
                self.assertEqual(retained['samples'][-1]['elapsed_seconds'], duration - .5)
                self.assertLess(len(retained['samples']) + 1, MAX_SAMPLES)
                self.assertEqual(retained['sampling_interval_seconds'], .5)
                size = sum(p.stat().st_size for p in (root / 'monitor').glob('*') if p.is_file())
                self.assertLess(size, LIMITS['monitor'] - 4096)
                # Conservative uncompressed/base64 allocation including an atomic
                # replacement chunk and two manifests, even if gzip saves nothing.
                max_sample_bytes = max(len(json.dumps(x, sort_keys=True).encode()) + 2 for x in retained['samples'])
                ceiling = ((duration * 2 + 1 + 1024) * max_sample_bytes * 4 // 3) + 262144
                self.assertLess(ceiling, LIMITS['monitor'] - 4096)

    def test_nonfrozen_cadence_and_excess_duration_rejected(self):
        for interval, duration in ((.25, 5100), (.5, 5101)):
            with self.assertRaises(ValueError):
                monitor.observe(1, '.', '.', started=0, deadline=duration, stop='absent', nonce='x',
                                interval=interval, mode='rehearsal')
