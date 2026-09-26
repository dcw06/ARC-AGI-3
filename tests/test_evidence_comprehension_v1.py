"""Evidence comprehension v1: frozen probe set, dual keys, request contents and scoring."""
import ast
import json
from pathlib import Path
import unittest

from research.action_effect_history_v1.contract import SYSTEM_PROMPT as LIVE_PROMPT
from research.evidence_comprehension_v1 import independent, probes as P
from research.evidence_comprehension_v1.score import heuristic_baselines, parse, score, summarize
from scripts import build_evidence_comprehension_v1 as B

ROOT = Path(__file__).resolve().parents[1]


class ProbeSet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = json.loads(B.OUTPUT.read_bytes())
        cls.contexts = {c['context_id']: c for c in cls.frozen['contexts']}

    def test_frozen_file_matches_a_fresh_build(self):
        self.assertEqual(B.encode(B.build()), B.OUTPUT.read_bytes())

    def test_every_key_matches_the_independent_derivation(self):
        fixtures = json.loads(B.FIXTURES.read_bytes())
        _, episodes = B.archived_episodes()
        for probe in self.frozen['probes']:
            context = self.contexts[probe['context_id']]
            if context['grids']:
                entries, _ = independent.archived_entries(episodes[context['provenance']['episode_id']],
                                                          context['provenance']['decision'])
            else:
                entries, _ = independent.synthetic_entries(context, fixtures)
            self.assertEqual(independent.answer(entries, context['observation']['legal_actions'], probe['family'],
                                                probe['arg']), probe['key'], probe['probe_id'])

    def test_independent_keys_share_no_code_with_the_record_path(self):
        tree = ast.parse((ROOT / 'research/evidence_comprehension_v1/independent.py').read_text(encoding='utf-8'))
        imported = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertEqual(imported, [])

    def test_real_contexts_are_the_exact_live_observations(self):
        _, episodes = B.archived_episodes()
        real = [c for c in self.frozen['contexts'] if c['grids']]
        self.assertEqual(len(real), len(B.REAL_EPISODES) * len(B.REAL_DECISIONS))
        for context in real:
            p = context['provenance']
            call = episodes[p['episode_id']]['calls'][p['call_index']]
            self.assertEqual(call['request_sha256'], p['request_sha256'])
            self.assertEqual(json.loads(call['request']['messages'][1]['content'])['observation'], context['observation'])

    def test_requests_carry_only_the_observation_and_question(self):
        self.assertTrue(P.SYSTEM_PROMPT.endswith(LIVE_PROMPT.split('\n', 1)[1]))  # live control text, verbatim
        for probe in self.frozen['probes']:
            request = P.build_request(self.contexts[probe['context_id']], probe)
            user = json.loads(request['messages'][1]['content'])
            self.assertEqual(set(user), {'observation', 'question'})
            self.assertNotIn('events', json.dumps(user))
            self.assertEqual((request['temperature'], request['seed']), (0, 0))

    def test_every_key_is_a_valid_answer_under_its_schema(self):
        for probe in self.frozen['probes']:
            row = score(probe, json.dumps({'answer': probe['key']}))
            self.assertTrue(row['valid'] and row['correct'], probe['probe_id'])

    def test_coverage_minimums(self):
        counts = json.loads(B.SUMMARY.read_bytes())['counts']
        for label in ('acknowledged_no_change', 'changed_then_returned', 'dispatch_failed', 'final_frame_changed',
                      'outcome_unknown', 'not_shown'):
            self.assertGreaterEqual(counts.get(f'evidence_only/outcome_class/key={label}', 0), 9, label)
        for label in ('evidence_only/observed_effect/near_miss_click', 'full_observation/observed_effect/near_miss_click',
                      'evidence_only/coordinate_actions/key=empty', 'evidence_only/coordinate_actions/key=value',
                      'evidence_only/tried_unchanged/key=value', 'evidence_only/tried_unchanged/key=empty'):
            self.assertGreaterEqual(counts.get(label, 0), 10, label)
        self.assertGreaterEqual(counts.get('evidence_only/outcome_class/dimension_change', 0), 5)


class Scoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = json.loads(B.OUTPUT.read_bytes())
        cls.observations = {c['context_id']: c['observation'] for c in cls.frozen['contexts']}

    def test_oracle_scores_perfectly_and_missing_answers_count_against(self):
        probes = self.frozen['probes']
        results = {p['probe_id']: score(p, json.dumps({'answer': p['key']})) for p in probes}
        table = summarize(probes, results)
        self.assertTrue(all(g['accuracy'] == 1.0 for g in table.values()))
        del results[probes[0]['probe_id']]
        table = summarize(probes, results)
        label = f"{probes[0]['condition']}/{probes[0]['family']}"
        self.assertEqual((table[label]['missing'], table[label]['correct']), (1, table[label]['n'] - 1))

    def test_invalid_and_wrong_answers(self):
        probe = next(p for p in self.frozen['probes'] if p['family'] == 'outcome_class')
        for content in ('not json', '{"answer": "maybe"}', '{"answer": "final_frame_changed", "why": "x"}', '[]'):
            self.assertFalse(score(probe, content)['valid'], content)
        wrong = next(label for label in (*P.OUTCOMES, 'not_shown') if label != probe['key'])
        self.assertEqual(score(probe, json.dumps({'answer': wrong})), {'probe_id': probe['probe_id'], 'valid': True,
                         'correct': False, 'duplicate_items': False, 'answer': wrong})
        recall = next(p for p in self.frozen['probes'] if p['family'] == 'recall_action' and p['key'] != 'not_shown')
        self.assertFalse(score(recall, json.dumps({'answer': {'action_id': 6, 'action_data': {'x': 1.5}}}))['valid'])

    def test_lists_are_scored_as_sets_and_duplicates_are_recorded(self):
        probe = next(p for p in self.frozen['probes'] if p['family'] == 'available_actions' and len(p['key']) > 1)
        row = score(probe, json.dumps({'answer': list(reversed(probe['key'])) + probe['key'][:1]}))
        self.assertTrue(row['correct'] and row['duplicate_items'])
        self.assertEqual(parse('tried_unchanged', '{"answer": []}'), [])

    def test_near_miss_clicks_are_not_the_clicked_action(self):
        near = [p for p in self.frozen['probes'] if 'near_miss_click' in p['strata']]
        self.assertTrue(near and all(p['key'] == 'not_observed' for p in near))
        entries = {c: o['action_effect_history']['entries'] for c, o in self.observations.items()}
        # For every near-miss probe the same action type was dispatched, so ignoring coordinates answers wrongly.
        self.assertTrue(all(any(e['action_id'] == 6 for e in entries[p['context_id']]) for p in near))
        baselines = heuristic_baselines(near, self.observations)
        self.assertTrue(all(v['correct'] == 0 for k, v in baselines.items() if k.endswith('ignore_coordinates')))


if __name__ == '__main__':
    unittest.main()
