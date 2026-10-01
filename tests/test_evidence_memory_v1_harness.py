"""Evidence-linked memory v1 (Track 2): scripted writers, readers and context pressure. No model is called."""
import ast
import json
from pathlib import Path
import unittest

from research.evidence_memory_v1 import fidelity as F, readers as RD, render as R, schema as S, trajectories as TR, \
    writers as W

PACKAGE = Path(__file__).resolve().parents[1] / 'research/evidence_memory_v1'
TRAJECTORIES = TR.generate(delays=(0, 8), count=1)


def evaluate(cls, gate=False, trajectories=TRAJECTORIES):
    out = []
    for t in trajectories:
        run = W.run_writer(cls(), t, gate=gate)
        out.append((t, run, F.evaluate(t['records'], run['memory'], t['evaluator_only']['expected'])))
    return out


def total(results, key):
    return sum(len(rep[key]) for _, _, rep in results)


class Writers(unittest.TestCase):
    def test_faithful_writer_is_faithful_everywhere(self):
        for gate in (False, True):
            for t, run, rep in evaluate(W.Faithful, gate):
                self.assertTrue(rep['faithful'], (t['id'], gate, rep))
                self.assertEqual(run['log'], [])

    def test_each_faulty_writer_is_caught_by_its_own_failure_class(self):
        lossy = evaluate(W.Lossy)
        self.assertLess(sum(r['facts']['retained'] for *_, r in lossy), sum(r['facts']['required'] for *_, r in lossy))
        self.assertEqual(total(lossy, 'unsupported') + total(lossy, 'overclaims'), 0)
        over = evaluate(W.Overclaiming)
        self.assertGreater(total(over, 'overclaims'), 0)
        self.assertGreater(total(over, 'unsupported'), 0)  # unknown outcomes recorded as "no change"
        self.assertGreater(total(over, 'ignored_counterexamples'), 0)
        self.assertTrue(any(r['revision']['still_live'] for *_, r in over))
        scope = evaluate(W.ScopeViolating)
        self.assertGreater(total(scope, 'scope_violations'), 0)
        self.assertGreater(total(scope, 'stale_state_dependent'), 0)
        self.assertTrue(any(r['required_live']['lost'] for *_, r in scope))

    def test_invalid_outputs_are_retained_and_charged(self):
        for t, run, rep in evaluate(W.Invalid):
            invalid = [r for r in run['log'] if r['kind'] == 'invalid_output']
            self.assertTrue(invalid and all(r['output'] and r['error'] for r in invalid))
            self.assertEqual(run['charge']['writer_calls'], len(t['records']))
            self.assertEqual(rep['numeric_confidence'], [])
            if len(t['records']) >= 5:
                self.assertTrue(any('confidence' in json.dumps(r.get('operation')) for r in run['log']))

    def test_every_writer_call_is_charged(self):
        for t, run, _ in evaluate(W.Faithful):
            self.assertEqual(run['charge']['writer_calls'], len(t['records']))
            self.assertGreater(run['charge']['input_chars'], 0)
            self.assertGreater(run['charge']['output_chars'], 0)

    def test_gate_blocks_bad_writes_but_not_omissions(self):
        ungated, gated = evaluate(W.Overclaiming), evaluate(W.Overclaiming, gate=True)
        self.assertEqual(total(gated, 'overclaims') + total(gated, 'unsupported'), 0)
        self.assertGreater(sum(len(run['log']) for _, run, _ in gated), 0)  # rejected writes are retained
        self.assertTrue(any(r['revision']['still_live'] for *_, r in gated))  # a never-revised claim survives
        self.assertGreater(total(ungated, 'overclaims'), total(gated, 'overclaims'))
        stale = evaluate(W.ScopeViolating, gate=True)
        self.assertGreater(total(stale, 'stale_state_dependent'), 0)


class Readers(unittest.TestCase):
    def test_known_correct_memory_and_scripted_readers(self):
        scores = {}
        for name, make in RD.READERS.items():
            rows = []
            for t in TRAJECTORIES:
                memory = W.run_writer(W.Faithful(), t)['memory']
                rows += RD.ask(t, make([e for e in memory['entries'] if e['status'] != S.RETIRED]))
            scores[name] = sum(r['correct'] for r in rows) / len(rows)
            if name == 'invalid':
                self.assertTrue(all(not r['valid'] and r['output'] for r in rows))
        self.assertEqual(scores['faithful'], 1.0)
        self.assertLess(scores['status_blind'], 1.0)
        self.assertEqual(scores['invalid'], 0.0)

    def test_reader_never_sees_the_answer(self):
        seen = []
        RD.ask(TRAJECTORIES[0], lambda q: seen.append(q) or '{}')
        self.assertTrue(seen and all('expected_answer' not in q for q in seen))

    def test_packages_respect_one_budget_and_never_show_retired_entries(self):
        for t in TRAJECTORIES:
            memory = W.run_writer(W.Faithful(), t)['memory']
            p = RD.packages(t, memory)
            self.assertLessEqual(p['memory']['chars'], p['budget_chars'])
            self.assertLessEqual(p['state_keyed_raw']['chars'], p['budget_chars'])
            self.assertTrue(all(e['status'] != S.RETIRED for e in p['memory']['entries']))
            self.assertNotIn('retired', R.memory_text(memory['entries']))


class ContextPressure(unittest.TestCase):
    def test_window_is_frozen(self):
        self.assertEqual(RD.WINDOW, 6)

    def test_recent_window_forgets_and_full_history_does_not(self):
        rows = RD.pressure(delays=(0, 8), count=2, families=['early_crucial'])
        near = [r for r in rows if r['delay'] == 0]
        far = [r for r in rows if r['delay'] == 8]
        self.assertTrue(all(r['full_history'] == 1.0 for r in rows))
        self.assertTrue(all(r['recent_raw'] == 1.0 and r['relevant_in_window'] for r in near))
        self.assertTrue(all(r['recent_raw'] < 1.0 and not r['relevant_in_window'] for r in far))
        self.assertTrue(all(r['state_keyed_raw'] == 1.0 for r in far))  # the control must be beaten, not the strawman


class Boundaries(unittest.TestCase):
    def test_no_model_network_or_process_imports(self):
        allowed = {'copy', 'json', 'hashlib', 'random', 'collections', 'research.evidence_memory_v1',
                   'research.transition_evidence_v1', 'research.transition_evidence_v1.transition'}
        for path in PACKAGE.glob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            modules = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
            modules |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            self.assertLessEqual(modules, allowed, path.name)

    def test_transition_contract_is_used_read_only(self):
        for path in PACKAGE.glob('*.py'):
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('fixtures.json', text)
            self.assertNotIn('write_bytes', text)
            self.assertNotIn("open(", text)


if __name__ == '__main__':
    unittest.main()
