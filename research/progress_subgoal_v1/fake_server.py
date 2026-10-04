"""CPU rehearsal stand-in for vLLM (never live; not target evidence): v2's fake server answering these questions.

Hand-written adapter, as in WS3 questionnaire v1: v1's answer buckets (mostly correct; deterministic wrong, invalid,
truncated and pass-2-divergent answers), keyed to this question set's requests.

Plus one rehearsal fault (rehearsal_timing.REPEAT_FAULT): added latency only from the first pass-2 call. v1's server
reads `self.latency` after counting the call, and calls are sequential, so `latency` is a property of the call number.
"""
from research.evidence_comprehension_v2 import fake_server as _v2
from research.evidence_comprehension_v2.fake_server import (  # noqa: F401  (re-exported, unchanged)
    ABORT_DELAY, HANG_AT, HANG_FAULTS, TRUNCATED, count_tokens, request_sha)
from research.progress_subgoal_v1.rehearsal_timing import REPEAT_FAULT

# v1's server faults plus the pass-2 slowdown: the host forwards a fault to the server only if it is listed here.
FAULTS = _v2.FAULTS + (REPEAT_FAULT,)


class ScriptedAnswers(_v2.ScriptedAnswers):
    def __init__(self):
        from research.progress_subgoal_v1.probes import build_request, load_frozen
        frozen, _ = load_frozen()
        contexts = {c['context_id']: c for c in frozen['contexts']}
        self.by_sha = {request_sha(build_request(contexts[p['context_id']], p)): p for p in frozen['probes']}
        self.pass_1_calls = len(frozen['schedule'][0]['probe_ids'])
        self.seen = {}

    @staticmethod
    def wrong(probe):
        from research.progress_subgoal_v1.questions import ANSWERS
        return next(a for a in ANSWERS[probe['family']] if a != probe['key'])


class FakeVLLM(_v2.FakeVLLM):
    def __init__(self, *, fault='none', latency_seconds=0.0, answers=None):
        if fault not in FAULTS:
            raise ValueError('fake server fault')
        answers = answers or ScriptedAnswers()
        # The pass-2 fault adds latency only from the first pass-2 call (questionnaire call pass_1 + 1).
        self.slow_from = answers.pass_1_calls + 1 if fault == REPEAT_FAULT else None
        super().__init__(fault='none' if fault == REPEAT_FAULT else fault, latency_seconds=latency_seconds,
                         answers=answers)

    def latency_for(self, number):
        return self._latency if self.slow_from is None or number >= self.slow_from else 0.0

    @property
    def latency(self):
        return self.latency_for(getattr(self, 'completions', 0))

    @latency.setter
    def latency(self, value):
        self._latency = value
