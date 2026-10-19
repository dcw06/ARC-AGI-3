"""Whole-schedule worker tests with fake transport/engines; no actual inference."""
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from research.feedback_probe_v1.live_worker import request_plan, study, DurableLedger
from research.feedback_probe_v1.interface import RECOGNITION_SYSTEM
from certification.direct_publisher_smoke_v1.accounting import Clock
from tests.feedback_probe_live_fixture import checkpoints, create, protocol_patches


class ProbeLiveWorkerChecks(unittest.TestCase):
    def test_frozen_maximum_and_duplicate_identity_refusal(self):
        rows = checkpoints()
        plan = request_plan(rows)
        self.assertEqual(len(plan), 73)
        self.assertEqual(sum(p['kind'] == 'recognition' for p in plan), 8)
        self.assertEqual(sum(p['kind'] == 'policy' for p in plan), 64)
        with self.assertRaises(ValueError):
            request_plan(rows+[rows[0]])

    def test_complete_worker_separates_recognition_and_counts_restoration(self):
        with tempfile.TemporaryDirectory() as folder:
            _, out, sent = create(folder)
            result = json.loads((out/'worker-result.json').read_bytes())
            self.assertEqual((result['bootstrap_attempts'], result['dispatch_attempts'], result['closed_scorecards']),
                             (16, 100, 16))
            self.assertEqual(result['ledger']['issued'], 73)
            self.assertEqual(len(result['recognition']), 8)
            self.assertEqual(len(result['continuations']), 16)
            self.assertFalse(result['lifecycle_certified'])
            # Recognition has a different system/schema; its answer is never
            # appended to a subsequent policy conversation.
            policies = [b for b in sent if b.get('max_tokens') == 256 and
                        b['messages'][0]['content'] != RECOGNITION_SYSTEM]
            self.assertEqual(len(policies), 64)
            self.assertTrue(all(len(b['messages']) == 2 for b in policies))

    def test_invalid_answers_are_retained_without_retry_or_hidden_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            _, out, _ = create(folder, invalid_recognition=True, invalid_policy=True)
            result = json.loads((out/'worker-result.json').read_bytes())
            self.assertEqual(result['ledger']['issued'], 25)
            self.assertEqual(result['dispatch_attempts'], 36)
            self.assertEqual(result['closed_scorecards'], 16)
            self.assertTrue(all(r['text'] == 'INVALID' for r in result['recognition']))
            self.assertTrue(all(r['reason'] == 'invalid_answer' for r in result['continuations']))

    def test_over_budget_native_count_refuses_before_HTTP_admission(self):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root = Path(folder); (root/'in').mkdir(); (root/'out').mkdir()
            (root/'in/checkpoints.json').write_text(json.dumps({'checkpoints': checkpoints()}))
            protocol_patches(stack)
            call = stack.enter_context(patch('research.feedback_probe_v1.live_worker.Client.call'))
            with self.assertRaisesRegex(ValueError, 'prompt-token budget'):
                study({'inputs': root/'in', 'input_manifest_sha256': 'x', 'started': time.monotonic(), 'port': 1},
                      root/'out', token_audit=lambda _: 8193)
            call.assert_not_called()
            result = json.loads((root/'out/worker-result.json').read_bytes())
            self.assertEqual(result['ledger']['issued'], 0)

    def test_late_durable_admission_cannot_send(self):
        now = [0]
        clock = Clock({'internal_seconds': 3300, 'admission_cutoff_seconds': 3000}, 0, now=lambda: now[0])
        plan = request_plan(checkpoints())
        ledger = DurableLedger(plan, clock, lambda _: now.__setitem__(0, 3000))
        with self.assertRaises(TimeoutError):
            ledger.admit('canary')
