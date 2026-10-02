"""Stagnation supervision v1 (Track 3): the independent evaluator replays CPU rehearsal evidence and catches tampering.

The rehearsal is the GPU-disabled closed loop with the scripted fake server and a scripted 16x16 game. No model."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.stagnation_supervision_v1 import intervention as I, thresholds as S
from research.stagnation_supervision_v1.closed_loop import bridge as B, evaluate as EV, fake_server as F
from research.stagnation_supervision_v1.closed_loop import runner as R, service as SVC
from research.stagnation_supervision_v1.closed_loop.evidence import RunEvidence, load_verified
from tests.test_stagnation_supervision_v1_closed_loop import ScriptedAdapter

TRIGGER = S.load()
SPEC = R.protocol()


def rehearse(folder, order, faults=(), event=None, at=None, server=None):
    adapter = ScriptedAdapter('scripted-0000', event, at)
    spec = {**SPEC, 'cases': [{'game_id': 'scripted-0000', 'environment_seed': 0, 'initial_available_actions': [1, 2, 6],
                               'initial_canonical_hash': adapter.obs(full_reset=True).canonical_hash, 'win_levels': 8}],
            'schedule': [{'block': 1, 'pair_id': 's1', 'game_id': 'scripted-0000', 'order': order}]}
    report = R.run(Path(folder) / 'run', SVC.LocalService(server or F.FakeModelServer(faults)),
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

    def disk_mutation(self, change):
        """Re-sign a changed run as valid disk evidence, then check semantic replay."""
        report = copy.deepcopy(self.loaded)
        change(report)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'run'
            writer = RunEvidence(path)
            for episode in report['episodes']:
                writer(path / 'episodes' / (episode['episode_id'] + '.json'), episode)
            writer(path / 'run.json', R.index_view(report))
            result = EV.evaluate_output(path, self.spec)
        self.assertTrue(result['evidence_verified'], result['problems'])
        self.assertFalse(result['technically_complete'], result['problems'])
        self.assertTrue(result['problems'], 'semantic mutation produced no evaluator problems')
        return result['problems']

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

    def test_re_signed_incomplete_or_reordered_inventory_is_rejected(self):
        def erased(report):
            report['pairs'].clear()
            report['episodes'].clear()
            for field in ('calls', 'dispatches', 'prompt_tokens', 'completion_tokens',
                          'reflection_calls', 'reflection_prompt_tokens', 'reflection_completion_tokens'):
                report[field] = 0

        def duplicate(report):
            copy_episode = copy.deepcopy(report['episodes'][0])
            copy_episode['episode_id'] = 's1-extra-continuation'
            report['episodes'].append(copy_episode)

        mutations = (
            erased,
            lambda report: report['episodes'].pop(),
            duplicate,
            lambda report: report['episodes'].reverse(),
            lambda report: report['pairs'].clear(),
            lambda report: report['pairs'].append(copy.deepcopy(report['pairs'][0])),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                problems = self.disk_mutation(mutation)
                self.assertTrue(problems)

    def test_re_signed_cleanup_and_unjustified_stop_are_rejected(self):
        def cleanup(report):
            self.episode(report, 'periodic')['cleanup']['closed'] = False

        def stop(report):
            episode = self.episode(report, 'continuation')
            episode['status'] = 'complete'
            episode['stop_reason'] = 'win'  # no environment WIN or level completion exists

        for mutation in (cleanup, stop):
            with self.subTest(mutation=mutation.__name__):
                self.assertTrue(self.disk_mutation(mutation))

    def test_re_signed_policy_call_and_observation_tampering_is_rejected(self):
        def malformed(report):
            call = self.episode(report, 'continuation')['calls'][0]
            call['response'] = 'not-json'
            call['response_bytes'] = len(b'not-json')
            call['response_sha256'] = hashlib.sha256(b'not-json').hexdigest()

        def non_stop(report):
            self.episode(report, 'continuation')['calls'][0]['finish_reason'] = 'length'

        def negative_tokens(report):
            call = self.episode(report, 'continuation')['calls'][0]
            old = call['server_prompt_tokens']
            call['server_prompt_tokens'] = -1
            call['tokenizer_prompt_tokens'] = -1
            report['prompt_tokens'] -= old + 1  # aggregate still matches retained calls

        def action_mismatch(report):
            episode = self.episode(report, 'continuation')
            step = episode['steps'][0]
            other = 2 if step['action']['action_id'] != 2 else 1
            response = json.dumps({'action': {'action_id': other, 'action_data': {}}}, separators=(',', ':'))
            call = episode['calls'][step['call_index']]
            call['response'] = response
            call['response_bytes'] = len(response.encode())
            call['response_sha256'] = hashlib.sha256(response.encode()).hexdigest()

        def observation(report):
            call = self.episode(report, 'continuation')['calls'][0]
            request = call['request']
            payload = json.loads(request['messages'][1]['content'])
            grid = payload['observation']['current_grid']
            grid[0][0] = (grid[0][0] + 1) % 16
            request['messages'][1]['content'] = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            call['request_sha256'] = R.digest(request)

        for mutation in (malformed, non_stop, negative_tokens, action_mismatch, observation):
            with self.subTest(mutation=mutation.__name__):
                self.assertTrue(self.disk_mutation(mutation))

    def test_re_signed_missing_or_reused_policy_call_binding_is_rejected(self):
        def out_of_range(report):
            self.episode(report, 'continuation')['steps'][0]['call_index'] = 9999

        def reused(report):
            steps = self.episode(report, 'continuation')['steps']
            steps[1]['call_index'] = steps[0]['call_index']

        for mutation in (out_of_range, reused):
            with self.subTest(mutation=mutation.__name__):
                self.assertTrue(self.disk_mutation(mutation))

    def test_re_signed_reflection_request_cannot_discard_evidence(self):
        def discard(report):
            reflection = self.episode(report, 'periodic')['reflections'][0]
            reflection['request']['messages'][1]['content'] = I.PROMPT + '\n\nEvidence:\n{}'
            reflection['request_sha256'] = R.digest(reflection['request'])

        problems = self.disk_mutation(discard)
        self.assertTrue(any('reflection' in problem for problem in problems), problems)


class FaultedRehearsals(unittest.TestCase):
    def test_validly_retained_invalid_first_policy_output_is_not_a_technical_failure(self):
        class InvalidFirstPolicy(F.FakeModelServer):
            def _policy(self, request):
                return 'not-json'

        with tempfile.TemporaryDirectory() as folder:
            spec, report = rehearse(folder, ['continuation'], server=InvalidFirstPolicy())
            result = EV.evaluate_output(Path(folder) / 'run', spec)
            self.assertEqual(result['problems'], [])
            self.assertTrue(result['evidence_verified'])
            self.assertTrue(result['technically_complete'])
            self.assertEqual(report['episodes'][0]['stop_reason'], 'invalid_output')
            self.assertEqual(report['episodes'][0]['steps'], [])

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
