"""Evidence-linked memory v1 (Track 2): the GPU-disabled Stage 1 run package (platform-independent checks).

The connected rehearsals (launcher -> supervisor -> worker -> host -> fake server -> runner -> evaluator) are in
tests/test_evidence_memory_v1_run_connected.py, derived from WS3's; they need POSIX (fcntl, process groups, Unix
sockets) and are skipped elsewhere. This file checks the derivation, the live refusal, the allow-list, the call
order and admission, and an in-process dry rehearsal of scoring and analysis through the fake server's answers.
"""
import json
import time
from pathlib import Path
import unittest

from research.evidence_memory_v1 import derive_run as D
from research.evidence_memory_v1.run import authority as A, probes as PR, schedule as S, score as SC
from research.evidence_memory_v1.run.evaluate import score_call

ROOT = Path(__file__).resolve().parents[1]
FROZEN, DIGEST = PR.load_frozen()
OUTCOME_WORDS = ('correct', 'accuracy', 'contrast', 'primary_endpoint', 'forgetting', 'abstention', 'abstained',
                 'unsupported', 'stability', 'conclusions', 'memory_preserves', 'truth')


def assert_no_outcomes(case, value):
    """No outcome-bearing key or value: technical counts only."""
    text = json.dumps(value).lower()
    for word in OUTCOME_WORDS:
        case.assertNotIn(word, text)


def keyed_passes(frozen=FROZEN):
    """Every scheduled probe answered with its key (a technically valid session)."""
    probes = {p['probe_id']: p for p in frozen['probes']}
    return {block['pass']: {i: SC.score(probes[i], json.dumps(probes[i]['key'])) for i in block['probe_ids']}
            for block in frozen['schedule']}


class Derivation(unittest.TestCase):
    def test_no_drift_and_every_file_names_its_reviewed_source(self):
        self.assertEqual(D.stale(), [])
        for target, (source, _) in D.DERIVED.items():
            self.assertTrue((ROOT / source).is_file(), source)
            text = (ROOT / target).read_text(encoding='utf-8')
            self.assertTrue(text.startswith(D.BANNER.format(source=source)), target)

    def test_a_missing_substitution_is_refused(self):
        source, subs = D.DERIVED['research/evidence_memory_v1/run/worker.py']
        D.DERIVED['research/evidence_memory_v1/run/worker.py'] = (source, subs + (('no such text', 'x', 1),))
        try:
            with self.assertRaises(ValueError):
                D.derive_one('research/evidence_memory_v1/run/worker.py')
        finally:
            D.DERIVED['research/evidence_memory_v1/run/worker.py'] = (source, subs)


class GpuDisabled(unittest.TestCase):
    def test_live_is_refused_before_any_approval_is_read(self):
        self.assertFalse(A.LIVE_ENABLED)
        with self.assertRaises(PermissionError) as raised:
            A.require(ROOT)
        self.assertIn('no approved live run', str(raised.exception.__cause__))
        self.assertEqual((A.LIMITS['automatic_retries'], A.LIMITS['maximum_attempts'], A.LIMITS['authorized_seconds'],
                          A.LIMITS['internal_seconds']), (0, 1, 3600, 3300))
        self.assertEqual(FROZEN['case_source'], 'development_stand_in')  # never a live case set

    def test_the_call_ceiling_covers_the_session(self):
        calls = sum(len(b['probe_ids']) for b in FROZEN['schedule'])
        self.assertEqual(calls, D.SESSION_A_CALLS)
        self.assertGreaterEqual(A.LIMITS['maximum_questionnaire_calls'], calls)


class OrderAndAdmission(unittest.TestCase):
    def test_pass_one_then_the_repeat_and_truncation_keeps_whole_groups(self):
        order = S.call_order(FROZEN)
        self.assertEqual([p for p, _, _ in order], sorted((p for p, _, _ in order), key=S.PHASES.index))
        probes = {p['probe_id']: p for p in FROZEN['probes']}
        groups = [(probes[i]['family'], probes[i]['group']) for _, pass_id, i in order if pass_id == 'pass_1']
        sizes = {}
        for g in groups:
            sizes[g] = sizes.get(g, 0) + 1
        for cut in range(0, len(groups), 97):  # wherever admission stops, at most one group is partial
            seen = {}
            for g in groups[:cut]:
                seen[g] = seen.get(g, 0) + 1
            self.assertLessEqual(sum(1 for g, n in seen.items() if n < sizes[g]), 1)

    def test_no_admitted_call_reaches_the_cleanup_reserve(self):
        for elapsed in (0, S.ADMISSION_CUTOFF_SECONDS - S.PER_CALL_BOUND_SECONDS,
                        S.ADMISSION_CUTOFF_SECONDS - S.PER_CALL_BOUND_SECONDS + 0.001):
            if S.admit(elapsed):
                self.assertLessEqual(elapsed + S.PER_CALL_BOUND_SECONDS, S.INTERNAL_SECONDS - S.CLEANUP_RESERVE_SECONDS)
        self.assertEqual(S.INTERNAL_SECONDS - S.CLEANUP_RESERVE_SECONDS, S.ADMISSION_CUTOFF_SECONDS)


class DryRehearsal(unittest.TestCase):
    """The fake server's scripted answers, scored and analysed exactly as the evaluator does (no transport)."""

    @classmethod
    def setUpClass(cls):
        from research.evidence_memory_v1.run.fake_server import TRUNCATED, ScriptedAnswers
        answers = ScriptedAnswers()
        contexts = {c['context_id']: c for c in FROZEN['contexts']}
        probes = {p['probe_id']: p for p in FROZEN['probes']}
        cls.passes = {'pass_1': {}, 'pass_2': {}}
        for _, pass_id, probe_id in S.call_order(FROZEN):
            probe = probes[probe_id]
            content = answers(PR.build_request(contexts[probe['context_id']], probe))
            call = ({'finish_reason': 'length', 'response': content[len(TRUNCATED):]} if content.startswith(TRUNCATED)
                    else {'finish_reason': 'stop', 'response': content})
            cls.passes[pass_id][probe_id] = score_call(probe, call)
        cls.answers = answers

    def test_canary_and_unknown_requests(self):
        self.assertIn('action', json.loads(self.answers({'messages': [{'role': 'user', 'content': 'canary'}]})))
        self.assertIn('not_in_probe_set', self.answers({'messages': [{'role': 'user', 'content': 'Evidence:\nx'}]}))

    def test_the_session_report_is_technical_only(self):
        result = SC.analyze(FROZEN['probes'], self.passes)
        self.assertEqual(result['completeness'], {'withheld': 'complete'})
        self.assertEqual(result['answers']['pass_1']['answered'], len(FROZEN['schedule'][0]['probe_ids']))
        self.assertLess(result['answers']['pass_1']['schema_valid'], result['answers']['pass_1']['answered'])
        # The scripted server answers about 4% invalidly: above the 2% per-arm rule, so the session is not valid.
        self.assertFalse(result['invalid_rule_met'])
        self.assertEqual(result['verdict'], 'session_technically_invalid_outputs')
        assert_no_outcomes(self, result)

    def test_a_valid_session_and_a_changed_response(self):
        passes = keyed_passes()
        result = SC.analyze(FROZEN['probes'], passes)
        self.assertEqual((result['invalid_rule_met'], result['verdict']), (True, 'session_technically_valid'))
        assert_no_outcomes(self, result)
        probe_id = FROZEN['schedule'][0]['probe_ids'][0]
        passes['pass_1'][probe_id] = SC.score({p['probe_id']: p for p in FROZEN['probes']}[probe_id], '{"values":["x"]}')
        changed = SC.analyze(FROZEN['probes'], passes)
        self.assertNotEqual(changed['answers']['pass_1']['responses_sha256'],
                            result['answers']['pass_1']['responses_sha256'])

    def test_the_invalid_output_rule_applies_to_the_repeat_pass(self):
        """Pass 1 fully valid, every repeat answer invalid: the session must not be technically valid."""
        passes = keyed_passes()
        probes = {p['probe_id']: p for p in FROZEN['probes']}
        for probe_id in passes['pass_2']:
            passes['pass_2'][probe_id] = SC.score(probes[probe_id], 'not json')
        result = SC.analyze(FROZEN['probes'], passes)
        self.assertEqual(result['completeness'], {'withheld': 'complete'})  # fully answered
        self.assertTrue(result['invalid_by_pass']['pass_1']['rule_met'])
        repeat = result['invalid_by_pass']['pass_2']
        self.assertFalse(repeat['rule_met'])
        for arm, row in repeat['by_arm'].items():
            self.assertEqual((row['answered'], row['invalid'], row['invalid_rate']), (row['scheduled'], row['scheduled'], 1.0))
        self.assertEqual(sum(r['scheduled'] for r in repeat['by_arm'].values()), len(FROZEN['schedule'][1]['probe_ids']))
        self.assertEqual(result['verdict'], 'session_technically_invalid_outputs')
        # A single invalid repeat answer in an arm stays within 2% only if that arm has at least 50 repeat answers.
        one = keyed_passes()
        first = FROZEN['schedule'][1]['probe_ids'][0]
        one['pass_2'][first] = SC.score(probes[first], 'not json')
        arm = probes[first]['arm']
        row = SC.analyze(FROZEN['probes'], one)['invalid_by_pass']['pass_2']['by_arm'][arm]
        self.assertEqual(row['rule_met'], 1 <= SC.INVALID_RATE_MAX * row['answered'])

    def test_a_missing_answer_makes_the_session_incomplete(self):
        passes = {k: dict(v) for k, v in self.passes.items()}
        passes['pass_2'].pop(next(iter(passes['pass_2'])))
        result = SC.analyze(FROZEN['probes'], passes)
        self.assertEqual((result['completeness']['withheld'], result['verdict']), ('incomplete', 'incomplete'))
        assert_no_outcomes(self, result)

    def test_truncated_answers_are_invalid_never_parsed(self):
        probe = FROZEN['probes'][0]
        row = score_call(probe, {'finish_reason': 'length', 'response': json.dumps(probe['key'])})
        self.assertEqual((row['valid'], row['correct']), (False, False))


def _post(base_url, request, timeout):
    """(status, body) for one completion request; ('timeout', None) when no reply arrives in time. The connection
    is always closed, so a hung server-side request sees the client disconnect."""
    import http.client
    import socket
    from urllib.parse import urlparse
    url = urlparse(base_url)
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=timeout)
    try:
        body = json.dumps(request).encode()
        connection.request('POST', '/v1/chat/completions', body, {'Content-Type': 'application/json'})
        response = connection.getresponse()
        return response.status, response.read()
    except (socket.timeout, TimeoutError):
        return 'timeout', None
    finally:
        connection.close()


class FaultPlacement(unittest.TestCase):
    """Every rehearsal server fault is keyed to the HANG_AT-th questionnaire call after the canary. It must be reached
    by the Stage 1 schedule and fire there (review of cee5b3f: with v1's canary rule it never fired)."""

    @classmethod
    def setUpClass(cls):
        from research.action_effect_history_v1.service import canary_request
        contexts = {c['context_id']: c for c in FROZEN['contexts']}
        probes = {p['probe_id']: p for p in FROZEN['probes']}
        cls.order = S.call_order(FROZEN)
        cls.requests = [PR.build_request(contexts[probes[i]['context_id']], probes[i]) for _, _, i in cls.order]
        cls.canary = canary_request()

    def test_the_fault_call_is_inside_pass_one_of_the_schedule(self):
        from research.evidence_memory_v1.run.fake_server import HANG_AT
        self.assertLessEqual(HANG_AT, len(FROZEN['schedule'][0]['probe_ids']))
        self.assertEqual(self.order[HANG_AT - 1][0], 'withheld_pass_1')

    def test_the_canary_and_every_stage1_question_are_told_apart(self):
        from research.evidence_memory_v1.run import fake_vllm
        from research.evidence_memory_v1.run.fake_server import FakeVLLM
        server = FakeVLLM()
        try:
            self.assertTrue(server.is_canary(self.canary))
            self.assertFalse(any(server.is_canary(r) for r in self.requests))
            # The root cause: v1's rule calls a Stage 1 question the canary.
            self.assertTrue(fake_vllm.FakeVLLM.is_canary(server, self.requests[0]))
        finally:
            server.server.server_close()

    def test_each_server_fault_fires_at_its_call(self):
        from research.evidence_memory_v1.run.fake_server import ABORT_DELAY, HANG_AT, HANG_FAULTS, FakeVLLM
        for fault in ('http_error',) + HANG_FAULTS:
            with self.subTest(fault=fault):
                server = FakeVLLM(fault=fault).start()
                try:
                    self.assertEqual(_post(server.base_url, self.canary, 10)[0], 200)
                    for request in self.requests[:HANG_AT - 1]:
                        self.assertEqual(_post(server.base_url, request, 10)[0], 200)
                    self.assertEqual(server.completions, HANG_AT - 1)  # the canary is not counted
                    status, _ = _post(server.base_url, self.requests[HANG_AT - 1], 1.5)
                    self.assertEqual(server.completions, HANG_AT)
                    if fault == 'http_error':
                        self.assertEqual(status, 500)
                        continue
                    self.assertEqual(status, 'timeout')  # the HANG_AT-th call hangs
                    if fault == 'trickle_metrics':
                        self.assertTrue(server.trickling)
                    expected = ('disconnect_ignored' if fault == 'no_abort' else 'aborted', HANG_AT)
                    until = time.monotonic() + ABORT_DELAY.get(fault, 0) + 5
                    while expected not in server.log and time.monotonic() < until:
                        time.sleep(0.05)
                    self.assertIn(expected, server.log)
                finally:
                    server.close()


class RehearsalOnlyKnobs(unittest.TestCase):
    """The end-to-end pooled test (tests/test_evidence_memory_v1_run_final_e2e.py) needs a second session's frozen
    set and technically valid rehearsal sessions; both knobs are rehearsal-only."""

    def test_the_frozen_set_override_is_honoured_only_in_cpu_rehearsal(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {PR.REHEARSAL_FROZEN_ENV: str(PR.FROZEN_PATH), 'EM1S_REHEARSAL': '1',
                                          'CUDA_VISIBLE_DEVICES': ''}):
            self.assertEqual(PR.load_frozen(), (FROZEN, DIGEST))
        for env in ({'EM1S_REHEARSAL': '0', 'CUDA_VISIBLE_DEVICES': ''}, {'EM1S_REHEARSAL': '1', 'CUDA_VISIBLE_DEVICES': '0'}):
            with mock.patch.dict(os.environ, {PR.REHEARSAL_FROZEN_ENV: str(PR.FROZEN_PATH), **env}):
                with self.assertRaises(PermissionError):
                    PR.load_frozen()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(PR.REHEARSAL_FROZEN_ENV, None)
            self.assertEqual(PR.frozen_path(), PR.FROZEN_PATH)

    def test_clean_answers_reach_the_server_and_answer_every_question_with_its_key(self):
        import ast
        from research.evidence_memory_v1.run.fake_server import CLEAN_FAULT, FAULTS, FakeVLLM
        tree = ast.parse((ROOT / 'research/evidence_memory_v1/run/worker.py').read_text(encoding='utf-8'))
        host_faults = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                           and any(isinstance(t, ast.Name) and t.id == 'HOST_FAULTS' for t in n.targets))
        self.assertIn(CLEAN_FAULT, host_faults)
        self.assertIn(CLEAN_FAULT, FAULTS)
        server = FakeVLLM(fault=CLEAN_FAULT)
        try:
            contexts = {c['context_id']: c for c in FROZEN['contexts']}
            for probe in FROZEN['probes'][:300]:
                request = PR.build_request(contexts[probe['context_id']], probe)
                self.assertEqual(json.loads(server.answers(request)), probe['key'])
            self.assertEqual(server.fault, 'none')  # no server fault is injected
        finally:
            server.server.server_close()


class SlowFaultPlacement(unittest.TestCase):
    """The deadline rehearsal's slow faults are derived from the frozen schedule so the admission cutoff provably
    falls inside the chosen pass (review of e80e01a: a fixed 0.075 s put the pass-2 cutoff inside pass 1)."""

    def test_margins_hold_with_stated_bounds(self):
        from research.evidence_memory_v1.run import rehearsal_timing as RT
        m = RT.margins(FROZEN)
        self.assertEqual((m['pass_1_calls'], m['repeat_calls'], m['cutoff'], m['last_admissible_start']),
                         (2592, 304, 300, 290.0))
        self.assertTrue(all(m['holds'].values()), m)
        # pass-1 time < last admissible start < cutoff < pass-1 time + repeat time, with margins on both sides
        self.assertGreaterEqual(m['pass_2_fault']['low_side_margin'], RT.LOW_MARGIN_SECONDS)
        self.assertGreater(m['pass_2_fault']['high_side_margin'], 0)
        self.assertGreater(m['pass_1_fault']['high_side_margin'], 0)
        self.assertGreaterEqual(m['timeout_margin'], RT.TIMEOUT_MARGIN_SECONDS)

    def test_the_derived_worker_uses_the_derived_values_and_forwards_the_repeat_fault(self):
        import ast
        from research.evidence_memory_v1.run import fake_server, rehearsal_timing as RT
        tree = ast.parse((ROOT / 'research/evidence_memory_v1/run/worker.py').read_text(encoding='utf-8'))
        values = {t.id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                  for t in n.targets if isinstance(t, ast.Name) and t.id in ('SLOW_LATENCY', 'HOST_FAULTS')}
        self.assertEqual(values['SLOW_LATENCY'], RT.slow_latencies(FROZEN))
        self.assertIn(RT.REPEAT_FAULT, values['HOST_FAULTS'])  # worker -> host
        self.assertIn(RT.REPEAT_FAULT, fake_server.FAULTS)  # host -> fake server

    def test_the_repeat_fault_slows_only_repeat_calls(self):
        from research.evidence_memory_v1.run import rehearsal_timing as RT
        from research.evidence_memory_v1.run.fake_server import FakeVLLM
        latency = RT.slow_latencies(FROZEN)
        n1 = len(FROZEN['schedule'][0]['probe_ids'])
        for fault, expected in ((RT.REPEAT_FAULT, (0.0, 0.0, latency[RT.REPEAT_FAULT])),
                                ('slow_withheld_pass_1', (latency['slow_withheld_pass_1'],) * 3)):
            server = FakeVLLM(fault=RT.REPEAT_FAULT if fault == RT.REPEAT_FAULT else 'none',
                              latency_seconds=latency[fault])
            try:
                self.assertEqual((server.latency_for(1), server.latency_for(n1), server.latency_for(n1 + 1)), expected)
            finally:
                server.server.server_close()

    def test_simulated_admission_stops_inside_the_chosen_pass(self):
        """The reviewed admission rule over the frozen order, with the server's per-call latency, across startup and
        per-call overhead from zero to the stated bounds."""
        from research.evidence_memory_v1.run import rehearsal_timing as RT
        from research.evidence_memory_v1.run.fake_server import FakeVLLM
        latency = RT.slow_latencies(FROZEN)
        order = S.call_order(FROZEN)
        for fault, phase in (('slow_withheld_pass_1', 'withheld_pass_1'), (RT.REPEAT_FAULT, 'withheld_pass_2')):
            server = FakeVLLM(fault=RT.REPEAT_FAULT if fault == RT.REPEAT_FAULT else 'none',
                              latency_seconds=latency[fault])
            try:
                for startup in (0.0, RT.STARTUP_MAX_SECONDS):
                    for overhead in (0.0, 0.04, RT.OVERHEAD_MAX_SECONDS):
                        clock, reached = startup, None
                        for n, (call_phase, _, _) in enumerate(order, 1):
                            if not S.admit(clock, RT.cutoff(), RT.bound()):
                                break
                            reached = call_phase
                            clock += overhead + server.latency_for(n)
                        else:
                            self.fail('the whole schedule finished before the cutoff')
                        with self.subTest(fault=fault, startup=startup, overhead=overhead):
                            self.assertEqual(reached, phase)
            finally:
                server.server.server_close()


if __name__ == '__main__':
    unittest.main()
