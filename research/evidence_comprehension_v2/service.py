"""Questionnaire model service for evidence comprehension v2: v1's reviewed service with the v2 allow-list.

The host serves only requests whose hash belongs to the frozen v2 question set, and at most as many calls
as the frozen schedule lists. Everything else (tokenizer admission, absolute per-call deadlines, cache and
idle verification, cancellation evidence, the worker-side proxy and the server-evidence validation) is
research/evidence_comprehension_v1/service.py, unchanged.
"""
from research.evidence_comprehension_v1 import service as _v1
from research.evidence_comprehension_v1.service import (  # noqa: F401  (re-exported, unchanged)
    CallCancelled, ProxyService, ServerConfigViolation, ServerNotIdle, finite_seconds, validate_ready,
    validate_server_config)


def frozen_requests():
    """{request_sha256: (probe_id, family)} for every frozen v2 question, the digest, and the call ceiling."""
    from research.action_effect_history_v1.service import request_hash
    from research.evidence_comprehension_v2.probes import build_request, load_frozen
    frozen, digest = load_frozen()
    contexts = {c['context_id']: c for c in frozen['contexts']}
    allowed = {request_hash(build_request(contexts[p['context_id']], p)): (p['probe_id'], p['family'])
               for p in frozen['probes']}
    return allowed, digest, sum(len(block['probe_ids']) for block in frozen['schedule'])


class QuestionnaireService(_v1.QuestionnaireService):
    """v1's service; only the allow-list, its digest and the call ceiling are the v2 question set's."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed, self.probe_set_sha256, self.max_calls = frozen_requests()
