"""Evidence-linked memory v1 (Track 2): schema, update rules, trajectories and the independent checker."""
import ast
import copy
import json
from pathlib import Path
import unittest

from research.evidence_memory_v1 import fidelity as F, schema as S, trajectories as TR, writers as W
from research.transition_evidence_v1 import transition as T

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'research/evidence_memory_v1'


def trajectory(family, delay=3, index=0):
    return TR.build(family, index, delay)


def entry(entry_id='e1', kind=S.OBSERVATION, action=None, value='no_observed_change', scope=None,
          status=S.SUPPORTED, evidence=(), counter=(), step=0):
    return W.new_entry(entry_id, kind, {'action': action or TR.act(1), 'predicate': 'visual_effect', 'value': value},
                       scope or {'kind': S.CROSS_LEVEL}, status, list(evidence), list(counter), step, 'test')


def codes(problems):
    return {p.split(':')[0] for p in problems}


class Store(unittest.TestCase):
    def setUp(self):
        t = trajectory('coordinate_specific')
        self.idx = S.index(t['records'])
        self.info = next(iter(self.idx.values()))  # a dead click: no observed change
        self.scope = {'kind': S.EXACT_STATE, 'level': 0, 'state_sha256': self.info['state']}
        self.obs = entry(action=self.info['action'], scope=self.scope, evidence=[self.info['ref']])
        self.memory = S.Memory()
        self.memory.add(self.obs, 0, 'observed')

    def test_no_numeric_confidence_and_fixed_fields(self):
        extra = {**copy.deepcopy(self.obs), 'id': 'e2', 'confidence': 0.9}
        with self.assertRaises(S.OperationError):
            self.memory.add(extra, 0, 'x')
        floaty = copy.deepcopy(self.obs)
        floaty['id'], floaty['claim']['action']['action_data'] = 'e3', {'x': 1.5, 'y': 2}
        self.assertIn('numeric_confidence', codes(S.shape_problems(floaty)))

    def test_no_silent_overwrite(self):
        with self.assertRaises(S.OperationError):
            self.memory.add(self.obs, 1, 'again')
        with self.assertRaises(S.OperationError):  # stale expected revision
            self.memory.revise('e1', 0, {'last_reviewed_step': 1}, 1, 'x')
        with self.assertRaises(S.OperationError):  # a reason is required
            self.memory.revise('e1', 1, {'last_reviewed_step': 1}, 1, '')
        with self.assertRaises(S.OperationError):  # the kind never changes
            self.memory.revise('e1', 1, {'kind': S.HYPOTHESIS}, 1, 'x')

    def test_evidence_rules(self):
        with self.assertRaises(S.OperationError):  # evidence dropped without a change of scope or claim
            self.memory.revise('e1', 1, {'evidence': []}, 1, 'x')
        self.memory.revise('e1', 1, {'counterevidence': [self.info['ref']]}, 1, 'x')
        with self.assertRaises(S.OperationError):  # counterevidence is append-only
            self.memory.revise('e1', 2, {'counterevidence': []}, 2, 'x')

    def test_retire_preserves_and_blocks(self):
        self.memory.review('e1', 1, 2, 're-examined')
        self.memory.retire('e1', 2, 3, 'superseded')
        self.assertEqual(self.memory.entries['e1']['status'], S.RETIRED)
        with self.assertRaises(S.OperationError):
            self.memory.revise('e1', 3, {'last_reviewed_step': 4}, 4, 'x')
        successor = {**copy.deepcopy(self.obs), 'id': 'e2', 'supersedes': 'e1'}
        self.memory.add(successor, 4, 'replacement')
        self.assertEqual([r['op'] for r in self.memory.audit], ['add', 'review', 'retire', 'add'])

    def test_audit_replays_and_is_append_only(self):
        self.memory.revise('e1', 1, {'last_reviewed_step': 2}, 2, 'x')
        first = copy.deepcopy(self.memory.audit[0])
        self.memory.retire('e1', 2, 3, 'done')
        self.assertEqual(self.memory.audit[0], first)
        self.assertEqual(S.replay(self.memory.audit), self.memory.view()['entries'])
        broken = copy.deepcopy(self.memory.audit)
        del broken[1]
        with self.assertRaises(S.OperationError):
            S.replay(broken)


class Checks(unittest.TestCase):
    def test_observation_must_be_reconstructable(self):
        t = trajectory('unknown_outcome')
        idx = S.index(t['records'])
        infos = sorted(idx.values(), key=lambda i: i['step'])
        unknown, failed, unchanged = infos[0], infos[1], infos[2]
        scope = lambda i: {'kind': S.EXACT_STATE, 'level': 0, 'state_sha256': i['state']}
        good = entry(action=unchanged['action'], scope=scope(unchanged), evidence=[unchanged['ref']], step=2)
        self.assertEqual(S.check(good, idx), [])
        for info in (unknown, failed):
            bad = entry(action=info['action'], scope=scope(info), evidence=[info['ref']], step=2)
            self.assertEqual(codes(S.check(bad, idx)), {'unknown_outcome_as_evidence'})
        wrong = entry(action=unchanged['action'], value='final_frame_differs', scope=scope(unchanged),
                      evidence=[unchanged['ref']], step=2)
        self.assertEqual(codes(S.check(wrong, idx)), {'observation_not_reconstructable'})
        future = entry(action=unchanged['action'], scope=scope(unchanged), evidence=[unchanged['ref']], step=1)
        self.assertEqual(codes(S.check(future, idx)), {'dangling_reference'})
        broad = entry(action=unchanged['action'], scope={'kind': S.LEVEL, 'level': 0}, evidence=[unchanged['ref']], step=2)
        self.assertIn('scope_violation', codes(S.check(broad, idx)))

    def test_three_failed_clicks_never_become_clicking_never_works(self):
        t = trajectory('coordinate_specific')
        idx = S.index(t['records'])
        dead = [i for i in sorted(idx.values(), key=lambda i: i['step'])][:3]
        claim = {'action_id': 6, 'action_data': S.ANY}
        never = entry(kind=S.HYPOTHESIS, action=claim, scope={'kind': S.LEVEL, 'level': 0},
                      evidence=[i['ref'] for i in dead], step=2)
        self.assertEqual(codes(S.check(never, idx)), {'overgeneralization'})
        tentative = {**never, 'status': S.TENTATIVE}
        self.assertEqual(S.check(tentative, idx), [])  # an explicitly tentative hypothesis is allowed ...
        self.assertEqual(codes(S.check(tentative, idx, as_of=len(idx) - 1)), {'counterexample_ignored'})  # ... until refuted
        universal = {**tentative, 'scope': {'kind': S.CROSS_LEVEL}, 'status': S.SUPPORTED}
        self.assertIn('scope_violation', codes(S.check(universal, idx)))

    def test_level_change_does_not_make_a_rule_universal(self):
        t = trajectory('level_change')
        idx = S.index(t['records'])
        level0 = [i for i in idx.values() if i['level'] == 0 and i['action'] == TR.act(4)]
        moved = entry(kind=S.HYPOTHESIS, action=TR.act(4), value='final_frame_differs',
                      scope={'kind': S.LEVEL, 'level': 1}, evidence=[i['ref'] for i in level0], step=len(idx) - 1)
        self.assertIn('scope_violation', codes(S.check(moved, idx)))
        cross = {**moved, 'scope': {'kind': S.CROSS_LEVEL}, 'status': S.TENTATIVE}
        self.assertEqual(codes(S.check(cross, idx)), {'counterexample_ignored'})

    def test_reset_invalidates_state_dependent_entries_only(self):
        t = trajectory('reset_keeps_mechanism')
        idx = S.index(t['records'])
        unchanged = next(i for i in idx.values() if i['action'] == TR.act(4))
        segment = entry(kind=S.HYPOTHESIS, action=TR.act(4), status=S.TENTATIVE, evidence=[unchanged['ref']],
                        scope={'kind': S.SEGMENT, 'level': 0, 'segment': 0}, step=len(idx) - 1)
        self.assertEqual(codes(S.check(segment, idx)), {'stale_state_dependent'})
        self.assertEqual(S.check(segment, idx, as_of=unchanged['step']), [])
        run = W.run_writer(W.Faithful(), t)
        live = {e['id'] for e in run['memory']['entries'] if e['status'] in S.LIVE}
        self.assertIn('hyp-level-L0-a1', live)  # the mechanism survives the reset
        retired = [r for r in run['memory']['audit'] if r['op'] == 'retire']
        self.assertTrue(retired and all(r['before']['scope']['kind'] == S.SEGMENT for r in retired))


class Trajectories(unittest.TestCase):
    def test_deterministic_valid_and_construction_agrees_with_gold(self):
        first, second = TR.generate(), TR.generate()
        self.assertEqual(TR.digest(first), TR.digest(second))
        self.assertEqual({t['family'] for t in first}, set(TR.FAMILIES))
        for t in first:
            self.assertEqual({t['partition']}, {'development'})
            for record in t['records']:
                self.assertEqual(T.validate(record), [])
            for q in t['evaluator_only']['expected']['questions']:
                self.assertEqual(F.gold(t['records'], q), q['expected_answer'], (t['id'], q['kind']))

    def test_raw_evidence_carries_no_labels_or_answers(self):
        for t in TR.generate():
            text = json.dumps(t['raws']).lower()
            for word in (t['family'], 'expected', 'construction', 'crucial', 'distract', 'confidence'):
                self.assertNotIn(word, text)

    def test_delay_moves_relevant_evidence_away_from_the_question(self):
        gaps = []
        for delay in (0, 4, 8):
            expected = trajectory('early_crucial', delay)['evaluator_only']['expected']
            gaps.append(expected['final_step'] - max(expected['relevant_steps']))
        self.assertEqual(gaps, [g + gaps[0] for g in (0, 4, 8)])

    def test_only_a_development_partition_exists(self):
        self.assertEqual((TR.PARTITION, TR.SEED), ('development', 'evidence-memory-v1-development'))
        names = {n.id for n in ast.walk(ast.parse((PACKAGE / 'trajectories.py').read_text(encoding='utf-8')))
                 if isinstance(n, ast.Name)}
        self.assertFalse({n for n in names if 'EVAL' in n.upper() or 'HOLDOUT' in n.upper()})


class IndependentChecker(unittest.TestCase):
    def test_fidelity_imports_nothing_from_the_project(self):
        tree = ast.parse((PACKAGE / 'fidelity.py').read_text(encoding='utf-8'))
        modules = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        modules |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertEqual(modules, {'json'})

    def test_agrees_with_schema_on_which_entries_are_faulty(self):
        for t in TR.generate(delays=(0, 8), count=1):
            idx = S.index(t['records'])
            for cls in W.WRITERS.values():
                memory = W.run_writer(cls(), t)['memory']
                report = F.evaluate(t['records'], memory, t['evaluator_only']['expected'])
                by_schema = {e['id'] for e in memory['entries']
                             if e['status'] != S.RETIRED and S.check(e, idx, len(idx) - 1)}
                by_checker = {x['id'] if isinstance(x, dict) else x for k in (
                    'unsupported', 'scope_violations', 'overclaims', 'ignored_counterexamples', 'stale_state_dependent')
                    for x in report[k]}
                self.assertEqual(by_schema, by_checker, (t['id'], cls.name))

    def test_audit_tampering_is_detected(self):
        t = trajectory('early_crucial')
        memory = W.run_writer(W.Faithful(), t)['memory']
        self.assertTrue(F.evaluate(t['records'], memory, t['evaluator_only']['expected'])['audit_consistent'])
        tampered = copy.deepcopy(memory)
        tampered['entries'][0]['claim']['value'] = 'final_frame_differs'  # an edit with no audit row
        self.assertFalse(F.evaluate(t['records'], tampered, t['evaluator_only']['expected'])['audit_consistent'])


if __name__ == '__main__':
    unittest.main()
