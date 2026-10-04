"""progress_subgoal_v1 rehearsal slow faults: derived from the frozen schedule so the admission cutoff provably falls
inside the chosen pass (platform-independent arithmetic; after Track 2's b1b7681)."""
import ast
import json
from pathlib import Path
import unittest

from research.progress_subgoal_v1 import probes as P, rehearsal_timing as RT, schedule as S

ROOT = Path(__file__).resolve().parents[1]
FROZEN = json.loads(P.FROZEN_PATH.read_bytes())


class SlowFaultPlacement(unittest.TestCase):
    def test_margins_hold_with_stated_bounds(self):
        m = RT.margins(FROZEN)
        self.assertEqual((m['pass_1_calls'], m['pass_2_calls'], m['cutoff'], m['last_admissible_start']),
                         (2790, 2790, 300, 290.0))
        self.assertTrue(all(m['holds'].values()), m)
        self.assertGreaterEqual(m['pass_2_fault']['low_side_margin'], RT.LOW_MARGIN_SECONDS)
        self.assertGreater(m['pass_2_fault']['high_side_margin'], 0)
        self.assertGreater(m['pass_1_fault']['high_side_margin'], 0)
        self.assertGreaterEqual(m['timeout_margin'], RT.TIMEOUT_MARGIN_SECONDS)
        # the rehearsal timing constants are the derived worker's
        from research.progress_subgoal_v1 import worker
        self.assertEqual(worker.timing('rehearsal', 'none')[:2], (RT.CALL_TIMEOUT_SECONDS, RT.VERIFY_SECONDS))
        self.assertEqual((S.TEARDOWN_SECONDS, S.BRIDGE_MARGIN_SECONDS), (RT.TEARDOWN_SECONDS, RT.BRIDGE_MARGIN_SECONDS))

    def test_a_uniform_latency_cannot_place_the_pass_2_cutoff(self):
        """Why the pass-2 fault slows only pass 2: no uniform per-call latency satisfies both sides."""
        m = RT.margins(FROZEN)
        n = m['pass_1_calls']
        low_max = (m['last_admissible_start'] - RT.LOW_MARGIN_SECONDS - RT.STARTUP_MAX_SECONDS) / n - RT.OVERHEAD_MAX_SECONDS
        high_min = RT.HIGH_FACTOR * m['cutoff'] / (n + m['pass_2_calls'])
        self.assertLess(low_max, high_min)

    def test_the_derived_worker_uses_the_derived_values_and_forwards_the_pass_2_fault(self):
        from research.progress_subgoal_v1 import fake_server
        tree = ast.parse((ROOT / 'research/progress_subgoal_v1/worker.py').read_text(encoding='utf-8'))
        values = {t.id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                  for t in n.targets if isinstance(t, ast.Name) and t.id in ('SLOW_LATENCY', 'HOST_FAULTS')}
        self.assertEqual(values['SLOW_LATENCY'], RT.slow_latencies(FROZEN))
        self.assertIn(RT.REPEAT_FAULT, values['HOST_FAULTS'])  # worker -> host
        self.assertIn(RT.REPEAT_FAULT, fake_server.FAULTS)  # host -> fake server

    def servers(self):
        from research.progress_subgoal_v1.fake_server import FakeVLLM
        latency = RT.slow_latencies(FROZEN)
        for fault in ('slow_withheld_pass_1', RT.REPEAT_FAULT):
            server = FakeVLLM(fault=RT.REPEAT_FAULT if fault == RT.REPEAT_FAULT else 'none',
                              latency_seconds=latency[fault])
            try:
                yield fault, server
            finally:
                server.server.server_close()

    def test_the_pass_2_fault_slows_only_pass_2_calls(self):
        latency = RT.slow_latencies(FROZEN)
        n1 = RT.passes(FROZEN)[0]
        for fault, server in self.servers():
            expected = ((0.0, 0.0, latency[fault]) if fault == RT.REPEAT_FAULT else (latency[fault],) * 3)
            self.assertEqual((server.latency_for(1), server.latency_for(n1), server.latency_for(n1 + 1)), expected)
            server.completions = n1 + 1  # the property v1's handler reads after counting the call
            self.assertEqual(server.latency, latency[fault])

    def test_simulated_admission_stops_inside_the_chosen_pass(self):
        """The reviewed admission rule over the frozen order, with the server's per-call latency, for startup and
        per-call overhead from zero to the stated bounds."""
        order = S.call_order(FROZEN)
        chosen = {'slow_withheld_pass_1': 'withheld_pass_1', RT.REPEAT_FAULT: 'withheld_pass_2'}
        for fault, server in self.servers():
            for startup in (0.0, RT.STARTUP_MAX_SECONDS):
                for overhead in (0.0, 0.04, RT.OVERHEAD_MAX_SECONDS):
                    admission = S.Admission(RT.cutoff(), RT.bound())
                    clock, reached = startup, None
                    for n, (phase, _, _) in enumerate(order):
                        if not admission.may_start(clock):
                            reached = phase
                            break
                        clock += overhead + server.latency_for(n + 1)
                        admission.record('answered')
                    with self.subTest(fault=fault, startup=startup, overhead=overhead):
                        self.assertEqual(reached, chosen[fault])
                        self.assertEqual(admission.stopped, 'admission_cutoff')
                        self.assertLessEqual(clock, RT.cutoff())


if __name__ == '__main__':
    unittest.main()
