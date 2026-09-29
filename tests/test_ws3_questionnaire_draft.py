"""Workstream 3 factual transition questionnaire, draft r2: keys, isolation, leakage, coverage, schedule and rules."""
import ast
import collections
import copy
import inspect
import json
from pathlib import Path
import unittest

from research.transition_evidence_v1 import fixtures as F, questionnaire as Q, transition as T
from research.transition_evidence_v1.score import analyze, score

ROOT = Path(__file__).resolve().parents[1]
BUILT = Q.build()
PROBES = BUILT['probes']
BY_PAIR = {}
for _p in PROBES:
    BY_PAIR.setdefault(_p['pair_id'], {})[_p['condition']] = _p


def request(p):
    return Q.build_request(BUILT['contexts'][p['context_id']], p)


def other(p):
    return next(a for a in Q.ANSWERS[p['family']] if a != p['key'])


def passes(bad=lambda p: False, answer=None, drop=()):
    rows = {}
    for p in PROBES:
        if p['probe_id'] in drop:
            continue
        a = (answer(p) if answer else other(p)) if bad(p) else p['key']
        rows[p['probe_id']] = score(p, json.dumps({'answer': a}))
    return {'pass_1': rows, 'pass_2': dict(rows)}


class Keys(unittest.TestCase):
    def test_keys_are_in_the_schema_and_causal_claims_are_never_supported(self):
        for p in PROBES:
            self.assertIn(p['key'], Q.ANSWERS[p['family']])
        self.assertNotIn('supported', {p['key'] for p in PROBES if p['family'] == 'claim_causal'})
        self.assertEqual({p['key'] for p in PROBES if p['family'] == 'claim_progress'}, {'supported', 'not_established'})

    def test_construction_keys_use_only_observable_facts(self):
        source = inspect.getsource(Q.key_from_construction)
        used = {n.slice.value for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Subscript)
                and isinstance(n.value, ast.Name) and n.value.id == 'expected' and isinstance(n.slice, ast.Constant)}
        self.assertEqual(used, {'dispatch', 'availability', 'any_differs', 'final_equals', 'vs_pre', 'events', 'progress'})
        for name in Q.UNOBSERVABLE_CONSTRUCTION:
            self.assertNotIn(name, source)

    def test_an_unobserved_change_underneath_never_changes_a_key(self):
        import random
        keys = []
        for flag in (False, True):
            b = F.Builder(random.Random(11))
            b.unknown(changed_underneath=flag)
            record = T.build(b.raws[0])
            keys.append([Q.key_from_record(record, f, a) for f in Q.FAMILIES for a in (Q.CLAIM_FAMILIES.get(f) or [None])])
        self.assertEqual(keys[0], keys[1])


class Isolation(unittest.TestCase):
    def test_conditions_differ_only_by_the_computed_field(self):
        for pair in BY_PAIR.values():
            raw, full = (json.loads(request(pair[c])['messages'][1]['content']) for c in Q.CONDITIONS)
            full['evidence'].pop('computed_measurements')
            self.assertEqual(raw, full)
            self.assertEqual(request(pair['raw_evidence'])['messages'][0], request(pair['raw_plus_computed_record'])['messages'][0])

    def test_candidate_adds_only_facts_computed_from_the_reference_evidence(self):
        for cid, context in BUILT['contexts'].items():
            if 'computed_measurements' not in context:
                continue
            ev = context
            if ev['dispatch']['status'] == 'acknowledged':
                outcome = {'status': 'acknowledged', 'after': {**ev['environment_after'], 'frames': ev['returned_frames']}}
            else:
                outcome = {'status': ev['dispatch']['status'], 'reason': ev['dispatch']['reason']}
            raw = {'identity': {'episode_id': 'x', 'action_index': 0},
                   'before': {**ev['environment_before'], 'frames': [ev['frame_before']]}, 'proposal': None,
                   'dispatched': ev['dispatched_action'], 'outcome': outcome, 'environment_source': 'x'}
            self.assertEqual(Q.computed_view(T.build(raw)), ev['computed_measurements'], cid)

    def test_requests_carry_no_keys_labels_or_provenance(self):
        for p in PROBES[::5]:
            content = request(p)['messages'][1]['content'].lower()
            for leak in ('"key"', 'shortcut', 'fixture', 'counter', 'transient', '"expected"', 'construction',
                         'recolour', 'q-', 't-', 'aeh', 'r8', 'archiv', 'synthetic', 'offline_development_engine'):
                self.assertNotIn(leak, content, (p['probe_id'], leak))


class Coverage(unittest.TestCase):
    def test_roles_are_declared_and_floors_hold(self):
        self.assertEqual(set(Q.ROLE_OF), set(Q.FAMILIES))
        report = Q.coverage(PROBES)  # raises if any floor fails
        for family in Q.ROLES['primary']:
            self.assertGreaterEqual(report['families'][family]['n'], 100)
            self.assertGreaterEqual(report['families'][family]['shortcut_disagreement_n'], 20)
        self.assertTrue(all(n >= 20 for n in report['critical_classes'].values()))
        self.assertTrue(all(n >= 100 for n in report['over_claim_denominators'].values()))

    def test_extraction_questions_are_tagged(self):
        for p in PROBES:
            self.assertEqual(p['extraction_under_candidate'], p['family'] in Q.EXTRACTION_UNDER_CANDIDATE)
        self.assertFalse(any(p['extraction_under_candidate'] for p in PROBES if p['family'].startswith('claim_')))

    def test_transfer_group_is_archived_labelled_and_separate(self):
        transfer = [p for p in PROBES if p['partition'] == 'transfer']
        self.assertEqual({p['fixture_family'] for p in transfer}, {'archived_transition'})
        self.assertTrue(10 <= len({p['case_context'] for p in transfer}) <= 16)  # 16 preselected, duplicates asked once
        owner = {}
        for p in PROBES:
            self.assertEqual(owner.setdefault(p['source_context'], p['partition']), p['partition'])


class Schedule(unittest.TestCase):
    def test_repetition_policy_order_and_balance(self):
        blocks = BUILT['schedule']
        self.assertEqual([(b['partition'], b['pass']) for b in blocks][:2], [('withheld', 'pass_1'), ('withheld', 'pass_2')])
        self.assertEqual(blocks[1]['probe_ids'], blocks[0]['probe_ids'][::-1])
        counts = collections.Counter(i for b in blocks for i in b['probe_ids'])
        for p in PROBES:
            self.assertEqual(counts[p['probe_id']], 2 if p['partition'] == 'withheld' else 1)
        by_id = {p['probe_id']: p for p in PROBES}
        firsts = collections.Counter(by_id[i]['condition'] for i in blocks[0]['probe_ids'][::2])
        self.assertLessEqual(abs(firsts['raw_evidence'] - firsts['raw_plus_computed_record']), 1)

    def test_every_request_is_unique(self):
        seen = set()
        for p in PROBES:
            raw = json.dumps(request(p), sort_keys=True)
            self.assertNotIn(raw, seen)
            seen.add(raw)


class Rules(unittest.TestCase):
    def test_reference_already_meeting_the_criterion_is_not_a_promotion(self):
        report = analyze(PROBES, passes())
        self.assertEqual(report['verdict'], 'reference_meets_criterion_tool_assisted')
        self.assertEqual(report['over_claims']['raw_plus_computed_record']['false_progress']['status'], 'passes')

    def test_candidate_fixing_reference_errors_is_a_clear_improvement(self):
        def bad(p):  # the reference misses every combination question on disagreement-relevant keys
            return p['condition'] == 'raw_evidence' and p['role'] == 'primary' and p['partition'] == 'withheld'
        self.assertEqual(analyze(PROBES, passes(bad))['verdict'], 'candidate_clear_improvement_tool_assisted')

    def test_false_progress_over_cap_blocks_promotion(self):
        denominators = sorted({p['case_context'] for p in PROBES if p['partition'] == 'withheld'
                               and (p['family'], p['key']) in Q.OVER_CLAIM_GATES['false_progress']})
        flagged = set(denominators[:len(denominators) // 20 + 1])  # a little over 5%

        def bad(p):
            if p['condition'] == 'raw_evidence' and p['role'] == 'primary' and p['partition'] == 'withheld':
                return True
            return (p['condition'] == 'raw_plus_computed_record' and p['case_context'] in flagged
                    and p['family'] == 'progress_status' and p['key'] == 'unknown')
        report = analyze(PROBES, passes(bad, answer=lambda p: 'confirmed' if p['family'] == 'progress_status' else other(p)))
        gate = report['over_claims']['raw_plus_computed_record']['false_progress']
        self.assertEqual(gate['status'], 'fails')
        self.assertNotEqual(report['verdict'], 'candidate_clear_improvement_tool_assisted')

    def test_invalid_answers_count_as_over_claims(self):
        causal = [p for p in PROBES if p['partition'] == 'withheld' and p['family'] == 'claim_causal'
                  and p['condition'] == 'raw_plus_computed_record'][:3]
        value = passes()
        for p in causal:
            value['pass_2'][p['probe_id']] = score(p, 'not json')
        gate = analyze(PROBES, value)['over_claims']['raw_plus_computed_record']['unsupported_causal_claim']
        self.assertEqual(gate['over_claim_contexts'], 3)

    def test_completeness_policy(self):
        primary = next(p['probe_id'] for p in PROBES if p['partition'] == 'withheld' and p['role'] == 'primary')
        report = analyze(PROBES, passes(drop=(primary,)))
        self.assertEqual((report['completeness']['primary'], report['verdict']), ('incomplete', 'incomplete_tool_assisted'))
        transfer = next(p['probe_id'] for p in PROBES if p['partition'] == 'transfer')
        report = analyze(PROBES, passes(drop=(transfer,)))
        self.assertEqual(report['completeness']['whole_schedule'], 'incomplete')
        self.assertEqual(report['verdict'], 'reference_meets_criterion_tool_assisted')


if __name__ == '__main__':
    unittest.main()
