# Derived from tests/ecv_diagnostics_fixtures.py by scripts/derive_evidence_comprehension_v2.py; edit the derivation, not this file.
"""Deliberately failing suites for the diagnostics-recorder regressions (not a test module; never discovered)."""
import unittest


class Passes(unittest.TestCase):
    def test_passes(self):
        self.assertTrue(True)


class SetUpClassFails(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raise RuntimeError('deliberate setUpClass failure')

    def test_never_runs(self):
        self.fail('must not run')


class TearDownClassFails(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        raise RuntimeError('deliberate tearDownClass failure')

    def test_passes_before_teardown(self):
        self.assertTrue(True)


class NestedThenRecords(unittest.TestCase):
    """Runs nested diagnostics (one normal, one interrupted), then records a rehearsal in the outer run."""
    observed = {}

    def test_a_nested_runs(self):
        import os
        import tempfile
        from scripts.check_evidence_comprehension_v2 import run_suites
        outer = (os.environ.get('ECV2_DIAGNOSTICS_LOG'), os.environ.get('ECV2_CURRENT_TEST'))
        with tempfile.TemporaryDirectory() as folder:
            run_suites({'inner': 'tests.ecv2_diagnostics_fixtures.Passes'}, 'nested', folder)

            class Interrupting:
                def run(self, suite):
                    raise KeyboardInterrupt
            try:
                run_suites({'inner': 'tests.ecv2_diagnostics_fixtures.Passes'}, 'nested-interrupted', folder,
                           runner_factory=Interrupting)
            except KeyboardInterrupt:
                pass
        NestedThenRecords.observed['after_nested'] = (os.environ.get('ECV2_DIAGNOSTICS_LOG'),
                                                      os.environ.get('ECV2_CURRENT_TEST'))
        NestedThenRecords.observed['before_nested'] = outer

    def test_b_records_rehearsal(self):
        import tempfile
        from pathlib import Path
        from tests.test_evidence_comprehension_v2_connected import record_rehearsal
        record_rehearsal('outer_fault_after_nested_runs', 480, Path(tempfile.gettempdir()) / 'outer-evidence',
                         {'study_status': 'failed'}, None, None)
