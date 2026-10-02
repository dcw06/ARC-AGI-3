"""CPU rehearsal stand-in for vLLM (never live; not target evidence): v2's fake server answering these questions.

Hand-written adapter, as in WS3 questionnaire v1: v1's answer buckets (mostly correct; deterministic wrong, invalid,
truncated and pass-2-divergent answers), keyed to this question set's requests.
"""
from research.evidence_comprehension_v2 import fake_server as _v2
from research.evidence_comprehension_v2.fake_server import (  # noqa: F401  (re-exported, unchanged)
    ABORT_DELAY, FAULTS, HANG_AT, HANG_FAULTS, TRUNCATED, count_tokens, request_sha)


class ScriptedAnswers(_v2.ScriptedAnswers):
    def __init__(self):
        from research.progress_subgoal_v1.probes import build_request, load_frozen
        frozen, _ = load_frozen()
        contexts = {c['context_id']: c for c in frozen['contexts']}
        self.by_sha = {request_sha(build_request(contexts[p['context_id']], p)): p for p in frozen['probes']}
        self.seen = {}

    @staticmethod
    def wrong(probe):
        from research.progress_subgoal_v1.questions import ANSWERS
        return next(a for a in ANSWERS[probe['family']] if a != probe['key'])


class FakeVLLM(_v2.FakeVLLM):
    def __init__(self, *, fault='none', latency_seconds=0.0, answers=None):
        super().__init__(fault=fault, latency_seconds=latency_seconds, answers=answers or ScriptedAnswers())
