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
