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
    inputs = {'output_tree': 'tree-' + label, 'run_manifest': 'm', 'run_calls': 'c', 'run_index': 'i',
              'frozen_set': digest, 'evaluator_source': 'e'}
    return {'label': label, 'frozen': frozen, 'frozen_sha256': digest, 'run_probe_set_sha256': digest,
            'technical': {'technically_complete': True, 'run': {'status': 'complete'}, 'mode': 'rehearsal'},
            'passes': answers(frozen), 'evaluated_inputs': dict(inputs), 'inputs': dict(inputs)}


def retained_calls(frozen):
    """A retained call log answering every scheduled probe (the shape the evidence loader returns)."""
    from research.action_effect_history_v1.service import request_hash
    contexts = {c['context_id']: c for c in frozen['contexts']}
    probes = {p['probe_id']: p for p in frozen['probes']}
    calls = []
    for block in frozen['schedule']:
        for probe_id in block['probe_ids']:
            probe = probes[probe_id]
            wrong = int(hashlib.sha256(probe_id.encode()).hexdigest(), 16) % 100 == 0
            calls.append({'index': len(calls), 'pass_id': block['pass'], 'probe_id': probe_id, 'status': 'answered',
                          'request_sha256': request_hash(ST.build_request(contexts[probe['context_id']], probe)),
                          'response': json.dumps(ScriptedAnswers.wrong(probe) if wrong else probe['key']),
                          'finish_reason': 'stop'})
    return calls


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

    def test_an_evaluation_not_bound_to_the_pooled_inputs_is_refused(self):
        stale = copy.deepcopy(self.b)
        stale['inputs']['run_calls'] = 'changed after the evaluation'
        self.refused([self.a, stale], fragment='not bound to the inputs being pooled')
        unbound = dict(self.b, evaluated_inputs=None)
        self.refused([self.a, unbound], fragment='not bound to the inputs being pooled')
        other_frozen = copy.deepcopy(self.b)
        other_frozen['inputs']['frozen_set'] = other_frozen['evaluated_inputs']['frozen_set'] = '0' * 64
        self.refused([self.a, other_frozen], fragment='evaluated inputs name a different frozen set')
        live = FI.pooled_analysis([self.a, self.b], self.binding, require_withheld=True, resamples=200)
        self.assertTrue(any("not live" in r for r in live['reasons']))  # rehearsal evaluations never count as live

    def test_the_development_stand_in_is_refused_unless_explicitly_allowed(self):
        result = FI.pooled_analysis([self.a, self.b], self.binding, resamples=200)
        self.assertEqual(result['status'], 'refused')
        self.assertTrue(any('is not withheld' in r for r in result['reasons']))

    def test_both_valid_sessions_give_the_analysis_of_the_concatenated_rows(self):
        result = FI.pooled_analysis([self.b, self.a], self.binding, require_withheld=False, resamples=300)
        self.assertEqual(result['status'], 'analysed')
        self.assertEqual({k: v['frozen_sha256'] for k, v in result['sessions'].items()}, self.binding)
        self.assertEqual(result['sessions']['A']['inputs'], self.a['inputs'])
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


class EvaluatorUsesTheSessionFrozenSet(unittest.TestCase):
    def test_the_evaluator_reads_the_frozen_set_given_for_the_session(self):
        from pathlib import Path
        from research.evidence_memory_v1.run import probes
        default = probes.load_frozen
        with FI._frozen_for_evaluation({'session': 'X'}, 'f' * 64):
            self.assertEqual(probes.load_frozen(), ({'session': 'X'}, 'f' * 64))
        self.assertIs(probes.load_frozen, default)
        here = Path(FI.__file__).parent
        for name in ('evaluate.py', 'score.py'):  # both import load_frozen at call time, so they see the session's set
            self.assertIn('from research.evidence_memory_v1.run.probes import load_frozen',
                          (here / name).read_text(encoding='utf-8'), name)
        self.assertNotIn('evaluation_a.json', Path(FI.__file__).read_text(encoding='utf-8'))  # no supplied evaluation


@unittest.skipUnless(FOUND, 'the pinned tokenizer files are not available offline')
class EvaluationBinding(unittest.TestCase):
    """evaluate_session on real output trees. The reviewed evaluator and evidence loader need POSIX, so here they are
    replaced by stand-ins: the evaluator fails exactly when the retained call log differs from the original, as the
    real one does for an altered run (request hashes, order, timing)."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        from pathlib import Path
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        frozen_a, _ = PR.load_frozen()
        frozen_b = ST.build('B', tokenizer=TK.Tokenizer(FOUND))
        cls.paths, cls.runs = {}, {}
        for label, frozen in (('A', frozen_a), ('B', frozen_b)):
            frozen_path = root / f'frozen_{label}.json'
            frozen_path.write_bytes(ST.encode(frozen))
            output = root / f'output_{label}'
            (output / 'worker/run').mkdir(parents=True)
            (output / 'control').mkdir()
            calls = retained_calls(frozen)
            (output / 'worker/run/calls.jsonl').write_text('\n'.join(json.dumps(c) for c in calls) + '\n')
            (output / 'worker/run/run.json').write_text(json.dumps({'status': 'complete'}))
            (output / 'worker/run/manifest.json').write_text('{}')
            (output / 'control/outer.json').write_text('{}')
            cls.paths[label] = (frozen_path, output)
            cls.runs[label] = {'probe_set_sha256': hashlib.sha256(ST.encode(frozen)).hexdigest(), 'calls': calls,
                               'original_log': (output / 'worker/run/calls.jsonl').read_bytes()}
        cls.binding = {label: cls.runs[label]['probe_set_sha256'] for label in ('A', 'B')}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def evaluate(self, label):
        run = self.runs[label]

        def evaluator(output, frozen, digest, mode, rehearsal_seconds):
            intact = (output / 'worker/run/calls.jsonl').read_bytes() == run['original_log']
            return {'mode': mode, 'technically_complete': intact,
                    'run': {'status': 'complete' if intact else 'incomplete'}}

        def loader(output):
            calls = [json.loads(line) for line in (output / 'worker/run/calls.jsonl').read_text().splitlines()]
            return {'probe_set_sha256': run['probe_set_sha256'], 'calls': calls}
        frozen_path, output = self.paths[label]
        return FI.evaluate_session(label, frozen_path, output, mode='rehearsal', rehearsal_seconds=600,
                                   evaluator=evaluator, loader=loader)

    def pool(self, sessions):
        return FI.pooled_analysis(sessions, self.binding, require_withheld=False, resamples=200)

    def test_an_altered_run_with_an_earlier_successful_evaluation_is_refused(self):
        a, b = self.evaluate('A'), self.evaluate('B')
        self.assertEqual(a['evaluated_inputs'], a['inputs'])
        self.assertEqual(self.pool([a, b])['status'], 'analysed')
        frozen_path, output = self.paths['B']
        log = output / 'worker/run/calls.jsonl'
        lines = log.read_text().splitlines()
        call = json.loads(lines[0])
        call['response'] = json.dumps({'values': ['changed_then_returned']})
        log.write_text('\n'.join([json.dumps(call)] + lines[1:]) + '\n')
        try:
            altered = self.evaluate('B')  # the independent evaluation of the altered run fails
            self.assertFalse(altered['technical']['technically_complete'])
            result = self.pool([a, altered])
            self.assertEqual(result['status'], 'refused')
            self.assertTrue(any('not technically complete' in r for r in result['reasons']))
            # The altered run paired with the earlier successful evaluation (a stale receipt): refused.
            stale = dict(altered, technical=b['technical'], evaluated_inputs=b['evaluated_inputs'])
            result = self.pool([a, stale])
            self.assertEqual(set(result), {'status', 'reasons'})
            self.assertTrue(any('not bound to the inputs being pooled' in r for r in result['reasons']), result)
            self.assertNotEqual(b['inputs']['run_calls'], altered['inputs']['run_calls'])
            self.assertNotEqual(b['inputs']['output_tree'], altered['inputs']['output_tree'])
        finally:
            log.write_bytes(self.runs['B']['original_log'])

    def test_the_digest_covers_the_frozen_set_the_run_files_the_tree_and_the_evaluator(self):
        frozen_path, output = self.paths['A']
        digest = FI.inputs_digest(output, frozen_path.read_bytes())
        self.assertEqual(set(digest), {'output_tree', 'run_manifest', 'run_calls', 'run_index', 'frozen_set',
                                       'evaluator_source'})
        self.assertEqual(digest['frozen_set'], self.binding['A'])
        extra = output / 'control/notebook-cost.json'
        extra.write_text('{}')
        try:
            self.assertNotEqual(FI.inputs_digest(output, frozen_path.read_bytes())['output_tree'], digest['output_tree'])
        finally:
            extra.unlink()


if __name__ == '__main__':
    unittest.main()
