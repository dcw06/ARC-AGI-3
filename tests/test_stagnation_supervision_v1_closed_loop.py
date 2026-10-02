"""Stagnation supervision v1 (Track 3): GPU-disabled closed-loop integration derived from action-effect-history v1.

Derivation drift, request contracts, the compute gate, and CPU fake-server rehearsals: the offline development
engine (ar25, all three arms) and a scripted adapter for faults and suggestion-block clearing. No model runs."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from research.stagnation_supervision_v1 import outcomes as O, supervision as SV, thresholds as S
from research.stagnation_supervision_v1.closed_loop import authority, bridge as B, contract as C, fake_server as F
from research.stagnation_supervision_v1.closed_loop import runner as R, service as SVC
from research.transition_evidence_v2 import transition as T2
from scripts import derive_stagnation_supervision_v1 as DERIVE

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'notebooks/action-effect-history-v1-review-r3/review-source-lock.json'
TRIGGER = S.load()
SPEC = R.protocol()


def episode_bodies(folder, report):
    return [json.loads((Path(folder) / 'episodes' / (e['episode_id'] + '.json')).read_text()) for e in report['episodes']]


def records_of(body):
    return T2.history([B.raw_transition(body['episode_id'], s) for s in body['steps']])


class Derivation(unittest.TestCase):
    def test_derived_files_match_the_derivation(self):
        self.assertEqual(DERIVE.stale(), [])

    def test_sources_are_the_reviewed_action_effect_history_files(self):
        bound = json.loads(LOCK.read_bytes())['bindings']
        manifest = DERIVE.verify_source_bindings()
        self.assertEqual(hashlib.sha256(LOCK.read_bytes()).hexdigest(),
                         manifest['historical_review_lock_sha256'])
        self.assertEqual(set(manifest['sources']), {DERIVE.src(target) for target in DERIVE.DERIVED})
        for target in DERIVE.DERIVED:
            source = DERIVE.src(target)
            entry = manifest['sources'][source]
            self.assertEqual(hashlib.sha256((ROOT / source).read_bytes()).hexdigest(), entry['sha256'], source)
            if source == 'scripts/rehearse_action_effect_history_v1.py':
                self.assertNotIn(source, bound)
                self.assertEqual(entry['provenance'], 'supplementary_source_review')
            else:
                self.assertEqual(entry['sha256'], bound[source], source)
                self.assertEqual(entry['provenance'], 'historical_review_lock')

    def test_counted_substitutions(self):
        base = 'research/stagnation_supervision_v1/closed_loop/'
        self.assertEqual(DERIVE.substitution_counts(), {
            base + 'contract.py': 6, base + 'runner.py': 21, base + 'engine.py': 0, base + 'evidence.py': 0,
            base + 'model_service.py': 6, base + 'host.py': 9, base + 'worker.py': 9, base + 'resources.py': 2,
            base + 'monitor.py': 1, base + 'supervisor.py': 13, base + 'authority.py': 10,
            'scripts/stagnation_supervision_v1_launch.py': 15, 'scripts/rehearse_stagnation_supervision_v1.py': 6})

    def test_live_mode_is_disabled_in_this_source_revision(self):
        from research.stagnation_supervision_v1.closed_loop import authority as A
        self.assertIs(A.LIVE_DISABLED, True)
        with self.assertRaises(PermissionError):
            A.require()
        self.assertEqual(set(A.SESSION_LIMITS), {'1', '2'})
        for limits in A.SESSION_LIMITS.values():
            self.assertEqual((limits['automatic_retries'], limits['holdout_runs'], limits['maximum_attempts']), (0, 0, 1))

    def test_runner_raw_transitions_match_the_replay_mapping(self):
        spec = importlib.util.spec_from_file_location('replay', ROOT / 'scripts/replay_transition_evidence_v1.py')
        replay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(replay)
        before = {'frames': [[[0, 1], [2, 3]]], 'levels_completed': 0, 'state': 'NOT_FINISHED', 'full_reset': False}
        for status, extra in (('acknowledged', {'after': before}), ('dispatch_failed', {'error': 'rejected'}),
                              ('outcome_unknown', {})):
            step = {'index': 3, 'before': before, 'action': {'action_id': 1, 'action_data': {}}, 'status': status,
                    **extra}
            self.assertEqual(B.raw_transition('e', step),
                             replay.raw_step('e', step, None, 'offline_development_engine'))

    def test_no_track_module_touches_the_masked_view(self):
        import ast
        for path in sorted((ROOT / 'research/stagnation_supervision_v1').rglob('*.py')):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in node.names] + [getattr(node, 'module', None) or '']
                    self.assertFalse(any('mask' in n for n in names), path)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    self.assertNotIn(node.value, ('masked', 'masks', 'mask'), path)


class Contracts(unittest.TestCase):
    def setUp(self):
        from agent.state import GameRuntimeState, Observation
        from arcengine import GameState
        frame = np.zeros((64, 64), dtype=np.uint8)
        obs = Observation('ar25-0c556536', (frame,), GameState.NOT_FINISHED, 0, 8, 'g', (1, 2, 6), True)
        self.runtime = GameRuntimeState(obs, action_budget_limit=40)
        self.block = {'label': SV.SUGGESTION_LABEL, 'text': 'Reflection: try action 1.', 'issued_after_action': 4,
                      'expires_after_action': 14, 'record_id': 'x#4'}

    def test_the_suggestion_sits_beside_the_observation_and_strips_to_the_continuation_request(self):
        plain = C.policy_request(self.runtime, 'continuation')
        with_block = C.policy_request(self.runtime, 'triggered', self.block)
        payload = json.loads(with_block['messages'][1]['content'])
        self.assertEqual(set(payload), {'observation', B.SUGGESTION_FIELD})
        self.assertNotIn(B.SUGGESTION_FIELD, payload['observation'])
        self.assertEqual(set(payload[B.SUGGESTION_FIELD]), set(B.SUGGESTION_KEYS))  # record_id is not shown
        self.assertEqual(C.strip_suggestion(with_block), plain)
        self.assertEqual(C.policy_request(self.runtime, 'periodic'), plain)
        self.assertEqual(with_block['messages'][0], plain['messages'][0])  # one system prompt for every arm
        with self.assertRaises(ValueError):
            C.policy_request(self.runtime, 'continuation', self.block)

    def test_service_contracts(self):
        self.assertEqual(SVC.validate_policy_request(C.policy_request(self.runtime, 'continuation')), 'without_suggestion')
        good = C.policy_request(self.runtime, 'periodic', self.block)
        self.assertEqual(SVC.validate_policy_request(good), 'with_suggestion')
        for mutate in (lambda p: p[B.SUGGESTION_FIELD].update(label='Observation'),
                       lambda p: p[B.SUGGESTION_FIELD].update(extra=1),
                       lambda p: p['observation'].update({B.SUGGESTION_FIELD: p.pop(B.SUGGESTION_FIELD)})):
            bad = copy.deepcopy(good)
            payload = json.loads(bad['messages'][1]['content'])
            mutate(payload)
            bad['messages'][1]['content'] = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            with self.assertRaises(ValueError):
                SVC.validate_policy_request(bad)
        reflection = B.reflection_request(SV.I.PROMPT + '\n\nEvidence:\n{}')
        self.assertEqual(SVC.validate_reflection_request(reflection), 'reflection')
        reflection['messages'][1]['content'] = 'free text'
        with self.assertRaises(ValueError):
            SVC.validate_reflection_request(reflection)

    def test_compute_is_disabled(self):
        with self.assertRaises(PermissionError):
            authority.require()
        with mock.patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '0'}):
            with self.assertRaises(PermissionError):
                authority.rehearsal_gate()


class OfflineEngineRehearsal(unittest.TestCase):
    """ar25, all three arms, 40 actions each, scripted fake server (about a minute on CPU)."""

    @classmethod
    def setUpClass(cls):
        from research.grounded_action_v1.engine import restore_game_mount
        from research.stagnation_supervision_v1.closed_loop.engine import DevelopmentAdapter
        cls.tmp = tempfile.TemporaryDirectory()
        folder = Path(cls.tmp.name)
        games = restore_game_mount(folder / 'games')
        cls.spec = {**SPEC, 'schedule': [s for s in SPEC['schedule'] if s['pair_id'] == 'b1-ar25']}
        cls.service = SVC.LocalService(F.FakeModelServer())
        cls.report = R.run(folder / 'run', cls.service,
                           lambda g, arm, eid: DevelopmentAdapter(g, arm, eid, games, folder / 'rec'),
                           spec=cls.spec, supervision_factory=B.supervision_factory(
                               cls.spec, TRIGGER, token_counter=B.fixture_token_counter()),
                           deadline_seconds=3000)
        cls.bodies = {b['arm']: b for b in episode_bodies(folder / 'run', cls.report)}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_run_completes_and_charges_every_reflection(self):
        self.assertEqual((self.report['status'], self.report['calls']), ('complete', 120))
        rows = [r for b in self.bodies.values() for r in b['reflections']]
        self.assertEqual(self.report['reflection_calls'], len(rows))
        self.assertEqual(self.report['reflection_prompt_tokens'], sum(r['server_prompt_tokens'] for r in rows))
        self.assertTrue(all(r['request_sha256'] and r['status'] == 'received' for r in rows))

    def test_continuation_never_reflects_but_is_observed(self):
        body = self.bodies['continuation']
        self.assertEqual(body['reflections'], [])
        self.assertFalse(any(s['suggestion_shown'] for s in body['steps']))
        self.assertGreater(body['supervision']['summary']['detector_firings'], 0)

    def test_reflection_timing_and_the_remaining_actions_gate(self):
        periodic = [e['action_index'] for e in self.bodies['periodic']['supervision']['events'] if e['outcome'] == 'called']
        self.assertEqual(periodic, [9, 19, 29])
        for arm in ('periodic', 'triggered'):
            events = self.bodies[arm]['supervision']['events']
            self.assertFalse(any(e['outcome'] == 'called' and e['action_index'] >= 30 for e in events))
            self.assertLessEqual(sum(e['outcome'] == 'called' for e in events), 4)

    def test_suggestion_blocks_follow_their_lifetime(self):
        for arm in ('periodic', 'triggered'):
            body = self.bodies[arm]
            delivered = [e for e in body['supervision']['events'] if e.get('delivered')]
            expected = {}
            for e in delivered:  # a later delivery replaces the earlier block
                for a in range(e['action_index'] + 1, e['action_index'] + 11):
                    expected[a] = e['action_index']
            shown = {s['index']: s['suggestion_shown']['issued_after_action'] for s in body['steps']
                     if s['suggestion_shown']}
            self.assertEqual(shown, {a: i for a, i in expected.items() if a < 40}, arm)

    def test_outcomes_are_measurable_in_every_arm(self):
        episodes = [{'arm': arm, 'records': records_of(b), 'reflections': [
            {'status': r['status'], 'valid': None, 'input_tokens': r.get('server_prompt_tokens'),
             'output_tokens': r.get('server_completion_tokens'), 'latency_s': r.get('latency_s')}
            for r in b['reflections']]} for arm, b in self.bodies.items()]
        summary = O.recovery_summary(episodes, TRIGGER, 40)
        self.assertGreaterEqual(summary['continuation']['opportunities'], 1)
        self.assertEqual(summary['continuation']['status'].get('recovered', 0), 0)  # the stuck policy never exits
        self.assertGreaterEqual(summary['triggered']['status'].get('recovered', 0), 1)
        cost = O.realised_cost(episodes)
        self.assertEqual(cost['by_arm']['continuation']['calls'], 0)
        for records in (e['records'] for e in episodes):
            self.assertEqual([p for r in records for p in T2.validate(r)], [])


SIZE = 16  # small frames keep scripted rehearsals fast; the runner and records accept any valid shape


class TokenAdmission(unittest.TestCase):
    def test_the_closed_loop_requires_an_exact_counter_and_admits_with_it(self):
        with self.assertRaises(TypeError):
            B.supervision_factory(SPEC, TRIGGER)
        with self.assertRaises(ValueError):
            B.supervision_factory(SPEC, TRIGGER, token_counter=None)
        _, [body] = scripted_run(['periodic'])
        called = [e for e in body['supervision']['events'] if e['outcome'] == 'called']
        self.assertTrue(called)
        for e, row in zip(called, body['reflections']):
            self.assertEqual(e['admission']['counter'], 'tokenizer')
            self.assertEqual(e['admission']['input_tokens'], row['tokenizer_prompt_tokens'])  # exact, not estimated

    def test_enumeration_covers_policy_and_reflection_requests(self):
        from research.stagnation_supervision_v1.closed_loop.requests import enumerate_requests, maximal_reflection_request
        rows = enumerate_requests(groups=['b1-ar25'], actions_per_episode=12)
        kinds = {}
        for r in rows:
            kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
            (SVC.validate_reflection_request if r['kind'] == 'reflection' else SVC.validate_policy_request)(r['request'])
            self.assertEqual(r['pair_id'], 'b1-ar25')
        self.assertEqual(kinds['policy'], 36)
        self.assertGreaterEqual(kinds['reflection'], 1)
        maximal = maximal_reflection_request()
        self.assertEqual(SVC.validate_reflection_request(maximal), 'reflection')
        longest = max(len(json.dumps(r['request'])) for r in rows if r['kind'] == 'reflection')
        self.assertGreater(len(json.dumps(maximal)), longest)
        from research.action_effect_history_v1.rehearsal import FixtureTokenizer
        audit_module = importlib.util.spec_from_file_location('audit', ROOT / 'scripts/audit_stagnation_supervision_v1_tokens.py')
        audit = importlib.util.module_from_spec(audit_module)
        audit_module.loader.exec_module(audit)
        report = audit.audit(FixtureTokenizer(), rows, maximal)
        self.assertEqual(report['by_kind']['policy']['requests'], 36)
        self.assertTrue(report['all_checks_pass'], report['checks'])


class ScriptedAdapter:
    """A 16x16 scripted game: the stuck ACTION6 changes nothing; any other action paints a new cell. `event` fires
    after the given action index: 'level' (levels_completed + 1), 'reset' (full_reset) or 'game_over'."""

    def __init__(self, game_id, event=None, at=None):
        self.game_id, self.event, self.at, self.n = game_id, event, at, 0
        self.levels, self.state = 0, 'NOT_FINISHED'
        self.frame = np.zeros((SIZE, SIZE), dtype=np.uint8)

    def obs(self, full_reset=False):
        from agent.state import Observation
        from arcengine import GameState
        return Observation(self.game_id, (self.frame.copy(),), GameState[self.state], self.levels, 8, 'guid',
                           (1, 2, 6), full_reset)

    def bootstrap(self):
        return self.obs(full_reset=True)

    def dispatch(self, action, before):
        reset = False
        if action != {'action_id': 6, 'action_data': F.STUCK_CELL}:
            self.frame[self.n % SIZE, (self.n * 5) % (SIZE - 3):(self.n * 5) % (SIZE - 3) + 3] = 1 + self.n % 9
        if self.n == self.at:
            if self.event == 'level':
                self.levels += 1
            elif self.event == 'reset':
                self.frame[:] = 0
                reset = True
            elif self.event == 'game_over':
                self.state = 'GAME_OVER'
        self.n += 1
        return self.obs(full_reset=reset), {'acknowledged': True, 'source': 'scripted'}

    def close(self):
        return {'closed': True}


def scripted_run(order, faults=(), event=None, at=None, policy=None):
    adapter = ScriptedAdapter('scripted-0000', event, at)
    initial = adapter.obs(full_reset=True).canonical_hash
    spec = {**SPEC, 'cases': [{'game_id': 'scripted-0000', 'environment_seed': 0, 'initial_available_actions': [1, 2, 6],
                               'initial_canonical_hash': initial, 'win_levels': 8}],
            'schedule': [{'block': 1, 'pair_id': 's1', 'game_id': 'scripted-0000', 'order': order}]}
    tmp = tempfile.TemporaryDirectory()
    report = R.run(Path(tmp.name) / 'run', SVC.LocalService(F.FakeModelServer(faults)),
                   lambda g, arm, eid: ScriptedAdapter(g, event, at), spec=spec,
                   supervision_factory=B.supervision_factory(spec, TRIGGER, policy or B.EXPERIMENT_POLICY,
                                                             token_counter=B.fixture_token_counter()),
                   deadline_seconds=3000)
    bodies = episode_bodies(Path(tmp.name) / 'run', report)
    tmp.cleanup()
    return report, bodies


class ScriptedRehearsals(unittest.TestCase):
    def test_invalid_reflections_are_retained_charged_and_never_delivered(self):
        report, [body] = scripted_run(['triggered'], faults=('reflection_invalid',))
        self.assertEqual(report['status'], 'complete')
        called = [e for e in body['supervision']['events'] if e['outcome'] == 'called']
        self.assertTrue(called)
        self.assertTrue(all(e['delivered'] is None and e['call']['raw_output'] == 'not json' for e in called))
        self.assertFalse(any(s['suggestion_shown'] for s in body['steps']))
        self.assertEqual(body['supervision']['summary']['tokens_charged'],
                         sum(r['server_prompt_tokens'] + r['server_completion_tokens'] for r in body['reflections']))

    def test_reflection_transport_failures_are_retained_and_counted(self):
        report, [body] = scripted_run(['periodic'], faults=('reflection_exception',))
        self.assertEqual(report['status'], 'complete')
        self.assertEqual([r['status'] for r in body['reflections']], ['failed'] * 3)
        summary = body['supervision']['summary']
        self.assertEqual((summary['failed_calls'], summary['calls']), (3, 3))
        self.assertGreater(summary['tokens_charged'], 0)  # a failed call is charged its estimated input

    def test_a_token_audit_mismatch_is_a_technical_failure(self):
        report, [body] = scripted_run(['triggered'], faults=('reflection_audit_mismatch',))
        self.assertEqual((report['status'], body['status']), ('technical_failure', 'technical_failure'))
        self.assertEqual(body['reflections'][-1]['status'], 'audit_failure')

    def test_suggestion_cleared_at_level_change_reset_and_terminal_state(self):
        for event in ('level', 'reset', 'game_over'):
            with self.subTest(event=event):
                report, [body] = scripted_run(['triggered'], event=event, at=4)
                events = body['supervision']['events']
                self.assertEqual(events[4].get('suggestion_cleared') is not None, True, events[4])
                self.assertFalse(any(s['suggestion_shown'] for s in body['steps'][5:6]))
                if event == 'game_over':
                    self.assertEqual(body['stop_reason'], 'game_over')
                    self.assertEqual(len(body['steps']), 5)

    def call_points(self, arm):
        _, [body] = scripted_run([arm])
        return [e['action_index'] for e in body['supervision']['events'] if e['outcome'] == 'called']

    def test_no_reflection_when_termination_or_a_boundary_coincides_with_a_due_reflection(self):
        """Review of 463cea3: GAME_OVER on the 10th action in the periodic arm used to get a reflection. Each
        reflection arm, at each of its own call points (a scheduled periodic call, a trigger firing), with each
        boundary: the transition and the detector output are recorded, no reflection is made and nothing is
        delivered."""
        expected = {'game_over': 'suppressed_terminal_state', 'level': 'suppressed_segment_boundary',
                    'reset': 'suppressed_segment_boundary'}
        for arm in ('periodic', 'triggered'):
            points = self.call_points(arm)
            self.assertGreaterEqual(len(points), 2, arm)
            for at in points[:2]:
                for event, outcome in expected.items():
                    with self.subTest(arm=arm, at=at, event=event):
                        report, [body] = scripted_run([arm], event=event, at=at)
                        events = body['supervision']['events']
                        e = events[at]
                        self.assertTrue(e['due'])
                        self.assertEqual(e['outcome'], outcome)
                        if arm == 'triggered':
                            self.assertTrue(e['detector_signals'])  # the detector output is still recorded
                        self.assertNotIn('call', e)
                        self.assertIsNone(e.get('delivered'))
                        before = [x for x in events if x['outcome'] == 'called' and x['action_index'] < at]
                        self.assertEqual(len(before), points.index(at))
                        self.assertEqual(body['steps'][at]['status'], 'acknowledged')
                        if event == 'game_over':  # play ended: nothing after it
                            self.assertEqual((body['stop_reason'], len(body['steps'])), ('game_over', at + 1))
                            self.assertEqual(e['remaining_actions'], 0)
                            self.assertEqual(len(body['reflections']), points.index(at))
                        else:  # play continues in a new segment; the next policy request carries no old block
                            self.assertIsNone(body['steps'][at + 1]['suggestion_shown'])

    def test_reflections_that_did_not_finish_with_stop_are_invalid_charged_and_retained(self):
        for fault, finish in (('reflection_length', 'length'), ('reflection_missing_finish', None),
                              ('reflection_unknown_finish', 'tool_calls')):
            with self.subTest(fault=fault):
                report, [body] = scripted_run(['periodic'], faults=(fault,))
                self.assertEqual(report['status'], 'complete')
                called = [e for e in body['supervision']['events'] if e['outcome'] == 'called']
                self.assertEqual(len(called), 3)
                for e, row in zip(called, body['reflections']):
                    self.assertIsNone(e['delivered'])
                    self.assertFalse(e['call']['parsed']['valid'])
                    self.assertEqual(e['call']['parsed']['problems'], [f'reflection did not finish with stop: {finish!r}'])
                    self.assertEqual(e['call']['raw_output'], row['response'])  # retained
                    self.assertEqual(row['finish_reason'], finish)
                self.assertFalse(any(s['suggestion_shown'] for s in body['steps']))
                summary = body['supervision']['summary']
                self.assertEqual((summary['invalid_outputs'], summary['valid_calls']), (3, 0))
                self.assertEqual(summary['tokens_charged'], sum(r['server_prompt_tokens'] + r['server_completion_tokens']
                                                                for r in body['reflections']))

    def test_an_invalid_completion_leaves_the_current_suggestion_lifetime_unchanged(self):
        responses = iter(['stop', 'length'])

        def call(text):
            content = json.loads(text.split('Evidence:\n', 1)[1])
            legal = [a for a in content['available_actions'] if 1 <= a <= 7]
            answer = {'observed_pattern': 'Repeats.', 'evidence_refs': [content['evidence'][-1]['action_index']],
                      'assumption_to_reconsider': 'That it responds.',
                      'distinguishing_test': {'description': 'Probe once.',
                                              'actions': [{'action_id': legal[0], 'action_data': {}}]}}
            return {'text': json.dumps(answer), 'input_tokens': 10, 'output_tokens': 5, 'finish_reason': next(responses)}
        s = SV.Supervisor('periodic', TRIGGER, call, {**B.EXPERIMENT_POLICY, 'period_actions': 6}, clock=lambda: 0.0,
                          episode_actions=40)
        frame = [[0] * 4 for _ in range(4)]
        for i in range(12):
            s.observe({'identity': {'episode_id': 'f', 'action_index': i},
                       'before': {'frames': [frame], 'levels_completed': 0, 'state': 'NOT_FINISHED', 'full_reset': False,
                                  'available_actions': [1, 2]},
                       'proposal': None, 'dispatched': {'action_id': 1, 'action_data': {}}, 'environment_source': 't',
                       'outcome': {'status': 'acknowledged', 'after': {
                           'frames': [frame], 'levels_completed': 0, 'state': 'NOT_FINISHED', 'full_reset': False,
                           'available_actions': [1, 2]}}})
        called = [e for e in s.events if e['outcome'] == 'called']
        self.assertEqual([e['delivered'] is not None for e in called], [True, False])
        self.assertEqual((s.suggestion['issued_after_action'], s.suggestion_for(15)['expires_after_action']), (5, 15))

    def test_no_reflection_in_the_last_window_and_none_in_continuation(self):
        report, bodies = scripted_run(['continuation', 'triggered'])
        cont, trig = bodies
        self.assertEqual(cont['reflections'], [])
        self.assertFalse(any(e['outcome'] == 'called' and e['action_index'] >= 30 for e in trig['supervision']['events']))


if __name__ == '__main__':
    unittest.main()
