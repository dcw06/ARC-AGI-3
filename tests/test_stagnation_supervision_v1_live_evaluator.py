"""Stagnation supervision v1 (Track 3): the independent evaluator replays CPU rehearsal evidence and catches tampering.

The rehearsal is the GPU-disabled closed loop with the scripted fake server and a scripted 16x16 game. No model."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from research.stagnation_supervision_v1 import thresholds as S
from research.stagnation_supervision_v1.closed_loop import bridge as B, evaluate as EV, fake_server as F
from research.stagnation_supervision_v1.closed_loop import runner as R, service as SVC
from research.stagnation_supervision_v1.closed_loop.evidence import load_verified
from tests.test_stagnation_supervision_v1_closed_loop import ScriptedAdapter

TRIGGER = S.load()
SPEC = R.protocol()


def rehearse(folder, order, faults=(), event=None, at=None):
    adapter = ScriptedAdapter('scripted-0000', event, at)
    spec = {**SPEC, 'cases': [{'game_id': 'scripted-0000', 'environment_seed': 0, 'initial_available_actions': [1, 2, 6],
                               'initial_canonical_hash': adapter.obs(full_reset=True).canonical_hash, 'win_levels': 8}],
            'schedule': [{'block': 1, 'pair_id': 's1', 'game_id': 'scripted-0000', 'order': order}]}
    report = R.run(Path(folder) / 'run', SVC.LocalService(F.FakeModelServer(faults)),
                   lambda g, arm, eid: ScriptedAdapter(g, event, at), spec=spec, deadline_seconds=3000,
                   supervision_factory=B.supervision_factory(spec, TRIGGER, token_counter=B.fixture_token_counter()))
    return spec, report


class Replay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.tmp.name) / 'clean'
        cls.spec, cls.report = rehearse(cls.folder, ['continuation', 'periodic', 'triggered'])
        cls.result = EV.evaluate_output(cls.folder / 'run', cls.spec)
        cls.loaded = load_verified(cls.folder / 'run')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_clean_rehearsal_replays_without_disagreement(self):
        r = self.result
        self.assertEqual(r['problems'], [])
        self.assertTrue(r['evidence_verified'])
        self.assertTrue(r['technically_complete'])
        self.assertEqual(r['admitted_groups'], ['s1'])
        self.assertEqual(set(r['recovery']), {'continuation', 'periodic', 'triggered'})
        self.assertGreaterEqual(r['recovery']['continuation']['opportunities'], 1)  # measurable without reflection
        cost = r['realised_cost']['by_arm']
        self.assertEqual(cost['continuation']['calls'], 0)
        self.assertEqual(cost['periodic']['calls'], 3)
        self.assertIn('equal budget', r['realised_cost']['note'])
        self.assertIn(r['false_interruptions']['triggered']['status'],
                      ('not_certifiable_minimum_not_met', 'within_provisional_cap', 'exceeds_provisional_cap'))

    def tamper(self, change):
        report = copy.deepcopy(self.loaded)
        change(report)
        return EV.evaluate_report(report, self.spec)['problems']

    def episode(self, report, arm):
        return next(e for e in report['episodes'] if e['arm'] == arm)

    def test_a_changed_supervision_decision_is_found(self):
        def change(report):
            events = self.episode(report, 'periodic')['supervision']['events']
            events[9]['outcome'] = 'suppressed_cooldown'
        self.assertTrue(any('supervision decision differs' in p for p in self.tamper(change)))

    def test_a_suggestion_smuggled_into_continuation_is_found(self):
        def change(report):
            episode = self.episode(report, 'continuation')
            call = episode['calls'][5]
            payload = json.loads(call['request']['messages'][1]['content'])
            payload[B.SUGGESTION_FIELD] = {'label': B.SV.SUGGESTION_LABEL, 'text': 'x', 'issued_after_action': 4,
                                           'expires_after_action': 14}
            call['request']['messages'][1]['content'] = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        self.assertTrue(any('suggestion block differs' in p for p in self.tamper(change)))

    def test_a_shown_suggestion_that_was_never_delivered_is_found(self):
        def change(report):
            step = self.episode(report, 'triggered')['steps'][-1]
            step['suggestion_shown'] = {'label': 'x'}
        self.assertTrue(any('suggestion shown differs' in p for p in self.tamper(change)))

    def test_altered_or_missing_reflection_evidence_is_found(self):
        def altered(report):
            row = self.episode(report, 'periodic')['reflections'][0]
            row['response'] = row['response'].replace('Take', 'Make')
        problems = self.tamper(altered)
        self.assertTrue(any('response hash' in p for p in problems))

        def removed(report):
            self.episode(report, 'periodic')['reflections'].pop()
        self.assertTrue(self.tamper(removed))

    def test_tampered_files_fail_evidence_verification(self):
        target = next((self.folder / 'run' / 'episodes').glob('*.json'))
        copy_dir = Path(self.tmp.name) / 'tampered'
        import shutil
        shutil.copytree(self.folder / 'run', copy_dir)
        path = copy_dir / 'episodes' / target.name
        path.write_bytes(path.read_bytes().replace(b'"status"', b'"statuS"', 1))
        result = EV.evaluate_output(copy_dir, self.spec)
        self.assertEqual((result['evidence_verified'], result['technically_complete']), (False, False))


class FaultedRehearsals(unittest.TestCase):
    def test_invalid_completions_failed_calls_and_game_over_replay_cleanly(self):
        for kwargs in ({'order': ['periodic'], 'faults': ('reflection_length',)},
                       {'order': ['periodic'], 'faults': ('reflection_exception',)},
                       {'order': ['triggered'], 'event': 'game_over', 'at': 13}):
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}), tempfile.TemporaryDirectory() as folder:
                spec, report = rehearse(folder, **kwargs)
                result = EV.evaluate_output(Path(folder) / 'run', spec)
                self.assertEqual(result['problems'], [])
                self.assertTrue(result['technically_complete'])

    def test_a_technical_failure_is_never_technically_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            spec, report = rehearse(folder, ['triggered'], faults=('reflection_audit_mismatch',))
            result = EV.evaluate_output(Path(folder) / 'run', spec)
            self.assertEqual(report['status'], 'technical_failure')
            self.assertFalse(result['technically_complete'])
            self.assertEqual(result['admitted_groups'], [])


if __name__ == '__main__':
    unittest.main()
