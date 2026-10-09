"""Full HTTP CPU rehearsals of the derived lifecycle (opt-in: PSV1R2_REHEARSALS=1; Linux; a host python with pip,
named by PSV1R2_REHEARSAL_HOST_PYTHON when the test interpreter has none).

Fixture wheels are installed into a real temporary venv; the scripted stub runs as an owned process group; the
complete frozen questionnaire (5,852 calls) runs through the controller; evidence is finalized and evaluated
independently. Scripted CPU evidence only: never GPU or model evidence, and scripted labels are not results."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from scripts.evaluate_progress_subgoal_v1_runtime2 import evaluate_output
from tests import psv1r2_fixtures as FX

ROOT = Path(__file__).resolve().parents[1]
ENABLED = os.environ.get('PSV1R2_REHEARSALS') == '1' and sys.platform == 'linux'


@unittest.skipUnless(ENABLED, 'set PSV1R2_REHEARSALS=1 on Linux to run the full HTTP rehearsals')
class Rehearsals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        cls.base = Path(tempfile.mkdtemp(prefix='psv1r2-rehearsal-', dir=Path.home()))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)

    def scenario(self, name, fault='none', policy='scripted'):
        from research.progress_subgoal_v1_runtime2.rehearsal import scenario
        result, protocol = scenario(ROOT, self.base / name, fault, policy)
        value = evaluate_output(self.base / name / 'evidence', mode='rehearsal', root=ROOT, protocol=protocol)
        self.assertEqual(result['evidence_class'], 'scripted_cpu_rehearsal')
        self.assertFalse(result['gpu_compatibility_evidence'])
        self.assertTrue(result['cleanup_verified'], result.get('cleanup'))
        self.assertTrue(result['cleanup']['server']['groups_absent'])
        self.assertTrue(result['lifecycle_deadline']['met'])
        self.assertLessEqual(result['ledger']['issued'], protocol['limits']['maximum_model_requests'])
        self.assertTrue(result['stages']['gpu'].startswith('not_exercised'))
        return result, protocol, value

    def test_nominal_complete_questionnaire_and_independent_reproduction(self):
        result, protocol, value = self.scenario('nominal')
        self.assertTrue(result['passed'], result.get('error'))
        self.assertEqual(result['questionnaire']['counts'], {'answered': 5852})
        self.assertEqual(result['ledger']['issued'], 11 + 5852)
        self.assertTrue(value['technically_complete'], (value['lifecycle_errors'], value['call_errors']))
        # The independent scorer reproduces, from the retained replies, the scores of the stub's scripted answers.
        from tests.test_progress_subgoal_v1_runtime2_evaluator import offline
        self.assertEqual(value['analysis'], offline('scripted'))
        retained = [json.loads(json.loads(p.read_bytes())['response'])['choices'][0]['message']['content']
                    for p in sorted((self.base / 'nominal/evidence/questionnaire/calls').iterdir())]
        self.assertEqual(retained, [c for c, _ in FX.scripted_contents('scripted')])

    def test_timeout_is_cancelled_verified_idle_and_left_missing(self):
        result, protocol, value = self.scenario('timeout', 'timeout_once')
        self.assertTrue(result['passed'], result.get('error'))
        self.assertEqual(value['run']['counts'], {'answered': 5851, 'timed_out': 1})
        self.assertEqual(value['call_errors'], [])
        self.assertEqual(value['gate_status'], 'incomplete')
        self.assertFalse(value['technically_complete'])

    def test_stop_rules_end_the_run_and_cleanup_still_runs(self):
        for name, fault, stop in (('consecutive', 'consecutive_timeouts', 'consecutive_timeouts'),
                                  ('not-idle', 'not_idle', 'transport_failure'),
                                  ('http-error', 'http_error', 'transport_failure')):
            result, protocol, value = self.scenario(name, fault)
            self.assertFalse(result['passed'])
            self.assertEqual(result['failed_stage'], 'questionnaire')
            self.assertEqual(value['run']['stop_reason'], stop)
            self.assertFalse(value['technically_complete'])
            self.assertEqual(set(value['gate'].values()), {'incomplete'})

    def test_admission_cutoff_cuts_the_schedule_and_the_verdict_is_incomplete(self):
        result, protocol, value = self.scenario('cutoff', 'admission_cutoff')
        self.assertEqual(result['questionnaire']['stop_reason'], 'admission_cutoff')
        self.assertLess(result['questionnaire']['calls_recorded'], 5852)
        self.assertEqual(value['call_errors'], [])
        self.assertEqual(value['gate_status'], 'incomplete')
        self.assertFalse(value['technically_complete'])

    def test_prompt_token_mismatch_against_the_frozen_audit_is_caught(self):
        result, protocol, value = self.scenario('mismatch', 'token_mismatch')
        self.assertTrue(any('token audit' in e for e in value['call_errors']))
        self.assertFalse(value['technically_complete'])


if __name__ == '__main__':
    unittest.main()
