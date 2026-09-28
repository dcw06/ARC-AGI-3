"""CPU rehearsal stand-in for vLLM (never used in live mode; not target evidence).

v1's fake server, unchanged, answering the frozen v2 questions: mostly correct, with deterministic wrong,
invalid, truncated and pass-2-divergent answers so scoring, agreement and invalid-pair handling are
exercised on every family.
"""
from research.evidence_comprehension_v1 import fake_server as _v1
from research.evidence_comprehension_v1.fake_server import (  # noqa: F401  (re-exported, unchanged)
    ABORT_DELAY, FAULTS, HANG_AT, HANG_FAULTS, TRUNCATED, count_tokens, request_sha)


class ScriptedAnswers(_v1.ScriptedAnswers):
    """v1's answer rule, keyed to the v2 requests."""

    def __init__(self):
        from research.evidence_comprehension_v2.probes import build_request, load_frozen
        frozen, _ = load_frozen()
        contexts = {c['context_id']: c for c in frozen['contexts']}
        self.by_sha = {request_sha(build_request(contexts[p['context_id']], p)): p for p in frozen['probes']}
        self.seen = {}

    @staticmethod
    def wrong(probe):
        """A schema-valid answer that differs from the key."""
        from research.evidence_comprehension_v2.probes import ANSWER_SCHEMAS
        family, key = probe['family'], probe['key']
        schema = ANSWER_SCHEMAS[family]
        if 'enum' in schema:
            return next(v for v in schema['enum'] if v != key)
        if family == 'qualifying_steps':
            return sorted(set(key) ^ {63})
        if family in ('legal_actions', 'coordinate_rule', 'legal_coordinate_actions'):
            return sorted(set(key) ^ {7})
        if family == 'tried_unchanged':
            return key[1:] if key else [{'action_id': 1, 'action_data': {}}]
        return 'dispatch_failed' if key != 'dispatch_failed' else 'outcome_unknown'


class FakeVLLM(_v1.FakeVLLM):
    def __init__(self, *, fault='none', latency_seconds=0.0, answers=None):
        super().__init__(fault=fault, latency_seconds=latency_seconds, answers=answers or ScriptedAnswers())
