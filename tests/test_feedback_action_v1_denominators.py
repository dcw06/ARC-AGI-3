"""Feedback-action v1: explicit denominators, undefined-versus-zero, minimums, and failure-inclusive rates."""
import copy
import unittest

from research.feedback_action_v1 import evaluate as EV, rehearsal as R

RESULTS = R.rehearse()


def rates(name, arm='candidate'):
    return RESULTS[(name, arm)][1]['metrics']['rates']


def nd(value):
    return value['numerator'], value['denominator'], value['status']


def fail(row, arm):
    """The same decision, had the model's output been invalid (opportunities unchanged: they come from evidence)."""
    out = {k: v for k, v in row.items()
           if k not in ('action_key', 'chosen_status', 'citations', 'cited_record_ids', 'prediction',
                        'prediction_result', 'repeat_cites_its_no_change', 'cites_nothing_with_evidence_shown')}
    out['opportunities'] = {k: v for k, v in row['opportunities'].items() if k != 'untested_type_chosen'}
    out['action_problem'] = 'not_json'
    out['procedure_problem'] = 'not_json' if arm == 'candidate' else None
    if row.get('revision') not in (None, 'previous_statement_absent'):
        out['revision'] = 'procedure_invalid'
    return out


class RateRules(unittest.TestCase):
    def test_undefined_is_never_zero(self):
        self.assertEqual(EV.rate(0, 0), {'numerator': 0, 'denominator': 0, 'minimum': 1, 'status': 'undefined',
                                         'value': None})
        self.assertEqual(EV.rate(0, 5)['value'], 0.0)
        self.assertEqual(EV.rate(2, 4, minimum=5)['status'], 'insufficient')
        self.assertIsNone(EV.rate(2, 4, minimum=5)['value'])
        self.assertEqual(EV.rate(2, 4, minimum=5)['observed'], 0.5)
        self.assertEqual(EV.rate(1, 1, applicable=False)['status'], 'not_applicable')

    def test_no_citations_means_undefined_unsupported_rate(self):
        self.assertEqual(nd(rates('contradiction_ignored')['unsupported_citation']), (0, 0, 'undefined'))
        self.assertEqual(nd(rates('decision_budget_exhausted_all_invalid')['unsupported_citation']), (0, 0, 'undefined'))

    def test_candidate_only_rates_are_not_applicable_to_the_baseline(self):
        for name in EV.CANDIDATE_ONLY:
            self.assertEqual(rates('delayed_effect', 'baseline')[name]['status'], 'not_applicable')


class Denominators(unittest.TestCase):
    def test_repeat_opportunities(self):
        self.assertEqual(nd(rates('contradiction_ignored')['repeat_after_no_change']), (1, 1, 'defined'))
        self.assertEqual(nd(rates('contradiction_revised')['repeat_after_no_change']), (0, 1, 'defined'))
        self.assertEqual(nd(rates('coordinate_actions')['repeat_after_no_change']), (1, 3, 'defined'))
        self.assertEqual(nd(rates('unknown_dispatch_outcome')['repeat_after_no_change']), (0, 2, 'defined'))
        # no same-state "no observed change" was ever shown: undefined, not 0 repeats (the s5i5 situation)
        self.assertEqual(nd(rates('reset_and_level_boundaries')['repeat_after_no_change']), (0, 0, 'undefined'))
        rows = RESULTS[('coordinate_actions', 'candidate')][1]['decisions']
        self.assertEqual([r['opportunities']['repeatable_keys'] for r in rows], [[], [[6, 1, 1]], [[6, 1, 1]],
                                                                                  [[6, 1, 1]]])

    def test_untested_action_type(self):
        rows = RESULTS[('contradiction_revised', 'candidate')][1]['decisions']
        self.assertEqual(rows[1]['opportunities']['untested_types'], [2, 3, 4])
        self.assertTrue(rows[1]['opportunities']['untested_type_chosen'])
        self.assertEqual(nd(rates('contradiction_revised')['untested_type_chosen']), (2, 2, 'defined'))
        self.assertEqual(nd(rates('contradiction_ignored')['untested_type_chosen']), (1, 2, 'defined'))

    def test_citation_opportunities_and_supply(self):
        # windows non-empty at decisions 1-3; decision 2's block is invalid (a citation without a ref)
        self.assertEqual(nd(rates('missing_and_invented_references')['citation_supply']), (2, 3, 'defined'))
        self.assertEqual(nd(rates('missing_and_invented_references')['unsupported_citation']), (3, 4, 'defined'))
        # cleared at a reset: the window is empty, so there was no citation opportunity
        self.assertEqual(nd(rates('contradiction_at_reset')['citation_supply']), (0, 0, 'undefined'))
        self.assertEqual(nd(rates('delayed_effect')['citation_supply']), (4, 4, 'defined'))

    def test_prediction_and_revision_include_failures(self):
        self.assertEqual(nd(rates('invalid_structured_output')['prediction_accuracy']), (1, 4, 'defined'))
        self.assertEqual(nd(rates('decision_budget_exhausted_all_invalid')['prediction_accuracy']), (0, 3, 'defined'))
        self.assertEqual(nd(rates('contradiction_revised')['revision_recognized']), (1, 1, 'defined'))
        self.assertEqual(nd(rates('reset_and_level_boundaries')['revision_recognized']), (0, 0, 'undefined'))

    def test_capped_episode_keeps_every_call(self):
        for arm in ('baseline', 'candidate'):
            r = rates('decision_budget_exhausted_all_invalid', arm)
            self.assertEqual(nd(r['invalid_action']), (3, 3, 'defined'))
            self.assertEqual(nd(r['untested_type_chosen']), (0, 3, 'defined'))


class FailureNeverImprovesARate(unittest.TestCase):
    def test_turning_any_decision_into_an_invalid_output(self):
        """For every rate usable for advancement: failing keeps the decision in the denominator and never moves the
        rate in the favourable direction."""
        checked = 0
        for (name, arm), (trajectory, evaluation) in RESULTS.items():
            rows = evaluation['decisions']
            before = EV.counts(arm, rows)
            for i in range(len(rows)):
                after = EV.counts(arm, rows[:i] + [fail(rows[i], arm)] + rows[i + 1:])
                for metric, (n0, d0) in before.items():
                    if metric in EV.DESCRIPTIVE_ONLY:
                        continue
                    n1, d1 = after[metric]
                    if metric == 'unsupported_citation':  # failure removes citations: it can only reduce evidence
                        self.assertLessEqual(d1, d0)
                        continue
                    self.assertGreaterEqual(d1, d0, (name, arm, i, metric))  # the failed decision stays counted
                    if d0 and d1:
                        if metric in EV.UNFAVOURABLE:
                            self.assertGreaterEqual(n1 / d1, n0 / d0, (name, arm, i, metric))
                        else:
                            self.assertLessEqual(n1 / d1, n0 / d0, (name, arm, i, metric))
                checked += 1
        self.assertGreater(checked, 60)

    def test_the_valid_only_rate_could_be_gamed_and_is_descriptive_only(self):
        rows = RESULTS[('coordinate_actions', 'baseline')][1]['decisions']
        self.assertEqual(EV.counts('baseline', rows)['repeat_after_no_change_valid_only'], (1, 3))
        failed = rows[:1] + [fail(rows[1], 'baseline')] + rows[2:]  # the repeat replaced by an invalid output
        self.assertEqual(EV.counts('baseline', failed)['repeat_after_no_change_valid_only'], (0, 2))  # looks better
        self.assertEqual(EV.counts('baseline', failed)['repeat_after_no_change'], (1, 3))  # the rule it must use
        self.assertEqual(EV.DESCRIPTIVE_ONLY, ('repeat_after_no_change_valid_only',))

    def test_unsupported_rate_cannot_be_earned_by_failing(self):
        """Failing removes citations, which makes the unsupported rate undefined or insufficient, never a pass."""
        rows = RESULTS[('missing_and_invented_references', 'candidate')][1]['decisions']
        failed = [fail(r, 'candidate') for r in rows]
        self.assertEqual(EV.rates('candidate', failed)['unsupported_citation']['status'], 'undefined')
        self.assertEqual(EV.rates('candidate', failed)['citation_supply']['value'], 0.0)


class Aggregation(unittest.TestCase):
    def test_minimums_apply_when_pooling(self):
        pooled = EV.aggregate([RESULTS[('contradiction_revised', 'candidate')][1],
                               RESULTS[('contradiction_ignored', 'candidate')][1]])
        self.assertEqual(nd(pooled['repeat_after_no_change']), (1, 2, 'insufficient'))
        self.assertEqual(nd(pooled['revision_recognized']), (1, 2, 'insufficient'))
        self.assertEqual(pooled['invalid_action']['status'], 'defined')
        with self.assertRaises(ValueError):
            EV.aggregate([RESULTS[('delayed_effect', 'candidate')][1], RESULTS[('delayed_effect', 'baseline')][1]])

    def test_minimums_are_stated(self):
        self.assertEqual(EV.MINIMUMS['citation_supply'], 10)
        self.assertEqual(EV.MINIMUMS['unsupported_citation'], 10)
        self.assertEqual(EV.MINIMUMS['repeat_after_no_change'], 5)
        self.assertEqual(EV.MINIMUMS['untested_type_chosen'], 5)
        self.assertEqual(EV.MINIMUMS['revision_recognized'], 3)
        self.assertEqual(EV.MINIMUMS['prediction_accuracy'], 10)


if __name__ == '__main__':
    unittest.main()
