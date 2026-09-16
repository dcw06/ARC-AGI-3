"""Preparation regressions using actual offline ls20; never GPU evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent.framework_adapter import LocalFrameworkAdapter
from certification.phase4_v1.lifecycle import (IsolatedInference, evaluate_local_record,
                                              validate_freeze)
from certification.phase4_v1.local_probe import probe


class LifecycleTests(unittest.TestCase):
    def test_frozen_workload(self):
        c, rows = validate_freeze()
        self.assertEqual(len(rows), 110)
        self.assertEqual(len({r['client_id'] for r in rows}), 110)
        self.assertEqual(len({r['game_id'] for r in rows}), 15)
        self.assertTrue(all(r['max_actions'] == 80 and r['request_seed'] == 0 for r in rows))
        self.assertFalse(c['phase4_complete'])

    def test_missing_bindings_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'certification/phase4_v1'
            p.mkdir(parents=True)
            (p / 'lock.json').write_text('{"bindings": {}}')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                validate_freeze(Path(folder))

    def test_queue_identity_is_opaque(self):
        class Executor:
            def execute(self, **kwargs):
                return kwargs
        a = IsolatedInference(Executor(), 'opaque-a')
        b = IsolatedInference(Executor(), 'opaque-b')
        self.assertEqual(a.execute(client_id='same-game')['client_id'], 'opaque-a')
        self.assertEqual(b.execute(client_id='same-game')['client_id'], 'opaque-b')

    def test_actual_environment_dispatch(self):
        value = probe()
        self.assertTrue(value['evaluation']['passed'], value)
        self.assertEqual(value['record']['result']['inference_completions'], 2)
        self.assertFalse(value['evaluation']['model_inference'])

    def test_actual_environment_fallback(self):
        value = probe('policy_error')
        self.assertTrue(value['evaluation']['passed'], value)
        self.assertEqual(value['record']['result']['policy_failures'], 2)

    def test_cancel_after_completion_prevents_actual_dispatch(self):
        value = probe('cancel')
        self.assertTrue(value['evaluation']['passed'], value)
        self.assertEqual(value['record']['result']['acknowledged_actions'], 0)

    def test_missing_policy_still_finalizes(self):
        with patch('certification.phase4_v1.local_probe.E1Policy', return_value=None):
            value = probe()
        self.assertFalse(value['evaluation']['passed'])
        self.assertEqual(value['record']['finalization_status'], 'acknowledged_local_framework')
        self.assertTrue(value['record']['client_closed'])

    def test_factory_exception_still_finalizes(self):
        with patch('certification.phase4_v1.local_probe.E1Policy', side_effect=ValueError('factory')):
            value = probe()
        self.assertFalse(value['evaluation']['passed'])
        self.assertEqual(value['record']['finalization_status'], 'acknowledged_local_framework')

    def test_close_exception_never_passes(self):
        with patch.object(LocalFrameworkAdapter, 'close_scorecard', side_effect=OSError('close')):
            value = probe()
        self.assertFalse(value['evaluation']['passed'])
        self.assertEqual(value['record']['finalization_status'], 'unknown')

    def test_empty_receipt_never_passes(self):
        with patch.object(LocalFrameworkAdapter, 'close_scorecard', return_value={'result': None}):
            value = probe()
        self.assertFalse(value['evaluation']['passed'])

    def test_missing_journal_or_wrong_receipt_never_passes(self):
        value = probe()['record']
        bad = copy.deepcopy(value)
        bad['client_journal'] = []
        self.assertFalse(evaluate_local_record(bad)['passed'])
        bad = copy.deepcopy(value)
        bad['scorecard_receipt']['card_id'] = 'different-card'
        self.assertFalse(evaluate_local_record(bad)['passed'])


if __name__ == '__main__':
    unittest.main()
