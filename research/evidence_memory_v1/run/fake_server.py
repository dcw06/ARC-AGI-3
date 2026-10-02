"""CPU rehearsal stand-in for vLLM (never live; not target evidence): v1's fake server answering Stage 1 questions.

The server is run/fake_vllm.py, derived from v1's with one change: its canary test is an overridable method. Stage 1's
user message is prose ('Evidence: ...'), so v1's rule (a user message not starting with '{' is the canary) would treat
every Stage 1 question as the canary: the questionnaire call counter would never advance and no fault keyed to
HANG_AT would fire. Here the canary is any request outside the frozen Stage 1 set (identified by request hash); the
service refuses any other unlisted request before it reaches the server.

v1's answer buckets are kept (mostly the key; deterministic wrong, invalid, truncated and pass-2-divergent answers).
"""
import hashlib
import json

from research.evidence_memory_v1.run import fake_vllm as _base
from research.evidence_memory_v1.run.fake_vllm import (  # noqa: F401  (re-exported, unchanged)
    ABORT_DELAY, FAULTS, HANG_AT, HANG_FAULTS, TRUNCATED, count_tokens, request_sha)

CANARY_ANSWER = json.dumps({'action': {'action_id': 6, 'action_data': {'x': 5, 'y': 5}}})  # v1's canary reply


class ScriptedAnswers(_base.ScriptedAnswers):
    def __init__(self):
        from research.evidence_memory_v1.run.probes import build_request, load_frozen
        frozen, _ = load_frozen()
        contexts = {c['context_id']: c for c in frozen['contexts']}
        self.by_sha = {request_sha(build_request(contexts[p['context_id']], p)): p for p in frozen['probes']}
        self.seen = {}

    def is_question(self, request):
        return request_sha(request) in self.by_sha

    def __call__(self, request):
        probe = self.by_sha.get(request_sha(request))
        if probe is None:
            user = request['messages'][-1]['content'] if request.get('messages') else ''
            return '{"values":["not_in_probe_set"]}' if str(user).startswith('Evidence:') else CANARY_ANSWER
        occurrence = self.seen[probe['probe_id']] = self.seen.get(probe['probe_id'], 0) + 1
        bucket = int(hashlib.sha256(probe['probe_id'].encode()).hexdigest(), 16) % 100
        if bucket < 3:
            return 'not json'
        if bucket == 3:  # truncated at the token cap: the text may look valid, but the finish is 'length'
            return TRUNCATED + json.dumps(probe['key'])
        wrong = bucket < 9 or (occurrence == 2 and bucket < 12)
        return json.dumps(self.wrong(probe) if wrong else probe['key'])

    @staticmethod
    def wrong(probe):
        """A schema-valid answer that differs from the key."""
        if probe['kind'] == 'recall':
            other = ['changed_then_returned'] if probe['key']['values'] != ['changed_then_returned'] else ['no_observed_change']
            return {'values': other}
        candidates = probe['question']['candidates']
        return {'choice': next((c for c in candidates if c != probe['key']['choice']), candidates[0])}


class FakeVLLM(_base.FakeVLLM):
    def __init__(self, *, fault='none', latency_seconds=0.0, answers=None):
        super().__init__(fault=fault, latency_seconds=latency_seconds, answers=answers or ScriptedAnswers())

    def is_canary(self, request):
        """The canary is the one request outside the frozen Stage 1 set; every Stage 1 question counts."""
        return not self.answers.is_question(request)
