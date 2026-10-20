"""New schedule/transport integration checks, using synthetic dependencies."""
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tests.action_effect_pilot_fixture import create, checkpoints, protocol_patches
from research.action_effect_choice_live_v2.live_worker import request_plan, study, DurableLedger
from certification.direct_publisher_smoke_v1.accounting import Clock


class WorkerChecks(unittest.TestCase):
    def test_plan_is_9_unique_requests(self):
        rows = checkpoints()
        self.assertEqual(len(request_plan(rows)), 9)
        with self.assertRaises(ValueError): request_plan(rows+[rows[0]])

    def test_complete_worker_has_no_reference_branches(self):
        with tempfile.TemporaryDirectory() as folder:
            _, out, sent = create(folder)
            result = json.loads((out/'worker-result.json').read_bytes())
            self.assertEqual((result['bootstrap_attempts'], result['dispatch_attempts'], result['closed_scorecards']), (4, 16, 4))
            self.assertEqual(result['ledger']['issued'], 9)
            self.assertEqual(len(sent), 9)
            self.assertEqual(len(result['conditions']), 4)
            self.assertFalse(result['lifecycle_certified'])

    def test_invalid_answer_stops_condition_retains_denominator(self):
        with tempfile.TemporaryDirectory() as folder:
            _, out, _ = create(folder, invalid=True)
            result = json.loads((out/'worker-result.json').read_bytes())
            self.assertEqual(result['ledger']['issued'], 5)
            self.assertEqual(result['dispatch_attempts'], 8)
            self.assertEqual(result['closed_scorecards'], 4)
            self.assertTrue(all(c['reason'] == 'invalid_answer' for c in result['conditions']))

    def test_token_ceiling_refuses_before_HTTP(self):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root = Path(folder); (root/'in').mkdir(); (root/'out').mkdir()
            (root/'in/checkpoints.json').write_text(json.dumps({'checkpoints': checkpoints()}))
            from research.action_effect_choice_v2.interface import candidates
            (root/'in/candidate-pairs.json').write_text(json.dumps([dict(checkpoint_id=cp['checkpoint_id'],candidates=candidates(cp,i)) for i,cp in enumerate(checkpoints())]))
            protocol_patches(stack)
            call = stack.enter_context(patch('research.action_effect_choice_live_v2.live_worker.Client.call'))
            with self.assertRaisesRegex(ValueError, 'prompt-token budget'):
                study({'inputs': root/'in', 'input_manifest_sha256': 'x', 'started': time.monotonic(), 'port': 1},
                      root/'out', token_audit=lambda _: 8193)
            call.assert_not_called()

    def test_durable_admission_cannot_cross_deadline(self):
        ticks = [0]
        clock = Clock({'internal_seconds': 3300, 'admission_cutoff_seconds': 3000}, 0, now=lambda: ticks[0])
        ledger = DurableLedger(request_plan(checkpoints()), clock, lambda _: ticks.__setitem__(0, 3000))
        with self.assertRaises(TimeoutError): ledger.admit('canary')
