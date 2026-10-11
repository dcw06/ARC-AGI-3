"""Successor replacement for the frozen R4 forced-cutoff assertion.

The original file remains byte-identical to the older packages which bind it.
Forced termination can leave either a verified partial snapshot (still marked
running), or interrupted evidence which must be rejected. Neither is complete.
"""
from pathlib import Path
import unittest

import test_stagnation_supervision_v1_connected as historical


class ForcedCutoffEvidence(unittest.TestCase):
    def test_interrupted_or_partial_evidence_is_never_complete(self):
        receipt, outer, host, evaluation, detail = historical.connected(
            'slow', seconds=340, admission_seconds=1, details=True)
        self.assertNotEqual(receipt['study_status'], 'study_complete_pending_independent_evaluation')
        self.assertFalse(evaluation['technically_complete'])
        self.assertFalse(evaluation['target_evaluation']['technically_complete'])
        historical.Connected.assert_owned_cleanup(self, receipt, outer, detail)
        self.assertIsNotNone(detail['run'])
        self.assertGreater(detail['run']['calls'], 0)
        self.assertIn('admission cutoff reserves cleanup', outer['error'])
        from research.stagnation_supervision_v1.closed_loop.evidence import EvidenceError, load_verified
        folder = Path(detail['output']) / 'worker/run'
        if not evaluation['evidence_verified']:
            with self.assertRaises(EvidenceError):
                load_verified(folder)
            self.assertTrue(any(p.startswith('run evidence:') for p in evaluation['problems']))
        else:
            retained = load_verified(folder)
            self.assertEqual(retained['calls'], detail['run']['calls'])
            self.assertGreater(sum(len(e['steps']) for e in retained['episodes']), 0)
            self.assertIn((retained['status'], retained['error']),
                          (('deadline_exceeded', 'run deadline enforced'),
                           ('technical_failure', 'model transport'), ('running', None)))
