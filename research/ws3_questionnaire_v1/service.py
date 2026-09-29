"""Questionnaire model service for the WS3 run: v1's reviewed service with the WS3 allow-list.

Only the allow-list, its digest and the call ceiling (the frozen schedule's length) change. It subclasses v1's
service directly, so no other question set is loaded besides v1's small one in the parent constructor.
"""
from research.evidence_comprehension_v1 import service as _v1
from research.evidence_comprehension_v1.service import (  # noqa: F401  (re-exported, unchanged)
    CallCancelled, ProxyService, ServerConfigViolation, ServerNotIdle, finite_seconds, validate_ready,
    validate_server_config)


def frozen_requests():
    from research.action_effect_history_v1.service import request_hash
    from research.ws3_questionnaire_v1.probes import build_request, load_frozen
    frozen, digest = load_frozen()
    contexts = {c['context_id']: c for c in frozen['contexts']}
    allowed = {request_hash(build_request(contexts[p['context_id']], p)): (p['probe_id'], p['family'])
               for p in frozen['probes']}
    return allowed, digest, sum(len(block['probe_ids']) for block in frozen['schedule'])


class QuestionnaireService(_v1.QuestionnaireService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed, self.probe_set_sha256, self.max_calls = frozen_requests()
