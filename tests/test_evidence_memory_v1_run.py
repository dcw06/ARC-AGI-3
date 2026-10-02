"""Evidence-linked memory v1 (Track 2): the GPU-disabled Stage 1 run package (platform-independent checks).

The connected rehearsals (launcher -> supervisor -> worker -> host -> fake server -> runner -> evaluator) are in
tests/test_evidence_memory_v1_run_connected.py, derived from WS3's; they need POSIX (fcntl, process groups, Unix
sockets) and are skipped elsewhere. This file checks the derivation, the live refusal, the allow-list, the call
order and admission, and an in-process dry rehearsal of scoring and analysis through the fake server's answers.
"""
import json
from pathlib import Path
import unittest

from research.evidence_memory_v1 import derive_run as D
from research.evidence_memory_v1.run import authority as A, probes as PR, schedule as S, score as SC
from research.evidence_memory_v1.run.evaluate import score_call

ROOT = Path(__file__).resolve().parents[1]
FROZEN, DIGEST = PR.load_frozen()


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

    def test_complete_run_gives_endpoint_contrasts_stability_and_retains_invalid_answers(self):
        result = SC.analyze(FROZEN['probes'], self.passes, resamples=500)
        self.assertEqual(result['completeness'], {'withheld': 'complete'})
        self.assertEqual(result['answers']['pass_1']['scored'], len(FROZEN['schedule'][0]['probe_ids']))
        self.assertLess(result['answers']['pass_1']['valid'], result['answers']['pass_1']['scored'])  # invalid kept
        analysis = result['analysis']
        self.assertEqual(set(analysis['primary_endpoint']), {'recent_raw', 'state_keyed_raw', 'memory'})
        self.assertEqual(set(analysis['contrasts']), {'memory_vs_recent_raw', 'memory_vs_state_keyed_raw',
                                                      'memory_vs_state_keyed_raw_evidence_in_both'})
        self.assertIsInstance(result['verdict'], str)
        s = result['stability']
        self.assertEqual(s['repeated_questions'], len(FROZEN['schedule'][1]['probe_ids']))
        self.assertLess(s['identical'], s['repeated_questions'])  # the scripted pass-2 divergence is detected

    def test_a_missing_repeat_answer_makes_the_run_incomplete(self):
        passes = {k: dict(v) for k, v in self.passes.items()}
        passes['pass_2'].pop(next(iter(passes['pass_2'])))
        result = SC.analyze(FROZEN['probes'], passes, resamples=200)
        self.assertEqual((result['completeness']['withheld'], result['verdict']), ('incomplete', 'incomplete'))
        self.assertNotIn('analysis', result)
        passes['pass_1'].pop(FROZEN['schedule'][0]['probe_ids'][-1])
        result = SC.analyze(FROZEN['probes'], passes, resamples=200)
        self.assertEqual(result['descriptive_complete_groups']['groups'], len({(p['family'], p['group'])
                                                                               for p in FROZEN['probes']}) - 1)

    def test_truncated_answers_are_invalid_never_parsed(self):
        probe = FROZEN['probes'][0]
        row = score_call(probe, {'finish_reason': 'length', 'response': json.dumps(probe['key'])})
        self.assertEqual((row['valid'], row['correct']), (False, False))


if __name__ == '__main__':
    unittest.main()
