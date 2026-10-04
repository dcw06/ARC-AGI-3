"""End to end with the REAL evaluator and evidence loader: two rehearsal sessions, pooled; an altered session refused.

Each session runs through the real connected rehearsal path (launcher -> supervisor -> worker -> host -> fake
server over HTTP -> runner) with its development stand-in frozen set (session B's via the rehearsal-only
EM1S_REHEARSAL_FROZEN override) and the `clean_answers` rehearsal fault, so each session can be technically valid.
Then run/final.py evaluates each exact output with the real derived evaluator routed to that session's frozen set,
and pools. The sessions are full size (2,896 and 2,832 calls): the pooled analysis's own checks require both
sessions to split groups 0-11 and every scheduled call to be answered, so a smaller rehearsal could not pool.
POSIX-only (fcntl, process groups, Unix sockets), like the connected suite.
"""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import unittest

POSIX = os.name == 'posix'
if POSIX:
    from research.evidence_memory_v1 import stage1 as ST, tokens as TK
    from research.evidence_memory_v1.run import final as FI, probes as PR
    from research.evidence_memory_v1.run.rehearse import rehearse

SECONDS = 900
BASE = Path.home() / 'ecv-rehearsal-tests'


@unittest.skipUnless(POSIX, 'the reviewed run stack is POSIX-only')
class PooledAnalysisEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not TK.locate():
            raise unittest.SkipTest('the pinned tokenizer files are not available offline')
        BASE.mkdir(exist_ok=True)
        cls.work = Path(tempfile.mkdtemp(dir=BASE))
        frozen_b = cls.work / 'frozen_B.json'
        frozen_b.write_bytes(ST.encode(ST.build('B', tokenizer=TK.Tokenizer(TK.locate()))))
        cls.frozen = {'A': PR.FROZEN_PATH, 'B': frozen_b}
        cls.binding = {label: hashlib.sha256(path.read_bytes()).hexdigest() for label, path in cls.frozen.items()}
        cls.outputs, cls.receipts = {}, {}
        for label, path in cls.frozen.items():
            os.environ[PR.REHEARSAL_FROZEN_ENV] = str(path)
            try:
                cls.receipts[label], cls.outputs[label] = rehearse('clean_answers', SECONDS, cls.work / label)
            finally:
                os.environ.pop(PR.REHEARSAL_FROZEN_ENV, None)
        cls.sessions = {label: FI.evaluate_session(label, cls.frozen[label], cls.outputs[label], mode='rehearsal',
                                                   rehearsal_seconds=SECONDS) for label in cls.frozen}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def pool(self, sessions):
        return FI.pooled_analysis(sessions, self.binding, require_withheld=False, resamples=500)

    def test_1_two_real_sessions_are_evaluated_and_pooled(self):
        for label, receipt in self.receipts.items():
            self.assertEqual(receipt['study_status'], 'study_ended_pending_independent_evaluation', label)
            session = self.sessions[label]
            self.assertTrue(session['technical']['technically_complete'], (label, session['technical']['lifecycle_errors'],
                                                                           session['technical']['call_errors']))
            self.assertEqual(session['technical']['analysis']['verdict'], 'session_technically_valid', label)
            self.assertEqual(session['run_probe_set_sha256'], self.binding[label])
            self.assertEqual(session['evaluated_inputs'], session['inputs'])
        result = self.pool([self.sessions['A'], self.sessions['B']])
        self.assertEqual(result['status'], 'analysed', result.get('reasons'))
        self.assertEqual(result['analysis']['primary_endpoint']['memory']['groups'], 60)

    def altered_b(self):
        """A copy of B's output with one byte of one retained answer flipped in the call log."""
        copy = self.work / 'B-altered'
        if not copy.exists():
            shutil.copytree(self.outputs['B'], copy)
            log = copy / 'worker/run/calls.jsonl'
            raw = log.read_bytes()
            at = raw.index(b'"values')  # inside the first retained recall answer
            log.write_bytes(raw[:at + 2] + (b'V' if raw[at + 2:at + 3] != b'V' else b'v') + raw[at + 3:])
        return FI.evaluate_session('B', self.frozen['B'], copy, mode='rehearsal', rehearsal_seconds=SECONDS)

    def test_2_an_altered_session_is_refused_because_its_re_evaluation_fails(self):
        altered = self.altered_b()
        self.assertFalse(altered['technical']['technically_complete'])
        result = self.pool([self.sessions['A'], altered])
        self.assertEqual(result['status'], 'refused')
        self.assertTrue(any('session B: the independent evaluation is not technically complete' in r
                            for r in result['reasons']), result['reasons'])

    def test_3_the_altered_session_with_its_earlier_successful_evaluation_is_refused(self):
        altered, earlier = self.altered_b(), self.sessions['B']
        stale = dict(altered, technical=earlier['technical'], evaluated_inputs=earlier['evaluated_inputs'])
        result = self.pool([self.sessions['A'], stale])
        self.assertEqual(set(result), {'status', 'reasons'})
        self.assertTrue(any('session B: the independent evaluation is not bound to the inputs being pooled' in r
                            for r in result['reasons']), result['reasons'])
        self.assertNotEqual(earlier['inputs']['run_calls'], altered['inputs']['run_calls'])


if __name__ == '__main__':
    unittest.main()
