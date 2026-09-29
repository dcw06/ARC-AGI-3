"""Workstream 3 factual transition questionnaire, draft r0: keys, isolation, leakage and balance (no model calls)."""
import collections
import json
import unittest

from research.transition_evidence_v1 import fixtures as F, questionnaire as Q

BUILT = Q.build()
PROBES = BUILT['probes']
BY_PAIR = {}
for _p in PROBES:
    BY_PAIR.setdefault(_p['pair_id'], {})[_p['condition']] = _p


def request(p):
    return Q.build_request(BUILT['contexts'][p['context_id']], p)


class Keys(unittest.TestCase):
    def test_three_derivations_agree_and_keys_are_in_the_schema(self):
        # build() raises if record, reference and construction keys ever disagree
        for p in PROBES:
            self.assertIn(p['key'], Q.ANSWERS[p['family']])

    def test_causal_claims_are_never_keyed_supported(self):
        causal = [p for p in PROBES if p['family'] == 'claim_causal']
        self.assertTrue(causal)
        self.assertNotIn('supported', {p['key'] for p in causal})

    def test_progress_claims_are_never_contradicted_by_a_missing_report(self):
        keys = {p['key'] for p in PROBES if p['family'] == 'claim_progress'}
        self.assertEqual(keys, {'supported', 'not_established'})


class Isolation(unittest.TestCase):
    def test_conditions_differ_only_by_the_computed_field(self):
        for pair in BY_PAIR.values():
            raw, full = (json.loads(request(pair[c])['messages'][1]['content']) for c in Q.CONDITIONS)
            computed = full['evidence'].pop('computed_measurements')
            self.assertEqual(raw, full)
            self.assertEqual(computed['computed_by'], 'deterministic tool from the evidence above, not the model')
            self.assertEqual(request(pair['raw_evidence'])['messages'][0], request(pair['raw_plus_computed_record'])['messages'][0])

    def test_requests_carry_no_keys_labels_or_construction(self):
        for p in PROBES[::7]:
            content = request(p)['messages'][1]['content'].lower()
            for leak in ('"key"', 'shortcut', 'fixture', 'counter', 'transient', '"expected"', 'construction', 'recolour',
                         'q-'):
                self.assertNotIn(leak, content, (p['probe_id'], leak))

    def test_computed_view_keeps_uncertainty(self):
        for cid, context in BUILT['contexts'].items():
            if 'computed_measurements' not in context:
                continue
            c = context['computed_measurements']
            if context['dispatch']['status'] != 'acknowledged':
                self.assertNotEqual(c['any_returned_frame_differs']['status'], 'measured')
                self.assertEqual(c['visual_effect']['status'], 'indeterminate')
            if c['progress']['status'] == 'confirmed':
                self.assertTrue(set(c['progress']['signals']) <= {'levels_completed_increased', 'state_WIN'})


class Partitions(unittest.TestCase):
    def test_sequences_never_cross_partitions_and_seeds_are_fresh(self):
        owner = {}
        for p in PROBES:
            self.assertEqual(owner.setdefault(p['source_context'], p['partition']), p['partition'])
        seeds = {s for s, _ in Q.PARTITIONS.values()}
        self.assertFalse(seeds & {s for s, _ in F.PARTITIONS.values()})

    def test_every_request_is_unique(self):
        seen = set()
        for p in PROBES:
            raw = json.dumps(request(p), sort_keys=True)
            self.assertNotIn(raw, seen)
            seen.add(raw)


class Balance(unittest.TestCase):
    def test_no_shortcut_dominates_and_disagreement_coverage_suffices(self):
        for family in Q.FAMILIES:
            group = [p for p in PROBES if p['partition'] == 'withheld' and p['condition'] == 'raw_evidence'
                     and p['family'] == family]
            counts = collections.Counter(s for p in group for s in p['shortcuts_correct'])
            best = max(counts.values())
            with self.subTest(family=family):
                self.assertLessEqual(best / len(group), 0.90)
                self.assertGreaterEqual(len(group) - best, 10)


if __name__ == '__main__':
    unittest.main()
