"""Backends implement the existing CompletionClient.complete contract, not a new agent."""
from decimal import Decimal
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time

from agent.e1_policy import CompletionResult
from .transport import TransportFailure, json_request, request_once

# Opus 5.5 needs Claude Code 2.1.280 or newer (older CLIs return HTTP 400 for this model).
MIN_CLAUDE_CLI = (2, 1, 280)
# Only these variables reach the CLI. ANTHROPIC_API_KEY and friends are deliberately absent:
# with them present the CLI bills the paid API instead of the signed-in subscription.
CLI_ENVIRONMENT = ('PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TMPDIR', 'SHELL', 'TERM')


class BudgetExceeded(RuntimeError):
    pass


class ProviderStopped(BudgetExceeded):
    """The subscription cannot serve further calls (plan limit, login): stop the attempt, never retry."""


PLAN_STOP = re.compile(r'usage limit|limit reached|hit your [a-z ]*limit|out of extra usage|credit balance'
                       r'|log ?in|authenticat|unauthori|subscription', re.IGNORECASE)


class Budget:
    def __init__(self, config):
        self.config = config
        self.calls = self.http_requests = 0
        self.spent = Decimal('0')
        self.reserved_unknown = Decimal('0')

    def check(self):
        c = self.config
        worst = (Decimal(str(c.input_usd_per_million)) * c.max_input_tokens
                 + Decimal(str(c.output_usd_per_million)) * c.max_output_tokens) / 1_000_000
        if self.calls >= c.max_model_calls or self.spent + self.reserved_unknown + worst > Decimal(str(c.spend_limit_usd)):
            raise BudgetExceeded('model-call or conservative dollar budget exhausted')
        return worst

    def reserve(self):
        worst = self.check()
        self.calls += 1
        self.reserved_unknown += worst
        return worst

    def settle(self, reservation, inputs, outputs, turns=1):
        # turns > 1 only for the CLI path, whose structured output spans internal turns with per-turn caps.
        c = self.config
        if (type(inputs) is not int or type(outputs) is not int or not 0 <= inputs <= c.max_input_tokens * turns
                or not 0 <= outputs <= c.max_output_tokens * turns):
            raise ValueError('invalid or over-cap usage; full reservation remains uncertain')
        actual = (Decimal(str(c.input_usd_per_million)) * inputs
                  + Decimal(str(c.output_usd_per_million)) * outputs) / 1_000_000
        self.reserved_unknown -= reservation
        self.spent += actual

    def report(self):
        return {'model_calls_attempted': self.calls, 'model_http_requests_attempted': self.http_requests,
                'estimated_usd_known': str(self.spent), 'estimated_usd_reserved_uncertain': str(self.reserved_unknown),
                'billing_limit_guaranteed': False}


class APIBackend:
    def __init__(self, config, budget, *, transport=request_once, timeout=None, key=None):
        self.config, self.budget, self.transport = config, budget, transport
        self.timeout = timeout or (lambda: config.request_timeout_seconds)
        self.key = key if key is not None else os.environ.get('ANTHROPIC_API_KEY', '')
        if config.backend == 'anthropic' and not self.key:
            raise ValueError('ANTHROPIC_API_KEY is required')
        self.last_record = None

    def complete(self, request):
        c = self.config
        if not c.live_enabled:
            raise PermissionError('live model execution is disabled')
        if set(request) != {'model', 'messages', 'max_tokens'} or request['model'] != c.model or request['max_tokens'] != c.max_output_tokens:
            raise ValueError('backend request differs from configured common contract')
        messages = request['messages']
        if (not isinstance(messages, list) or len(messages) != 2 or messages[0].get('role') != 'system'
                or messages[1].get('role') != 'user' or any(not isinstance(m.get('content'), str) for m in messages)):
            raise ValueError('expected one text system and one text user message')
        reservation = self.budget.reserve()  # before any HTTP, retained even on an uncertain result
        begin = time.monotonic()
        self.last_record = {'outcome': 'entered', 'backend': c.backend, 'model': c.model}
        def post(url, body, headers):
            self.budget.http_requests += 1
            return json_request(url, body, headers, self.timeout(), self.transport)
        if c.backend == 'anthropic':
            headers = {'x-api-key': self.key, 'anthropic-version': c.anthropic_version}
            common = {'model': c.model, 'system': messages[0]['content'], 'messages': messages[1:],
                      'thinking': {'type': c.thinking}}
            count = post('https://api.anthropic.com/v1/messages/count_tokens', common, headers)['input_tokens']
            if type(count) is not int or count < 0 or count > c.max_input_tokens:
                raise BudgetExceeded('token-count preflight exceeds input cap; no generation sent')
            value = post('https://api.anthropic.com/v1/messages',
                         {**common, 'max_tokens': c.max_output_tokens, 'output_config': {'effort': c.effort}}, headers)
            self.last_record = {'outcome': 'response_received', 'backend': c.backend, 'model': value.get('model'),
                                'message_id': value.get('id'), 'stop_reason': value.get('stop_reason'),
                                'usage': value.get('usage'), 'provider_response': value}
            if value.get('model') != c.model:
                raise ValueError('provider returned a different model')
            usage = value['usage']
            if usage.get('cache_creation_input_tokens', 0) or usage.get('cache_read_input_tokens', 0):
                raise ValueError('unexpected caching; pricing not covered, reservation remains uncertain')
            inputs, outputs = usage['input_tokens'], usage['output_tokens']
            self.budget.settle(reservation, inputs, outputs)
            if value.get('stop_reason') != 'end_turn':
                raise ValueError('incomplete/non-text assistant turn; no action will be dispatched')
            blocks = value['content']
            if not isinstance(blocks, list) or any(b.get('type') not in ('text', 'thinking', 'redacted_thinking') for b in blocks):
                raise ValueError('unexpected content/tool call')
            content = ''.join(b['text'] for b in blocks if b['type'] == 'text')
        else:
            # The local model's pricing is explicitly configured; no Anthropic key is sent.
            origin = c.local_model_url.rstrip('/').removesuffix('/v1')
            count = post(origin + '/tokenize', {'model': c.model, 'messages': messages,
                                              'add_generation_prompt': True}, {})['count']
            if type(count) is not int or not 0 <= count <= c.max_input_tokens:
                raise BudgetExceeded('local tokenizer preflight exceeds input cap; no generation sent')
            value = post(origin + '/v1/chat/completions', dict(request), {})
            self.last_record = {'outcome': 'response_received', 'backend': c.backend, 'provider_response': value}
            usage, choice = value['usage'], value['choices'][0]
            inputs, outputs = usage['prompt_tokens'], usage['completion_tokens']
            self.budget.settle(reservation, inputs, outputs)
            if value.get('model') != c.model or choice.get('finish_reason') != 'stop':
                raise ValueError('model mismatch or incomplete local response')
            content = choice['message']['content']
            self.last_record = {'outcome': 'response_received', 'backend': c.backend, 'model': c.model,
                                'usage': usage, 'stop_reason': choice['finish_reason'], 'provider_response': value}
        if not isinstance(content, str) or not content:
            raise ValueError('no assistant text')
        self.last_record['assistant_text'] = content
        return CompletionResult(content, inputs, outputs, time.monotonic() - begin)


def run_cli(argv, stdin_text, env, cwd, timeout):
    """One owned CLI process group with an absolute timeout; no retry inside."""
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=env, cwd=cwd, start_new_session=True, text=True)
    try:
        out, err = process.communicate(stdin_text, timeout=timeout)
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(10)
        raise
    return process.returncode, out, err


def cli_version(executable, runner=run_cli):
    code, out, _ = runner([executable, '--version'], '', {k: os.environ[k] for k in CLI_ENVIRONMENT if k in os.environ},
                          tempfile.gettempdir(), 30)
    match = re.match(r'\s*(\d+)\.(\d+)\.(\d+)', out or '')
    if code != 0 or not match:
        raise ValueError('could not read the Claude Code CLI version')
    return tuple(int(g) for g in match.groups())


class ClaudeCodeBackend:
    """Uses the signed-in Claude subscription through `claude -p`: no tools, no settings, no MCP, no API key."""

    def __init__(self, config, budget, *, timeout=None, runner=run_cli, executable=None, version=None):
        if config.backend != 'claude_code':
            raise ValueError('ClaudeCodeBackend needs backend claude_code')
        self.config, self.budget, self.runner = config, budget, runner
        self.timeout = timeout or (lambda: config.request_timeout_seconds)
        self.executable = executable or shutil.which(config.claude_cli)
        if not self.executable:
            raise ValueError('Claude Code CLI not found: ' + config.claude_cli)
        self.version = version or cli_version(self.executable, runner)
        if self.version < MIN_CLAUDE_CLI:
            raise ValueError('Claude Code %s is too old for %s; need %s or newer (run: brew upgrade claude-code)' % (
                '.'.join(map(str, self.version)), config.model, '.'.join(map(str, MIN_CLAUDE_CLI))))
        from .policy import response_schema
        self.schema = json.dumps(response_schema(config.stage), separators=(',', ':'))
        self.last_record = None
        self.cli_changes = 0
        self.identity = self.file_identity()

    def file_identity(self):
        try:
            st = os.stat(os.path.realpath(self.executable))
        except OSError:
            return None
        return st.st_ino, st.st_size, st.st_mtime_ns

    def refresh_if_replaced(self):
        """Another Claude Code session may auto-update the shared CLI mid-run: record the version actually used."""
        if self.identity is None:  # an injected runner with no real executable (tests)
            return
        identity = self.file_identity()
        if identity is None:
            raise TransportFailure('Claude Code CLI is missing (possibly mid-update)')
        if identity != self.identity:
            self.version = cli_version(self.executable, self.runner)
            self.identity = identity
            self.cli_changes += 1
            if self.version < MIN_CLAUDE_CLI:
                raise BudgetExceeded('Claude Code CLI was replaced by a version too old for ' + self.config.model)

    def environment(self):
        env = {k: os.environ[k] for k in CLI_ENVIRONMENT if k in os.environ}
        env['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] = str(self.config.max_output_tokens)
        env['DISABLE_AUTOUPDATER'] = '1'
        # Each call is a fresh one-shot session with a unique prompt: cache writes are billed and never read back.
        env['DISABLE_PROMPT_CACHING'] = '1'
        return env

    def complete(self, request):
        c = self.config
        if not c.live_enabled:
            raise PermissionError('live model execution is disabled')
        if set(request) != {'model', 'messages', 'max_tokens'} or request['model'] != c.model or request['max_tokens'] != c.max_output_tokens:
            raise ValueError('backend request differs from configured common contract')
        messages = request['messages']
        if (not isinstance(messages, list) or len(messages) != 2 or messages[0].get('role') != 'system'
                or messages[1].get('role') != 'user' or any(not isinstance(m.get('content'), str) for m in messages)):
            raise ValueError('expected one text system and one text user message')
        # No token-count endpoint on this path: a conservative two-characters-per-token estimate.
        estimate = (len(messages[0]['content']) + len(messages[1]['content'])) // 2
        if estimate > c.max_input_tokens:
            raise BudgetExceeded('estimated prompt exceeds the input cap; no generation sent')
        self.refresh_if_replaced()
        reservation = self.budget.reserve()
        begin = time.monotonic()
        self.last_record = {'outcome': 'entered', 'backend': c.backend, 'model': c.model,
                            'cli_version': '.'.join(map(str, self.version)), 'cli_changes': self.cli_changes}
        argv = [self.executable, '-p', '--model', c.model, '--effort', c.effort, '--output-format', 'json',
                '--tools', '', '--json-schema', self.schema, '--system-prompt', messages[0]['content'],
                '--no-session-persistence', '--setting-sources', '', '--strict-mcp-config', '--disable-slash-commands']
        limit = self.timeout()
        if limit <= 0:
            raise TransportFailure('no model time remains')
        workdir = tempfile.mkdtemp(prefix='claude-arc-cli-')  # empty: no CLAUDE.md, project memory or settings
        try:
            self.budget.http_requests += 1
            try:
                code, out, err = self.runner(argv, messages[1]['content'], self.environment(), workdir, limit)
            except subprocess.TimeoutExpired:
                raise TransportFailure('Claude Code call exceeded its deadline; usage unknown')
            except OSError as exc:
                raise TransportFailure('Claude Code could not be started: ' + type(exc).__name__)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        try:
            value = json.loads(out)
        except (TypeError, ValueError):
            self.last_record = {**self.last_record, 'outcome': 'unreadable', 'exit_code': code, 'stderr_tail': (err or '')[-500:]}
            raise TransportFailure('Claude Code returned no JSON result')
        usage, by_model = value.get('usage') or {}, value.get('modelUsage') or {}
        self.last_record = {**self.last_record, 'outcome': 'response_received', 'exit_code': code,
            'subtype': value.get('subtype'), 'is_error': value.get('is_error'), 'api_error_status': value.get('api_error_status'),
            'stop_reason': value.get('stop_reason'), 'terminal_reason': value.get('terminal_reason'),
            'num_turns': value.get('num_turns'), 'duration_ms': value.get('duration_ms'), 'usage': usage,
            'model_usage': by_model, 'notional_cost_usd': value.get('total_cost_usd'), 'session_id': value.get('session_id')}
        if value.get('is_error') or value.get('subtype') != 'success' or code != 0:
            text = str(value.get('result'))[:300]
            self.last_record['error_text'] = text
            if value.get('api_error_status') in (401, 403) or PLAN_STOP.search(text):
                # Plan limit or login problem: no later call can succeed, so stop rather than retry.
                raise ProviderStopped('Claude Code cannot continue: ' + text)
            raise TransportFailure('Claude Code reported an error: ' + text)
        if c.model not in by_model:
            raise ValueError('response did not come from the configured model')
        inputs = sum(int(usage.get(k) or 0) for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
        outputs = int(usage.get('output_tokens') or 0)
        turns = value.get('num_turns')
        self.budget.settle(reservation, inputs, outputs, turns if type(turns) is int and 1 <= turns <= 8 else 1)
        answer = value.get('structured_output')
        if not isinstance(answer, dict):
            raise ValueError('no structured output; no action will be dispatched')
        content = json.dumps(answer, separators=(',', ':'), allow_nan=False)
        self.last_record['assistant_text'] = content
        return CompletionResult(content, inputs, outputs, time.monotonic() - begin)
