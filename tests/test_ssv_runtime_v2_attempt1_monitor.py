"""Session-1 attempt 1 (ssv1rt2-s1-c5ebca7f): the monitor's first RSS probe took 5.45 s on the target and the frozen
1-s sampling-gap limit stopped the monitor before readiness. Virtual-clock regressions (CPU only; no GPU or provider)."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from certification.phase4_integrated_v2.monitor import VRAM
from certification.phase4_integrated_v2.telemetry import TelemetryWriter

FIXTURE = {'uuid': 'GPU-REHEARSAL-INJECTED', 'name': 'RTX PRO 6000 (injected rehearsal)', 'total_bytes': 96 * 1024**3,
           'used_bytes': 1}


def exercise(monitor, slow_calls, samples=6):
    """Run `observe` on a virtual clock; the RSS probe calls numbered in `slow_calls` (1-based) cost 5.45 s."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'control').mkdir()
        stop = root / 'control/stop.json'
        now, calls = [100.0], []

        def sleep(seconds):
            now[0] += seconds
            if len(calls) >= samples:
                stop.touch()

        class Probes:
            def __init__(self, *args):
                pass

            def bind(self):
                return {'gpu_uuid': FIXTURE['uuid'], 'max_used_vram_bytes': VRAM, 'initial_telemetry': FIXTURE}

            def sample(self, uuid):
                now[0] += .012
                return dict(FIXTURE)

            def rss(self, pid):
                calls.append(pid)
                now[0] += 5.45 if len(calls) in slow_calls else .03
                return 15343616

            def scratch_bytes(self):
                return 0

            def gpu_pids(self):
                return []

        class Writer:
            def __init__(self, store, ready, **kwargs):
                self.writer, self.samples = TelemetryWriter(store), []

            def health(self):
                return {}

            def submit(self, record, meta):
                self.samples.append(record)

            def finish(self, meta, deadline):
                self.writer.save({**meta, 'samples': self.samples})

        with patch.object(monitor, 'probes_for', return_value=Probes), patch.object(monitor, 'AsyncTelemetry', Writer):
            result = monitor.observe(7, root, root, started=0, deadline=4000, stop=stop, nonce='attempt1',
                                     mode='rehearsal', clock=lambda: now[0], sleep=sleep)
        failure = (root / 'monitor/failure.json').read_text() if (root / 'monitor/failure.json').exists() else ''
        return result, failure


class FirstProbeCost(unittest.TestCase):
    def test_pre_fix_monitor_reproduces_the_target_failure(self):
        from research.stagnation_supervision_v1.closed_loop import monitor as frozen  # the r7 monitor's logic, unchanged
        result, failure = exercise(frozen, slow_calls={1})
        self.assertEqual(result['status'], 'failed')
        self.assertIn('monitor limit: sampling_gap_seconds', result['error'])
        self.assertIn('sampling_gap_seconds', failure)

    def test_warm_up_absorbs_a_one_time_first_probe_cost(self):
        from research.stagnation_supervision_runtime_v2 import monitor
        result, failure = exercise(monitor, slow_calls={1})
        self.assertEqual(result['status'], 'monitor_completed', failure)
        self.assertEqual(failure, '')

    def test_a_slow_sampled_probe_still_fails_closed(self):
        from research.stagnation_supervision_runtime_v2 import monitor
        result, failure = exercise(monitor, slow_calls={3})  # call 1 is the warm-up; call 3 is the second sample
        self.assertEqual(result['status'], 'failed')
        self.assertIn('monitor limit: sampling_gap_seconds', result['error'])

    def test_the_monitor_clock_starts_after_the_warm_up(self):
        import inspect
        from research.stagnation_supervision_runtime_v2 import monitor
        source = inspect.getsource(monitor.observe)
        self.assertLess(source.index('probes.rss(worker_pid)'), source.index("state['monitor_started_seconds']"))


if __name__ == '__main__':
    unittest.main()
