"""CPU rehearsal stand-in for vLLM (never live; not target evidence): v2's fake server answering v3 questions."""
from research.evidence_comprehension_v2 import fake_server as _v2
from research.evidence_comprehension_v2.fake_server import (  # noqa: F401  (re-exported, unchanged)
    ABORT_DELAY, FAULTS, HANG_AT, HANG_FAULTS, TRUNCATED, count_tokens, request_sha)


class ScriptedAnswers(_v2.ScriptedAnswers):
    """v2's answer rule (v1's buckets, v2's wrong answers), keyed to the v3 requests; v2's set is not loaded."""

    def __init__(self):
        from research.evidence_comprehension_v3.probes import build_request, load_frozen
        frozen, _ = load_frozen()
        contexts = {c['context_id']: c for c in frozen['contexts']}
        self.by_sha = {request_sha(build_request(contexts[p['context_id']], p)): p for p in frozen['probes']}
        self.seen = {}


class FakeVLLM(_v2.FakeVLLM):
    def __init__(self, *, fault='none', latency_seconds=0.0, answers=None):
        super().__init__(fault=fault, latency_seconds=latency_seconds, answers=answers or ScriptedAnswers())
