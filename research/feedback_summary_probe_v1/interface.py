"""Reuse the tested summary; isolate factual reading from subsequent control."""
from research.recent_feedback_v1.interface import VARIANTS, request_for_variant
from research.feedback_probe_v1.interface import recognition_request as original_recognition


def policy_request(base, variant):
    return request_for_variant(base, variant)


def recognition_request(base, variant):
    # Build summary from the raw displayed input, before adding the question.
    policy = policy_request(base, variant)
    factual = original_recognition(base)
    if variant == 'recent_summary':
        factual['messages'][1]['content'].insert(-1, policy['messages'][1]['content'][-1])
    return factual
