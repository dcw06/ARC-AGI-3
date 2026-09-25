"""Common corrected baseline and the action-effect-history candidate (request construction only).

This is a new baseline: not unchanged E1S-R and not a continuation of R8. Both arms use the same
system prompt, observation payload, response schema and decoding settings. The history arm's
observation carries exactly one extra field, `action_effect_history`, computed by a deterministic
frame-comparison tool from already-observed dispatches only.
"""
import copy
import json

BASELINE_ID = 'action_effect_history_v1_common_baseline'
HISTORY_FIELD = 'action_effect_history'
HISTORY_LIMIT = 4
MAX_TOKENS = 128

# Argument requirements verified against the pinned arcengine GameAction definitions:
# ACTION1-5 and ACTION7 are SimpleAction (no arguments); ACTION6 is ComplexAction with
# integer x and y constrained to 0..63; RESET (0) is never selected by the policy.
SYSTEM_PROMPT = (
    "You control one ARC-AGI-3 game from the supplied observation. Return only one compact JSON "
    "object matching the supplied action schema, with no rationale or Markdown, under 64 tokens.\n"
    "Actions: choose exactly one action_id from legal_actions. Never choose reset or action 0. "
    "ACTION6 is the only action that takes arguments: action_data must be {\"x\": X, \"y\": Y} with "
    "integers 0 to 63, where x is the column counted left to right and y is the row counted top to "
    "bottom, so the selected cell is current_grid[y][x]. Every other action (1, 2, 3, 4, 5, 7) takes "
    "empty action_data {}.\n"
    "An action being legal does not mean its effect is known. This prompt does not describe what any "
    "action does in this game; effects can only be learned from observations. history_compaction "
    "reports any older transitions omitted from this prompt."
)
HISTORY_DESCRIPTION = {
    'computed_by': 'deterministic frame-comparison tool, not the model',
    'scope': f'up to the {HISTORY_LIMIT} most recent dispatched actions since the last level change or reset, oldest first',
    'fields': 'changed_cells_by_frame counts cells that differ from the frame before that action; '
              'null means the dispatch failed or its outcome is unknown, not that nothing changed',
}


def history_field(history):
    """Current-segment entries only, most recent HISTORY_LIMIT, oldest first; already-observed data only."""
    # Keep only the current segment (history.view() may span earlier segments).
    records = history.records if history is not None else []
    segment = records[-1]['segment'] if records else 0
    if records:
        last = records[-1]
        if last['status'] == 'acknowledged' and (last['reset'] or last['level_delta']):
            segment += 1  # the next decision starts a new segment
    current = [r for r in records if r['segment'] == segment]
    shown = current[-HISTORY_LIMIT:]
    from research.action_effect_v1.records import policy_view
    return {**HISTORY_DESCRIPTION, 'omitted_entries': len(current) - len(shown),
            'entries': [{'step': r['step'], **policy_view(r)} for r in shown]}


def observation_payload(runtime):
    from agent.representation import build_raw_bundle
    return build_raw_bundle(runtime.observation, runtime.evidence, recent_limit=1).policy_payload()


def policy_request(runtime, arm, history=None, *, model='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8', seed=0):
    if arm not in ('baseline', 'history'):
        raise ValueError('arm')
    observation = observation_payload(runtime)
    if arm == 'history':
        observation[HISTORY_FIELD] = history_field(history)
    return build_request(observation, model=model, seed=seed)


def build_request(observation, *, model='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8', seed=0):
    from certification.phase4_transient_v2.action_contract import response_format
    legal = observation['legal_actions']
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': json.dumps({'observation': observation}, sort_keys=True, separators=(',', ':'))}]
    return {'model': model, 'messages': messages, 'temperature': 0, 'seed': seed, 'max_tokens': MAX_TOKENS,
            'chat_template_kwargs': {'enable_thinking': False}, 'response_format': copy.deepcopy(response_format(legal))}


def strip_history(request):
    """The request with the history field removed; must equal the baseline request exactly."""
    value = copy.deepcopy(request)
    payload = json.loads(value['messages'][1]['content'])
    payload['observation'].pop(HISTORY_FIELD, None)
    value['messages'][1]['content'] = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return value
