"""Evidence comprehension v1: call order, admission control and interrupted-gate reporting (review of r2)."""
import json
import unittest

from research.evidence_comprehension_v1 import schedule as S
from research.evidence_comprehension_v1.probes import GATE_CONDITION
from research.evidence_comprehension_v1.score import analyze, score
from scripts import build_evidence_comprehension_v1 as B

PROBES = json.loads(B.OUTPUT.read_bytes())['probes']
BY_ID = {p['probe_id']: p for p in PROBES}


def simulate(call_seconds, *, startup=403, timeouts=()):
    """Run the schedule against a fake clock. Returns (passes, admission, calls started, clock at end)."""
    admission = S.Admission()
    passes, clock, started = {'pass_1': {}, 'pass_2': {}}, float(startup), 0
    for n, (_, pass_id, probe_id) in enumerate(S.call_order(PROBES)):
        if not admission.may_start(clock):
            break
        started += 1
        if n in timeouts:
            clock += S.PER_CALL_TIMEOUT_SECONDS  # cancelled at its timeout: no score row
            admission.record('timed_out')
            continue
        clock += call_seconds
        probe = BY_ID[probe_id]
        passes[pass_id][probe_id] = score(probe, json.dumps({'answer': probe['key']}))
        admission.record('answered')
    return passes, admission, started, clock


class Order(unittest.TestCase):
    def test_gate_passes_come_first_and_pass_two_is_reversed(self):
        order = S.call_order(PROBES)
        gate = [p['probe_id'] for p in PROBES if p['condition'] == GATE_CONDITION]
        self.assertEqual(len(order), 2 * len(PROBES))
        self.assertEqual([i for ph, _, i in order if ph == 'gate_pass_1'], gate)
        self.assertEqual([i for ph, _, i in order if ph == 'gate_pass_2'], gate[::-1])
        phases = [ph for ph, _, _ in order]
        self.assertEqual(phases, sorted(phases, key=S.PHASES.index))


class Admission(unittest.TestCase):
    def test_no_admitted_call_can_reach_the_cleanup_reserve(self):
        for elapsed in (0, 1000, S.ADMISSION_CUTOFF_SECONDS - S.PER_CALL_TIMEOUT_SECONDS,
                        S.ADMISSION_CUTOFF_SECONDS - S.PER_CALL_TIMEOUT_SECONDS + 0.001, S.ADMISSION_CUTOFF_SECONDS):
            if S.admit(elapsed):
                self.assertLessEqual(elapsed + S.PER_CALL_TIMEOUT_SECONDS, S.INTERNAL_SECONDS - S.CLEANUP_RESERVE_SECONDS)
        self.assertFalse(S.admit(S.ADMISSION_CUTOFF_SECONDS - S.PER_CALL_TIMEOUT_SECONDS + 0.001))

    def test_consecutive_timeouts_stop_admission(self):
        a = S.Admission()
        a.record('timed_out')
        self.assertTrue(a.may_start(0))
        a.record('answered')
        a.record('timed_out')
        a.record('timed_out')
        self.assertFalse(a.may_start(0))
        self.assertEqual(a.stopped, 'consecutive_timeouts')


class InterruptedGate(unittest.TestCase):
    """Deadline interruption during each gate pass, with timing estimates wrong by large factors."""

    def assert_incomplete_and_protected(self, passes, admission, clock):
        report = analyze(PROBES, {k: v for k, v in passes.items()})
        self.assertEqual(report['gate_status'], 'incomplete')
        self.assertNotIn('criterion_met', report['gate'].values())
        self.assertEqual(admission.stopped, 'admission_cutoff')
        self.assertLessEqual(clock, S.ADMISSION_CUTOFF_SECONDS)  # the cleanup reserve is untouched

    def test_interruption_during_gate_pass_one(self):
        # 8 s per call instead of ~1 s: time runs out partway through gate pass 1.
        passes, admission, started, clock = simulate(8.0)
        gate_n = sum(p['condition'] == GATE_CONDITION for p in PROBES)
        self.assertLess(started, gate_n)
        self.assertEqual(passes['pass_2'], {})
        self.assert_incomplete_and_protected(passes, admission, clock)

    def test_interruption_during_gate_pass_two(self):
        # 3.5 s per call: gate pass 1 completes, pass 2 is cut.
        passes, admission, started, clock = simulate(3.5)
        gate_n = sum(p['condition'] == GATE_CONDITION for p in PROBES)
        self.assertTrue(gate_n < started < 2 * gate_n)
        self.assertEqual(len(passes['pass_1']), gate_n)
        self.assert_incomplete_and_protected(passes, admission, clock)

    def test_slow_startup_interrupts_the_gate(self):
        passes, admission, _, clock = simulate(1.0, startup=2600)
        self.assert_incomplete_and_protected(passes, admission, clock)

    def test_timeouts_leave_missing_answers_never_scored(self):
        passes, admission, _, _ = simulate(0.5, timeouts=(5, 9))
        report = analyze(PROBES, passes)
        self.assertEqual(report['gate_status'], 'incomplete')
        order = S.call_order(PROBES)
        for n in (5, 9):
            _, pass_id, probe_id = order[n]
            self.assertNotIn(probe_id, passes[pass_id])

    def test_fast_run_completes_the_gate(self):
        passes, admission, started, clock = simulate(0.5)
        report = analyze(PROBES, passes)
        self.assertEqual(report['gate_status'], 'complete')
        self.assertEqual(set(report['gate'].values()), {'criterion_met'})
        self.assertIsNone(admission.stopped)
        self.assertEqual(started, 2 * len(PROBES))


if __name__ == '__main__':
    unittest.main()
