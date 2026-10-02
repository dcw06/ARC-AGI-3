"""Stagnation supervision v1 (Track 3): CPU-only archive diagnostic of the frozen detector (descriptive only)."""
import json
import runpy
import unittest

from research.stagnation_supervision_v1 import archive_diagnostic as A, thresholds as S

STORED = json.loads(A.RESULTS.read_text(encoding='utf-8'))
FROZEN = {  # as pinned by the migration test, at 316573d
    'trigger_spec.json': '8dc8d9097d4764a3ecbe5185b3c8ec021d2ab15316e81f0515a67c3d9f6cd7d9',
    'detector.py': 'ee8b340cf69cd092e37508b86152da4b33073bbb9ab5caf833cef6ec6e931d62',
    'thresholds.py': '0a88196a13f74fd3ccb9a89441926ea54b5e3209b9589641b96461ffbfee3985',
}


class ArchiveDiagnostic(unittest.TestCase):
    def test_result_reproduces_from_the_locked_archive_with_the_frozen_detector(self):
        self.assertEqual(json.loads(A.encode(A.run())), STORED)
        self.assertEqual(STORED['frozen_files_sha256'], FROZEN)
        self.assertEqual(STORED['params'], S.load()['params'])
        self.assertEqual(STORED['view'], 'full_frame_unmasked')
        self.assertEqual(STORED['transitions'], 144)
        self.assertEqual(sorted(STORED['per_game']), ['ar25', 's5i5', 'wa30'])

    def test_result_is_write_once(self):
        with self.assertRaises(SystemExit):
            runpy.run_module('research.stagnation_supervision_v1.archive_diagnostic', run_name='__main__')

    def test_every_trigger_retains_its_evidence_and_signals(self):
        for episode in STORED['episodes']:
            for t in episode['triggers']:
                self.assertTrue(t['signals'])
                self.assertEqual(t['cited_evidence'], sorted({i for s in t['signals'] for i in s['evidence']}))
                self.assertEqual([f['action_index'] for f in t['trace']], t['cited_evidence'])
                self.assertIn(t['step'], episode['firing_steps'])

    def test_counts_are_consistent(self):
        for game, g in STORED['per_game'].items():
            episodes = [e for e in STORED['episodes'] if e['game'].startswith(game)]
            self.assertEqual(g['triggers'], sum(len(e['triggers']) for e in episodes))
            self.assertEqual(g['candidate_missed_patterns'], sum(len(e['candidate_missed_patterns']) for e in episodes))
            self.assertEqual(g['potential_false_interruptions'],
                             sum(t['potential_false_interruption'] for e in episodes for t in e['triggers']))

    def test_the_labels_are_declared_absent(self):
        self.assertIn('no independent stagnation labels', STORED['labels'])
        self.assertIn('before the detector was run on these traces', STORED['definitions'])


if __name__ == '__main__':
    unittest.main()
