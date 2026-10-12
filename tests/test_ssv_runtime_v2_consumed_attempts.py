"""r10/r11 (fourth and fifth reviews): every consumed attempt id, failed or completed, is refused by the gate in either
session, and the gate requires the complete consumed-attempt history. Synthetic authority trees live only in temporary
directories."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from research.stagnation_supervision_runtime_v2 import authority as A
from tests import ssv_runtime_v2_fixtures as FX

CONSUMED = ('ssv1-r5-session1-reservation-001', 'ssv1rt2-s1-c5ebca7f7b444bb3b63b6c90b3cf306b',
            'ssv1rt2-s1r-994053875c1c4a6ea06ab09be3e9c4bc', 'ssv1rt2-s1a3-615924add9624c5abec34e9de3c52ed0')


class ConsumedAttempts(unittest.TestCase):
    def test_the_protocol_and_the_gate_record_every_consumed_attempt(self):
        protocol = json.loads((A.ROOT / A.PROTOCOL).read_bytes())
        self.assertEqual(protocol['consumed_attempts'], list(CONSUMED))
        self.assertEqual(A.REQUIRED_CONSUMED, frozenset(CONSUMED))

    def test_each_consumed_attempt_id_is_refused_by_the_gate_and_the_package_builder(self):
        from research.stagnation_supervision_runtime_v2.notebook import launch_artifacts
        for attempt in CONSUMED[1:]:  # the R6 id does not match the runtime v2 attempt pattern and is refused anyway
            with self.subTest(attempt=attempt), tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(FX, 'ATTEMPT', attempt):
                root = FX.authority_tree(Path(tmp) / 'root')
                with self.assertRaisesRegex(A.LiveRefused, 'attempt id invalid or already consumed'):
                    A.require_live(root)
                with self.assertRaises(A.LiveRefused):
                    launch_artifacts(root)
        with tempfile.TemporaryDirectory() as tmp:  # control: a fresh id passes the same synthetic gate
            root = FX.authority_tree(Path(tmp) / 'root')
            self.assertEqual(A.require_live(root)[1]['attempt_id'], FX.ATTEMPT)

    def test_the_completed_session_1_attempt_is_refused_for_session_2(self):
        from research.stagnation_supervision_runtime_v2.notebook import launch_artifacts
        from tests.test_ssv_runtime_v2_r2_gaps import session1_record
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(FX, 'ATTEMPT', CONSUMED[3]):
            root = FX.authority_tree(Path(tmp) / 'root', session='2', session1_evaluation=session1_record())
            with self.assertRaisesRegex(A.LiveRefused, 'attempt id invalid or already consumed'):
                A.require_live(root)
            with self.assertRaises(A.LiveRefused):
                launch_artifacts(root)
        with tempfile.TemporaryDirectory() as tmp:  # control: a fresh session-2 id with the same dependency passes
            root = FX.authority_tree(Path(tmp) / 'root', session='2', session1_evaluation=session1_record())
            self.assertEqual(A.require_live(root)[1]['session'], '2')

    def test_a_protocol_that_drops_a_consumed_attempt_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = FX.authority_tree(Path(tmp) / 'root')
            path = root / A.PROTOCOL
            protocol = json.loads(path.read_bytes())
            protocol['consumed_attempts'] = [a for a in protocol['consumed_attempts'] if a != CONSUMED[3]]
            path.write_text(json.dumps(protocol, indent=1, sort_keys=True) + '\n', encoding='utf-8')
            with self.assertRaisesRegex(A.LiveRefused, 'protocol unreadable'):
                A.require_live(root)


if __name__ == '__main__':
    unittest.main()
