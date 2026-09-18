"""Acceptance for the approved, single arc_action_v12 startup completion."""
import math
import re


def valid_canary(audit):
    if not isinstance(audit, dict):
        return False
    prompt = audit.get('server_prompt_tokens')
    local = audit.get('tokenizer_prompt_tokens')
    completion = audit.get('server_completion_tokens')
    duration = audit.get('service_seconds')
    digest = audit.get('request_sha256')
    return (
        audit.get('status') == 'passed'
        and audit.get('action_contract') == 'arc_action_v12'
        and type(prompt) is int and type(local) is int and 0 < prompt == local
        and prompt + 128 <= 65536
        and type(completion) is int and 1 <= completion <= 128
        and type(duration) in (int, float) and math.isfinite(duration) and duration >= 0
        and isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest) is not None
    )
