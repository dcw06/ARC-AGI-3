"""Scientific distinctions checked on the successor's actual schedule (the frozen question set the runtime sends).

Read-only, CPU only. Nothing here changes a question, key, arm, prompt or rule: it verifies that the evidence and the
unchanged scorer keep the distinctions the protocol depends on, on exactly the requests the successor sends.
"""
import copy
import json
from pathlib import Path
import unittest

from research.progress_subgoal_v1 import questions as Q
from research.progress_subgoal_v1.evaluate_run import score_call
from research.progress_subgoal_v1.score import analyze
from research.transition_evidence_v1 import transition as T, vocabulary as V
from tests import psv1r2_fixtures as FX

ROOT = Path(__file__).resolve().parents[1]
A, B = Q.PRIMARY_CONDITIONS


def frame_valid(frame):
    return (isinstance(frame, list) and frame and all(isinstance(r, list) and r for r in frame)
            and len({len(r) for r in frame}) == 1
            and all(type(v) is int and 0 <= v <= 15 for r in frame for v in r))


def changed(a, b):
    return sum(x != y for ra, rb in zip(a, b) for x, y in zip(ra, rb))


class FrozenSet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen, cls.digest, cls.rows, _, _ = FX.schedule()
        cls.contexts = {c['context_id']: c['evidence'] for c in cls.frozen['contexts']}
        cls.probes = {p['probe_id']: p for p in cls.frozen['probes']}
        cls.withheld = [p for p in cls.frozen['probes'] if p['partition'] == 'withheld']

    def last(self, probe):
        return self.contexts[probe['context_id']]['transitions'][-1]

    def keys(self, family, cls_name=None, where=None):
        out = {}
        for p in self.withheld:
            if p['condition'] != A or p['family'] != family:
                continue
            if cls_name and cls_name not in p['critical_classes']:
                continue
            if where and not where(p):
                continue
            out[p['key']] = out.get(p['key'], 0) + 1
        return out

    # ---- arms and evidence

    def test_the_successor_sends_the_frozen_question_set(self):
        self.assertEqual(self.digest, FX.frozen_protocol()['experiment']['probe_set_sha256'])
        self.assertEqual(self.frozen['conditions'], list(Q.PRIMARY_CONDITIONS))
        self.assertEqual(len(self.rows), 5852)

    def test_arms_see_identical_evidence_and_differ_only_in_the_safeguard(self):
        by_case = {}
        for p in self.frozen['probes']:
            by_case.setdefault(p['case_context'], {})[p['condition']] = p['context_id']
        for case, ids in by_case.items():
            self.assertEqual(self.contexts[ids[A]], self.contexts[ids[B]], case)
        self.assertEqual(self.frozen['system_prompts'][B], self.frozen['system_prompts'][A] + Q.SAFEGUARD)
        pairs = {}
        for _, _, _, probe_id, request in self.rows:
            pairs.setdefault(self.probes[probe_id]['pair_id'], {})[self.probes[probe_id]['condition']] = request
        for pair in pairs.values():
            a, b = copy.deepcopy(pair[A]), copy.deepcopy(pair[B])
            self.assertEqual(a['messages'][1], b['messages'][1])
            a['messages'][0] = b['messages'][0] = None
            self.assertEqual(a, b)

    def test_computed_record_restates_the_raw_evidence_and_adds_no_answers(self):
        """Raw vs computed differ only as intended: every computed measurement is recomputed here from the raw part of
        the same transition, and the computed record carries no keys, labels or causal statements."""
        allowed = {'computed_by', 'observation_availability', 'returned_frames', 'any_returned_frame_differs',
                   'final_frame_equals_frame_before', 'visual_effect', 'environment_events', 'progress',
                   'continuity_with_previous_transition'}
        checked = 0
        for evidence in self.contexts.values():
            for step in evidence['transitions']:
                cm = step['computed_measurements']
                self.assertEqual(set(cm), allowed)
                status = step['dispatch']['status']
                if status != V.ACKNOWLEDGED:
                    self.assertEqual((step['returned_frames'], step['environment_after']), ('none observed', 'not observed'))
                    self.assertEqual(cm['visual_effect']['status'], V.INDETERMINATE)
                    self.assertEqual(cm['observation_availability']['status'],
                                     V.NOT_APPLICABLE if status == V.FAILED else V.MISSING)
                    self.assertEqual(cm['progress']['status'], V.UNKNOWN)
                    continue
                before, frames = step['frame_before'], step['returned_frames']
                self.assertEqual(len(cm['returned_frames']), len(frames))
                diffs = []
                for row, frame in zip(cm['returned_frames'], frames):
                    self.assertEqual(row['valid'], frame_valid(frame))
                    if row['valid']:
                        self.assertEqual(row['changed_cells_vs_frame_before']['value'], changed(before, frame))
                        diffs.append(changed(before, frame) > 0)
                env_b, env_a = step['environment_before'], step['environment_after']
                confirmed = (env_a.get('state') == 'WIN' or (env_a.get('levels_completed') or 0)
                             > (env_b.get('levels_completed') or 0))
                self.assertEqual(cm['progress']['status'], V.CONFIRMED if confirmed else V.UNKNOWN)
                final_valid = bool(frames) and frame_valid(frames[-1])
                visual = cm['visual_effect']['status']
                if not frames or not final_valid:
                    self.assertEqual(visual, V.INDETERMINATE)
                elif changed(before, frames[-1]) > 0:
                    self.assertEqual(visual, V.FINAL_FRAME_DIFFERS)
                elif any(diffs):
                    self.assertEqual(visual, V.CHANGED_THEN_RETURNED)
                elif all(frame_valid(f) for f in frames):
                    self.assertEqual(visual, V.NO_OBSERVED_CHANGE)
                else:
                    self.assertEqual(visual, V.INDETERMINATE)
                checked += 1
        self.assertGreater(checked, 2500)
        text = json.dumps([e['transitions'] for e in self.contexts.values()]).lower()
        for word in ('"key"', 'shortcut', 'critical_class', 'fixture_family'):
            self.assertNotIn(word, text)

    # ---- distinctions

    def test_unknown_outcomes_stay_unknown(self):
        unknown = lambda p: self.last(p)['dispatch']['status'] == V.OUTCOME_UNKNOWN  # noqa: E731
        self.assertEqual(set(self.keys('visual_effect', where=unknown)), {'indeterminate'})
        self.assertEqual(set(self.keys('progress_status', where=unknown)), {'unknown'})
        self.assertEqual(set(self.keys('region_changed', where=unknown)), {'cannot_tell'})
        contexts = {p['case_context'] for p in self.withheld if 'unobserved_last_outcome' in p['critical_classes']}
        self.assertGreaterEqual(len(contexts), 20)
        failed = lambda p: self.last(p)['dispatch']['status'] == V.FAILED  # noqa: E731
        self.assertLessEqual(set(self.keys('visual_effect', where=failed)), {'indeterminate'})
        self.assertLessEqual(set(self.keys('region_changed', where=failed)), {'cannot_tell'})

    def test_transient_changes_are_neither_no_change_nor_a_final_difference(self):
        transient = lambda p: self.last(p)['computed_measurements']['visual_effect']['status'] == V.CHANGED_THEN_RETURNED  # noqa: E731
        self.assertEqual(set(self.keys('visual_effect', where=transient)), {'changed_then_returned'})
        contexts = {p['case_context'] for p in self.withheld if 'transient_change' in p['critical_classes']}
        self.assertGreaterEqual(len(contexts), 20)

    def test_dimension_changes_keep_their_distinction_in_the_unchanged_presentation(self):
        # Protocol v2 section 4 excludes dimension changes from this generator (WS3 v1 covers them); the frozen set has none.
        comparabilities = {f.get('comparability_to_frame_before') for e in self.contexts.values()
                           for s in e['transitions'] for f in (s['computed_measurements']['returned_frames'] or [])}
        self.assertNotIn(V.DIMENSIONS_DIFFER, comparabilities)
        # The unchanged contract and presentation still keep the distinction if such evidence is sent.
        from research.transition_evidence_v1 import fixtures as WF
        fixtures = json.loads(WF.OUTPUT.read_bytes())['fixtures']
        raw = next(r for f in fixtures for r in f['raws'] if r['outcome']['status'] == V.ACKNOWLEDGED
                   and (r['outcome']['after'].get('frames') or [None])[-1] is not None
                   and len(r['outcome']['after']['frames'][-1]) != len(r['before']['frames'][-1]))
        view = Q.computed_view(T.history([raw])[-1])
        final = view['returned_frames'][-1]
        self.assertEqual(final['comparability_to_frame_before'], V.DIMENSIONS_DIFFER)
        self.assertEqual(final['changed_cells_vs_frame_before']['status'], 'unavailable')
        self.assertEqual(view['visual_effect']['status'], V.FINAL_FRAME_DIFFERS)

    def test_visible_change_is_not_confirmed_progress(self):
        self.assertEqual(set(self.keys('progress_status', 'visible_change_without_progress')), {'unknown'})
        claim = lambda p: p['claim'] == 'progress_confirmed'  # noqa: E731
        self.assertLessEqual(set(self.keys('claim_progress', 'visible_change_without_progress', claim)),
                             {'not_established', 'contradicted'})
        self.assertEqual(set(self.keys('progress_status', 'progress_without_visible_change')), {'confirmed'})
        # A respondent that reads any visible change as progress fails the false-progress gate on these requests.
        passes = self.policy(lambda p, key: ('confirmed' if p['family'] == 'progress_status'
                                             and self.last(p)['computed_measurements']['any_returned_frame_differs'].get('value')
                                             else key))
        report = analyze(self.frozen['probes'], passes, 'withheld')
        for arm in Q.PRIMARY_CONDITIONS:
            self.assertEqual(report['over_claims'][arm]['false_progress']['status'], 'fails')
            self.assertEqual(report['over_claims'][arm]['unsupported_causal_claim']['status'], 'passes')

    def test_temporal_sequence_is_not_causation(self):
        self.assertNotIn('supported', self.keys('claim_causal'))
        mechanism = lambda p: p['claim'] == 'mechanism_identified'  # noqa: E731
        self.assertLessEqual(set(self.keys('claim_causal', where=mechanism)), {'not_established', 'contradicted'})
        self.assertIn('strengthened', self.keys('effect_hypothesis'))
        caused = lambda p: p['claim'] == 'caused_region_change'  # noqa: E731
        self.assertLessEqual(set(self.keys('claim_causal', 'hypothesis_strengthened', caused)),
                             {'not_established', 'contradicted'})
        # A respondent that reads a repeated sequence as a cause fails the unsupported-causal-claim gate.
        passes = self.policy(lambda p, key: 'supported' if p['family'] == 'claim_causal' and key == 'not_established'
                             else key)
        report = analyze(self.frozen['probes'], passes, 'withheld')
        for arm in Q.PRIMARY_CONDITIONS:
            self.assertEqual(report['over_claims'][arm]['unsupported_causal_claim']['status'], 'fails')

    def test_interrupted_schedules_cannot_produce_complete_verdicts(self):
        full = self.policy(lambda p, key: key)
        report = analyze(self.frozen['probes'], full, 'withheld')
        self.assertEqual(set(r['status'] for r in report['readiness'].values()), {'eligible_for_memory_or_supervision'})
        cut = {'pass_1': full['pass_1']}  # pass 2 never ran
        report = analyze(self.frozen['probes'], cut, 'withheld')
        self.assertEqual(report['completeness']['primary'], 'incomplete')
        self.assertEqual(set(r['status'] for r in report['readiness'].values()), {'incomplete'})
        one = copy.deepcopy(full)
        gate_probe = next(p for p in self.withheld if Q.gate_member('false_progress', p))
        del one['pass_2'][gate_probe['probe_id']]
        report = analyze(self.frozen['probes'], one, 'withheld')
        self.assertEqual(report['completeness']['over_claim_gates'], 'incomplete')
        self.assertEqual(set(r['status'] for r in report['readiness'].values()), {'incomplete'})
        report = analyze(self.frozen['probes'], full, 'withheld', recovered=True)
        self.assertEqual(set(r['status'] for r in report['readiness'].values()), {'incomplete'})

    def test_invalid_answers_are_a_reliability_category_not_over_claims(self):
        passes = self.policy(lambda p, key: None if p['family'] in ('claim_causal', 'claim_progress') else key)
        report = analyze(self.frozen['probes'], passes, 'withheld')
        for arm in Q.PRIMARY_CONDITIONS:
            self.assertEqual(report['over_claims'][arm]['unsupported_causal_claim']['over_claim_contexts'], 0)
            self.assertEqual(report['over_claims'][arm]['false_no_progress']['over_claim_contexts'], 0)
            self.assertEqual(report['validity'][arm]['all_responses']['status'], 'fails')
            self.assertEqual(report['readiness'][arm]['status'], 'not_eligible')
            self.assertTrue(any('validity not met' in x for x in report['readiness'][arm]['problems']))

    def policy(self, answer):
        """Scored passes for a scripted policy over the scheduled calls (None: an invalid, malformed reply)."""
        passes = {'pass_1': {}, 'pass_2': {}}
        for _, _, pass_id, probe_id, _ in self.rows:
            p = self.probes[probe_id]
            value = answer(p, p['key'])
            content = 'not json' if value is None else json.dumps({'answer': value})
            passes[pass_id][probe_id] = score_call(p, {'finish_reason': 'stop', 'response': content})
        return passes


if __name__ == '__main__':
    unittest.main()
