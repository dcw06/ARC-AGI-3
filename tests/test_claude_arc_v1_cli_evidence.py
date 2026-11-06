"""Exercise real CLI evidence setup with scripted model/ARC clients; no network."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.claude_arc_v1 import audit, cli, run
from tests.test_claude_arc_v1 import FakeArc, FakeBackend, settings


class CLIEvidence(unittest.TestCase):
    def test_live_cli_source_inventory_survives_and_record_audit_passes(self):
        root = Path(__file__).resolve().parents[1]
        private = root / '.cache/claude_arc_runs'
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private) as directory:
            folder = Path(directory)
            config = settings()
            configuration = folder / 'config.json'
            configuration.write_text(json.dumps(config.public()))
            output = folder / 'attempt'
            arc = FakeArc()
            backend = FakeBackend(config)
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'synthetic-only', 'ARC_API_KEY': 'synthetic-only'}), \
                    patch('research.claude_arc_v1.backends.APIBackend', return_value=backend), \
                    patch('research.claude_arc_v1.arc.make_adapter', return_value=arc), \
                    patch('socket.create_connection', side_effect=AssertionError('no network')), \
                    patch('builtins.print'):
                code = cli.main(['--config', str(configuration), '--execute', '--confirm-paid-api',
                                 '--confirm-online-arc', '--output', str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(arc.opened, 1)
            self.assertEqual(arc.closed, 1)
            first = json.loads((output / 'events.jsonl').read_text().splitlines()[0])
            self.assertEqual(first['kind'], 'source_bindings')
            self.assertIsInstance(first['sha256'], str)
            self.assertEqual(first['files_sha256']['research/claude_arc_v1/cli.py'],
                             hashlib.sha256((root / 'research/claude_arc_v1/cli.py').read_bytes()).hexdigest())
            self.assertEqual(audit.audit(output)['actions_acknowledged'], 1)

    def test_reserved_fields_refuse_before_advancing_or_writing_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = run.Evidence(Path(directory) / 'events')
            try:
                for field in ('sha256', 'previous_sha256', 'sequence'):
                    with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'reserved'):
                        evidence.write('source_bindings', **{field: {'file': 'digest'}})
                    self.assertEqual(evidence.sequence, 0)
                    self.assertEqual(evidence.previous, '0' * 64)
                    self.assertEqual(evidence.path.read_bytes(), b'')
                evidence.write('source_bindings', files_sha256={'file': 'digest'})
                event = json.loads(evidence.path.read_text())
                expected = event.pop('sha256')
                self.assertEqual(hashlib.sha256(json.dumps(event, sort_keys=True,
                    separators=(',', ':'), allow_nan=False).encode()).hexdigest(), expected)
            finally:
                evidence.close()


if __name__ == '__main__':
    unittest.main()
