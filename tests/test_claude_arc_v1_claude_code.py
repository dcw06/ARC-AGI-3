"""Subscription (Claude Code CLI) backend, compact grids and per-game failure handling. No network, no CLI."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from arcengine import GameState
from agent.e1_policy import CompletionResult
from research.claude_arc_v1 import audit, config, policy, run
from research.claude_arc_v1.backends import Budget, BudgetExceeded, ClaudeCodeBackend, ProviderStopped
from research.claude_arc_v1.cli import validate_live
from research.claude_arc_v1.transport import TransportFailure
from tests.test_claude_arc_v1 import FakeArc, FakeBackend, observation


def cli_settings(**kw):
    values = dict(live_enabled=True, backend='claude_code', model='claude-opus-5-5', max_actions_per_game=2,
                  input_usd_per_million=0, output_usd_per_million=0, max_output_tokens=32000,
                  max_input_tokens=200000)
    values.update(kw)
    return replace(config.Config(), **values)


def cli_result(answer, *, model='claude-opus-5-5', error=False, turns=2, structured=True):
    value = {'type': 'result', 'subtype': 'success', 'is_error': error, 'num_turns': turns,
             'result': json.dumps(answer), 'stop_reason': 'tool_use', 'terminal_reason': 'completed',
             'usage': {'input_tokens': 5, 'cache_creation_input_tokens': 900, 'cache_read_input_tokens': 100,
                       'output_tokens': 300}, 'modelUsage': {model: {'outputTokens': 300}},
             'total_cost_usd': 0.01, 'session_id': 'synthetic'}
    if structured:
        value['structured_output'] = answer
    return json.dumps(value)


class ScriptedCLI:
    def __init__(self, *outputs):
        self.outputs, self.calls = list(outputs), []

    def __call__(self, argv, stdin_text, env, cwd, timeout):
        self.calls.append({'argv': argv, 'stdin': stdin_text, 'env': env, 'cwd': cwd, 'cwd_listing': os.listdir(cwd),
                           'timeout': timeout})
        out = self.outputs.pop(0)
        if isinstance(out, BaseException):
            raise out
        return 0, out, ''


ACTION = {'action': {'action_id': 1, 'action_data': {}}}


def backend_for(c, cli, version=(2, 1, 318)):
    return ClaudeCodeBackend(c, Budget(c), runner=cli, executable='/synthetic/claude', version=version)


class Backend(unittest.TestCase):
    def test_subscription_call_strips_api_keys_and_returns_structured_action(self):
        c = cli_settings()
        cli = ScriptedCLI(cli_result(ACTION))
        backend = backend_for(c, cli)
        request = policy.Policy(c).request(observation())
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'must-not-leak', 'ANTHROPIC_AUTH_TOKEN': 'nor-this',
                                       'ARC_API_KEY': 'nor-this', 'PATH': '/usr/bin', 'HOME': '/tmp'}):
            result = backend.complete(request)
        call = cli.calls[0]
        self.assertEqual(json.loads(result.content), ACTION)
        self.assertEqual((result.prompt_tokens, result.completion_tokens), (1005, 300))
        self.assertFalse({'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ARC_API_KEY'} & call['env'].keys())
        self.assertEqual(call['env']['CLAUDE_CODE_MAX_OUTPUT_TOKENS'], '32000')
        self.assertEqual(call['cwd_listing'], [])
        self.assertFalse(Path(call['cwd']).exists())
        argv = call['argv']
        for flag, value in (('--model', 'claude-opus-5-5'), ('--effort', 'medium'), ('--tools', ''),
                            ('--setting-sources', ''), ('--output-format', 'json')):
            self.assertEqual(argv[argv.index(flag) + 1], value)
        self.assertEqual(argv[argv.index('--system-prompt') + 1], request['messages'][0]['content'])
        self.assertEqual(json.loads(argv[argv.index('--json-schema') + 1]), policy.response_schema('baseline'))
        self.assertEqual(call['stdin'], request['messages'][1]['content'])
        self.assertIn('--no-session-persistence', argv)
        self.assertEqual(backend.budget.calls, 1)

    def test_old_cli_refuses_before_any_call(self):
        with self.assertRaisesRegex(ValueError, 'too old'):
            backend_for(cli_settings(), ScriptedCLI(), version=(2, 1, 196))

    def test_error_wrong_model_or_missing_structure_returns_no_action(self):
        for output in (cli_result(ACTION, error=True), cli_result(ACTION, model='claude-haiku-5-5'),
                       cli_result(ACTION, structured=False), 'not json'):
            with self.subTest(output=output[:40]):
                c = cli_settings()
                with self.assertRaises((ValueError, TransportFailure)):
                    backend_for(c, ScriptedCLI(output)).complete(policy.Policy(c).request(observation()))

    def test_plan_limit_or_login_stops_but_other_cli_errors_are_transient(self):
        def errored(text, status=None):
            value = json.loads(cli_result(ACTION, error=True))
            value.update(result=text, api_error_status=status)
            return json.dumps(value)
        c = cli_settings()
        for output in (errored("Claude AI usage limit reached; resets 9pm"), errored('Invalid API key · Please run /login'),
                       errored('unauthorized', 401)):
            with self.subTest(output=output[-80:]), self.assertRaises(ProviderStopped):
                backend_for(c, ScriptedCLI(output)).complete(policy.Policy(c).request(observation()))
        backend = backend_for(c, ScriptedCLI(errored('API Error: 529 Overloaded', 529)))
        with self.assertRaises(TransportFailure):
            backend.complete(policy.Policy(c).request(observation()))
        self.assertEqual(backend.last_record['error_text'], 'API Error: 529 Overloaded')

    def test_missing_binary_is_a_transport_failure(self):
        c = cli_settings()
        with self.assertRaises(TransportFailure):
            backend_for(c, ScriptedCLI(FileNotFoundError('claude'))).complete(policy.Policy(c).request(observation()))

    def test_prompt_cache_disabled_for_one_shot_calls(self):
        c = cli_settings()
        cli = ScriptedCLI(cli_result(ACTION))
        backend_for(c, cli).complete(policy.Policy(c).request(observation()))
        self.assertEqual(cli.calls[0]['env']['DISABLE_PROMPT_CACHING'], '1')

    def test_replaced_cli_is_rechecked_and_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / 'claude'
            executable.write_bytes(b'v1')
            c = cli_settings()
            versions = ['2.1.320 (Claude Code)']
            def runner(argv, stdin_text, env, cwd, timeout):
                if argv[1:] == ['--version']:
                    return 0, versions.pop(0), ''
                return 0, cli_result(ACTION), ''
            backend = ClaudeCodeBackend(c, Budget(c), runner=runner, executable=str(executable), version=(2, 1, 318))
            backend.complete(policy.Policy(c).request(observation()))
            self.assertEqual(backend.last_record['cli_changes'], 0)
            executable.write_bytes(b'v2-longer')  # an auto-update swapped the file
            backend.complete(policy.Policy(c).request(observation()))
            self.assertEqual((backend.version, backend.last_record['cli_version'], backend.last_record['cli_changes']),
                             ((2, 1, 320), '2.1.320', 1))
            executable.unlink()
            with self.assertRaises(TransportFailure):
                backend.complete(policy.Policy(c).request(observation()))

    def test_timeout_is_uncertain_transport_failure(self):
        c = cli_settings()
        backend = backend_for(c, ScriptedCLI(subprocess.TimeoutExpired('claude', 1)))
        with self.assertRaises(TransportFailure):
            backend.complete(policy.Policy(c).request(observation()))
        self.assertEqual(backend.budget.calls, 1)

    def test_oversized_prompt_refuses_before_reserving(self):
        c = cli_settings(max_input_tokens=10)
        backend = backend_for(c, ScriptedCLI())
        with self.assertRaises(BudgetExceeded):
            backend.complete(policy.Policy(c).request(observation()))
        self.assertEqual(backend.budget.calls, 0)

    def test_subscription_consent_is_separate_and_needs_no_anthropic_key(self):
        c = cli_settings()
        args = dict(execute=True, confirm_paid=False, confirm_online=True, confirm_competition=False,
                    environ={'ARC_API_KEY': 'test-arc'})
        with self.assertRaisesRegex(PermissionError, 'subscription'):
            validate_live(c, **args)
        validate_live(c, **args, confirm_subscription=True)

    def test_schema_requires_exactly_the_stage_contract(self):
        for stage in config.STAGES:
            p = policy.Policy(cli_settings(stage=stage))
            answer = json.loads(FakeBackend(p.config).complete(p.request(observation())).content)
            self.assertEqual(set(policy.response_schema(stage)['required']), set(answer))


class CompactGrid(unittest.TestCase):
    def test_hex_prompt_keeps_exact_evidence_and_lists_changed_cells(self):
        c = cli_settings(grid_encoding='hex_rows', stage='history')
        p = policy.Policy(c)
        before = observation(frames=[[[0, 10], [15, 3]]])
        request = p.request(before)
        current = json.loads(request['messages'][1]['content'])['evidence']['current']
        self.assertEqual(current['final_frame'], ['00|0a', '01|f3'])
        self.assertNotIn('frames', current)
        self.assertIn('hexadecimal', request['messages'][0]['content'])
        decision, answer = p.parse(json.dumps(ACTION), before)
        after = observation(frames=[[[1, 1], [0, 0]], [[0, 10], [15, 4]]])
        transition = p.observe(before, decision, after, answer)
        self.assertEqual(transition['after']['frames'][1], [[0, 10], [15, 4]])  # evidence unchanged
        evidence = json.loads(p.request(after)['messages'][1]['content'])['evidence']
        shown = evidence['history'][0]
        self.assertEqual(shown['changed_cells'], [[1, 1, 1, '3', '4']])
        # The newest result is the current board, so it is not sent twice; the stored entry keeps it.
        self.assertEqual(shown['after']['final_frame'], 'same as evidence.current.final_frame')
        self.assertEqual(evidence['current']['final_frame'], ['00|0a', '01|f4'])
        self.assertEqual(p.compact[0]['after']['final_frame'], ['00|0a', '01|f4'])
        self.assertNotIn('before', shown)

    def test_history_board_limit_keeps_only_the_newest_boards(self):
        for limit, expected in ((3, ['omitted', 'omitted', 'board', 'board', 'same']),
                                (0, ['board', 'board', 'board', 'board', 'same'])):
            with self.subTest(limit=limit):
                c = cli_settings(grid_encoding='hex_rows', stage='history', history_limit=8, history_board_limit=limit)
                p = policy.Policy(c)
                for i in range(5):
                    decision, answer = p.parse(json.dumps(ACTION), observation())
                    p.observe(observation(), decision, observation(frames=[[[0, i], [0, 0]]]), answer)
                history = json.loads(p.request(observation())['messages'][1]['content'])['evidence']['history']
                kinds = ['board' if isinstance(h['after']['final_frame'], list) else h['after']['final_frame'].split(' ')[0]
                         for h in history]
                self.assertEqual(kinds, expected)
                self.assertTrue(all('changed_cells' in h for h in history))
                self.assertTrue(all(isinstance(e['after']['final_frame'], list) for e in p.compact))  # stored intact

    def test_rows_are_labelled_and_grouped_in_eights(self):
        frame = np.tile(np.arange(16), (64, 4))[:, :64]
        rows = policy.hex_rows(frame)
        self.assertEqual(len(rows), 64)
        self.assertEqual(rows[38], '38|01234567 89abcdef 01234567 89abcdef 01234567 89abcdef 01234567 89abcdef')
        x = 42  # the documented rule: character x%8 of group x//8
        self.assertEqual(rows[38][3:].split(' ')[x // 8][x % 8], '0123456789abcdef'[frame[38, x]])

    def test_changed_cells_are_runs_with_a_bounded_fallback(self):
        before = np.zeros((64, 64), dtype=np.uint8)
        after = before.copy()
        after[10, 4:12] = 12  # one 8-cell run
        after[11, 4:12] = 12
        self.assertEqual(policy.changed_cells(before, after), [[4, 11, 10, '0', 'c'], [4, 11, 11, '0', 'c']])
        noisy = before.copy()
        noisy[0:20:2, 0:64:2] = 1  # 320 isolated cells, 320 runs
        summary = policy.changed_cells(before, noisy)
        self.assertEqual((summary['cells'], summary['listed']), (320, False))
        self.assertEqual(summary['bounding_box'], {'x_first': 0, 'x_last': 62, 'y_first': 0, 'y_last': 18})

    def test_json_encoding_prompt_is_unchanged(self):
        c = cli_settings()
        request = policy.Policy(c).request(observation())
        self.assertEqual(request['messages'][0]['content'], policy.SYSTEM)
        self.assertIn('frames', json.loads(request['messages'][1]['content'])['evidence']['current'])

    def test_out_of_palette_frame_falls_back_to_integers(self):
        frame = np.full((2, 2), 200)
        self.assertIsNone(policy.hex_rows(frame))
        c = cli_settings(grid_encoding='hex_rows')
        current = json.loads(policy.Policy(c).request(observation(frames=[frame]))['messages'][1]['content'])
        self.assertIn('frames', current['evidence']['current'])

    def test_hypotheses_can_survive_a_level_when_configured(self):
        raw = {**ACTION, 'hypotheses': [{'id': 'h', 'statement': 'ACTION1 moves the block up',
                                         'status': 'tentative', 'evidence_ids': []}]}
        for clear, expected in ((True, 0), (False, 1)):
            p = policy.Policy(cli_settings(stage='hypotheses', clear_hypotheses_on_level=clear))
            decision, answer = p.parse(json.dumps(raw), observation())
            p.observe(observation(), decision, observation(level=1), answer)
            self.assertEqual(len(p.hypotheses), expected)


class ObservationEvidence(unittest.TestCase):
    """Replays the smoke-test ft09 failure: a rule read off the first board, before any transition exists."""

    def answer(self, evidence_ids, status='supported_locally'):
        return json.dumps({**ACTION, 'hypotheses': [
            {'id': 'key_rule', 'statement': 'centre key maps 2 to colour 9', 'status': status, 'evidence_ids': evidence_ids}]})

    def test_first_board_can_be_cited_only_when_enabled(self):
        enabled = policy.Policy(cli_settings(stage='hypotheses', observation_evidence_ids=True))
        current = json.loads(enabled.request(observation())['messages'][1]['content'])['evidence']['current']
        self.assertEqual(current['observation_id'], 'o0')
        enabled.parse(self.answer(['o0']), observation())
        for bad in ([], ['o1'], ['t1']):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                enabled.parse(self.answer(bad), observation())
        disabled = policy.Policy(cli_settings(stage='hypotheses'))
        self.assertNotIn('observation_id', json.loads(disabled.request(observation())['messages'][1]['content'])['evidence']['current'])
        with self.assertRaises(ValueError):
            disabled.parse(self.answer(['o0']), observation())

    def test_history_boards_carry_ids_within_the_window(self):
        c = cli_settings(stage='hypotheses', observation_evidence_ids=True, grid_encoding='hex_rows', history_limit=2)
        p = policy.Policy(c)
        for _ in range(3):
            decision, answer = p.parse(self.answer([], 'tentative'), observation())
            p.observe(observation(), decision, observation(), answer)
        request = p.request(observation())
        evidence = json.loads(request['messages'][1]['content'])['evidence']
        self.assertEqual(evidence['current']['observation_id'], 'o3')
        self.assertEqual([h['after']['observation_id'] for h in evidence['history']], ['o2', 'o3'])
        self.assertIn('t1..t3', json.loads(request['messages'][1]['content'])['procedure'][-1])
        p.parse(self.answer(['o1', 't3']), observation())
        p.parse(self.answer(['o0', 't1']), observation())  # outside the shown window but recorded: citable
        with self.assertRaisesRegex(ValueError, r"'key_rule' cites unavailable evidence \['o4'\]; citable: t1-t3, o0-o3"):
            p.parse(self.answer(['o4']), observation())  # a board that does not exist yet

    def test_rejections_name_the_problem(self):
        p = policy.Policy(cli_settings(stage='hypotheses', observation_evidence_ids=True))
        twice = {**ACTION, 'hypotheses': [{'id': 'h', 'statement': 's', 'status': 'tentative', 'evidence_ids': []}] * 2}
        with self.assertRaisesRegex(ValueError, "duplicate hypothesis id 'h'"):
            p.parse(json.dumps(twice), observation())
        with self.assertRaisesRegex(ValueError, "'key_rule' repeats an evidence id"):
            p.parse(self.answer(['o0', 'o0']), observation())


class FlakyBackend(FakeBackend):
    """Fails the listed call numbers (1-based) with invalid text; other calls return a legal action."""

    def __init__(self, c, failing):
        super().__init__(c)
        self.failing, self.count = set(failing), 0

    def complete(self, request):
        self.count += 1
        if self.count in self.failing:
            reserved = self.budget.reserve()
            self.budget.settle(reserved, 1, 1)
            self.requests.append(request)
            return CompletionResult('not json', 1, 1, 0)
        return super().complete(request)


class Controller(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, c, backend, arc):
        folder = Path(self.temp.name) / 'run'
        result = run.evaluate(c, backend, arc, run.Evidence(folder))
        return result, folder

    def test_retry_after_invalid_reply_then_acts(self):
        c = cli_settings(model_retries_per_action=1)
        backend, arc = FlakyBackend(c, {1}), FakeArc()
        result, folder = self.execute(c, backend, arc)
        self.assertTrue(result['full_lifecycle_complete'])
        self.assertEqual((backend.count, len(arc.actions)), (2, 1))
        kinds = [json.loads(line)['kind'] for line in (folder / 'events.jsonl').read_text().splitlines()]
        self.assertIn('model_failed_retrying', kinds)
        self.assertEqual(audit.audit(folder)['model_requests_entered'], 2)

    def test_retry_after_rejected_reply_says_why_but_transport_retry_does_not(self):
        c = cli_settings(model_retries_per_action=1, stage='hypotheses')
        backend = FlakyBackend(c, {1})
        self.execute(c, backend, FakeArc())
        first, second = (json.loads(r['messages'][1]['content']) for r in backend.requests)
        self.assertNotIn('previous_reply_rejected', first)
        self.assertIn('JSONDecodeError', second['previous_reply_rejected'])

        class TransportFlaky(FakeBackend):
            calls = 0
            def complete(self, request):
                TransportFlaky.calls += 1
                self.requests.append(request)
                if TransportFlaky.calls == 1:
                    raise TransportFailure('synthetic timeout')
                self.requests.pop()
                return super().complete(request)
        self.temp.cleanup()
        self.temp = tempfile.TemporaryDirectory()
        backend = TransportFlaky(c)
        self.execute(c, backend, FakeArc())
        self.assertEqual(backend.requests[0], backend.requests[1])

    def test_next_game_after_exhausted_retries_and_audit_passes(self):
        c = cli_settings(mode='competition', games=(), on_model_failure='next_game')
        backend, arc = FlakyBackend(c, {1}), FakeArc(('ft09-test', 'ls20-test'))
        result, folder = self.execute(c, backend, arc)
        self.assertEqual(arc.made, ['ft09-test', 'ls20-test'])
        self.assertEqual([r['stop_reason'] for r in result['games']], ['JSONDecodeError', 'win'])
        self.assertEqual(result['problems'], ['ft09-test: JSONDecodeError'])
        self.assertEqual(arc.closed, 1)
        self.assertEqual(audit.audit(folder)['games_attempted'], 2)

    def test_outage_backs_off_then_stops_instead_of_discarding_games(self):
        c = cli_settings(mode='competition', games=(), on_model_failure='next_game', model_retries_per_action=2,
                         model_retry_backoff_seconds=30)

        class Down(FakeBackend):
            def complete(self, request):
                self.budget.reserve()
                self.requests.append(request)
                raise TransportFailure('Claude Code reported an error: network unreachable')
        arc, slept = FakeArc(('ft09-test', 'ls20-test', 'vc33-test')), []
        folder = Path(self.temp.name) / 'run'
        result = run.evaluate(c, Down(c), arc, run.Evidence(folder), sleep=slept.append)
        self.assertEqual(arc.made, ['ft09-test'])  # the other environments are never initialized
        self.assertEqual(slept, [30, 30])
        self.assertEqual(result['games_not_started'], ['ls20-test', 'vc33-test'])
        self.assertEqual(arc.closed, 1)
        audit.audit(folder)

    def test_recovers_when_the_outage_clears(self):
        c = cli_settings(model_retries_per_action=2, model_retry_backoff_seconds=30)

        class Blip(FakeBackend):
            calls = 0
            def complete(self, request):
                Blip.calls += 1
                if Blip.calls == 1:
                    self.budget.reserve()
                    raise TransportFailure('synthetic timeout')
                return super().complete(request)
        arc, slept = FakeArc(), []
        result = run.evaluate(c, Blip(c), arc, run.Evidence(Path(self.temp.name) / 'run'), sleep=slept.append)
        self.assertTrue(result['full_lifecycle_complete'])
        self.assertEqual((slept, len(arc.actions)), ([30], 1))

    def test_plan_limit_stops_immediately_without_retry(self):
        c = cli_settings(mode='competition', games=(), on_model_failure='next_game', model_retries_per_action=2)

        class Limited(FakeBackend):
            def complete(self, request):
                self.budget.reserve()
                raise ProviderStopped('usage limit reached')
        backend, arc = Limited(c), FakeArc(('ft09-test', 'ls20-test'))
        result, folder = self.execute(c, backend, arc)
        self.assertEqual((arc.made, backend.budget.calls), (['ft09-test'], 1))
        self.assertEqual(result['games'][0]['stop_reason'], 'ProviderStopped')
        audit.audit(folder)

    def test_three_games_in_a_row_without_actions_stop_the_run(self):
        c = cli_settings(mode='competition', games=(), on_model_failure='next_game')
        games = tuple('g%d-test' % i for i in range(5))
        arc = FakeArc(games)
        result, folder = self.execute(c, FlakyBackend(c, set(range(1, 100))), arc)
        self.assertEqual(arc.made, list(games[:3]))
        self.assertIn('stopped: three consecutive games ended before any action', result['problems'])
        audit.audit(folder)

    def test_inactivity_guard_counts_backoff(self):
        cli_settings(request_timeout_seconds=240, model_retries_per_action=2, model_retry_backoff_seconds=30)
        with self.assertRaisesRegex(ValueError, 'inactivity'):
            cli_settings(request_timeout_seconds=270, model_retries_per_action=2, model_retry_backoff_seconds=30)

    def test_default_still_stops_the_attempt(self):
        c = cli_settings(mode='competition', games=())
        arc = FakeArc(('ft09-test', 'ls20-test'))
        result, _ = self.execute(c, FlakyBackend(c, {1}), arc)
        self.assertEqual(arc.made, ['ft09-test'])
        self.assertEqual(result['games_not_started'], ['ls20-test'])

    def scripted_arc(self, states):
        """Each dispatch returns the next scripted state; levels stay at 0."""
        arc, script = FakeArc(), list(states)
        def dispatch(client, decision):
            arc.actions.append(decision)
            client.observation = observation(client.game_id, 0, script.pop(0))
            return client.observation
        arc.dispatch = dispatch
        return arc

    def test_level_reset_after_game_over_keeps_notes_and_audits(self):
        c = cli_settings(resets_per_game=1, max_actions_per_game=5, stage='hypotheses')
        arc = self.scripted_arc([GameState.GAME_OVER, GameState.NOT_FINISHED, GameState.WIN])
        backend = FakeBackend(c)
        result, folder = self.execute(c, backend, arc)
        self.assertEqual([a.action_id for a in arc.actions], [1, 0, 1])
        self.assertEqual(len(backend.requests), 2)  # the reset needs no model call
        self.assertEqual((result['games'][0]['stop_reason'], result['games'][0]['level_resets']), ('win', 1))
        self.assertIn('restarts the current level', backend.requests[0]['messages'][0]['content'])
        self.assertEqual(audit.audit(folder)['actions_acknowledged'], 3)

    def test_game_over_stops_when_resets_are_used_up_or_absent(self):
        for resets, expected in ((0, [1]), (1, [1, 0, 1])):
            with self.subTest(resets=resets):
                self.temp.cleanup()
                self.temp = tempfile.TemporaryDirectory()
                c = cli_settings(resets_per_game=resets, max_actions_per_game=5)
                arc = self.scripted_arc([GameState.GAME_OVER, GameState.NOT_FINISHED, GameState.GAME_OVER])
                result, folder = self.execute(c, FakeBackend(c), arc)
                self.assertEqual([a.action_id for a in arc.actions], expected)
                self.assertEqual(result['games'][0]['stop_reason'], 'game_over')
                audit.audit(folder)

    def test_game_over_on_last_permitted_action_is_labelled_game_over(self):
        c = cli_settings(resets_per_game=3, max_actions_per_game=1)
        result, folder = self.execute(c, FakeBackend(c), self.scripted_arc([GameState.GAME_OVER]))
        self.assertEqual(result['games'][0]['stop_reason'], 'game_over')
        audit.audit(folder)

    def test_audit_rejects_a_reset_beyond_the_configured_count(self):
        c = cli_settings(resets_per_game=1, max_actions_per_game=5)
        arc = self.scripted_arc([GameState.GAME_OVER, GameState.NOT_FINISHED, GameState.WIN])
        _, folder = self.execute(c, FakeBackend(c), arc)
        path = folder / 'events.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for row in rows:
            if row['kind'] == 'configuration':
                row['config']['resets_per_game'] = 0
        # Re-chain so only the reset rule, not the hash chain, can reject it.
        import hashlib
        previous, lines = '0' * 64, []
        for row in rows:
            row.pop('sha256')
            row['previous_sha256'] = previous
            previous = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            lines.append(json.dumps({**row, 'sha256': previous}))
        path.write_text('\n'.join(lines) + '\n')
        with self.assertRaisesRegex(ValueError, 'illegal level reset'):
            audit.audit(folder)

    def test_budget_exhaustion_is_never_skipped_past(self):
        c = cli_settings(mode='competition', games=(), on_model_failure='next_game', max_model_calls=1,
                         max_actions_per_game=3)
        arc = FakeArc(('ft09-test', 'ls20-test'))
        arc.dispatch = lambda client, decision: client.observation  # never terminal
        result, folder = self.execute(c, FakeBackend(c), arc)
        self.assertEqual(arc.made, ['ft09-test'])
        self.assertEqual(result['games'][0]['stop_reason'], 'BudgetExceeded')
        audit.audit(folder)


class CLIWiring(unittest.TestCase):
    def run_cli(self, version):
        from research.claude_arc_v1 import cli
        root = Path(__file__).resolve().parents[1]
        private = root / '.cache/claude_arc_runs'
        private.mkdir(parents=True, exist_ok=True)
        folder = Path(tempfile.mkdtemp(dir=private))
        self.addCleanup(lambda: __import__('shutil').rmtree(folder, ignore_errors=True))
        c = cli_settings(max_actions_per_game=1)
        configuration = folder / 'config.json'
        configuration.write_text(json.dumps(c.public()))
        executable = folder / 'claude'
        executable.write_bytes(b'synthetic cli')
        scripted = ScriptedCLI(cli_result(ACTION))
        def factory(config_, budget):
            return ClaudeCodeBackend(config_, budget, runner=scripted, executable=str(executable), version=version)
        output = folder / 'attempt'
        with patch.dict('os.environ', {'ARC_API_KEY': 'synthetic-only'}), \
                patch('research.claude_arc_v1.backends.ClaudeCodeBackend', side_effect=factory), \
                patch('research.claude_arc_v1.arc.make_adapter', return_value=FakeArc()), \
                patch('socket.create_connection', side_effect=AssertionError('no network')), \
                patch('builtins.print'):
            code = cli.main(['--config', str(configuration), '--execute', '--confirm-online-arc',
                             '--confirm-subscription-usage', '--output', str(output)])
        return code, output, scripted

    def test_real_cli_path_binds_backend_and_audits(self):
        code, output, scripted = self.run_cli((2, 1, 318))
        self.assertEqual(code, 0)
        self.assertEqual(len(scripted.calls), 1)
        events = [json.loads(line) for line in (output / 'events.jsonl').read_text().splitlines()]
        binding = next(e for e in events if e['kind'] == 'backend_binding')
        self.assertEqual(binding['cli_version'], '2.1.318')
        self.assertEqual(audit.audit(output)['actions_acknowledged'], 1)

    def test_old_cli_refuses_before_any_evidence_or_scorecard(self):
        with self.assertRaisesRegex(ValueError, 'too old'):
            self.run_cli((2, 1, 196))


if __name__ == '__main__':
    unittest.main()
