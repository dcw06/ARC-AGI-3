from pathlib import Path
import tempfile
import unittest

from certification.phase4_v6.clean_environment import CleanEnvironment


class BootstrapRepairTests(unittest.TestCase):
    def test_failure_preserves_real_stderr_and_named_stage(self):
        import json
        import sys
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runner = CleanEnvironment(root, root/'evidence')
            with self.assertRaisesRegex(RuntimeError, 'diagnostic_failure'):
                runner.execute('diagnostic_failure', [sys.executable, '-c',
                    "import sys; print('underlying bootstrap error',file=sys.stderr); sys.exit(7)"])
            self.assertIn('underlying bootstrap error', (root/'evidence/stages.log').read_text())
            stages = json.loads((root/'evidence/stages.json').read_text())
            self.assertFalse(stages[0]['passed'])
            self.assertEqual(stages[0]['stage'], 'diagnostic_failure')
            with self.assertRaisesRegex(ValueError, 'cannot be retried'):
                runner.execute('diagnostic_failure', [sys.executable, '-c', 'pass'])

    def test_existing_venv_and_unpinned_requirements_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runner = CleanEnvironment(root, root/'evidence')
            (root/'venv').mkdir()
            with self.assertRaises(FileExistsError):
                runner.bootstrap()
            with self.assertRaises(ValueError):
                runner.install('install', root, ['https://example.com/package.whl'])

    def test_expired_deadline_does_not_launch(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runner = CleanEnvironment(root, root/'evidence', seconds=0)
            with patch('certification.phase4_v6.clean_environment.command') as command:
                with self.assertRaises(RuntimeError):
                    runner.execute('already_expired', ['unused'])
                command.assert_not_called()
