"""Prospective limits, frozen inputs and interruption-safe derived live lifecycle."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha
from research.recent_feedback_v1.live_contract import check_cases, protocol, MAX_PROMPT_TOKENS
from research.recent_feedback_v1.live_evaluation import audit_transport
from research.recent_feedback_v1.live_runtime import finalize, check_authority
from research.recent_feedback_v1.live_worker import study, canary, request_plan

ROOT = Path(__file__).resolve().parents[1]


class RecentLive(unittest.TestCase):
    def test_derivations_and_design_are_frozen(self):
        from scripts.derive_recent_feedback_live_v1 import PINS, derive
        for name in PINS:
            self.assertEqual((ROOT/'research/recent_feedback_v1'/name).read_bytes(), derive(name))
        frozen = protocol()
        self.assertEqual(frozen['max_prompt_tokens_per_request'], 8192)
        self.assertEqual(frozen['comparison_protocol_sha256'], sha(ROOT/'research/recent_feedback_v1/protocol.json'))

    def test_case_drift_is_rejected(self):
        for cases in ([], [{}]*6, {'cases': []}):
            with self.assertRaises(ValueError):
                check_cases(cases)

    def test_request_schedule_and_no_authority(self):
        cases = [{'case_id': str(i), 'order': ['recent_raw', 'recent_summary']} for i in range(6)]
        self.assertEqual(len(request_plan(cases)), 289)
        self.assertEqual(len({r['id'] for r in request_plan(cases)}), 289)
        with self.assertRaises(PermissionError):
            check_authority(None, 'a'*64)

    def test_prompt_ceiling_refuses_before_any_HTTP_admission(self):
        for value in (True, 0, -1, MAX_PROMPT_TOKENS+1):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root/'cases.json').write_text('{"cases": []}')
                with patch('research.recent_feedback_v1.live_worker.check_cases'), patch(
                        'research.recent_feedback_v1.live_worker.Client.call') as call:
                    with self.assertRaises(ValueError):
                        study({'cases': str(root/'cases.json'), 'started': time.monotonic(), 'port': 1},
                              root, token_audit=lambda body: value)
                    call.assert_not_called()
                self.assertEqual((root/'transport.jsonl').read_bytes(), b'')
                result = json.loads((root/'worker-result.json').read_bytes())
                self.assertIsNotNone(result['error'])
                self.assertEqual(result['ledger']['issued'], 0)

    def test_independent_transport_rejects_over_budget_even_matching_reply(self):
        body = canary()
        def events(native):
            return [{'kind': 'HTTP_request', 'id': 'canary', 'body': body, 'native_prompt_tokens': native},
                    {'kind': 'HTTP_admission', 'id': 'canary', 'request_kind': 'canary', 'sequence': 1,
                     'method': 'POST', 'path': '/v1/chat/completions', 'issued_at': 1},
                    {'kind': 'HTTP_response', 'id': 'canary', 'status': 200, 'raw': json.dumps({
                        'model': body['model'], 'choices': [{'message': {'role': 'assistant', 'content': 'ok'},
                                                          'finish_reason': 'stop'}],
                        'usage': {'prompt_tokens': native, 'completion_tokens': 1, 'total_tokens': native+1}})}]
        self.assertEqual(len(audit_transport(events(8192), {'canary': body})[0]), 1)
        for value in (True, 0, -1, 8193):
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit_transport(events(value), {'canary': body})

    def test_finalization_remains_fail_closed_at_every_write(self):
        for interrupted_name in ('provisional-result.json', 'return-witness.json'):
            with self.subTest(name=interrupted_name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                emitted = []
                def writer(path, value):
                    path.write_text(json.dumps(value))
                    if path.name == interrupted_name:
                        raise KeyboardInterrupt('injected after write')
                with self.assertRaises(KeyboardInterrupt):
                    finalize(root, {'started_monotonic': 0, 'error': None}, deadline=60,
                             now=lambda: 59.9, writer=writer, emit=lambda *a, **k: emitted.append(a))
                self.assertFalse(json.loads((root/'provisional-result.json').read_bytes())['lifecycle_finalized'])
                self.assertEqual(emitted, [])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ticks = [59.9]
            def writer(path, value):
                path.write_text(json.dumps(value))
                ticks[0] = 60.1
            with self.assertRaises(TimeoutError):
                finalize(root, {'started_monotonic': 0, 'error': None}, deadline=60,
                         now=lambda: ticks[0], writer=writer)
            self.assertFalse((root/'return-witness.json').exists())


if __name__ == '__main__':
    unittest.main()
