"""A module whose setUpModule fails, for the diagnostics-recorder regressions (never discovered)."""
import unittest


def setUpModule():
    raise RuntimeError('deliberate setUpModule failure')


class NeverRuns(unittest.TestCase):
    def test_never_runs(self):
        self.fail('must not run')
