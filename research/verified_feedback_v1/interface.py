"""Matched summary-only versus explicit verified executed-feedback requests."""
from copy import deepcopy
import json

from research.action_effect_choice_v2.interface import make_request as baseline_request
from research.initial_geometry_assistance_v1.geometry import digest
from research.recent_feedback_v1.interface import displayed_history
from .feedback import build_feedback, display

CONDITIONS = ('summary_only', 'verified_feedback')


def make_request(base, pair, condition, previous=None, *, study_decision_index,
                 restored_prefix_length, trajectory_id, frozen=None, forecast_pin=None,
                 transition=None, transition_pin=None, current=None):
    if condition not in CONDITIONS:
        raise ValueError('unknown feedback condition')
    body = baseline_request(base, pair, 'neutral_choice', previous,
        study_decision_index=study_decision_index, restored_prefix_length=restored_prefix_length)
    if study_decision_index == 0:
        if any(value is not None for value in (frozen, forecast_pin, transition, transition_pin, current)):
            raise ValueError('no previous study feedback exists at the first decision')
        return body
    receipt = build_feedback(frozen, forecast_pin, transition, transition_pin,
        trajectory_id=trajectory_id, study_decision_index=study_decision_index,
        restored_prefix_length=restored_prefix_length, current=current)
    if digest(frozen['answer']) != digest(previous) or digest(frozen['candidates']) != digest(pair):
        raise ValueError('request previous answer or candidates differ from pre-dispatch commitment')
    step, current_grid, history = displayed_history(base)
    info, before, after = history[-1]
    meta = json.loads(base['messages'][1]['content'][0]['text'])
    if (step != transition['step']+1 or info['historical_step'] != transition['step'] or
            digest(info['action']) != digest(transition['action']) or
            before != tuple(map(tuple, transition['before']['grid'])) or
            after != tuple(map(tuple, transition['after']['grid'])) or current_grid != after or
            info['before_state'] != transition['before']['state'] or
            info['after_state'] != current['state'] or info['after_levels_completed'] != current['levels_completed'] or
            meta['current_state'] != current['state'] or meta['current_levels_completed'] != current['levels_completed'] or
            digest(meta['current_legal_actions']) != digest(current['legal_actions'])):
        raise ValueError('displayed previous transition/current observation differs from receipt')
    if condition == 'verified_feedback':
        body['messages'][1]['content'].append({'type': 'text', 'text': json.dumps(
            display(receipt), sort_keys=True, separators=(',', ':'), allow_nan=False)})
    return body
