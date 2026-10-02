"""Questionnaire model service for progress_subgoal_v1: v1's reviewed service with this question set's allow-list.

Hand-written adapter, the same as WS3 questionnaire v1's: only the allow-list, its digest and the call ceiling (the
schedule's length) change. It subclasses v1's service directly.
"""
from research.evidence_comprehension_v1 import service as _v1
from research.evidence_comprehension_v1.service import (  # noqa: F401  (re-exported, unchanged)
    CallCancelled, ProxyService, ServerConfigViolation, ServerNotIdle, finite_seconds, validate_ready,
    validate_server_config)


def frozen_requests():
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1.probes import build_request, load_frozen
    frozen, digest = load_frozen()
    contexts = {c['context_id']: c for c in frozen['contexts']}
    allowed = {request_hash(build_request(contexts[p['context_id']], p)): (p['probe_id'], p['family'])
               for p in frozen['probes']}
    return allowed, digest, sum(len(block['probe_ids']) for block in frozen['schedule'])


class QuestionnaireService(_v1.QuestionnaireService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed, self.probe_set_sha256, self.max_calls = frozen_requests()
