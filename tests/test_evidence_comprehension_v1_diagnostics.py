"""Diagnostics recorder regressions (review of adf3b9d): fixture errors, runner exceptions, incomplete suites."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_evidence_comprehension_v1 import run_suites

FIXTURES = 'tests.ecv_diagnostics_fixtures'


def saved(directory, run_id):
    return json.loads((Path(directory) / f'{run_id}.json').read_bytes())


class Recorder(unittest.TestCase):
    def run_record(self, suites, **kwargs):
        with tempfile.TemporaryDirectory() as folder:
            returned = run_suites(suites, 'regression', folder, **kwargs)
            return returned, saved(folder, 'regression')

    def test_reviewer_case_setupclass_error_after_a_passing_suite(self):
        returned, record = self.run_record({'first': FIXTURES + '.Passes', 'second': FIXTURES + '.SetUpClassFails'})
        self.assertEqual(returned, record)
        self.assertFalse(record['all_passed'])
        self.assertEqual(list(record['suites']), ['first', 'second'])  # both suites retained
        second = record['suites']['second']
        self.assertTrue(second['completed'])
        self.assertFalse(second['passed'])
        fixture = [t for t in second['tests'] if t.get('kind') == 'fixture']
        self.assertEqual(len(fixture), 1)
        self.assertEqual(fixture[0]['outcome'], 'error')
        self.assertIn('deliberate setUpClass failure', fixture[0]['detail'])
        self.assertIn('setUpClass', fixture[0]['test'])
        self.assertNotIn('TypeError', json.dumps(record))  # the recorder no longer crashes

    def test_setupmodule_and_teardownclass_errors_are_retained(self):
        for suites, message in (({'module': 'tests.ecv_diagnostics_module_fixture'}, 'deliberate setUpModule failure'),
                                ({'teardown': FIXTURES + '.TearDownClassFails'}, 'deliberate tearDownClass failure')):
            with self.subTest(message=message):
                _, record = self.run_record(suites)
                self.assertFalse(record['all_passed'])
                suite = next(iter(record['suites'].values()))
                fixture = [t for t in suite['tests'] if t.get('kind') == 'fixture']
                self.assertTrue(fixture and message in fixture[0]['detail'])
        _, record = self.run_record({'teardown': FIXTURES + '.TearDownClassFails'})
        passed = [t for t in record['suites']['teardown']['tests'] if t.get('kind') != 'fixture']
        self.assertEqual([t['outcome'] for t in passed], ['success'])  # the test itself still recorded

    def test_runner_exception_is_retained_and_later_suites_still_run(self):
        calls = []

        class Exploding:
            def run(self, suite):
                raise OSError('deliberate runner failure')

        def factory():
            calls.append(1)
            return Exploding() if len(calls) == 1 else unittest.TextTestRunner(
                verbosity=0, resultclass=__import__('scripts.check_evidence_comprehension_v1',
                                                    fromlist=['Recorder']).Recorder)
        _, record = self.run_record({'broken': FIXTURES + '.Passes', 'after': FIXTURES + '.Passes'},
                                    runner_factory=factory)
        self.assertFalse(record['all_passed'])
        self.assertFalse(record['suites']['broken']['completed'])
        self.assertIn('deliberate runner failure', record['suites']['broken']['runner_exception'])
        self.assertTrue(record['suites']['after']['completed'] and record['suites']['after']['passed'])

    def test_interrupted_run_saves_an_incomplete_record_then_reraises(self):
        class Interrupting:
            def run(self, suite):
                raise KeyboardInterrupt

        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(KeyboardInterrupt):
                run_suites({'first': FIXTURES + '.Passes', 'second': FIXTURES + '.Passes'}, 'interrupted', folder,
                           runner_factory=Interrupting)
            record = saved(folder, 'interrupted')
        self.assertFalse(record['all_passed'])
        self.assertEqual(record['requested_suites'], ['first', 'second'])
        self.assertEqual(list(record['suites']), ['first'])  # the second never ran: not success

    def test_all_requested_suites_passing_is_success(self):
        _, record = self.run_record({'one': FIXTURES + '.Passes', 'two': FIXTURES + '.Passes'})
        self.assertTrue(record['all_passed'])
        self.assertTrue(all(s['completed'] for s in record['suites'].values()))


if __name__ == '__main__':
    unittest.main()
