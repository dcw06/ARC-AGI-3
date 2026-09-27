"""Evidence comprehension v1: call order, admission control and interrupted-gate reporting (review of r2)."""
import json
from pathlib import Path
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
            clock += S.PER_CALL_BOUND_SECONDS  # cancelled at its timeout: no score row
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
        for elapsed in (0, 1000, S.ADMISSION_CUTOFF_SECONDS - S.PER_CALL_BOUND_SECONDS,
                        S.ADMISSION_CUTOFF_SECONDS - S.PER_CALL_BOUND_SECONDS + 0.001, S.ADMISSION_CUTOFF_SECONDS):
            if S.admit(elapsed):
                self.assertLessEqual(elapsed + S.PER_CALL_BOUND_SECONDS, S.INTERNAL_SECONDS - S.CLEANUP_RESERVE_SECONDS)
        self.assertFalse(S.admit(S.ADMISSION_CUTOFF_SECONDS - S.PER_CALL_BOUND_SECONDS + 0.001))

    def test_invalid_timing_values_are_rejected(self):
        # Review of r3: negative, non-finite and boolean values, and a negative timeout admitting past the cutoff.
        inf, nan = float('inf'), float('nan')
        for args in ((-1,), (-inf,), (inf,), (nan,), (True,), (False,), ('10',), (None,),
                     (0, S.ADMISSION_CUTOFF_SECONDS, -1), (S.ADMISSION_CUTOFF_SECONDS + 100, S.ADMISSION_CUTOFF_SECONDS, -200),
                     (0, S.ADMISSION_CUTOFF_SECONDS, 0), (0, S.ADMISSION_CUTOFF_SECONDS, inf), (0, S.ADMISSION_CUTOFF_SECONDS, True),
                     (0, -inf), (0, 0), (0, S.INTERNAL_SECONDS), (0, nan)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                S.admit(*args)
        for args in ((S.ADMISSION_CUTOFF_SECONDS, -5), (0, 0)):
            with self.subTest(settings=args), self.assertRaises(ValueError):
                S.Admission(*args)
        self.assertTrue(S.admit(0.0))
        self.assertFalse(S.admit(float(S.ADMISSION_CUTOFF_SECONDS)))

    def test_a_cancelled_call_stops_admission_with_its_cause(self):
        a = S.Admission()
        a.record('answered')
        a.record('canceled')
        self.assertFalse(a.may_start(0))
        self.assertEqual(a.stopped, 'canceled')

    def test_consecutive_timeouts_stop_admission(self):
        a = S.Admission()
        a.record('timed_out')
        self.assertTrue(a.may_start(0))
        a.record('answered')
        a.record('timed_out')
        a.record('timed_out')
        self.assertFalse(a.may_start(0))
        self.assertEqual(a.stopped, 'consecutive_timeouts')


class CancelledInFlight(unittest.TestCase):
    """Review of adf3b9d follow-up: a call abandoned because of cancellation is attributed to the cancellation."""

    def run_with(self, raise_after_cancel):
        import tempfile
        from research.evidence_comprehension_v1.runner import run

        class Service:
            def __init__(self, cancel):
                self.cancel, self.calls = cancel, 0

            def complete(self, request, deadline=None):
                self.calls += 1
                if self.calls == 3:
                    if raise_after_cancel:
                        self.cancel.write_text('{}')  # the supervisor cancels while this call is in flight
                    raise RuntimeError('TimeoutError: bridge admission closed')
                return {'content': '{"answer":[1]}', 'tokenizer_prompt_tokens': 10, 'server_prompt_tokens': 10,
                        'server_completion_tokens': 3, 'finish_reason': 'stop', 'cache_check': None, 'host_timing': None}
        with tempfile.TemporaryDirectory() as folder:
            cancel = Path(folder) / 'cancel.json'
            index = run(Path(folder) / 'run', Service(cancel), started=__import__('time').monotonic(), kind='test',
                        cutoff_seconds=3000, bound_seconds=10, cancel=cancel)
            third = json.loads((Path(folder) / 'run/calls/00002.json').read_bytes())
        return index, third

    def test_in_flight_call_during_cancellation_is_recorded_as_canceled(self):
        index, third = self.run_with(True)
        self.assertEqual((third['status'], index['stop_reason'], index['status']), ('canceled', 'canceled', 'incomplete'))

    def test_a_real_transport_failure_is_still_a_transport_failure(self):
        index, third = self.run_with(False)
        self.assertEqual((third['status'], index['stop_reason']), ('transport_failure', 'transport_failure'))


class DeadlineExpired(unittest.TestCase):
    """Series-2 run 4: a call whose own deadline passed before it could be sent is attributed to the deadline."""

    def run_with(self, jump_seconds, cancel_too=False):
        import tempfile
        from research.evidence_comprehension_v1.runner import run
        now = [100.0]

        class Service:
            def __init__(self, cancel):
                self.cancel, self.calls = cancel, 0

            def complete(self, request, deadline=None):
                self.calls += 1
                now[0] += 0.01
                if self.calls == 3:
                    now[0] += jump_seconds  # e.g. a VM pause: the monotonic clock catches up past the bound
                    if cancel_too:
                        self.cancel.write_text('{}')
                    raise TimeoutError('bridge admission closed')
                return {'content': '{"answer":[1]}', 'tokenizer_prompt_tokens': 10, 'server_prompt_tokens': 10,
                        'server_completion_tokens': 3, 'finish_reason': 'stop', 'cache_check': None, 'host_timing': None}
        with tempfile.TemporaryDirectory() as folder:
            cancel = Path(folder) / 'cancel.json'
            index = run(Path(folder) / 'run', Service(cancel), started=100.0, kind='test', cutoff_seconds=3000,
                        bound_seconds=10, cancel=cancel, clock=lambda: now[0])
            third = json.loads((Path(folder) / 'run/calls/00002.json').read_bytes())
        return index, third

    def test_failure_after_the_call_bound_is_deadline_expired(self):
        index, third = self.run_with(12.0)
        self.assertEqual((third['status'], index['stop_reason']), ('deadline_expired', 'deadline_expired'))
        self.assertGreaterEqual(third['returned_at'] - third['started_at'], 10)

    def test_failure_within_the_bound_stays_a_transport_failure(self):
        index, third = self.run_with(2.0)
        self.assertEqual((third['status'], index['stop_reason']), ('transport_failure', 'transport_failure'))

    def test_cancellation_takes_precedence(self):
        index, third = self.run_with(12.0, cancel_too=True)
        self.assertEqual((third['status'], index['stop_reason']), ('canceled', 'canceled'))

    def test_evaluator_rejects_a_deadline_expired_label_that_is_not_true(self):
        from research.action_effect_history_v1.service import request_hash
        from research.evidence_comprehension_v1.probes import build_request, load_frozen
        from scripts.evaluate_evidence_comprehension_v1 import call_errors, frozen_timing
        frozen, sha = load_frozen()
        contexts = {c['context_id']: c for c in frozen['contexts']}
        probes = {p['probe_id']: p for p in frozen['probes']}
        phase, pass_id, pid = S.call_order(frozen['probes'])[0]
        timing = frozen_timing('rehearsal', 480)
        run = {'probe_set_sha256': sha, 'cutoff_seconds': timing['cutoff'], 'bound_seconds': timing['bound'],
               'scheduled_calls': 2 * len(frozen['probes'])}
        base = {'index': 0, 'phase': phase, 'pass_id': pass_id, 'probe_id': pid, 'status': 'deadline_expired',
                'request_sha256': request_hash(build_request(contexts[probes[pid]['context_id']], probes[pid]))}
        truthful = dict(base, started_at=5.0, returned_at=5.0 + timing['bound'] + 0.1)
        false = dict(base, started_at=5.0, returned_at=6.0)
        self.assertEqual(call_errors({**run, 'calls': [truthful]}, frozen, sha, [], timing)[0], [])
        errors = call_errors({**run, 'calls': [false]}, frozen, sha, [], timing)[0]
        self.assertTrue(any('deadline_expired before its per-call bound' in e for e in errors))


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
