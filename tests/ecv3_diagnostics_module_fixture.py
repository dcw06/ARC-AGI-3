# Derived from tests/ecv2_diagnostics_module_fixture.py by scripts/derive_evidence_comprehension_v3.py; edit the derivation, not this file.
"""A module whose setUpModule fails, for the diagnostics-recorder regressions (never discovered)."""
import unittest


def setUpModule():
    raise RuntimeError('deliberate setUpModule failure')


class NeverRuns(unittest.TestCase):
    def test_never_runs(self):
        self.fail('must not run')
