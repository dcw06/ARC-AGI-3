"""Feedback-action v1 live integration, GPU-disabled: derivation drift, request contract, and the derived runner on the
real offline development engine with the CPU fake server (no model, no GPU)."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.feedback_action_v1 import adapter as AD, derive as D, evaluate as EV, evidence as E
from research.feedback_action_v1.live import policy as P, runner as R
from research.feedback_action_v1.live.engine import DevelopmentAdapter
from research.feedback_action_v1.live.fake_server import FakeServer
from research.transition_evidence_v2 import transition as T

ROOT = Path(__file__).resolve().parents[1]
REVIEW_LOCK = ROOT / 'notebooks/action-effect-history-v1-review-r3/review-source-lock.json'


def one_pair(block, pair_id):
    spec = P.session_spec(block)
    spec['schedule'] = [p for p in spec['schedule'] if p['pair_id'] == pair_id]
    return spec


class Derivation(unittest.TestCase):
    def test_no_drift(self):
        self.assertEqual(D.stale(), [])

    def test_sources_are_the_reviewed_r3_files(self):
        lock = json.loads(REVIEW_LOCK.read_bytes())
        text = json.dumps(lock)
        for name in D.DERIVED:
            path = D.SOURCE_DIR + name
            digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            self.assertIn(f'"{path}": "{digest}"', text, path)
        contract = 'research/action_effect_history_v1/contract.py'  # observation_payload, reused unchanged
        self.assertIn(f'"{contract}": "{hashlib.sha256((ROOT / contract).read_bytes()).hexdigest()}"', text)

    def test_counted_substitutions_fail_closed(self):
        original = D.RUNNER
        try:
            D.DERIVED['runner.py'] = original + (('this text does not occur', 'x', 1),)
            with self.assertRaises(ValueError):
                D.derive_one('runner.py')
        finally:
            D.DERIVED['runner.py'] = original
        for target, text in D.derive().items():
            self.assertTrue(text.startswith('# Derived from research/action_effect_history_v1/'), target)
            self.assertNotIn('action_effect_history', text.split('\n', 1)[1])


class LiveRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from research.grounded_action_v1.engine import restore_game_mount
        cls.tmp = tempfile.TemporaryDirectory()
        cls.games = restore_game_mount(Path(cls.tmp.name) / 'games')
        cls.session = cls.run_spec(P.session_spec(1), 'normal')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def run_spec(cls, spec, mode):
        folder = Path(tempfile.mkdtemp(dir=cls.tmp.name))
        report = R.run(folder / 'run', FakeServer(mode),
                       lambda g, a, e: DevelopmentAdapter(g, a, e, cls.games, folder / 'rec'), spec=spec)
        assert R.load(folder / 'run') == report  # durable evidence reassembles to the returned report
        return report

    def test_session_completes_on_the_real_engine(self):
        report = self.session
        self.assertEqual((report['status'], report['calls'], report['dispatches']), ('complete', 144, 144))
        self.assertEqual([(e['game_id'][:4], e['arm']) for e in report['episodes']],
                         [('s5i5', 'baseline'), ('s5i5', 'candidate'), ('ls20', 'candidate'), ('ls20', 'baseline'),
                          ('sk48', 'baseline'), ('sk48', 'candidate')])
        for e in report['episodes']:
            self.assertEqual((e['stop_reason'], len(e['steps']), len(e['calls'])), ('action_cap', 24, 24))
            self.assertTrue(e['cleanup']['closed'])

    def test_every_request_is_the_contract_and_the_isolated_treatment(self):
        for e in self.session['episodes']:
            for n, call in enumerate(e['calls']):
                request = call['request']
                self.assertEqual(P.validate_policy_request(request), e['arm'])
                user = json.loads(request['messages'][1]['content'])
                if e['arm'] == 'candidate':
                    baseline = AD.strip_procedure(request)
                    self.assertEqual(P.validate_policy_request(baseline), 'baseline')
                    self.assertEqual(json.loads(baseline['messages'][1]['content'])['observation'], user['observation'])
                    if n == 0:
                        self.assertEqual(user[AD.PREVIOUS_FIELD]['reason'], 'no earlier decision in this episode')
                    else:
                        self.assertTrue(user[AD.PREVIOUS_FIELD]['available'])
                        self.assertEqual(user[AD.PREVIOUS_FIELD]['about'], f'T{n - 1}')
                else:
                    self.assertNotIn(AD.PREVIOUS_FIELD, user)

    def test_evidence_in_each_request_is_the_shared_view_of_the_retained_raws(self):
        for e in self.session['episodes']:
            raws = [s['raw_transition'] for s in e['steps']]
            self.assertEqual(T.verify_history(T.history(raws), raws), [])
            for n, call in enumerate(e['calls']):
                observation = json.loads(call['request']['messages'][1]['content'])['observation']
                view = observation[E.FIELD]
                self.assertEqual(view, E.view(raws[:n], observation['current_grid']))
                self.assertEqual(len(view['entries']), min(n, E.WINDOW))
            for step in e['steps']:
                self.assertEqual(step['record_id'], f"{e['episode_id']}#{step['index']}")
                self.assertEqual(step['raw_transition']['before']['available_actions'], step['before']['available_actions'])

    def test_model_statements_are_separate_v2_records(self):
        for e in self.session['episodes']:
            statements = e['model_statements']
            if e['arm'] == 'baseline':
                self.assertEqual(statements, [])
                continue
            self.assertEqual([s['about_record_id'] for s in statements], [s['record_id'] for s in e['steps']])
            self.assertTrue(all(s['version'] == 'transition_evidence_v2' and s['status'] == 'hypothesis'
                                for s in statements))
            self.assertNotIn('hypothesis', json.dumps([s['raw_transition'] for s in e['steps']]))

    def test_independent_evaluator_reads_live_episodes(self):
        for e in self.session['episodes']:
            evaluation = EV.evaluate_trajectory(P.trajectory(e))
            self.assertEqual(evaluation['metrics']['decisions'], 24)
            self.assertEqual(evaluation['metrics']['invalid_actions'], {})
            rates = evaluation['metrics']['rates']
            self.assertEqual(rates['invalid_action']['value'], 0.0)
            if e['arm'] == 'candidate':
                self.assertEqual(rates['citation_supply']['denominator'], 23)  # evidence shown from the 2nd decision
                self.assertEqual(rates['unsupported_citation']['numerator'], 0)  # the script cites truthfully
            if e['game_id'].startswith('s5i5'):  # the step bar: every frame is new, so no repeat opportunity
                self.assertEqual(rates['repeat_after_no_change']['status'], 'undefined')

    def test_invalid_outputs_never_end_an_episode_and_the_call_cap_does(self):
        report = self.run_spec(one_pair(1, 'b1-ls20'), 'invalid_every_third')
        self.assertEqual(report['status'], 'complete')
        for e in report['episodes']:
            invalid = [c for c in e['calls'] if c['status'] == 'invalid_output']
            self.assertEqual(e['stop_reason'], 'decision_cap')
            self.assertEqual(len(e['calls']), 32)
            self.assertEqual(len(e['steps']), 32 - len(invalid))
            self.assertGreater(len(invalid), 0)
            evaluation = EV.evaluate_trajectory(P.trajectory(e))
            self.assertEqual(evaluation['metrics']['rates']['invalid_action']['numerator'], len(invalid))
            self.assertEqual(evaluation['metrics']['rates']['invalid_action']['denominator'], 32)

    def test_always_invalid_stops_at_the_cap_and_the_schedule_continues(self):
        report = self.run_spec(one_pair(2, 'b2-sk48'), 'always_invalid')
        self.assertEqual(report['status'], 'complete')
        self.assertEqual([(e['arm'], e['stop_reason'], len(e['calls']), len(e['steps'])) for e in report['episodes']],
                         [('candidate', 'decision_cap', 32, 0), ('baseline', 'decision_cap', 32, 0)])

    def test_truncation_is_an_invalid_output_in_both_parsers(self):
        report = self.run_spec(one_pair(1, 'b1-sk48'), 'truncated_candidate')
        candidate = [e for e in report['episodes'] if e['arm'] == 'candidate'][0]
        truncated = [c for c in candidate['calls'] if c['finish_reason'] == 'length']
        self.assertEqual(len(truncated), 1)
        self.assertEqual(truncated[0]['status'], 'invalid_output')
        self.assertEqual((candidate['stop_reason'], len(candidate['calls']), len(candidate['steps'])),
                         ('action_cap', 25, 24))
        rows = EV.evaluate_trajectory(P.trajectory(candidate))['decisions']
        self.assertEqual(sum(r['action_problem'] == 'truncated' for r in rows), 1)
        # the request after the truncation carries no statement (no older one is substituted)
        n = candidate['calls'].index(truncated[0])
        carried = json.loads(candidate['calls'][n + 1]['request']['messages'][1]['content'])[AD.PREVIOUS_FIELD]
        self.assertFalse(carried['available'])


    def test_tampered_requests_are_refused(self):
        requests = {e['arm']: e['calls'][3]['request'] for e in self.session['episodes']}
        baseline, candidate = copy.deepcopy(requests['baseline']), copy.deepcopy(requests['candidate'])
        P.validate_policy_request(baseline)
        P.validate_policy_request(candidate)

        def edit_user(request, change):
            value = copy.deepcopy(request)
            user = json.loads(value['messages'][1]['content'])
            change(user)
            value['messages'][1]['content'] = json.dumps(user, sort_keys=True, separators=(',', ':'))
            return value

        bad = [dict(baseline, max_tokens=640), dict(candidate, max_tokens=128), dict(baseline, temperature=0.7),
               edit_user(baseline, lambda u: u.update({AD.PREVIOUS_FIELD: AD.carried_statement(None)})),
               edit_user(candidate, lambda u: u.pop(AD.PREVIOUS_FIELD)),
               edit_user(candidate, lambda u: u[AD.PREVIOUS_FIELD].update(hypothesis='x' * 241)),
               edit_user(baseline, lambda u: u['observation'][E.FIELD].update(scope='changed')),
               edit_user(baseline, lambda u: u['observation'].update(extra=1)),
               dict(baseline, response_format=AD.candidate_response_format([1, 2, 3, 4]))]
        swapped = copy.deepcopy(candidate)
        swapped['messages'][0]['content'] = AD.SYSTEM_PROMPT  # procedure removed but the block schema kept
        bad.append(swapped)
        for request in bad:
            with self.assertRaises(ValueError):
                P.validate_policy_request(request)


if __name__ == '__main__':
    unittest.main()
