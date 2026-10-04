"""Evidence-linked memory v1 (Track 2): the registered two-session analysis refuses anything but both valid sessions.

Session B's frozen set is built here (development stand-in, like A's) with the pinned tokenizer. Answers are each
probe's key, with a deterministic 1% replaced by a schema-valid wrong answer, so both sessions are technically
valid and the analysis is not trivial.
"""
import copy
import hashlib
import json
import unittest

from research.evidence_memory_v1 import protocol as P, stage1 as ST, tokens as TK
from research.evidence_memory_v1.run import final as FI, probes as PR, score as SC
from research.evidence_memory_v1.run.fake_server import ScriptedAnswers

FOUND = TK.locate()
OUTCOME_WORDS = ('correct', 'accuracy', 'contrast', 'primary_endpoint', 'forgetting', 'abstention', 'unsupported',
                 'stability', 'conclusions', 'verdict', 'estimate')


def answers(frozen):
    probes = {p['probe_id']: p for p in frozen['probes']}
    out = {}
    for block in frozen['schedule']:
        out[block['pass']] = {}
        for probe_id in block['probe_ids']:
            probe = probes[probe_id]
            wrong = int(hashlib.sha256(probe_id.encode()).hexdigest(), 16) % 100 == 0
            answer = ScriptedAnswers.wrong(probe) if wrong else probe['key']
            out[block['pass']][probe_id] = SC.score(probe, json.dumps(answer))
    return out


def session(label, frozen):
    digest = FI.frozen_sha256(frozen)
    return {'label': label, 'frozen': frozen, 'frozen_sha256': digest, 'run_probe_set_sha256': digest,
            'technical': {'technically_complete': True, 'run': {'status': 'complete'}}, 'passes': answers(frozen)}


@unittest.skipUnless(FOUND, 'the pinned tokenizer files are not available offline')
class TwoSessionAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frozen_a, _ = PR.load_frozen()
        frozen_b = ST.build('B', tokenizer=TK.Tokenizer(FOUND))
        cls.a, cls.b = session('A', frozen_a), session('B', frozen_b)
        cls.binding = {'A': cls.a['frozen_sha256'], 'B': cls.b['frozen_sha256']}

    def refused(self, sessions, binding=None, fragment=None):
        result = FI.pooled_analysis(sessions, binding or self.binding, require_withheld=False, resamples=200)
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(set(result), {'status', 'reasons'})
        text = json.dumps(result).lower()
        for word in OUTCOME_WORDS:
            self.assertNotIn(word, text)
        if fragment:
            self.assertTrue(any(fragment in r for r in result['reasons']), result['reasons'])
        return result

    def test_one_session_alone_is_refused(self):
        self.refused([self.a], fragment='both sessions')
        self.refused([self.b], fragment='both sessions')

    def test_an_invalid_second_session_is_refused(self):
        missing = copy.deepcopy(self.b)
        missing['passes']['pass_2'].pop(next(iter(missing['passes']['pass_2'])))
        self.refused([self.a, missing], fragment='recomputed technical status is incomplete')
        noisy = copy.deepcopy(self.b)
        for n, probe_id in enumerate(list(noisy['passes']['pass_1'])):
            if n % 20 == 0:  # 5% schema-invalid answers
                noisy['passes']['pass_1'][probe_id] = SC.score({'probe_id': probe_id, 'question': {'kind': 'recall'},
                                                               'truth': ['no_evidence'], 'package': ['no_evidence']},
                                                              'not json')
        self.refused([self.a, noisy], fragment='session_technically_invalid_outputs')
        unevaluated = dict(self.b, technical={'technically_complete': False})
        self.refused([self.a, unevaluated], fragment='not technically complete')
        other_run = dict(self.b, run_probe_set_sha256='0' * 64)
        self.refused([self.a, other_run], fragment='retained run names a different frozen set')

    def test_swapped_duplicated_or_unregistered_sessions_are_refused(self):
        self.refused([dict(self.a, label='B'), dict(self.b, label='A')], fragment='registered for session')
        self.refused([self.a, self.a], fragment='each exactly once')
        self.refused([self.a, self.b], binding={'A': self.a['frozen_sha256'], 'B': '0' * 64},
                     fragment='not the one registered for session B')
        tampered = copy.deepcopy(self.b)
        tampered['frozen']['probes'][0]['truth'] = ['changed_then_returned']
        self.refused([self.a, tampered], fragment='does not match its stated hash')

    def test_the_development_stand_in_is_refused_unless_explicitly_allowed(self):
        result = FI.pooled_analysis([self.a, self.b], self.binding, resamples=200)
        self.assertEqual(result['status'], 'refused')
        self.assertTrue(any('is not withheld' in r for r in result['reasons']))

    def test_both_valid_sessions_give_the_analysis_of_the_concatenated_rows(self):
        result = FI.pooled_analysis([self.b, self.a], self.binding, require_withheld=False, resamples=300)
        self.assertEqual(result['status'], 'analysed')
        self.assertEqual(result['sessions'], self.binding)
        rows = []
        for s in (self.a, self.b):
            rows += SC.rows_by_pass(s['frozen'], s['passes'])['pass_1']
        expected = P.analyze_rows({arm: [r for r in rows if r['arm'] == arm] for arm in SC.ARMS}, resamples=300)
        self.assertEqual(result['analysis'], expected)
        self.assertEqual(result['verdict'], expected['conclusions']['verdict'])
        groups = {(r['family'], r['group']) for r in rows}
        self.assertEqual(len(groups), 84)  # both sessions pooled: 7 families x 12 groups
        self.assertEqual(result['analysis']['primary_endpoint']['memory']['groups'], 60)
        repeats = sum(len(s['frozen']['schedule'][1]['probe_ids']) for s in (self.a, self.b))
        self.assertEqual(result['stability']['repeated_questions'], repeats)


if __name__ == '__main__':
    unittest.main()
