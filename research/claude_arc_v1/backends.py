"""Backends implement the existing CompletionClient.complete contract, not a new agent."""
from decimal import Decimal
import os
import time

from agent.e1_policy import CompletionResult
from .transport import json_request, request_once


class BudgetExceeded(RuntimeError):
    pass


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

    def settle(self, reservation, inputs, outputs):
        c = self.config
        if (type(inputs) is not int or type(outputs) is not int or not 0 <= inputs <= c.max_input_tokens
                or not 0 <= outputs <= c.max_output_tokens):
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
