# Derived from tests/ws3q_diagnostics_module_fixture.py by scripts/derive_progress_subgoal_v1.py; edit the derivation, not this file.
"""A module whose setUpModule fails, for the diagnostics-recorder regressions (never discovered)."""
import unittest


def setUpModule():
    raise RuntimeError('deliberate setUpModule failure')


class NeverRuns(unittest.TestCase):
    def test_never_runs(self):
        self.fail('must not run')
