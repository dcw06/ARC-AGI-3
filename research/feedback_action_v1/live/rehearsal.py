"""CPU rehearsal model for the connected harness (never used in live mode; no model, no GPU).

The scripted completions are the CPU fake server's (`live/fake_server.py`), unchanged. This module adds what the
connected rehearsal needs on top of them:
- transport faults (`transport`, `slow`) and the fake server's own modes (`always_invalid`, `truncated_candidate`);
- optionally the pinned tokenizer (FA1_REHEARSAL_TOKENIZER=<folder>): prompt tokens are then counted exactly as the
  service admits them, and completion tokens from the scripted text plus the end-of-sequence token, so the
  cross-process token audit runs on real counts;
- optionally the pinned guided-decoding library (FA1_REHEARSAL_GRAMMAR=1, model interpreter only): every request's
  response_format is compiled by xgrammar exactly as vLLM 0.19's default backend compiles it (json_schema,
  any_whitespace=True) and the scripted completion must be accepted by that grammar;
- dispatch faults for the game adapter (`dispatch_failed`, `dispatch_unknown`), rehearsal-gated.
Scripted outputs exercise plumbing; they say nothing about how a model behaves.
"""
import json
import os
import time
from types import SimpleNamespace

HOST_FAULTS = ('none', 'model_startup', 'transport', 'slow', 'always_invalid', 'truncated_candidate')
DISPATCH_FAULTS = ('dispatch_failed', 'dispatch_unknown')
TRANSPORT_FAILURE_CALL = 6   # the policy call (counting the canary as 0) at which `transport` fails
DISPATCH_FAULT_INDEX = 3     # the session-wide dispatch (1-based) at which a dispatch fault fires


def pinned_tokenizer(folder):
    """The pinned tokenizer, verified against the frozen tokenizer manifest before use."""
    from certification.phase4_integrated_v2.tokenizer_binding import verify
    from transformers import AutoTokenizer
    verify(folder)
    return AutoTokenizer.from_pretrained(str(folder), local_files_only=True, trust_remote_code=False)


class GrammarCheck:
    """xgrammar compilation and acceptance, as vLLM 0.19's default structured-output backend applies it."""

    def __init__(self):
        import xgrammar
        from xgrammar import testing
        self.xgr, self.accepts = xgrammar, testing._is_grammar_accept_string
        self.cache = {}
        self.checked = self.accepted = 0

    def __call__(self, request, content):
        # Property order is kept exactly as sent: the decoder enforces the schema's property order.
        schema = json.dumps(request['response_format']['json_schema']['schema'])
        grammar = self.cache.get(schema)
        if grammar is None:
            grammar = self.cache[schema] = self.xgr.Grammar.from_json_schema(schema, any_whitespace=True)
        self.checked += 1
        if not self.accepts(grammar, content):
            raise ValueError('scripted completion rejected by the request grammar')
        self.accepted += 1


class RehearsalTransport:
    def __init__(self, fault='none', *, tokenizer=None, grammar=None, slow_seconds=2.0):
        from research.feedback_action_v1.live.fake_server import ScriptedTransport
        if fault not in HOST_FAULTS:
            raise ValueError('rehearsal fault')
        mode = fault if fault in ('always_invalid', 'truncated_candidate') else 'normal'
        self.scripted, self.fault, self.slow = ScriptedTransport(mode), fault, slow_seconds
        self.tokenizer, self.grammar = tokenizer, grammar
        self.calls = -1  # the canary is call 0

    def __call__(self, request):
        self.calls += 1
        if self.fault == 'transport' and self.calls == TRANSPORT_FAILURE_CALL:
            raise ConnectionError('rehearsal transport failure')
        if self.fault == 'slow':
            time.sleep(self.slow)
        result = self.scripted(request)
        # `always_invalid` returns unparseable text a grammar-constrained decoder cannot produce; it rehearses the
        # runner's invalid-output path, so only the other completions are checked against the grammar.
        if self.grammar is not None and result.finish_reason == 'stop' and self.fault != 'always_invalid':
            self.grammar(request, result.content)
        if self.tokenizer is None:
            return result
        prompt = len(self.tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                                         truncation=False, **request['chat_template_kwargs']))
        completion = len(self.tokenizer.encode(result.content, add_special_tokens=False)) + 1  # plus end of turn
        if result.finish_reason == 'length':
            completion = request['max_tokens']
        elif completion > request['max_tokens']:
            raise ValueError('scripted completion exceeds its cap under the pinned tokenizer')
        return SimpleNamespace(content=result.content, prompt_tokens=prompt, completion_tokens=completion,
                               finish_reason=result.finish_reason)

    def summary(self):
        return {'policy_calls': max(0, self.calls), 'tokenizer': 'pinned' if self.tokenizer is not None else 'fixture',
                'grammar_checked': self.grammar.checked if self.grammar else 0,
                'grammar_accepted': self.grammar.accepted if self.grammar else 0, 'fault': self.fault,
                'evidence_class': 'scripted_model_not_target_evidence'}


def rehearsal_transport(fault):
    """The transport and tokenizer the rehearsal host uses, from the rehearsal environment."""
    folder = os.environ.get('FA1_REHEARSAL_TOKENIZER')
    tokenizer = pinned_tokenizer(folder) if folder else None
    grammar = GrammarCheck() if os.environ.get('FA1_REHEARSAL_GRAMMAR') == '1' else None
    return RehearsalTransport(fault, tokenizer=tokenizer, grammar=grammar), tokenizer


class FaultyAdapter:
    """Rehearsal only: the game adapter with one dispatch fault at the session's DISPATCH_FAULT_INDEX-th dispatch."""
    dispatched = 0  # session-wide, shared by every episode's adapter in this worker

    def __init__(self, fault, adapter):
        from .authority import rehearsal_gate
        rehearsal_gate()
        if fault not in DISPATCH_FAULTS:
            raise ValueError('dispatch fault')
        self.fault, self.adapter = fault, adapter

    def bootstrap(self):
        return self.adapter.bootstrap()

    def dispatch(self, action, before):
        type(self).dispatched += 1
        if type(self).dispatched == DISPATCH_FAULT_INDEX:
            if self.fault == 'dispatch_failed':
                from .runner import DispatchRejected
                raise DispatchRejected('rehearsal: dispatch refused before reaching the game')
            self.adapter.dispatch(action, before)  # applied, but the outcome is never observed
            raise ConnectionError('rehearsal: dispatch sent, outcome unknown')
        return self.adapter.dispatch(action, before)

    def close(self):
        return self.adapter.close()


def adapter_for(fault, adapter):
    return FaultyAdapter(fault, adapter) if fault in DISPATCH_FAULTS else adapter
