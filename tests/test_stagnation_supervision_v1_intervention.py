"""Stagnation supervision v1 (Track 3): bounded intervention interface, policy limits and CPU rehearsals.

Every supervisor output here is scripted. No model runs."""
import copy
import inspect
import json
import unittest

from research.stagnation_supervision_v1 import detector as D, fixtures as F, intervention as I, supervision as SV
from research.stagnation_supervision_v1 import thresholds as S
from research.transition_evidence_v1 import transition as T

SPEC = S.load()
DEV = F.generate('development')
GRID = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]
CLICK = {'action_id': 6, 'action_data': {'x': 1, 'y': 1}}


def raw(index, before=GRID, after=GRID, action=CLICK, status='acknowledged', reset=False, levels=(0, 0), **extra):
    out = {'identity': {'episode_id': 'r', 'action_index': index},
           'before': {'frames': [before], 'levels_completed': levels[0], 'state': 'NOT_FINISHED', 'full_reset': False},
           'proposal': None, 'dispatched': action, 'environment_source': 'test', **extra}
    if status == 'acknowledged':
        out['outcome'] = {'status': status, 'after': {'frames': [] if after is None else [after],
                                                      'levels_completed': levels[1], 'state': 'NOT_FINISHED',
                                                      'full_reset': reset}}
    else:
        out['outcome'] = {'status': status, 'reason': 'test'}
    return out


def loop(n, start=0):
    return [raw(start + i) for i in range(n)]


def well_formed(request):
    """A contract-valid test action: the first available id in 1..7, with coordinates only for ACTION6."""
    action_id = next(a for a in request['content']['available_actions'] if 1 <= a <= 7)
    return {'action_id': action_id, 'action_data': {'x': 0, 'y': 0} if action_id == 6 else {}}


def answer(request, **override):
    shown = [e['action_index'] for e in request['content']['evidence']]
    value = {'observed_pattern': 'The same click repeats and the frame stays the same.',
             'evidence_refs': shown[-2:],
             'assumption_to_reconsider': 'That this click position responds at all.',
             'distinguishing_test': {'description': 'Click a different cell once; a change would show position matters.',
                                     'actions': [well_formed(request)]}}
    value.update(override)
    return json.dumps(value)


def ok(tokens_in=100, tokens_out=50, text=None):
    return {'text': text, 'input_tokens': tokens_in, 'output_tokens': tokens_out, 'latency_s': 0.5}


class EchoSupervisor:
    """Answers each request validly, from the request alone (no other knowledge)."""

    def __init__(self, tokens_in=100, tokens_out=50, override=None):
        self.requests, self.tokens, self.override = [], (tokens_in, tokens_out), override or {}

    def __call__(self, text):
        self.requests.append(text)
        content = json.loads(text.split('Evidence:\n', 1)[1])
        return ok(*self.tokens, text=answer({'content': content}, **self.override))


def records_for(raws):
    return T.history(raws)


class RequestBoundary(unittest.TestCase):
    def test_request_is_built_from_records_only(self):
        params = set(inspect.signature(I.build_request).parameters)
        self.assertEqual(params, {'records', 'decision_index', 'arm', 'detector_signals', 'available_actions'})
        self.assertEqual(set(I.build_request(records_for(loop(3)), 2, 'triggered', [])['content']), set(I.REQUEST_KEYS))

    def test_environment_side_material_never_reaches_the_request(self):
        raws = loop(4)
        for r in raws:
            r['environment_source'] = 'SENTINEL_ENV_SOURCE'
            r['game_source'] = 'SENTINEL_GAME_SOURCE def solve(): ...'
        request = I.build_request(records_for(raws), 3, 'triggered', [])
        self.assertNotIn('SENTINEL', json.dumps(request))

    def test_future_records_are_never_shown(self):
        raws = loop(5)
        raws[4]['dispatched'] = {'action_id': 3, 'action_data': {}}
        request = I.build_request(records_for(raws), 2, 'triggered', [])
        self.assertEqual([e['action_index'] for e in request['content']['evidence']], [0, 1, 2])
        self.assertEqual(request['content']['available_actions'], [6])
        self.assertEqual(request['content']['available_actions_source'], 'shown_evidence')

    def test_periodic_and_triggered_requests_share_one_template(self):
        records = records_for(loop(8))
        a = I.build_request(records, 7, 'periodic', [])
        b = I.build_request(records, 7, 'triggered', [])
        self.assertEqual(a['text'], b['text'])
        self.assertNotIn('periodic', a['text'])
        self.assertNotIn('triggered', b['text'])
        self.assertEqual(len(a['content']['evidence']), min(8, I.WINDOW))


class OutputValidation(unittest.TestCase):
    def setUp(self):
        self.request = I.build_request(records_for(loop(6)), 5, 'triggered', [], available_actions=[1, 2, 6])

    def check_invalid(self, text, fragment):
        parsed = I.parse(text, self.request)
        self.assertFalse(parsed['valid'])
        self.assertIsNone(parsed['intervention'])
        self.assertEqual(parsed['raw'], text)  # retained exactly
        self.assertTrue(any(fragment in p for p in parsed['problems']), parsed['problems'])

    def test_valid_output_is_rendered_in_the_fixed_template_only(self):
        parsed = I.parse(answer(self.request), self.request)
        self.assertTrue(parsed['valid'], parsed['problems'])
        text = I.render(parsed['intervention'])
        self.assertTrue(text.startswith('Reflection (a hypothesis from a reviewer, not an observation)'))
        self.assertIn('does not mean progress is impossible', text)

    def test_malformed_outputs(self):
        self.check_invalid('not json', 'not JSON')
        self.check_invalid(json.dumps(['a list']), 'exactly the fields')
        value = json.loads(answer(self.request))
        self.check_invalid(json.dumps({**value, 'next_actions': [1, 2]}), 'exactly the fields')
        del value['assumption_to_reconsider']
        self.check_invalid(json.dumps(value), 'exactly the fields')
        self.check_invalid(answer(self.request, observed_pattern=''), 'non-empty string')
        self.check_invalid(answer(self.request, observed_pattern='x' * 301), 'longer than')
        self.check_invalid('{' + ' ' * I.MAX_OUTPUT_CHARS + '}', 'output longer')
        self.check_invalid(None, 'not text')

    def test_unobserved_evidence_cannot_be_cited(self):
        self.check_invalid(answer(self.request, evidence_refs=[6]), 'not shown')
        self.check_invalid(answer(self.request, evidence_refs=[]), 'non-empty list')
        self.check_invalid(answer(self.request, evidence_refs=[3, 3]), 'distinct')

    def test_environment_source_knowledge_is_rejected(self):
        for text in ('In the source code the click handler ignores this cell.',
                     'The game_id suggests a key-door puzzle.',
                     'This matches ls20, where the key is behind the wall.',
                     'As in s5i5 the bottom row is a timer.',
                     'Reading level.py shows the goal.'):
            self.check_invalid(answer(self.request, observed_pattern=text), 'observed_pattern')

    def test_unobserved_solutions_are_rejected(self):
        self.check_invalid(answer(self.request, assumption_to_reconsider='The solution is to press 2 three times.'),
                           'solution_claim')
        test = {'description': 'This will complete the level.', 'actions': [{'action_id': 2, 'action_data': {}}]}
        self.check_invalid(answer(self.request, distinguishing_test=test), 'solution_claim')
        plan = {'description': 'Try moving.', 'actions': [{'action_id': 2, 'action_data': {}}] * 4}
        self.check_invalid(answer(self.request, distinguishing_test=plan), '1 to 3 actions')

    def with_action(self, action):
        return answer(self.request, distinguishing_test={'description': 'Probe once.', 'actions': [action]})

    def test_test_actions_must_be_available_and_inside_the_frame(self):
        self.check_invalid(self.with_action({'action_id': 4, 'action_data': {}}), 'currently legal')
        self.check_invalid(self.with_action({'action_id': 6, 'action_data': {'x': 4, 'y': 0}}),
                           'outside the observed frame')
        self.check_invalid(self.with_action({'action_id': 6, 'action_data': {'x': 1, 'y': 1, 'level': 2}}),
                           'ACTION6 requires')
        self.assertTrue(I.parse(self.with_action({'action_id': 6, 'action_data': {'x': 3, 'y': 2}}),
                                self.request)['valid'])

    def test_action6_arguments_follow_the_control_contract(self):
        for data in ({}, {'x': 1}, {'y': 1}, {'x': 1.0, 'y': 1}, {'x': '1', 'y': 1}, {'x': True, 'y': 1},
                     {'x': 1, 'y': False}, {'x': -1, 'y': 0}, {'x': 64, 'y': 0}, {'x': 0, 'y': 3}, None, [1, 1]):
            with self.subTest(data=data):
                self.check_invalid(self.with_action({'action_id': 6, 'action_data': data}), 'test action')

    def test_simple_actions_take_no_arguments(self):
        for action_id in (1, 2):
            for data in ({'x': 2, 'y': 1}, {'x': 0}, {'note': 'go'}, None):
                with self.subTest(action_id=action_id, data=data):
                    self.check_invalid(self.with_action({'action_id': action_id, 'action_data': data}),
                                       'only ACTION6 may carry action_data')
            self.assertTrue(I.parse(self.with_action({'action_id': action_id, 'action_data': {}}),
                                    self.request)['valid'])

    def test_action_ids_must_be_contract_integers(self):
        for action_id in (True, 1.0, '1', 0, 8, None):
            with self.subTest(action_id=action_id):
                self.check_invalid(self.with_action({'action_id': action_id, 'action_data': {}}), 'currently legal')
        reset_only = I.build_request(records_for(loop(3)), 2, 'triggered', [], available_actions=[0])
        parsed = I.parse(answer(self.request, distinguishing_test={
            'description': 'Probe once.', 'actions': [{'action_id': 0, 'action_data': {}}]}), reset_only)
        self.assertFalse(parsed['valid'])
        self.assertIn('test action: no action available under arc_action_v12', parsed['problems'])

    def test_the_contract_validator_is_imported_not_copied(self):
        from certification.phase4_transient_v2 import action_contract
        self.assertIs(I.validate_action, action_contract.validate_action)
        self.assertEqual(I.ACTION_CONTRACT_ID, 'arc_action_v12')


class PolicyRehearsal(unittest.TestCase):
    def test_repeated_triggers_respect_cooldown_and_the_intervention_cap(self):
        s = SV.Supervisor('triggered', SPEC, EchoSupervisor(), clock=lambda: 0.0)
        for r in loop(30):
            s.observe(r)
        calls = [e['action_index'] for e in s.events if e['outcome'] == 'called']
        self.assertEqual(calls, [1, 7, 13, 19])
        self.assertTrue(all(b - a >= SV.POLICY['cooldown_actions'] for a, b in zip(calls, calls[1:])))
        outcomes = [e['outcome'] for e in s.events]
        self.assertIn('suppressed_cooldown', outcomes)
        self.assertEqual(outcomes[20:], ['suppressed_cooldown'] * 5 + ['suppressed_intervention_cap'] * 5)
        self.assertEqual(s.summary()['tokens_charged'], 4 * 150)
        self.assertEqual(s.summary()['valid_calls'], 4)

    def test_token_budget_exhaustion(self):
        policy = {**SV.POLICY, 'max_supervisor_tokens_per_episode': 5000}
        s = SV.Supervisor('triggered', SPEC, EchoSupervisor(tokens_in=1800, tokens_out=200), policy, clock=lambda: 0.0)
        for r in loop(30):
            s.observe(r)
        summary = s.summary()
        self.assertEqual(summary['calls'], 2)
        self.assertEqual(summary['tokens_charged'], 4000)
        self.assertIn('suppressed_token_budget', summary['outcomes'])
        self.assertLessEqual(summary['tokens_charged'], policy['max_supervisor_tokens_per_episode'])

    def test_invalid_outputs_and_failures_are_charged_retained_and_counted(self):
        outputs = [ok(text='no json here'), RuntimeError('timeout after 30 s'),
                   ok(text='{"observed_pattern": "see the source code"}')]
        s = SV.rehearse(loop(30), 'triggered', SPEC, outputs)
        called = [e for e in s.events if e['outcome'] == 'called']
        self.assertEqual(len(called), 4)  # the fourth call finds the script exhausted: also a charged failure
        self.assertEqual([c['call']['raw_output'] for c in called[:3]],
                         ['no json here', None, '{"observed_pattern": "see the source code"}'])
        self.assertTrue(all(c['delivered'] is None for c in called))
        self.assertEqual(called[1]['call']['error'], 'RuntimeError: timeout after 30 s')
        self.assertEqual(called[3]['call']['error'], 'RuntimeError: scripted outputs exhausted')
        self.assertGreater(called[1]['call']['input_tokens'], 0)  # a failed call is still charged
        summary = s.summary()
        self.assertEqual((summary['invalid_outputs'], summary['failed_calls'], summary['valid_calls']), (2, 2, 0))
        self.assertEqual(summary['tokens_charged'], sum(c['call']['input_tokens'] + c['call']['output_tokens']
                                                        for c in called))
        self.assertIn('suppressed_intervention_cap', summary['outcomes'])

    def test_contract_violating_actions_are_retained_charged_and_counted(self):
        actions = ({'action_id': 6, 'action_data': {}}, {'action_id': 6, 'action_data': {'x': True, 'y': 1}},
                   {'action_id': 1, 'action_data': {'x': 2, 'y': 3}})
        bad = [ok(text=json.dumps({'observed_pattern': 'The same click repeats.', 'evidence_refs': [0, 1],
                                   'assumption_to_reconsider': 'That the click responds.',
                                   'distinguishing_test': {'description': 'Probe once.', 'actions': [action]}}))
               for action in actions]
        policy = {**SV.POLICY, 'max_interventions_per_episode': 3}
        s = SV.rehearse(loop(30), 'triggered', SPEC, bad, policy=policy, available_actions=[1, 6])
        called = [e for e in s.events if e['outcome'] == 'called']
        self.assertEqual([c['call']['raw_output'] for c in called], [b['text'] for b in bad])
        self.assertTrue(all(c['delivered'] is None and not c['call']['parsed']['valid'] for c in called))
        self.assertTrue(all(any('arc_action_v12' in p for p in c['call']['parsed']['problems']) for c in called))
        summary = s.summary()
        self.assertEqual((summary['calls'], summary['invalid_outputs'], summary['tokens_charged']), (3, 3, 3 * 150))
        self.assertIn('suppressed_intervention_cap', summary['outcomes'])

    def test_failed_dispatches_alone_never_trigger(self):
        s = SV.rehearse([raw(i, status='failed') for i in range(12)], 'triggered', SPEC, [])
        self.assertEqual(s.summary()['calls'], 0)
        self.assertEqual(s.summary()['detector_firings'], 0)

    def test_due_calls_are_deferred_when_the_state_was_not_observed(self):
        raws = loop(12)
        raws[5]['outcome'] = {'status': 'outcome_unknown', 'reason': 'timeout'}
        raws[11]['outcome']['after']['frames'] = []
        s = SV.Supervisor('periodic', SPEC, EchoSupervisor(), clock=lambda: 0.0)
        for r in raws:
            s.observe(r)
        self.assertEqual([e['outcome'] for e in s.events if e['due']], ['deferred_unobserved_state'] * 2)
        self.assertEqual(s.summary()['calls'], 0)

    def test_reset_clears_the_detector_but_not_the_episode_limits(self):
        moved = copy.deepcopy(GRID)
        moved[0][0] = 15
        raws = loop(8) + [raw(8, GRID, moved, {'action_id': 0, 'action_data': {}}, reset=True)]
        raws += [raw(9 + i, moved, moved) for i in range(16)]
        policy = {**SV.POLICY, 'max_interventions_per_episode': 3}
        s = SV.Supervisor('triggered', SPEC, EchoSupervisor(), policy, clock=lambda: 0.0)
        for r in raws:
            s.observe(r)
        firing = [e['action_index'] for e in s.events if e['detector_signals']]
        self.assertNotIn(9, firing)  # first step after the reset is a new segment
        self.assertIn(10, firing)
        self.assertEqual([e['action_index'] for e in s.events if e['outcome'] == 'called'], [1, 7, 13])
        self.assertIn('suppressed_intervention_cap', s.summary()['outcomes'])

    def test_arms_differ_only_in_timing(self):
        raws = loop(18)
        runs = {}
        for arm in SV.ARMS:
            echo = EchoSupervisor()
            s = SV.Supervisor(arm, SPEC, echo, clock=lambda: 0.0)
            for r in raws:
                s.observe(r)
            runs[arm] = (s, echo)
        cont = runs['continuation'][0].summary()
        self.assertEqual((cont['calls'], cont['tokens_charged']), (0, 0))
        self.assertGreater(cont['detector_firings'], 0)  # loops are measured in the continuation arm too
        periodic = [e['action_index'] for e in runs['periodic'][0].events if e['outcome'] == 'called']
        triggered = [e['action_index'] for e in runs['triggered'][0].events if e['outcome'] == 'called']
        self.assertEqual(periodic, [5, 11, 17])
        self.assertEqual(triggered, [1, 7, 13])
        prompt = lambda t: t.split('Evidence:\n')[0]  # noqa: E731
        self.assertEqual({prompt(t) for _, (s, echo) in runs.items() for t in echo.requests}, {I.PROMPT + '\n\n'})
        per_call = {arm: s.summary()['tokens_charged'] / s.summary()['calls'] for arm, (s, _) in runs.items()
                    if s.summary()['calls']}
        self.assertEqual(per_call['periodic'], per_call['triggered'])

    def test_triggered_calls_match_the_evaluated_trigger_stream(self):
        policy = {**SV.POLICY, 'max_interventions_per_episode': 10 ** 6, 'max_supervisor_tokens_per_episode': 10 ** 9}
        for fixture in DEV['fixtures']:
            s = SV.Supervisor('triggered', SPEC, EchoSupervisor(), policy, clock=lambda: 0.0)
            by_index = {p['action_index']: p for p in fixture['predictions'] or ()}
            for r in fixture['raws']:
                s.observe(r, by_index.get(r['identity']['action_index']))
            records = T.history(fixture['raws'])
            stream = D.triggers(D.statistics(records, fixture['predictions']), SPEC['params'],
                                SPEC['cooldown_actions'])
            # the supervisor never reflects at a reset, level change or terminal state (review of 463cea3); the
            # evaluated detector stream still counts those triggers
            boundary = {r['identity']['action_index'] for r in records
                        if set(r['environment']['events']) & set(SV.CLEARING_EVENTS)}
            self.assertEqual([e['action_index'] for e in s.events if e['outcome'] == 'called'],
                             [d['action_index'] for d in stream if d['trigger'] and d['action_index'] not in boundary],
                             fixture['id'])
            self.assertTrue(all(e['outcome'] == 'suppressed_segment_boundary' for e in s.events
                                if e['due'] and e['action_index'] in boundary))
            self.assertTrue(all(e['delivered'] for e in s.events if e['outcome'] == 'called'))


class EscapeMetrics(unittest.TestCase):
    def results(self, family):
        out = []
        for fixture in DEV['fixtures']:
            if DEV['evaluator_only'][fixture['id']]['family'] != family:
                continue
            s = SV.Supervisor('triggered', SPEC, EchoSupervisor(), clock=lambda: 0.0)
            for r in fixture['raws']:
                s.observe(r)
            out += SV.escapes(s.events, s.records)
        return out

    def test_escape_outcomes(self):
        self.assertEqual({e['result'] for e in self.results('repeated_click_no_effect')}, {'did_not_leave'})
        escaped = self.results('loop_then_escape')
        self.assertTrue(escaped)
        self.assertTrue(all(e['actions_to_leave'] and e['result'] == 'no_progress_before_end' for e in escaped))
        self.assertIn('another_detected_loop', {e['result'] for e in self.results('loop_escape_into_loop')})

    def test_progress_needs_a_confirmed_signal(self):
        moved = copy.deepcopy(GRID)
        moved[2][3] = 0
        raws = loop(3) + [raw(3, GRID, moved, {'action_id': 2, 'action_data': {}}),
                          raw(4, moved, GRID, {'action_id': 3, 'action_data': {}}, levels=(0, 1))]
        s = SV.Supervisor('triggered', SPEC, EchoSupervisor(), clock=lambda: 0.0)
        for r in raws:
            s.observe(r)
        self.assertEqual(SV.escapes(s.events, s.records), [{'intervention_at': 1, 'actions_to_leave': 2,
                                                            'result': 'progress'}])


if __name__ == '__main__':
    unittest.main()
